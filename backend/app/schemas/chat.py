from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatMessageBase(BaseModel):
    content: str
    message_type: str = "text"
    video_timestamp: Optional[float] = None

class ChatMessageCreate(ChatMessageBase):
    chat_room_id: int

class ChatMessageResponse(ChatMessageBase):
    id: int
    username: str
    user_id: Optional[int] = None
    chat_room_id: int
    is_deleted: bool
    is_highlighted: bool
    created_at: datetime
    reactions: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True

class MessageReactionCreate(BaseModel):
    emoji: str
    message_id: int

class MessageReactionResponse(BaseModel):
    id: int
    emoji: str
    user_id: int
    message_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ChatRoomResponse(BaseModel):
    id: int
    stream_id: int
    is_active: bool
    is_moderated: bool
    max_message_length: int
    created_at: datetime

    class Config:
        from_attributes = True

class WebSocketMessage(BaseModel):
    type: str  # message, reaction, join, leave, system
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[int] = None
    username: Optional[str] = None
