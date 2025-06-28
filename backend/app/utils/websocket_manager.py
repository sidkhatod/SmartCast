import json
import asyncio
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import redis
from app.core.config import settings

class ConnectionManager:
    def __init__(self):
        # Active WebSocket connections per stream
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # User information per connection
        self.connection_info: Dict[WebSocket, Dict] = {}
        # Redis client for pub/sub
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def connect(self, websocket: WebSocket, stream_id: str, user_id: int = None, username: str = "Anonymous"):
        """Connect a client to a stream chat"""
        await websocket.accept()

        # Add to active connections
        if stream_id not in self.active_connections:
            self.active_connections[stream_id] = set()
        self.active_connections[stream_id].add(websocket)

        # Store connection info
        self.connection_info[websocket] = {
            "stream_id": stream_id,
            "user_id": user_id,
            "username": username,
            "connected_at": datetime.utcnow()
        }

        # Notify others about new user
        await self.broadcast_to_stream(stream_id, {
            "type": "user_joined",
            "username": username,
            "timestamp": datetime.utcnow().isoformat(),
            "viewer_count": len(self.active_connections[stream_id])
        })

    def disconnect(self, websocket: WebSocket):
        """Disconnect a client"""
        if websocket in self.connection_info:
            info = self.connection_info[websocket]
            stream_id = info["stream_id"]
            username = info["username"]

            # Remove from active connections
            if stream_id in self.active_connections:
                self.active_connections[stream_id].discard(websocket)

                # Clean up empty stream rooms
                if not self.active_connections[stream_id]:
                    del self.active_connections[stream_id]

            # Remove connection info
            del self.connection_info[websocket]

            # Notify others about user leaving
            if stream_id in self.active_connections:
                asyncio.create_task(self.broadcast_to_stream(stream_id, {
                    "type": "user_left",
                    "username": username,
                    "timestamp": datetime.utcnow().isoformat(),
                    "viewer_count": len(self.active_connections[stream_id])
                }))

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_text(json.dumps(message))
        except:
            self.disconnect(websocket)

    async def broadcast_to_stream(self, stream_id: str, message: dict):
        """Broadcast message to all clients in a stream"""
        if stream_id not in self.active_connections:
            return

        message_text = json.dumps(message)
        disconnected = []

        for websocket in self.active_connections[stream_id].copy():
            try:
                await websocket.send_text(message_text)
            except:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)

    async def handle_message(self, websocket: WebSocket, data: dict):
        """Handle incoming WebSocket message"""
        if websocket not in self.connection_info:
            return

        info = self.connection_info[websocket]
        stream_id = info["stream_id"]
        username = info["username"]

        message_type = data.get("type", "message")

        if message_type == "chat_message":
            # Broadcast chat message
            await self.broadcast_to_stream(stream_id, {
                "type": "chat_message",
                "content": data.get("content", ""),
                "username": username,
                "user_id": info.get("user_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "video_timestamp": data.get("video_timestamp")
            })

        elif message_type == "emoji_reaction":
            # Broadcast emoji reaction
            await self.broadcast_to_stream(stream_id, {
                "type": "emoji_reaction",
                "emoji": data.get("emoji", "👍"),
                "username": username,
                "user_id": info.get("user_id"),
                "timestamp": datetime.utcnow().isoformat()
            })

        elif message_type == "typing":
            # Broadcast typing indicator
            await self.broadcast_to_stream(stream_id, {
                "type": "typing",
                "username": username,
                "is_typing": data.get("is_typing", False),
                "timestamp": datetime.utcnow().isoformat()
            })

    def get_stream_viewer_count(self, stream_id: str) -> int:
        """Get current viewer count for a stream"""
        return len(self.active_connections.get(stream_id, set()))

# Global WebSocket manager instance
websocket_manager = ConnectionManager()

class WebSocketManager:
    """Main WebSocket manager for the application"""

    def __init__(self):
        self.manager = websocket_manager

    async def connect(self, websocket: WebSocket, stream_id: str):
        """Connect client to stream chat"""
        await self.manager.connect(websocket, stream_id)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle the message
                await self.manager.handle_message(websocket, message_data)

        except WebSocketDisconnect:
            self.manager.disconnect(websocket)
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.manager.disconnect(websocket)
