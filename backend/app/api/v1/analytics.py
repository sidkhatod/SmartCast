from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()

@router.get("/platform")
async def get_platform_analytics(db: Session = Depends(get_db)):
    """Get platform-wide analytics"""
    # In production, this would query actual analytics tables
    return {
        "total_streams": 1234,
        "live_streams": 56,
        "total_users": 8921,
        "hours_watched": 45200,
        "total_messages": 125000
    }

@router.get("/stream/{stream_id}")
async def get_detailed_stream_analytics(stream_id: str, db: Session = Depends(get_db)):
    """Get detailed analytics for a specific stream"""
    return {
        "stream_id": stream_id,
        "views": 5432,
        "unique_viewers": 3210,
        "average_watch_time": 1245,
        "peak_viewers": 890,
        "chat_messages": 2567,
        "quality_distribution": {
            "1080p": 45,
            "720p": 35,
            "480p": 20
        },
        "geographic_distribution": {
            "US": 60,
            "EU": 25,
            "Asia": 15
        }
    }
