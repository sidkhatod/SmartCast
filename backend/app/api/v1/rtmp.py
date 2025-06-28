from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.stream_service import StreamService
from app.schemas.stream import LiveStreamCreate, LiveStreamResponse
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/start", response_model=LiveStreamResponse)
async def start_live_stream(
    stream_data: LiveStreamCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a live RTMP stream"""
    if not current_user.is_streamer:
        raise HTTPException(
            status_code=403,
            detail="Only streamers can start live streams"
        )

    # Create live stream
    live_stream = StreamService.create_live_stream(
        db=db,
        user_id=current_user.id,
        stream_data=stream_data
    )

    return LiveStreamResponse(
        **live_stream.__dict__,
        stream_key=live_stream.stream_key,
        rtmp_url=live_stream.rtmp_url
    )

@router.post("/{stream_id}/stop")
async def stop_live_stream(
    stream_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop a live RTMP stream"""
    stream = StreamService.get_stream_by_id(db, stream_id)

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update stream status
    from datetime import datetime
    StreamService.update_stream_status(
        db, stream_id, 
        status="ended", 
        is_live=False, 
        ended_at=datetime.utcnow()
    )

    return {"message": "Stream stopped successfully"}

@router.get("/{stream_id}/status")
async def get_stream_status(stream_id: str, db: Session = Depends(get_db)):
    """Get live stream status"""
    stream = StreamService.get_stream_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    return {
        "stream_id": stream_id,
        "status": stream.status,
        "is_live": stream.is_live,
        "viewer_count": stream.viewer_count,
        "started_at": stream.started_at,
        "title": stream.title
    }

@router.get("/")
async def list_live_streams(db: Session = Depends(get_db)):
    """List all currently live streams"""
    streams = StreamService.get_streams(db, is_live=True, limit=50)
    return [
        {
            "stream_id": stream.stream_id,
            "title": stream.title,
            "username": stream.user.username,
            "viewer_count": stream.viewer_count,
            "category": stream.category,
            "thumbnail_url": stream.thumbnail_url
        }
        for stream in streams
    ]
