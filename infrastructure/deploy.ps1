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

# Colors for output using native character codes
$Red    = "$([char]27)[31m"
$Green  = "$([char]27)[32m"
$Yellow = "$([char]27)[33m"
$Blue   = "$([char]27)[34m"
$Reset  = "$([char]27)[0m"

function Write-ColorOutput {
    param(
        [string]$Message, 
        [string]$Color = $Reset
    )
    Write-Host "$Color$Message$Reset"
}

function Check-Prerequisites {
    Write-ColorOutput "[CHECK] Checking prerequisites..." $Blue
    
    try {
        $terraformVersion = terraform version
        Write-ColorOutput "[OK] Terraform found" $Green
    }
    catch {
        Write-ColorOutput "[ERROR] Terraform not found. Please install Terraform first." $Red
        exit 1
    }
    
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
    
    if (-not (Test-Path "terraform.tfvars")) {
        Write-ColorOutput "[ERROR] terraform.tfvars not found. Please copy terraform.tfvars.example and update with your values." $Red
        exit 1
    }
    
    Write-ColorOutput "[OK] All prerequisites met!" $Green
}

function Initialize-Terraform {
    Write-ColorOutput "[INIT] Initializing Terraform..." $Blue
    
    terraform init
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[ERROR] Terraform initialization failed!" $Red
        exit 1
    }
    
    Write-ColorOutput "[OK] Terraform initialized successfully!" $Green
}

function Plan-Infrastructure {
    Write-ColorOutput "[PLAN] Planning infrastructure changes..." $Blue
    
    $planFile = "terraform-$Environment.tfplan"
    
    if ($Destroy) {
        terraform plan -destroy -var="environment=$Environment" -out=$planFile
    }
    else {
        terraform plan -var="environment=$Environment" -out=$planFile
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[ERROR] Terraform planning failed!" $Red
        exit 1
    }
    
    Write-ColorOutput "[OK] Terraform plan completed successfully!" $Green
    return $planFile
}

function Apply-Infrastructure {
    param([string]$PlanFile)
    
    if ($Destroy) {
        Write-ColorOutput "[DESTROY] Destroying infrastructure..." $Yellow
    }
    else {
        Write-ColorOutput "[APPLY] Applying infrastructure changes..." $Blue
    }
    
    if ($AutoApprove) {
        terraform apply -auto-approve $PlanFile
    }
    else {
        terraform apply $PlanFile
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[ERROR] Terraform apply failed!" $Red
        exit 1
    }
    
    if ($Destroy) {
        Write-ColorOutput "[OK] Infrastructure destroyed successfully!" $Green
    }
    else {
        Write-ColorOutput "[OK] Infrastructure deployed successfully!" $Green
    }
}

function Show-Outputs {
    Write-ColorOutput "[OUTPUTS] Infrastructure outputs:" $Blue
    terraform output
}

function Main {
    Write-ColorOutput "[START] Nativity.AI Infrastructure Deployment" $Blue
    Write-ColorOutput "Environment: $Environment" $Yellow
    
    if ($Destroy) {
        Write-ColorOutput "[WARN] DESTROY MODE - This will delete all infrastructure!" $Red
        $confirmation = Read-Host "Are you sure you want to destroy the $Environment environment? (yes/no)"
        if ($confirmation -ne "yes") {
            Write-ColorOutput "[CANCEL] Deployment cancelled." $Yellow
            exit 0
        }
    }
    
    # Clean, modern approach to get script directory
    if ($PSScriptRoot) {
        Set-Location $PSScriptRoot
    }
    else {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
        if ($scriptPath) { Set-Location $scriptPath }
    }
    
    try {
        Check-Prerequisites
        Initialize-Terraform
        
        $planFile = Plan-Infrastructure
        
        if ($Plan) {
            Write-ColorOutput "[INFO] Plan-only mode. Review the plan above." $Yellow
            return
        }
        
        Apply-Infrastructure -PlanFile $planFile
        
        if (-not $Destroy) {
            Show-Outputs
            
            Write-Host ""
            Write-ColorOutput "[SUCCESS] Deployment completed successfully!" $Green
            Write-ColorOutput "Next steps:" $Blue
            Write-ColorOutput "1. Build and push Docker images to ECR" $Reset
            Write-ColorOutput "2. Update ECS services with new task definitions" $Reset
            Write-ColorOutput "3. Configure domain and SSL certificate (if using custom domain)" $Reset
            Write-ColorOutput "4. Set up monitoring alerts and notifications" $Reset
        }
    }
    catch {
        Write-ColorOutput "[ERROR] Deployment failed: $_" $Red
        exit 1
    }
    finally {
        $targetPlan = "terraform-$Environment.tfplan"
        if (Test-Path $targetPlan) {
            Remove-Item $targetPlan -Force
        }
    }
}

# Run main function
Main
