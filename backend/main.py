"""
Nativity.ai - FastAPI Backend
AI-powered video localization for Bharat

"Hyper-localizing the internet for Bharat, one video at a time."
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from routes.video import router as video_router
from services.gemini_service import gemini_service
from services.s3_service import s3_service
from services.ffmpeg_service import ffmpeg_service, check_ffmpeg_installation
from services.tts_service import tts_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    import os
    print("\n" + "="*50)
    print("🇮🇳 Nativity.ai starting up...")
    print(f"   📂 CWD: {os.getcwd()}")
    print("="*50)
    print(f"   ✓ Gemini API: {'✅ Ready' if gemini_service.is_configured() else '❌ Not configured'}")
    print(f"   ✓ AWS S3:     {'✅ Ready' if s3_service.is_configured() else '❌ Not configured'}")
    print(f"   ✓ FFmpeg:     {'✅ Ready' if ffmpeg_service.is_available() else '❌ Not installed'}")
    print(f"   ✓ TTS:        ✅ Ready (edge-tts)")
    
    if not ffmpeg_service.is_available():
        print("\n   ⚠️  WARNING: FFmpeg not found!")
        print("   Video processing will not work without FFmpeg.")
        print("   Install: https://ffmpeg.org/download.html")
    
    print("="*50 + "\n")
    
    yield
    
    # Shutdown
    print("\n👋 Nativity.ai shutting down...")


app = FastAPI(
    title="Nativity.ai API",
    description="""
    ## 🇮🇳 Hyper-localizing the internet for Bharat
    
    Nativity.ai is an AI-powered media pipeline that automatically localizes 
    video content for Indian audiences using Google Gemini 3 Pro.
    
    ### Features
    - **Video Analysis**: Extract transcript, OCR, and cultural context
    - **Cultural Transcreation**: Adapt idioms and references for local audiences
    - **Multi-language Support**: Hindi, Tamil, Bengali, Telugu, Marathi
    - **Neural TTS**: Natural-sounding Indian language voices
    - **Video Processing**: FFmpeg-powered audio replacement and optimization
    - **WhatsApp Mode**: Auto-generate <15MB versions for easy sharing
    - **S3 Integration**: Scalable video storage and delivery
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # Next.js dev server
        "http://127.0.0.1:3000",
        "http://localhost:8000",    # FastAPI docs
        "*"  # Allow all for hackathon demo
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(video_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "🇮🇳 Namaste! Nativity.ai API is running.",
        "tagline": "Hyper-localizing the internet for Bharat, one video at a time.",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check for monitoring"""
    config_status = settings.validate()
    ffmpeg_status = check_ffmpeg_installation()
    
    all_services_ready = (
        gemini_service.is_configured() and
        s3_service.is_configured() and
        ffmpeg_service.is_available()
    )
    
    return {
        "status": "ok" if all_services_ready else "degraded",
        "services": {
            "api": "running",
            "gemini": "ready" if gemini_service.is_configured() else "not configured",
            "aws_s3": "ready" if s3_service.is_configured() else "not configured",
            "ffmpeg": "ready" if ffmpeg_service.is_available() else "not installed",
            "tts": "ready"  # edge-tts is always available
        },
        "ffmpeg_details": ffmpeg_status,
        "configuration": config_status,
        "supported_languages": settings.SUPPORTED_LANGUAGES
    }


@app.get("/api/config/status")
async def config_status():
    """
    Check which services are properly configured
    Useful for frontend to show setup instructions
    """
    return {
        "gemini": {
            "configured": gemini_service.is_configured(),
            "model": "gemini-2.0-flash" if gemini_service.is_configured() else None
        },
        "aws": {
            "configured": s3_service.is_configured(),
            "region": settings.AWS_REGION if s3_service.is_configured() else None,
            "bucket": settings.S3_BUCKET_NAME if s3_service.is_configured() else None
        },
        "ffmpeg": {
            "installed": ffmpeg_service.is_available(),
            "details": check_ffmpeg_installation()
        },
        "tts": {
            "configured": True,
            "engine": "edge-tts",
            "voices": ["Hindi", "Tamil", "Bengali", "Telugu", "Marathi"]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
