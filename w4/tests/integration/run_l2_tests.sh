#!/bin/bash

# Script to run L2 integration tests
# Usage: ./run_l2_tests.sh

set -e

echo "=========================================="
echo "Running L2 Integration Tests"
echo "=========================================="
echo ""

# Check if BEDROCK_KB_ID is set
if [ -z "$BEDROCK_KB_ID" ]; then
    echo "Error: BEDROCK_KB_ID environment variable is not set"
    echo "Please set it with: export BEDROCK_KB_ID=your-kb-id"
    exit 1
fi

echo "Knowledge Base ID: $BEDROCK_KB_ID"
echo ""

# Navigate to the tests/integration directory
cd "$(dirname "$0")"

# Run the tests with pytest
echo "Running L2 integration tests..."
python -m pytest test_l2_integration.py -v -s

echo ""
echo "=========================================="
echo "L2 Integration Tests Complete"
echo "=========================================="
