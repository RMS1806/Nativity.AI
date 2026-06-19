"""
Queue Service for Nativity.ai
Handles job queuing using AWS SQS with local fallback

This service provides:
- AWS SQS integration for production
- Local in-memory queue for development
- Retry logic with exponential backoff
- Dead letter queue for failed jobs
- Job priority handling
"""

import json
import boto3
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from dataclasses import dataclass, asdict
from enum import Enum

from config import settings


class JobPriority(Enum):
    """Job priority levels"""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class QueueJob:
    """Represents a job in the queue"""
    job_id: str
    job_type: str
    user_id: str
    payload: Dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL
    created_at: str = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat() + "Z"


class QueueService:
    """
    Queue service with AWS SQS backend and local fallback
    
    Features:
    - Production: Uses AWS SQS with DLQ
    - Development: Uses in-memory queue
    - Automatic retry with exponential backoff
    - Priority job handling
    """
    
    def __init__(self):
        self._sqs_client = None
        self._queue_url = None
        self._dlq_url = None
        self._local_queue = []  # Fallback for development
        self._processing = False
        self._configure()
    
    def _configure(self):
        """Configure SQS client and queue URLs"""
        try:
            if self._is_aws_configured():
                self._sqs_client = boto3.client(
                    'sqs',
                    region_name=settings.AWS_REGION
                )
                
                # Queue names based on environment
                # Use Terraform-created queues
                # Use Terraform-created queues
                self._queue_url = settings.VIDEO_PROCESSING_QUEUE_URL
                
                if self._queue_url:
                    print(f"✅ Using SQS queue: {self._queue_url}")
                else:
                    print("⚠️ VIDEO_PROCESSING_QUEUE_URL not configured")
            else:
                print("⚠️  AWS not configured, using local in-memory queue")
                
        except Exception as e:
            print(f"⚠️  SQS configuration failed: {e}")
            print("   Falling back to local in-memory queue")
    
    def _is_aws_configured(self) -> bool:
        return bool(settings.AWS_REGION)
    
    def _get_or_create_queue(self, queue_name: str, is_dlq: bool = False) -> Optional[str]:
        """Get existing queue URL or create new queue"""
        try:
            # Try to get existing queue
            response = self._sqs_client.get_queue_url(QueueName=queue_name)
            return response['QueueUrl']
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                # Queue doesn't exist, create it
                return self._create_queue(queue_name, is_dlq)
            else:
                print(f"Error getting queue {queue_name}: {e}")
                return None
    
    def _create_queue(self, queue_name: str, is_dlq: bool = False) -> Optional[str]:
        """Create a new SQS queue with appropriate settings"""
        try:
            attributes = {
                'VisibilityTimeoutSeconds': '300',  # 5 minutes
                'MessageRetentionPeriod': '1209600',  # 14 days
                'ReceiveMessageWaitTimeSeconds': '20',  # Long polling
            }
            
            if not is_dlq:
                # Main queue with DLQ configuration
                attributes.update({
                    'RedrivePolicy': json.dumps({
                        'deadLetterTargetArn': f"arn:aws:sqs:{settings.AWS_REGION}:{self._get_account_id()}:{queue_name}-dlq",
                        'maxReceiveCount': 3
                    })
                })
            
            response = self._sqs_client.create_queue(
                QueueName=queue_name,
                Attributes=attributes
            )
            
            print(f"✅ Created SQS queue: {queue_name}")
            return response['QueueUrl']
            
        except Exception as e:
            print(f"❌ Failed to create queue {queue_name}: {e}")
            return None
    
    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        try:
            sts = boto3.client('sts')
            return sts.get_caller_identity()['Account']
        except:
            return "123456789012"  # Fallback
    
    def is_available(self) -> bool:
        """Check if queue service is available.

        An unset queue URL is an empty string (not None), so we must check
        truthiness — otherwise enqueue/dequeue try SQS with an empty URL and
        silently fall back to a local queue while reporting "Ready".
        """
        return self._sqs_client is not None and bool(self._queue_url)
    
    async def enqueue_job(
        self,
        job_type: str,
        user_id: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        delay_seconds: int = 0,
        job_id: Optional[str] = None
    ) -> str:
        """
        Add a job to the queue

        Args:
            job_type: Type of job (e.g., 'video_localization', 'draft_creation')
            user_id: User identifier
            payload: Job data
            priority: Job priority level
            delay_seconds: Delay before job becomes available
            job_id: Use an existing job ID (e.g. from job_service.create_job) so the
                    worker updates the same record the frontend is polling. If omitted,
                    a new ID is generated.

        Returns:
            str: Job ID
        """
        job_id = job_id or str(uuid.uuid4())
        
        job = QueueJob(
            job_id=job_id,
            job_type=job_type,
            user_id=user_id,
            payload=payload,
            priority=priority
        )
        
        if self.is_available():
            # Use SQS
            success = await self._enqueue_sqs(job, delay_seconds)
            if success:
                return job_id
        
        # Fallback to local queue
        self._enqueue_local(job)
        return job_id
    
    async def _enqueue_sqs(self, job: QueueJob, delay_seconds: int = 0) -> bool:
        """Enqueue job to AWS SQS"""
        try:
            message_body = json.dumps(asdict(job))
            
            # Message attributes for filtering and routing
            message_attributes = {
                'JobType': {
                    'StringValue': job.job_type,
                    'DataType': 'String'
                },
                'Priority': {
                    'StringValue': job.priority.value,
                    'DataType': 'String'
                },
                'UserId': {
                    'StringValue': job.user_id,
                    'DataType': 'String'
                }
            }
            
            response = self._sqs_client.send_message(
                QueueUrl=self._queue_url,
                MessageBody=message_body,
                MessageAttributes=message_attributes,
                DelaySeconds=delay_seconds
            )
            
            print(f"✅ Job {job.job_id} enqueued to SQS")
            return True
            
        except Exception as e:
            print(f"❌ Failed to enqueue job {job.job_id} to SQS: {e}")
            return False
    
    def _enqueue_local(self, job: QueueJob):
        """Enqueue job to local in-memory queue"""
        self._local_queue.append(job)
        # Sort by priority (urgent first)
        priority_order = {
            JobPriority.URGENT: 0,
            JobPriority.HIGH: 1,
            JobPriority.NORMAL: 2,
            JobPriority.LOW: 3
        }
        self._local_queue.sort(key=lambda j: priority_order[j.priority])
        print(f"✅ Job {job.job_id} enqueued locally")
    
    async def dequeue_job(self, wait_time_seconds: int = 20) -> Optional[QueueJob]:
        """
        Get next job from queue
        
        Args:
            wait_time_seconds: How long to wait for messages (SQS long polling)
            
        Returns:
            QueueJob or None if no jobs available
        """
        if self.is_available():
            return await self._dequeue_sqs(wait_time_seconds)
        else:
            return self._dequeue_local()
    
    async def _dequeue_sqs(self, wait_time_seconds: int) -> Optional[QueueJob]:
        """Dequeue job from AWS SQS"""
        try:
            response = self._sqs_client.receive_message(
                QueueUrl=self._queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            if not messages:
                return None
            
            message = messages[0]
            job_data = json.loads(message['Body'])
            
            # Handle Lambda-generated messages
            if 'jobId' in job_data:
                job = QueueJob(
                    job_id=job_data['jobId'],
                    job_type=job_data.get('jobType', 'video_processing'),
                    user_id=job_data.get('userId', 'unknown'),
                    payload=job_data
                )
            else:
                # Handle QueueJob-formatted messages
                job = QueueJob(**job_data)
            
            # Store receipt handle for deletion
            job.receipt_handle = message['ReceiptHandle']
            
            return job
            
        except Exception as e:
            print(f"❌ Failed to dequeue from SQS: {e}")
            return None
    
    def _dequeue_local(self) -> Optional[QueueJob]:
        """Dequeue job from local queue"""
        if self._local_queue:
            return self._local_queue.pop(0)
        return None
    
    async def complete_job(self, job: QueueJob) -> bool:
        """
        Mark job as completed and remove from queue
        
        Args:
            job: Completed job
            
        Returns:
            bool: True if successful
        """
        if self.is_available() and hasattr(job, 'receipt_handle'):
            return await self._complete_sqs_job(job)
        
        # Local jobs are already removed when dequeued
        return True
    
    async def _complete_sqs_job(self, job: QueueJob) -> bool:
        """Complete SQS job by deleting message"""
        try:
            self._sqs_client.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=job.receipt_handle
            )
            print(f"✅ Job {job.job_id} completed and removed from SQS")
            return True
            
        except Exception as e:
            print(f"❌ Failed to complete SQS job {job.job_id}: {e}")
            return False
    
    async def retry_job(self, job: QueueJob, delay_seconds: int = None) -> bool:
        """
        Retry a failed job with exponential backoff
        
        Args:
            job: Failed job to retry
            delay_seconds: Custom delay, or None for exponential backoff
            
        Returns:
            bool: True if job was requeued for retry
        """
        if job.retry_count >= job.max_retries:
            print(f"❌ Job {job.job_id} exceeded max retries ({job.max_retries})")
            return False
        
        job.retry_count += 1
        
        # Exponential backoff: 30s, 60s, 120s, 240s...
        if delay_seconds is None:
            delay_seconds = min(30 * (2 ** (job.retry_count - 1)), 300)  # Max 5 minutes
        
        print(f"🔄 Retrying job {job.job_id} (attempt {job.retry_count}/{job.max_retries}) in {delay_seconds}s")
        
        # Re-enqueue with delay
        await self.enqueue_job(
            job_type=job.job_type,
            user_id=job.user_id,
            payload=job.payload,
            priority=job.priority,
            delay_seconds=delay_seconds
        )
        
        return True
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics
        
        Returns:
            dict with queue metrics
        """
        if self.is_available():
            return self._get_sqs_stats()
        else:
            return {
                "queue_type": "local",
                "approximate_messages": len(self._local_queue),
                "approximate_messages_not_visible": 0,
                "approximate_messages_delayed": 0
            }
    
    def _get_sqs_stats(self) -> Dict[str, Any]:
        """Get SQS queue statistics"""
        try:
            response = self._sqs_client.get_queue_attributes(
                QueueUrl=self._queue_url,
                AttributeNames=[
                    'ApproximateNumberOfMessages',
                    'ApproximateNumberOfMessagesNotVisible',
                    'ApproximateNumberOfMessagesDelayed'
                ]
            )
            
            attributes = response['Attributes']
            return {
                "queue_type": "sqs",
                "queue_url": self._queue_url,
                "approximate_messages": int(attributes.get('ApproximateNumberOfMessages', 0)),
                "approximate_messages_not_visible": int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                "approximate_messages_delayed": int(attributes.get('ApproximateNumberOfMessagesDelayed', 0))
            }
            
        except Exception as e:
            return {
                "queue_type": "sqs",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check queue service health
        
        Returns:
            dict with health information
        """
        if self.is_available():
            stats = self.get_queue_stats()
            return {
                "status": "healthy",
                "backend": "sqs",
                "queue_url": self._queue_url,
                "stats": stats
            }
        else:
            return {
                "status": "degraded",
                "backend": "local",
                "message": "Using local in-memory queue (not suitable for production)",
                "local_queue_size": len(self._local_queue)
            }


# Singleton instance
queue_service = QueueService()