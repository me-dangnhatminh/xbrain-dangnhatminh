#!/bin/bash

# Script to run L1 integration tests for GeekBrain AI System
# This script checks prerequisites and runs the integration tests

set -e  # Exit on error

echo "=========================================="
echo "GeekBrain AI System - L1 Integration Tests"
echo "=========================================="
echo ""

# Check if we're in the correct directory
if [ ! -f "tests/integration/test_l1_integration.py" ]; then
    echo "Error: Must run from w4/ directory"
    echo "Usage: cd w4 && bash tests/integration/run_l1_tests.sh"
    exit 1
fi

# Check environment variables
echo "Checking environment variables..."

if [ -z "$BEDROCK_KB_ID" ]; then
    echo "Warning: BEDROCK_KB_ID is not set"
    echo "Please set it with: export BEDROCK_KB_ID='your-kb-id'"
    echo ""
fi

if [ -z "$API_BASE_URL" ]; then
    echo "Info: API_BASE_URL not set, using default: http://localhost:8001"
    export API_BASE_URL="http://localhost:8001"
fi

echo "  BEDROCK_KB_ID: ${BEDROCK_KB_ID:-'not set'}"
echo "  API_BASE_URL: $API_BASE_URL"
echo ""

# Check if API is running
echo "Checking if API is running at $API_BASE_URL..."

if curl -s -f "$API_BASE_URL/health" > /dev/null 2>&1; then
    echo "✓ API is running"
    echo ""
else
    echo "✗ API is not responding at $API_BASE_URL"
    echo ""
    echo "Please start the API server first:"
    echo "  cd w4/src"
    echo "  python main.py"
    echo ""
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest is not installed"
    echo "Install with: pip install pytest requests"
    exit 1
fi

# Run the tests
echo "Running L1 integration tests..."
echo "=========================================="
echo ""

# Run tests with verbose output
pytest tests/integration/test_l1_integration.py -v -s

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ All L1 integration tests passed!"
    echo "=========================================="
    exit 0
else
    echo ""
    echo "=========================================="
    echo "✗ Some tests failed. See output above."
    echo "=========================================="
    exit 1
fi
