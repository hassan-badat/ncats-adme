#!/bin/bash
# Quick script to build and test Docker container
# Usage: ./docker-test.sh [backend-only|full]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DOCKERFILE="${1:-backend-only}"

case "$DOCKERFILE" in
    backend-only)
        DOCKERFILE_PATH="Dockerfile-backend-only"
        IMAGE_NAME="ncats-adme-backend"
        ;;
    full|ncats)
        DOCKERFILE_PATH="Dockerfile-ncats"
        IMAGE_NAME="ncats-adme-full"
        ;;
    opendata)
        DOCKERFILE_PATH="Dockerfile-opendata"
        IMAGE_NAME="ncats-adme-opendata"
        ;;
    *)
        echo "Usage: $0 [backend-only|full|opendata]"
        echo "  backend-only: Backend API only (recommended for testing)"
        echo "  full: Full stack with frontend (NCATS deployment)"
        echo "  opendata: Full stack with frontend (OpenData deployment)"
        exit 1
        ;;
esac

CONTAINER_NAME="${IMAGE_NAME}-test"
PORT="${PORT:-5000}"

echo "=========================================="
echo "Building Docker Image"
echo "=========================================="
echo "Dockerfile: $DOCKERFILE_PATH"
echo "Image: $IMAGE_NAME:latest"
echo ""

# Stop and remove existing container if it exists
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Build the image
echo "Building image (this may take 10-20 minutes)..."
docker build -f "$DOCKERFILE_PATH" -t "${IMAGE_NAME}:latest" .

if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Starting Container"
echo "=========================================="
echo "Container: $CONTAINER_NAME"
echo "Port: $PORT"
echo ""

# Run the container
docker run -d \
    -p "${PORT}:5000" \
    --name "$CONTAINER_NAME" \
    "${IMAGE_NAME}:latest"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start container"
    exit 1
fi

echo "Container started!"
echo ""
echo "Waiting for server to initialize (30 seconds)..."
sleep 30

echo ""
echo "=========================================="
echo "Testing Server"
echo "=========================================="

# Test healthcheck
echo "Testing healthcheck endpoint..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/healthcheck" || echo "000")

if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo "✓ Healthcheck passed (HTTP $HEALTH_RESPONSE)"
else
    echo "✗ Healthcheck failed (HTTP $HEALTH_RESPONSE)"
    echo "View logs with: docker logs -f $CONTAINER_NAME"
    exit 1
fi

# Test a simple prediction
echo ""
echo "Testing RLM prediction..."
RLM_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/api/v1/predict?model=rlm&smiles=CCO" || echo "000")

if [ "$RLM_RESPONSE" = "200" ]; then
    echo "✓ RLM prediction test passed (HTTP $RLM_RESPONSE)"
else
    echo "✗ RLM prediction test failed (HTTP $RLM_RESPONSE)"
    echo "View logs with: docker logs -f $CONTAINER_NAME"
fi

echo ""
echo "=========================================="
echo "Container Information"
echo "=========================================="
echo "Container Name: $CONTAINER_NAME"
echo "Image: ${IMAGE_NAME}:latest"
echo "URL: http://localhost:${PORT}"
echo ""
echo "Useful commands:"
echo "  View logs:    docker logs -f $CONTAINER_NAME"
echo "  Stop:         docker stop $CONTAINER_NAME"
echo "  Start:        docker start $CONTAINER_NAME"
echo "  Remove:       docker rm -f $CONTAINER_NAME"
echo "  Shell access: docker exec -it $CONTAINER_NAME /bin/bash"
echo ""
echo "Run full test suite:"
echo "  python testing/create_baseline_predictions.py --url http://localhost:${PORT}"
echo ""

