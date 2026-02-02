#!/bin/bash
# ADME Test Runner
#
# Usage:
#   ./scripts/test.sh [mode]
#
# Modes:
#   auto        - Build and run autonomous tests in Docker (default)
#   local       - Run tests locally without Docker (Apple Silicon compatible)
#   build       - Just build the test Docker image
#   dev         - Start development server with docker-compose
#
# Production builds:
#   ncats       - Build full stack for NCATS subdomain
#   opendata    - Build full stack for OpenData subdomain
#   backend     - Build backend-only image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

MODE="${1:-auto}"
PORT="${PORT:-5000}"

# Create results directory
mkdir -p results

case "$MODE" in
    #==========================================================================
    # Testing Modes
    #==========================================================================
    
    auto)
        echo "=========================================="
        echo "AUTONOMOUS TEST MODE"
        echo "=========================================="
        echo ""
        echo "This will:"
        echo "  1. Build the Docker image"
        echo "  2. Start the server and wait for models to load"
        echo "  3. Run the full test suite"
        echo "  4. Save results to ./results/<timestamp>/"
        echo ""
        
        # Build the image
        echo "Building test image..."
        docker build -f docker/Dockerfile.test -t ncats-adme-test:latest .
        
        if [ $? -ne 0 ]; then
            echo "ERROR: Docker build failed"
            exit 1
        fi
        
        # Stop any existing container
        docker stop adme-test 2>/dev/null || true
        docker rm adme-test 2>/dev/null || true
        
        # Run autonomous tests
        echo ""
        echo "Starting test container..."
        
        docker run -d \
            --name adme-test \
            -v "$(pwd)/results:/results" \
            -e MODEL_TIMEOUT=1800 \
            ncats-adme-test:latest
        
        echo ""
        echo "=========================================="
        echo "CONTAINER RUNNING IN BACKGROUND"
        echo "=========================================="
        echo ""
        echo "Monitor progress:"
        echo "  docker logs -f adme-test"
        echo ""
        echo "Results will be in: ./results/<timestamp>/"
        echo ""
        ;;
    
    local)
        # Local testing without Docker (for Apple Silicon)
        echo "=========================================="
        echo "LOCAL TEST MODE (No Docker)"
        echo "=========================================="
        
        RESULTS_DIR="./results"
        BASE_URL="http://localhost:$PORT"
        
        # Check conda environment
        if [[ -z "$CONDA_DEFAULT_ENV" ]]; then
            echo ""
            echo "ERROR: No conda environment active."
            echo "Please run: conda activate ncats-adme"
            exit 1
        fi
        
        echo "Using conda environment: $CONDA_DEFAULT_ENV"
        
        # Start server
        echo ""
        echo "[1/4] Starting Flask server..."
        cd server
        python app.py &
        SERVER_PID=$!
        cd ..
        
        # Cleanup on exit
        cleanup() {
            echo "Shutting down server..."
            kill $SERVER_PID 2>/dev/null || true
        }
        trap cleanup EXIT
        
        # Wait for server
        echo "[2/4] Waiting for server..."
        for i in {1..60}; do
            if curl -s "$BASE_URL/healthcheck" > /dev/null 2>&1; then
                echo "Server is up!"
                break
            fi
            sleep 2
        done
        
        # Wait for models
        echo "[3/4] Waiting for models to load..."
        python server/scripts/wait_for_models.py --timeout 1800 --url "$BASE_URL"
        
        # Run tests
        echo "[4/4] Running test suite..."
        python server/scripts/run_tests.py --url "$BASE_URL" --output "$RESULTS_DIR" --baseline testing/baseline_predictions.json
        
        echo ""
        echo "Results saved to: $RESULTS_DIR"
        ;;
    
    build)
        echo "Building test image..."
        docker build -f docker/Dockerfile.test -t ncats-adme-test:latest .
        echo ""
        echo "Build complete: ncats-adme-test:latest"
        ;;
    
    dev)
        echo "Starting development server..."
        docker-compose up -d adme-dev
        echo ""
        echo "Development server: http://localhost:5000"
        echo "View logs: docker-compose logs -f adme-dev"
        echo "Stop: docker-compose down"
        ;;
    
    #==========================================================================
    # Production Build Modes
    #==========================================================================
    
    ncats)
        echo "Building NCATS production image..."
        docker build -f docker/Dockerfile.ncats -t ncats-adme-ncats:latest .
        echo ""
        echo "Build complete: ncats-adme-ncats:latest"
        ;;
    
    opendata)
        echo "Building OpenData production image..."
        docker build -f docker/Dockerfile.opendata -t ncats-adme-opendata:latest .
        echo ""
        echo "Build complete: ncats-adme-opendata:latest"
        ;;
    
    backend)
        echo "Building backend-only image..."
        docker build -f docker/Dockerfile.backend -t ncats-adme-backend:latest .
        echo ""
        echo "Build complete: ncats-adme-backend:latest"
        echo "Run with: docker run -p 5000:5000 ncats-adme-backend:latest"
        ;;
    
    *)
        echo "ADME Test Runner"
        echo ""
        echo "Usage: $0 [mode]"
        echo ""
        echo "Testing modes:"
        echo "  auto      Run autonomous tests in Docker (default)"
        echo "  local     Run tests locally without Docker"
        echo "  build     Just build the test image"
        echo "  dev       Start development server"
        echo ""
        echo "Production builds:"
        echo "  ncats     Build for NCATS subdomain"
        echo "  opendata  Build for OpenData subdomain"
        echo "  backend   Build backend-only image"
        echo ""
        echo "Examples:"
        echo "  ./scripts/test.sh auto      # Run autonomous tests"
        echo "  ./scripts/test.sh local     # Run locally (Apple Silicon)"
        echo "  ./scripts/test.sh ncats     # Build production image"
        exit 1
        ;;
esac

