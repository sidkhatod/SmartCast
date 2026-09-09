from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), unique=True, nullable=False)

    # Room settings
    is_active = Column(Boolean, default=True)
    is_moderated = Column(Boolean, default=False)
    max_message_length = Column(Integer, default=500)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stream = relationship("Stream", back_populates="chat_room")
    messages = relationship("ChatMessage", back_populates="chat_room")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, emoji, system

    # User information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable for anonymous users
    username = Column(String(50), nullable=False)  # stored for display

    # Chat room
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)

    # Video synchronization
    video_timestamp = Column(Float, nullable=True)  # timestamp in video (seconds)

    # Message metadata
    is_deleted = Column(Boolean, default=False)
    is_highlighted = Column(Boolean, default=False)
    msg_metadata = Column("metadata", JSON, nullable=True)  # for reactions, mentions, etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="chat_messages")
    chat_room = relationship("ChatRoom", back_populates="messages")
    reactions = relationship("MessageReaction", back_populates="message")

class MessageReaction(Base):
    __tablename__ = "message_reactions"

    id = Column(Integer, primary_key=True, index=True)

    # Reaction details
    emoji = Column(String(10), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("ChatMessage", back_populates="reactions")
