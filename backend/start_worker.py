"""
Celery worker entry point for Nativity.ai.

Run locally:
    python start_worker.py

Run on Render (Background Worker start command):
    celery -A celery_app worker --loglevel=info --concurrency=1 -Q high,default,low

Concurrency is deliberately kept at 1 — video processing (Gemini + FFmpeg)
is RAM-heavy and the Render free tier has only 512 MB.
"""

import subprocess
import sys
import os


def main():
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=1",   # one job at a time — safe for 512 MB Render free tier
        "-Q", "high,default,low",  # consume all queues
    ]

    print("🚀 Starting Celery worker...")
    print(f"   Command: {' '.join(cmd)}")

    os.execv(sys.executable, cmd)


if __name__ == "__main__":
    main()