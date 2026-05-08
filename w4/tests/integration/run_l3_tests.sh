#!/bin/bash

# Script to run L3 integration tests
# This script ensures all prerequisites are met before running tests

set -e  # Exit on error

echo "=========================================="
echo "L3 Integration Tests Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "../../geekbrain.db" ]; then
    echo -e "${RED}Error: geekbrain.db not found. Please run from w4/tests/integration/ directory${NC}"
    exit 1
fi

# Check if monitoring API is running
echo "Checking Monitoring API..."
if curl -s http://localhost:8000/services > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Monitoring API is running${NC}"
else
    echo -e "${RED}✗ Monitoring API is not running${NC}"
    echo -e "${YELLOW}Please start monitoring API:${NC}"
    echo "  cd w4"
    echo "  python monitoring_api.py"
    exit 1
fi

# Check if main API is running
echo "Checking Main API..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Main API is running${NC}"
else
    echo -e "${RED}✗ Main API is not running${NC}"
    echo -e "${YELLOW}Please start main API:${NC}"
    echo "  cd w4/src"
    echo "  uvicorn main:app --reload --port 8001"
    exit 1
fi

# Check environment variables
echo "Checking environment variables..."
if [ -z "$BEDROCK_KB_ID" ]; then
    echo -e "${YELLOW}Warning: BEDROCK_KB_ID not set${NC}"
    echo "Some tests may fail if Knowledge Base is not configured"
fi

echo ""
echo "=========================================="
echo "Running L3 Integration Tests"
echo "=========================================="
echo ""

# Run pytest with L3 marker
cd ../..
pytest tests/integration/test_l3_integration.py -v -s -m l3 "$@"

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All L3 tests passed!${NC}"
else
    echo -e "${RED}✗ Some L3 tests failed${NC}"
fi
echo "=========================================="

exit $TEST_EXIT_CODE
