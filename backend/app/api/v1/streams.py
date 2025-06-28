from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.stream_service import StreamService
from app.schemas.stream import StreamResponse, StreamCreate, StreamWithUser, LiveStreamCreate, LiveStreamResponse
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[StreamWithUser])
async def list_streams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = None,
    is_live: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all streams with pagination and filtering"""
    streams = StreamService.get_streams(
        db=db,
        skip=skip,
        limit=limit,
        category=category,
        is_live=is_live
    )

    # Add user information
    result = []
    for stream in streams:
        stream_dict = stream.__dict__.copy()
        stream_dict["username"] = stream.user.username
        stream_dict["user_avatar"] = stream.user.avatar_url
        result.append(stream_dict)

    return result

@router.get("/{stream_id}", response_model=StreamResponse)
async def get_stream(stream_id: str, db: Session = Depends(get_db)):
    """Get stream by ID"""
    stream = StreamService.get_stream_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

@router.post("/", response_model=StreamResponse)
async def create_stream(
    stream_data: StreamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new stream"""
    if not current_user.is_streamer:
        raise HTTPException(
            status_code=403,
            detail="Only streamers can create streams"
        )

    stream = StreamService.create_stream(
        db=db,
        user_id=current_user.id,
        stream_data=stream_data
    )
    return stream

@router.get("/{stream_id}/analytics")
async def get_stream_analytics(
    stream_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get stream analytics (owner only)"""
    stream = StreamService.get_stream_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    analytics = StreamService.get_stream_analytics(db, stream_id)
    return analytics

@router.put("/{stream_id}")
async def update_stream(
    stream_id: str,
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update stream information"""
    stream = StreamService.get_stream_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated_stream = StreamService.update_stream_status(db, stream_id, **updates)
    return updated_stream
