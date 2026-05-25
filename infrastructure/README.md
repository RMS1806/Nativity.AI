# Nativity.AI AWS Infrastructure

This directory contains the complete AWS infrastructure as code for Nativity.AI using Terraform. The infrastructure provides a production-ready, scalable, and secure cloud environment for video processing and AI-powered content generation.

## 🏗️ Architecture Overview

### Core Components

- **API Gateway + Lambda Functions**: Serverless API endpoints
- **ECS Fargate Clusters**: Managed container orchestration for API and worker services
- **SQS Queues**: Reliable message queuing for job processing
- **Step Functions**: Visual workflow automation and orchestration
- **ElastiCache Redis**: High-performance caching and session storage
- **DynamoDB**: NoSQL database for jobs and user data
- **S3**: Object storage for videos and processed content
- **CloudWatch**: Comprehensive monitoring and alerting

### Infrastructure Features

- ✅ **Auto Scaling**: Automatic scaling based on CPU, memory, and queue depth
- ✅ **High Availability**: Multi-AZ deployment with load balancing
- ✅ **Security**: VPC isolation, encryption at rest and in transit
- ✅ **Monitoring**: CloudWatch dashboards, alarms, and log aggregation
- ✅ **Cost Optimization**: Intelligent tiering, spot instances (optional)
- ✅ **Backup & Recovery**: Automated backups and point-in-time recovery

## 📋 Prerequisites

### Required Tools

1. **Terraform** (>= 1.0)
   ```bash
   # Windows (using Chocolatey)
   choco install terraform
   
   # Or download from: https://www.terraform.io/downloads
   ```

2. **AWS CLI** (>= 2.0)
   ```bash
   # Windows (using Chocolatey)
   choco install awscli
   
   # Configure with your credentials
   aws configure
   ```

3. **Docker Desktop**
   ```bash
   # Download from: https://www.docker.com/products/docker-desktop
   ```

### AWS Account Setup

1. **IAM Permissions**: Ensure your AWS user has the following permissions:
   - EC2, ECS, ECR (full access)
   - VPC, ALB, Route53 (full access)
   - SQS, SNS, Step Functions (full access)
   - DynamoDB, S3, ElastiCache (full access)
   - CloudWatch, Lambda (full access)
   - IAM (limited to creating service roles)

2. **Service Quotas**: Verify you have sufficient quotas for:
   - ECS tasks (at least 20)
   - VPC resources (subnets, security groups)
   - ElastiCache nodes

## 🚀 Quick Start

### 1. Configure Variables

```bash
# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
notepad terraform.tfvars
```

**Required Variables:**
```hcl
# Application Secrets
google_api_key   = "your-google-gemini-api-key"
clerk_issuer_url = "your-clerk-issuer-url"

# Environment Configuration
environment = "dev"  # or "staging", "prod"
aws_region  = "us-east-1"
```

### 2. Deploy Infrastructure

```powershell
# Plan the deployment (review changes)
.\deploy.ps1 -Environment dev -Plan

# Deploy the infrastructure
.\deploy.ps1 -Environment dev

# For production with auto-approval
.\deploy.ps1 -Environment prod -AutoApprove
```

### 3. Build and Deploy Applications

```powershell
# Build and deploy all services
.\build-and-deploy.ps1 -Environment dev

# Deploy specific service
.\build-and-deploy.ps1 -Environment dev -Service api
```

## 📁 File Structure

```
infrastructure/
├── main.tf                 # Main Terraform configuration
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── vpc.tf                  # VPC and networking
├── ecs.tf                  # ECS cluster and services
├── ecr.tf                  # Container registries
├── sqs.tf                  # Message queues
├── redis.tf                # ElastiCache Redis
├── dynamodb.tf             # DynamoDB tables
├── s3.tf                   # S3 storage
├── lambda.tf               # Lambda functions
├── api-gateway.tf          # API Gateway
├── step-functions.tf       # Step Functions workflows
├── autoscaling.tf          # Auto scaling configuration
├── monitoring.tf           # CloudWatch monitoring
├── ssm.tf                  # Parameter store
├── deploy.ps1              # Deployment script
├── build-and-deploy.ps1    # Docker build/deploy script
└── terraform.tfvars.example # Example variables
```

## 🔧 Configuration

### Environment-Specific Settings

#### Development
```hcl
environment = "dev"
ecs_api_cpu = 256
ecs_api_memory = 512
redis_node_type = "cache.t3.micro"
enable_spot_instances = true
log_retention_days = 7
```

#### Staging
```hcl
environment = "staging"
ecs_api_cpu = 512
ecs_api_memory = 1024
redis_node_type = "cache.t3.small"
enable_spot_instances = false
log_retention_days = 14
```

#### Production
```hcl
environment = "prod"
ecs_api_cpu = 1024
ecs_api_memory = 2048
redis_node_type = "cache.r6g.large"
enable_spot_instances = false
log_retention_days = 30
backup_retention_days = 30
```

### Auto Scaling Configuration

The infrastructure includes intelligent auto scaling based on:

- **CPU Utilization**: Scale when CPU > 70% (API) or > 60% (Worker)
- **Memory Utilization**: Scale when memory > 80% (API) or > 70% (Worker)
- **Queue Depth**: Scale workers when SQS messages > 10 per worker
- **Request Count**: Scale API when requests > 1000 per minute per instance

### Security Configuration

- **VPC Isolation**: All resources deployed in private subnets
- **Security Groups**: Least privilege access rules
- **Encryption**: At rest (S3, DynamoDB, Redis) and in transit (TLS)
- **Secrets Management**: AWS Systems Manager Parameter Store
- **WAF**: Optional Web Application Firewall for additional protection

## 📊 Monitoring & Alerting

### CloudWatch Dashboard

Access your monitoring dashboard:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=nativity-ai-dev-dashboard
```

### Key Metrics Monitored

- **ECS Services**: CPU, memory, task count
- **SQS Queues**: Message count, processing time
- **Redis**: CPU, memory, connections
- **DynamoDB**: Read/write capacity, throttling
- **Load Balancer**: Response time, error rates
- **Application**: Job success/failure rates, processing time

### Alerts Configuration

Alerts are sent to SNS topics for:
- High CPU/memory utilization
- Failed job processing
- Queue depth issues
- Application errors
- Infrastructure failures

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to AWS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy Infrastructure
        run: |
          cd infrastructure
          terraform init
          terraform plan -var="environment=prod"
          terraform apply -auto-approve -var="environment=prod"
      
      - name: Build and Deploy Applications
        run: |
          cd infrastructure
          ./build-and-deploy.ps1 -Environment prod -AutoApprove
```

## 🛠️ Maintenance

### Regular Tasks

1. **Update Dependencies**
   ```bash
   terraform init -upgrade
   ```

2. **Review Costs**
   - Monitor AWS Cost Explorer
   - Review CloudWatch billing alarms
   - Optimize unused resources

3. **Security Updates**
   - Update container base images
   - Review security group rules
   - Rotate secrets regularly

4. **Backup Verification**
   - Test DynamoDB point-in-time recovery
   - Verify S3 cross-region replication (prod)

### Scaling Considerations

- **Vertical Scaling**: Increase CPU/memory for ECS tasks
- **Horizontal Scaling**: Adjust auto scaling limits
- **Database Scaling**: Switch to DynamoDB on-demand mode for unpredictable workloads
- **Cache Scaling**: Upgrade Redis node type or add read replicas

## 🚨 Troubleshooting

### Common Issues

1. **ECS Tasks Failing to Start**
   ```bash
   # Check ECS service events
   aws ecs describe-services --cluster nativity-ai-dev-cluster --services nativity-ai-dev-api
   
   # Check CloudWatch logs
   aws logs tail /aws/ecs/nativity-ai-dev/api --follow
   ```

2. **High Queue Depth**
   ```bash
   # Check worker scaling
   aws application-autoscaling describe-scalable-targets --service-namespace ecs
   
   # Manual scaling if needed
   aws ecs update-service --cluster nativity-ai-dev-cluster --service nativity-ai-dev-worker --desired-count 5
   ```

3. **Database Connection Issues**
   ```bash
   # Check security group rules
   aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx
   
   # Test connectivity from ECS task
   aws ecs execute-command --cluster nativity-ai-dev-cluster --task task-id --interactive --command "/bin/bash"
   ```

### Log Analysis

```bash
# API logs
aws logs filter-log-events --log-group-name /aws/ecs/nativity-ai-dev/api --filter-pattern "ERROR"

# Worker logs
aws logs filter-log-events --log-group-name /aws/ecs/nativity-ai-dev/worker --filter-pattern "Job failed"

# Step Functions logs
aws logs filter-log-events --log-group-name /aws/stepfunctions/nativity-ai-dev --start-time 1640995200000
```

## 💰 Cost Optimization

### Development Environment
- Use `t3.micro` instances
- Enable spot instances
- Reduce log retention to 7 days
- Use smaller Redis cache nodes

### Production Environment
- Enable S3 Intelligent Tiering
- Use Reserved Instances for predictable workloads
- Implement lifecycle policies for old data
- Monitor and right-size resources regularly

### Cost Monitoring
```bash
# Get current month costs
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost
```

## 🔐 Security Best Practices

1. **Network Security**
   - All resources in private subnets
   - NAT Gateways for outbound internet access
   - Security groups with least privilege

2. **Data Protection**
   - Encryption at rest for all storage
   - TLS 1.2+ for all communications
   - Regular security patches

3. **Access Control**
   - IAM roles with minimal permissions
   - No hardcoded credentials
   - Regular access reviews

4. **Monitoring**
   - CloudTrail for API logging
   - GuardDuty for threat detection
   - Config for compliance monitoring

## 📞 Support

For infrastructure issues:
1. Check CloudWatch logs and metrics
2. Review Terraform state for configuration drift
3. Consult AWS documentation for service-specific issues
4. Contact AWS Support for service limits or account issues

## 🔄 Disaster Recovery

### Backup Strategy
- **DynamoDB**: Point-in-time recovery enabled
- **S3**: Cross-region replication (production)
- **Redis**: Daily snapshots
- **Infrastructure**: Terraform state in S3 with versioning

### Recovery Procedures
1. **Infrastructure**: Redeploy using Terraform
2. **Data**: Restore from DynamoDB backups
3. **Files**: Restore from S3 cross-region replica
4. **Cache**: Rebuild Redis cache from application data

This infrastructure provides a robust, scalable foundation for Nativity.AI's video processing and AI content generation platform. Regular monitoring and maintenance ensure optimal performance and cost efficiency.