# ECS Infrastructure for Nativity.AI

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
  
  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      
      log_configuration {
        cloud_watch_encryption_enabled = true
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.ecs_exec.name
      }
    }
  }
  
  setting {
    name  = "containerInsights"
    value = var.enable_detailed_monitoring ? "enabled" : "disabled"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-cluster"
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs_exec" {
  name              = "/aws/ecs/${local.name_prefix}/exec"
  retention_in_days = var.log_retention_days
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-exec-logs"
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/ecs/${local.name_prefix}/api"
  retention_in_days = var.log_retention_days
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-logs"
  })
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/ecs/${local.name_prefix}/worker"
  retention_in_days = var.log_retention_days
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-worker-logs"
  })
}

# IAM Roles for ECS

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-task-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-task-execution-role"
  })
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for accessing secrets and parameters
resource "aws_iam_role_policy" "ecs_task_execution_custom" {
  name = "${local.name_prefix}-ecs-task-execution-custom"
  role = aws_iam_role.ecs_task_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "ssm:GetParameters",
          "ssm:GetParameter",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:${local.name_prefix}/*",
          "arn:aws:ssm:${local.region}:${local.account_id}:parameter/${local.name_prefix}/*"
        ]
      }
    ]
  })
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-task-role"
  })
}

# Policy for ECS tasks to access AWS services
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${local.name_prefix}-ecs-task-policy"
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ChangeMessageVisibility"
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
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.jobs.arn,
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.jobs.arn}/index/*",
          "${aws_dynamodb_table.users.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.storage.arn,
          "${aws_s3_bucket.storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.api.arn}:*",
          "${aws_cloudwatch_log_group.worker.arn}:*"
        ]
      }
    ]
  })
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = aws_subnet.public[*].id
  
  enable_deletion_protection = false  # Set to true in production
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb"
  })
}

# ALB Target Group for API
resource "aws_lb_target_group" "api" {
  name        = "${local.name_prefix}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-target-group"
  })
}

# ALB Listener
resource "aws_lb_listener" "api" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-listener"
  })
}

# ECS Task Definitions

# API Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name_prefix}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_api_cpu
  memory                   = var.ecs_api_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/${aws_ecr_repository.api.name}:latest"
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "NODE_ENV"
          value = var.environment
        },
        {
          name  = "PORT"
          value = "8000"
        },
        {
          name  = "REDIS_HOST"
          value = aws_elasticache_replication_group.redis.configuration_endpoint_address
        },
        {
          name  = "REDIS_PORT"
          value = tostring(aws_elasticache_replication_group.redis.port)
        },
        {
          name  = "VIDEO_PROCESSING_QUEUE_URL"
          value = aws_sqs_queue.video_processing.url
        },
        {
          name  = "HIGH_PRIORITY_QUEUE_URL"
          value = aws_sqs_queue.high_priority.url
        },
        {
          name  = "DRAFT_CREATION_QUEUE_URL"
          value = aws_sqs_queue.draft_creation.url
        },
        {
          name  = "JOBS_TABLE_NAME"
          value = aws_dynamodb_table.jobs.name
        },
        {
          name  = "USERS_TABLE_NAME"
          value = aws_dynamodb_table.users.name
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.storage.bucket
        },
        {
          name  = "AWS_REGION"
          value = local.region
        }
      ]
      
      secrets = [
        {
          name      = "GOOGLE_API_KEY"
          valueFrom = aws_ssm_parameter.google_api_key.arn
        },
        {
          name      = "CLERK_ISSUER_URL"
          valueFrom = aws_ssm_parameter.clerk_issuer_url.arn
        },
        {
          name      = "REDIS_AUTH_TOKEN"
          valueFrom = aws_ssm_parameter.redis_auth_token.arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      essential = true
    }
  ])
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-task-definition"
  })
}

# Worker Task Definition
resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_worker_cpu
  memory                   = var.ecs_worker_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name  = "worker"
      image = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com/${aws_ecr_repository.worker.name}:latest"
      
      environment = [
        {
          name  = "NODE_ENV"
          value = var.environment
        },
        {
          name  = "REDIS_HOST"
          value = aws_elasticache_replication_group.redis.configuration_endpoint_address
        },
        {
          name  = "REDIS_PORT"
          value = tostring(aws_elasticache_replication_group.redis.port)
        },
        {
          name  = "VIDEO_PROCESSING_QUEUE_URL"
          value = aws_sqs_queue.video_processing.url
        },
        {
          name  = "HIGH_PRIORITY_QUEUE_URL"
          value = aws_sqs_queue.high_priority.url
        },
        {
          name  = "DRAFT_CREATION_QUEUE_URL"
          value = aws_sqs_queue.draft_creation.url
        },
        {
          name  = "JOBS_TABLE_NAME"
          value = aws_dynamodb_table.jobs.name
        },
        {
          name  = "USERS_TABLE_NAME"
          value = aws_dynamodb_table.users.name
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.storage.bucket
        },
        {
          name  = "AWS_REGION"
          value = local.region
        }
      ]
      
      secrets = [
        {
          name      = "GOOGLE_API_KEY"
          valueFrom = aws_ssm_parameter.google_api_key.arn
        },
        {
          name      = "REDIS_AUTH_TOKEN"
          valueFrom = aws_ssm_parameter.redis_auth_token.arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      essential = true
    }
  ])
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-worker-task-definition"
  })
}

# ECS Services

# API Service
resource "aws_ecs_service" "api" {
  name            = "${local.name_prefix}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.ecs_api_desired_count
  launch_type     = "FARGATE"
  
  network_configuration {
    security_groups  = [aws_security_group.ecs.id]
    subnets         = aws_subnet.private[*].id
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  
  depends_on = [aws_lb_listener.api]
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api-service"
  })
}

# Worker Service
resource "aws_ecs_service" "worker" {
  name            = "${local.name_prefix}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.ecs_worker_desired_count
  launch_type     = "FARGATE"
  
  network_configuration {
    security_groups  = [aws_security_group.ecs.id]
    subnets         = aws_subnet.private[*].id
    assign_public_ip = false
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-worker-service"
  })
}

# Outputs
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}