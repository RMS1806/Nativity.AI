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
from datetime import datetime

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

router = APIRouter(prefix="/api/video", tags=["Video Localization"])

# In-memory job storage (replace with Redis/DB in production)
jobs: dict[str, LocalizationJob] = {}

# Store analysis results for jobs (would be DB in production)
job_results: dict[str, dict] = {}


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
    
    Complete pipeline runs in background:
    1. Download video from S3
    2. Analyze with Gemini (transcript, translation, cultural adaptation)
    3. Generate TTS audio
    4. Stitch with FFmpeg
    5. Upload result to S3
    
    Returns job_id immediately. Poll /api/video/job/{job_id} for status.
    """
    job_id = str(uuid.uuid4())
    user_id = user.get("sub")
    
    job = LocalizationJob(
        job_id=job_id,
        status=JobStatus.PENDING,
        progress=0,
        message="Job created, starting full localization...",
        input_file=request.file_key,
        target_language=request.target_language.value
    )
    jobs[job_id] = job
    
    # Add background processing task for FULL pipeline
    background_tasks.add_task(
        process_localization_job,
        job_id,
        request.file_key,
        request.target_language.value,
        user_id
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Localization started. Poll /api/video/job/{job_id} for status."
    }


async def process_draft_creation(
    job_id: str,
    file_key: str,
    target_language: str,
    user_id: Optional[str] = None
):
    """
    Background task for Phase 1: Create translation draft.
    Downloads video, analyzes with Gemini, returns segments for human review.
    Does NOT run TTS or video dubbing.
    """
    job = jobs.get(job_id)
    if not job:
        return
    
    temp_dir = None
    
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix=f"nativity_draft_{job_id[:8]}_")
        local_video_path = os.path.join(temp_dir, "input_video.mp4")
        
        # ═══════════════════════════════════════════
        # STEP 1: Download from S3
        # ═══════════════════════════════════════════
        job.status = JobStatus.UPLOADING
        job.progress = 10
        job.message = "📥 Downloading video from S3..."
        
        download_result = s3_service.download_file(file_key, local_video_path)
        if "error" in download_result:
            raise Exception(f"Download failed: {download_result['error']}")
        
        job.progress = 25
        job.message = "✅ Video downloaded, starting AI analysis..."
        
        # ═══════════════════════════════════════════
        # STEP 2: Generate Translation Draft with Gemini
        # ═══════════════════════════════════════════
        job.status = JobStatus.ANALYZING
        job.progress = 30
        job.message = "🧠 Gemini is analyzing and translating your video..."
        
        draft_result = await gemini_service.generate_translation_draft(
            video_path=local_video_path,
            target_language=target_language
        )
        
        if "error" in draft_result:
            raise Exception(f"Analysis failed: {draft_result['error']}")
        
        segments = draft_result.get("segments", [])
        job.progress = 90
        job.message = f"✅ Found {len(segments)} segments. Ready for review!"
        
        # Store draft results
        job_results[job_id] = {
            "draft": draft_result,
            "segments": segments,
            "cultural_analysis": draft_result.get("cultural_analysis", []),
            "video_title": draft_result.get("video_title", ""),
            "target_language": target_language,
            "_full_analysis": draft_result.get("_full_analysis", {})
        }
        
        # ═══════════════════════════════════════════
        # PHASE 1 COMPLETE - Ready for human review
        # ═══════════════════════════════════════════
        job.status = JobStatus.COMPLETE  # Frontend will check for segments to know it's a draft
        job.progress = 100
        job.message = "📝 Draft ready! Review and edit translations before finalizing."
        
        # Save to DynamoDB with NEEDS_REVIEW status
        if user_id:
            db_service.save_video(
                user_id=user_id,
                job_id=job_id,
                target_language=target_language,
                input_file=file_key,
                status="needs_review",
                draft_segments=segments,
                cultural_report=draft_result.get("cultural_analysis"),
                segments_count=len(segments)
            )
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"❌ Analysis failed: {str(e)}"
    
    finally:
        # Cleanup temp files
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


@router.post("/finalize")
async def finalize_dubbing(
    request: dict,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Phase 2: Finalize dubbing with approved/edited segments.
    
    Input: { "job_id": "...", "approved_segments": [...] }
    
    This endpoint:
    1. Takes user-edited segments
    2. Generates TTS audio for each segment
    3. Stitches audio with original video
    4. Uploads to S3
    5. Sets status to COMPLETE
    """
    job_id = request.get("job_id")
    approved_segments = request.get("approved_segments", [])
    
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    
    if not approved_segments:
        raise HTTPException(status_code=400, detail="approved_segments is required")
    
    user_id = user.get("sub")
    
    # Get original job data
    original_job = jobs.get(job_id)
    if not original_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check FFmpeg availability
    if not ffmpeg_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="FFmpeg not installed. Please install FFmpeg to process videos."
        )
    
    # Update job status
    original_job.status = JobStatus.PENDING
    original_job.progress = 0
    original_job.message = "Starting final dubbing with your edits..."
    
    # Update segments in DynamoDB
    if user_id:
        db_service.update_job_segments(
            user_id=user_id,
            job_id=job_id,
            segments=approved_segments,
            status="processing"
        )
    
    # Add background task for Phase 2
    background_tasks.add_task(
        process_finalize_dubbing,
        job_id,
        original_job.input_file,
        original_job.target_language,
        approved_segments,
        user_id
    )
    
    return {
        "job_id": job_id,
        "status": "finalizing",
        "message": "Dubbing started with your approved segments. Poll /api/video/job/{job_id} for status."
    }


async def process_finalize_dubbing(
    job_id: str,
    file_key: str,
    target_language: str,
    approved_segments: list,
    user_id: Optional[str] = None
):
    """
    Background task for Phase 2: Generate TTS and stitch video.
    Uses the user-approved/edited segments.
    """
    job = jobs.get(job_id)
    if not job:
        return
    
    temp_dir = None
    tts_temp_service = None
    
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix=f"nativity_final_{job_id[:8]}_")
        local_video_path = os.path.join(temp_dir, "input_video.mp4")
        output_video_path = os.path.join(temp_dir, "output_localized.mp4")
        whatsapp_video_path = os.path.join(temp_dir, "output_whatsapp.mp4")
        
        # ═══════════════════════════════════════════
        # STEP 1: Download from S3
        # ═══════════════════════════════════════════
        job.status = JobStatus.UPLOADING
        job.progress = 5
        job.message = "📥 Downloading video from S3..."
        
        download_result = s3_service.download_file(file_key, local_video_path)
        if "error" in download_result:
            raise Exception(f"Download failed: {download_result['error']}")
        
        job.progress = 15
        job.message = "✅ Video downloaded, generating audio..."
        
        # ═══════════════════════════════════════════
        # STEP 2: Generate TTS Audio from Approved Segments
        # ═══════════════════════════════════════════
        job.status = JobStatus.GENERATING_AUDIO
        job.progress = 20
        job.message = "🎙️ Generating localized voice audio from your edits..."
        
        # Create TTS service with temp directory
        tts_temp_service = TTSService(output_dir=os.path.join(temp_dir, "audio_segments"))
        
        # Convert approved segments to the format TTS service expects
        tts_segments = []
        for seg in approved_segments:
            tts_segments.append({
                "start_time": seg.get("start", 0),
                "end_time": seg.get("end", 0),
                "translated_text": seg.get("translated_text", ""),
                "original_text": seg.get("original_text", "")
            })
        
        # Generate audio for each segment
        audio_segments = await tts_temp_service.generate_segments_from_analysis(
            segments=tts_segments,
            language=target_language,
            gender="female"  # Default to female voice
        )
        
        job.progress = 50
        job.message = f"✅ Generated {len(audio_segments)} audio segments"
        
        # ═══════════════════════════════════════════
        # STEP 3: Stitch Video with FFmpeg
        # ═══════════════════════════════════════════
        job.status = JobStatus.STITCHING
        job.progress = 55
        job.message = "🎬 Stitching new audio with video..."
        
        # Convert audio segments to dict format for FFmpeg
        audio_segment_dicts = [
            {
                "file_path": seg.file_path,
                "start_time": seg.start_time,
                "end_time": seg.end_time
            }
            for seg in audio_segments
        ]
        
        # Calculate TTS delay from first approved segment start time
        tts_delay = 0.0
        if approved_segments:
            # Safely get start time of first segment
            first_seg = approved_segments[0]
            tts_delay = first_seg.get("start", 0.0)
            
        # Stitch video
        stitch_result = ffmpeg_service.stitch_video(
            original_video_path=local_video_path,
            audio_segments=audio_segment_dicts,
            output_path=output_video_path,
            optimize_for_mobile=True,
            tts_delay_seconds=tts_delay
        )
        
        if not stitch_result.success:
            raise Exception(f"Video stitching failed: {stitch_result.error}")
        
        job.progress = 80
        job.message = f"✅ Video stitched! Size: {stitch_result.file_size_mb:.1f}MB"
        
        # Create WhatsApp version if needed
        whatsapp_result = None
        if stitch_result.file_size_mb > 15:
            job.message = "📱 Creating WhatsApp-optimized version..."
            whatsapp_result = ffmpeg_service.create_whatsapp_version(
                input_path=output_video_path,
                output_path=whatsapp_video_path,
                target_size_mb=14.5
            )
        
        # ═══════════════════════════════════════════
        # STEP 4: Upload to S3
        # ═══════════════════════════════════════════
        job.progress = 90
        job.message = "☁️ Uploading localized video to S3..."
        
        output_key = f"outputs/{job_id}/localized_{target_language}.mp4"
        
        upload_result = s3_service.upload_file(output_video_path, output_key)
        if "error" in upload_result:
            raise Exception(f"Upload failed: {upload_result['error']}")
        
        # Upload WhatsApp version if created
        whatsapp_url = None
        if whatsapp_result and whatsapp_result.success:
            whatsapp_key = f"outputs/{job_id}/whatsapp_{target_language}.mp4"
            whatsapp_upload = s3_service.upload_file(whatsapp_video_path, whatsapp_key)
            if whatsapp_upload.get("success"):
                whatsapp_download = s3_service.generate_presigned_download_url(whatsapp_key)
                whatsapp_url = whatsapp_download.get("download_url")
        
        # Get download URL
        download_result = s3_service.generate_presigned_download_url(output_key)
        
        # ═══════════════════════════════════════════
        # COMPLETE!
        # ═══════════════════════════════════════════
        job.status = JobStatus.COMPLETE
        job.progress = 100
        job.output_file = output_key
        job.message = "🎉 Localization complete! Your video is ready."
        
        # Update job results
        if job_id in job_results:
            job_results[job_id].update({
                "output_url": download_result.get("download_url"),
                "whatsapp_url": whatsapp_url,
                "file_size_mb": stitch_result.file_size_mb
            })
        
        # ═══════════════════════════════════════════
        # STEP 4.5: Generate & Upload WebVTT Subtitles
        # ═══════════════════════════════════════════
        subtitle_s3_key = None
        try:
            def format_vtt_time(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = seconds % 60
                return f"{h:02d}:{m:02d}:{s:06.3f}"

            def parse_timestamp(val):
                """Convert MM:SS or HH:MM:SS strings OR numeric values to float seconds."""
                if isinstance(val, (int, float)):
                    return float(val)
                parts = str(val).strip().split(":")
                parts = [float(p) for p in parts]
                if len(parts) == 2:   # MM:SS
                    return parts[0] * 60 + parts[1]
                if len(parts) == 3:   # HH:MM:SS
                    return parts[0] * 3600 + parts[1] * 60 + parts[2]
                return 0.0

            vtt_lines = ["WEBVTT", ""]
            for idx, seg in enumerate(approved_segments):
                start_sec = parse_timestamp(seg.get("start", 0))
                end_sec   = parse_timestamp(seg.get("end",   0))
                text      = seg.get("translated_text", "").strip()
                if not text:
                    continue
                vtt_lines.append(str(idx + 1))
                vtt_lines.append(f"{format_vtt_time(start_sec)} --> {format_vtt_time(end_sec)}")
                vtt_lines.append(text)
                vtt_lines.append("")

            vtt_content  = "\n".join(vtt_lines)
            vtt_tmp_path = os.path.join(temp_dir, f"{job_id}.vtt")
            with open(vtt_tmp_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)

            subtitle_s3_key = f"subtitles/{job_id}.vtt"
            s3_service.upload_file(vtt_tmp_path, subtitle_s3_key)
        except Exception as vtt_err:
            print(f"[VTT] Non-fatal: could not generate subtitles: {vtt_err}")

        # Update DynamoDB with completion
        if user_id:
            db_service.update_job_status(
                user_id=user_id,
                job_id=job_id,
                status="complete",
                output_url=download_result.get("download_url"),
                output_s3_key=output_key,  # store raw key so /history can regenerate fresh URLs
                subtitle_s3_key=subtitle_s3_key,
                approved_segments=approved_segments  # persist translated text for metadata generation
            )
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"❌ Processing failed: {str(e)}"
        
        if user_id:
            db_service.update_job_status(
                user_id=user_id,
                job_id=job_id,
                status="failed"
            )
    
    finally:
        # Cleanup temp files
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


# Keep original full pipeline for backwards compatibility (legacy)
async def process_localization_job(
    job_id: str,
    file_key: str,
    target_language: str,
    user_id: Optional[str] = None
):
    """
    Background task to process video localization
    
    Full pipeline:
    1. Download from S3
    2. Analyze with Gemini
    3. Generate TTS audio
    4. Stitch with FFmpeg
    5. Upload to S3
    """
    job = jobs.get(job_id)
    if not job:
        return
    
    temp_dir = None
    tts_temp_service = None
    
    try:
        # Create temp directory for all processing
        temp_dir = tempfile.mkdtemp(prefix=f"nativity_{job_id[:8]}_")
        local_video_path = os.path.join(temp_dir, "input_video.mp4")
        output_video_path = os.path.join(temp_dir, "output_localized.mp4")
        whatsapp_video_path = os.path.join(temp_dir, "output_whatsapp.mp4")
        
        # ═══════════════════════════════════════════
        # STEP 1: Download from S3
        # ═══════════════════════════════════════════
        job.status = JobStatus.UPLOADING
        job.progress = 5
        job.message = "📥 Downloading video from S3..."
        
        download_result = s3_service.download_file(file_key, local_video_path)
        if "error" in download_result:
            raise Exception(f"Download failed: {download_result['error']}")
        
        job.progress = 15
        job.message = "✅ Video downloaded successfully"
        
        # ═══════════════════════════════════════════
        # STEP 2: Analyze with Gemini
        # ═══════════════════════════════════════════
        job.status = JobStatus.ANALYZING
        job.progress = 20
        job.message = "🧠 Gemini is watching and understanding your video..."
        
        analysis_result = await gemini_service.analyze_video(
            video_path=local_video_path,
            target_language=target_language
        )
        
        if "error" in analysis_result:
            raise Exception(f"Analysis failed: {analysis_result['error']}")
        
        segments = analysis_result.get('segments', [])
        cultural_report = analysis_result.get('cultural_report', {})
        
        job.progress = 40
        job.message = f"✅ Analysis complete! Found {len(segments)} segments. Idioms adapted: {cultural_report.get('idioms_adapted', 0)}"
        
        # Store analysis for later retrieval
        job_results[job_id] = {
            "analysis": analysis_result,
            "segments_count": len(segments)
        }
        
        # ═══════════════════════════════════════════
        # STEP 3: Generate TTS Audio
        # ═══════════════════════════════════════════
        job.status = JobStatus.GENERATING_AUDIO
        job.progress = 45
        job.message = "🎙️ Generating localized voice audio..."
        
        # Create TTS service with temp directory
        tts_temp_service = TTSService(output_dir=os.path.join(temp_dir, "audio_segments"))
        
        # Determine voice gender from TTS instructions
        tts_instructions = analysis_result.get('tts_instructions', {})
        voice_gender = tts_instructions.get('recommended_voice_gender', 'female')
        if voice_gender == 'mixed':
            voice_gender = 'female'  # Default to female for mixed
        
        # Generate audio for each segment
        audio_segments = await tts_temp_service.generate_segments_from_analysis(
            segments=segments,
            language=target_language,
            gender=voice_gender
        )
        
        job.progress = 65
        job.message = f"✅ Generated {len(audio_segments)} audio segments"
        
        # ═══════════════════════════════════════════
        # STEP 4: Stitch Video with FFmpeg
        # ═══════════════════════════════════════════
        job.status = JobStatus.STITCHING
        job.progress = 70
        job.message = "🎬 Stitching new audio with video..."
        
        # Convert audio segments to dict format for FFmpeg
        audio_segment_dicts = [
            {
                "file_path": seg.file_path,
                "start_time": seg.start_time,
                "end_time": seg.end_time
            }
            for seg in audio_segments
        ]
        
        # Get first speech offset from Gemini analysis
        video_metadata = analysis_result.get("video_metadata", {})
        tts_delay = video_metadata.get("first_speech_offset_seconds", 0.0)
        
        # Stitch video with optimized settings
        stitch_result = ffmpeg_service.stitch_video(
            original_video_path=local_video_path,
            audio_segments=audio_segment_dicts,
            output_path=output_video_path,
            optimize_for_mobile=True,
            tts_delay_seconds=tts_delay
        )
        
        if not stitch_result.success:
            raise Exception(f"Video stitching failed: {stitch_result.error}")
        
        job.progress = 85
        job.message = f"✅ Video stitched! Size: {stitch_result.file_size_mb:.1f}MB"
        
        # ═══════════════════════════════════════════
        # STEP 4.5: Create WhatsApp Version (Optional)
        # ═══════════════════════════════════════════
        whatsapp_result = None
        if stitch_result.file_size_mb > 15:
            job.message = "📱 Creating WhatsApp-optimized version (<15MB)..."
            whatsapp_result = ffmpeg_service.create_whatsapp_version(
                input_path=output_video_path,
                output_path=whatsapp_video_path,
                target_size_mb=14.5
            )
        
        # ═══════════════════════════════════════════
        # STEP 5: Upload to S3
        # ═══════════════════════════════════════════
        job.progress = 90
        job.message = "☁️ Uploading localized video to S3..."
        
        # Generate output S3 keys
        output_key = f"outputs/{job_id}/localized_{target_language}.mp4"
        
        upload_result = s3_service.upload_file(output_video_path, output_key)
        if "error" in upload_result:
            raise Exception(f"Upload failed: {upload_result['error']}")
        
        # Upload WhatsApp version if created
        whatsapp_url = None
        if whatsapp_result and whatsapp_result.success:
            whatsapp_key = f"outputs/{job_id}/whatsapp_{target_language}.mp4"
            whatsapp_upload = s3_service.upload_file(whatsapp_video_path, whatsapp_key)
            if whatsapp_upload.get("success"):
                whatsapp_download = s3_service.generate_presigned_download_url(whatsapp_key)
                whatsapp_url = whatsapp_download.get("download_url")
        
        # Get download URL
        download_result = s3_service.generate_presigned_download_url(output_key)
        
        # ═══════════════════════════════════════════
        # COMPLETE!
        # ═══════════════════════════════════════════
        job.status = JobStatus.COMPLETE
        job.progress = 100
        job.output_file = output_key
        job.message = "🎉 Localization complete! Your video is ready."
        
        # Store final results
        job_results[job_id].update({
            "output_url": download_result.get("download_url"),
            "whatsapp_url": whatsapp_url,
            "file_size_mb": stitch_result.file_size_mb,
            "cultural_report": cultural_report
        })
        
        # ═══════════════════════════════════════════
        # STEP 5.5: Generate & Upload WebVTT Subtitles
        # ═══════════════════════════════════════════
        subtitle_s3_key = None
        try:
            def format_vtt_time(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = seconds % 60
                return f"{h:02d}:{m:02d}:{s:06.3f}"

            vtt_lines = ["WEBVTT", ""]
            for idx, seg in enumerate(segments):
                start_sec = seg.get("start_time", 0)
                end_sec   = seg.get("end_time",   0)
                text      = seg.get("translated_text", "").strip()
                if not text:
                    continue
                vtt_lines.append(str(idx + 1))
                vtt_lines.append(f"{format_vtt_time(float(start_sec))} --> {format_vtt_time(float(end_sec))}")
                vtt_lines.append(text)
                vtt_lines.append("")

            vtt_content  = "\n".join(vtt_lines)
            vtt_tmp_path = os.path.join(temp_dir, f"{job_id}.vtt")
            with open(vtt_tmp_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)

            subtitle_s3_key = f"subtitles/{job_id}.vtt"
            s3_service.upload_file(vtt_tmp_path, subtitle_s3_key)
        except Exception as vtt_err:
            print(f"[VTT] Non-fatal: could not generate subtitles: {vtt_err}")

        # Calculate words localized from all segments
        words_localized = sum(
            len(seg.get("translated_text", "").split())
            for seg in segments
        )

        # Save to DynamoDB for persistent history
        if user_id:
            db_service.save_video(
                user_id=user_id,
                job_id=job_id,
                target_language=target_language,
                input_file=file_key,
                status="complete",
                output_url=download_result.get("download_url"),
                output_s3_key=output_key,  # store raw key so /history can regenerate fresh URLs
                whatsapp_url=whatsapp_url,
                file_size_mb=stitch_result.file_size_mb,
                cultural_report=cultural_report,
                segments_count=len(segments),
                draft_segments=segments,  # persist translated text for metadata generation
                subtitle_s3_key=subtitle_s3_key,
                words_localized=words_localized
            )
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"❌ Processing failed: {str(e)}"
    
    finally:
        # Cleanup temp files
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass  # Best effort cleanup


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a localization job
    Frontend polls this endpoint to show progress
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = job.dict()
    
    # Include results if job is complete
    if job.status == JobStatus.COMPLETE and job_id in job_results:
        response["results"] = job_results[job_id]
    
    return response


@router.get("/job/{job_id}/analysis")
async def get_job_analysis(job_id: str):
    """
    Get the detailed Gemini analysis for a completed job
    """
    if job_id not in job_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return job_results[job_id].get("analysis", {})


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
    print(f"\n{'='*60}")
    print(f"[METADATA] Request: job_id={job_id}, user_id={user_id}")

    # ── Step 1: Resolve target_language and translated_text ──────────────────
    translated_text = None
    target_language = "hindi"

    # Path A: in-memory job_results (freshly processed job, same server session)
    print(f"[METADATA] Checking in-memory job_results... key present: {job_id in job_results}")
    if job_id in job_results:
        result_data = job_results[job_id]
        segments = result_data.get("segments") or []
        target_language = result_data.get("target_language", "hindi")
        print(f"[METADATA] In-memory: found {len(segments)} segments, lang={target_language}")
        if segments:
            translated_text = " ".join(
                seg.get("translated_text", "") for seg in segments
            ).strip()
            print(f"[METADATA] In-memory translated_text length: {len(translated_text)}")

    # Path B: DynamoDB fallback
    if not translated_text:
        print(f"[METADATA] No translated_text from memory. Querying DynamoDB...")
        if not user_id:
            print("[METADATA] ERROR: user_id is None — cannot query DynamoDB")
        else:
            import json as _json
            raw_item = db_service.get_video_by_job_id(user_id, job_id)
            print(f"[METADATA] DynamoDB item found: {raw_item is not None}")
            if raw_item:
                target_language = raw_item.get("target_language", "hindi")
                raw_segments_json = raw_item.get("draft_segments")
                print(f"[METADATA] target_language={target_language}")
                print(f"[METADATA] draft_segments present: {raw_segments_json is not None}")
                if raw_segments_json:
                    try:
                        db_segments = _json.loads(raw_segments_json)
                        print(f"[METADATA] Parsed {len(db_segments)} segments from DynamoDB")
                        if db_segments:
                            # Log first segment keys so we can see the structure
                            print(f"[METADATA] First segment keys: {list(db_segments[0].keys())}")
                            print(f"[METADATA] First segment translated_text: {repr(db_segments[0].get('translated_text', 'KEY MISSING'))[:120]}")
                        translated_text = " ".join(
                            seg.get("translated_text", "") for seg in db_segments
                        ).strip()
                        print(f"[METADATA] Extracted translated_text length: {len(translated_text)}")
                    except Exception as parse_err:
                        print(f"[METADATA] ERROR parsing draft_segments JSON: {parse_err}")
                        translated_text = None
                else:
                    print("[METADATA] draft_segments field is empty/null in DynamoDB item")
            else:
                print("[METADATA] DynamoDB returned no item for this job_id")

    # ── Step 2: Guard – transcript must exist ────────────────────────────────
    print(f"[METADATA] Final translated_text: {'FOUND (len=' + str(len(translated_text)) + ')' if translated_text else 'MISSING — will 400'}")
    if not translated_text:
        raise HTTPException(
            status_code=400,
            detail="Transcript not available for this video. Please ensure the job has been finalized."
        )

    # ── Step 3: Validate job status (only for in-memory jobs) ────────────────
    job = jobs.get(job_id)
    if job and job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Job is not yet complete")

    if not gemini_service.is_configured():
        raise HTTPException(status_code=503, detail="Gemini API not configured")

    # ── Step 4: Generate transcript-grounded metadata ────────────────────────
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
    
    # Delete from DynamoDB
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
    
    # Optionally: Delete S3 files (commented out for now - can enable if needed)
    # try:
    #     output_key = f"outputs/{job_id}/"
    #     s3_service.delete_folder(output_key)
    # except Exception as e:
    #     print(f"Warning: Failed to delete S3 files for {job_id}: {e}")
    
    return {
        "success": True,
        "message": f"Video {job_id} deleted successfully"
    }
