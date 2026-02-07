#!/bin/bash
# Smart build wrapper for ADME Docker images
# Captures build output and provides a clear summary
#
# Usage:
#   ./scripts/build.sh [dockerfile] [--no-cache]
#
# Examples:
#   ./scripts/build.sh              # Build Dockerfile.test (default)
#   ./scripts/build.sh backend      # Build Dockerfile.backend
#   ./scripts/build.sh test --no-cache  # Force full rebuild

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

TARGET="${1:-test}"
EXTRA_ARGS=""
if [ "$2" = "--no-cache" ]; then
    EXTRA_ARGS="--no-cache"
fi

DOCKERFILE="docker/Dockerfile.${TARGET}"
IMAGE_NAME="ncats-adme-${TARGET}:latest"
LOG_FILE="testing/results/build_${TARGET}.log"

mkdir -p testing/results

if [ ! -f "$DOCKERFILE" ]; then
    echo "ERROR: Dockerfile not found: $DOCKERFILE"
    echo "Available:"
    ls docker/Dockerfile.* 2>/dev/null | while read f; do
        name=$(basename "$f" | sed 's/Dockerfile\.//')
        echo "  ./scripts/build.sh $name"
    done
    exit 1
fi

echo "=========================================="
echo "ADME Docker Build"
echo "=========================================="
echo "Dockerfile: $DOCKERFILE"
echo "Image:      $IMAGE_NAME"
echo "Log:        $LOG_FILE"
echo "Started:    $(date)"
echo "=========================================="
echo ""

# Run build, capture output
BUILD_START=$(date +%s)

if docker build $EXTRA_ARGS -f "$DOCKERFILE" -t "$IMAGE_NAME" . > "$LOG_FILE" 2>&1; then
    BUILD_END=$(date +%s)
    BUILD_TIME=$((BUILD_END - BUILD_START))

    echo "=========================================="
    echo "✅ BUILD SUCCEEDED"
    echo "=========================================="
    echo "Image: $IMAGE_NAME"
    echo "Time:  ${BUILD_TIME}s"
    echo "Size:  $(docker images "$IMAGE_NAME" --format '{{.Size}}')"
    echo ""
    echo "Next steps:"
    echo "  Run tests:  docker run -v \$(pwd)/testing/results:/results $IMAGE_NAME"
    echo "  Run shell:  docker run -it $IMAGE_NAME bash"
    echo ""
    echo "Full build log: $LOG_FILE"
else
    BUILD_END=$(date +%s)
    BUILD_TIME=$((BUILD_END - BUILD_START))
    EXIT_CODE=$?

    echo "=========================================="
    echo "❌ BUILD FAILED (exit code: $EXIT_CODE)"
    echo "=========================================="
    echo "Time: ${BUILD_TIME}s"
    echo ""

    # Extract the most relevant error information
    echo "--- FAILED STEP ---"
    grep -E "^(Step |STEP |#[0-9])" "$LOG_FILE" | tail -3
    echo ""

    echo "--- ERROR DETAILS ---"
    # Show lines around the first real error
    grep -n -i -E "(error|failed|cannot|no such|not found|ModuleNotFoundError|ImportError)" "$LOG_FILE" | head -10
    echo ""

    echo "--- LAST 20 LINES ---"
    tail -20 "$LOG_FILE"
    echo ""

    echo "Full build log: $LOG_FILE"
    echo ""
    echo "⚠️  DO NOT auto-retry. Review the error above first."

    exit $EXIT_CODE
fi

