# 🚀 Nativity.AI AWS Deployment Guide

This guide walks you through deploying Nativity.AI to AWS, including both automated infrastructure deployment and manual AWS Console tasks.

## 📋 Prerequisites Checklist

### 1. Local Environment Setup
- [ ] **Terraform** installed (>= 1.0)
- [ ] **AWS CLI** installed and configured
- [ ] **Docker Desktop** running
- [ ] **PowerShell** (Windows) or **Bash** (Linux/Mac)
- [ ] **Git** for version control

### 2. AWS Account Requirements
- [ ] AWS Account with appropriate permissions
- [ ] AWS CLI configured with access keys
- [ ] Sufficient service quotas (see below)

### 3. API Keys and Secrets
- [ ] **Google Gemini API Key** (for AI processing)
- [ ] **Clerk Issuer URL** (for authentication)

## 🔧 AWS Console Setup Tasks

### Task 1: Verify Service Quotas
**Location**: AWS Console → Service Quotas

Check and request increases if needed:
- [ ] **ECS Tasks per Service**: At least 20
- [ ] **VPC per Region**: At least 5
- [ ] **Internet Gateways per Region**: At least 5
- [ ] **NAT Gateways per AZ**: At least 2
- [ ] **Application Load Balancers**: At least 5
- [ ] **ElastiCache Nodes**: At least 5

**How to check**:
1. Go to AWS Console → Service Quotas
2. Search for each service (ECS, VPC, EC2, ElastiCache)
3. Check current limits vs. requirements
4. Request increases if needed (can take 24-48 hours)

### Task 2: Create S3 Bucket for Terraform State (Recommended)
**Location**: AWS Console → S3

Create a bucket to store Terraform state remotely:
- [ ] Bucket name: `nativity-ai-terraform-state-{random-suffix}`
- [ ] Enable versioning
- [ ] Enable server-side encryption
- [ ] Block all public access

**Steps**:
1. Go to S3 Console
2. Click "Create bucket"
3. Name: `nativity-ai-terraform-state-{your-initials}-{random-number}`
4. Region: Same as your deployment region
5. Enable "Bucket Versioning"
6. Enable "Default encryption" with SSE-S3
7. Keep "Block all public access" enabled
8. Create bucket

### Task 3: Create IAM User for Deployment (Optional but Recommended)
**Location**: AWS Console → IAM

Create a dedicated user for deployments:
- [ ] Username: `nativity-ai-deployer`
- [ ] Attach policies: `PowerUserAccess` or custom policy
- [ ] Generate access keys
- [ ] Configure AWS CLI with these keys

**Steps**:
1. Go to IAM Console → Users
2. Click "Add users"
3. Username: `nativity-ai-deployer`
4. Select "Programmatic access"
5. Attach existing policies: `PowerUserAccess`
6. Create user and download access keys
7. Run `aws configure` with the new keys

### Task 4: Register Domain (Optional)
**Location**: AWS Console → Route 53 or External Domain Provider

If you want a custom domain:
- [ ] Register domain or transfer to Route 53
- [ ] Create hosted zone
- [ ] Note the domain name for configuration

## 🏗️ Infrastructure Deployment

### Step 1: Configure Terraform Variables

```bash
cd Nativity.AI/infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# Required Configuration
project_name = "nativity-ai"
environment  = "dev"  # Change to "prod" for production
aws_region   = "us-east-1"

# Required Secrets (GET THESE FROM YOUR PROVIDERS)
google_api_key    = "your-google-gemini-api-key-here"
clerk_issuer_url  = "your-clerk-issuer-url-here"

# Optional Domain Configuration
domain_name     = ""  # e.g., "api.nativity.ai"
certificate_arn = ""  # ACM certificate ARN if using custom domain

# Environment-specific Settings
# For Development:
ecs_api_cpu                = 256
ecs_api_memory            = 512
redis_node_type           = "cache.t3.micro"
enable_spot_instances     = true
log_retention_days        = 7

# For Production:
# ecs_api_cpu                = 1024
# ecs_api_memory            = 2048
# redis_node_type           = "cache.r6g.large"
# enable_spot_instances     = false
# log_retention_days        = 30
```

### Step 2: Deploy Infrastructure

```powershell
# Review what will be created
.\deploy.ps1 -Environment dev -Plan

# Deploy the infrastructure
.\deploy.ps1 -Environment dev

# For production (with auto-approval)
.\deploy.ps1 -Environment prod -AutoApprove
```

**Expected Output**:
- VPC and networking components
- ECS cluster and services
- SQS queues and SNS topics
- DynamoDB tables
- ElastiCache Redis cluster
- S3 buckets
- Lambda functions
- Step Functions workflows
- CloudWatch monitoring

### Step 3: Verify Infrastructure Deployment

**Check in AWS Console**:
- [ ] **ECS**: Cluster created but services not running (expected)
- [ ] **VPC**: New VPC with public/private subnets
- [ ] **SQS**: Three queues created (video-processing, high-priority, draft-creation)
- [ ] **DynamoDB**: Jobs and Users tables created
- [ ] **ElastiCache**: Redis cluster running
- [ ] **S3**: Storage bucket created
- [ ] **CloudWatch**: Dashboard and alarms configured

## 🐳 Application Deployment

### Step 4: Build and Deploy Docker Images

```powershell
# Build and deploy all services
.\build-and-deploy.ps1 -Environment dev

# Or deploy specific services
.\build-and-deploy.ps1 -Environment dev -Service api
.\build-and-deploy.ps1 -Environment dev -Service worker
```

**What this does**:
1. Builds Docker images for API and Worker services
2. Pushes images to ECR repositories
3. Updates ECS services with new task definitions
4. Waits for deployment to complete

### Step 5: Verify Application Deployment

**Check ECS Services**:
1. Go to ECS Console → Clusters → `nativity-ai-dev-cluster`
2. Check services are running:
   - [ ] `nativity-ai-dev-api` (2 tasks running)
   - [ ] `nativity-ai-dev-worker` (1 task running)

**Test API Endpoint**:
```bash
# Get the load balancer URL from Terraform output
curl http://your-load-balancer-url/health
# Should return: {"status": "healthy", "timestamp": "..."}
```

## 🔧 Post-Deployment Configuration

### Task 5: Configure SSL Certificate (If Using Custom Domain)
**Location**: AWS Console → Certificate Manager

1. Go to Certificate Manager
2. Request a public certificate
3. Add domain name (e.g., `api.nativity.ai`)
4. Choose DNS validation
5. Add CNAME records to your DNS
6. Wait for validation
7. Update `certificate_arn` in terraform.tfvars
8. Re-run deployment

### Task 6: Set Up DNS (If Using Custom Domain)
**Location**: AWS Console → Route 53

1. Go to Route 53 → Hosted zones
2. Select your domain
3. Create A record:
   - Name: `api` (or whatever subdomain)
   - Type: A - IPv4 address
   - Alias: Yes
   - Route traffic to: Application Load Balancer
   - Region: Your deployment region
   - Load balancer: Select your ALB

### Task 7: Configure Monitoring Alerts
**Location**: AWS Console → SNS

Set up email notifications for alerts:
1. Go to SNS Console
2. Find topics:
   - `nativity-ai-dev-alerts`
   - `nativity-ai-dev-critical-alerts`
3. Create subscriptions:
   - Protocol: Email
   - Endpoint: your-email@domain.com
4. Confirm subscriptions via email

### Task 8: Set Up CloudWatch Dashboard Access
**Location**: AWS Console → CloudWatch

1. Go to CloudWatch → Dashboards
2. Find `nativity-ai-dev-dashboard`
3. Bookmark the URL for easy access
4. Configure additional widgets if needed

## 🧪 Testing the Deployment

### Test 1: API Health Check
```bash
curl http://your-load-balancer-url/health
```

### Test 2: Upload a Video (Simulated)
```bash
# This would typically be done through your frontend
# For now, you can test by uploading to S3 directly
aws s3 cp test-video.mp4 s3://your-bucket-name/uploads/videos/test-user/standard/test-video.mp4
```

### Test 3: Check Job Processing
1. Go to DynamoDB Console
2. Check `nativity-ai-dev-jobs` table for new entries
3. Monitor SQS queues for message processing
4. Check CloudWatch logs for processing activity

### Test 4: Monitor Auto Scaling
1. Generate load on the API
2. Watch ECS services scale up in the console
3. Monitor CloudWatch metrics

## 📊 Monitoring and Maintenance

### Daily Monitoring
- [ ] Check CloudWatch dashboard
- [ ] Review any alarm notifications
- [ ] Monitor costs in AWS Cost Explorer

### Weekly Maintenance
- [ ] Review CloudWatch logs for errors
- [ ] Check ECS service health
- [ ] Monitor DynamoDB and S3 usage
- [ ] Review security group rules

### Monthly Tasks
- [ ] Update Docker base images
- [ ] Review and optimize costs
- [ ] Update Terraform modules
- [ ] Backup verification tests

## 🚨 Troubleshooting Common Issues

### Issue 1: ECS Tasks Failing to Start
**Symptoms**: Tasks start then immediately stop

**Solutions**:
1. Check CloudWatch logs: `/aws/ecs/nativity-ai-dev/api`
2. Verify environment variables in task definition
3. Check ECR image exists and is accessible
4. Verify IAM roles have correct permissions

### Issue 2: High Memory Usage
**Symptoms**: Tasks being killed due to memory

**Solutions**:
1. Increase memory allocation in terraform.tfvars
2. Optimize application memory usage
3. Enable memory monitoring alerts

### Issue 3: Queue Messages Not Processing
**Symptoms**: Messages stuck in SQS queues

**Solutions**:
1. Check worker service is running
2. Verify SQS permissions
3. Check dead letter queues for failed messages
4. Scale up worker instances

### Issue 4: High Costs
**Symptoms**: Unexpected AWS charges

**Solutions**:
1. Enable cost alerts
2. Use Spot instances for non-production
3. Implement S3 lifecycle policies
4. Right-size ECS tasks and Redis nodes

## 🔐 Security Checklist

### Network Security
- [ ] All resources in private subnets
- [ ] Security groups follow least privilege
- [ ] WAF enabled (if configured)
- [ ] VPC Flow Logs enabled

### Data Security
- [ ] Encryption at rest enabled (S3, DynamoDB, Redis)
- [ ] Encryption in transit (HTTPS/TLS)
- [ ] Secrets stored in Parameter Store
- [ ] No hardcoded credentials

### Access Control
- [ ] IAM roles with minimal permissions
- [ ] Regular access reviews
- [ ] MFA enabled for AWS accounts
- [ ] CloudTrail logging enabled

## 📞 Support and Next Steps

### If You Need Help
1. Check CloudWatch logs first
2. Review this troubleshooting guide
3. Check AWS service health dashboard
4. Contact AWS Support for service issues

### Next Steps After Deployment
1. **Frontend Integration**: Connect your React/Next.js frontend
2. **CI/CD Pipeline**: Set up GitHub Actions or similar
3. **Monitoring**: Configure additional custom metrics
4. **Scaling**: Optimize auto-scaling parameters
5. **Security**: Implement additional security measures
6. **Backup**: Test disaster recovery procedures

### Useful AWS Console URLs
- **ECS Cluster**: `https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters`
- **CloudWatch Dashboard**: `https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:`
- **SQS Queues**: `https://console.aws.amazon.com/sqs/v2/home?region=us-east-1#/queues`
- **DynamoDB Tables**: `https://console.aws.amazon.com/dynamodb/home?region=us-east-1#tables:`

---

🎉 **Congratulations!** You now have a production-ready, scalable Nativity.AI deployment on AWS!