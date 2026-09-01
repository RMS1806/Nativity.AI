"""
Video Localization API Routes
Handles upload, processing, and delivery endpoints

Full Pipeline: Upload → Gemini Analysis → TTS Generation → FFmpeg Stitching → S3 Delivery
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import uuid
import os
import shutil
import tempfile
from typing import Optional
from datetime import datetime, timezone

from models import (
    VideoUploadRequest,
    VideoUploadResponse,
    LocalizationRequest,
    LocalizationJob,
    JobStatus,
    QuickTranslateRequest,
    QuickTranslateResponse,
    TargetLanguage
)
from services.gemini_service import gemini_service
from services.s3_service import s3_service
from services.tts_service import tts_service, TTSService
from services.ffmpeg_service import ffmpeg_service, check_ffmpeg_installation
from config import settings
from dependencies import get_current_user, get_optional_user
from services.db_service import db_service
from services.job_service import job_service
from services.redis_service import redis_service
from services.queue_service import queue_service, JobPriority
from tasks import _run_localization, _run_draft_creation, _run_audio_localization

router = APIRouter(prefix="/api/video", tags=["Video Localization"])

_STALE_JOB_MINUTES = 12  # no progress update in 12 min = pipeline is dead


@router.post("/upload-url", response_model=VideoUploadResponse)
async def get_upload_url(request: VideoUploadRequest):
    """
    Generate a presigned URL for direct browser upload to S3
    Frontend uses this to upload video directly without going through our server
    """
    if not s3_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="S3 not configured. Please set AWS credentials."
        )

    result = s3_service.generate_presigned_upload_url(
        file_name=request.file_name,
        content_type=request.content_type
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/localize")
async def start_localization(
    request: LocalizationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Start full video localization pipeline.
    Responds instantly with job_id; processing runs in a background thread.
    Poll /api/video/job/{job_id} for real-time status.
    """
    user_id = user.get("sub")

    job = job_service.create_job(
        user_id=user_id,
        input_file=request.file_key,
        target_language=request.target_language.value
    )

    background_tasks.add_task(
        _run_localization,
        job.job_id,
        user_id,
        request.file_key,
        request.target_language.value,
    )

    return {
        "job_id": job.job_id,
        "status": "processing",
        "message": "Localization started. Poll /api/video/job/{job_id} for status."
    }


@router.post("/localize-audio")
async def start_audio_localization(
    request: LocalizationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Audio-only dub pipeline.
    Extracts audio from the uploaded video, dubs it into target_language,
    and returns a .aac file — no video encode, no length limit.
    Poll /api/video/job/{job_id} for status just like the full pipeline.
    """
    user_id = user.get("sub")

    job = job_service.create_job(
        user_id=user_id,
        input_file=request.file_key,
        target_language=request.target_language.value
    )

    background_tasks.add_task(
        _run_audio_localization,
        job.job_id,
        user_id,
        request.file_key,
        request.target_language.value,
    )

    return {
        "job_id": job.job_id,
        "status": "processing",
        "message": "Audio localization started. Poll /api/video/job/{job_id} for status."
    }


@router.post("/create-draft")
async def create_translation_draft(
    request: LocalizationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Create translation draft for human review (Phase 1 of two-phase workflow).
    Analyzes video with Gemini and returns segments for editing — no TTS or FFmpeg.
    Use /api/video/finalize after reviewing/editing segments.
    """
    user_id = user.get("sub")

    job = job_service.create_job(
        user_id=user_id,
        input_file=request.file_key,
        target_language=request.target_language.value
    )

    background_tasks.add_task(
        _run_draft_creation,
        job.job_id,
        user_id,
        request.file_key,
        request.target_language.value,
    )

    return {
        "job_id": job.job_id,
        "status": "processing",
        "message": "Draft creation started. Poll /api/video/job/{job_id} for status."
    }


@router.get("/queue/status")
async def get_queue_status():
    """
    Get queue statistics and health
    Useful for monitoring and debugging
    """
    return {
        "queue_health": queue_service.health_check(),
        "queue_stats": queue_service.get_queue_stats()
    }


@router.post("/finalize")
async def finalize_dubbing(
    request: dict,
    user: dict = Depends(get_current_user)
):
    """
    Phase 2: Finalize dubbing with approved/edited segments.

    The two-phase draft → finalize workflow is not yet wired to the Celery
    worker. This endpoint is a placeholder — return 501 so callers get a
    clear error instead of a crash.
    """
    raise HTTPException(
        status_code=501,
        detail="Two-phase finalize workflow is not yet implemented in the current worker setup. Use /localize for single-pass localization."
    )


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a localization job
    Frontend polls this endpoint to show progress
    """
    job = job_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Stale job detection: background thread may have crashed without updating Redis.
    # If a non-terminal job has had no progress update for _STALE_JOB_MINUTES, mark
    # it failed so the user doesn't wait forever for something already dead.
    if job.status not in (JobStatus.COMPLETE, JobStatus.FAILED):
        raw = redis_service.get_job_status(job_id)
        updated_at_str = (raw or {}).get("updated_at", "")
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                elapsed_min = (datetime.now(timezone.utc) - updated_at).total_seconds() / 60
                if elapsed_min > _STALE_JOB_MINUTES:
                    msg = (
                        f"Pipeline stalled — no progress update in {int(elapsed_min)} min. "
                        "The background process likely crashed. Please retry."
                    )
                    print(f"⚠️  Stale job detected: {job_id} (last update {elapsed_min:.1f} min ago)")
                    job_service.update_job_status(
                        job_id=job_id,
                        status=JobStatus.FAILED,
                        message=msg,
                        error="stale_pipeline",
                    )
                    job.status = JobStatus.FAILED
                    job.message = msg
            except Exception as e:
                print(f"Stale job check error: {e}")

    response = job.dict()

    # Include results if job is complete
    if job.status == JobStatus.COMPLETE:
        results = job_service.get_job_results(job_id)
        if results:
            response["results"] = results

    return response


@router.get("/job/{job_id}/analysis")
async def get_job_analysis(job_id: str):
    """
    Get the detailed Gemini analysis for a completed job.

    Reads from the database (the durable store). Returns the translated segments
    (for SRT download) and the cultural_analysis / cultural_report
    (for the Cultural Insights modal).
    """
    import json as _json

    raw = db_service.get_job_by_id(job_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Analysis not found")

    def _parse(field, default):
        val = raw.get(field)
        if not val:
            return default
        if isinstance(val, str):
            try:
                return _json.loads(val)
            except (_json.JSONDecodeError, TypeError):
                return default
        return val

    return {
        "segments": _parse("draft_segments", []),
        "cultural_analysis": _parse("cultural_analysis", []),
        "cultural_report": _parse("cultural_report", {}),
    }


@router.post("/metadata")
async def generate_video_metadata(
    request: dict,
    user: dict = Depends(get_current_user)
):
    """
    Generate YouTube SEO metadata for a completed localization job.
    Uses Gemini AI with the actual video transcript to create optimized
    title, description, and tags grounded in real video content.

    Request body: { "job_id": "..." }
    """
    job_id = request.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")

    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    # ── Step 1: Resolve target_language and translated_text from DB ───────────
    import json as _json
    translated_text = None
    target_language = "hindi"

    raw_item = db_service.get_video_by_job_id(user_id, job_id)
    if raw_item:
        target_language = raw_item.get("target_language", "hindi")
        raw_segments_json = raw_item.get("draft_segments")
        if raw_segments_json:
            try:
                db_segments = _json.loads(raw_segments_json)
                translated_text = " ".join(
                    seg.get("translated_text", "") for seg in db_segments
                ).strip()
            except Exception as parse_err:
                print(f"[METADATA] ERROR parsing draft_segments JSON: {parse_err}")
                translated_text = None

    # ── Step 2: Guard – transcript must exist ────────────────────────────────
    if not translated_text:
        raise HTTPException(
            status_code=400,
            detail="Transcript not available for this video. Please ensure the job has completed."
        )

    if not gemini_service.is_configured():
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    # ── Step 3: Generate transcript-grounded metadata ─────────────────────────
    print(f"[METADATA] Calling Gemini generate_metadata with lang={target_language}")
    metadata = await gemini_service.generate_metadata(
        translated_text=translated_text,
        target_language=target_language
    )

    print(f"[METADATA] Gemini returned keys: {list(metadata.keys())}")
    if "error" in metadata:
        print(f"[METADATA] Gemini returned error: {metadata['error']}")
        raise HTTPException(status_code=500, detail=metadata["error"])

    print(f"[METADATA] Success — title={repr(str(metadata.get('title',''))[:60])}")
    print(f"{'='*60}\n")
    return metadata


@router.post("/upload-direct")
async def upload_video_direct(
    file: UploadFile = File(...),
    target_language: TargetLanguage = TargetLanguage.HINDI
):
    """
    Direct video upload endpoint (for testing without S3)
    Saves file locally and processes with Gemini
    """
    if not gemini_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini API not configured. Set GOOGLE_API_KEY."
        )

    # Validate file type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a video file."
        )

    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename or "video.mp4")

    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Analyze with Gemini
        result = await gemini_service.analyze_video(
            video_path=temp_path,
            target_language=target_language.value
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@router.post("/translate", response_model=QuickTranslateResponse)
async def quick_translate(request: QuickTranslateRequest):
    """
    Quick text translation endpoint for testing Gemini integration
    No video required - just translates text with cultural adaptation
    """
    if not gemini_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini API not configured. Set GOOGLE_API_KEY."
        )

    result = await gemini_service.quick_translate(
        text=request.text,
        target_language=request.target_language.value
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/tts-test")
async def test_tts(
    text: str = "नमस्ते, नैटिविटी एआई में आपका स्वागत है।",
    language: str = "hindi",
    gender: str = "female"
):
    """
    Test TTS generation endpoint
    Returns a generated audio file info
    """
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "test_audio.mp3")

    result = await tts_service.generate_audio_segment(
        text=text,
        language=language,
        file_path=output_path,
        gender=gender
    )

    # Cleanup
    if os.path.exists(output_path):
        os.remove(output_path)
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)

    return result


@router.get("/ffmpeg-status")
async def get_ffmpeg_status():
    """
    Check FFmpeg installation status
    """
    return check_ffmpeg_installation()


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported target languages
    """
    return {
        "languages": [
            {"code": "hindi", "name": "Hindi", "native": "हिंदी"},
            {"code": "tamil", "name": "Tamil", "native": "தமிழ்"},
            {"code": "bengali", "name": "Bengali", "native": "বাংলা"},
            {"code": "telugu", "name": "Telugu", "native": "తెలుగు"},
            {"code": "marathi", "name": "Marathi", "native": "मराठी"}
        ]
    }


@router.get("/history")
async def get_user_history(
    user: dict = Depends(get_current_user),
    limit: int = 20
):
    """
    Get the authenticated user's video localization history
    Requires authentication via Clerk JWT

    Returns list of past localizations with fresh download URLs and dashboard stats
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid user token"
        )

    result = db_service.get_user_history(user_id, limit=limit)

    if "error" in result:
        raise HTTPException(
            status_code=503,
            detail=f"Database error: {result['error']}"
        )

    # Regenerate fresh presigned URLs for each video
    videos = result.get("videos", [])
    for video in videos:
        # Regenerate output URL if we have the output S3 key
        output_key = video.get("output_s3_key") or video.get("output_file")
        if output_key and s3_service.is_configured():
            fresh_url = s3_service.create_presigned_url(output_key, expiration=3600)
            if fresh_url:
                video["output_url"] = fresh_url

        # Regenerate subtitle download URL if we have the subtitle S3 key
        subtitle_key = video.get("subtitle_s3_key")
        if subtitle_key and s3_service.is_configured():
            fresh_subtitle_url = s3_service.create_presigned_url(subtitle_key, expiration=3600)
            if fresh_subtitle_url:
                video["subtitle_url"] = fresh_subtitle_url

        # Regenerate input URL if needed
        input_key = video.get("input_file") or video.get("input_s3_key")
        if input_key and s3_service.is_configured():
            fresh_input_url = s3_service.create_presigned_url(input_key, expiration=3600)
            if fresh_input_url:
                video["input_url"] = fresh_input_url

    # Calculate real dashboard stats from user's history
    total_projects = len(videos)

    # Count unique target languages
    unique_languages = set()
    for video in videos:
        lang = video.get("target_language")
        if lang:
            unique_languages.add(lang)
    languages_used = len(unique_languages)

    # Sum words localized across all completed videos
    words_localized = sum(
        video.get("words_localized") or 0
        for video in videos
        if video.get("status") == "complete"
    )

    # Add stats to response
    result["stats"] = {
        "total_projects": total_projects,
        "languages_used": languages_used,
        "words_localized": words_localized,
    }

    return result


@router.delete("/{job_id}")
async def delete_video(
    job_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Delete a video from user's history.
    Requires authentication - users can only delete their own videos.

    Args:
        job_id: The job ID to delete

    Returns:
        Success confirmation or error
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid user token"
        )

    result = db_service.delete_video(user_id, job_id)

    if "error" in result:
        if "not found" in result["error"].lower():
            raise HTTPException(
                status_code=404,
                detail="Video not found or not owned by user"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete video: {result['error']}"
        )

    return {
        "success": True,
        "message": f"Video {job_id} deleted successfully"
    }
