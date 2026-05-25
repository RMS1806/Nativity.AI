# PowerShell Script to Build and Deploy Docker Images to AWS ECR
# Usage: .\build-and-deploy.ps1 -Environment dev|staging|prod [-Service api|worker|all]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,
    
    [ValidateSet("api", "worker", "all")]
    [string]$Service = "all",
    
    [string]$Tag = "latest"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = $Reset)
    Write-Host "$Color$Message$Reset"
}

function Get-TerraformOutput {
    param([string]$OutputName)
    
    try {
        $output = terraform output -raw $OutputName 2>$null
        return $output
    }
    catch {
        Write-ColorOutput "❌ Failed to get Terraform output: $OutputName" $Red
        exit 1
    }
}

function Login-ECR {
    param([string]$Region, [string]$AccountId)
    
    Write-ColorOutput "🔐 Logging into ECR..." $Blue
    
    try {
        $loginCommand = aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"
        Write-ColorOutput "✅ Successfully logged into ECR" $Green
    }
    catch {
        Write-ColorOutput "❌ Failed to login to ECR: $_" $Red
        exit 1
    }
}

function Build-DockerImage {
    param(
        [string]$ServiceName,
        [string]$DockerfilePath,
        [string]$RepositoryUri,
        [string]$Tag
    )
    
    Write-ColorOutput "🏗️ Building $ServiceName Docker image..." $Blue
    
    $imageTag = "$RepositoryUri:$Tag"
    $envTag = "$RepositoryUri:$Environment-$Tag"
    
    try {
        # Build the image
        docker build -t $imageTag -f $DockerfilePath .
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
        
        # Tag with environment
        docker tag $imageTag $envTag
        if ($LASTEXITCODE -ne 0) {
            throw "Docker tag failed"
        }
        
        Write-ColorOutput "✅ Successfully built $ServiceName image" $Green
        return @($imageTag, $envTag)
    }
    catch {
        Write-ColorOutput "❌ Failed to build $ServiceName image: $_" $Red
        exit 1
    }
}

function Push-DockerImage {
    param([string[]]$ImageTags, [string]$ServiceName)
    
    Write-ColorOutput "📤 Pushing $ServiceName Docker images..." $Blue
    
    try {
        foreach ($tag in $ImageTags) {
            Write-ColorOutput "Pushing $tag..." $Yellow
            docker push $tag
            if ($LASTEXITCODE -ne 0) {
                throw "Docker push failed for $tag"
            }
        }
        
        Write-ColorOutput "✅ Successfully pushed $ServiceName images" $Green
    }
    catch {
        Write-ColorOutput "❌ Failed to push $ServiceName images: $_" $Red
        exit 1
    }
}

function Update-ECSService {
    param([string]$ClusterName, [string]$ServiceName)
    
    Write-ColorOutput "🔄 Updating ECS service: $ServiceName..." $Blue
    
    try {
        aws ecs update-service --cluster $ClusterName --service $ServiceName --force-new-deployment
        if ($LASTEXITCODE -ne 0) {
            throw "ECS service update failed"
        }
        
        Write-ColorOutput "✅ Successfully triggered ECS service update for $ServiceName" $Green
    }
    catch {
        Write-ColorOutput "❌ Failed to update ECS service $ServiceName`: $_" $Red
        exit 1
    }
}

function Wait-ForDeployment {
    param([string]$ClusterName, [string]$ServiceName)
    
    Write-ColorOutput "⏳ Waiting for deployment to complete for $ServiceName..." $Yellow
    
    try {
        aws ecs wait services-stable --cluster $ClusterName --services $ServiceName
        if ($LASTEXITCODE -ne 0) {
            throw "Deployment wait failed"
        }
        
        Write-ColorOutput "✅ Deployment completed successfully for $ServiceName" $Green
    }
    catch {
        Write-ColorOutput "❌ Deployment failed or timed out for $ServiceName`: $_" $Red
        exit 1
    }
}

function Deploy-Service {
    param([string]$ServiceName)
    
    Write-ColorOutput "`n🚀 Deploying $ServiceName service..." $Blue
    
    # Get repository URI from Terraform outputs
    $repositoryUri = Get-TerraformOutput "${ServiceName}_repository_url"
    
    # Determine Dockerfile path
    $dockerfilePath = switch ($ServiceName) {
        "api" { "../api/Dockerfile" }
        "worker" { "../worker/Dockerfile" }
    }
    
    # Check if Dockerfile exists
    if (-not (Test-Path $dockerfilePath)) {
        Write-ColorOutput "❌ Dockerfile not found: $dockerfilePath" $Red
        Write-ColorOutput "Please ensure the Dockerfile exists in the correct location." $Yellow
        return
    }
    
    # Build and push Docker image
    $imageTags = Build-DockerImage -ServiceName $ServiceName -DockerfilePath $dockerfilePath -RepositoryUri $repositoryUri -Tag $Tag
    Push-DockerImage -ImageTags $imageTags -ServiceName $ServiceName
    
    # Update ECS service
    $clusterName = Get-TerraformOutput "ecs_cluster_name"
    $ecsServiceName = "nativity-ai-$Environment-$ServiceName"
    
    Update-ECSService -ClusterName $clusterName -ServiceName $ecsServiceName
    Wait-ForDeployment -ClusterName $clusterName -ServiceName $ecsServiceName
}

function Check-Prerequisites {
    Write-ColorOutput "🔍 Checking prerequisites..." $Blue
    
    # Check if Docker is running
    try {
        docker version | Out-Null
        Write-ColorOutput "✅ Docker is running" $Green
    }
    catch {
        Write-ColorOutput "❌ Docker is not running. Please start Docker first." $Red
        exit 1
    }
    
    # Check if AWS CLI is configured
    try {
        $awsIdentity = aws sts get-caller-identity 2>$null
        if ($awsIdentity) {
            $identity = $awsIdentity | ConvertFrom-Json
            Write-ColorOutput "✅ AWS CLI configured for account: $($identity.Account)" $Green
        }
        else {
            Write-ColorOutput "❌ AWS CLI not configured. Please run 'aws configure' first." $Red
            exit 1
        }
    }
    catch {
        Write-ColorOutput "❌ AWS CLI not found or not configured." $Red
        exit 1
    }
    
    # Check if we're in the infrastructure directory
    if (-not (Test-Path "main.tf")) {
        Write-ColorOutput "❌ Please run this script from the infrastructure directory." $Red
        exit 1
    }
}

function Main {
    Write-ColorOutput "🌟 Nativity.AI Docker Build and Deploy" $Blue
    Write-ColorOutput "Environment: $Environment" $Yellow
    Write-ColorOutput "Service: $Service" $Yellow
    Write-ColorOutput "Tag: $Tag" $Yellow
    
    # Change to infrastructure directory
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptPath
    
    try {
        Check-Prerequisites
        
        # Get AWS account info
        $accountId = Get-TerraformOutput "account_id"
        $region = Get-TerraformOutput "region"
        
        # Login to ECR
        Login-ECR -Region $region -AccountId $accountId
        
        # Deploy services
        if ($Service -eq "all") {
            Deploy-Service -ServiceName "api"
            Deploy-Service -ServiceName "worker"
        }
        else {
            Deploy-Service -ServiceName $Service
        }
        
        Write-ColorOutput "`n🎉 Build and deployment completed successfully!" $Green
        Write-ColorOutput "Next steps:" $Blue
        Write-ColorOutput "1. Check ECS service status in AWS Console" $Reset
        Write-ColorOutput "2. Monitor CloudWatch logs for any issues" $Reset
        Write-ColorOutput "3. Test the API endpoints" $Reset
        Write-ColorOutput "4. Verify job processing is working" $Reset
        
        # Show useful URLs
        $loadBalancerDns = Get-TerraformOutput "load_balancer_dns_name"
        $dashboardUrl = Get-TerraformOutput "cloudwatch_dashboard_url"
        
        Write-ColorOutput "`nUseful URLs:" $Blue
        Write-ColorOutput "API Endpoint: http://$loadBalancerDns" $Reset
        Write-ColorOutput "CloudWatch Dashboard: $dashboardUrl" $Reset
    }
    catch {
        Write-ColorOutput "❌ Build and deployment failed: $_" $Red
        exit 1
    }
}

# Run main function
Main