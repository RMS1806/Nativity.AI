"""
Celery application for Nativity.ai
Uses Redis (Upstash free tier) as broker and result backend.
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "nativity",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],  # tasks.py lives next to this file
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Worker behaviour
    # One task at a time — video processing is RAM-heavy on free Render tier
    worker_prefetch_multiplier=1,
    task_acks_late=True,           # ACK only after the task finishes (safe retries on crash)

    # Retry / visibility
    task_soft_time_limit=900,      # 15 min soft limit — warn before kill
    task_time_limit=1200,          # 20 min hard limit

    # Result TTL — keep results for 24 h, then discard
    result_expires=86400,

    # Don't keep results for tasks where the caller never asks
    task_ignore_result=False,
)
