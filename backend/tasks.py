"""
Celery tasks for Nativity.ai video processing.

Two tasks:
  - process_video_localization  — full pipeline (download → Gemini → TTS → FFmpeg → R2)
  - process_draft_creation      — analysis only (download → Gemini)

Disk strategy (Render free tier has limited ephemeral disk):
  - If R2_PUBLIC_URL is set: pass the public URL to Gemini directly — no local
    download needed for the analysis step. Input video is only written to disk
    right before FFmpeg needs it, then deleted immediately after stitching.
  - Without R2_PUBLIC_URL: classic flow — download once, reuse for both Gemini
    upload and FFmpeg.
  - Stale temp directories (left by crashed jobs) are swept at the start of
    every task so disk doesn't accumulate across jobs.
"""

import asyncio
import glob
import tempfile
import shutil
import os
import time as _time

from celery_app import celery_app
from config import settings
from services.job_service import job_service
from services.gemini_service import gemini_service
from services.s3_service import s3_service
from services.tts_service import TTSService
from services.ffmpeg_service import ffmpeg_service
from models import JobStatus


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _cleanup_stale_temp_dirs(max_age_seconds: int = 7200):
    """
    Delete /tmp/nativity_* directories older than max_age_seconds.
    Called at the start of each task so disk freed by the finally-block of a
    crashed job (which may not have run) is recovered before the next job starts.
    """
    cutoff = _time.time() - max_age_seconds
    for stale in glob.glob("/tmp/nativity_*"):
        try:
            if os.path.isdir(stale) and os.path.getmtime(stale) < cutoff:
                shutil.rmtree(stale, ignore_errors=True)
                print(f"[Cleanup] Removed stale temp dir: {stale}")
        except Exception as e:
            print(f"[Cleanup] Warning sweeping {stale}: {e}")


def _r2_public_url(file_key: str) -> str | None:
    """Return a public R2 URL for file_key, or None if R2_PUBLIC_URL is not set."""
    base = (settings.R2_PUBLIC_URL or "").rstrip("/")
    return f"{base}/{file_key}" if base else None


# ──────────────────────────────────────────────────────────────────────────────
# Full localization task
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.process_video_localization",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=900,   # 15 min soft
    time_limit=1200,       # 20 min hard
)
def process_video_localization(self, job_id: str, user_id: str, file_key: str, target_language: str):
    """
    Full video localization pipeline:
      1. Gemini analysis  (URL path: no download; Files API path: download first)
      2. TTS audio generation
      3. Download to disk for FFmpeg (if URL path was used)
      4. FFmpeg stitch
      5. Free input + audio from disk early
      6. Upload output to R2
      7. Mark job complete in PostgreSQL
    """
    print(f"[Celery] Starting full localization: job_id={job_id}")
    _cleanup_stale_temp_dirs()

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"nativity_{job_id[:8]}_")
        local_video_path = os.path.join(temp_dir, "input_video.mp4")
        output_video_path = os.path.join(temp_dir, "output_localized.mp4")
        whatsapp_video_path = os.path.join(temp_dir, "output_whatsapp.mp4")

        public_url = _r2_public_url(file_key)

        # ── Step 1: Gemini analysis ───────────────────────────────────────────
        job_service.update_job_status(
            job_id=job_id, status=JobStatus.ANALYZING,
            progress=15, message="🧠 Gemini is analyzing your video...", user_id=user_id
        )

        if public_url:
            # URL path — Gemini fetches the video; input_video is NOT on disk yet.
            print(f"[Task] Using R2 public URL for Gemini (saves disk during analysis)")
            analysis_result = asyncio.run(
                gemini_service.analyze_video(video_url=public_url, target_language=target_language)
            )
            if "error" in analysis_result:
                # URL path failed (e.g. Gemini couldn't reach R2) — fall back to download.
                print(f"[Task] URL path failed ({analysis_result['error']}), falling back to download")
                job_service.update_job_status(
                    job_id=job_id, status=JobStatus.UPLOADING,
                    progress=10, message="📥 Downloading video from storage...", user_id=user_id
                )
                dl = s3_service.download_file(file_key, local_video_path)
                if "error" in dl:
                    raise Exception(f"Download failed: {dl['error']}")
                analysis_result = asyncio.run(
                    gemini_service.analyze_video(video_path=local_video_path, target_language=target_language)
                )
        else:
            # Classic path — download first, then upload to Gemini Files API.
            job_service.update_job_status(
                job_id=job_id, status=JobStatus.UPLOADING,
                progress=10, message="📥 Downloading video from storage...", user_id=user_id
            )
            dl = s3_service.download_file(file_key, local_video_path)
            if "error" in dl:
                raise Exception(f"Download failed: {dl['error']}")
            job_service.update_job_status(
                job_id=job_id, status=JobStatus.ANALYZING,
                progress=20, message="🧠 Uploading to Gemini for analysis...", user_id=user_id
            )
            analysis_result = asyncio.run(
                gemini_service.analyze_video(video_path=local_video_path, target_language=target_language)
            )

        if "error" in analysis_result:
            raise Exception(f"Analysis failed: {analysis_result['error']}")

        segments = analysis_result.get("segments", [])
        cultural_report = analysis_result.get("cultural_report", {})

        job_service.update_job_status(
            job_id=job_id, progress=45,
            message=f"✅ Analysis complete! Found {len(segments)} segments", user_id=user_id
        )

        # ── Step 2: TTS audio generation ─────────────────────────────────────
        job_service.update_job_status(
            job_id=job_id, status=JobStatus.GENERATING_AUDIO,
            progress=50, message="🎙️ Generating localized voice audio...", user_id=user_id
        )

        tts_temp_service = TTSService(output_dir=os.path.join(temp_dir, "audio_segments"))
        tts_instructions = analysis_result.get("tts_instructions", {})
        voice_gender = tts_instructions.get("recommended_voice_gender", "female")
        if voice_gender == "mixed":
            voice_gender = "female"

        audio_segments = asyncio.run(
            tts_temp_service.generate_segments_from_analysis(
                segments=segments,
                language=target_language,
                gender=voice_gender
            )
        )

        job_service.update_job_status(
            job_id=job_id, progress=70,
            message=f"✅ Generated {len(audio_segments)} audio segments", user_id=user_id
        )

        # ── Step 3: Ensure input video is on disk for FFmpeg ─────────────────
        # If we used the URL path, the video was never downloaded — do it now.
        if not os.path.exists(local_video_path):
            job_service.update_job_status(
                job_id=job_id, message="📥 Downloading video for FFmpeg...", user_id=user_id
            )
            dl = s3_service.download_file(file_key, local_video_path)
            if "error" in dl:
                raise Exception(f"Download for FFmpeg failed: {dl['error']}")

        # ── Step 4: FFmpeg stitch ─────────────────────────────────────────────
        job_service.update_job_status(
            job_id=job_id, status=JobStatus.STITCHING,
            progress=75, message="🎬 Stitching new audio with video...", user_id=user_id
        )

        audio_segment_dicts = [
            {"file_path": seg.file_path, "start_time": seg.start_time, "end_time": seg.end_time}
            for seg in audio_segments
        ]

        video_metadata = analysis_result.get("video_metadata", {})
        tts_delay = video_metadata.get("first_speech_offset_seconds", 0.0)

        stitch_result = ffmpeg_service.stitch_video(
            original_video_path=local_video_path,
            audio_segments=audio_segment_dicts,
            output_path=output_video_path,
            optimize_for_mobile=True,
            tts_delay_seconds=tts_delay
        )

        if not stitch_result.success:
            raise Exception(f"Video stitching failed: {stitch_result.error}")

        job_service.update_job_status(
            job_id=job_id, progress=85,
            message=f"✅ Video stitched! Size: {stitch_result.file_size_mb:.1f}MB", user_id=user_id
        )

        # ── Step 5: Free input + audio early — output upload is next ─────────
        # Deleting these now frees disk before the (possibly slow) R2 upload.
        try:
            os.remove(local_video_path)
        except Exception:
            pass
        try:
            shutil.rmtree(os.path.join(temp_dir, "audio_segments"), ignore_errors=True)
        except Exception:
            pass

        # ── Step 6: WhatsApp version (optional) ──────────────────────────────
        whatsapp_url = None
        if stitch_result.file_size_mb > 15:
            job_service.update_job_status(
                job_id=job_id, message="📱 Creating WhatsApp-optimized version...", user_id=user_id
            )
            whatsapp_result = ffmpeg_service.create_whatsapp_version(
                input_path=output_video_path,
                output_path=whatsapp_video_path,
                target_size_mb=14.5
            )
            if whatsapp_result and whatsapp_result.success:
                whatsapp_key = f"outputs/{job_id}/whatsapp_{target_language}.mp4"
                wa_upload = s3_service.upload_file(whatsapp_video_path, whatsapp_key)
                if wa_upload.get("success"):
                    wa_dl = s3_service.generate_presigned_download_url(whatsapp_key)
                    whatsapp_url = wa_dl.get("download_url")
                try:
                    os.remove(whatsapp_video_path)
                except Exception:
                    pass

        # ── Step 7: Upload output to R2 ───────────────────────────────────────
        job_service.update_job_status(
            job_id=job_id, progress=90,
            message="☁️ Uploading localized video to storage...", user_id=user_id
        )

        output_key = f"outputs/{job_id}/localized_{target_language}.mp4"
        upload_result = s3_service.upload_file(output_video_path, output_key)
        if "error" in upload_result:
            raise Exception(f"Upload failed: {upload_result['error']}")

        # ── Step 8: Generate subtitle VTT and upload ──────────────────────────
        subtitle_s3_key = None
        try:
            subtitle_s3_key = _generate_and_upload_vtt(
                segments=segments,
                job_id=job_id,
                temp_dir=temp_dir,
                parse_key="translated_text",
                start_key="start_time",
                end_key="end_time",
            )
        except Exception as vtt_err:
            print(f"[VTT] Non-fatal: {vtt_err}")

        download_result = s3_service.generate_presigned_download_url(output_key)

        results = {
            "analysis": analysis_result,
            "segments": segments,
            "cultural_report": cultural_report,
            "cultural_analysis": analysis_result.get("cultural_analysis", []),
            "segments_count": len(segments),
            "file_size_mb": stitch_result.file_size_mb,
            "words_localized": sum(len(seg.get("translated_text", "").split()) for seg in segments),
            "subtitle_s3_key": subtitle_s3_key,
        }

        job_service.complete_job(
            job_id=job_id,
            user_id=user_id,
            output_url=download_result.get("download_url"),
            output_s3_key=output_key,
            results=results,
            whatsapp_url=whatsapp_url,
            file_size_mb=stitch_result.file_size_mb,
        )

        print(f"[Celery] Job {job_id} completed successfully")
        return {"status": "complete", "job_id": job_id}

    except Exception as exc:
        print(f"[Celery] Job {job_id} failed: {exc}")
        job_service.fail_job(job_id, user_id, str(exc))
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc

    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[Cleanup] Warning: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Draft creation task (analysis only — no TTS / FFmpeg)
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.process_draft_creation",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=600,
    time_limit=900,
)
def process_draft_creation(self, job_id: str, user_id: str, file_key: str, target_language: str):
    """
    Phase 1 only: Gemini analysis → draft segments for human review.
    No TTS or FFmpeg. Uses URL path when R2_PUBLIC_URL is available so the
    video is never written to Render's disk at all for this task.
    """
    print(f"[Celery] Starting draft creation: job_id={job_id}")
    _cleanup_stale_temp_dirs()

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"nativity_draft_{job_id[:8]}_")
        local_video_path = os.path.join(temp_dir, "input_video.mp4")
        public_url = _r2_public_url(file_key)

        job_service.update_job_status(
            job_id=job_id, status=JobStatus.ANALYZING,
            progress=15, message="🧠 Gemini is analyzing and translating...", user_id=user_id
        )

        if public_url:
            print(f"[Task] Draft: using R2 public URL for Gemini")
            draft_result = asyncio.run(
                gemini_service.generate_translation_draft(
                    video_url=public_url,
                    target_language=target_language
                )
            )
            if "error" in draft_result:
                # Fall back to download
                print(f"[Task] Draft URL path failed, falling back to download")
                job_service.update_job_status(
                    job_id=job_id, status=JobStatus.UPLOADING,
                    progress=10, message="📥 Downloading video for analysis...", user_id=user_id
                )
                dl = s3_service.download_file(file_key, local_video_path)
                if "error" in dl:
                    raise Exception(f"Download failed: {dl['error']}")
                draft_result = asyncio.run(
                    gemini_service.generate_translation_draft(
                        video_path=local_video_path,
                        target_language=target_language
                    )
                )
        else:
            job_service.update_job_status(
                job_id=job_id, status=JobStatus.UPLOADING,
                progress=10, message="📥 Downloading video for analysis...", user_id=user_id
            )
            dl = s3_service.download_file(file_key, local_video_path)
            if "error" in dl:
                raise Exception(f"Download failed: {dl['error']}")
            draft_result = asyncio.run(
                gemini_service.generate_translation_draft(
                    video_path=local_video_path,
                    target_language=target_language
                )
            )

        if "error" in draft_result:
            raise Exception(f"Analysis failed: {draft_result['error']}")

        segments = draft_result.get("segments", [])

        job_service.update_job_status(
            job_id=job_id, status=JobStatus.COMPLETE,
            progress=100,
            message=f"📝 Draft ready! {len(segments)} segments for review.",
            user_id=user_id
        )

        results = {
            "draft": draft_result,
            "segments": segments,
            "cultural_analysis": draft_result.get("cultural_analysis", []),
            "video_title": draft_result.get("video_title", ""),
            "target_language": target_language,
        }
        job_service.redis.set_job_results(job_id, results)

        print(f"[Celery] Draft job {job_id} completed")
        return {"status": "complete", "job_id": job_id}

    except Exception as exc:
        print(f"[Celery] Draft job {job_id} failed: {exc}")
        job_service.fail_job(job_id, user_id, str(exc))
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc

    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[Cleanup] Warning: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _generate_and_upload_vtt(segments, job_id, temp_dir, parse_key, start_key, end_key):
    """Generate a WebVTT subtitle file and upload it to R2. Returns the S3 key."""

    def _to_seconds(val):
        if isinstance(val, (int, float)):
            return float(val)
        parts = [float(p) for p in str(val).strip().split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0.0

    def _fmt(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"

    lines = ["WEBVTT", ""]
    for idx, seg in enumerate(segments):
        text = seg.get(parse_key, "").strip()
        if not text:
            continue
        lines.append(str(idx + 1))
        lines.append(f"{_fmt(_to_seconds(seg.get(start_key, 0)))} --> {_fmt(_to_seconds(seg.get(end_key, 0)))}")
        lines.append(text)
        lines.append("")

    vtt_path = os.path.join(temp_dir, f"{job_id}.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    key = f"subtitles/{job_id}.vtt"
    s3_service.upload_file(vtt_path, key)
    return key
