# CloudWatch Monitoring and Alerting for Nativity.AI

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.api.name, "ClusterName", aws_ecs_cluster.main.name],
            [".", "MemoryUtilization", ".", ".", ".", "."],
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.worker.name, "ClusterName", aws_ecs_cluster.main.name],
            [".", "MemoryUtilization", ".", ".", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          title   = "ECS Service Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessages", "QueueName", aws_sqs_queue.video_processing.name],
            [".", ".", ".", aws_sqs_queue.high_priority.name],
            [".", ".", ".", aws_sqs_queue.draft_creation.name],
            [".", ".", ".", aws_sqs_queue.video_processing_dlq.name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          title   = "SQS Queue Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix],
            [".", "TargetResponseTime", ".", "."],
            [".", "HTTPCode_Target_2XX_Count", ".", "."],
            [".", "HTTPCode_Target_4XX_Count", ".", "."],
            [".", "HTTPCode_Target_5XX_Count", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          title   = "Load Balancer Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "${aws_elasticache_replication_group.redis.replication_group_id}-001"],
            [".", "DatabaseMemoryUsagePercentage", ".", "."],
            [".", "NetworkBytesIn", ".", "."],
            [".", "NetworkBytesOut", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          title   = "Redis Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.jobs.name],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ConsumedReadCapacityUnits", ".", aws_dynamodb_table.users.name],
            [".", "ConsumedWriteCapacityUnits", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          title   = "DynamoDB Metrics"
          period  = 300
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cloudwatch-dashboard"
  })
}

# Custom Metrics for Application Performance

# Custom Metric Filter for API Errors
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${local.name_prefix}-api-errors"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ...]"
  
  metric_transformation {
    name      = "APIErrors"
    namespace = "Nativity.AI/Application"
    value     = "1"
  }
}

# Custom Metric Filter for Job Processing Time
resource "aws_cloudwatch_log_metric_filter" "job_processing_time" {
  name           = "${local.name_prefix}-job-processing-time"
  log_group_name = aws_cloudwatch_log_group.worker.name
  pattern        = "[timestamp, request_id, level, message=\"Job completed\", duration]"
  
  metric_transformation {
    name      = "JobProcessingTime"
    namespace = "Nativity.AI/Application"
    value     = "$duration"
    unit      = "Seconds"
  }
}

# Custom Metric Filter for Failed Jobs
resource "aws_cloudwatch_log_metric_filter" "failed_jobs" {
  name           = "${local.name_prefix}-failed-jobs"
  log_group_name = aws_cloudwatch_log_group.worker.name
  pattern        = "[timestamp, request_id, level=\"ERROR\", message=\"Job failed\", ...]"
  
  metric_transformation {
    name      = "FailedJobs"
    namespace = "Nativity.AI/Application"
    value     = "1"
  }
}

# Application Performance Alarms

# API Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "${local.name_prefix}-api-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "APIErrors"
  namespace           = "Nativity.AI/Application"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors API error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  tags = local.common_tags
}

# Job Failure Rate Alarm
resource "aws_cloudwatch_metric_alarm" "job_failure_rate" {
  alarm_name          = "${local.name_prefix}-job-failure-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FailedJobs"
  namespace           = "Nativity.AI/Application"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors job failure rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  tags = local.common_tags
}

# Long Job Processing Time Alarm
resource "aws_cloudwatch_metric_alarm" "long_job_processing" {
  alarm_name          = "${local.name_prefix}-long-job-processing"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "JobProcessingTime"
  namespace           = "Nativity.AI/Application"
  period              = "300"
  statistic           = "Average"
  threshold           = "1800"  # 30 minutes
  alarm_description   = "This metric monitors long job processing times"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  tags = local.common_tags
}

# Load Balancer Health Alarms

# High Response Time Alarm
resource "aws_cloudwatch_metric_alarm" "alb_high_response_time" {
  alarm_name          = "${local.name_prefix}-alb-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"  # 5 seconds
  alarm_description   = "This metric monitors ALB response time"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
  
  tags = local.common_tags
}

# High 5XX Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  alarm_name          = "${local.name_prefix}-alb-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors ALB 5XX errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
  
  tags = local.common_tags
}

# DynamoDB Throttling Alarms

# Jobs Table Read Throttling
resource "aws_cloudwatch_metric_alarm" "jobs_table_read_throttling" {
  alarm_name          = "${local.name_prefix}-jobs-table-read-throttling"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ReadThrottledEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB read throttling"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    TableName = aws_dynamodb_table.jobs.name
  }
  
  tags = local.common_tags
}

# Jobs Table Write Throttling
resource "aws_cloudwatch_metric_alarm" "jobs_table_write_throttling" {
  alarm_name          = "${local.name_prefix}-jobs-table-write-throttling"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "WriteThrottledEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB write throttling"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    TableName = aws_dynamodb_table.jobs.name
  }
  
  tags = local.common_tags
}

# SNS Topic for Critical Alerts (separate from general alerts)
resource "aws_sns_topic" "critical_alerts" {
  name = "${local.name_prefix}-critical-alerts"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-critical-alerts-topic"
    Type = "Critical"
  })
}

# CloudWatch Composite Alarms for System Health

# Overall System Health Alarm
resource "aws_cloudwatch_composite_alarm" "system_health" {
  alarm_name        = "${local.name_prefix}-system-health"
  alarm_description = "Overall system health for Nativity.AI"
  
  alarm_rule = join(" OR ", [
    "ALARM(${aws_cloudwatch_metric_alarm.api_high_cpu.alarm_name})",
    "ALARM(${aws_cloudwatch_metric_alarm.worker_high_cpu.alarm_name})",
    "ALARM(${aws_cloudwatch_metric_alarm.redis_cpu_utilization.alarm_name})",
    "ALARM(${aws_cloudwatch_metric_alarm.video_processing_dlq_messages.alarm_name})",
    "ALARM(${aws_cloudwatch_metric_alarm.alb_5xx_errors.alarm_name})"
  ])
  
  alarm_actions = [aws_sns_topic.critical_alerts.arn]
  ok_actions    = [aws_sns_topic.critical_alerts.arn]
  
  tags = local.common_tags
}

# Outputs
output "cloudwatch_dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = "https://${local.region}.console.aws.amazon.com/cloudwatch/home?region=${local.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "sns_alerts_topic_arn" {
  description = "ARN of the SNS alerts topic"
  value       = aws_sns_topic.alerts.arn
}

output "sns_critical_alerts_topic_arn" {
  description = "ARN of the SNS critical alerts topic"
  value       = aws_sns_topic.critical_alerts.arn
}