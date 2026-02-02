#!/bin/bash
# Autonomous test runner - starts server, waits for models, runs tests
# Results are saved to /results directory (mount as volume to retrieve)
#
# Usage:
#   docker run -v $(pwd)/results:/results adme-cached
#
# Environment variables:
#   RESULTS_DIR - Directory to save results (default: /results)
#   MODEL_TIMEOUT - Timeout for model loading in seconds (default: 1800 = 30 min)
#   KEEP_RUNNING - Keep server running after tests (default: false)

set -e

RESULTS_DIR="${RESULTS_DIR:-/results}"
BASE_URL="http://localhost:5000"
TIMEOUT="${MODEL_TIMEOUT:-1800}"  # 30 minutes default

# Create results directory
mkdir -p "$RESULTS_DIR"

# Redirect all output to log file while also displaying to console
exec > >(tee "$RESULTS_DIR/test_run.log") 2>&1

echo "=========================================="
echo "AUTONOMOUS TEST RUN"
echo "Started: $(date)"
echo "=========================================="
echo "Configuration:"
echo "  Results directory: $RESULTS_DIR"
echo "  Model timeout: ${TIMEOUT}s"
echo "  Keep running: ${KEEP_RUNNING:-false}"
echo "=========================================="

# Start Flask server in background
echo ""
echo "[1/4] Starting Flask server..."
cd /opt/adme
python app.py &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Wait for server to be responsive (using Python since curl may not be installed)
echo ""
echo "[2/4] Waiting for server to respond..."
SERVER_READY=false
for i in {1..60}; do
    if python -c "import requests; r = requests.get('$BASE_URL/healthcheck', timeout=5); exit(0 if r.status_code == 200 else 1)" 2>/dev/null; then
        echo "Server is up and responding!"
        SERVER_READY=true
        break
    fi
    echo "  Attempt $i/60 - waiting..."
    sleep 2
done

if [ "$SERVER_READY" = false ]; then
    echo "ERROR: Server failed to start within 2 minutes"
    echo "Check logs for errors"
    exit 1
fi

# Poll model status until all loaded
echo ""
echo "[3/4] Waiting for all models to load (timeout: ${TIMEOUT}s)..."
python scripts/wait_for_models.py --timeout "$TIMEOUT" --url "$BASE_URL"
WAIT_EXIT=$?

if [ $WAIT_EXIT -ne 0 ]; then
    echo ""
    echo "=========================================="
    echo "ERROR: Model loading timed out or failed"
    echo "=========================================="
    echo "Check $RESULTS_DIR/test_run.log for details"
    
    # Save partial results
    echo "Model loading failed" > "$RESULTS_DIR/status.txt"
    
    # Kill server before exit
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Run test suite
echo ""
echo "=========================================="
echo "[4/4] RUNNING TEST SUITE"
echo "=========================================="
# Use baseline file for comparison (retrained models compare, new models just show output)
BASELINE_PATH="/opt/adme/testing/baseline_predictions.json"
# Disable set -e temporarily to capture exit code even on failure
set +e
python scripts/run_tests.py --url "$BASE_URL" --output "$RESULTS_DIR" --baseline "$BASELINE_PATH"
TEST_EXIT=$?
set -e

# Find the latest timestamped run directory
LATEST_RUN=$(find "$RESULTS_DIR" -maxdepth 1 -type d -name "20*" | sort -r | head -1)

echo ""
echo "=========================================="
echo "TEST RUN COMPLETE"
echo "Finished: $(date)"
echo "=========================================="

if [ -n "$LATEST_RUN" ] && [ -d "$LATEST_RUN" ]; then
    echo "Results saved to: $LATEST_RUN"
    echo "  - predictions.json  (full test results)"
    echo "  - report.txt        (summary report with baseline comparison)"
    echo "  - test_run.log      (in $RESULTS_DIR)"
    
    # Write status file in run directory
    if [ $TEST_EXIT -eq 0 ]; then
        echo "SUCCESS" > "$LATEST_RUN/status.txt"
    else
        echo "TESTS_FAILED" > "$LATEST_RUN/status.txt"
    fi
else
    echo "Results saved to: $RESULTS_DIR"
fi

# Copy log file to run directory after all output is done
if [ -n "$LATEST_RUN" ] && [ -d "$LATEST_RUN" ]; then
    sync  # Flush buffers
    cp "$RESULTS_DIR/test_run.log" "$LATEST_RUN/test_run.log" 2>/dev/null || true
fi

# Keep server running for manual inspection (optional)
if [ "${KEEP_RUNNING:-false}" = "true" ]; then
    echo ""
    echo "Server staying up for inspection."
    echo "Connect to: $BASE_URL"
    echo "Press Ctrl+C to stop."
    wait $SERVER_PID
else
    echo ""
    echo "Shutting down server..."
    kill $SERVER_PID 2>/dev/null || true
    echo "Done."
fi

exit $TEST_EXIT

