# Lambda Functions for Nativity.AI API

# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for Lambda Functions
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "${aws_s3_bucket.video_storage.arn}",
          "${aws_s3_bucket.video_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.nativity_production.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.video_processing.arn,
          aws_sqs_queue.video_processing_dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheClusters",
          "elasticache:DescribeReplicationGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.video_processing.arn
      }
    ]
  })
}

# CloudWatch Log Groups for Lambda Functions
resource "aws_cloudwatch_log_group" "upload_handler" {
  name              = "/aws/lambda/${local.name_prefix}-upload-handler"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "status_handler" {
  name              = "/aws/lambda/${local.name_prefix}-status-handler"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "translate_handler" {
  name              = "/aws/lambda/${local.name_prefix}-translate-handler"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "localize_handler" {
  name              = "/aws/lambda/${local.name_prefix}-localize-handler"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

# Lambda Function: Upload Handler
resource "aws_lambda_function" "upload_handler" {
  filename         = "lambda_functions/upload_handler.zip"
  function_name    = "${local.name_prefix}-upload-handler"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.video_storage.bucket
      DYNAMODB_TABLE = aws_dynamodb_table.nativity_production.name
      REDIS_ENDPOINT = aws_elasticache_replication_group.redis.primary_endpoint_address
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.upload_handler,
  ]

  tags = local.common_tags
}

# Lambda Function: Status Handler
resource "aws_lambda_function" "status_handler" {
  filename         = "lambda_functions/status_handler.zip"
  function_name    = "${local.name_prefix}-status-handler"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.nativity_production.name
      REDIS_ENDPOINT = aws_elasticache_replication_group.redis.primary_endpoint_address
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.status_handler,
  ]

  tags = local.common_tags
}

# Lambda Function: Translate Handler
resource "aws_lambda_function" "translate_handler" {
  filename         = "lambda_functions/translate_handler.zip"
  function_name    = "${local.name_prefix}-translate-handler"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      GOOGLE_API_KEY = var.google_api_key
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.translate_handler,
  ]

  tags = local.common_tags
}

# Lambda Function: Localize Handler
resource "aws_lambda_function" "localize_handler" {
  filename         = "lambda_functions/localize_handler.zip"
  function_name    = "${local.name_prefix}-localize-handler"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "handler.lambda_handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  environment {
    variables = {
      SQS_QUEUE_URL     = aws_sqs_queue.video_processing.url
      DYNAMODB_TABLE    = aws_dynamodb_table.nativity_production.name
      REDIS_ENDPOINT    = aws_elasticache_replication_group.redis.primary_endpoint_address
      STEP_FUNCTION_ARN = aws_sfn_state_machine.video_processing.arn
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.localize_handler,
  ]

  tags = local.common_tags
}

# Lambda Permissions for API Gateway
resource "aws_lambda_permission" "upload_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "status_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "translate_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.translate_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "localize_handler" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.localize_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}