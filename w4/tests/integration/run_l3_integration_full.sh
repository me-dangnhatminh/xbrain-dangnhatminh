#!/bin/bash

# Script to run L3 integration tests (Task 14.4)
# 
# This script runs the integration tests for L3 Tool-Augmented RAG functionality.
# 
# Prerequisites:
# 1. API server running on port 8001
# 2. Monitoring API running on port 8000
# 3. Database seeded with test data
# 4. AWS credentials configured
# 5. BEDROCK_KB_ID environment variable set

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================"
echo "L3 Integration Tests - Task 14.4"
echo "========================================"
echo ""

# Check if API server is running
echo -n "Checking API server (port 8001)... "
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "Please start the API server:"
    echo "  cd w4/src"
    echo "  python main.py"
    echo ""
    exit 1
fi

# Check if Monitoring API is running
echo -n "Checking Monitoring API (port 8000)... "
if curl -s http://localhost:8000/services > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "Please start the Monitoring API:"
    echo "  cd w4"
    echo "  python monitoring_api.py"
    echo ""
    exit 1
fi

# Check if BEDROCK_KB_ID is set
echo -n "Checking BEDROCK_KB_ID... "
if [ -z "$BEDROCK_KB_ID" ]; then
    echo -e "${RED}✗ Not set${NC}"
    echo ""
    echo "Please set BEDROCK_KB_ID environment variable:"
    echo "  export BEDROCK_KB_ID=your-kb-id-here"
    echo ""
    exit 1
else
    echo -e "${GREEN}✓ Set${NC}"
fi

# Check if database exists
echo -n "Checking database... "
if [ -f "w4/geekbrain.db" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${YELLOW}⚠ Not found${NC}"
    echo ""
    echo "Database not found. Please seed the database:"
    echo "  cd w4"
    echo "  python seed_data.py"
    echo ""
fi

echo ""
echo "========================================"
echo "Running L3 Integration Tests"
echo "========================================"
echo ""

# Change to w4 directory
cd "$(dirname "$0")/../.."

# Run the tests
pytest tests/integration/test_l3_integration_full.py -v -s \
    --tb=short \
    --color=yes \
    -m "integration and l3"

# Capture exit code
EXIT_CODE=$?

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All L3 Integration Tests Passed${NC}"
else
    echo -e "${RED}✗ Some L3 Integration Tests Failed${NC}"
fi
echo "========================================"

exit $EXIT_CODE
