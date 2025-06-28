from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import os
import uuid
import aiofiles
from pathlib import Path

from app.core.database import get_db
from app.core.config import settings
from app.services.stream_service import StreamService
from app.services.video_service import VideoProcessingService
from app.schemas.upload import UploadResponse, ProcessingStatus
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter()

async def process_uploaded_video(file_path: str, stream_id: str, db_session):
    """Background task to process uploaded video"""
    try:
        # Update status to processing
        StreamService.update_stream_status(db_session, stream_id, status="processing")

        # Process video to HLS
        result = await VideoProcessingService.process_video_to_hls(file_path, stream_id)

        # Generate thumbnail
        thumbnail_dir = Path(settings.STORAGE_DIR) / "thumbnails"
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_path = thumbnail_dir / f"{stream_id}.jpg"

        await VideoProcessingService.generate_thumbnail(file_path, str(thumbnail_path))

        # Update stream with HLS URL and thumbnail
        StreamService.update_stream_status(
            db_session,
            stream_id,
            status="ready",
            hls_url=result["master_playlist"],
            thumbnail_url=f"/storage/thumbnails/{stream_id}.jpg",
            video_path=file_path
        )

    except Exception as e:
        print(f"Error processing video: {e}")
        StreamService.update_stream_status(db_session, stream_id, status="error")

@router.post("/", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("general"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload video file for processing"""
    if not current_user.is_streamer:
        raise HTTPException(status_code=403, detail="Only streamers can upload videos")

    # Validate file type
    if not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video")

    # Create stream record
    from app.schemas.stream import StreamCreate
    stream_data = StreamCreate(
        title=title,
        description=description,
        category=category,
        is_public=True
    )

    stream = StreamService.create_stream(db, current_user.id, stream_data)

    # Save uploaded file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_extension = Path(file.filename).suffix
    filename = f"{stream.stream_id}{file_extension}"
    file_path = upload_dir / filename

    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Start background processing
    background_tasks.add_task(
        process_uploaded_video,
        str(file_path),
        stream.stream_id,
        db
    )

    return UploadResponse(
        stream_id=stream.stream_id,
        filename=filename,
        file_size=len(content),
        status="uploaded",
        message="Video uploaded successfully. Processing started."
    )

@router.get("/status/{stream_id}", response_model=ProcessingStatus)
async def get_processing_status(stream_id: str, db: Session = Depends(get_db)):
    """Get video processing status"""
    stream = StreamService.get_stream_by_id(db, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    progress = 0.0
    if stream.status == "processing":
        progress = 50.0
    elif stream.status == "ready":
        progress = 100.0
    elif stream.status == "error":
        progress = 0.0

    return ProcessingStatus(
        stream_id=stream_id,
        status=stream.status,
        progress=progress,
        message=f"Status: {stream.status}",
        hls_url=stream.hls_url,
        thumbnail_url=stream.thumbnail_url,
        error=None if stream.status != "error" else "Processing failed"
    )
