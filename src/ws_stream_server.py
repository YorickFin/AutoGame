import asyncio
import json
import logging
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
        self._cached_keyframe_meta: str | None = None
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

    async def send_event(
        self,
        kind: str,
        meta: dict[str, Any] | None = None,
        payload: bytes | None = None,
    ) -> None:
        """Send an event to all connected WebSocket clients.

        Args:
            kind: Event kind ("session", "video", "audio")
            meta: Optional metadata dict (will be sent as JSON text)
            payload: Optional binary payload (will be sent as binary message)
        """
        # Build metadata message
        msg: dict[str, Any] = {"kind": kind}
        if meta:
            msg.update(meta)

        text_payload = json.dumps(msg, ensure_ascii=False)

        # Cache session event for late-connecting clients (BEFORE connection check)
        if kind == "session":
            self._last_session_event = text_payload
            self._session_cached.set()
        # Cache the first keyframe for late-connecting clients
        if kind == "video" and payload is not None and (meta or {}).get("keyFrame"):
            if self._cached_keyframe_meta is None:
                self._cached_keyframe_meta = text_payload
                self._cached_keyframe_data = payload
                self._keyframe_cached.set()

        if not self._connections:
            return

        # Send to all connected clients
        dead: set[ServerConnection] = set()
        for ws in self._connections:
            try:
                await ws.send(text_payload)
                if payload is not None:
                    await ws.send(payload)
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
                await websocket.send(self._cached_keyframe_meta)
                await websocket.send(self._cached_keyframe_data)
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
