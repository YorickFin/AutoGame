"""Button mapping executor for controls, swipes, and dpad operations."""

from __future__ import annotations

import math
from ..services import services


class ButtonMapping:
    """Handles button mapping operations: controls, swipes, and dpad."""

    _DIR_VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    _OPPOSITE_DIRS = {"up": "down", "down": "up", "left": "right", "right": "left"}

    def __init__(self):
        self._active_mapping = None
        self._down_state_keys: dict[str, tuple[int, float, float]] = {}
        self._dpad_states: dict[int, dict] = {}

    @property
    def active_mapping(self):
        return self._active_mapping

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    def apply(self, mapping_data):
        """Apply button mapping configuration."""
        self._active_mapping = mapping_data

    def remove(self):
        """Remove button mapping."""
        self.reset()
        self._active_mapping = None

    def reset(self):
        """Reset all button states."""
        self._down_state_keys.clear()
        self._dpad_states.clear()

    def get_mapped_keys(self):
        """Return set of all configured keys."""
        keys = set()
        if not self._active_mapping:
            return keys

        for ctrl in self._active_mapping.get("controls", []):
            k = ctrl.get("key")
            if k:
                keys.add(k)
        for swp in self._active_mapping.get("swipes", []):
            k = swp.get("key")
            if k:
                keys.add(k)
        for dpad in self._active_mapping.get("dpad", []):
            for _, info in dpad.get("keys", {}).items():
                k = info.get("key")
                if k:
                    keys.add(k)
        for cam in self._active_mapping.get("camera", []):
            k = cam.get("key")
            if k:
                keys.add(k)
        return keys

    @staticmethod
    def _resolve_edge(pressed_keys, key_to_dir, cx, cy, radius, sw=None, sh=None):
        """Resolve the edge position from a set of pressed dpad keys."""
        if not pressed_keys:
            return None
        dx = sum(ButtonMapping._DIR_VECTORS[key_to_dir[k]][0] for k in pressed_keys if k in key_to_dir)
        dy = sum(ButtonMapping._DIR_VECTORS[key_to_dir[k]][1] for k in pressed_keys if k in key_to_dir)

        radius = radius * 2

        if sw is not None and sh is not None and sw > 0 and sh > 0 and dx != 0 and dy != 0:
            dx_w = dx / sw
            dy_w = dy / sh
            length_w = math.sqrt(dx_w * dx_w + dy_w * dy_w)
            if length_w == 0:
                return None
            return (cx + dx_w / length_w * radius, cy + dy_w / length_w * radius)

        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return None
        return (cx + dx / length * radius, cy + dy / length * radius)

    def on_key_down(self, key_name) -> bool:
        """Handle key press for button mapping operations."""
        if not self._active_mapping:
            return False

        if key_name in self._down_state_keys:
            return False

        # Check single controls
        for ctrl in self._active_mapping.get("controls", []):
            if ctrl.get("key") == key_name:
                x = ctrl.get("x", 0.5)
                y = ctrl.get("y", 0.5)
                resp = self._scrcpy_manager.send_normalized_touch(0, x, y)
                if resp.get("ok"):
                    pid = resp.get("pointer_id")
                    if pid is not None:
                        self._down_state_keys[key_name] = (pid, x, y)
                return True

        # Check swipes
        for swp in self._active_mapping.get("swipes", []):
            if swp.get("key") == key_name:
                path = swp.get("path", [])
                if path:
                    self._scrcpy_manager.key_mapping_swipe(path)
                return True

        # Check dpad
        for dpad_idx, dpad in enumerate(self._active_mapping.get("dpad", [])):
            keys_config = dpad.get("keys", {})

            key_to_dir = {}
            dir_to_key = {}
            for dir_name, info in keys_config.items():
                k = info.get("key")
                if k:
                    key_to_dir[k] = dir_name
                    dir_to_key[dir_name] = k

            if key_name not in key_to_dir:
                continue

            cx = dpad.get("x", 0.5)
            cy = dpad.get("y", 0.5)
            radius = dpad.get("size", 0.06)

            _sw, _sh = self._scrcpy_manager._last_session if self._scrcpy_manager._last_session else (None, None)

            if dpad_idx not in self._dpad_states:
                self._dpad_states[dpad_idx] = {"pressed": set(), "keys_down": set(), "pid": None, "ex": 0.0, "ey": 0.0}

            state = self._dpad_states[dpad_idx]

            if key_name in state["pressed"]:
                return True

            new_dir_name = key_to_dir[key_name]
            opposite_dir = self._OPPOSITE_DIRS.get(new_dir_name)

            # 记录物理按键状态
            state["keys_down"].add(key_name)

            old_pressed = set(state["pressed"])
            old_edge = self._resolve_edge(old_pressed, key_to_dir, cx, cy, radius, _sw, _sh)

            new_pressed = set(old_pressed)
            new_pressed.add(key_name)
            if opposite_dir and opposite_dir in dir_to_key:
                opp_key = dir_to_key[opposite_dir]
                if opp_key in new_pressed:
                    new_pressed.remove(opp_key)
            state["pressed"] = new_pressed

            new_edge = self._resolve_edge(new_pressed, key_to_dir, cx, cy, radius, _sw, _sh)

            if new_edge is None:
                if state["pid"] is not None:
                    self._scrcpy_manager.send_normalized_touch(1, state["ex"], state["ey"], pointer_id=state["pid"])
                    state["pid"] = None
                return True

            if old_edge is None:
                resp = self._scrcpy_manager.send_normalized_touch(0, cx, cy)
                if resp.get("ok"):
                    pid = resp.get("pointer_id")
                    if pid is not None:
                        self._scrcpy_manager.send_normalized_touch(2, new_edge[0], new_edge[1], pointer_id=pid)
                        state["pid"] = pid
                        state["ex"], state["ey"] = new_edge
                return True

            ox, oy = old_edge
            nx, ny = new_edge
            old_len = math.sqrt((ox - cx) ** 2 + (oy - cy) ** 2)
            new_len = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
            if old_len > 0 and new_len > 0:
                dot = ((ox - cx) / old_len) * ((nx - cx) / new_len) + ((oy - cy) / old_len) * ((ny - cy) / new_len)
            else:
                dot = 1.0

            if dot < 0:
                self._scrcpy_manager.send_normalized_touch(1, state["ex"], state["ey"], pointer_id=state["pid"])
                resp = self._scrcpy_manager.send_normalized_touch(0, cx, cy)
                if resp.get("ok"):
                    pid = resp.get("pointer_id")
                    if pid is not None:
                        self._scrcpy_manager.send_normalized_touch(2, nx, ny, pointer_id=pid)
                        state["pid"] = pid
                        state["ex"], state["ey"] = nx, ny
            else:
                self._scrcpy_manager.send_normalized_touch(2, nx, ny, pointer_id=state["pid"])
                state["ex"], state["ey"] = nx, ny

            return True

        return False

    def on_key_up(self, key_name) -> bool:
        """Handle key release for button mapping operations."""
        if not self._active_mapping:
            return False

        # Check single controls
        item = self._down_state_keys.pop(key_name, None)
        if item is not None:
            pid, px, py = item
            self._scrcpy_manager.send_normalized_touch(1, px, py, pointer_id=pid)
            return True

        # Check dpad
        for dpad_idx, dpad in enumerate(self._active_mapping.get("dpad", [])):
            keys_config = dpad.get("keys", {})

            key_to_dir = {}
            dir_to_key = {}
            for dir_name, info in keys_config.items():
                k = info.get("key")
                if k:
                    key_to_dir[k] = dir_name
                    dir_to_key[dir_name] = k

            if key_name not in key_to_dir:
                continue

            if dpad_idx not in self._dpad_states:
                return True

            state = self._dpad_states[dpad_idx]

            new_dir_name = key_to_dir[key_name]
            opposite_dir = self._OPPOSITE_DIRS.get(new_dir_name)

            # 1. 移除物理按键记录
            state["keys_down"].discard(key_name)

            # 2. 如果该键不在触摸活跃集合中（被覆盖了），不处理触摸
            if key_name not in state["pressed"]:
                return True

            # 3. 从活跃集合中移除
            state["pressed"].discard(key_name)

            # 4. 检查相反方向是否还在物理按下 → 恢复
            if opposite_dir and opposite_dir in dir_to_key:
                opp_key = dir_to_key[opposite_dir]
                if opp_key in state["keys_down"]:
                    state["pressed"].add(opp_key)

            # 5. 后续触摸释放/移动逻辑
            if not state["pressed"]:
                if state["pid"] is not None:
                    self._scrcpy_manager.send_normalized_touch(1, state["ex"], state["ey"], pointer_id=state["pid"])
                    state["pid"] = None
            else:
                cx = dpad.get("x", 0.5)
                cy = dpad.get("y", 0.5)
                radius = dpad.get("size", 0.06)
                new_edge = self._resolve_edge(
                    state["pressed"], key_to_dir, cx, cy, radius,
                    self._scrcpy_manager._last_session[0] if self._scrcpy_manager._last_session else None,
                    self._scrcpy_manager._last_session[1] if self._scrcpy_manager._last_session else None
                )
                if new_edge is not None and state["pid"] is not None:
                    self._scrcpy_manager.send_normalized_touch(2, new_edge[0], new_edge[1], pointer_id=state["pid"])
                    state["ex"], state["ey"] = new_edge

            return True

        return False

    def has_mleft_key_configured(self) -> bool:
        """Check if any control is configured with MLeft key."""
        if not self._active_mapping:
            return False

        for ctrl in self._active_mapping.get("controls", []):
            if ctrl.get("key") == "MLeft":
                return True

        for swp in self._active_mapping.get("swipes", []):
            if swp.get("key") == "MLeft":
                return True

        for dpad in self._active_mapping.get("dpad", []):
            for _, info in dpad.get("keys", {}).items():
                if info.get("key") == "MLeft":
                    return True

        for cam in self._active_mapping.get("camera", []):
            if cam.get("key") == "MLeft":
                return True

        return False
