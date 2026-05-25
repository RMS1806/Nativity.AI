# S3 Storage Infrastructure for Nativity.AI

# Main Storage Bucket
resource "aws_s3_bucket" "storage" {
  bucket = "${local.name_prefix}-storage-${random_id.bucket_suffix.hex}"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-storage-bucket"
    Type = "Primary Storage"
  })
}

# Random suffix for bucket name uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Bucket Versioning
resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  rule {
    id     = "video_files_lifecycle"
    status = "Enabled"
    
    filter {
      prefix = "videos/"
    }
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
  
  rule {
    id     = "temp_files_cleanup"
    status = "Enabled"
    
    filter {
      prefix = "temp/"
    }
    
    expiration {
      days = 7
    }
  }
  
  rule {
    id     = "incomplete_multipart_uploads"
    status = "Enabled"
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
  
  dynamic "rule" {
    for_each = var.s3_intelligent_tiering ? [1] : []
    content {
      id     = "intelligent_tiering"
      status = "Enabled"
      
      filter {
        prefix = "processed/"
      }
      
      transition {
        days          = 0
        storage_class = "INTELLIGENT_TIERING"
      }
    }
  }
}

# CORS Configuration
resource "aws_s3_bucket_cors_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]  # Restrict this in production
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Notification Configuration for processing triggers
resource "aws_s3_bucket_notification" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  # Trigger Lambda when video files are uploaded
  lambda_function {
    lambda_function_arn = aws_lambda_function.video_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/videos/"
    filter_suffix       = ".mp4"
  }
  
  lambda_function {
    lambda_function_arn = aws_lambda_function.video_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/videos/"
    filter_suffix       = ".mov"
  }
  
  lambda_function {
    lambda_function_arn = aws_lambda_function.video_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/videos/"
    filter_suffix       = ".avi"
  }
  
  depends_on = [aws_lambda_permission.s3_invoke_video_processor]
}

# CloudWatch Metrics for S3
resource "aws_s3_bucket_metric" "storage_metrics" {
  bucket = aws_s3_bucket.storage.id
  name   = "EntireBucket"
}

# CloudWatch Alarms for S3
resource "aws_cloudwatch_metric_alarm" "s3_bucket_size" {
  alarm_name          = "${local.name_prefix}-s3-bucket-size"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = "107374182400"  # 100 GB in bytes
  alarm_description   = "This metric monitors S3 bucket size"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    BucketName  = aws_s3_bucket.storage.bucket
    StorageType = "StandardStorage"
  }
  
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "s3_number_of_objects" {
  alarm_name          = "${local.name_prefix}-s3-number-of-objects"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "NumberOfObjects"
  namespace           = "AWS/S3"
  period              = "86400"  # 24 hours
  statistic           = "Average"
  threshold           = "100000"  # 100k objects
  alarm_description   = "This metric monitors S3 object count"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    BucketName  = aws_s3_bucket.storage.bucket
    StorageType = "AllStorageTypes"
  }
  
  tags = local.common_tags
}

# Backup Bucket (for cross-region replication)
resource "aws_s3_bucket" "backup" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = "${local.name_prefix}-backup-${random_id.bucket_suffix.hex}"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-bucket"
    Type = "Backup Storage"
  })
}

# Backup Bucket Versioning
resource "aws_s3_bucket_versioning" "backup" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.backup[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# Backup Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "backup" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.backup[0].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Replication Configuration (for production)
resource "aws_s3_bucket_replication_configuration" "storage" {
  count  = var.environment == "prod" ? 1 : 0
  role   = aws_iam_role.s3_replication[0].arn
  bucket = aws_s3_bucket.storage.id
  
  rule {
    id     = "replicate_all"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.backup[0].arn
      storage_class = "STANDARD_IA"
    }
  }
  
  depends_on = [aws_s3_bucket_versioning.storage]
}

# IAM Role for S3 Replication
resource "aws_iam_role" "s3_replication" {
  count = var.environment == "prod" ? 1 : 0
  name  = "${local.name_prefix}-s3-replication-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-replication-role"
  })
}

# IAM Policy for S3 Replication
resource "aws_iam_role_policy" "s3_replication" {
  count = var.environment == "prod" ? 1 : 0
  name  = "${local.name_prefix}-s3-replication-policy"
  role  = aws_iam_role.s3_replication[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Resource = "${aws_s3_bucket.storage.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.storage.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Resource = "${aws_s3_bucket.backup[0].arn}/*"
      }
    ]
  })
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the main S3 storage bucket"
  value       = aws_s3_bucket.storage.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the main S3 storage bucket"
  value       = aws_s3_bucket.storage.arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.storage.bucket_domain_name
}

output "s3_backup_bucket_name" {
  description = "Name of the backup S3 bucket (production only)"
  value       = var.environment == "prod" ? aws_s3_bucket.backup[0].bucket : null
}