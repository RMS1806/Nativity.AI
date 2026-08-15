"""
Queue Service for Nativity.ai
Dispatches jobs to Celery workers (Redis broker via Upstash).

All SQS / boto3 code has been removed. The public API (enqueue_job,
health_check, get_queue_stats) is preserved so no routes need changes.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from celery_app import celery_app


class JobPriority(Enum):
    """Job priority levels — Celery maps these to named queues."""
    LOW    = "low"
    NORMAL = "normal"
    HIGH   = "high"
    URGENT = "urgent"


# Map priority → Celery queue name
_PRIORITY_QUEUE = {
    JobPriority.LOW:    "low",
    JobPriority.NORMAL: "default",
    JobPriority.HIGH:   "high",
    JobPriority.URGENT: "high",
}


@dataclass
class QueueJob:
    """Lightweight job descriptor (kept for compat with VideoProcessor signatures)."""
    job_id: str
    job_type: str
    user_id: str
    payload: Dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL
    created_at: str = None
    retry_count: int = 0
    max_retries: int = 2

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat() + "Z"


class QueueService:
    """
    Dispatches video processing jobs to Celery workers.
    Redis (Upstash) is used as the Celery broker.
    """

    def is_available(self) -> bool:
        """Always True — Celery is always the queue backend."""
        return True

    async def enqueue_job(
        self,
        job_type: str,
        user_id: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        delay_seconds: int = 0,
        job_id: Optional[str] = None,
    ) -> str:
        """
        Dispatch a Celery task for the given job type.

        Returns the job_id (pre-created by job_service before this is called).
        """
        job_id = job_id or str(uuid.uuid4())
        queue_name = _PRIORITY_QUEUE.get(priority, "default")

        if job_type == "video_localization":
            from tasks import process_video_localization
            process_video_localization.apply_async(
                kwargs={
                    "job_id": job_id,
                    "user_id": user_id,
                    "file_key": payload.get("file_key"),
                    "target_language": payload.get("target_language"),
                },
                queue=queue_name,
                countdown=delay_seconds,
            )
            print(f"✅ Celery: video_localization job {job_id} queued → {queue_name}")

        elif job_type == "draft_creation":
            from tasks import process_draft_creation
            process_draft_creation.apply_async(
                kwargs={
                    "job_id": job_id,
                    "user_id": user_id,
                    "file_key": payload.get("file_key"),
                    "target_language": payload.get("target_language"),
                },
                queue=queue_name,
                countdown=delay_seconds,
            )
            print(f"✅ Celery: draft_creation job {job_id} queued → {queue_name}")

        else:
            print(f"⚠️  Unknown job type: {job_type} — not dispatched")

        return job_id

    def get_queue_stats(self) -> Dict[str, Any]:
        """Return basic queue info via Celery inspect."""
        try:
            inspect = celery_app.control.inspect(timeout=2)
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            active_count = sum(len(v) for v in active.values())
            reserved_count = sum(len(v) for v in reserved.values())
            return {
                "queue_type": "celery+redis",
                "active_tasks": active_count,
                "reserved_tasks": reserved_count,
            }
        except Exception as e:
            return {"queue_type": "celery+redis", "error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Return queue health status."""
        try:
            stats = self.get_queue_stats()
            return {
                "status": "healthy",
                "backend": "celery+redis",
                "stats": stats,
            }
        except Exception as e:
            return {
                "status": "degraded",
                "backend": "celery+redis",
                "error": str(e),
            }

    # ── Legacy stubs (called by VideoProcessor — no longer needed but kept for compat) ──

    async def dequeue_job(self, wait_time_seconds: int = 20) -> None:
        """Not used with Celery — workers pull directly from Redis broker."""
        return None

    async def complete_job(self, job) -> bool:
        """Not needed — Celery handles ACK automatically (acks_late=True)."""
        return True

    async def retry_job(self, job, delay_seconds: int = None) -> bool:
        """Not needed — Celery task retries are configured in the task decorator."""
        return False


# Singleton
queue_service = QueueService()