#!/usr/bin/env python3
"""
Worker Startup Script for Nativity.ai
Starts background video processing workers

Usage:
    python start_worker.py                    # Start single worker
    python start_worker.py --workers 3       # Start 3 workers
    python start_worker.py --worker-id gpu-1 # Custom worker ID
"""

import asyncio
import argparse
import signal
import sys
from typing import List
from workers.video_processor import VideoProcessor


class WorkerManager:
    """Manages multiple video processing workers"""
    
    def __init__(self):
        self.workers: List[VideoProcessor] = []
        self.running = False
    
    async def start_workers(self, worker_count: int = 1, worker_prefix: str = "worker"):
        """Start multiple workers"""
        self.running = True
        
        print(f"🚀 Starting {worker_count} video processing workers...")
        
        # Create workers
        for i in range(worker_count):
            worker_id = f"{worker_prefix}-{i+1}"
            worker = VideoProcessor(worker_id=worker_id)
            self.workers.append(worker)
        
        # Start all workers concurrently
        tasks = [worker.start() for worker in self.workers]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received")
        finally:
            await self.stop_workers()
    
    async def stop_workers(self):
        """Stop all workers gracefully"""
        print("🛑 Stopping workers...")
        
        for worker in self.workers:
            worker.stop()
        
        # Wait a moment for graceful shutdown
        await asyncio.sleep(2)
        
        print("👋 All workers stopped")
    
    def get_stats(self) -> dict:
        """Get statistics for all workers"""
        return {
            "worker_count": len(self.workers),
            "running": self.running,
            "workers": [worker.get_stats() for worker in self.workers]
        }


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Nativity.ai Video Processing Workers')
    parser.add_argument('--workers', type=int, default=1, help='Number of workers to start')
    parser.add_argument('--worker-prefix', default='worker', help='Worker ID prefix')
    args = parser.parse_args()
    
    manager = WorkerManager()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}")
        # This will cause the KeyboardInterrupt in start_workers
        raise KeyboardInterrupt()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await manager.start_workers(
            worker_count=args.workers,
            worker_prefix=args.worker_prefix
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested")
    except Exception as e:
        print(f"❌ Worker manager error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())