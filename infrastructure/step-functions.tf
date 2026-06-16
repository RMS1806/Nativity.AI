# AWS Step Functions for Nativity.AI Workflow Orchestration

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions" {
  name = "${local.name_prefix}-step-functions-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-step-functions-role"
  })
}

# IAM Policy for Step Functions
resource "aws_iam_role_policy" "step_functions" {
  name = "${local.name_prefix}-step-functions-policy"
  role = aws_iam_role.step_functions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.video_processor.arn,
          aws_lambda_function.job_status_updater.arn,
          "${aws_lambda_function.video_processor.arn}:*",
          "${aws_lambda_function.job_status_updater.arn}:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.video_processing.arn,
          aws_sqs_queue.high_priority.arn,
          aws_sqs_queue.draft_creation.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.jobs.arn,
          "${aws_dynamodb_table.jobs.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutRule",
          "events:PutTargets",
          "events:DescribeRule",
          "events:DeleteRule",
          "events:RemoveTargets"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${local.name_prefix}"
  retention_in_days = var.log_retention_days
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-step-functions-logs"
  })
}

# Video Processing Workflow State Machine
resource "aws_sfn_state_machine" "video_processing" {
  name     = "${local.name_prefix}-video-processing"
  role_arn = aws_iam_role.step_functions.arn
  
  definition = jsonencode({
    Comment = "Nativity.AI Video Processing Workflow"
    StartAt = "ValidateInput"
    States = {
      ValidateInput = {
        Type = "Task"
        Resource = aws_lambda_function.video_processor.arn
        Parameters = {
          "action" = "validate"
          "jobId.$" = "$.jobId"
          "videoUrl.$" = "$.videoUrl"
          "userId.$" = "$.userId"
        }
        Next = "CheckJobType"
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts = 3
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.TaskFailed"]
            Next = "HandleValidationError"
            ResultPath = "$.error"
          }
        ]
      }
      
      CheckJobType = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.jobType"
            StringEquals = "draft"
            Next = "ProcessDraft"
          },
          {
            Variable = "$.jobType"
            StringEquals = "high_priority"
            Next = "ProcessHighPriority"
          }
        ]
        Default = "ProcessStandard"
      }
      
      ProcessDraft = {
        Type = "Task"
        Resource = aws_lambda_function.video_processor.arn
        Parameters = {
          "action" = "process_draft"
          "jobId.$" = "$.jobId"
          "videoUrl.$" = "$.videoUrl"
          "userId.$" = "$.userId"
        }
        Next = "UpdateJobStatus"
        TimeoutSeconds = 600  # 10 minutes for drafts
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts = 2
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.TaskFailed", "States.Timeout"]
            Next = "HandleProcessingError"
            ResultPath = "$.error"
          }
        ]
      }
      
      ProcessHighPriority = {
        Type = "Task"
        Resource = aws_lambda_function.video_processor.arn
        Parameters = {
          "action" = "process_high_priority"
          "jobId.$" = "$.jobId"
          "videoUrl.$" = "$.videoUrl"
          "userId.$" = "$.userId"
        }
        Next = "UpdateJobStatus"
        TimeoutSeconds = 1800  # 30 minutes for high priority
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 5
            MaxAttempts = 3
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.TaskFailed", "States.Timeout"]
            Next = "HandleProcessingError"
            ResultPath = "$.error"
          }
        ]
      }
      
      ProcessStandard = {
        Type = "Task"
        Resource = aws_lambda_function.video_processor.arn
        Parameters = {
          "action" = "process_standard"
          "jobId.$" = "$.jobId"
          "videoUrl.$" = "$.videoUrl"
          "userId.$" = "$.userId"
        }
        Next = "UpdateJobStatus"
        TimeoutSeconds = 3600  # 60 minutes for standard processing
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 10
            MaxAttempts = 3
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.TaskFailed", "States.Timeout"]
            Next = "HandleProcessingError"
            ResultPath = "$.error"
          }
        ]
      }
      
      UpdateJobStatus = {
        Type = "Task"
        Resource = aws_lambda_function.job_status_updater.arn
        Parameters = {
          "jobId.$" = "$.jobId"
          "status" = "completed"
          "result.$" = "$.result"
        }
        Next = "NotifyUser"
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts = 3
            BackoffRate = 2.0
          }
        ]
      }
      
      NotifyUser = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = aws_sns_topic.job_notifications.arn
          Message = {
            "jobId.$" = "$.jobId"
            "userId.$" = "$.userId"
            "status" = "completed"
            "message" = "Your video processing job has been completed successfully!"
          }
        }
        End = true
      }
      
      HandleValidationError = {
        Type = "Task"
        Resource = aws_lambda_function.job_status_updater.arn
        Parameters = {
          "jobId.$" = "$.jobId"
          "status" = "failed"
          "error.$" = "$.error"
        }
        Next = "NotifyValidationFailure"
      }
      
      HandleProcessingError = {
        Type = "Task"
        Resource = aws_lambda_function.job_status_updater.arn
        Parameters = {
          "jobId.$" = "$.jobId"
          "status" = "failed"
          "error.$" = "$.error"
        }
        Next = "NotifyProcessingFailure"
      }
      
      NotifyValidationFailure = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = aws_sns_topic.job_notifications.arn
          Message = {
            "jobId.$" = "$.jobId"
            "userId.$" = "$.userId"
            "status" = "failed"
            "message" = "Your video processing job failed during validation. Please check your input and try again."
          }
        }
        End = true
      }
      
      NotifyProcessingFailure = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = aws_sns_topic.job_notifications.arn
          Message = {
            "jobId.$" = "$.jobId"
            "userId.$" = "$.userId"
            "status" = "failed"
            "message" = "Your video processing job failed during processing. Our team has been notified."
          }
        }
        End = true
      }
    }
  })
  
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-video-processing-workflow"
    Type = "Video Processing"
  })
}

# Batch Job Processing Workflow State Machine
resource "aws_sfn_state_machine" "batch_processing" {
  name     = "${local.name_prefix}-batch-processing"
  role_arn = aws_iam_role.step_functions.arn
  
  definition = jsonencode({
    Comment = "Nativity.AI Batch Job Processing Workflow"
    StartAt = "GetBatchJobs"
    States = {
      GetBatchJobs = {
        Type = "Task"
        Resource = aws_lambda_function.job_status_updater.arn
        Parameters = {
          "action" = "get_pending_jobs"
          "limit" = 10
        }
        Next = "CheckJobsExist"
      }
      
      CheckJobsExist = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.jobs"
            IsPresent = true
            Next = "ProcessJobsInParallel"
          }
        ]
        Default = "NoJobsToProcess"
      }
      
      ProcessJobsInParallel = {
        Type = "Map"
        ItemsPath = "$.jobs"
        MaxConcurrency = 5
        Iterator = {
          StartAt = "ProcessSingleJob"
          States = {
            ProcessSingleJob = {
              Type = "Task"
              Resource = "arn:aws:states:::states:startExecution.sync"
              Parameters = {
                StateMachineArn = aws_sfn_state_machine.video_processing.arn
                Input = {
                  "jobId.$" = "$.jobId"
                  "videoUrl.$" = "$.videoUrl"
                  "userId.$" = "$.userId"
                  "jobType.$" = "$.jobType"
                }
              }
              End = true
              Retry = [
                {
                  ErrorEquals = ["States.ExecutionLimitExceeded"]
                  IntervalSeconds = 30
                  MaxAttempts = 3
                  BackoffRate = 2.0
                }
              ]
            }
          }
        }
        Next = "BatchComplete"
      }
      
      BatchComplete = {
        Type = "Pass"
        Result = "Batch processing completed successfully"
        End = true
      }
      
      NoJobsToProcess = {
        Type = "Pass"
        Result = "No jobs to process"
        End = true
      }
    }
  })
  
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-batch-processing-workflow"
    Type = "Batch Processing"
  })
}

# SNS Topic for Job Notifications
resource "aws_sns_topic" "job_notifications" {
  name = "${local.name_prefix}-job-notifications"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-job-notifications-topic"
  })
}

# EventBridge Rule to trigger batch processing
resource "aws_cloudwatch_event_rule" "batch_processing_schedule" {
  name                = "${local.name_prefix}-batch-processing-schedule"
  description         = "Trigger batch processing every 5 minutes"
  schedule_expression = "rate(5 minutes)"
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-batch-processing-schedule"
  })
}

# EventBridge Target for Step Functions
resource "aws_cloudwatch_event_target" "batch_processing" {
  rule      = aws_cloudwatch_event_rule.batch_processing_schedule.name
  target_id = "BatchProcessingTarget"
  arn       = aws_sfn_state_machine.batch_processing.arn
  role_arn  = aws_iam_role.eventbridge_step_functions.arn
}

# IAM Role for EventBridge to invoke Step Functions
resource "aws_iam_role" "eventbridge_step_functions" {
  name = "${local.name_prefix}-eventbridge-step-functions-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eventbridge-step-functions-role"
  })
}

# IAM Policy for EventBridge to invoke Step Functions
resource "aws_iam_role_policy" "eventbridge_step_functions" {
  name = "${local.name_prefix}-eventbridge-step-functions-policy"
  role = aws_iam_role.eventbridge_step_functions.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = [
          aws_sfn_state_machine.batch_processing.arn
        ]
      }
    ]
  })
}

# CloudWatch Alarms for Step Functions

# Failed Executions Alarm
resource "aws_cloudwatch_metric_alarm" "step_functions_failed_executions" {
  alarm_name          = "${local.name_prefix}-step-functions-failed-executions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors Step Functions failed executions"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    StateMachineArn = aws_sfn_state_machine.video_processing.arn
  }
  
  tags = local.common_tags
}

# Long Running Executions Alarm
resource "aws_cloudwatch_metric_alarm" "step_functions_long_executions" {
  alarm_name          = "${local.name_prefix}-step-functions-long-executions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Average"
  threshold           = "3600000"  # 1 hour in milliseconds
  alarm_description   = "This metric monitors Step Functions execution time"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    StateMachineArn = aws_sfn_state_machine.video_processing.arn
  }
  
  tags = local.common_tags
}

