# 🚀 Nativity.AI AWS Migration - Complete Step-by-Step Guide

## 📋 Overview
This guide will take you from your current local setup to a fully deployed AWS cloud infrastructure in approximately 45 minutes.

---

## 🔧 PHASE 1: Prerequisites Setup (15 minutes)

### Step 1.1: Install Required Tools

**On Windows:**
```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install tools
choco install terraform awscli docker-desktop git -y

# Restart PowerShell after installation
```

**Verify installations:**
```powershell
terraform version
aws --version
docker --version
git --version
```

### Step 1.2: Configure AWS CLI

**Get AWS Access Keys:**
1. Go to **AWS Console → IAM → Users → Your User → Security Credentials**
2. Click **"Create access key"**
3. Select **"Command Line Interface (CLI)"**
4. Download the CSV file with your keys

**Configure AWS CLI:**
```powershell
aws configure
# Enter when prompted:
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: us-east-1
# Default output format: json
```

**Test AWS connection:**
```powershell
aws sts get-caller-identity
# Should return your account info
```

### Step 1.3: Get Required API Keys

**Google Gemini API Key:**
1. Go to **https://makersuite.google.com/app/apikey**
2. Click **"Create API Key"**
3. Copy the key (starts with `AIza...`)

**Clerk Authentication URL:**
1. Go to your **Clerk Dashboard → Configure → JWT Templates**
2. Copy your **Issuer URL** (looks like `https://your-app.clerk.accounts.dev`)

---

## 🏗️ PHASE 2: Infrastructure Deployment (15 minutes)

### Step 2.1: Configure Terraform Variables

**Navigate to infrastructure directory:**
```powershell
cd Nativity.AI/infrastructure
```

**Copy and edit configuration:**
```powershell
cp terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

**Edit terraform.tfvars with your values:**
```hcl
# Project Configuration
project_name = "nativity-ai"
environment  = "dev"
aws_region   = "us-east-1"

# REQUIRED: Replace with your actual values
google_api_key    = "AIza_your_google_api_key_here"
clerk_issuer_url  = "https://your-app.clerk.accounts.dev"

# Network Configuration
vpc_cidr           = "10.0.0.0/16"
availability_zones = 2

# ECS Configuration (Development settings)
ecs_api_cpu                = 512
ecs_api_memory            = 1024
ecs_worker_cpu            = 1024
ecs_worker_memory         = 2048
ecs_api_desired_count     = 2
ecs_worker_desired_count  = 1

# Auto Scaling
api_autoscaling_min_capacity    = 1
api_autoscaling_max_capacity    = 10
worker_autoscaling_min_capacity = 1
worker_autoscaling_max_capacity = 20

# Cost Optimization (Development)
redis_node_type        = "cache.t3.micro"
enable_spot_instances  = true
log_retention_days     = 14

# Security (IMPORTANT: Restrict in production)
allowed_cidr_blocks = ["0.0.0.0/0"]
enable_waf         = true

# Monitoring
enable_detailed_monitoring = true
backup_retention_days     = 7
```

### Step 2.2: Deploy Infrastructure

**Plan the deployment (review what will be created):**
```powershell
.\deploy.ps1 -Environment dev -Plan
```

**Deploy the infrastructure:**
```powershell
.\deploy.ps1 -Environment dev
```

**Expected output:**
```
🌟 Nativity.AI Infrastructure Deployment
Environment: dev
🔍 Checking prerequisites...
✅ Terraform found: Terraform v1.x.x
✅ AWS CLI configured for account: 123456789012
✅ All prerequisites met!
🚀 Initializing Terraform...
✅ Terraform initialized successfully!
📋 Planning infrastructure changes...
✅ Terraform plan completed successfully!
🏗️ Applying infrastructure changes...
✅ Infrastructure deployed successfully!
```

**Save the outputs:**
```powershell
terraform output > deployment-outputs.txt
```

---

## 🐳 PHASE 3: Application Deployment (10 minutes)

### Step 3.1: Verify Docker is Running

```powershell
docker ps
# Should show running containers or empty list (not error)
```

### Step 3.2: Build and Deploy Applications

**Deploy all services:**
```powershell
.\build-and-deploy.ps1 -Environment dev
```

**Expected output:**
```
🌟 Nativity.AI Docker Build and Deploy
Environment: dev
Service: all
Tag: latest
🔍 Checking prerequisites...
✅ Docker is running
✅ AWS CLI configured for account: 123456789012
🔐 Logging into ECR...
✅ Successfully logged into ECR
🚀 Deploying api service...
🏗️ Building api Docker image...
✅ Successfully built api image
📤 Pushing api Docker images...
✅ Successfully pushed api images
🔄 Updating ECS service: nativity-ai-dev-api...
✅ Successfully triggered ECS service update for api
⏳ Waiting for deployment to complete for api...
✅ Deployment completed successfully for api
```

---

## ✅ PHASE 4: Verification & Testing (5 minutes)

### Step 4.1: Check Infrastructure in AWS Console

**ECS Services:**
1. Go to **AWS Console → ECS → Clusters**
2. Click **"nativity-ai-dev-cluster"**
3. Verify services are running:
   - ✅ `nativity-ai-dev-api` (2/2 tasks running)
   - ✅ `nativity-ai-dev-worker` (1/1 tasks running)

**Load Balancer:**
1. Go to **AWS Console → EC2 → Load Balancers**
2. Find **"nativity-ai-dev-alb"**
3. Copy the **DNS name** (e.g., `nativity-ai-dev-alb-123456789.us-east-1.elb.amazonaws.com`)

### Step 4.2: Test API Endpoint

**Get your API URL:**
```powershell
terraform output load_balancer_dns_name
```

**Test health endpoint:**
```powershell
# Replace with your actual load balancer DNS
curl http://nativity-ai-dev-alb-123456789.us-east-1.elb.amazonaws.com/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "service": "nativity-ai-api"
}
```

### Step 4.3: Verify Database and Queues

**DynamoDB Tables:**
1. Go to **AWS Console → DynamoDB → Tables**
2. Verify tables exist:
   - ✅ `nativity-ai-dev-jobs`
   - ✅ `nativity-ai-dev-users`

**SQS Queues:**
1. Go to **AWS Console → SQS**
2. Verify queues exist:
   - ✅ `nativity-ai-dev-video-processing`
   - ✅ `nativity-ai-dev-high-priority`
   - ✅ `nativity-ai-dev-draft-creation`

---

## 📊 PHASE 5: Monitoring Setup (5 minutes)

### Step 5.1: Access CloudWatch Dashboard

**Get dashboard URL:**
```powershell
terraform output cloudwatch_dashboard_url
```

**Or manually navigate:**
1. Go to **AWS Console → CloudWatch → Dashboards**
2. Click **"nativity-ai-dev-dashboard"**
3. Bookmark this URL for monitoring

### Step 5.2: Set Up Email Alerts

**Configure SNS notifications:**
1. Go to **AWS Console → SNS → Topics**
2. Find **"nativity-ai-dev-alerts"**
3. Click **"Create subscription"**
4. Protocol: **Email**
5. Endpoint: **your-email@domain.com**
6. Click **"Create subscription"**
7. Check your email and **confirm subscription**

**Repeat for critical alerts:**
1. Find **"nativity-ai-dev-critical-alerts"**
2. Create email subscription
3. Confirm subscription

---

## 🧪 PHASE 6: Test Complete System (5 minutes)

### Step 6.1: Test Video Upload Simulation

**Upload a test file to S3:**
```powershell
# Create a test file
echo "test video content" > test-video.txt

# Get your S3 bucket name
$bucketName = terraform output -raw s3_bucket_name

# Upload test file
aws s3 cp test-video.txt s3://$bucketName/uploads/videos/test-user/standard/test-video.mp4
```

### Step 6.2: Monitor Job Processing

**Check DynamoDB for new job:**
1. Go to **AWS Console → DynamoDB → Tables → nativity-ai-dev-jobs**
2. Click **"Explore table items"**
3. Look for new job entry

**Check SQS queue activity:**
1. Go to **AWS Console → SQS → nativity-ai-dev-video-processing**
2. Monitor **"Messages available"** count

**Check CloudWatch logs:**
1. Go to **AWS Console → CloudWatch → Log groups**
2. Check logs in:
   - `/aws/ecs/nativity-ai-dev/api`
   - `/aws/ecs/nativity-ai-dev/worker`
   - `/aws/lambda/nativity-ai-dev-video-processor`

---

## 🎯 SUCCESS CRITERIA

After completing all steps, you should have:

### ✅ Infrastructure Running
- [ ] **ECS Cluster**: Running with API and Worker services
- [ ] **Load Balancer**: Responding to health checks
- [ ] **Databases**: DynamoDB tables created and accessible
- [ ] **Queues**: SQS queues ready for job processing
- [ ] **Storage**: S3 bucket configured with lifecycle policies
- [ ] **Caching**: Redis cluster running and accessible

### ✅ Monitoring Active
- [ ] **CloudWatch Dashboard**: Showing real-time metrics
- [ ] **Email Alerts**: Configured and confirmed
- [ ] **Auto Scaling**: Configured and ready to scale
- [ ] **Health Checks**: All services passing health checks

### ✅ Security Configured
- [ ] **VPC Isolation**: All resources in private subnets
- [ ] **Encryption**: Enabled for all data stores
- [ ] **IAM Roles**: Least privilege access configured
- [ ] **Secrets**: Stored securely in Parameter Store

---

## 🚨 TROUBLESHOOTING

### Issue: Terraform Apply Fails
**Solution:**
```powershell
# Check AWS credentials
aws sts get-caller-identity

# Check service quotas
aws service-quotas get-service-quota --service-code ecs --quota-code L-34B43A08

# Re-run with verbose logging
terraform apply -var="environment=dev" -auto-approve
```

### Issue: ECS Tasks Not Starting
**Solution:**
1. Go to **ECS Console → Clusters → Services → Tasks**
2. Click on **stopped task**
3. Check **"Stopped reason"**
4. Common fixes:
   - Increase memory allocation
   - Check ECR image exists
   - Verify IAM permissions

### Issue: API Health Check Fails
**Solution:**
```powershell
# Check ECS service status
aws ecs describe-services --cluster nativity-ai-dev-cluster --services nativity-ai-dev-api

# Check CloudWatch logs
aws logs tail /aws/ecs/nativity-ai-dev/api --follow
```

### Issue: High Costs
**Solution:**
1. **Enable Spot Instances**: Set `enable_spot_instances = true`
2. **Reduce Resources**: Lower CPU/memory in terraform.tfvars
3. **Monitor Usage**: Check CloudWatch metrics for actual usage

---

## 📈 NEXT STEPS

### Immediate (Today)
1. **Test all API endpoints** with your frontend
2. **Upload a real video** and verify processing
3. **Monitor costs** in AWS Cost Explorer
4. **Document your API URLs** for team access

### This Week
1. **Set up CI/CD pipeline** for automated deployments
2. **Configure custom domain** and SSL certificate
3. **Load test** the system to verify auto-scaling
4. **Security review** and hardening

### This Month
1. **Production environment** deployment
2. **Disaster recovery** testing
3. **Performance optimization** based on real usage
4. **Advanced monitoring** and custom metrics

---

## 📞 SUPPORT

### Getting Help
- **AWS Documentation**: https://docs.aws.amazon.com/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/
- **CloudWatch Dashboard**: Use the URL from terraform output
- **Cost Monitoring**: AWS Cost Explorer in console

### Emergency Contacts
- **AWS Support**: Available through AWS Console
- **Critical Issues**: Check CloudWatch alarms first
- **Cost Alerts**: Set up billing alerts in AWS Console

---

## 🎉 CONGRATULATIONS!

You have successfully migrated Nativity.AI to AWS! Your infrastructure is now:

- **🚀 Scalable**: Auto-scales based on demand
- **🔒 Secure**: VPC isolated with encryption
- **📊 Monitored**: CloudWatch dashboards and alerts
- **💰 Cost-Optimized**: Spot instances and intelligent tiering
- **🌍 Production-Ready**: High availability across multiple AZs

**Your API is now live at:** `http://your-load-balancer-dns-name`

**Total deployment time:** ~45 minutes  
**Monthly cost estimate:** $70-145 for development environment

Ready to process thousands of videos in the cloud! 🎬✨