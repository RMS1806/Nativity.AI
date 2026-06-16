# SQS Queues for Nativity.AI Video Processing

# Dead Letter Queue (must be created first)
resource "aws_sqs_queue" "video_processing_dlq" {
  name = "${local.name_prefix}-video-processing-dlq"

  message_retention_seconds = var.sqs_message_retention_period
  visibility_timeout_seconds = var.sqs_visibility_timeout

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-video-processing-dlq"
    Type = "DeadLetterQueue"
  })
}

# Main Processing Queue
resource "aws_sqs_queue" "video_processing" {
  name = "${local.name_prefix}-video-processing"

  message_retention_seconds  = var.sqs_message_retention_period
  visibility_timeout_seconds = var.sqs_visibility_timeout
  receive_wait_time_seconds  = 20  # Long polling

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.video_processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-video-processing"
    Type = "MainQueue"
  })
}

# High Priority Queue
resource "aws_sqs_queue" "high_priority" {
  name = "${local.name_prefix}-high-priority"

  message_retention_seconds  = var.sqs_message_retention_period
  visibility_timeout_seconds = var.sqs_visibility_timeout
  receive_wait_time_seconds  = 20

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.video_processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-high-priority"
    Type = "HighPriorityQueue"
  })
}

# Draft Creation Queue
resource "aws_sqs_queue" "draft_creation" {
  name = "${local.name_prefix}-draft-creation"

  message_retention_seconds  = var.sqs_message_retention_period
  visibility_timeout_seconds = var.sqs_visibility_timeout
  receive_wait_time_seconds  = 20

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.video_processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-draft-creation"
    Type = "DraftCreationQueue"
  })
}

# SQS Queue Policy for Step Functions
resource "aws_sqs_queue_policy" "video_processing" {
  queue_url = aws_sqs_queue.video_processing.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.video_processing.arn
        Condition = {
          StringEquals = {
            "aws:SourceArn" = aws_sfn_state_machine.video_processing.arn
          }
        }
      }
    ]
  })
}

# CloudWatch Alarms for Queue Monitoring
resource "aws_cloudwatch_metric_alarm" "queue_depth" {
  alarm_name          = "${local.name_prefix}-queue-depth-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "50"
  alarm_description   = "This metric monitors SQS queue depth"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.video_processing.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${local.name_prefix}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors dead letter queue messages"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.video_processing_dlq.name
  }

  tags = local.common_tags
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

  tags = local.common_tags
}