"""
AWS Lambda function for video processing orchestration
Handles video upload triggers and job routing
"""

import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
s3 = boto3.client('s3')

# Environment variables
JOBS_TABLE_NAME = os.environ['JOBS_TABLE_NAME']
VIDEO_PROCESSING_QUEUE_URL = os.environ['VIDEO_PROCESSING_QUEUE_URL']
HIGH_PRIORITY_QUEUE_URL = os.environ['HIGH_PRIORITY_QUEUE_URL']
DRAFT_CREATION_QUEUE_URL = os.environ['DRAFT_CREATION_QUEUE_URL']

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for video processing
    
    Handles different actions:
    - validate: Validate input parameters
    - process_draft: Process draft video jobs
    - process_high_priority: Process high priority jobs
    - process_standard: Process standard jobs
    - s3_trigger: Handle S3 upload events
    """
    
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle S3 trigger events
        if 'Records' in event:
            return handle_s3_trigger(event)
        
        # Handle Step Functions actions
        action = event.get('action', 'process_standard')
        
        if action == 'validate':
            return validate_input(event)
        elif action == 'process_draft':
            return process_draft(event)
        elif action == 'process_high_priority':
            return process_high_priority(event)
        elif action == 'process_standard':
            return process_standard(event)
        else:
            raise ValueError(f"Unknown action: {action}")
            
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise

def handle_s3_trigger(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle S3 upload trigger events"""
    
    results = []
    
    for record in event['Records']:
        if record['eventSource'] == 'aws:s3':
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            logger.info(f"Processing S3 upload: s3://{bucket}/{key}")
            
            # Extract user ID and job type from S3 key structure
            # Expected format: uploads/videos/{userId}/{jobType}/{filename}
            path_parts = key.split('/')
            
            if len(path_parts) >= 4 and path_parts[0] == 'uploads' and path_parts[1] == 'videos':
                user_id = path_parts[2]
                job_type = path_parts[3] if path_parts[3] in ['draft', 'high_priority', 'standard'] else 'standard'
                
                # Create job record
                job_id = create_job_record(user_id, f"s3://{bucket}/{key}", job_type)
                
                # Queue job for processing
                queue_job(job_id, user_id, f"s3://{bucket}/{key}", job_type)
                
                results.append({
                    'jobId': job_id,
                    'status': 'queued',
                    'videoUrl': f"s3://{bucket}/{key}"
                })
            else:
                logger.warning(f"Skipping file with unexpected path structure: {key}")
    
    return {
        'statusCode': 200,
        'results': results
    }

def validate_input(event: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input parameters for job processing"""
    
    required_fields = ['jobId', 'videoUrl', 'userId']
    
    for field in required_fields:
        if field not in event:
            raise ValueError(f"Missing required field: {field}")
    
    job_id = event['jobId']
    video_url = event['videoUrl']
    user_id = event['userId']
    
    # Validate video URL format
    if not (video_url.startswith('s3://') or video_url.startswith('http')):
        raise ValueError(f"Invalid video URL format: {video_url}")
    
    # Check if job exists in DynamoDB
    jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
    
    try:
        response = jobs_table.get_item(Key={'jobId': job_id})
        if 'Item' not in response:
            raise ValueError(f"Job not found: {job_id}")
        
        job = response['Item']
        
        # Validate job belongs to user
        if job.get('userId') != user_id:
            raise ValueError(f"Job {job_id} does not belong to user {user_id}")
        
        # Check job status
        if job.get('status') not in ['pending', 'queued']:
            raise ValueError(f"Job {job_id} is not in a processable state: {job.get('status')}")
        
    except Exception as e:
        logger.error(f"Error validating job {job_id}: {str(e)}")
        raise
    
    return {
        'jobId': job_id,
        'videoUrl': video_url,
        'userId': user_id,
        'jobType': job.get('jobType', 'standard'),
        'status': 'validated'
    }

def process_draft(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process draft video jobs (fast, lower quality)"""
    
    job_id = event['jobId']
    video_url = event['videoUrl']
    user_id = event['userId']
    
    logger.info(f"Processing draft job {job_id} for user {user_id}")
    
    # Update job status to processing
    update_job_status(job_id, 'processing', {'processingType': 'draft'})
    
    # Simulate draft processing (in real implementation, this would call AI services)
    result = {
        'jobId': job_id,
        'userId': user_id,
        'processingType': 'draft',
        'result': {
            'transcript': 'Draft transcript generated quickly...',
            'summary': 'Quick summary of the video content.',
            'keyPoints': ['Point 1', 'Point 2', 'Point 3'],
            'processingTime': 30,  # seconds
            'quality': 'draft'
        },
        'completedAt': datetime.utcnow().isoformat()
    }
    
    logger.info(f"Draft processing completed for job {job_id}")
    
    return result

def process_high_priority(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process high priority video jobs (fast, high quality)"""
    
    job_id = event['jobId']
    video_url = event['videoUrl']
    user_id = event['userId']
    
    logger.info(f"Processing high priority job {job_id} for user {user_id}")
    
    # Update job status to processing
    update_job_status(job_id, 'processing', {'processingType': 'high_priority'})
    
    # Simulate high priority processing
    result = {
        'jobId': job_id,
        'userId': user_id,
        'processingType': 'high_priority',
        'result': {
            'transcript': 'High quality transcript with timestamps...',
            'summary': 'Detailed summary with key insights.',
            'keyPoints': ['Detailed Point 1', 'Detailed Point 2', 'Detailed Point 3'],
            'sentiment': 'positive',
            'topics': ['AI', 'Technology', 'Innovation'],
            'processingTime': 300,  # seconds
            'quality': 'high'
        },
        'completedAt': datetime.utcnow().isoformat()
    }
    
    logger.info(f"High priority processing completed for job {job_id}")
    
    return result

def process_standard(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process standard video jobs (balanced speed and quality)"""
    
    job_id = event['jobId']
    video_url = event['videoUrl']
    user_id = event['userId']
    
    logger.info(f"Processing standard job {job_id} for user {user_id}")
    
    # Update job status to processing
    update_job_status(job_id, 'processing', {'processingType': 'standard'})
    
    # Simulate standard processing
    result = {
        'jobId': job_id,
        'userId': user_id,
        'processingType': 'standard',
        'result': {
            'transcript': 'Complete transcript with speaker identification...',
            'summary': 'Comprehensive summary with detailed analysis.',
            'keyPoints': ['Key Point 1', 'Key Point 2', 'Key Point 3', 'Key Point 4'],
            'sentiment': 'neutral',
            'topics': ['Business', 'Strategy', 'Growth'],
            'actionItems': ['Action 1', 'Action 2'],
            'processingTime': 600,  # seconds
            'quality': 'standard'
        },
        'completedAt': datetime.utcnow().isoformat()
    }
    
    logger.info(f"Standard processing completed for job {job_id}")
    
    return result

def create_job_record(user_id: str, video_url: str, job_type: str) -> str:
    """Create a new job record in DynamoDB"""
    
    import uuid
    
    job_id = str(uuid.uuid4())
    
    jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
    
    job_item = {
        'jobId': job_id,
        'userId': user_id,
        'videoUrl': video_url,
        'jobType': job_type,
        'status': 'pending',
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat()
    }
    
    jobs_table.put_item(Item=job_item)
    
    logger.info(f"Created job record: {job_id}")
    
    return job_id

def queue_job(job_id: str, user_id: str, video_url: str, job_type: str):
    """Queue job for processing based on job type"""
    
    # Select appropriate queue based on job type
    if job_type == 'draft':
        queue_url = DRAFT_CREATION_QUEUE_URL
    elif job_type == 'high_priority':
        queue_url = HIGH_PRIORITY_QUEUE_URL
    else:
        queue_url = VIDEO_PROCESSING_QUEUE_URL
    
    message = {
        'jobId': job_id,
        'userId': user_id,
        'videoUrl': video_url,
        'jobType': job_type,
        'queuedAt': datetime.utcnow().isoformat()
    }
    
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
        MessageAttributes={
            'jobType': {
                'StringValue': job_type,
                'DataType': 'String'
            },
            'userId': {
                'StringValue': user_id,
                'DataType': 'String'
            }
        }
    )
    
    # Update job status to queued
    update_job_status(job_id, 'queued', {'queueUrl': queue_url})
    
    logger.info(f"Queued job {job_id} in {queue_url}")

def update_job_status(job_id: str, status: str, additional_data: Dict[str, Any] = None):
    """Update job status in DynamoDB"""
    
    jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
    
    update_expression = "SET #status = :status, updatedAt = :updated_at"
    expression_attribute_names = {'#status': 'status'}
    expression_attribute_values = {
        ':status': status,
        ':updated_at': datetime.utcnow().isoformat()
    }
    
    if additional_data:
        for key, value in additional_data.items():
            update_expression += f", #{key} = :{key}"
            expression_attribute_names[f'#{key}'] = key
            expression_attribute_values[f':{key}'] = value
    
    jobs_table.update_item(
        Key={'jobId': job_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values
    )
    
    logger.info(f"Updated job {job_id} status to {status}")