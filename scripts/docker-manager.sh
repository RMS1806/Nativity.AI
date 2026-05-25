#!/bin/bash
# Docker Management Script for Nativity.ai
# Provides easy commands for container operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="nativity"
DEV_COMPOSE="docker-compose.yml"
PROD_COMPOSE="docker-compose.prod.yml"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Development environment commands
dev_start() {
    log_info "Starting development environment..."
    check_docker
    docker-compose -f $DEV_COMPOSE up -d
    log_success "Development environment started!"
    log_info "API: http://localhost:8000"
    log_info "Frontend: http://localhost:3000"
    log_info "Redis: localhost:6379"
}

dev_stop() {
    log_info "Stopping development environment..."
    docker-compose -f $DEV_COMPOSE down
    log_success "Development environment stopped!"
}

dev_restart() {
    log_info "Restarting development environment..."
    dev_stop
    dev_start
}

dev_logs() {
    local service=${1:-""}
    if [ -n "$service" ]; then
        log_info "Showing logs for service: $service"
        docker-compose -f $DEV_COMPOSE logs -f $service
    else
        log_info "Showing logs for all services..."
        docker-compose -f $DEV_COMPOSE logs -f
    fi
}

dev_shell() {
    local service=${1:-"api"}
    log_info "Opening shell in $service container..."
    docker-compose -f $DEV_COMPOSE exec $service /bin/bash
}

# Production environment commands
prod_start() {
    log_info "Starting production environment..."
    check_docker
    docker-compose -f $PROD_COMPOSE up -d
    log_success "Production environment started!"
    log_info "Access via: http://localhost (Nginx proxy)"
}

prod_stop() {
    log_info "Stopping production environment..."
    docker-compose -f $PROD_COMPOSE down
    log_success "Production environment stopped!"
}

prod_restart() {
    log_info "Restarting production environment..."
    prod_stop
    prod_start
}

prod_scale_workers() {
    local count=${1:-2}
    log_info "Scaling workers to $count instances..."
    docker-compose -f $PROD_COMPOSE up -d --scale worker=$count
    log_success "Workers scaled to $count instances!"
}

# Build commands
build_all() {
    log_info "Building all containers..."
    check_docker
    docker-compose -f $DEV_COMPOSE build --no-cache
    log_success "All containers built successfully!"
}

build_api() {
    log_info "Building API container..."
    docker-compose -f $DEV_COMPOSE build --no-cache api
    log_success "API container built!"
}

build_worker() {
    log_info "Building worker container..."
    docker-compose -f $DEV_COMPOSE build --no-cache worker
    log_success "Worker container built!"
}

build_frontend() {
    log_info "Building frontend container..."
    docker-compose -f $DEV_COMPOSE build --no-cache frontend
    log_success "Frontend container built!"
}

# Utility commands
status() {
    log_info "Container status:"
    docker-compose -f $DEV_COMPOSE ps
    echo ""
    log_info "Production container status:"
    docker-compose -f $PROD_COMPOSE ps
}

health_check() {
    log_info "Checking service health..."
    
    # Check API health
    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "API is healthy"
    else
        log_error "API is not responding"
    fi
    
    # Check Redis
    if docker-compose -f $DEV_COMPOSE exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
    else
        log_error "Redis is not responding"
    fi
    
    # Check Frontend
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "Frontend is healthy"
    else
        log_error "Frontend is not responding"
    fi
}

cleanup() {
    log_info "Cleaning up Docker resources..."
    
    # Stop all containers
    docker-compose -f $DEV_COMPOSE down
    docker-compose -f $PROD_COMPOSE down
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    log_success "Cleanup completed!"
}

# Help function
show_help() {
    echo "Nativity.ai Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Development Commands:"
    echo "  dev:start          Start development environment"
    echo "  dev:stop           Stop development environment"
    echo "  dev:restart        Restart development environment"
    echo "  dev:logs [service] Show logs (optionally for specific service)"
    echo "  dev:shell [service] Open shell in container (default: api)"
    echo ""
    echo "Production Commands:"
    echo "  prod:start         Start production environment"
    echo "  prod:stop          Stop production environment"
    echo "  prod:restart       Restart production environment"
    echo "  prod:scale [count] Scale workers (default: 2)"
    echo ""
    echo "Build Commands:"
    echo "  build:all          Build all containers"
    echo "  build:api          Build API container"
    echo "  build:worker       Build worker container"
    echo "  build:frontend     Build frontend container"
    echo ""
    echo "Utility Commands:"
    echo "  status             Show container status"
    echo "  health             Check service health"
    echo "  cleanup            Clean up Docker resources"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev:start       # Start development environment"
    echo "  $0 dev:logs api    # Show API logs"
    echo "  $0 prod:scale 4    # Scale to 4 workers"
    echo "  $0 build:all       # Rebuild all containers"
}

# Main command dispatcher
case "${1:-help}" in
    "dev:start")
        dev_start
        ;;
    "dev:stop")
        dev_stop
        ;;
    "dev:restart")
        dev_restart
        ;;
    "dev:logs")
        dev_logs $2
        ;;
    "dev:shell")
        dev_shell $2
        ;;
    "prod:start")
        prod_start
        ;;
    "prod:stop")
        prod_stop
        ;;
    "prod:restart")
        prod_restart
        ;;
    "prod:scale")
        prod_scale_workers $2
        ;;
    "build:all")
        build_all
        ;;
    "build:api")
        build_api
        ;;
    "build:worker")
        build_worker
        ;;
    "build:frontend")
        build_frontend
        ;;
    "status")
        status
        ;;
    "health")
        health_check
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac