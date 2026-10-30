import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
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
            # Unique per broadcast so clients can drop a frame they already handled
            "event_id": uuid.uuid4().hex,
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

# In-memory event bus: API handlers and the case engine publish, one dispatcher
# fans out to WebSocket clients, so slow clients never block a payment request
# and every client sees events in publish order.
_event_bus: Optional[asyncio.Queue] = None
_dispatcher_task: Optional[asyncio.Task] = None

def _bus() -> asyncio.Queue:
    global _event_bus
    if _event_bus is None:
        _event_bus = asyncio.Queue()
    return _event_bus

async def _dispatch_events():
    bus = _bus()
    while True:
        event_type, payload = await bus.get()
        try:
            await manager.broadcast(event_type, payload)
        except Exception as e:
            logger.error(f"Event dispatch failed for {event_type}: {e}")
        finally:
            bus.task_done()

def start_event_dispatcher():
    global _dispatcher_task
    if _dispatcher_task is None or _dispatcher_task.done():
        _dispatcher_task = asyncio.create_task(_dispatch_events())

def stop_event_dispatcher():
    global _dispatcher_task
    if _dispatcher_task and not _dispatcher_task.done():
        _dispatcher_task.cancel()
    _dispatcher_task = None

async def broadcast(event_type: str, payload: Dict[str, Any]):
    """Publishes an event onto the bus; the dispatcher delivers it to all clients"""
    await _bus().put((event_type, payload))

