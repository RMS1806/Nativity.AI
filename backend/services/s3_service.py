"""
Cloudflare R2 Storage Service for Nativity.ai
Drop-in replacement for the previous AWS S3 service.

R2 is S3-compatible — boto3 works unchanged, just with a different
endpoint_url and credentials (R2 API tokens instead of AWS keys).

Required env vars:
  R2_ACCOUNT_ID          — found in R2 dashboard
  R2_ACCESS_KEY_ID       — R2 API token ID
  R2_SECRET_ACCESS_KEY   — R2 API token secret
  R2_BUCKET_NAME         — bucket name
  R2_PUBLIC_URL          — public bucket URL (e.g. https://pub-xxx.r2.dev)
"""

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Optional
import os
from config import settings


class S3Service:
    """
    Storage service backed by Cloudflare R2 (S3-compatible).
    All method signatures are identical to the previous S3Service
    so no route or worker code needs to change.
    """

    def __init__(self):
        self.bucket_name = settings.R2_BUCKET_NAME
        self.public_url  = settings.R2_PUBLIC_URL.rstrip("/") if settings.R2_PUBLIC_URL else ""
        self._client     = None

    @property
    def client(self):
        """Lazy R2 client — uses boto3 with a custom endpoint_url."""
        if self._client is None:
            endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
        return self._client

    def is_configured(self) -> bool:
        """Check if R2 is properly configured."""
        return bool(
            settings.R2_ACCOUNT_ID
            and settings.R2_ACCESS_KEY_ID
            and settings.R2_SECRET_ACCESS_KEY
            and settings.R2_BUCKET_NAME
        )
    
    def generate_presigned_upload_url(
        self,
        file_name: str,
        content_type: str = "video/mp4",
        expires_in: int = 3600
    ) -> dict:
        """
        Generate a presigned PUT URL for direct browser upload to R2.
        The browser PUTs the video file directly — the API server is not in the data path.
        """
        if not self.is_configured():
            return {"error": "R2 storage not configured"}

        file_key = f"uploads/{file_name}"

        try:
            presigned_url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": file_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

            return {
                "upload_url": presigned_url,
                "file_key": file_key,
                "bucket": self.bucket_name,
                "expires_in": expires_in,
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def generate_presigned_download_url(
        self,
        file_key: str,
        expires_in: int = 3600
    ) -> dict:
        """Generate a presigned GET URL for downloading / streaming a file from R2."""
        if not self.is_configured():
            return {"error": "R2 storage not configured"}

        try:
            presigned_url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=expires_in,
            )
            return {
                "download_url": presigned_url,
                "file_key": file_key,
                "expires_in": expires_in,
            }
        except ClientError as e:
            return {"error": str(e)}
    
    def create_presigned_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned GET URL for an R2 object.
        If R2_PUBLIC_URL is set, returns a plain public CDN URL instead
        (no expiry, suitable for publicly-accessible buckets).
        """
        if not object_name or not self.is_configured():
            return None

        try:
            # Strip any accidental full-URL prefix — keep bare key only
            if ".r2.cloudflarestorage.com" in object_name or ".r2.dev" in object_name:
                object_name = object_name.split(".com/")[-1].split("?")[0]
            if "amazonaws.com" in object_name:
                object_name = object_name.split(".com/")[-1].split("?")[0]

            # If bucket is public, serve via public URL (no expiry)
            if self.public_url:
                return f"{self.public_url}/{object_name}"

            # Otherwise, generate a time-limited presigned URL
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )

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
