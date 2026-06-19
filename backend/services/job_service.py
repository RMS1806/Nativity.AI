"""
Unified Job Management Service for Nativity.ai
Combines Redis (fast) and DynamoDB (persistent) for optimal performance

This service provides:
- Fast job status updates via Redis
- Persistent job storage via DynamoDB
- Automatic fallback when Redis is unavailable
- Job recovery and cleanup utilities
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from services.redis_service import redis_service
from services.db_service import db_service
from models import JobStatus, LocalizationJob


class JobService:
    """
    Unified job management combining Redis and DynamoDB
    
    Strategy:
    - Write to both Redis (fast) and DynamoDB (persistent)
    - Read from Redis first, fallback to DynamoDB
    - Use Redis for real-time updates, DynamoDB for history
    """
    
    def __init__(self):
        self.redis = redis_service
        self.db = db_service
    
    def create_job(
        self,
        user_id: str,
        input_file: str,
        target_language: str,
        job_type: str = "localization"
    ) -> LocalizationJob:
        """
        Create a new job with unique ID
        
        Args:
            user_id: User identifier
            input_file: S3 key of input file
            target_language: Target language code
            job_type: Type of job (localization, draft, etc.)
            
        Returns:
            LocalizationJob object
        """
        job_id = str(uuid.uuid4())
        
        job = LocalizationJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            progress=0,
            message="Job created, initializing...",
            input_file=input_file,
            target_language=target_language
        )
        
        # Save to both Redis and DynamoDB
        self._save_job_status(job, user_id)
        
        # Save initial record to DynamoDB
        self.db.save_video(
            user_id=user_id,
            job_id=job_id,
            target_language=target_language,
            input_file=input_file,
            status="pending",
            progress=0
        )
        
        return job
    
    def update_job_status(
        self,
        job_id: str,
        status: JobStatus = None,
        progress: int = None,
        message: str = None,
        user_id: str = None,
        error: str = None
    ) -> bool:
        """
        Update job status in both Redis and DynamoDB
        
        Args:
            job_id: Job identifier
            status: New job status
            progress: Progress percentage (0-100)
            message: Status message
            user_id: User ID (for DynamoDB updates)
            error: Error message if failed
            
        Returns:
            bool: True if successful
        """
        # Get current job to preserve existing data
        current_job = self.get_job_status(job_id)
        if not current_job:
            print(f"Warning: Job {job_id} not found for status update")
            return False
        
        # Update job object (status is optional — preserve current when not given)
        if status is not None:
            current_job.status = status
        if progress is not None:
            current_job.progress = progress
        if message is not None:
            current_job.message = message
        if error is not None:
            current_job.error = error

        # Save to Redis for real-time updates
        self.redis.set_job_status(
            job_id=job_id,
            status=current_job.status.value,
            progress=current_job.progress,
            message=current_job.message
        )

        # Save to DynamoDB for persistence (if user_id available)
        if user_id:
            if current_job.status == JobStatus.FAILED and error:
                self.db.save_video(
                    user_id=user_id,
                    job_id=job_id,
                    target_language=current_job.target_language,
                    input_file=current_job.input_file,
                    status="failed",
                    progress=current_job.progress,
                    error_message=error
                )
            else:
                self.db.update_job_progress(
                    user_id=user_id,
                    job_id=job_id,
                    progress=current_job.progress,
                    message=current_job.message,
                    status=current_job.status.value
                )
        
        return True
    
    def get_job_status(self, job_id: str) -> Optional[LocalizationJob]:
        """
        Get job status, trying Redis first, then DynamoDB
        
        Args:
            job_id: Job identifier
            
        Returns:
            LocalizationJob object or None
        """
        # Try Redis first (fast)
        redis_data = self.redis.get_job_status(job_id)
        if redis_data:
            return LocalizationJob(
                job_id=redis_data.get("job_id"),
                status=JobStatus(redis_data.get("status", "pending")),
                progress=redis_data.get("progress", 0),
                message=redis_data.get("message", ""),
                input_file="",  # Not stored in Redis
                target_language=""  # Not stored in Redis
            )
        
        # Fallback to DynamoDB (slower but persistent)
        db_job = self.db.get_job_by_id(job_id)
        if db_job:
            return LocalizationJob(
                job_id=db_job.get("job_id"),
                status=JobStatus(db_job.get("status", "pending")),
                progress=db_job.get("progress", 0),
                message=db_job.get("message", ""),
                input_file=db_job.get("input_file", ""),
                target_language=db_job.get("target_language", ""),
                output_file=db_job.get("output_s3_key"),
                error=db_job.get("error_message")
            )
        
        return None
    
    def complete_job(
        self,
        job_id: str,
        user_id: str,
        output_url: str,
        output_s3_key: str,
        results: Dict[str, Any],
        whatsapp_url: str = None,
        file_size_mb: float = None
    ) -> bool:
        """
        Mark job as complete with results
        
        Args:
            job_id: Job identifier
            user_id: User identifier
            output_url: Download URL for result
            output_s3_key: S3 key for output file
            results: Job results dictionary
            whatsapp_url: Optional WhatsApp version URL
            file_size_mb: Output file size
            
        Returns:
            bool: True if successful
        """
        # Update status to complete
        self.update_job_status(
            job_id=job_id,
            status=JobStatus.COMPLETE,
            progress=100,
            message="🎉 Localization complete! Your video is ready.",
            user_id=user_id
        )
        
        # Store results in Redis for fast access
        self.redis.set_job_results(job_id, results)
        
        # Update DynamoDB with final results
        current_job = self.get_job_status(job_id)
        if current_job:
            self.db.save_video(
                user_id=user_id,
                job_id=job_id,
                target_language=current_job.target_language,
                input_file=current_job.input_file,
                status="complete",
                output_url=output_url,
                output_s3_key=output_s3_key,
                whatsapp_url=whatsapp_url,
                file_size_mb=file_size_mb,
                progress=100,
                cultural_report=results.get("cultural_report"),
                segments_count=results.get("segments_count"),
                draft_segments=results.get("segments"),
                subtitle_s3_key=results.get("subtitle_s3_key"),
                words_localized=results.get("words_localized")
            )
        
        return True
    
    def fail_job(
        self,
        job_id: str,
        user_id: str,
        error_message: str
    ) -> bool:
        """
        Mark job as failed with error message
        
        Args:
            job_id: Job identifier
            user_id: User identifier
            error_message: Error description
            
        Returns:
            bool: True if successful
        """
        return self.update_job_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            message=f"❌ Processing failed: {error_message}",
            user_id=user_id,
            error=error_message
        )
    
    def get_job_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job results from Redis or DynamoDB
        
        Args:
            job_id: Job identifier
            
        Returns:
            dict with results or None
        """
        # Try Redis first
        results = self.redis.get_job_results(job_id)
        if results:
            return results
        
        # Fallback to DynamoDB (results might be in draft_segments)
        db_job = self.db.get_job_by_id(job_id)
        if db_job and db_job.get("draft_segments"):
            import json
            try:
                segments = json.loads(db_job["draft_segments"])
                return {
                    "segments": segments,
                    "cultural_report": json.loads(db_job.get("cultural_report", "{}")),
                    "output_url": db_job.get("output_url"),
                    "whatsapp_url": db_job.get("whatsapp_url"),
                    "file_size_mb": float(db_job.get("file_size_mb", 0))
                }
            except (json.JSONDecodeError, ValueError):
                pass
        
        return None
    
    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """
        Clean up old completed jobs from Redis
        DynamoDB jobs are kept for history
        
        Args:
            days_old: Remove Redis entries older than this many days
            
        Returns:
            int: Number of jobs cleaned up
        """
        if not self.redis.is_available():
            return 0
        
        # This would require storing timestamps in Redis
        # For now, just return 0 as a placeholder
        # In production, you'd implement TTL-based cleanup
        return 0
    
    def get_user_jobs(
        self,
        user_id: str,
        limit: int = 20,
        include_active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get user's job history from DynamoDB
        
        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return
            include_active_only: Only return active jobs
            
        Returns:
            list of job dictionaries
        """
        history = self.db.get_user_history(user_id, limit)
        if not history.get("success"):
            return []
        
        jobs = history.get("videos", [])
        
        if include_active_only:
            jobs = [
                job for job in jobs 
                if job.get("status") in ["pending", "processing", "needs_review"]
            ]
        
        return jobs
    
    def _save_job_status(self, job: LocalizationJob, user_id: str = None):
        """
        Internal method to save job status to both Redis and DynamoDB
        
        Args:
            job: LocalizationJob object
            user_id: Optional user ID for DynamoDB
        """
        # Save to Redis for fast access
        self.redis.set_job_status(
            job_id=job.job_id,
            status=job.status.value,
            progress=job.progress,
            message=job.message
        )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of job management services
        
        Returns:
            dict with health status
        """
        redis_health = self.redis.health_check()
        
        # Test DynamoDB
        db_healthy = self.db.is_configured()
        
        return {
            "job_service": "healthy",
            "redis": redis_health,
            "dynamodb": {
                "status": "healthy" if db_healthy else "unavailable",
                "configured": db_healthy
            }
        }


# Singleton instance
job_service = JobService()