# Test Suite

Comprehensive test suite for the Facial Region SVG Service API.

## Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── fixtures/                # Test data files
│   ├── valid_payload.json  # Sample valid request payload
│   └── README.md
├── test_submit_endpoint.py  # Tests for /api/v1/frontal/crop/submit
└── README.md               # This file
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov httpx
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

### Run Specific Test File

```bash
pytest tests/test_submit_endpoint.py
```

### Run Specific Test Class

```bash
pytest tests/test_submit_endpoint.py::TestSubmitFacialProcessingTask
```

### Run Specific Test

```bash
pytest tests/test_submit_endpoint.py::TestSubmitFacialProcessingTask::test_successful_submission
```

### Run with Verbose Output

```bash
pytest -v
```

### Run and Stop on First Failure

```bash
pytest -x
```

## Test Coverage

The test suite covers:

### ✅ Happy Path Tests
- Successful task submission with valid payload
- Custom query parameters (show_labels, region_opacity, stroke_width)
- Custom region definitions
- Single region processing
- Boundary value testing

### ✅ Validation Tests
- Missing required fields (image, landmarks, segmentation_map)
- Invalid landmark count (not 478)
- Invalid landmark format
- Invalid segmentation_map structure
- Invalid landmark indices (>477 or <0)
- Negative coordinates
- Invalid parameter ranges

### ✅ Error Handling Tests
- Invalid base64 image data
- Image decode failures
- Out of range parameters
- Type validation errors

### ✅ Edge Cases
- Unicode region names
- Very long region names
- Duplicate indices in regions
- Empty segmentation_map
- Large landmark values
- Concurrent submissions

## Test Fixtures

### Adding Your Payload

Replace the placeholder in `tests/fixtures/valid_payload.json` with your actual test payload:

```bash
# Copy your payload
cat your_payload.json > tests/fixtures/valid_payload.json
```

Or paste directly into the file:
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "landmarks": [
    {"x": 100.5, "y": 200.3},
    ...
  ],
  "segmentation_map": {
    "forehead": [127, 162, 21, ...],
    ...
  }
}
```

## Mocking

The tests use mocking to avoid:
- Actual Celery task execution (uses `@patch` for `process_facial_regions_task`)
- Real image processing (mocks `decode_base64_image` where needed)
- Database operations
- Redis connections

This makes tests:
- ⚡ Fast (no I/O operations)
- 🔒 Isolated (no external dependencies)
- 🎯 Focused (testing API logic only)

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov httpx
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Writing New Tests

### Test Structure

```python
class TestYourFeature:
    """Test suite for your feature."""
    
    def test_success_case(self, valid_payload, mock_celery_task):
        """Test successful operation."""
        response = client.post("/api/v1/your/endpoint", json=valid_payload)
        assert response.status_code == 200
    
    def test_error_case(self, valid_payload):
        """Test error handling."""
        payload = valid_payload.copy()
        payload['field'] = 'invalid'
        response = client.post("/api/v1/your/endpoint", json=payload)
        assert response.status_code == 422
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Clear test names** describing what is tested
3. **Use fixtures** for shared setup
4. **Mock external dependencies**
5. **Test both success and failure paths**
6. **Document complex test logic**

## Debugging Tests

### Run with Print Statements

```bash
pytest -s  # Don't capture stdout
```

### Run with PDB Debugger

```bash
pytest --pdb  # Drop into debugger on failure
```

### Show Local Variables on Failure

```bash
pytest -l
```

## Test Markers

Use markers to organize tests:

```python
@pytest.mark.unit
def test_unit_logic():
    pass

@pytest.mark.integration  
def test_api_integration():
    pass

@pytest.mark.slow
def test_long_running():
    pass
```

Run specific markers:
```bash
pytest -m unit        # Run only unit tests
pytest -m "not slow"  # Skip slow tests
```

## Current Coverage

Run tests with coverage to see current coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

Target: **>80% coverage** for all API endpoints
