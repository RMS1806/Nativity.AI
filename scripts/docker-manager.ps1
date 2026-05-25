# Docker Management Script for Nativity.ai (PowerShell)
# Provides easy commands for container operations on Windows

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$Service = "",
    
    [Parameter(Position=2)]
    [int]$Count = 2
)

# Configuration
$ProjectName = "nativity"
$DevCompose = "docker-compose.yml"
$ProdCompose = "docker-compose.prod.yml"

# Helper functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check if Docker is running
function Test-Docker {
    try {
        docker info | Out-Null
        return $true
    }
    catch {
        Write-Error "Docker is not running. Please start Docker Desktop first."
        exit 1
    }
}

# Development environment commands
function Start-DevEnvironment {
    Write-Info "Starting development environment..."
    Test-Docker
    docker-compose -f $DevCompose up -d
    Write-Success "Development environment started!"
    Write-Info "API: http://localhost:8000"
    Write-Info "Frontend: http://localhost:3000"
    Write-Info "Redis: localhost:6379"
}

function Stop-DevEnvironment {
    Write-Info "Stopping development environment..."
    docker-compose -f $DevCompose down
    Write-Success "Development environment stopped!"
}

function Restart-DevEnvironment {
    Write-Info "Restarting development environment..."
    Stop-DevEnvironment
    Start-DevEnvironment
}

function Show-DevLogs {
    param([string]$ServiceName = "")
    
    if ($ServiceName) {
        Write-Info "Showing logs for service: $ServiceName"
        docker-compose -f $DevCompose logs -f $ServiceName
    } else {
        Write-Info "Showing logs for all services..."
        docker-compose -f $DevCompose logs -f
    }
}

function Open-DevShell {
    param([string]$ServiceName = "api")
    
    Write-Info "Opening shell in $ServiceName container..."
    docker-compose -f $DevCompose exec $ServiceName /bin/bash
}

# Production environment commands
function Start-ProdEnvironment {
    Write-Info "Starting production environment..."
    Test-Docker
    docker-compose -f $ProdCompose up -d
    Write-Success "Production environment started!"
    Write-Info "Access via: http://localhost (Nginx proxy)"
}

function Stop-ProdEnvironment {
    Write-Info "Stopping production environment..."
    docker-compose -f $ProdCompose down
    Write-Success "Production environment stopped!"
}

function Restart-ProdEnvironment {
    Write-Info "Restarting production environment..."
    Stop-ProdEnvironment
    Start-ProdEnvironment
}

function Scale-Workers {
    param([int]$WorkerCount = 2)
    
    Write-Info "Scaling workers to $WorkerCount instances..."
    docker-compose -f $ProdCompose up -d --scale worker=$WorkerCount
    Write-Success "Workers scaled to $WorkerCount instances!"
}

# Build commands
function Build-AllContainers {
    Write-Info "Building all containers..."
    Test-Docker
    docker-compose -f $DevCompose build --no-cache
    Write-Success "All containers built successfully!"
}

function Build-ApiContainer {
    Write-Info "Building API container..."
    docker-compose -f $DevCompose build --no-cache api
    Write-Success "API container built!"
}

function Build-WorkerContainer {
    Write-Info "Building worker container..."
    docker-compose -f $DevCompose build --no-cache worker
    Write-Success "Worker container built!"
}

function Build-FrontendContainer {
    Write-Info "Building frontend container..."
    docker-compose -f $DevCompose build --no-cache frontend
    Write-Success "Frontend container built!"
}

# Utility commands
function Show-Status {
    Write-Info "Development container status:"
    docker-compose -f $DevCompose ps
    Write-Host ""
    Write-Info "Production container status:"
    docker-compose -f $ProdCompose ps
}

function Test-Health {
    Write-Info "Checking service health..."
    
    # Check API health
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "API is healthy"
        } else {
            Write-Error "API returned status code: $($response.StatusCode)"
        }
    }
    catch {
        Write-Error "API is not responding"
    }
    
    # Check Redis
    try {
        $redisResult = docker-compose -f $DevCompose exec -T redis redis-cli ping 2>$null
        if ($redisResult -match "PONG") {
            Write-Success "Redis is healthy"
        } else {
            Write-Error "Redis is not responding"
        }
    }
    catch {
        Write-Error "Redis check failed"
    }
    
    # Check Frontend
    try {
        $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
        if ($frontendResponse.StatusCode -eq 200) {
            Write-Success "Frontend is healthy"
        } else {
            Write-Error "Frontend returned status code: $($frontendResponse.StatusCode)"
        }
    }
    catch {
        Write-Error "Frontend is not responding"
    }
}

function Invoke-Cleanup {
    Write-Info "Cleaning up Docker resources..."
    
    # Stop all containers
    docker-compose -f $DevCompose down
    docker-compose -f $ProdCompose down
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    Write-Success "Cleanup completed!"
}

# Help function
function Show-Help {
    Write-Host "Nativity.ai Docker Management Script (PowerShell)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\docker-manager.ps1 [COMMAND] [SERVICE] [COUNT]" -ForegroundColor White
    Write-Host ""
    Write-Host "Development Commands:" -ForegroundColor Yellow
    Write-Host "  dev:start          Start development environment"
    Write-Host "  dev:stop           Stop development environment"
    Write-Host "  dev:restart        Restart development environment"
    Write-Host "  dev:logs [service] Show logs (optionally for specific service)"
    Write-Host "  dev:shell [service] Open shell in container (default: api)"
    Write-Host ""
    Write-Host "Production Commands:" -ForegroundColor Yellow
    Write-Host "  prod:start         Start production environment"
    Write-Host "  prod:stop          Stop production environment"
    Write-Host "  prod:restart       Restart production environment"
    Write-Host "  prod:scale [count] Scale workers (default: 2)"
    Write-Host ""
    Write-Host "Build Commands:" -ForegroundColor Yellow
    Write-Host "  build:all          Build all containers"
    Write-Host "  build:api          Build API container"
    Write-Host "  build:worker       Build worker container"
    Write-Host "  build:frontend     Build frontend container"
    Write-Host ""
    Write-Host "Utility Commands:" -ForegroundColor Yellow
    Write-Host "  status             Show container status"
    Write-Host "  health             Check service health"
    Write-Host "  cleanup            Clean up Docker resources"
    Write-Host "  help               Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\docker-manager.ps1 dev:start       # Start development environment"
    Write-Host "  .\docker-manager.ps1 dev:logs api    # Show API logs"
    Write-Host "  .\docker-manager.ps1 prod:scale 4    # Scale to 4 workers"
    Write-Host "  .\docker-manager.ps1 build:all       # Rebuild all containers"
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "dev:start" {
        Start-DevEnvironment
    }
    "dev:stop" {
        Stop-DevEnvironment
    }
    "dev:restart" {
        Restart-DevEnvironment
    }
    "dev:logs" {
        Show-DevLogs -ServiceName $Service
    }
    "dev:shell" {
        $shellService = if ($Service) { $Service } else { "api" }
        Open-DevShell -ServiceName $shellService
    }
    "prod:start" {
        Start-ProdEnvironment
    }
    "prod:stop" {
        Stop-ProdEnvironment
    }
    "prod:restart" {
        Restart-ProdEnvironment
    }
    "prod:scale" {
        $workerCount = if ($Service) { [int]$Service } else { $Count }
        Scale-Workers -WorkerCount $workerCount
    }
    "build:all" {
        Build-AllContainers
    }
    "build:api" {
        Build-ApiContainer
    }
    "build:worker" {
        Build-WorkerContainer
    }
    "build:frontend" {
        Build-FrontendContainer
    }
    "status" {
        Show-Status
    }
    "health" {
        Test-Health
    }
    "cleanup" {
        Invoke-Cleanup
    }
    default {
        Show-Help
    }
}