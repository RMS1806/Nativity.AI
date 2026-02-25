"""
AWS S3 Service for Nativity.ai
Handles file uploads, downloads, and presigned URL generation
"""

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Optional
import os
from config import settings


class S3Service:
    """
    Service for interacting with AWS S3
    Handles video storage and retrieval
    """
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of S3 client"""
        if self._client is None:
            self._client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region,
                config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
            )
        return self._client
    
    def is_configured(self) -> bool:
        """Check if S3 is properly configured"""
        return bool(
            settings.AWS_ACCESS_KEY_ID and 
            settings.AWS_SECRET_ACCESS_KEY and 
            settings.S3_BUCKET_NAME
        )
    
    def generate_presigned_upload_url(
        self, 
        file_name: str, 
        content_type: str = "video/mp4",
        expires_in: int = 3600
    ) -> dict:
        """
        Generate a presigned URL for direct browser upload to S3
        
        Args:
            file_name: Name of the file to upload
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds
        
        Returns:
            dict with upload_url and file_key
        """
        if not self.is_configured():
            return {"error": "S3 not configured"}
        
        file_key = f"uploads/{file_name}"
        
        try:
            presigned_url = self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            # Debug logging for URL troubleshooting
            print(f"Generated S3 URL: {presigned_url}")
            
            return {
                "upload_url": presigned_url,
                "file_key": file_key,
                "bucket": self.bucket_name,
                "expires_in": expires_in
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def generate_presigned_download_url(
        self, 
        file_key: str, 
        expires_in: int = 3600
    ) -> dict:
        """
        Generate a presigned URL for downloading/streaming a file
        
        Args:
            file_key: S3 key of the file
            expires_in: URL expiration time in seconds
        
        Returns:
            dict with download_url
        """
        if not self.is_configured():
            return {"error": "S3 not configured"}
        
        try:
            presigned_url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key
                },
                ExpiresIn=expires_in
            )
            
            return {
                "download_url": presigned_url,
                "file_key": file_key,
                "expires_in": expires_in
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def create_presigned_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL to share an S3 object.
        If CLOUDFRONT_DOMAIN is set, the S3 domain is swapped for the CloudFront
        domain so all video traffic is served through the CDN.

        Args:
            object_name: S3 key or full URL of the object
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL string (CloudFront or S3) or None if error
        """
        if not object_name or not self.is_configured():
            return None

        try:
            # Handle full URLs stored by mistake — extract the bare S3 key
            if "amazonaws.com" in object_name:
                object_name = object_name.split(".com/")[-1].split("?")[0]

            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )

            # Swap S3 domain for CloudFront domain if configured
            cloudfront_domain = os.environ.get('CLOUDFRONT_DOMAIN')
            if cloudfront_domain and url:
                from urllib.parse import urlparse

                parsed_url = urlparse(url)

                # Strip any accidental scheme prefix from the env var value
                clean_cf_domain = (
                    cloudfront_domain
                    .replace('https://', '')
                    .replace('http://', '')
                    .strip('/')
                )

                # Replace only the netloc so the path + secure query params are intact
                url = url.replace(parsed_url.netloc, clean_cf_domain)

            return url

        except Exception as e:
            print(f"Error generating presigned URL for {object_name}: {e}")
            return None
    
    def upload_file(self, local_path: str, s3_key: str) -> dict:
        """
        Upload a local file to S3
        
        Args:
            local_path: Path to local file
            s3_key: Destination key in S3
        
        Returns:
            dict with upload status
        """
        if not self.is_configured():
            return {"error": "S3 not configured"}
        
        try:
            self.client.upload_file(local_path, self.bucket_name, s3_key)
            return {
                "success": True,
                "bucket": self.bucket_name,
                "key": s3_key,
                "url": f"s3://{self.bucket_name}/{s3_key}"
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def download_file(self, s3_key: str, local_path: str) -> dict:
        """
        Download a file from S3 to local path
        
        Args:
            s3_key: S3 key of the file
            local_path: Destination local path
        
        Returns:
            dict with download status
        """
        if not self.is_configured():
            return {"error": "S3 not configured"}
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.download_file(self.bucket_name, s3_key, local_path)
            return {
                "success": True,
                "local_path": local_path
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def list_files(self, prefix: str = "uploads/") -> dict:
        """
        List files in the bucket with given prefix
        
        Args:
            prefix: S3 key prefix to filter
        
        Returns:
            dict with list of files
        """
        if not self.is_configured():
            return {"error": "S3 not configured"}
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat()
                })
            
            return {"files": files, "count": len(files)}
        except ClientError as e:
            return {"error": str(e)}


# Singleton instance
s3_service = S3Service()
