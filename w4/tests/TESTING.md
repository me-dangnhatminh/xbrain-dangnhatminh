# Testing Guide for GeekBrain AI System

This guide explains how to run tests for the GeekBrain AI System.

## Test Structure

```
w4/tests/
├── unit/                    # Unit tests (fast, mocked dependencies)
│   └── test_rag_pipeline.py
├── integration/             # Integration tests (require running services)
│   ├── test_l1_integration.py
│   ├── run_l1_tests.sh
│   └── README.md
├── validation/              # Validation tests (end-to-end scenarios)
└── TESTING.md              # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install pytest requests
```

### 2. Run Unit Tests (No Setup Required)

Unit tests use mocked AWS services and don't require any running infrastructure:

```bash
cd w4
pytest tests/unit/ -v
```

### 3. Run Integration Tests (Requires Setup)

Integration tests require:
- AWS credentials configured
- Bedrock Knowledge Base created and synced
- API server running

**Setup:**

```bash
# Set environment variables
export BEDROCK_KB_ID="your-knowledge-base-id"
export API_BASE_URL="http://localhost:8001"

# Start API server (in separate terminal)
cd w4/src
python main.py
```

**Run tests:**

```bash
# Option 1: Use the test runner script
cd w4
bash tests/integration/run_l1_tests.sh

# Option 2: Run pytest directly
cd w4
pytest tests/integration/test_l1_integration.py -v
```

## Test Commands Reference

### Run All Tests

```bash
cd w4
pytest tests/ -v
```

### Run Specific Test Types

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# L1 tests only (using markers)
pytest -m l1 -v

# Integration tests only (using markers)
pytest -m integration -v
```

### Run Specific Test Files

```bash
# Run specific test file
pytest tests/integration/test_l1_integration.py -v

# Run specific test class
pytest tests/integration/test_l1_integration.py::TestL1Integration -v

# Run specific test method
pytest tests/integration/test_l1_integration.py::TestL1Integration::test_team_platform_lead_query -v
```

### Run with Different Output Levels

```bash
# Verbose output
pytest tests/ -v

# Very verbose output (show test names and docstrings)
pytest tests/ -vv

# Show print statements
pytest tests/ -v -s

# Show full traceback on failures
pytest tests/ -v --tb=long

# Show only failed tests
pytest tests/ -v --tb=short -x
```

### Run with Filtering

```bash
# Run tests matching a keyword
pytest tests/ -k "team_platform" -v

# Run tests NOT matching a keyword
pytest tests/ -k "not edge_case" -v

# Run only failed tests from last run
pytest tests/ --lf -v

# Run failed tests first, then others
pytest tests/ --ff -v
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit` - Unit tests (fast, mocked)
- `@pytest.mark.integration` - Integration tests (require services)
- `@pytest.mark.l1` - L1 (Simple RAG) tests
- `@pytest.mark.l2` - L2 (Multi-Source RAG) tests
- `@pytest.mark.l3` - L3 (Tool-Augmented RAG) tests
- `@pytest.mark.l4` - L4 (Memory-Enabled RAG) tests
- `@pytest.mark.slow` - Tests that take > 5 seconds

**Examples:**

```bash
# Run only unit tests
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run L1 and L2 tests
pytest -m "l1 or l2" -v

# Run integration tests but not slow ones
pytest -m "integration and not slow" -v
```

## Environment Variables

### Required for Integration Tests

```bash
# Bedrock Knowledge Base ID
export BEDROCK_KB_ID="your-kb-id-here"
```

### Optional

```bash
# Bedrock Model ID (defaults to Claude Sonnet)
export BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"

# API Base URL (defaults to http://localhost:8001)
export API_BASE_URL="http://localhost:8001"

# AWS Region (defaults to AWS CLI default)
export AWS_DEFAULT_REGION="us-east-1"
```

## Continuous Integration

For CI/CD pipelines, use this command to run tests with proper error handling:

```bash
# Run unit tests (always safe in CI)
pytest tests/unit/ -v --tb=short --junitxml=test-results.xml

# Run integration tests (only if services are available)
if [ -n "$BEDROCK_KB_ID" ]; then
    pytest tests/integration/ -v --tb=short --junitxml=integration-results.xml
fi
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'rag_pipeline'"

**Solution:** Make sure you're running pytest from the `w4/` directory, or add the src directory to PYTHONPATH:

```bash
cd w4
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/
```

### "Connection refused" or "API is not responding"

**Solution:** Start the API server:

```bash
cd w4/src
python main.py
```

### "Knowledge Base is not configured"

**Solution:** Set the BEDROCK_KB_ID environment variable:

```bash
export BEDROCK_KB_ID="your-kb-id-here"
```

### "Expected 'Alex Chen' in answer" (Test Failure)

**Possible causes:**
1. Knowledge Base not synced with correct documents
2. Documents don't contain expected information
3. Bedrock service issues

**Solution:** Verify Knowledge Base sync status and document content.

### Tests are slow

**Solution:** Run only unit tests for fast feedback:

```bash
pytest tests/unit/ -v
```

Or run integration tests in parallel (requires pytest-xdist):

```bash
pip install pytest-xdist
pytest tests/integration/ -v -n auto
```

## Test Coverage

To generate test coverage reports:

```bash
# Install coverage tools
pip install pytest-cov

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Best Practices

1. **Run unit tests frequently** - They're fast and catch most issues
2. **Run integration tests before commits** - Ensure end-to-end functionality
3. **Use markers to filter tests** - Run only relevant tests during development
4. **Check test output carefully** - Integration tests print useful debug info
5. **Keep tests independent** - Each test should be able to run in isolation
6. **Use descriptive test names** - Test names should explain what they verify

## Next Steps

After L1 integration tests pass:

1. Implement L2 integration tests (multi-source retrieval)
2. Implement L3 integration tests (tool-augmented RAG)
3. Implement L4 integration tests (memory-enabled conversations)
4. Add validation tests for complete user scenarios

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Markers](https://docs.pytest.org/en/stable/example/markers.html)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
