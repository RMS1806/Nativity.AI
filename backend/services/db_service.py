"""
DynamoDB Service for Nativity.ai
Handles persistent storage of video localization history

Table Schema:
    - PK: USER#<user_id>
    - SK: VIDEO#<iso_timestamp>
    
Each item stores:
    - job_id: Unique job identifier
    - status: Job status (complete, failed, etc.)
    - target_language: Language code
    - input_file: Original S3 key
    - output_url: Presigned download URL
    - cultural_report: Gemini's cultural adaptation report
    - created_at: ISO timestamp
"""

import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from config import settings


TABLE_NAME = "NativityProduction"


class DBService:
    """DynamoDB service for storing and retrieving video history"""
    
    def __init__(self):
        self._table = None
        self._dynamodb = None
    
    @property
    def dynamodb(self):
        """Lazy initialization of DynamoDB resource"""
        if self._dynamodb is None and self.is_configured():
            self._dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        return self._dynamodb
    
    @property
    def table(self):
        """Lazy initialization of DynamoDB table"""
        if self._table is None and self.dynamodb:
            self._table = self.dynamodb.Table(TABLE_NAME)
        return self._table
    
    def is_configured(self) -> bool:
        """Check if AWS credentials are configured"""
        return bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
    
    def save_video(
        self,
        user_id: str,
        job_id: str,
        target_language: str,
        input_file: str,
        status: str = "complete",
        output_url: Optional[str] = None,
        whatsapp_url: Optional[str] = None,
        file_size_mb: Optional[float] = None,
        cultural_report: Optional[Dict[str, Any]] = None,
        segments_count: Optional[int] = None,
        draft_segments: Optional[List[Dict[str, Any]]] = None,
        output_s3_key: Optional[str] = None,
        subtitle_s3_key: Optional[str] = None,
        words_localized: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save a video localization job to user's history.
        
        Args:
            user_id: Clerk user ID (from JWT 'sub' claim)
            job_id: Unique job identifier
            target_language: Language code (hindi, tamil, etc.)
            input_file: Original S3 key
            status: Job status (processing, needs_review, complete, failed)
            output_url: Presigned download URL
            whatsapp_url: WhatsApp-optimized version URL
            file_size_mb: Output file size in MB
            cultural_report: Gemini's cultural adaptation report
            segments_count: Number of audio segments generated
            draft_segments: List of segment dicts for human review
            output_s3_key: S3 key for output file (for URL regeneration)
            
        Returns:
            dict with success status
        """
        if not self.table:
            return {"error": "DynamoDB not configured"}
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Build item with required fields
        item = {
            'PK': f"USER#{user_id}",
            'SK': f"VIDEO#{timestamp}",
            'job_id': job_id,
            'user_id': user_id,
            'target_language': target_language,
            'input_file': input_file,
            'status': status,
            'created_at': timestamp,
        }
        
        # Add optional fields if provided
        if output_url:
            item['output_url'] = output_url
        if output_s3_key:
            item['output_s3_key'] = output_s3_key
        if subtitle_s3_key:
            item['subtitle_s3_key'] = subtitle_s3_key
        if words_localized is not None:
            item['words_localized'] = words_localized
        if whatsapp_url:
            item['whatsapp_url'] = whatsapp_url
        if file_size_mb is not None:
            item['file_size_mb'] = str(file_size_mb)  # DynamoDB prefers strings for decimals
        if cultural_report:
            item['cultural_report'] = json.dumps(cultural_report)
        if segments_count is not None:
            item['segments_count'] = segments_count
        if draft_segments:
            item['draft_segments'] = json.dumps(draft_segments)
        
        try:
            self.table.put_item(Item=item)
            return {
                "success": True,
                "pk": item['PK'],
                "sk": item['SK']
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def update_job_segments(
        self,
        user_id: str,
        job_id: str,
        segments: List[Dict[str, Any]],
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the segments for a job (after human review/editing).
        
        Args:
            user_id: Clerk user ID
            job_id: Job ID to update
            segments: Updated list of segment dicts
            status: Optional new status to set
            
        Returns:
            dict with success status or error
        """
        if not self.table:
            return {"error": "DynamoDB not configured"}
        
        # First, find the item by job_id
        video = self.get_video_by_job_id(user_id, job_id)
        if "error" in video:
            return video
        if not video.get("video"):
            return {"error": "Video not found"}
        
        pk = video["video"]["PK"]
        sk = video["video"]["SK"]
        
        # Build update expression
        update_expr = "SET draft_segments = :segments, updated_at = :updated"
        expr_values = {
            ":segments": json.dumps(segments),
            ":updated": datetime.utcnow().isoformat() + "Z"
        }
        
        if status:
            update_expr += ", #status = :status"
            expr_values[":status"] = status
            expr_names = {"#status": "status"}
        else:
            expr_names = None
        
        try:
            update_kwargs = {
                "Key": {"PK": pk, "SK": sk},
                "UpdateExpression": update_expr,
                "ExpressionAttributeValues": expr_values
            }
            if expr_names:
                update_kwargs["ExpressionAttributeNames"] = expr_names
            
            self.table.update_item(**update_kwargs)
            return {"success": True, "job_id": job_id}
        except ClientError as e:
            return {"error": str(e)}
    
    def update_job_status(
        self,
        user_id: str,
        job_id: str,
        status: str,
        output_url: Optional[str] = None,
        output_s3_key: Optional[str] = None,
        subtitle_s3_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of a job and optionally set output URL.
        
        Args:
            user_id: Clerk user ID
            job_id: Job ID to update
            status: New status
            output_url: Optional output URL to set
            output_s3_key: Optional S3 key for output
            
        Returns:
            dict with success status or error
        """
        if not self.table:
            return {"error": "DynamoDB not configured"}
        
        # Find the item by job_id
        video = self.get_video_by_job_id(user_id, job_id)
        if "error" in video:
            return video
        if not video.get("video"):
            return {"error": "Video not found"}
        
        pk = video["video"]["PK"]
        sk = video["video"]["SK"]
        
        # Build update expression
        update_expr = "SET #status = :status, updated_at = :updated"
        expr_values = {
            ":status": status,
            ":updated": datetime.utcnow().isoformat() + "Z"
        }
        expr_names = {"#status": "status"}
        
        if output_url:
            update_expr += ", output_url = :output_url"
            expr_values[":output_url"] = output_url
        if output_s3_key:
            update_expr += ", output_s3_key = :output_s3_key"
            expr_values[":output_s3_key"] = output_s3_key
        if subtitle_s3_key:
            update_expr += ", subtitle_s3_key = :subtitle_s3_key"
            expr_values[":subtitle_s3_key"] = subtitle_s3_key
        
        try:
            self.table.update_item(
                Key={"PK": pk, "SK": sk},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names
            )
            return {"success": True, "job_id": job_id}
        except ClientError as e:
            return {"error": str(e)}
    
    def get_user_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get a user's video localization history.
        
        Args:
            user_id: Clerk user ID
            limit: Maximum number of items to return (default 20)
            
        Returns:
            dict with 'videos' list or 'error'
        """
        if not self.table:
            return {"error": "DynamoDB not configured"}
        
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}",
                    ':sk_prefix': 'VIDEO#'
                },
                ScanIndexForward=False,  # Newest first
                Limit=limit
            )
            
            # Parse and clean up items
            videos = []
            for item in response.get('Items', []):
                video = {
                    'job_id': item.get('job_id'),
                    'target_language': item.get('target_language'),
                    'input_file': item.get('input_file'),
                    'status': item.get('status'),
                    'created_at': item.get('created_at'),
                    'output_url': item.get('output_url'),
                    'output_s3_key': item.get('output_s3_key'),  # needed to regenerate fresh presigned URLs
                    'subtitle_s3_key': item.get('subtitle_s3_key'),
                    'words_localized': int(item['words_localized']) if item.get('words_localized') else None,
                    'whatsapp_url': item.get('whatsapp_url'),
                    'file_size_mb': float(item['file_size_mb']) if item.get('file_size_mb') else None,
                    'segments_count': item.get('segments_count'),
                }
                
                # Parse cultural report if present
                if item.get('cultural_report'):
                    try:
                        video['cultural_report'] = json.loads(item['cultural_report'])
                    except json.JSONDecodeError:
                        video['cultural_report'] = None
                
                videos.append(video)
            
            return {
                "success": True,
                "videos": videos,
                "count": len(videos)
            }
            
        except ClientError as e:
            return {"error": str(e)}
    
    def get_video_by_job_id(
        self,
        user_id: str,
        job_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific video by job ID for a user.
        Note: This requires scanning the user's items.
        """
        if not self.table:
            return None
        
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                FilterExpression='job_id = :job_id',
                ExpressionAttributeValues={
                    ':pk': f"USER#{user_id}",
                    ':sk_prefix': 'VIDEO#',
                    ':job_id': job_id
                }
            )
            
            items = response.get('Items', [])
            return items[0] if items else None
            
        except ClientError:
            return None
    
    def delete_video(
        self,
        user_id: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Delete a video record from user's history.
        
        Args:
            user_id: Clerk user ID
            job_id: Job ID to delete
            
        Returns:
            dict with success status or error
        """
        if not self.table:
            return {"error": "DynamoDB not configured"}
        
        # First, find the item to get its SK (sort key)
        video = self.get_video_by_job_id(user_id, job_id)
        if not video:
            return {"error": "Video not found or not owned by user"}
        
        try:
            # Delete the item using PK and SK
            self.table.delete_item(
                Key={
                    'PK': video.get('PK') or f"USER#{user_id}",
                    'SK': video.get('SK')
                }
            )
            
            return {
                "success": True,
                "deleted_job_id": job_id
            }
            
        except ClientError as e:
            return {"error": str(e)}


# Singleton instance
db_service = DBService()
