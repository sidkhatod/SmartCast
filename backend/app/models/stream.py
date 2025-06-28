from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid

class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(String(50), unique=True, index=True, default=lambda: str(uuid.uuid4()))

    # Stream metadata
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)

    # Stream status
    status = Column(String(20), default="created")  # created, processing, live, ended, archived
    is_live = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)

    # File information
    video_path = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    duration = Column(Float, nullable=True)  # in seconds

    # HLS information
    hls_url = Column(String(500), nullable=True)
    master_playlist = Column(String(500), nullable=True)

    # RTMP information
    rtmp_url = Column(String(500), nullable=True)
    stream_key = Column(String(100), nullable=True)

    # Analytics
    viewer_count = Column(Integer, default=0)
    total_views = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="streams")
    chat_room = relationship("ChatRoom", back_populates="stream", uselist=False)
    analytics = relationship("StreamAnalytics", back_populates="stream")

class StreamQuality(Base):
    __tablename__ = "stream_qualities"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False)

    # Quality settings
    resolution = Column(String(20), nullable=False)  # 480p, 720p, 1080p
    bitrate = Column(Integer, nullable=False)  # in kbps
    fps = Column(Integer, default=30)
    codec = Column(String(20), default="h264")

    # File paths
    playlist_url = Column(String(500), nullable=False)
    segment_pattern = Column(String(500), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
