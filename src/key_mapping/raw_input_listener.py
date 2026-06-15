"""Raw input listener that captures raw mouse deltas via RAWINPUT.

Creates a hidden window on a dedicated thread and registers for
WM_INPUT (raw mouse data) so the CameraController can read
hardware-level relative deltas for unbounded 3D camera control.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import collections
import logging
import threading
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Windows constants
# ---------------------------------------------------------------------------
WM_INPUT = 0x00FF
WM_NCDESTROY = 0x0082

RIM_TYPEMOUSE = 0

RID_INPUT = 0x10000003

RIDEV_REMOVE = 0x00000001
RIDEV_INPUTSINK = 0x00000100

HID_USAGE_PAGE_GENERIC = 0x01
HID_USAGE_GENERIC_MOUSE = 0x02

MOUSE_MOVE_RELATIVE = 0
MOUSE_MOVE_ABSOLUTE = 1

CS_HREDRAW = 2
CS_VREDRAW = 1

WS_POPUP = 0x80000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

SW_HIDE = 0

# ---------------------------------------------------------------------------
# ctypes structures for RAWINPUT
# ---------------------------------------------------------------------------


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", ctypes.c_uint32),
        ("dwSize", ctypes.c_uint32),
        ("hDevice", ctypes.c_void_p),
        ("wParam", ctypes.c_void_p),
    ]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", ctypes.c_uint16),
        ("usButtonFlags", ctypes.c_uint16),
        ("usButtonData", ctypes.c_uint16),
        ("ulRawButtons", ctypes.c_uint32),
        ("lLastX", ctypes.c_long),
        ("lLastY", ctypes.c_long),
        ("ulExtraInformation", ctypes.c_uint32),
    ]


class RAWINPUT(ctypes.Structure):
    class _DATA(ctypes.Union):
        _fields_ = [
            ("mouse", RAWMOUSE),
        ]

    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", _DATA),
    ]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", ctypes.c_uint16),
        ("usUsage", ctypes.c_uint16),
        ("dwFlags", ctypes.c_uint32),
        ("hwndTarget", ctypes.c_void_p),
    ]


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint32),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint,
                              ctypes.c_void_p, ctypes.c_void_p)

# ---------------------------------------------------------------------------
# Load DLLs
# ---------------------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.RegisterClassW.restype = ctypes.c_uint16

user32.UnregisterClassW.argtypes = [ctypes.c_uint16, ctypes.c_void_p]
user32.UnregisterClassW.restype = ctypes.c_int

user32.CreateWindowExW.argtypes = [
    ctypes.c_uint32, ctypes.c_uint16, ctypes.c_wchar_p,
    ctypes.c_uint32, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
]
user32.CreateWindowExW.restype = ctypes.c_void_p

user32.DestroyWindow.argtypes = [ctypes.c_void_p]
user32.DestroyWindow.restype = ctypes.c_int

user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                   ctypes.c_void_p, ctypes.c_void_p]
user32.DefWindowProcW.restype = ctypes.c_int

user32.RegisterRawInputDevices.argtypes = [
    ctypes.POINTER(RAWINPUTDEVICE), ctypes.c_uint, ctypes.c_uint,
]
user32.RegisterRawInputDevices.restype = ctypes.c_int

user32.GetRawInputData.argtypes = [
    ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint), ctypes.c_uint,
]
user32.GetRawInputData.restype = ctypes.c_uint

user32.PeekMessageW.argtypes = [
    ctypes.POINTER(ctypes.wintypes.MSG),
    ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
]
user32.PeekMessageW.restype = ctypes.c_int

user32.TranslateMessage.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
user32.TranslateMessage.restype = ctypes.c_int

user32.DispatchMessageW.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_long

# GetModuleHandleW lives in kernel32, not user32
kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p


# ---------------------------------------------------------------------------
# RawInputListener
# ---------------------------------------------------------------------------

class RawInputListener:
    """Captures raw mouse deltas via a hidden RAWINPUT window.

    Typical usage::

        listener = RawInputListener()
        listener.start()
        ...
        dx, dy = listener.read_deltas()
        ...
        listener.stop()
    """

    _next_id = 0
    _id_lock = threading.Lock()

    POLL_INTERVAL = 0.001  # 1 ms message pump sleep

    def __init__(self):
        self._hwnd: int | None = None
        self._class_atom: int | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._started = threading.Event()

        # Unique class name per instance so rapid restart never clashes
        with self._id_lock:
            self._class_name = f"AutoGameRawInputWnd_{self._next_id}"
            self._next_id += 1

        # Thread-safe delta accumulator
        self._delta_queue: collections.deque[tuple[int, int]] = (
            collections.deque()
        )
        self._delta_lock = threading.Lock()

        # Keep a strong reference to the WNDPROC callback
        self._wndproc_cb = WNDPROC(self._wndproc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start the listener on a background thread.

        Returns True if the hidden window was created and RAWINPUT
        registered successfully.
        """
        if self._thread and self._thread.is_alive():
            return True

        self._stop_event.clear()
        self._started.clear()
        self._thread = threading.Thread(target=self._run,
                                        name="raw-input-listener",
                                        daemon=True)
        self._thread.start()

        # Wait up to 3 seconds for startup confirmation
        ok = self._started.wait(timeout=3.0)
        if not ok:
            logger.error("RawInputListener failed to start within 3s")
            self.stop()
            return False
        return True

    def stop(self) -> None:
        """Stop the listener and destroy the hidden window."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

        # Backup synchronous cleanup (normally already done by the thread)
        if self._hwnd is not None:
            try:
                user32.DestroyWindow(self._hwnd)
            except Exception:
                pass
            self._hwnd = None
        if self._class_atom is not None:
            try:
                hinst = kernel32.GetModuleHandleW(None)
                user32.UnregisterClassW(self._class_atom, hinst)
            except Exception:
                pass
            self._class_atom = None

    def read_deltas(self) -> tuple[int, int]:
        """Return the sum of all accumulated raw deltas since last call.

        Returns (dx, dy) where positive dx = right, positive dy = down.
        """
        with self._delta_lock:
            if not self._delta_queue:
                return 0, 0
            total_dx = sum(d for d, _ in self._delta_queue)
            total_dy = sum(d for _, d in self._delta_queue)
            self._delta_queue.clear()
        return total_dx, total_dy

    def peek_deltas(self) -> tuple[int, int]:
        """Return accumulated deltas WITHOUT consuming the queue.

        Use this when multiple consumers share one RawInputListener.
        Only one consumer should call read_deltas() (which clears the
        queue) to prevent unbounded growth.
        """
        with self._delta_lock:
            if not self._delta_queue:
                return 0, 0
            total_dx = sum(d for d, _ in self._delta_queue)
            total_dy = sum(d for _, d in self._delta_queue)
        return total_dx, total_dy

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Internal: thread entry point
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Background thread: create window, pump messages."""
        try:
            self._create_hidden_window()
        except Exception as exc:
            logger.error("RawInputListener: failed to create window: %s",
                         exc)
            return

        try:
            self._register_raw_input()
        except Exception as exc:
            logger.error("RawInputListener: failed to register: %s", exc)
            self._destroy_hidden_window()
            return

        self._started.set()
        logger.info("RawInputListener started (hwnd=%d)", self._hwnd)

        msg = ctypes.wintypes.MSG()
        while not self._stop_event.is_set():
            if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(self.POLL_INTERVAL)

        self._destroy_hidden_window()
        logger.info("RawInputListener stopped")

    # ------------------------------------------------------------------
    # Internal: window management
    # ------------------------------------------------------------------

    def _create_hidden_window(self) -> None:
        hinstance = kernel32.GetModuleHandleW(None)

        wc = WNDCLASS()
        wc.style = CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = ctypes.cast(self._wndproc_cb, ctypes.c_void_p)
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = self._class_name

        atom = user32.RegisterClassW(ctypes.byref(wc))
        if atom == 0:
            raise ctypes.WinError()
        self._class_atom = atom

        ex_style = WS_EX_TOOLWINDOW | WS_EX_LAYERED | WS_EX_TRANSPARENT
        hwnd = user32.CreateWindowExW(
            ex_style,
            atom,
            "",       # no title
            WS_POPUP,
            0, 0, 0, 0,
            None,     # no parent
            None,
            hinstance,
            None,
        )
        if hwnd is None:
            raise ctypes.WinError()
        self._hwnd = hwnd

        # Hide the window (it's already WS_POPUP with 0 size, but be safe)
        user32.ShowWindow(hwnd, SW_HIDE)

    def _destroy_hidden_window(self) -> None:
        if self._hwnd is not None:
            try:
                user32.DestroyWindow(self._hwnd)
            except Exception:
                pass
            self._hwnd = None
        if self._class_atom is not None:
            try:
                hinst = kernel32.GetModuleHandleW(None)
                user32.UnregisterClassW(self._class_atom, hinst)
            except Exception:
                pass
            self._class_atom = None

    def _register_raw_input(self) -> None:
        """Register for raw mouse input via the hidden window."""
        rid = RAWINPUTDEVICE()
        rid.usUsagePage = HID_USAGE_PAGE_GENERIC
        rid.usUsage = HID_USAGE_GENERIC_MOUSE
        rid.dwFlags = RIDEV_INPUTSINK
        rid.hwndTarget = self._hwnd

        ret = user32.RegisterRawInputDevices(
            ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE),
        )
        if not ret:
            raise ctypes.WinError()

    # ------------------------------------------------------------------
    # Internal: window procedure
    # ------------------------------------------------------------------

    def _wndproc(self, hwnd: int, msg: int, wparam: int,
                 lparam: int) -> int:
        """Window procedure for the hidden RAWINPUT window."""
        if msg == WM_INPUT:
            self._handle_raw_input(lparam)
            return 0
        if msg == WM_NCDESTROY:
            self._hwnd = None
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _handle_raw_input(self, lparam: int) -> None:
        """Parse WM_INPUT and extract mouse deltas."""
        # First call: get required buffer size
        size = ctypes.c_uint(0)
        ret = user32.GetRawInputData(
            lparam, RID_INPUT, None, ctypes.byref(size),
            ctypes.sizeof(RAWINPUTHEADER),
        )
        if ret == 0xFFFFFFFF or size.value == 0:
            return

        # Allocate buffer and read
        buf = ctypes.create_string_buffer(size.value)
        actual = user32.GetRawInputData(
            lparam, RID_INPUT, buf, ctypes.byref(size),
            ctypes.sizeof(RAWINPUTHEADER),
        )
        if actual == 0xFFFFFFFF:
            return

        raw = RAWINPUT.from_buffer(buf)
        if raw.header.dwType != RIM_TYPEMOUSE:
            return

        mouse = raw.data.mouse
        # Only accept relative deltas (ignore absolute, e.g. tablets)
        if mouse.usFlags & MOUSE_MOVE_ABSOLUTE:
            return

        dx = mouse.lLastX
        dy = mouse.lLastY
        if dx == 0 and dy == 0:
            return

        with self._delta_lock:
            self._delta_queue.append((dx, dy))
