import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import WebSocket

logger = logging.getLogger("pivaani.events")

class ConnectionManager:
    """Manages active WebSocket client connections for real-time soundbox and demo telemetry."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, event_type: str, payload: Dict[str, Any]):
        """
        Broadcasts structured telemetry event to all connected dashboard and soundbox clients.
        """
        message = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        }
        encoded = json.dumps(message)
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(encoded)
            except Exception as e:
                logger.warning(f"Failed to send to client ({e}); marking for removal.")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

# Global singleton connection manager
manager = ConnectionManager()

async def broadcast(event_type: str, payload: Dict[str, Any]):
    """Global broadcast utility for services and background tasks"""
    await manager.broadcast(event_type, payload)

