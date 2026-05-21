import asyncio
import json
import logging
import struct
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection


logger = logging.getLogger(__name__)


class WsStreamServer:
    """WebSocket server that pushes scrcpy video/audio frames as binary streams.

    Protocol (JSON text + binary alternating):
      1. Server -> Client text:   {"kind":"session","width":1080,"height":2400,"codec":"h264"}
      2. Server -> Client text:   {"kind":"video","pts":123456,"keyFrame":true,"config":false}
      3. Server -> Client binary: raw H.264 NAL units (annexb format)
      4. Server -> Client text:   {"kind":"audio","pts":789012}
      5. Server -> Client binary: raw PCM 16-bit LE stereo 48000Hz
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._last_session_event: str | None = None
        self._session_cached: asyncio.Event = asyncio.Event()
        self._cached_keyframe_meta: bytes | None = None
        self._cached_keyframe_data: bytes | None = None
        self._keyframe_cached: asyncio.Event = asyncio.Event()
        self._server: Any = None
        self._port: int = 0
        self._connections: set[ServerConnection] = set()

    @property
    def port(self) -> int:
        return self._port

    @property
    def connected(self) -> bool:
        return len(self._connections) > 0

    async def start(self) -> int:
        """Start the WebSocket server on a random port. Returns the port number."""
        self._server = await websockets.serve(
            self._handler,
            host="127.0.0.1",
            port=0,
            max_size=2**24,  # 16 MB max message
        )
        self._port = self._server.sockets[0].getsockname()[1]
        logger.info("WebSocket stream server started on port %d", self._port)
        return self._port

    async def stop(self) -> None:
        """Stop the WebSocket server and close all connections."""
        for ws in set(self._connections):
            try:
                await ws.close(code=1001, reason="Server shutting down")
            except Exception:
                pass
        self._connections.clear()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("WebSocket stream server stopped")

    def _build_binary_header(self, kind: str, meta: dict[str, Any] | None) -> bytes:
        """Build a 9-byte binary header from metadata.

        Format: [1B flags][8B pts LE]
          flags bit 0: keyFrame
          flags bit 1: is_audio (0=video, 1=audio)
          flags bit 2: config
        """
        flags = 0
        pts = 0
        if meta:
            if meta.get("keyFrame"):
                flags |= 0x01
            if kind == "audio":
                flags |= 0x02
            if meta.get("config"):
                flags |= 0x04
            pts = meta.get("pts") or 0
        return struct.pack("<Bq", flags, pts)

    async def send_event(
        self,
        kind: str,
        meta: dict[str, Any] | None = None,
        payload: bytes | None = None,
    ) -> None:
        """Send an event to all connected WebSocket clients.

        Session events: sent as JSON text (one-time metadata).
        Video/audio events: sent as single binary message: [9B header][payload].
        """
        msg: dict[str, Any] = {"kind": kind}
        if meta:
            msg.update(meta)

        text_payload = json.dumps(msg, ensure_ascii=False)

        # Cache session event for late-connecting clients
        if kind == "session":
            self._last_session_event = text_payload
            self._session_cached.set()
        # Cache the first keyframe for late-connecting clients
        if kind == "video" and payload is not None and (meta or {}).get("keyFrame"):
            if self._cached_keyframe_meta is None:
                header = self._build_binary_header(kind, meta)
                self._cached_keyframe_meta = header
                self._cached_keyframe_data = payload
                self._keyframe_cached.set()

        if not self._connections:
            return

        dead: set[ServerConnection] = set()
        for ws in self._connections:
            try:
                if kind == "session":
                    # Session: JSON text (one-time)
                    await ws.send(text_payload)
                else:
                    # Video/audio: single binary message = header + payload
                    header = self._build_binary_header(kind, meta)
                    if payload is not None:
                        await ws.send(header + payload)
                    else:
                        await ws.send(header)
            except Exception:
                dead.add(ws)

        self._connections -= dead

    async def _handler(self, websocket: ServerConnection) -> None:
        """Handle a new WebSocket client connection."""
        self._connections.add(websocket)
        logger.info("WebSocket client connected (total: %d)", len(self._connections))
        # Wait for session event to arrive (up to 10s) then replay
        try:
            await asyncio.wait_for(self._session_cached.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for session event")
        # Also wait for first keyframe
        try:
            await asyncio.wait_for(self._keyframe_cached.wait(), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for first keyframe")
        # Replay last session event so client gets session metadata
        if self._last_session_event is not None:
            try:
                await websocket.send(self._last_session_event)
            except Exception:
                pass
        if self._cached_keyframe_meta is not None and self._cached_keyframe_data is not None:
            try:
                await websocket.send(self._cached_keyframe_meta + self._cached_keyframe_data)
            except Exception:
                pass
        try:
            # Keep connection alive and handle incoming control messages
            async for _message in websocket:
                # We don't expect client messages currently
                pass
        except Exception:
            pass
        finally:
            self._connections.discard(websocket)
            logger.info(
                "WebSocket client disconnected (remaining: %d)",
                len(self._connections),
            )
