# PowerShell Deployment Script for Nativity.AI AWS Infrastructure
# Usage: .\deploy.ps1 -Environment dev|staging|prod [-Plan] [-Destroy]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,
    
    [switch]$Plan,
    [switch]$Destroy,
    [switch]$AutoApprove
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

function Check-Prerequisites {
    Write-ColorOutput "🔍 Checking prerequisites..." $Blue
    
    # Check if Terraform is installed
    try {
        $terraformVersion = terraform version
        Write-ColorOutput "✅ Terraform found: $($terraformVersion[0])" $Green
    }
    catch {
        Write-ColorOutput "❌ Terraform not found. Please install Terraform first." $Red
        exit 1
    }
    
    # Check if AWS CLI is installed and configured
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
    
    # Check if terraform.tfvars exists
    if (-not (Test-Path "terraform.tfvars")) {
        Write-ColorOutput "❌ terraform.tfvars not found. Please copy terraform.tfvars.example and update with your values." $Red
        exit 1
    }
    
    Write-ColorOutput "✅ All prerequisites met!" $Green
}

function Initialize-Terraform {
    Write-ColorOutput "🚀 Initializing Terraform..." $Blue
    
    # Initialize Terraform
    terraform init
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ Terraform initialization failed!" $Red
        exit 1
    }
    
    Write-ColorOutput "✅ Terraform initialized successfully!" $Green
}

function Plan-Infrastructure {
    Write-ColorOutput "📋 Planning infrastructure changes..." $Blue
    
    $planFile = "terraform-$Environment.tfplan"
    
    if ($Destroy) {
        terraform plan -destroy -var="environment=$Environment" -out=$planFile
    }
    else {
        terraform plan -var="environment=$Environment" -out=$planFile
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ Terraform planning failed!" $Red
        exit 1
    }
    
    Write-ColorOutput "✅ Terraform plan completed successfully!" $Green
    return $planFile
}

function Apply-Infrastructure {
    param([string]$PlanFile)
    
    if ($Destroy) {
        Write-ColorOutput "🔥 Destroying infrastructure..." $Yellow
    }
    else {
        Write-ColorOutput "🏗️ Applying infrastructure changes..." $Blue
    }
    
    if ($AutoApprove) {
        terraform apply -auto-approve $PlanFile
    }
    else {
        terraform apply $PlanFile
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ Terraform apply failed!" $Red
        exit 1
    }
    
    if ($Destroy) {
        Write-ColorOutput "✅ Infrastructure destroyed successfully!" $Green
    }
    else {
        Write-ColorOutput "✅ Infrastructure deployed successfully!" $Green
    }
}

function Show-Outputs {
    Write-ColorOutput "📊 Infrastructure outputs:" $Blue
    terraform output
}

function Main {
    Write-ColorOutput "🌟 Nativity.AI Infrastructure Deployment" $Blue
    Write-ColorOutput "Environment: $Environment" $Yellow
    
    if ($Destroy) {
        Write-ColorOutput "⚠️  DESTROY MODE - This will delete all infrastructure!" $Red
        $confirmation = Read-Host "Are you sure you want to destroy the $Environment environment? (yes/no)"
        if ($confirmation -ne "yes") {
            Write-ColorOutput "❌ Deployment cancelled." $Yellow
            exit 0
        }
    }
    
    # Change to infrastructure directory
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptPath
    
    try {
        Check-Prerequisites
        Initialize-Terraform
        
        $planFile = Plan-Infrastructure
        
        if ($Plan) {
            Write-ColorOutput "📋 Plan-only mode. Review the plan above." $Yellow
            return
        }
        
        Apply-Infrastructure -PlanFile $planFile
        
        if (-not $Destroy) {
            Show-Outputs
            
            Write-ColorOutput "`n🎉 Deployment completed successfully!" $Green
            Write-ColorOutput "Next steps:" $Blue
            Write-ColorOutput "1. Build and push Docker images to ECR" $Reset
            Write-ColorOutput "2. Update ECS services with new task definitions" $Reset
            Write-ColorOutput "3. Configure domain and SSL certificate (if using custom domain)" $Reset
            Write-ColorOutput "4. Set up monitoring alerts and notifications" $Reset
        }
    }
    catch {
        Write-ColorOutput "❌ Deployment failed: $_" $Red
        exit 1
    }
    finally {
        # Clean up plan files
        if (Test-Path "terraform-$Environment.tfplan") {
            Remove-Item "terraform-$Environment.tfplan"
        }
    }
}

# Run main function
Main