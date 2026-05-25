"""
Background Video Processing Worker for Nativity.ai
Handles video localization jobs from the queue

This worker:
- Polls SQS/local queue for jobs
- Processes video localization pipeline
- Updates job status in real-time
- Handles retries and error recovery
- Runs independently from the API server
"""

import asyncio
import tempfile
import shutil
import os
import sys
from typing import Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.queue_service import queue_service, QueueJob
from services.job_service import job_service
from services.gemini_service import gemini_service
from services.s3_service import s3_service
from services.tts_service import TTSService
from services.ffmpeg_service import ffmpeg_service
from models import JobStatus


class VideoProcessor:
    """
    Background worker for processing video localization jobs
    
    Features:
    - Async job processing
    - Real-time status updates
    - Error handling and retries
    - Resource cleanup
    - Graceful shutdown
    """
    
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.running = False
        self.current_job = None
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = None
    
    async def start(self):
        """Start the worker and begin processing jobs"""
        self.running = True
        self.start_time = datetime.utcnow()
        
        print(f"🚀 Video processor {self.worker_id} starting...")
        print(f"   Queue backend: {queue_service.health_check()['backend']}")
        print(f"   Services ready: Gemini={gemini_service.is_configured()}, S3={s3_service.is_configured()}, FFmpeg={ffmpeg_service.is_available()}")
        
        while self.running:
            try:
                # Get next job from queue (with long polling)
                job = await queue_service.dequeue_job(wait_time_seconds=20)
                
                if job:
                    await self._process_job(job)
                else:
                    # No jobs available, short sleep
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                print(f"\n🛑 Worker {self.worker_id} received shutdown signal")
                break
            except Exception as e:
                print(f"❌ Worker {self.worker_id} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        print(f"👋 Worker {self.worker_id} stopped. Processed: {self.processed_count}, Failed: {self.failed_count}")
    
    def stop(self):
        """Stop the worker gracefully"""
        self.running = False
    
    async def _process_job(self, job: QueueJob):
        """
        Process a single video localization job
        
        Args:
            job: QueueJob to process
        """
        self.current_job = job
        job_id = job.job_id
        
        print(f"\n📹 Processing job {job_id} (type: {job.job_type})")
        
        try:
            # Update job status to processing
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.ANALYZING,
                progress=5,
                message="🚀 Starting video processing...",
                user_id=job.user_id
            )
            
            # Route to appropriate processor based on job type
            if job.job_type == "video_localization":
                success = await self._process_full_localization(job)
            elif job.job_type == "draft_creation":
                success = await self._process_draft_creation(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            if success:
                # Mark job as complete and remove from queue
                await queue_service.complete_job(job)
                self.processed_count += 1
                print(f"✅ Job {job_id} completed successfully")
            else:
                # Job failed, handle retry
                await self._handle_job_failure(job, "Processing failed")
                
        except Exception as e:
            print(f"❌ Job {job_id} failed with error: {e}")
            await self._handle_job_failure(job, str(e))
        
        finally:
            self.current_job = None
    
    async def _process_full_localization(self, job: QueueJob) -> bool:
        """
        Process complete video localization pipeline
        
        Args:
            job: Job containing file_key, target_language, user_id
            
        Returns:
            bool: True if successful
        """
        payload = job.payload
        file_key = payload.get("file_key")
        target_language = payload.get("target_language")
        user_id = job.user_id
        job_id = job.job_id
        
        temp_dir = None
        tts_temp_service = None
        
        try:
            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp(prefix=f"nativity_{job_id[:8]}_")
            local_video_path = os.path.join(temp_dir, "input_video.mp4")
            output_video_path = os.path.join(temp_dir, "output_localized.mp4")
            whatsapp_video_path = os.path.join(temp_dir, "output_whatsapp.mp4")
            
            # Step 1: Download from S3
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.UPLOADING,
                progress=10,
                message="📥 Downloading video from S3...",
                user_id=user_id
            )
            
            download_result = s3_service.download_file(file_key, local_video_path)
            if "error" in download_result:
                raise Exception(f"Download failed: {download_result['error']}")
            
            # Step 2: Analyze with Gemini
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.ANALYZING,
                progress=25,
                message="🧠 Gemini is analyzing your video...",
                user_id=user_id
            )
            
            analysis_result = await gemini_service.analyze_video(
                video_path=local_video_path,
                target_language=target_language
            )
            
            if "error" in analysis_result:
                raise Exception(f"Analysis failed: {analysis_result['error']}")
            
            segments = analysis_result.get('segments', [])
            cultural_report = analysis_result.get('cultural_report', {})
            
            job_service.update_job_status(
                job_id=job_id,
                progress=45,
                message=f"✅ Analysis complete! Found {len(segments)} segments",
                user_id=user_id
            )
            
            # Step 3: Generate TTS Audio
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.GENERATING_AUDIO,
                progress=50,
                message="🎙️ Generating localized voice audio...",
                user_id=user_id
            )
            
            tts_temp_service = TTSService(output_dir=os.path.join(temp_dir, "audio_segments"))
            
            # Determine voice gender
            tts_instructions = analysis_result.get('tts_instructions', {})
            voice_gender = tts_instructions.get('recommended_voice_gender', 'female')
            if voice_gender == 'mixed':
                voice_gender = 'female'
            
            # Generate audio segments
            audio_segments = await tts_temp_service.generate_segments_from_analysis(
                segments=segments,
                language=target_language,
                gender=voice_gender
            )
            
            job_service.update_job_status(
                job_id=job_id,
                progress=70,
                message=f"✅ Generated {len(audio_segments)} audio segments",
                user_id=user_id
            )
            
            # Step 4: Stitch Video with FFmpeg
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.STITCHING,
                progress=75,
                message="🎬 Stitching new audio with video...",
                user_id=user_id
            )
            
            # Convert audio segments for FFmpeg
            audio_segment_dicts = [
                {
                    "file_path": seg.file_path,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time
                }
                for seg in audio_segments
            ]
            
            # Get TTS delay from analysis
            video_metadata = analysis_result.get("video_metadata", {})
            tts_delay = video_metadata.get("first_speech_offset_seconds", 0.0)
            
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
            
            job_service.update_job_status(
                job_id=job_id,
                progress=85,
                message=f"✅ Video stitched! Size: {stitch_result.file_size_mb:.1f}MB",
                user_id=user_id
            )
            
            # Step 5: Create WhatsApp version if needed
            whatsapp_url = None
            if stitch_result.file_size_mb > 15:
                job_service.update_job_status(
                    job_id=job_id,
                    message="📱 Creating WhatsApp-optimized version...",
                    user_id=user_id
                )
                
                whatsapp_result = ffmpeg_service.create_whatsapp_version(
                    input_path=output_video_path,
                    output_path=whatsapp_video_path,
                    target_size_mb=14.5
                )
                
                if whatsapp_result and whatsapp_result.success:
                    whatsapp_key = f"outputs/{job_id}/whatsapp_{target_language}.mp4"
                    whatsapp_upload = s3_service.upload_file(whatsapp_video_path, whatsapp_key)
                    if whatsapp_upload.get("success"):
                        whatsapp_download = s3_service.generate_presigned_download_url(whatsapp_key)
                        whatsapp_url = whatsapp_download.get("download_url")
            
            # Step 6: Upload to S3
            job_service.update_job_status(
                job_id=job_id,
                progress=90,
                message="☁️ Uploading localized video to S3...",
                user_id=user_id
            )
            
            output_key = f"outputs/{job_id}/localized_{target_language}.mp4"
            upload_result = s3_service.upload_file(output_video_path, output_key)
            
            if "error" in upload_result:
                raise Exception(f"Upload failed: {upload_result['error']}")
            
            # Get download URL
            download_result = s3_service.generate_presigned_download_url(output_key)
            
            # Step 7: Complete job
            results = {
                "analysis": analysis_result,
                "segments": segments,
                "cultural_report": cultural_report,
                "segments_count": len(segments),
                "file_size_mb": stitch_result.file_size_mb,
                "words_localized": sum(len(seg.get("translated_text", "").split()) for seg in segments)
            }
            
            job_service.complete_job(
                job_id=job_id,
                user_id=user_id,
                output_url=download_result.get("download_url"),
                output_s3_key=output_key,
                results=results,
                whatsapp_url=whatsapp_url,
                file_size_mb=stitch_result.file_size_mb
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Full localization failed for job {job_id}: {e}")
            job_service.fail_job(job_id, user_id, str(e))
            return False
            
        finally:
            # Cleanup temp files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"⚠️  Cleanup warning: {e}")
    
    async def _process_draft_creation(self, job: QueueJob) -> bool:
        """
        Process draft creation (analysis only, no TTS/video processing)
        
        Args:
            job: Job containing file_key, target_language, user_id
            
        Returns:
            bool: True if successful
        """
        # Implementation similar to _process_full_localization but stops after Gemini analysis
        # This would be used for the two-phase workflow (draft → review → finalize)
        
        payload = job.payload
        file_key = payload.get("file_key")
        target_language = payload.get("target_language")
        user_id = job.user_id
        job_id = job.job_id
        
        temp_dir = None
        
        try:
            temp_dir = tempfile.mkdtemp(prefix=f"nativity_draft_{job_id[:8]}_")
            local_video_path = os.path.join(temp_dir, "input_video.mp4")
            
            # Download and analyze only
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.UPLOADING,
                progress=10,
                message="📥 Downloading video for analysis...",
                user_id=user_id
            )
            
            download_result = s3_service.download_file(file_key, local_video_path)
            if "error" in download_result:
                raise Exception(f"Download failed: {download_result['error']}")
            
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.ANALYZING,
                progress=30,
                message="🧠 Gemini is analyzing and translating...",
                user_id=user_id
            )
            
            draft_result = await gemini_service.generate_translation_draft(
                video_path=local_video_path,
                target_language=target_language
            )
            
            if "error" in draft_result:
                raise Exception(f"Analysis failed: {draft_result['error']}")
            
            segments = draft_result.get("segments", [])
            
            # Complete with draft results
            job_service.update_job_status(
                job_id=job_id,
                status=JobStatus.COMPLETE,
                progress=100,
                message=f"📝 Draft ready! {len(segments)} segments for review.",
                user_id=user_id
            )
            
            # Store draft results
            results = {
                "draft": draft_result,
                "segments": segments,
                "cultural_analysis": draft_result.get("cultural_analysis", []),
                "video_title": draft_result.get("video_title", ""),
                "target_language": target_language
            }
            
            job_service.redis.set_job_results(job_id, results)
            
            return True
            
        except Exception as e:
            print(f"❌ Draft creation failed for job {job_id}: {e}")
            job_service.fail_job(job_id, user_id, str(e))
            return False
            
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
    
    async def _handle_job_failure(self, job: QueueJob, error_message: str):
        """
        Handle job failure with retry logic
        
        Args:
            job: Failed job
            error_message: Error description
        """
        # Try to retry the job
        retry_success = await queue_service.retry_job(job)
        
        if not retry_success:
            # Max retries exceeded, mark as permanently failed
            job_service.fail_job(
                job_id=job.job_id,
                user_id=job.user_id,
                error_message=f"Max retries exceeded. Last error: {error_message}"
            )
            self.failed_count += 1
        
        # Complete the current job (remove from queue)
        await queue_service.complete_job(job)
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "current_job": self.current_job.job_id if self.current_job else None,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "uptime_seconds": uptime,
            "queue_stats": queue_service.get_queue_stats()
        }


async def main():
    """Main entry point for the worker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Nativity.ai Video Processing Worker')
    parser.add_argument('--worker-id', default='worker-1', help='Unique worker identifier')
    args = parser.parse_args()
    
    worker = VideoProcessor(worker_id=args.worker_id)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested")
    finally:
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())