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
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"
$Reset = $null

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color
    )

    if ($Color) {
        Write-Host $Message -ForegroundColor $Color
    }
    else {
        Write-Host $Message
    }
}

function Get-TerraformOutput {
    param([string]$OutputName)
    
    try {
        $output = terraform output -raw $OutputName 2>$null
        return $output
    }
    catch {
        Write-ColorOutput "[ERROR] Failed to get Terraform output: $OutputName" $Red
        exit 1
    }
}

function Login-ECR {
    param(
        [string]$Region,
        [string]$AccountId
    )

    Write-ColorOutput "[INFO] Logging into ECR..." $Blue

    try {
        $token = aws ecr get-login-password --region $Region
        
        docker login `
            --username AWS `
            --password $token `
            "$AccountId.dkr.ecr.$Region.amazonaws.com"

        if ($LASTEXITCODE -ne 0) {
            throw "Docker login failed"
        }

        Write-ColorOutput "[OK] Successfully logged into ECR" $Green
    }
    catch {
        Write-ColorOutput "[ERROR] Failed to login to ECR: $_" $Red
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
    
    Write-ColorOutput "[INFO] Building $ServiceName Docker image..." $Blue
    
    $imageTag = "${RepositoryUri}:${Tag}"
    $envTag = "${RepositoryUri}:${Environment}-${Tag}"
    try {
        # Build the image
        $buildContext = Split-Path $DockerfilePath -Parent
        
        docker build `
            -t $imageTag `
            -f $DockerfilePath `
            $buildContext | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
        
        # Tag with environment
        docker tag $imageTag $envTag | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Docker tag failed"
        }
        
        Write-ColorOutput "[OK] Successfully built $ServiceName image" $Green
        [PSCustomObject]@{
            ImageTag = $imageTag
            EnvTag   = $envTag
        }
    }
    catch {
        Write-ColorOutput "[ERROR] Failed to build $ServiceName image: $_" $Red
        exit 1
    }
}
function Push-DockerImage {
    param([string[]]$ImageTags, [string]$ServiceName)
    
    Write-ColorOutput "[INFO] Pushing $ServiceName Docker images..." $Blue
    
    try {
        foreach ($tag in $ImageTags) {
            Write-ColorOutput "[INFO] Pushing $tag..." $Yellow
            docker push $tag
            if ($LASTEXITCODE -ne 0) {
                throw "Docker push failed for $tag"
            }
        }
        
        Write-ColorOutput "[OK] Successfully pushed $ServiceName images" $Green
    }
    catch {
        Write-ColorOutput "[ERROR] Failed to push $ServiceName images: $_" $Red
        exit 1
    }
}

function Update-ECSService {
    param([string]$ClusterName, [string]$ServiceName)
    
    Write-ColorOutput "[INFO] Updating ECS service: $ServiceName..." $Blue
    
    try {
        aws ecs update-service --cluster $ClusterName --service $ServiceName --force-new-deployment
        if ($LASTEXITCODE -ne 0) {
            throw "ECS service update failed"
        }
        
        Write-ColorOutput "[OK] Successfully triggered ECS service update for $ServiceName" $Green
    }
    catch {
        Write-ColorOutput "[ERROR] Failed to update ECS service $ServiceName`: $_" $Red
        exit 1
    }
}

function Wait-ForDeployment {
    param(
        [string]$ClusterName,
        [string]$ServiceName
    )

    Write-ColorOutput "[INFO] Waiting for deployment to complete for $ServiceName..." $Yellow

    $timeoutMinutes = 30
    $startTime = Get-Date

    while ($true) {

        $service = aws ecs describe-services `
            --cluster $ClusterName `
            --services $ServiceName `
            --query "services[0]" `
            --output json | ConvertFrom-Json

        $running = $service.runningCount
        $desired = $service.desiredCount
        $pending = $service.pendingCount

        Write-Host "Running=$running Pending=$pending Desired=$desired"

        if ($running -eq $desired -and $pending -eq 0) {
            Write-ColorOutput "[OK] Deployment completed successfully for $ServiceName" $Green
            return
        }

        $elapsed = (Get-Date) - $startTime

        if ($elapsed.TotalMinutes -gt $timeoutMinutes) {
            throw "Deployment timeout after $timeoutMinutes minutes"
        }

        Start-Sleep -Seconds 15
    }
}

function Deploy-Service {
    param([string]$ServiceName)
    
    Write-ColorOutput "`n[INFO] Deploying $ServiceName service..." $Blue
    
    # Get repository URI from Terraform outputs
    $repositoryUri = Get-TerraformOutput "${ServiceName}_repository_url"
    # Determine Dockerfile path
    $dockerfilePath = switch ($ServiceName) {
        "api" { "../backend/dockerfile" }
        "worker" { "../backend/dockerfile.worker" }
    }
    
    # Check if Dockerfile exists
    if (-not (Test-Path $dockerfilePath)) {
        Write-ColorOutput "[ERROR] Dockerfile not found: $dockerfilePath" $Red
        Write-ColorOutput "[INFO] Please ensure the Dockerfile exists in the correct location." $Yellow
        return
    }
    
        # Build and push Docker image
    $imageInfo = Build-DockerImage `
        -ServiceName $ServiceName `
        -DockerfilePath $dockerfilePath `
        -RepositoryUri $repositoryUri `
        -Tag $Tag
    
    Push-DockerImage `
        -ImageTags @(
            $imageInfo.ImageTag,
            $imageInfo.EnvTag
        ) `
        -ServiceName $ServiceName
    
    # Update ECS service
    $clusterName = Get-TerraformOutput "ecs_cluster_name"
    $ecsServiceName = "nativity-ai-$Environment-$ServiceName"
    
    Update-ECSService -ClusterName $clusterName -ServiceName $ecsServiceName
    Wait-ForDeployment -ClusterName $clusterName -ServiceName $ecsServiceName
}

function Check-Prerequisites {
    Write-ColorOutput "[INFO] Checking prerequisites..." $Blue
    
    # Check if Docker is running
    try {
        docker version | Out-Null
        Write-ColorOutput "[OK] Docker is running" $Green
    }
    catch {
        Write-ColorOutput "[ERROR] Docker is not running. Please start Docker first." $Red
        exit 1
    }
    
    # Check if AWS CLI is configured
    try {
        $awsIdentity = aws sts get-caller-identity 2>$null
        if ($awsIdentity) {
            $identity = $awsIdentity | ConvertFrom-Json
            Write-ColorOutput "[OK] AWS CLI configured for account: $($identity.Account)" $Green
        }
        else {
            Write-ColorOutput "[ERROR] AWS CLI not configured. Please run 'aws configure' first." $Red
            exit 1
        }
    }
    catch {
        Write-ColorOutput "[ERROR] AWS CLI not found or not configured." $Red
        exit 1
    }
    
    # Check if we're in the infrastructure directory
    if (-not (Test-Path "main.tf")) {
        Write-ColorOutput "[ERROR] Please run this script from the infrastructure directory." $Red
        exit 1
    }
}

function Main {
    Write-ColorOutput "[INFO] Nativity.AI Docker Build and Deploy" $Blue
    Write-ColorOutput "Environment: $Environment" $Yellow
    Write-ColorOutput "Service: $Service" $Yellow
    Write-ColorOutput "Tag: $Tag" $Yellow
    # Change to the script directory
    if ($PSScriptRoot) {
        Set-Location $PSScriptRoot
    }
    else {
        Write-ColorOutput "[WARN] PSScriptRoot not available. Using current directory." $Yellow
    }
    
    try {
        Check-Prerequisites
        
        # Get AWS account info
        $accountId = Get-TerraformOutput "account_id"
        $region = Get-TerraformOutput "region"
        if ([string]::IsNullOrWhiteSpace($accountId)) {
            throw "Terraform output 'account_id' is empty"
        }
        
        if ([string]::IsNullOrWhiteSpace($region)) {
            throw "Terraform output 'region' is empty"
        }
        
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
        
        Write-ColorOutput "Build and deployment completed successfully!" $Green
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
        Write-ColorOutput "[ERROR] Build and deployment failed: $($_.Exception.Message)" $Red
        exit 1
    }
}

# Run main function
Main