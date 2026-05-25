"""
Lambda Function: Status Handler
Retrieves job status from DynamoDB and Redis
"""

import json
import boto3
import redis
import os
from typing import Dict, Any, Optional

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
REDIS_ENDPOINT = os.environ.get('REDIS_ENDPOINT')

# DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE)

# Redis client (with fallback)
redis_client = None
if REDIS_ENDPOINT:
    try:
        redis_client = redis.Redis(host=REDIS_ENDPOINT, port=6379, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        print(f"Redis connection failed: {e}")
        redis_client = None


def get_job_from_redis(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status from Redis"""
    if not redis_client:
        return None
    
    try:
        job_data = redis_client.get(f"job:{job_id}")
        if job_data:
            return json.loads(job_data)
    except Exception as e:
        print(f"Redis error: {e}")
    
    return None


def get_job_from_dynamodb(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status from DynamoDB"""
    try:
        # Scan for job by job_id (in production, consider GSI)
        response = table.scan(
            FilterExpression='job_id = :job_id',
            ExpressionAttributeValues={':job_id': job_id},
            Limit=1
        )
        
        items = response.get('Items', [])
        if items:
            item = items[0]
            
            # Parse JSON fields
            if 'draft_segments' in item:
                try:
                    item['draft_segments'] = json.loads(item['draft_segments'])
                except:
                    pass
            
            if 'cultural_report' in item:
                try:
                    item['cultural_report'] = json.loads(item['cultural_report'])
                except:
                    pass
            
            return item
    except Exception as e:
        print(f"DynamoDB error: {e}")
    
    return None


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Get job status by job_id
    
    Expected path parameter: job_id
    """
    try:
        # Extract job_id from path parameters
        job_id = event.get('pathParameters', {}).get('job_id')
        
        if not job_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'job_id is required'
                })
            }
        
        # Try Redis first (fast)
        job_data = get_job_from_redis(job_id)
        
        # Fallback to DynamoDB
        if not job_data:
            job_data = get_job_from_dynamodb(job_id)
        
        if not job_data:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Job not found'
                })
            }
        
        # Format response
        response_data = {
            'job_id': job_data.get('job_id'),
            'status': job_data.get('status', 'unknown'),
            'progress': job_data.get('progress', 0),
            'message': job_data.get('message', ''),
            'input_file': job_data.get('input_file', ''),
            'target_language': job_data.get('target_language', ''),
            'created_at': job_data.get('created_at', ''),
            'updated_at': job_data.get('updated_at', '')
        }
        
        # Add output file if complete
        if job_data.get('status') == 'complete':
            if job_data.get('output_url'):
                response_data['output_file'] = job_data['output_url']
            if job_data.get('whatsapp_url'):
                response_data['whatsapp_url'] = job_data['whatsapp_url']
            if job_data.get('draft_segments'):
                response_data['results'] = {
                    'segments': job_data['draft_segments'],
                    'cultural_report': job_data.get('cultural_report'),
                    'segments_count': job_data.get('segments_count', 0)
                }
        
        # Add error if failed
        if job_data.get('status') == 'failed':
            response_data['error'] = job_data.get('error_message', 'Processing failed')
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        print(f"Error in status_handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }