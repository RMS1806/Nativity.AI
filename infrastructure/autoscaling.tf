# Auto Scaling Configuration for Nativity.AI ECS Services

# Auto Scaling Target for API Service
resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_autoscaling_max_capacity
  min_capacity       = var.api_autoscaling_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-autoscaling-target"
  })
}

# Auto Scaling Target for Worker Service
resource "aws_appautoscaling_target" "worker" {
  max_capacity       = var.worker_autoscaling_max_capacity
  min_capacity       = var.worker_autoscaling_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-worker-autoscaling-target"
  })
}

# Auto Scaling Policy for API - CPU Based
resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${local.name_prefix}-api-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300  # 5 minutes
    scale_out_cooldown = 60   # 1 minute
  }
}

# Auto Scaling Policy for API - Memory Based
resource "aws_appautoscaling_policy" "api_memory" {
  name               = "${local.name_prefix}-api-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80.0
    scale_in_cooldown  = 300  # 5 minutes
    scale_out_cooldown = 60   # 1 minute
  }
}

# Auto Scaling Policy for API - ALB Request Count
resource "aws_appautoscaling_policy" "api_requests" {
  name               = "${local.name_prefix}-api-requests-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.api.arn_suffix}"
    }
    target_value       = 1000.0  # Requests per target per minute
    scale_in_cooldown  = 300     # 5 minutes
    scale_out_cooldown = 60      # 1 minute
  }
}

# Auto Scaling Policy for Worker - CPU Based
resource "aws_appautoscaling_policy" "worker_cpu" {
  name               = "${local.name_prefix}-worker-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 60.0  # Lower threshold for workers
    scale_in_cooldown  = 600   # 10 minutes (longer for workers)
    scale_out_cooldown = 120   # 2 minutes
  }
}

# Auto Scaling Policy for Worker - Memory Based
resource "aws_appautoscaling_policy" "worker_memory" {
  name               = "${local.name_prefix}-worker-memory-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 70.0  # Lower threshold for workers
    scale_in_cooldown  = 600   # 10 minutes
    scale_out_cooldown = 120   # 2 minutes
  }
}

# Custom Auto Scaling Policy for Worker - SQS Queue Depth
resource "aws_appautoscaling_policy" "worker_queue_depth" {
  name               = "${local.name_prefix}-worker-queue-depth-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace
  
  target_tracking_scaling_policy_configuration {
    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessages"
      namespace   = "AWS/SQS"
      statistic   = "Average"
    }
    target_value       = 10.0  # Target 10 messages per worker
    scale_in_cooldown  = 600   # 10 minutes
    scale_out_cooldown = 60    # 1 minute (fast scale out for queue processing)
  }
}

# Scheduled Scaling for Predictable Load Patterns

# Scale up during business hours (9 AM UTC)
resource "aws_appautoscaling_scheduled_action" "api_scale_up" {
  name               = "${local.name_prefix}-api-scale-up"
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  schedule           = "cron(0 9 ? * MON-FRI *)"  # 9 AM UTC, Monday to Friday
  
  scalable_target_action {
    min_capacity = var.api_autoscaling_min_capacity + 1
    max_capacity = var.api_autoscaling_max_capacity
  }
}

# Scale down during off hours (6 PM UTC)
resource "aws_appautoscaling_scheduled_action" "api_scale_down" {
  name               = "${local.name_prefix}-api-scale-down"
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  schedule           = "cron(0 18 ? * MON-FRI *)"  # 6 PM UTC, Monday to Friday
  
  scalable_target_action {
    min_capacity = var.api_autoscaling_min_capacity
    max_capacity = var.api_autoscaling_max_capacity
  }
}

# CloudWatch Alarms for Auto Scaling Monitoring

# API Service High CPU Alarm
resource "aws_cloudwatch_metric_alarm" "api_high_cpu" {
  alarm_name          = "${local.name_prefix}-api-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors API service CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ServiceName = aws_ecs_service.api.name
    ClusterName = aws_ecs_cluster.main.name
  }
  
  tags = local.common_tags
}

# Worker Service High CPU Alarm
resource "aws_cloudwatch_metric_alarm" "worker_high_cpu" {
  alarm_name          = "${local.name_prefix}-worker-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors worker service CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ServiceName = aws_ecs_service.worker.name
    ClusterName = aws_ecs_cluster.main.name
  }
  
  tags = local.common_tags
}

# Queue Depth Alarm for Worker Scaling
resource "aws_cloudwatch_metric_alarm" "queue_depth_high" {
  alarm_name          = "${local.name_prefix}-queue-depth-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "100"  # More than 100 messages waiting
  alarm_description   = "This metric monitors video processing queue depth"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    QueueName = aws_sqs_queue.video_processing.name
  }
  
  tags = local.common_tags
}

