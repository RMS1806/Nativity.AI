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
import json as _json
import subprocess as _subprocess
import tempfile
import shutil
import os
import threading
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
# VAD-based chunking helpers (Fix 2)
# ──────────────────────────────────────────────────────────────────────────────

GEMINI_CHUNK_THRESHOLD_S = 240.0  # videos longer than this get chunked (4 min)
GEMINI_CHUNK_TARGET_S    = 240.0  # aim for ~4-min chunks


def _get_video_info_url(video_url: str) -> tuple[float, str]:
    """
    ffprobe a public URL to get duration and video codec.
    Only reads container headers — no full download.
    Returns (duration_seconds, codec_name).
    """
    try:
        r = _subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", "-select_streams", "v:0", video_url],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            data = _json.loads(r.stdout)
            duration = float(data.get("format", {}).get("duration", 0))
            codec = (data.get("streams") or [{}])[0].get("codec_name", "unknown")
            return duration, codec
    except Exception as e:
        print(f"[ffprobe] URL check failed: {e}")
    return 0.0, "unknown"


def _get_video_duration_url(video_url: str) -> float:
    duration, _ = _get_video_info_url(video_url)
    return duration


def _find_silence_cut_points(audio_path: str, target_s: float = 240.0, min_silence_s: float = 0.5) -> list:
    """
    Run ffmpeg silencedetect on a local audio file.
    Returns list of (t_start, t_end) tuples for each chunk.
    Cut points are placed at silence gaps nearest to each target_s multiple.
    Falls back to hard cuts if no silence is found near a boundary.
    """
    r = _subprocess.run(
        ["ffmpeg", "-i", audio_path,
         "-af", f"silencedetect=noise=-30dB:d={min_silence_s}",
         "-f", "null", "-"],
        capture_output=True, text=True
    )

    silence_ends = []
    for line in r.stderr.splitlines():
        if "silence_end" in line:
            try:
                ts = float(line.split("silence_end:")[1].strip().split()[0])
                silence_ends.append(ts)
            except (IndexError, ValueError):
                pass

    # Get audio duration via ffprobe
    try:
        rp = _subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
            capture_output=True, text=True, timeout=15
        )
        duration = float(_json.loads(rp.stdout).get("format", {}).get("duration", 0))
    except Exception:
        duration = 0.0

    if not duration or duration <= target_s:
        return [(0.0, duration or None)]

    # Build cut points near each target_s multiple
    cut_points = [0.0]
    t = target_s
    window = target_s * 0.3  # accept silence within ±30% of target

    while t < duration - target_s * 0.25:
        candidates = [s for s in silence_ends if abs(s - t) <= window]
        if candidates:
            cut_points.append(min(candidates, key=lambda s: abs(s - t)))
        else:
            cut_points.append(t)
        t += target_s

    cut_points.append(duration)
    return [(cut_points[i], cut_points[i + 1]) for i in range(len(cut_points) - 1)]


def _add_time_offset(timestamp: str, offset_s: float) -> str:
    """Add offset_s seconds to a 'MM:SS' or 'HH:MM:SS' timestamp string."""
    try:
        parts = [float(p) for p in str(timestamp).strip().split(":")]
        if len(parts) == 2:
            total = parts[0] * 60 + parts[1] + offset_s
        elif len(parts) == 3:
            total = parts[0] * 3600 + parts[1] * 60 + parts[2] + offset_s
        else:
            total = float(parts[0]) + offset_s
        m, s = divmod(total, 60)
        return f"{int(m):02d}:{s:05.2f}"
    except Exception:
        return timestamp


async def _analyze_video_in_chunks(video_url: str, target_language: str, temp_dir: str) -> dict:
    """
    VAD-based chunked Gemini analysis for videos longer than GEMINI_CHUNK_THRESHOLD_S.

    1. Download audio-only track for silencedetect (small, fast).
    2. Find cut points at silence gaps near every GEMINI_CHUNK_TARGET_S seconds.
    3. For each chunk: extract to disk → upload to Gemini Files API → analyze → delete.
    4. Re-index all segment timestamps to absolute positions → merge.

    Chunks use Gemini Files API (not R2) so no temp R2 storage is needed.
    """
    print(f"[VAD] Starting chunked Gemini analysis ({GEMINI_CHUNK_TARGET_S:.0f}s chunks)...")

    # Step 1: Download audio only for VAD (much smaller than full video)
    audio_path = os.path.join(temp_dir, "vad_audio.m4a")
    r = _subprocess.run(
        ["ffmpeg", "-y", "-i", video_url,
         "-vn", "-acodec", "aac", "-ar", "16000", "-ac", "1", audio_path],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0 or not os.path.exists(audio_path):
        print(f"[VAD] Audio download failed — falling back to single Gemini call")
        return await gemini_service.analyze_video(video_url=video_url, target_language=target_language)

    # Step 2: Find silence cut points
    chunks = _find_silence_cut_points(audio_path, target_s=GEMINI_CHUNK_TARGET_S)
    print(f"[VAD] {len(chunks)} chunk(s): {[(round(s, 1), round(e, 1)) for s, e in chunks]}")

    try:
        os.remove(audio_path)
    except Exception:
        pass

    if len(chunks) <= 1:
        print("[VAD] Single chunk — using direct Gemini call")
        return await gemini_service.analyze_video(video_url=video_url, target_language=target_language)

    # Step 3: Process each chunk
    all_segments = []
    all_cultural_analysis = []
    merged_result = None
    tail_context = ""

    for i, (t_start, t_end) in enumerate(chunks):
        chunk_dur = t_end - t_start
        chunk_path = os.path.join(temp_dir, f"vad_chunk_{i:04d}.mp4")

        print(f"[VAD] Chunk {i+1}/{len(chunks)}: [{t_start:.1f}s – {t_end:.1f}s] ({chunk_dur:.1f}s)")

        # Extract chunk via stream copy (no re-encode)
        r = _subprocess.run(
            ["ffmpeg", "-y",
             "-ss", str(t_start), "-t", str(chunk_dur),
             "-i", video_url, "-c", "copy", chunk_path],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0 or not os.path.exists(chunk_path):
            print(f"[VAD] Chunk {i+1} extract failed — skipping")
            continue

        # Analyze via Gemini Files API (handles upload/cleanup on Gemini's side)
        chunk_result = await gemini_service.analyze_video(
            video_path=chunk_path,
            target_language=target_language,
            continuation_context=tail_context if i > 0 else None,
        )

        # Delete local chunk immediately to free disk
        try:
            os.remove(chunk_path)
        except Exception:
            pass

        if "error" in chunk_result:
            print(f"[VAD] Chunk {i+1} analysis failed: {chunk_result['error']}")
            continue

        # Re-index timestamps to absolute positions in the full video
        for seg in chunk_result.get("segments", []):
            seg["start_time"] = _add_time_offset(seg.get("start_time", "00:00"), t_start)
            seg["end_time"]   = _add_time_offset(seg.get("end_time",   "00:00"), t_start)
            all_segments.append(seg)

        for ca in chunk_result.get("cultural_analysis", []):
            if "timestamp" in ca:
                ca["timestamp"] = _add_time_offset(ca["timestamp"], t_start)
            all_cultural_analysis.append(ca)

        # Capture tail context (last 2 segments' original text) for next chunk
        last_segs = chunk_result.get("segments", [])[-2:]
        tail_context = " ".join(s.get("original_text", "") for s in last_segs)

        if merged_result is None:
            merged_result = chunk_result

    if merged_result is None:
        return {"error": "All chunks failed to analyze"}

    merged_result["segments"] = all_segments
    merged_result["cultural_analysis"] = all_cultural_analysis
    return merged_result


# One pipeline at a time — prevents concurrent FFmpeg processes from OOM-killing
# the Render free-tier process (512 MB RAM).
_pipeline_semaphore = threading.Semaphore(1)


# ──────────────────────────────────────────────────────────────────────────────
# Full localization task
# ──────────────────────────────────────────────────────────────────────────────

def _run_localization(job_id: str, user_id: str, file_key: str, target_language: str):
    """
    Full video localization pipeline — runs as a plain function so it can be
    invoked by FastAPI background_tasks OR wrapped by the Celery task below.

      1. Gemini analysis  (URL path: no download; Files API path: download first)
      2. TTS audio generation
      3. Download to disk for FFmpeg (if URL path was used)
      4. FFmpeg stitch
      5. Free input + audio from disk early
      6. Upload output to R2
      7. Mark job complete in PostgreSQL
    """
    print(f"[Task] Starting full localization: job_id={job_id}")
    _cleanup_stale_temp_dirs()

    print(f"[Task] Waiting for pipeline slot: job_id={job_id}")
    with _pipeline_semaphore:
        print(f"[Task] Pipeline slot acquired: job_id={job_id}")
        _run_localization_inner(job_id, user_id, file_key, target_language)


def _run_localization_inner(job_id: str, user_id: str, file_key: str, target_language: str):
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

        if not public_url:
            raise Exception(
                "R2_PUBLIC_URL is not configured. Set this environment variable on Render "
                "to allow Gemini to fetch the video directly from R2."
            )

        print(f"[Task] Using R2 public URL for Gemini: {public_url}")
        video_duration, video_codec = _get_video_info_url(public_url)
        print(f"[Task] Video duration: {video_duration:.1f}s, codec: {video_codec} (threshold: {GEMINI_CHUNK_THRESHOLD_S}s)")

        # Gemini's URL fetcher only reliably handles H.264. For HEVC/VP9/AV1/other
        # codecs download first and use the Files API (which transcodes on Google's side).
        gemini_needs_download = video_codec not in ("h264", "unknown")
        if gemini_needs_download:
            print(f"[Task] Codec {video_codec!r} not H.264 — downloading for Files API")
            dl = s3_service.download_file(file_key, local_video_path)
            if "error" in dl:
                raise Exception(f"Download for Files API failed: {dl['error']}")

        if video_duration > GEMINI_CHUNK_THRESHOLD_S:
            print(f"[Task] Long video — using VAD-chunked Gemini analysis")
            analysis_result = asyncio.run(
                _analyze_video_in_chunks(public_url, target_language, temp_dir)
            )
        elif gemini_needs_download:
            analysis_result = asyncio.run(
                gemini_service.analyze_video(
                    video_path=local_video_path, target_language=target_language
                )
            )
        else:
            try:
                analysis_result = asyncio.run(
                    gemini_service.analyze_video(video_url=public_url, target_language=target_language)
                )
            except Exception as url_err:
                # Safety net: URL fetch still failed despite H.264 (transient R2 block).
                if "invalid_argument" in str(url_err).lower() or "400" in str(url_err):
                    print(f"[Task] URL fetch failed ({url_err}) — downloading as last resort")
                    dl = s3_service.download_file(file_key, local_video_path)
                    if "error" in dl:
                        raise Exception(f"Fallback download failed: {dl['error']}")
                    analysis_result = asyncio.run(
                        gemini_service.analyze_video(
                            video_path=local_video_path, target_language=target_language
                        )
                    )
                else:
                    raise
        if "error" in analysis_result:
            raise Exception(f"Gemini analysis failed: {analysis_result['error']}")

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

        # ── Step 4.5: Extract audio-only dub track for YouTube ────────────────
        # Strip the video stream from the already-stitched output — instant,
        # no re-encode. Produces the alternate audio track creators upload to
        # YouTube Studio so viewers can switch between Original and Hindi.
        dub_audio_url = None
        dub_audio_s3_key = None
        dub_audio_path = os.path.join(temp_dir, "dub_audio.aac")
        try:
            audio_ext = _subprocess.run(
                ["ffmpeg", "-y", "-i", output_video_path, "-vn", "-c:a", "copy", dub_audio_path],
                capture_output=True, text=True, timeout=60
            )
            if audio_ext.returncode == 0 and os.path.exists(dub_audio_path):
                dub_audio_s3_key = f"outputs/{job_id}/dub_audio_{target_language}.aac"
                dub_upload = s3_service.upload_file(dub_audio_path, dub_audio_s3_key)
                if dub_upload.get("success"):
                    dub_dl = s3_service.generate_presigned_download_url(dub_audio_s3_key)
                    dub_audio_url = dub_dl.get("download_url")
                    print(f"[Task] Dub audio track uploaded: {dub_audio_s3_key}")
        except Exception as dub_err:
            print(f"[Task] Dub audio extraction non-fatal: {dub_err}")

        # ── Step 5: Free input + audio early — output upload is next ─────────
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
            "dub_audio_url": dub_audio_url,
            "dub_audio_s3_key": dub_audio_s3_key,
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

        print(f"[Task] Job {job_id} completed successfully")
        return {"status": "complete", "job_id": job_id}

    except Exception as exc:
        print(f"[Task] Job {job_id} failed: {exc}")
        job_service.fail_job(job_id, user_id, str(exc))
        raise

    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[Cleanup] Warning: {e}")


@celery_app.task(
    bind=True,
    name="tasks.process_video_localization",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=900,
    time_limit=1200,
)
def process_video_localization(self, job_id: str, user_id: str, file_key: str, target_language: str):
    """Celery wrapper — delegates to _run_localization and retries on failure."""
    try:
        return _run_localization(job_id, user_id, file_key, target_language)
    except Exception as exc:
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc


# ──────────────────────────────────────────────────────────────────────────────
# Draft creation task (analysis only — no TTS / FFmpeg)
# ──────────────────────────────────────────────────────────────────────────────

def _run_draft_creation(job_id: str, user_id: str, file_key: str, target_language: str):
    """
    Phase 1 only: Gemini analysis → draft segments for human review.
    No TTS or FFmpeg. Uses URL path when R2_PUBLIC_URL is available so the
    video is never written to Render's disk at all for this task.
    Callable directly by background_tasks or wrapped by the Celery task below.
    """
    print(f"[Task] Starting draft creation: job_id={job_id}")
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

        if not public_url:
            raise Exception(
                "R2_PUBLIC_URL is not configured. Set this environment variable on Render "
                "to allow Gemini to fetch the video directly from R2."
            )

        print(f"[Task] Draft: using R2 public URL for Gemini: {public_url}")
        draft_result = asyncio.run(
            gemini_service.generate_translation_draft(
                video_url=public_url,
                target_language=target_language
            )
        )
        if "error" in draft_result:
            raise Exception(f"Gemini analysis failed: {draft_result['error']}")

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

        print(f"[Task] Draft job {job_id} completed")
        return {"status": "complete", "job_id": job_id}

    except Exception as exc:
        print(f"[Task] Draft job {job_id} failed: {exc}")
        job_service.fail_job(job_id, user_id, str(exc))
        raise

    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[Cleanup] Warning: {e}")


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
    """Celery wrapper — delegates to _run_draft_creation and retries on failure."""
    try:
        return _run_draft_creation(job_id, user_id, file_key, target_language)
    except Exception as exc:
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc


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
