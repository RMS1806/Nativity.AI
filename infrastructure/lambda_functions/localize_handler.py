"""
Lambda Function: Localize Handler
Starts video localization by triggering Step Functions workflow
"""

import json
import boto3
import uuid
import os
from datetime import datetime
from typing import Dict, Any

# Initialize AWS clients
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
stepfunctions_client = boto3.client('stepfunctions')

# Environment variables
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
STEP_FUNCTION_ARN = os.environ['STEP_FUNCTION_ARN']

# DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Start video localization workflow
    
    Expected input:
    {
        "file_key": "uploads/video.mp4",
        "target_language": "hindi"
    }
    """
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        file_key = body.get('file_key')
        target_language = body.get('target_language', 'hindi')
        
        # Extract user ID from JWT (if available)
        user_id = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_id = event['requestContext']['authorizer'].get('sub')
        
        if not file_key:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'file_key is required'
                })
            }
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Create job record in DynamoDB
        if user_id:
            table.put_item(
                Item={
                    'PK': f"USER#{user_id}",
                    'SK': f"VIDEO#{timestamp}",
                    'job_id': job_id,
                    'user_id': user_id,
                    'target_language': target_language,
                    'input_file': file_key,
                    'status': 'pending',
                    'progress': 0,
                    'message': 'Job queued for processing...',
                    'created_at': timestamp
                }
            )
        
        # Start Step Functions workflow
        workflow_input = {
            'job_id': job_id,
            'user_id': user_id,
            'file_key': file_key,
            'target_language': target_language,
            'created_at': timestamp
        }
        
        stepfunctions_client.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=f"localization-{job_id}",
            input=json.dumps(workflow_input)
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'job_id': job_id,
                'status': 'queued',
                'message': 'Video localization started. Poll /api/video/job/{job_id} for status.'
            })
        }
        
    except Exception as e:
        print(f"Error in localize_handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': 'Failed to start localization',
                'message': str(e)
            })
        }