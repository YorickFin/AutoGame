from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

from .ws_stream_server import WsStreamServer
from autoxkit.android.adb import AdbServerLauncher
from autoxkit.android import AudioVideoEvent, ScrcpyClient, ScrcpyOptions, StreamKind
from autoxkit.android.control import PointerManager, ACTION_DOWN


class ScrcpyManager:
    """Manages a single scrcpy connection for screen casting.

    Runs the async scrcpy client on a background thread and exposes
    thread-safe synchronous methods for the pywebview API.
    """

    PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins" / "scrcpy"

    ANDROID_KEYCODE_HOME = 3
    ANDROID_KEYCODE_BACK = 4
    ANDROID_KEYCODE_VOLUME_UP = 24
    ANDROID_KEYCODE_VOLUME_DOWN = 25
    ANDROID_KEYCODE_APP_SWITCH = 187
    ANDROID_ACTION_DOWN = 0
    ANDROID_ACTION_UP = 1



    # Android keycode map (key name -> Android keycode)
    ANDROID_KEYCODE_MAP = {
    "A": 29,
    "B": 30,
    "C": 31,
    "D": 32,
    "E": 33,
    "F": 34,
    "G": 35,
    "H": 36,
    "I": 37,
    "J": 38,
    "K": 39,
    "L": 40,
    "M": 41,
    "N": 42,
    "O": 43,
    "P": 44,
    "Q": 45,
    "R": 46,
    "S": 47,
    "T": 48,
    "U": 49,
    "V": 50,
    "W": 51,
    "X": 52,
    "Y": 53,
    "Z": 54,
    "0": 7,
    "1": 8,
    "2": 9,
    "3": 10,
    "4": 11,
    "5": 12,
    "6": 13,
    "7": 14,
    "8": 15,
    "9": 16,
    "Space": 62,
    "Enter": 66,
    "Back": 4,
    "Tab": 61,
    "Esc": 111,
    "CapsLock": 115,
    "LShift": 59,
    "RShift": 60,
    "LCtrl": 113,
    "RCtrl": 114,
    "LAlt": 57,
    "RAlt": 58,
    "LWin": 551,
    "RWin": 552,
    "Menu": 82,
    "Left": 21,
    "Up": 19,
    "Right": 22,
    "Down": 20,
    "Insert": 214,
    "Delete": 67,
    "Home": 3,
    "End": 123,
    "PgUp": 92,
    "PgDown": 93,
    "Numpad0": 144,
    "Numpad1": 145,
    "Numpad2": 146,
    "Numpad3": 147,
    "Numpad4": 148,
    "Numpad5": 149,
    "Numpad6": 150,
    "Numpad7": 151,
    "Numpad8": 152,
    "Numpad9": 153,
    "Multiply": 78,
    "Add": 81,
    "Subtract": 69,
    "Divide": 88,
    "Numlock": 143,
    "Decimal": 158,
    "F1": 131,
    "F2": 132,
    "F3": 133,
    "F4": 134,
    "F5": 135,
    "F6": 136,
    "F7": 137,
    "F8": 138,
    "F9": 139,
    "F10": 140,
    "F11": 141,
    "F12": 142
}

    # Mouse button names that map to touch events
    MOUSE_BUTTON_MAP_ADB = {
        'MLeft': 'touch',
        'MRight': 'touch',
        'Middle': 'touch',
        'MSide1': 'touch',
        'MSide2': 'touch',
    }

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="scrcpy-manager")
        self._thread.start()
        self._client: ScrcpyClient | None = None
        self._pump_task: asyncio.Task[None] | None = None
        self._ws_server: WsStreamServer | None = None
        self._last_session: tuple[int, int] | None = None
        self._launcher: AdbServerLauncher | None = None
        self._address: str | None = None
        self._pointer_manager = PointerManager()
        self._serial: str | None = None

    # ------------------------------------------------------------------ #
    # Public API (called from pywebview thread)
    # ------------------------------------------------------------------ #

    def start(self, serial: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Start a scrcpy connection."""
        return self._submit(self._start(serial, config))

    def stop(self) -> dict[str, Any]:
        """Stop the scrcpy connection."""
        return self._submit(self._stop())

    def status(self) -> dict[str, Any]:
        """Return current connection status."""
        if self._client is None:
            return {"running": False}
        return {
            "running": True,
            "deviceName": self._client.device_meta.device_name if self._client.device_meta else None,
        }

    def get_ws_port(self) -> int:
        """Return the WebSocket stream server port, or -1 if not running."""
        if self._ws_server is not None:
            return self._ws_server.port
        return -1

    def start_ws_stream(self) -> int:
        """Start the WebSocket stream server. Returns the port number."""
        return self._submit(self._start_ws_stream())

    def stop_ws_stream(self) -> None:
        """Stop the WebSocket stream server."""
        return self._submit(self._stop_ws_stream())

    async def _start_ws_stream(self) -> int:
        self._ws_server = WsStreamServer(self._loop)
        port = await self._ws_server.start()
        return port

    async def _stop_ws_stream(self) -> None:
        if self._ws_server is not None:
            await self._ws_server.stop()
            self._ws_server = None

    def send_touch(self, action: int, x: int, y: int, width: int, height: int) -> dict[str, Any]:
        return self._submit(self._send_touch(action, x, y, width, height))

    def send_keycode(self, keycode: int, action: int = 0) -> dict[str, Any]:
        return self._submit(self._send_keycode(action, keycode))

    def set_clipboard(self, text: str) -> dict[str, Any]:
        return self._submit(self._set_clipboard(text))

    def switch_to_wireless(self) -> dict[str, Any]:
        return self._submit(self._switch_to_wireless())

    def discover_usb_serial(self) -> str | None:
        return self._submit(self._discover_usb_serial())

    def volume_up(self) -> dict[str, Any]:
        return self._submit(self._volume_up())

    def volume_down(self) -> dict[str, Any]:
        return self._submit(self._volume_down())

    def back(self) -> dict[str, Any]:
        return self._submit(self._back())

    def switch_app(self) -> dict[str, Any]:
        return self._submit(self._switch_app())

    def home(self) -> dict[str, Any]:
        return self._submit(self._home())

    # ------------------------------------------------------------------ #
    # Async implementations
    # ------------------------------------------------------------------ #

    async def _start(self, serial: str | None, config: dict[str, Any] | None) -> dict[str, Any]:
        if self._client is not None:
            return self._make_status()

        cfg = config or {}
        video_source = cfg.get("videoSource", "display")
        audio_source = cfg.get("audioSource", "output")
        quality = cfg.get("quality", "unlimited")
        bitrate = cfg.get("bitrate", "unlimited")
        fps_limit = cfg.get("fpsLimit", "unlimited")

        video_enabled = video_source != "none"
        audio_enabled = audio_source != "none"

        server_args: list[str] = []
        if video_enabled:
            server_args.append(f"video_source={video_source}")
            if quality != "unlimited":
                server_args.append(f"max_size={quality}")
            if isinstance(bitrate, int):
                # Frontend sends bitrate as integer (1-100 Mbps)
                server_args.append(f"video_bit_rate={bitrate * 1000000}")
            if fps_limit != "unlimited":
                server_args.append(f"max_fps={fps_limit}")
        if audio_enabled:
            server_args.append(f"audio_source={audio_source}")
            server_args.append("audio_codec=raw")
        server_args.append("video_codec=h264")

        adb_path = self.PLUGIN_DIR / "adb.exe"
        server_path = self.PLUGIN_DIR / "scrcpy-server"

        options = ScrcpyOptions(
            serial=serial,
            adb_path=adb_path,
            server_path=server_path,
            video=video_enabled,
            audio=audio_enabled,
            control=True,
            log_level="info",
            server_args=server_args,
        )

        client = ScrcpyClient(options)
        try:
            await client.start()
        except Exception as exc:
            return {"running": False, "error": str(exc)}

        self._client = client
        if client is not None and client.control is not None:
            client.control.pointer_manager = self._pointer_manager
        await self._start_ws_stream()
        self._pump_task = asyncio.create_task(self._pump_events(client))
        return self._make_status()

    async def _stop(self) -> dict[str, Any]:
        if self._pump_task is not None:
            self._pump_task.cancel()
            self._pump_task = None
        if self._client is not None:
            await self._client.stop()
            self._client = None
        self._last_session = None
        return {"running": False}

    async def _send_touch(self, action: int, x: int, y: int, width: int, height: int) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.send_touch(action, x, y, width, height, pressure=0.0 if action == 1 else 1.0)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _send_keycode(self, action: int, keycode: int) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.send_keycode(action, keycode)
            if action == 0:
                await self._client.control.send_keycode(1, keycode)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _set_clipboard(self, text: str) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.set_clipboard(text, sequence=1, paste=False)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _switch_to_wireless(self) -> dict[str, Any]:

        try:
            if self._address is None:
                self._launcher = AdbServerLauncher(
                    adb_path=self.PLUGIN_DIR / "adb.exe",
                    server_path=self.PLUGIN_DIR / "scrcpy-server",
                )
                device_ip = await self._launcher.get_device_ip()
                await self._launcher.enable_tcpip(5555)
                self._address = f"{device_ip}:5555"

            await self._launcher.connect_tcpip(self._address)
            return {"ok": True, "serial": self._address}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _discover_usb_serial(self) -> str | None:
        self._launcher = AdbServerLauncher(
            adb_path=self.PLUGIN_DIR / "adb.exe",
            server_path=self.PLUGIN_DIR / "scrcpy-server",
        )

        return await self._launcher.discover_usb_serial()

    async def _volume_up(self) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.send_keycode(self.ANDROID_ACTION_DOWN, self.ANDROID_KEYCODE_VOLUME_UP)
            await self._client.control.send_keycode(self.ANDROID_ACTION_UP, self.ANDROID_KEYCODE_VOLUME_UP)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _volume_down(self) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.send_keycode(self.ANDROID_ACTION_DOWN, self.ANDROID_KEYCODE_VOLUME_DOWN)
            await self._client.control.send_keycode(self.ANDROID_ACTION_UP, self.ANDROID_KEYCODE_VOLUME_DOWN)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _back(self) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.send_keycode(self.ANDROID_ACTION_DOWN, self.ANDROID_KEYCODE_BACK)
            await self._client.control.send_keycode(self.ANDROID_ACTION_UP, self.ANDROID_KEYCODE_BACK)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _switch_app(self) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.send_keycode(self.ANDROID_ACTION_DOWN, self.ANDROID_KEYCODE_APP_SWITCH)
            await self._client.control.send_keycode(self.ANDROID_ACTION_UP, self.ANDROID_KEYCODE_APP_SWITCH)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    async def _home(self) -> dict[str, Any]:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            await self._client.control.send_keycode(self.ANDROID_ACTION_DOWN, self.ANDROID_KEYCODE_HOME)
            await self._client.control.send_keycode(self.ANDROID_ACTION_UP, self.ANDROID_KEYCODE_HOME)
            return {"ok": True}
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}


    # ------------------------------------------------------------------ #
    # Event pump
    # ------------------------------------------------------------------ #

    async def _pump_events(self, client: ScrcpyClient) -> None:
        try:
            async for event in client.av.events():
                await self._forward_to_ws(event)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _forward_to_ws(self, event: AudioVideoEvent) -> None:
        """Forward an AudioVideoEvent to the WebSocket stream server."""
        if self._ws_server is None:
            return

        codec = event.codec.label if event.codec else None

        if event.kind is StreamKind.SESSION and event.session is not None:
            self._last_session = (event.session.width, event.session.height)
            await self._ws_server.send_event("session", {
                "codec": codec,
                "width": event.session.width,
                "height": event.session.height,
                "clientResized": event.session.client_resized,
            })
        elif event.kind is StreamKind.VIDEO and event.payload:
            await self._ws_server.send_event(
                "video",
                {"pts": event.pts, "keyFrame": event.key_frame, "config": event.config},
                event.payload,
            )
        elif event.kind is StreamKind.AUDIO and event.payload:
            await self._ws_server.send_event(
                "audio",
                {"pts": event.pts},
                event.payload,
            )

    def _make_status(self) -> dict[str, Any]:
        if self._client is None:
            return {"running": False}
        return {
            "running": True,
            "deviceName": self._client.device_meta.device_name if self._client.device_meta else None,
        }

    def _submit(self, coro: Any) -> Any:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()



    # Key mapping: send events via scrcpy control stream

    def apply_key_mapping(self, mapping_data: dict) -> dict:
        self._active_key_mapping = mapping_data
        return {"ok": True}

    def remove_key_mapping(self) -> dict:
        self._active_key_mapping = None
        return {"ok": True}

    def key_mapping_trigger(self, key_name: str, action: str) -> dict:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        if action == "down":
            android_action = self.ANDROID_ACTION_DOWN
        elif action == "up":
            android_action = self.ANDROID_ACTION_UP
        else:
            return {"ok": False, "error": f"unknown action: {action}"}
        android_keycode = self.ANDROID_KEYCODE_MAP.get(key_name)
        if android_keycode is not None:
            self._submit(self._client.control.send_keycode(android_action, android_keycode))
            return {"ok": True}
        return {"ok": False, "error": f"unknown key: {key_name}"}

    def send_normalized_touch(self, action: int, x: float, y: float, pointer_id: int | None = None) -> dict:
        """Send touch event with normalized 0.0-1.0 coordinates.

        Converts to session pixel coordinates using last known session size.
        When *pointer_id* is ``None``, the ``send_touch_managed`` path is
        used (auto-allocate on DOWN / auto-release on UP).
        Returns ``{"ok": True, "pointer_id": <id>}`` on success.
        """
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        if not self._last_session:
            return {"ok": False, "error": "no session size"}
        sw, sh = self._last_session
        px = max(0, min(sw, int(x * sw)))
        py = max(0, min(sh, int(y * sh)))
        return self._submit(self._send_touch_managed(action, px, py, sw, sh, pointer_id))

    async def _send_touch_managed(self, action: int, x: int, y: int, width: int, height: int, pointer_id: int | None = None) -> dict:
        """Send touch event via control stream with optional pointer ID management.

        Wraps ``control.send_touch_managed`` and returns the allocated
        pointer_id in the response dict when applicable.
        """
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        try:
            pid = await self._client.control.send_touch_managed(
                action, x, y, width, height,
                pointer_id=pointer_id,
                pressure=0.0 if action == 1 else 1.0,
            )
            if pid is None and action == ACTION_DOWN:
                return {"ok": False, "error": "failed to allocate pointer (max 10 touches)"}
            result: dict[str, Any] = {"ok": True}
            if pid is not None:
                result["pointer_id"] = pid
            return result
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            return {"ok": False, "error": str(exc)}

    def key_mapping_reset(self) -> dict:
        """Reset the pointer manager, releasing all active touch pointers."""
        self._pointer_manager.reset()
        return {"ok": True}

    def get_pointer_manager(self) -> PointerManager:
        return self._pointer_manager


    def key_mapping_swipe(self, path_data: list) -> dict:
        if self._client is None or self._client.control is None:
            return {"ok": False, "error": "control stream is not running"}
        if not self._last_session:
            return {"ok": False, "error": "no session size"}
        try:
            sw, sh = self._last_session
            asyncio.run_coroutine_threadsafe(self._send_swipe_async(path_data, sw, sh), self._loop)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _send_swipe_async(self, path_data: list, sw: int, sh: int):
        if not path_data:
            return
        first = path_data[0]
        px = max(0, min(sw, int(first["x"] * sw)))
        py = max(0, min(sh, int(first["y"] * sh)))
        await self._client.control.send_touch(0, px, py, sw, sh, pointer_id=123)
        for i in range(1, len(path_data)):
            pt = path_data[i]
            delay = pt.get("delayMs", 0) - path_data[i-1].get("delayMs", 0)
            if delay > 0:
                await asyncio.sleep(delay / 1000.0)
            px = max(0, min(sw, int(pt["x"] * sw)))
            py = max(0, min(sh, int(pt["y"] * sh)))
            await self._client.control.send_touch(2, px, py, sw, sh, pointer_id=123)
        last = path_data[-1]
        px = max(0, min(sw, int(last["x"] * sw)))
        py = max(0, min(sh, int(last["y"] * sh)))
        await self._client.control.send_touch(1, px, py, sw, sh, pointer_id=123)

    # ------------------------------------------------------------------ #
    # Screen ratio management (adb shell wm size)
    # ------------------------------------------------------------------ #

    def set_screen_ratio(self, width_ratio: int, height_ratio: int) -> dict:
        return self._submit(self._set_screen_ratio(width_ratio, height_ratio))

    def reset_screen_ratio(self) -> dict:
        return self._submit(self._reset_screen_ratio())

    def _ensure_launcher(self) -> AdbServerLauncher:
        if self._launcher is None:
            self._launcher = AdbServerLauncher(
                adb_path=self.PLUGIN_DIR / "adb.exe",
                server_path=self.PLUGIN_DIR / "scrcpy-server",
                serial=self._serial,
            )
        return self._launcher

    async def _get_device_screen_size_via_adb(self):
        launcher = self._ensure_launcher()
        try:
            output = await launcher.shell_output("wm", "size")
            for line in output.splitlines():
                if "Physical size:" in line or "Override size:" in line:
                    size_str = line.split(":", 1)[-1].strip()
                    w_str, h_str = size_str.split("x", 1)
                    return int(w_str.strip()), int(h_str.strip())
            return None
        except Exception:
            return None

    async def _set_screen_ratio(self, width_ratio, height_ratio):
        if self._last_session:
            device_w, device_h = self._last_session
        else:
            sz = await self._get_device_screen_size_via_adb()
            if sz is None:
                return {"ok": False, "error": "cannot determine device screen size"}
            device_w, device_h = sz

        h = min(device_w, device_h)
        w = h * width_ratio // height_ratio

        if h > device_h or w > device_w:
            w = max(device_w, device_h)
            h = w * height_ratio // width_ratio

        launcher = self._ensure_launcher()
        try:
            output = await launcher.shell_output("wm", "size", f"{h}x{w}")
            return {
                "ok": True,
                "output": output.strip(),
                "size": f"{h}x{w}",
                "ratio": f"{width_ratio}:{height_ratio}",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _reset_screen_ratio(self):
        launcher = self._ensure_launcher()
        try:
            output = await launcher.shell_output("wm", "size", "reset")
            return {"ok": True, "output": output.strip()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

