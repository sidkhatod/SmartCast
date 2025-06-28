from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.stream import Stream, StreamQuality
from app.models.chat import ChatRoom
from app.schemas.stream import StreamCreate, LiveStreamCreate
from typing import List, Optional
import uuid
import os
from datetime import datetime

class StreamService:
    @staticmethod
    def get_streams(db: Session, skip: int = 0, limit: int = 100, 
                   category: str = None, is_live: bool = None) -> List[Stream]:
        query = db.query(Stream)

        if category:
            query = query.filter(Stream.category == category)

        if is_live is not None:
            query = query.filter(Stream.is_live == is_live)

        return query.filter(Stream.is_public == True).offset(skip).limit(limit).all()

    @staticmethod
    def get_stream_by_id(db: Session, stream_id: str) -> Optional[Stream]:
        return db.query(Stream).filter(Stream.stream_id == stream_id).first()

    @staticmethod
    def create_stream(db: Session, user_id: int, stream_data: StreamCreate) -> Stream:
        stream_id = str(uuid.uuid4())

        db_stream = Stream(
            stream_id=stream_id,
            title=stream_data.title,
            description=stream_data.description,
            category=stream_data.category,
            tags=stream_data.tags,
            is_public=stream_data.is_public,
            user_id=user_id,
            status="created"
        )

        db.add(db_stream)
        db.commit()
        db.refresh(db_stream)

        # Create chat room for the stream
        chat_room = ChatRoom(stream_id=db_stream.id)
        db.add(chat_room)
        db.commit()

        return db_stream

    @staticmethod
    def create_live_stream(db: Session, user_id: int, stream_data: LiveStreamCreate) -> Stream:
        stream_id = str(uuid.uuid4())
        stream_key = str(uuid.uuid4())

        db_stream = Stream(
            stream_id=stream_id,
            title=stream_data.title,
            description=stream_data.description,
            category=stream_data.category,
            tags=stream_data.tags,
            is_public=stream_data.is_public,
            user_id=user_id,
            status="live",
            is_live=True,
            stream_key=stream_key,
            rtmp_url=f"rtmp://localhost:1935/live/{stream_key}",
            started_at=datetime.utcnow()
        )

        db.add(db_stream)
        db.commit()
        db.refresh(db_stream)

        # Create chat room
        chat_room = ChatRoom(stream_id=db_stream.id)
        db.add(chat_room)
        db.commit()

        return db_stream

    @staticmethod
    def update_stream_status(db: Session, stream_id: str, status: str, **kwargs):
        stream = StreamService.get_stream_by_id(db, stream_id)
        if stream:
            stream.status = status
            for key, value in kwargs.items():
                if hasattr(stream, key):
                    setattr(stream, key, value)
            db.commit()
            return stream
        return None

    @staticmethod
    def get_stream_analytics(db: Session, stream_id: str):
        stream = StreamService.get_stream_by_id(db, stream_id)
        if not stream:
            return None

        # Basic analytics - in production this would query analytics tables
        return {
            "stream_id": stream_id,
            "concurrent_viewers": stream.viewer_count,
            "total_views": stream.total_views,
            "status": stream.status,
            "duration": stream.duration,
            "created_at": stream.created_at,
            "started_at": stream.started_at,
            "ended_at": stream.ended_at
        }
