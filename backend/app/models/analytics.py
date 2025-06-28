from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class StreamAnalytics(Base):
    __tablename__ = "stream_analytics"

    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False)

    # Viewer metrics
    concurrent_viewers = Column(Integer, default=0)
    peak_viewers = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    unique_viewers = Column(Integer, default=0)

    # Engagement metrics
    chat_messages = Column(Integer, default=0)
    emoji_reactions = Column(Integer, default=0)
    average_watch_time = Column(Float, default=0.0)  # in seconds

    # Quality metrics
    quality_switches = Column(Integer, default=0)
    buffer_events = Column(Integer, default=0)
    error_rate = Column(Float, default=0.0)

    # CDN metrics
    cdn_distribution = Column(JSON, nullable=True)  # CDN usage stats
    geographic_data = Column(JSON, nullable=True)  # viewer locations

    # Performance metrics
    startup_time = Column(Float, nullable=True)  # average startup time
    bitrate_stats = Column(JSON, nullable=True)  # bitrate usage distribution

    # Timestamps
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stream = relationship("Stream", back_populates="analytics")

class ViewerSession(Base):
    __tablename__ = "viewer_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Session identification
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False)

    # Session details
    ip_address = Column(String(45), nullable=True)  # supports IPv6
    user_agent = Column(String(500), nullable=True)
    country = Column(String(2), nullable=True)  # ISO country code
    city = Column(String(100), nullable=True)

    # Viewing metrics
    join_time = Column(DateTime(timezone=True), server_default=func.now())
    leave_time = Column(DateTime(timezone=True), nullable=True)
    watch_duration = Column(Float, default=0.0)  # in seconds

    # Quality metrics
    selected_quality = Column(String(20), nullable=True)
    cdn_server = Column(String(20), nullable=True)
    buffer_count = Column(Integer, default=0)

    # Interaction metrics
    chat_messages_sent = Column(Integer, default=0)
    reactions_sent = Column(Integer, default=0)
