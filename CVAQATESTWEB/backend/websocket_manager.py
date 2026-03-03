"""
WebSocket manager for real-time communication with frontend
"""
import json
import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for live updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_log(self, level: str, message: str, data: dict = None):
        """Send a log message to frontend."""
        payload = {
            "type": "log",
            "level": level,
            "message": message,
            "data": data or {},
        }
        await self.broadcast(payload)

    async def send_chat_message(self, sender: str, message: str,
                                 test_id: str = "", screenshot: str = ""):
        """Send a chat message update to frontend."""
        payload = {
            "type": "chat",
            "sender": sender,
            "message": message,
            "test_id": test_id,
            "screenshot": screenshot,
        }
        await self.broadcast(payload)

    async def send_test_result(self, test_id: str, test_name: str,
                                category: str, status: str,
                                details: str = "", error: str = ""):
        """Send test result to frontend."""
        payload = {
            "type": "test_result",
            "test_id": test_id,
            "test_name": test_name,
            "category": category,
            "status": status,
            "details": details,
            "error": error,
        }
        await self.broadcast(payload)

    async def send_progress(self, current: int, total: int,
                             current_test: str = ""):
        """Send progress update to frontend."""
        payload = {
            "type": "progress",
            "current": current,
            "total": total,
            "current_test": current_test,
            "percentage": round((current / total) * 100, 1) if total > 0 else 0,
        }
        await self.broadcast(payload)

    async def send_status(self, status: str, message: str = ""):
        """Send overall status update."""
        payload = {
            "type": "status",
            "status": status,
            "message": message,
        }
        await self.broadcast(payload)


# Global instance
ws_manager = ConnectionManager()
