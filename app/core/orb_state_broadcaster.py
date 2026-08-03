import asyncio
from typing import Set
from loguru import logger
from fastapi import WebSocket

class OrbStateBroadcaster:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._current_state: str = 'idle'
    
    def register(self, ws: WebSocket):
        self._clients.add(ws)
        logger.debug(f"OrbState: Client registered. Total: {len(self._clients)}")
    
    def unregister(self, ws: WebSocket):
        self._clients.discard(ws)
        logger.debug(f"OrbState: Client unregistered. Total: {len(self._clients)}")
    
    async def emit(self, state: str):
        self._current_state = state
        dead = set()
        for ws in self._clients:
            try:
                await ws.send_json({"type": "orb_state", "state": state})
            except Exception:
                dead.add(ws)
        self._clients -= dead
    
    @property
    def current_state(self) -> str:
        return self._current_state

orb_broadcaster = OrbStateBroadcaster()
