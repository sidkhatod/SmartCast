from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)

    # User roles and status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_streamer = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Profile information
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    streams = relationship("Stream", back_populates="user")
    chat_messages = relationship("ChatMessage", back_populates="user")
