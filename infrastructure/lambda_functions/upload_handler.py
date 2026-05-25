"""
Lambda Function: Upload Handler
Generates presigned URLs for S3 video uploads
"""

import json
import boto3
import os
from datetime import datetime
from typing import Dict, Any

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
S3_BUCKET = os.environ['S3_BUCKET_NAME']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']

# DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Generate presigned URL for S3 upload
    
    Expected input:
    {
        "file_name": "video.mp4",
        "content_type": "video/mp4"
    }
    """
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        file_name = body.get('file_name')
        content_type = body.get('content_type', 'video/mp4')
        
        if not file_name:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'file_name is required'
                })
            }
        
        # Generate unique file key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_key = f"uploads/{timestamp}_{file_name}"
        
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': file_key,
                'ContentType': content_type
            },
            ExpiresIn=3600  # 1 hour
        )
        
        # Log upload request (optional)
        try:
            table.put_item(
                Item={
                    'PK': f"UPLOAD#{timestamp}",
                    'SK': f"FILE#{file_key}",
                    'file_name': file_name,
                    'file_key': file_key,
                    'content_type': content_type,
                    'created_at': timestamp,
                    'status': 'pending'
                }
            )
        except Exception as e:
            print(f"Warning: Could not log upload request: {e}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'upload_url': presigned_url,
                'file_key': file_key,
                'bucket': S3_BUCKET,
                'expires_in': 3600
            })
        }
        
    except Exception as e:
        print(f"Error in upload_handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }