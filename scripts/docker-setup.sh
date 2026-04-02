#!/bin/bash

# Docker setup and health check script for Swing Trade Platform
# This script validates Docker configuration and ensures all services are healthy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_docker_installed() {
    print_header "Checking Docker Installation"

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        return 1
    fi

    DOCKER_VERSION=$(docker --version)
    print_success "Docker is installed: $DOCKER_VERSION"

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        return 1
    fi

    COMPOSE_VERSION=$(docker-compose --version)
    print_success "Docker Compose is installed: $COMPOSE_VERSION"

    return 0
}

validate_docker_compose_config() {
    print_header "Validating docker-compose Configuration"

    cd "$PROJECT_ROOT"

    if docker-compose config > /dev/null 2>&1; then
        print_success "docker-compose.yml is valid"
        return 0
    else
        print_error "docker-compose.yml validation failed"
        docker-compose config
        return 1
    fi
}

create_env_local() {
    print_header "Setting Up Environment File"

    if [ -f "$PROJECT_ROOT/.env.local" ]; then
        print_success ".env.local already exists"
    else
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            print_warning ".env.local not found, creating from .env.example"
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env.local"
            print_success ".env.local created from template"
        else
            print_error ".env.example not found"
            return 1
        fi
    fi

    return 0
}

build_images() {
    print_header "Building Docker Images"

    cd "$PROJECT_ROOT"

    if docker-compose build --no-cache; then
        print_success "All Docker images built successfully"
        return 0
    else
        print_error "Failed to build Docker images"
        return 1
    fi
}

start_services() {
    print_header "Starting Services"

    cd "$PROJECT_ROOT"

    if docker-compose up -d; then
        print_success "Services started in detached mode"
        return 0
    else
        print_error "Failed to start services"
        return 1
    fi
}

wait_for_services() {
    print_header "Waiting for Services to Be Healthy"

    cd "$PROJECT_ROOT"

    local max_attempts=30
    local attempt=1

    # Wait for PostgreSQL
    echo "Waiting for PostgreSQL..."
    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "PostgreSQL did not become ready in time"
            return 1
        fi

        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done

    # Wait for Redis
    echo "Waiting for Redis..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            print_success "Redis is ready"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "Redis did not become ready in time"
            return 1
        fi

        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done

    # Wait for Backend API
    echo "Waiting for Backend API..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Backend API is ready"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_warning "Backend API not responding yet, but continuing..."
            break
        fi

        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done

    return 0
}

show_service_status() {
    print_header "Service Status"

    cd "$PROJECT_ROOT"

    docker-compose ps

    return 0
}

test_connections() {
    print_header "Testing Service Connections"

    cd "$PROJECT_ROOT"

    # Test PostgreSQL
    echo "Testing PostgreSQL connection..."
    if docker-compose exec -T postgres psql -U postgres -d swing_trade -c "SELECT version();" > /dev/null 2>&1; then
        print_success "PostgreSQL connection successful"
    else
        print_error "PostgreSQL connection failed"
    fi

    # Test Redis
    echo "Testing Redis connection..."
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        print_success "Redis connection successful"
    else
        print_error "Redis connection failed"
    fi

    # Test Backend API
    echo "Testing Backend API..."
    if curl -f http://localhost:8000/health 2>/dev/null | grep -q '"status":"ok"'; then
        print_success "Backend API health check passed"
    else
        print_warning "Backend API health check not responding yet"
    fi

    return 0
}

main() {
    print_header "Docker Setup for Swing Trade Platform"

    check_docker_installed || exit 1
    validate_docker_compose_config || exit 1
    create_env_local || exit 1
    build_images || exit 1
    start_services || exit 1
    wait_for_services || exit 1
    show_service_status
    test_connections

    print_header "Setup Complete"
    echo "Services are running and accessible at:"
    echo "  - Backend API: http://localhost:8000"
    echo "  - Backend Docs: http://localhost:8000/docs"
    echo "  - Frontend: http://localhost:5173"
    echo "  - PostgreSQL: localhost:5432 (user: postgres)"
    echo "  - Redis: localhost:6379"
    echo ""
    echo "To stop services: docker-compose down"
    echo "To view logs: docker-compose logs -f [service-name]"
    echo ""
}

# Run main function
main "$@"
