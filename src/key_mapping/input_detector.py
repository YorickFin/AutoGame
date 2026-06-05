"""Input detector that monitors soft input state on Android device."""

from __future__ import annotations

import re
import threading
import time
from ..services import services


class InputDetector:
    """Monitors and reports input state."""

    def __init__(self):
        self._input_shown: bool | None = None
        self._input_just_hidden = False
        self._last_notify_state: tuple[bool, bool] | None = None
        self._poll_stop = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._poll_started = False

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    @property
    def _api(self):
        return services.api

    @property
    def input_shown(self) -> bool | None:
        return self._input_shown

    @input_shown.setter
    def input_shown(self, value: bool | None):
        self._input_shown = value

    def read_and_clear_just_hidden(self) -> bool:
        val = self._input_just_hidden
        self._input_just_hidden = False
        return val

    def start(self):
        """Start input polling thread."""
        if self._poll_started:
            return
        self._poll_started = True
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self):
        """Stop input polling thread."""
        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
        self._poll_thread = None
        self._poll_started = False

    def reset(self):
        """Reset internal state."""
        self.stop()
        self.input_shown = None
        self._input_just_hidden = False
        self._last_notify_state = None

    def _queryinput_shown(self) -> bool | None:
        """Query Android if soft input is shown. Returns None if query fails."""
        output = self._scrcpy_manager.adb_shell("dumpsys", "input_method")
        if output is None:
            return None
        m = re.search(r"mInputShown=(true|false)", output)
        return m.group(1) == "true" if m else None

    def _notify_input_change(self, shown: bool, just_hidden: bool, api):
        """Notify frontend about input state change."""
        state = (shown, just_hidden)
        if api and self._last_notify_state != state:
            api._notify_input_state(shown, just_hidden)
            self._last_notify_state = state

    def _update_input_state(self, shown: bool | None, api):
        """Update input state and notify frontend of changes."""
        if shown is None:
            return

        prev = self.input_shown
        self.input_shown = shown

        if prev == shown:
            return

        if shown:
            self._notify_input_change(True, False, api)
        else:
            self._input_just_hidden = True
            self._notify_input_change(False, True, api)

    def _poll_loop(self):
        """Background polling loop for input state."""
        while not self._poll_stop.is_set():
            time.sleep(0.1)
            shown = self._queryinput_shown()
            if shown is not None:
                self._update_input_state(shown, self._api)
