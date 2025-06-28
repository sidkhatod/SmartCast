from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import create_tables
from app.api.v1 import auth, streams, chat, upload, rtmp, analytics
from app.utils.websocket_manager import WebSocketManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket manager instance
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting SmartCast application...")
    await create_tables()
    logger.info("Database tables created/verified")

    yield

    # Shutdown
    logger.info("Shutting down SmartCast application...")

# Create FastAPI application
app = FastAPI(
    title="SmartCast API",
    description="Production-ready live streaming platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(streams.router, prefix=f"{settings.API_V1_STR}/streams", tags=["streams"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(upload.router, prefix=f"{settings.API_V1_STR}/upload", tags=["upload"])
app.include_router(rtmp.router, prefix=f"{settings.API_V1_STR}/rtmp", tags=["rtmp"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])

# Mount static files for CDN simulation
app.mount("/cdn", StaticFiles(directory="cdn"), name="cdn")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# WebSocket endpoint for chat
@app.websocket("/ws/chat/{stream_id}")
async def websocket_chat_endpoint(websocket, stream_id: str):
    await websocket_manager.connect(websocket, stream_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SmartCast API"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "SmartCast Streaming Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# RTMP callback endpoints for nginx-rtmp
@app.post("/rtmp/on_publish")
async def rtmp_on_publish(name: str, addr: str, clientid: str, call: str):
    """Called when RTMP stream starts"""
    logger.info(f"RTMP stream started: {name} from {addr}")
    # Validate stream key and start processing
    return JSONResponse(content={"status": "success"})

@app.post("/rtmp/on_publish_done")
async def rtmp_on_publish_done(name: str, addr: str, clientid: str, call: str):
    """Called when RTMP stream ends"""
    logger.info(f"RTMP stream ended: {name} from {addr}")
    # Trigger VOD processing
    return JSONResponse(content={"status": "success"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
