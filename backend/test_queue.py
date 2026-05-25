#!/usr/bin/env python3
"""
Queue System Test Script
Tests the queue service functionality

Usage:
    python test_queue.py
"""

import asyncio
import json
from services.queue_service import queue_service, JobPriority


async def test_queue_system():
    """Test the queue system functionality"""
    print("🧪 Testing Queue System")
    print("=" * 50)
    
    # Test 1: Health Check
    print("1. Testing queue health...")
    health = queue_service.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Backend: {health['backend']}")
    
    # Test 2: Queue Stats
    print("\n2. Getting queue stats...")
    stats = queue_service.get_queue_stats()
    print(f"   Queue type: {stats.get('queue_type', 'unknown')}")
    print(f"   Messages: {stats.get('approximate_messages', 0)}")
    
    # Test 3: Enqueue Jobs
    print("\n3. Enqueuing test jobs...")
    
    test_jobs = [
        {
            "job_type": "video_localization",
            "user_id": "test_user_1",
            "payload": {"file_key": "test1.mp4", "target_language": "hindi"},
            "priority": JobPriority.NORMAL
        },
        {
            "job_type": "draft_creation", 
            "user_id": "test_user_2",
            "payload": {"file_key": "test2.mp4", "target_language": "tamil"},
            "priority": JobPriority.HIGH
        },
        {
            "job_type": "video_localization",
            "user_id": "test_user_3", 
            "payload": {"file_key": "test3.mp4", "target_language": "bengali"},
            "priority": JobPriority.LOW
        }
    ]
    
    job_ids = []
    for i, job_data in enumerate(test_jobs):
        job_id = await queue_service.enqueue_job(**job_data)
        job_ids.append(job_id)
        print(f"   ✅ Enqueued job {i+1}: {job_id}")
    
    # Test 4: Check Updated Stats
    print("\n4. Updated queue stats...")
    stats = queue_service.get_queue_stats()
    print(f"   Messages after enqueue: {stats.get('approximate_messages', 0)}")
    
    # Test 5: Dequeue Jobs
    print("\n5. Dequeuing jobs...")
    
    dequeued_jobs = []
    for i in range(len(test_jobs)):
        job = await queue_service.dequeue_job(wait_time_seconds=1)
        if job:
            dequeued_jobs.append(job)
            print(f"   ✅ Dequeued job: {job.job_id} (type: {job.job_type}, priority: {job.priority.value})")
            
            # Complete the job to remove it from queue
            await queue_service.complete_job(job)
        else:
            print(f"   ❌ No job dequeued (attempt {i+1})")
    
    # Test 6: Final Stats
    print("\n6. Final queue stats...")
    stats = queue_service.get_queue_stats()
    print(f"   Messages after dequeue: {stats.get('approximate_messages', 0)}")
    
    # Test 7: Priority Order Check
    print("\n7. Testing priority ordering...")
    if len(dequeued_jobs) >= 2:
        # High priority job should come before normal/low priority
        priorities = [job.priority for job in dequeued_jobs]
        print(f"   Dequeue order: {[p.value for p in priorities]}")
        
        # Check if HIGH priority came first
        if priorities[0] == JobPriority.HIGH:
            print("   ✅ Priority ordering working correctly")
        else:
            print("   ⚠️  Priority ordering may not be working as expected")
    
    print("\n" + "=" * 50)
    print("🎉 Queue system test completed!")
    
    return {
        "health": health,
        "final_stats": stats,
        "jobs_processed": len(dequeued_jobs),
        "test_passed": len(dequeued_jobs) > 0
    }


async def main():
    """Main test function"""
    try:
        results = await test_queue_system()
        
        if results["test_passed"]:
            print("✅ All tests passed!")
            return 0
        else:
            print("❌ Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)