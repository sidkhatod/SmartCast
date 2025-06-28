from sqlalchemy.orm import Session
from app.models.chat import ChatRoom, ChatMessage, MessageReaction
from app.schemas.chat import ChatMessageCreate, MessageReactionCreate
from typing import List, Optional

class ChatService:
    @staticmethod
    def get_chat_room_by_stream_id(db: Session, stream_id: int) -> Optional[ChatRoom]:
        return db.query(ChatRoom).filter(ChatRoom.stream_id == stream_id).first()

    @staticmethod
    def create_chat_message(db: Session, message_data: ChatMessageCreate, 
                           user_id: int = None, username: str = "Anonymous") -> ChatMessage:
        db_message = ChatMessage(
            content=message_data.content,
            message_type=message_data.message_type,
            video_timestamp=message_data.video_timestamp,
            user_id=user_id,
            username=username,
            chat_room_id=message_data.chat_room_id
        )

        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message

    @staticmethod
    def get_chat_messages(db: Session, chat_room_id: int, 
                         skip: int = 0, limit: int = 100) -> List[ChatMessage]:
        return (db.query(ChatMessage)
                .filter(and_(
                    ChatMessage.chat_room_id == chat_room_id,
                    ChatMessage.is_deleted == False
                ))
                .order_by(ChatMessage.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all())

    @staticmethod
    def add_reaction(db: Session, reaction_data: MessageReactionCreate, 
                    user_id: int) -> MessageReaction:
        # Check if user already reacted with this emoji
        existing = (db.query(MessageReaction)
                   .filter(and_(
                       MessageReaction.message_id == reaction_data.message_id,
                       MessageReaction.user_id == user_id,
                       MessageReaction.emoji == reaction_data.emoji
                   ))
                   .first())

        if existing:
            # Remove existing reaction
            db.delete(existing)
            db.commit()
            return None

        # Add new reaction
        db_reaction = MessageReaction(
            emoji=reaction_data.emoji,
            user_id=user_id,
            message_id=reaction_data.message_id
        )

        db.add(db_reaction)
        db.commit()
        db.refresh(db_reaction)
        return db_reaction

    @staticmethod
    def delete_message(db: Session, message_id: int, user_id: int) -> bool:
        message = (db.query(ChatMessage)
                  .filter(and_(
                      ChatMessage.id == message_id,
                      ChatMessage.user_id == user_id
                  ))
                  .first())

        if message:
            message.is_deleted = True
            db.commit()
            return True

        return False
