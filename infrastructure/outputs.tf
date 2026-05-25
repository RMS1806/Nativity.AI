# Terraform Outputs for Nativity.AI Infrastructure

# Account and Region Information
output "account_id" {
  description = "AWS Account ID"
  value       = local.account_id
}

output "region" {
  description = "AWS Region"
  value       = local.region
}

output "name_prefix" {
  description = "Resource naming prefix"
  value       = local.name_prefix
}

# VPC and Networking
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

# Load Balancer
output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "load_balancer_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

# ECS Cluster
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

# ECR Repositories
output "api_repository_url" {
  description = "URL of the API ECR repository"
  value       = aws_ecr_repository.api.repository_url
}

output "worker_repository_url" {
  description = "URL of the Worker ECR repository"
  value       = aws_ecr_repository.worker.repository_url
}

output "api_repository_name" {
  description = "Name of the API ECR repository"
  value       = aws_ecr_repository.api.name
}

output "worker_repository_name" {
  description = "Name of the Worker ECR repository"
  value       = aws_ecr_repository.worker.name
}

# SQS Queues
output "video_processing_queue_url" {
  description = "URL of the main video processing queue"
  value       = aws_sqs_queue.video_processing.url
}

output "video_processing_queue_arn" {
  description = "ARN of the main video processing queue"
  value       = aws_sqs_queue.video_processing.arn
}

output "high_priority_queue_url" {
  description = "URL of the high priority queue"
  value       = aws_sqs_queue.high_priority.url
}

output "draft_creation_queue_url" {
  description = "URL of the draft creation queue"
  value       = aws_sqs_queue.draft_creation.url
}

output "video_processing_dlq_url" {
  description = "URL of the video processing dead letter queue"
  value       = aws_sqs_queue.video_processing_dlq.url
}

# DynamoDB Tables
output "jobs_table_name" {
  description = "Name of the jobs DynamoDB table"
  value       = aws_dynamodb_table.jobs.name
}

output "jobs_table_arn" {
  description = "ARN of the jobs DynamoDB table"
  value       = aws_dynamodb_table.jobs.arn
}

output "users_table_name" {
  description = "Name of the users DynamoDB table"
  value       = aws_dynamodb_table.users.name
}

output "users_table_arn" {
  description = "ARN of the users DynamoDB table"
  value       = aws_dynamodb_table.users.arn
}

# Redis
output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
}

output "redis_port" {
  description = "Redis cluster port"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_auth_token" {
  description = "Redis authentication token"
  value       = random_password.redis_auth_token.result
  sensitive   = true
}

# S3 Storage
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

# Lambda Functions
output "video_processor_function_name" {
  description = "Name of the video processor Lambda function"
  value       = aws_lambda_function.video_processor.function_name
}

output "video_processor_function_arn" {
  description = "ARN of the video processor Lambda function"
  value       = aws_lambda_function.video_processor.arn
}

output "job_status_updater_function_name" {
  description = "Name of the job status updater Lambda function"
  value       = aws_lambda_function.job_status_updater.function_name
}

output "job_status_updater_function_arn" {
  description = "ARN of the job status updater Lambda function"
  value       = aws_lambda_function.job_status_updater.arn
}

# API Gateway
output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = aws_api_gateway_deployment.main.invoke_url
}

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_api_gateway_rest_api.main.id
}

# Step Functions
output "video_processing_state_machine_arn" {
  description = "ARN of the video processing state machine"
  value       = aws_sfn_state_machine.video_processing.arn
}

output "batch_processing_state_machine_arn" {
  description = "ARN of the batch processing state machine"
  value       = aws_sfn_state_machine.batch_processing.arn
}

# SNS Topics
output "sns_alerts_topic_arn" {
  description = "ARN of the SNS alerts topic"
  value       = aws_sns_topic.alerts.arn
}

output "sns_critical_alerts_topic_arn" {
  description = "ARN of the SNS critical alerts topic"
  value       = aws_sns_topic.critical_alerts.arn
}

output "job_notifications_topic_arn" {
  description = "ARN of the job notifications SNS topic"
  value       = aws_sns_topic.job_notifications.arn
}

# SSM Parameters
output "ssm_parameter_prefix" {
  description = "SSM parameter prefix for Nativity.AI"
  value       = "/${local.name_prefix}/"
}

output "google_api_key_parameter_arn" {
  description = "ARN of the Google API key SSM parameter"
  value       = aws_ssm_parameter.google_api_key.arn
}

output "clerk_issuer_url_parameter_arn" {
  description = "ARN of the Clerk issuer URL SSM parameter"
  value       = aws_ssm_parameter.clerk_issuer_url.arn
}

output "redis_auth_token_parameter_arn" {
  description = "ARN of the Redis auth token SSM parameter"
  value       = aws_ssm_parameter.redis_auth_token.arn
}

# Auto Scaling
output "api_autoscaling_target_arn" {
  description = "ARN of the API auto scaling target"
  value       = aws_appautoscaling_target.api.arn
}

output "worker_autoscaling_target_arn" {
  description = "ARN of the worker auto scaling target"
  value       = aws_appautoscaling_target.worker.arn
}

# Monitoring
output "cloudwatch_dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = "https://${local.region}.console.aws.amazon.com/cloudwatch/home?region=${local.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

# Security Groups
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ID of the ECS security group"
  value       = aws_security_group.ecs.id
}

output "redis_security_group_id" {
  description = "ID of the Redis security group"
  value       = aws_security_group.redis.id
}

# Application URLs
output "application_url" {
  description = "Main application URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "api_health_check_url" {
  description = "API health check URL"
  value       = "${var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"}/health"
}

# Environment Information
output "environment_summary" {
  description = "Summary of the deployed environment"
  value = {
    environment     = var.environment
    region         = local.region
    vpc_id         = aws_vpc.main.id
    cluster_name   = aws_ecs_cluster.main.name
    api_url        = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
    dashboard_url  = "https://${local.region}.console.aws.amazon.com/cloudwatch/home?region=${local.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
  }
}