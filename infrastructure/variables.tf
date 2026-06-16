# Variables for Nativity.AI Infrastructure

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "nativity-ai"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

# API Gateway Configuration
variable "api_gateway_stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = "v1"
}

# Lambda Configuration
variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
  default     = "python3.10"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

# ECS Configuration
variable "ecs_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 1024
}

variable "ecs_memory" {
  description = "ECS task memory in MB"
  type        = number
  default     = 2048
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

# SQS Configuration
variable "sqs_visibility_timeout" {
  description = "SQS message visibility timeout in seconds"
  type        = number
  default     = 300
}

variable "sqs_message_retention_period" {
  description = "SQS message retention period in seconds"
  type        = number
  default     = 1209600 # 14 days
}

# S3 Configuration
variable "s3_bucket_name" {
  description = "S3 bucket name for video storage"
  type        = string
  default     = ""
}

# External API Keys (passed via environment variables)
variable "google_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
}

variable "clerk_issuer_url" {
  description = "Clerk authentication issuer URL"
  type        = string
  default     = ""
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# CloudFront Configuration
variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
}

# Monitoring Configuration
variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

# Additional ECS Configuration
variable "ecs_api_cpu" {
  description = "ECS API task CPU units"
  type        = number
  default     = 512
}

variable "ecs_api_memory" {
  description = "ECS API task memory in MB"
  type        = number
  default     = 1024
}

variable "ecs_api_desired_count" {
  description = "Desired number of ECS API tasks"
  type        = number
  default     = 2
}

variable "ecs_worker_cpu" {
  description = "ECS Worker task CPU units"
  type        = number
  default     = 1024
}

variable "ecs_worker_memory" {
  description = "ECS Worker task memory in MB"
  type        = number
  default     = 2048
}

variable "ecs_worker_desired_count" {
  description = "Desired number of ECS Worker tasks"
  type        = number
  default     = 1
}

# Auto Scaling Configuration
variable "api_autoscaling_min_capacity" {
  description = "Minimum capacity for API autoscaling"
  type        = number
  default     = 1
}

variable "api_autoscaling_max_capacity" {
  description = "Maximum capacity for API autoscaling"
  type        = number
  default     = 10
}

variable "worker_autoscaling_min_capacity" {
  description = "Minimum capacity for Worker autoscaling"
  type        = number
  default     = 1
}

variable "worker_autoscaling_max_capacity" {
  description = "Maximum capacity for Worker autoscaling"
  type        = number
  default     = 20
}

# Domain Configuration
variable "domain_name" {
  description = "Custom domain name for the API (optional)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = ""
}

# Redis Configuration
variable "redis_node_type" {
  description = "Redis cache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of Redis cache nodes"
  type        = number
  default     = 1
}

# Security and Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization"
  type        = bool
  default     = true
}

variable "s3_intelligent_tiering" {
  description = "Enable S3 Intelligent-Tiering for cost optimization"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "Allowed CIDR blocks for security group ingress"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_waf" {
  description = "Enable AWS WAF for API Gateway"
  type        = bool
  default     = true
}

# Backup Configuration
variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 7
}

variable "enable_point_in_time_recovery" {
  description = "Enable DynamoDB point-in-time recovery"
  type        = bool
  default     = true
}