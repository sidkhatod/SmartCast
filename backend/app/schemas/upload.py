from pydantic import BaseModel
from typing import Optional

class UploadResponse(BaseModel):
    stream_id: str
    filename: str
    file_size: int
    status: str
    message: str

class ProcessingStatus(BaseModel):
    stream_id: str
    status: str
    progress: float
    message: str
    hls_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error: Optional[str] = None
