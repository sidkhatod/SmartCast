from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class StreamBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: bool = True

class StreamCreate(StreamBase):
    pass

class StreamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None

class LiveStreamCreate(StreamBase):
    """Schema for creating a live RTMP stream"""
    pass

class StreamResponse(StreamBase):
    id: int
    stream_id: str
    status: str
    is_live: bool
    video_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    hls_url: Optional[str] = None
    rtmp_url: Optional[str] = None
    viewer_count: int
    total_views: int
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    user_id: int

    class Config:
        from_attributes = True

class StreamWithUser(StreamResponse):
    username: str
    user_avatar: Optional[str] = None

class LiveStreamResponse(StreamResponse):
    stream_key: str
    rtmp_url: str

class StreamAnalyticsResponse(BaseModel):
    stream_id: str
    concurrent_viewers: int
    peak_viewers: int
    total_views: int
    chat_messages: int
    average_watch_time: float
    quality_distribution: Dict[str, int]
    cdn_distribution: Dict[str, int]
    geographic_data: Dict[str, Any]

class QualityInfo(BaseModel):
    resolution: str
    bitrate: int
    fps: int
    playlist_url: str

class CDNInfo(BaseModel):
    server_id: str
    latency: float
    load_percentage: float
    is_available: bool
