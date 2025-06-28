from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.chat_service import ChatService
from app.schemas.chat import ChatMessageResponse, ChatMessageCreate, MessageReactionCreate
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/{stream_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    stream_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get chat messages for a stream"""
    # Get chat room by stream ID (simplified - in production, validate stream exists)
    messages = ChatService.get_chat_messages(db, int(stream_id), skip, limit)
    return messages

@router.post("/{stream_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    stream_id: str,
    message_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a chat message"""
    # Create message data
    message_create = ChatMessageCreate(
        content=message_data["content"],
        message_type=message_data.get("message_type", "text"),
        video_timestamp=message_data.get("video_timestamp"),
        chat_room_id=int(stream_id)  # Simplified mapping
    )

    message = ChatService.create_chat_message(
        db=db,
        message_data=message_create,
        user_id=current_user.id,
        username=current_user.username
    )

    return message

@router.post("/messages/{message_id}/reactions")
async def add_message_reaction(
    message_id: int,
    reaction_data: MessageReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add or remove reaction to a message"""
    reaction = ChatService.add_reaction(
        db=db,
        reaction_data=reaction_data,
        user_id=current_user.id
    )

    if reaction:
        return {"status": "added", "reaction": reaction}
    else:
        return {"status": "removed"}

@router.delete("/messages/{message_id}")
async def delete_chat_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat message"""
    success = ChatService.delete_message(db, message_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Message not found or access denied")

    return {"status": "deleted"}
