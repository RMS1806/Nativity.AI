"""
Redis Service for Nativity.ai
Handles real-time job status caching and session management

Redis is used for:
- Real-time job status updates (fast polling)
- Job progress caching
- Session data caching
- Rate limiting counters
"""

import redis
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from config import settings


class RedisService:
    """
    Redis service for caching and real-time data
    Falls back gracefully if Redis is not available
    """
    
    def __init__(self):
        self._client = None
        self._available = False
        self._connect()
    
    def _connect(self):
        """Initialize Redis connection with fallback"""
        try:
            # Try to connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self._client.ping()
            self._available = True
            print("✅ Redis connected successfully")
            
        except Exception as e:
            print(f"⚠️  Redis not available: {e}")
            print("   Falling back to DynamoDB-only mode")
            self._client = None
            self._available = False
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self._available and self._client is not None
    
    def set_job_status(
        self, 
        job_id: str, 
        status: str, 
        progress: int = 0, 
        message: str = "",
        ttl: int = 3600
    ) -> bool:
        """
        Set job status in Redis for real-time updates
        
        Args:
            job_id: Unique job identifier
            status: Job status (pending, processing, complete, failed)
            progress: Progress percentage (0-100)
            message: Status message for user
            ttl: Time to live in seconds (default 1 hour)
        
        Returns:
            bool: True if successful, False if Redis unavailable
        """
        if not self.is_available():
            return False
        
        try:
            job_data = {
                "job_id": job_id,
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            key = f"job:{job_id}"
            self._client.setex(key, ttl, json.dumps(job_data))
            
            # Also set a quick status key for fast lookups
            self._client.setex(f"job_status:{job_id}", ttl, status)
            
            return True
            
        except Exception as e:
            print(f"Redis set_job_status error: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status from Redis
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            dict with job data or None if not found/unavailable
        """
        if not self.is_available():
            return None
        
        try:
            key = f"job:{job_id}"
            data = self._client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            print(f"Redis get_job_status error: {e}")
            return None
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete job data from Redis
        
        Args:
            job_id: Job ID to delete
            
        Returns:
            bool: True if successful
        """
        if not self.is_available():
            return False
        
        try:
            keys_to_delete = [
                f"job:{job_id}",
                f"job_status:{job_id}",
                f"job_results:{job_id}"
            ]
            
            self._client.delete(*keys_to_delete)
            return True
            
        except Exception as e:
            print(f"Redis delete_job error: {e}")
            return False
    
    def set_job_results(
        self, 
        job_id: str, 
        results: Dict[str, Any], 
        ttl: int = 7200
    ) -> bool:
        """
        Store job results (analysis, output URLs, etc.)
        
        Args:
            job_id: Job identifier
            results: Results dictionary
            ttl: Time to live in seconds (default 2 hours)
            
        Returns:
            bool: True if successful
        """
        if not self.is_available():
            return False
        
        try:
            key = f"job_results:{job_id}"
            self._client.setex(key, ttl, json.dumps(results))
            return True
            
        except Exception as e:
            print(f"Redis set_job_results error: {e}")
            return False
    
    def get_job_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job results from Redis
        
        Args:
            job_id: Job identifier
            
        Returns:
            dict with results or None
        """
        if not self.is_available():
            return None
        
        try:
            key = f"job_results:{job_id}"
            data = self._client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            print(f"Redis get_job_results error: {e}")
            return None
    
    def get_user_active_jobs(self, user_id: str) -> list:
        """
        Get list of active jobs for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            list of job IDs
        """
        if not self.is_available():
            return []
        
        try:
            pattern = f"job:*"
            active_jobs = []
            
            for key in self._client.scan_iter(match=pattern):
                data = self._client.get(key)
                if data:
                    job_data = json.loads(data)
                    # You'd need to store user_id in job data for this to work
                    # For now, return all active jobs
                    if job_data.get("status") in ["pending", "processing"]:
                        active_jobs.append(job_data.get("job_id"))
            
            return active_jobs
            
        except Exception as e:
            print(f"Redis get_user_active_jobs error: {e}")
            return []
    
    def increment_counter(self, key: str, ttl: int = 3600) -> int:
        """
        Increment a counter (useful for rate limiting)
        
        Args:
            key: Counter key
            ttl: Time to live in seconds
            
        Returns:
            int: New counter value
        """
        if not self.is_available():
            return 0
        
        try:
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)
            results = pipe.execute()
            return results[0]
            
        except Exception as e:
            print(f"Redis increment_counter error: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health and return status
        
        Returns:
            dict with health information
        """
        if not self.is_available():
            return {
                "status": "unavailable",
                "message": "Redis connection not available"
            }
        
        try:
            # Test basic operations
            test_key = "health_check_test"
            self._client.set(test_key, "test", ex=10)
            value = self._client.get(test_key)
            self._client.delete(test_key)
            
            if value == "test":
                return {
                    "status": "healthy",
                    "message": "Redis is working correctly"
                }
            else:
                return {
                    "status": "degraded",
                    "message": "Redis read/write test failed"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Redis health check failed: {e}"
            }


# Singleton instance
redis_service = RedisService()