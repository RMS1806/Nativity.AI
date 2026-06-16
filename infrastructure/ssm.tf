# SSM Parameters for Nativity.AI Configuration Management

# Google API Key (Secure String)
resource "aws_ssm_parameter" "google_api_key" {
  name  = "/${local.name_prefix}/google-api-key"
  type  = "SecureString"
  value = var.google_api_key
  
  description = "Google Gemini API Key for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-google-api-key"
    Type = "Secret"
  })
}

# Clerk Issuer URL (Secure String)
resource "aws_ssm_parameter" "clerk_issuer_url" {
  name  = "/${local.name_prefix}/clerk-issuer-url"
  type  = "SecureString"
  value = var.clerk_issuer_url
  
  description = "Clerk authentication issuer URL for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-clerk-issuer-url"
    Type = "Secret"
  })
}

# Redis Auth Token (Secure String)
resource "aws_ssm_parameter" "redis_auth_token" {
  name  = "/${local.name_prefix}/redis-auth-token"
  type  = "SecureString"
  value = random_password.redis_auth_token.result
  
  description = "Redis authentication token for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-auth-token"
    Type = "Secret"
  })
}

# Application Configuration Parameters

# Environment Configuration
resource "aws_ssm_parameter" "environment" {
  name  = "/${local.name_prefix}/environment"
  type  = "String"
  value = var.environment
  
  description = "Environment name for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-environment"
    Type = "Configuration"
  })
}

# AWS Region
resource "aws_ssm_parameter" "aws_region" {
  name  = "/${local.name_prefix}/aws-region"
  type  = "String"
  value = local.region
  
  description = "AWS Region for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-aws-region"
    Type = "Configuration"
  })
}

# SQS Queue URLs
resource "aws_ssm_parameter" "video_processing_queue_url" {
  name  = "/${local.name_prefix}/video-processing-queue-url"
  type  = "String"
  value = aws_sqs_queue.video_processing.url
  
  description = "Video processing queue URL for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-video-processing-queue-url"
    Type = "Configuration"
  })
}

resource "aws_ssm_parameter" "high_priority_queue_url" {
  name  = "/${local.name_prefix}/high-priority-queue-url"
  type  = "String"
  value = aws_sqs_queue.high_priority.url
  
  description = "High priority queue URL for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-high-priority-queue-url"
    Type = "Configuration"
  })
}

resource "aws_ssm_parameter" "draft_creation_queue_url" {
  name  = "/${local.name_prefix}/draft-creation-queue-url"
  type  = "String"
  value = aws_sqs_queue.draft_creation.url
  
  description = "Draft creation queue URL for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-draft-creation-queue-url"
    Type = "Configuration"
  })
}

# DynamoDB Table Names
resource "aws_ssm_parameter" "jobs_table_name" {
  name  = "/${local.name_prefix}/jobs-table-name"
  type  = "String"
  value = aws_dynamodb_table.jobs.name
  
  description = "Jobs table name for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-jobs-table-name"
    Type = "Configuration"
  })
}

resource "aws_ssm_parameter" "users_table_name" {
  name  = "/${local.name_prefix}/users-table-name"
  type  = "String"
  value = aws_dynamodb_table.users.name
  
  description = "Users table name for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-users-table-name"
    Type = "Configuration"
  })
}

# S3 Bucket Name
resource "aws_ssm_parameter" "s3_bucket_name" {
  name  = "/${local.name_prefix}/s3-bucket-name"
  type  = "String"
  value = aws_s3_bucket.storage.bucket
  
  description = "S3 storage bucket name for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-bucket-name"
    Type = "Configuration"
  })
}

# Redis Configuration
resource "aws_ssm_parameter" "redis_host" {
  name  = "/${local.name_prefix}/redis-host"
  type  = "String"
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
  
  description = "Redis host endpoint for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-host"
    Type = "Configuration"
  })
}

resource "aws_ssm_parameter" "redis_port" {
  name  = "/${local.name_prefix}/redis-port"
  type  = "String"
  value = tostring(aws_elasticache_replication_group.redis.port)
  
  description = "Redis port for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-port"
    Type = "Configuration"
  })
}

# Application URLs
resource "aws_ssm_parameter" "api_url" {
  name  = "/${local.name_prefix}/api-url"
  type  = "String"
  value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
  
  description = "API URL for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-url"
    Type = "Configuration"
  })
}

# Monitoring Configuration
resource "aws_ssm_parameter" "log_level" {
  name  = "/${local.name_prefix}/log-level"
  type  = "String"
  value = var.environment == "prod" ? "info" : "debug"
  
  description = "Application log level for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-log-level"
    Type = "Configuration"
  })
}

# Feature Flags
resource "aws_ssm_parameter" "enable_detailed_monitoring" {
  name  = "/${local.name_prefix}/enable-detailed-monitoring"
  type  = "String"
  value = tostring(var.enable_detailed_monitoring)
  
  description = "Enable detailed monitoring flag for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-enable-detailed-monitoring"
    Type = "Configuration"
  })
}

# Processing Configuration
resource "aws_ssm_parameter" "max_concurrent_jobs" {
  name  = "/${local.name_prefix}/max-concurrent-jobs"
  type  = "String"
  value = "10"
  
  description = "Maximum concurrent jobs for Nativity.AI workers"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-max-concurrent-jobs"
    Type = "Configuration"
  })
}

resource "aws_ssm_parameter" "job_timeout_minutes" {
  name  = "/${local.name_prefix}/job-timeout-minutes"
  type  = "String"
  value = "30"
  
  description = "Job timeout in minutes for Nativity.AI"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-job-timeout-minutes"
    Type = "Configuration"
  })
}

