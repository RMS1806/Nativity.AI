"""
AWS Lambda function for job status management
Handles job status updates and batch job retrieval
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key, Attr

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Environment variables
JOBS_TABLE_NAME = os.environ['JOBS_TABLE_NAME']
USERS_TABLE_NAME = os.environ['USERS_TABLE_NAME']

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for job status management
    
    Handles different actions:
    - update_status: Update job status and result
    - get_pending_jobs: Get pending jobs for batch processing
    - get_job_status: Get current job status
    - cleanup_old_jobs: Clean up old completed jobs
    """
    
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        action = event.get('action', 'update_status')
        
        if action == 'update_status':
            return update_job_status(event)
        elif action == 'get_pending_jobs':
            return get_pending_jobs(event)
        elif action == 'get_job_status':
            return get_job_status(event)
        elif action == 'cleanup_old_jobs':
            return cleanup_old_jobs(event)
        else:
            raise ValueError(f"Unknown action: {action}")
            
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise

def update_job_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Update job status and result in DynamoDB"""
    
    job_id = event.get('jobId')
    status = event.get('status')
    result = event.get('result')
    error = event.get('error')
    
    if not job_id or not status:
        raise ValueError("jobId and status are required")
    
    jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
    
    # Get current job to check if it exists
    try:
        response = jobs_table.get_item(Key={'jobId': job_id})
        if 'Item' not in response:
            raise ValueError(f"Job not found: {job_id}")
        
        current_job = response['Item']
        
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        raise
    
    # Prepare update expression
    update_expression = "SET #status = :status, updatedAt = :updated_at"
    expression_attribute_names = {'#status': 'status'}
    expression_attribute_values = {
        ':status': status,
        ':updated_at': datetime.utcnow().isoformat()
    }
    
    # Add result if provided
    if result:
        update_expression += ", #result = :result"
        expression_attribute_names['#result'] = 'result'
        expression_attribute_values[':result'] = result
    
    # Add error if provided
    if error:
        update_expression += ", #error = :error"
        expression_attribute_names['#error'] = 'error'
        expression_attribute_values[':error'] = error
    
    # Add completion timestamp for completed/failed jobs
    if status in ['completed', 'failed']:
        update_expression += ", completedAt = :completed_at"
        expression_attribute_values[':completed_at'] = datetime.utcnow().isoformat()
        
        # Calculate processing duration
        created_at = datetime.fromisoformat(current_job['createdAt'].replace('Z', '+00:00'))
        completed_at = datetime.utcnow()
        duration = (completed_at - created_at).total_seconds()
        
        update_expression += ", processingDuration = :duration"
        expression_attribute_values[':duration'] = duration
    
    # Update the job
    try:
        jobs_table.update_item(
            Key={'jobId': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(f"Updated job {job_id} status to {status}")
        
        # Update user statistics
        update_user_stats(current_job['userId'], status)
        
        # Send notification for completed/failed jobs
        if status in ['completed', 'failed']:
            send_job_notification(current_job, status, result, error)
        
        return {
            'statusCode': 200,
            'jobId': job_id,
            'status': status,
            'updatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {str(e)}")
        raise

def get_pending_jobs(event: Dict[str, Any]) -> Dict[str, Any]:
    """Get pending jobs for batch processing"""
    
    limit = event.get('limit', 10)
    job_type = event.get('jobType')  # Optional filter by job type
    
    jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
    
    try:
        # Query for pending jobs
        filter_expression = Attr('status').eq('pending')
        
        if job_type:
            filter_expression = filter_expression & Attr('jobType').eq(job_type)
        
        response = jobs_table.scan(
            FilterExpression=filter_expression,
            Limit=limit,
            ProjectionExpression='jobId, userId, videoUrl, jobType, createdAt'
        )
        
        jobs = response.get('Items', [])
        
        # Sort by creation time (oldest first)
        jobs.sort(key=lambda x: x['createdAt'])
        
        logger.info(f"Found {len(jobs)} pending jobs")
        
        return {
            'statusCode': 200,
            'jobs': jobs,
            'count': len(jobs)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving pending jobs: {str(e)}")
        raise

def get_job_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Get current job status and details"""
    
    job_id = event.get('jobId')
    user_id = event.get('userId')  # Optional for authorization
    
    if not job_id:
        raise ValueError("jobId is required")
    
    jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
    
    try:
        response = jobs_table.get_item(Key={'jobId': job_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'error': f"Job not found: {job_id}"
            }
        
        job = response['Item']
        
        # Check authorization if user_id provided
        if user_id and job.get('userId') != user_id:
            return {
                'statusCode': 403,
                'error': "Access denied"
            }
        
        # Remove sensitive information
        safe_job = {
            'jobId': job['jobId'],
            'status': job['status'],
            'jobType': job.get('jobType', 'standard'),
            'createdAt': job['createdAt'],
            'updatedAt': job['updatedAt']
        }
        
        # Add result if completed
        if job.get('result'):
            safe_job['result'] = job['result']
        
        # Add error if failed
        if job.get('error'):
            safe_job['error'] = job['error']
        
        # Add completion info if available
        if job.get('completedAt'):
            safe_job['completedAt'] = job['completedAt']
            safe_job['processingDuration'] = job.get('processingDuration')
        
        return {
            'statusCode': 200,
            'job': safe_job
        }
        
    except Exception as e:
        logger.error(f"Error retrieving job status {job_id}: {str(e)}")
        raise

def cleanup_old_jobs(event: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up old completed jobs to manage storage costs"""
    
    days_to_keep = event.get('daysToKeep', 30)
    dry_run = event.get('dryRun', True)
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    cutoff_iso = cutoff_date.isoformat()
    
    jobs_table = dynamodb.Table(JOBS_TABLE_NAME)
    
    try:
        # Scan for old completed jobs
        response = jobs_table.scan(
            FilterExpression=Attr('status').is_in(['completed', 'failed']) & 
                           Attr('completedAt').lt(cutoff_iso),
            ProjectionExpression='jobId, userId, completedAt, status'
        )
        
        old_jobs = response.get('Items', [])
        
        deleted_count = 0
        
        if not dry_run:
            # Delete old jobs in batches
            with jobs_table.batch_writer() as batch:
                for job in old_jobs:
                    batch.delete_item(Key={'jobId': job['jobId']})
                    deleted_count += 1
        
        logger.info(f"{'Would delete' if dry_run else 'Deleted'} {len(old_jobs)} old jobs")
        
        return {
            'statusCode': 200,
            'oldJobsFound': len(old_jobs),
            'deletedCount': deleted_count,
            'dryRun': dry_run,
            'cutoffDate': cutoff_iso
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {str(e)}")
        raise

def update_user_stats(user_id: str, job_status: str):
    """Update user statistics based on job completion"""
    
    users_table = dynamodb.Table(USERS_TABLE_NAME)
    
    try:
        # Get current user stats
        response = users_table.get_item(Key={'userId': user_id})
        
        if 'Item' not in response:
            # Create user record if it doesn't exist
            user_item = {
                'userId': user_id,
                'createdAt': datetime.utcnow().isoformat(),
                'totalJobs': 0,
                'completedJobs': 0,
                'failedJobs': 0
            }
            users_table.put_item(Item=user_item)
        
        # Update statistics based on job status
        if job_status == 'completed':
            users_table.update_item(
                Key={'userId': user_id},
                UpdateExpression="ADD completedJobs :inc SET lastJobAt = :timestamp",
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
        elif job_status == 'failed':
            users_table.update_item(
                Key={'userId': user_id},
                UpdateExpression="ADD failedJobs :inc SET lastJobAt = :timestamp",
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
        
        # Always increment total jobs counter
        users_table.update_item(
            Key={'userId': user_id},
            UpdateExpression="ADD totalJobs :inc",
            ExpressionAttributeValues={':inc': 1}
        )
        
        logger.info(f"Updated user stats for {user_id}")
        
    except Exception as e:
        logger.error(f"Error updating user stats for {user_id}: {str(e)}")
        # Don't raise - user stats update shouldn't fail the main operation

def send_job_notification(job: Dict[str, Any], status: str, result: Dict[str, Any] = None, error: Dict[str, Any] = None):
    """Send job completion notification via SNS"""
    
    try:
        # This would typically send to a user notification topic
        # For now, we'll just log the notification
        
        notification = {
            'jobId': job['jobId'],
            'userId': job['userId'],
            'status': status,
            'jobType': job.get('jobType', 'standard'),
            'completedAt': datetime.utcnow().isoformat()
        }
        
        if result:
            notification['hasResult'] = True
        
        if error:
            notification['error'] = error
        
        logger.info(f"Job notification: {json.dumps(notification)}")
        
        # In a real implementation, you would send this to SNS:
        # sns.publish(
        #     TopicArn=USER_NOTIFICATIONS_TOPIC_ARN,
        #     Message=json.dumps(notification),
        #     Subject=f"Job {status}: {job['jobId']}"
        # )
        
    except Exception as e:
        logger.error(f"Error sending job notification: {str(e)}")
        # Don't raise - notification failure shouldn't fail the main operation