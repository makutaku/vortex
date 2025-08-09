#!/bin/bash
set -e

# Production Docker Build Script for Vortex
# Builds and optionally pushes Docker images to Docker Hub

# Configuration
DEFAULT_REGISTRY="docker.io"
DEFAULT_USERNAME="your-dockerhub-username"  # TODO: Replace with your Docker Hub username
IMAGE_NAME="vortex"
DOCKERFILE="Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

show_usage() {
    echo "Usage: $0 [OPTIONS] [VERSION]"
    echo ""
    echo "Build and optionally push Vortex Docker image to Docker Hub"
    echo ""
    echo "Arguments:"
    echo "  VERSION                 Version tag (default: latest)"
    echo ""
    echo "Options:"
    echo "  -u, --username USERNAME Docker Hub username (default: $DEFAULT_USERNAME)"
    echo "  -r, --registry REGISTRY Docker registry URL (default: $DEFAULT_REGISTRY)"
    echo "  -p, --push              Push image to registry after building"
    echo "  --no-cache              Build without using cache"
    echo "  --dry-run               Show what would be done without executing"
    echo "  --test                  Run Docker tests after building"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 v1.0.0                           # Build image with version v1.0.0"
    echo "  $0 -p v1.0.0                       # Build and push v1.0.0"
    echo "  $0 -u myuser -p latest              # Build and push with custom username"
    echo "  $0 --test --no-cache v1.0.0        # Build with no cache and run tests"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME         Docker Hub username (overrides -u)"
    echo "  DOCKER_REGISTRY         Docker registry (overrides -r)"
    echo "  DOCKER_PASSWORD         Docker Hub password (for automated login)"
    echo ""
}

# Parse command line arguments
VERSION="latest"
REGISTRY="${DOCKER_REGISTRY:-$DEFAULT_REGISTRY}"
USERNAME="${DOCKER_USERNAME:-$DEFAULT_USERNAME}"
PUSH=false
NO_CACHE=false
DRY_RUN=false
RUN_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--username)
            USERNAME="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --test)
            RUN_TESTS=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || [[ "$1" == "latest" ]]; then
                VERSION="$1"
            else
                log_error "Unknown option or invalid version: $1"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate configuration
if [[ "$USERNAME" == "your-dockerhub-username" ]]; then
    log_error "Please set your Docker Hub username using -u option or DOCKER_USERNAME environment variable"
    exit 1
fi

# Build configuration
FULL_IMAGE_NAME="$USERNAME/$IMAGE_NAME"
LOCAL_TAG="$FULL_IMAGE_NAME:$VERSION"
REGISTRY_TAG="$REGISTRY/$FULL_IMAGE_NAME:$VERSION"

# Show configuration
log_info "========================================="
log_info "🐳 Vortex Production Build Configuration"
log_info "========================================="
log_info "Registry:     $REGISTRY"
log_info "Username:     $USERNAME"
log_info "Image:        $IMAGE_NAME"
log_info "Version:      $VERSION"
log_info "Local Tag:    $LOCAL_TAG"
log_info "Registry Tag: $REGISTRY_TAG"
log_info "Push:         $PUSH"
log_info "No Cache:     $NO_CACHE"
log_info "Run Tests:    $RUN_TESTS"
log_info "Dry Run:      $DRY_RUN"
log_info "========================================="

if [[ "$DRY_RUN" == "true" ]]; then
    log_warning "DRY RUN MODE - Commands will be displayed but not executed"
    echo ""
fi

# Function to execute or show commands
execute_cmd() {
    local cmd="$1"
    local desc="$2"
    
    log_info "$desc"
    echo "Command: $cmd"
    
    if [[ "$DRY_RUN" != "true" ]]; then
        eval "$cmd"
        if [[ $? -eq 0 ]]; then
            log_success "$desc completed"
        else
            log_error "$desc failed"
            exit 1
        fi
    else
        log_warning "DRY RUN: Command not executed"
    fi
    echo ""
}

# Pre-flight checks
log_info "Running pre-flight checks..."

if [[ "$DRY_RUN" != "true" ]]; then
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running or accessible"
        exit 1
    fi
    
    # Check if Dockerfile exists
    if [[ ! -f "$DOCKERFILE" ]]; then
        log_error "Dockerfile not found: $DOCKERFILE"
        exit 1
    fi
    
    log_success "Pre-flight checks passed"
else
    log_warning "DRY RUN: Skipping pre-flight checks"
fi

echo ""

# Build the image
BUILD_ARGS=""
if [[ "$NO_CACHE" == "true" ]]; then
    BUILD_ARGS="--no-cache"
fi

BUILD_CMD="docker build $BUILD_ARGS -t $LOCAL_TAG -f $DOCKERFILE ."
execute_cmd "$BUILD_CMD" "Building Docker image"

# Tag for registry if different from local
if [[ "$REGISTRY_TAG" != "$LOCAL_TAG" ]]; then
    TAG_CMD="docker tag $LOCAL_TAG $REGISTRY_TAG"
    execute_cmd "$TAG_CMD" "Tagging image for registry"
fi

# Also tag as latest if version is not latest
if [[ "$VERSION" != "latest" ]]; then
    LATEST_LOCAL="$FULL_IMAGE_NAME:latest"
    LATEST_REGISTRY="$REGISTRY/$FULL_IMAGE_NAME:latest"
    
    TAG_LATEST_CMD="docker tag $LOCAL_TAG $LATEST_LOCAL"
    execute_cmd "$TAG_LATEST_CMD" "Tagging image as latest"
    
    if [[ "$REGISTRY_TAG" != "$LOCAL_TAG" ]]; then
        TAG_LATEST_REGISTRY_CMD="docker tag $LOCAL_TAG $LATEST_REGISTRY"
        execute_cmd "$TAG_LATEST_REGISTRY_CMD" "Tagging latest for registry"
    fi
fi

# Run tests if requested
if [[ "$RUN_TESTS" == "true" ]]; then
    log_info "Running Docker tests..."
    if [[ "$DRY_RUN" != "true" ]]; then
        if [[ -f "./tests/docker/test-docker-build.sh" ]]; then
            ./tests/docker/test-docker-build.sh
            if [[ $? -eq 0 ]]; then
                log_success "All Docker tests passed"
            else
                log_error "Docker tests failed"
                exit 1
            fi
        else
            log_warning "Docker test script not found: ./tests/docker/test-docker-build.sh"
        fi
    else
        log_warning "DRY RUN: Docker tests not executed"
    fi
    echo ""
fi

# Push to registry if requested
if [[ "$PUSH" == "true" ]]; then
    log_info "Preparing to push to registry..."
    
    # Login to registry if credentials are available
    if [[ -n "$DOCKER_PASSWORD" ]]; then
        LOGIN_CMD="echo '$DOCKER_PASSWORD' | docker login $REGISTRY -u $USERNAME --password-stdin"
        execute_cmd "$LOGIN_CMD" "Logging in to Docker registry"
    else
        if [[ "$DRY_RUN" != "true" ]]; then
            log_info "No DOCKER_PASSWORD environment variable found"
            log_info "Please ensure you are logged in to Docker Hub:"
            log_info "  docker login $REGISTRY"
            read -p "Press Enter to continue or Ctrl+C to cancel..."
        else
            log_warning "DRY RUN: Docker login would be required"
        fi
    fi
    
    # Push versioned image
    PUSH_CMD="docker push $REGISTRY_TAG"
    execute_cmd "$PUSH_CMD" "Pushing versioned image to registry"
    
    # Push latest if we tagged it
    if [[ "$VERSION" != "latest" ]]; then
        PUSH_LATEST_CMD="docker push $REGISTRY/$FULL_IMAGE_NAME:latest"
        execute_cmd "$PUSH_LATEST_CMD" "Pushing latest image to registry"
    fi
fi

# Summary
log_info "========================================="
log_success "🚀 Build completed successfully!"
log_info "========================================="
log_info "Built images:"
log_info "  • $LOCAL_TAG"
if [[ "$VERSION" != "latest" ]]; then
    log_info "  • $FULL_IMAGE_NAME:latest"
fi

if [[ "$PUSH" == "true" ]]; then
    log_info ""
    log_info "Pushed to registry:"
    log_info "  • $REGISTRY_TAG"
    if [[ "$VERSION" != "latest" ]]; then
        log_info "  • $REGISTRY/$FULL_IMAGE_NAME:latest"
    fi
    
    log_info ""
    log_info "To deploy, use:"
    log_info "  docker run -d --name vortex $REGISTRY_TAG"
    log_info "  docker-compose up -d  # (update image in docker-compose.yml)"
fi

if [[ "$DRY_RUN" != "true" ]]; then
    log_info ""
    log_info "Image size:"
    docker images $FULL_IMAGE_NAME --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
fi

log_info ""
log_info "Next steps:"
log_info "  1. Test the image: docker run --rm $LOCAL_TAG vortex --help"
log_info "  2. Deploy to production"
log_info "  3. Monitor application logs"

echo ""