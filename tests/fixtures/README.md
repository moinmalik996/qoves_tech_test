# Test Fixtures

This directory contains test fixtures (sample data) for the test suite.

## Files

- `valid_payload.json` - A complete valid request payload for the `/api/v1/frontal/crop/submit` endpoint
- Add your actual test payload JSON here

## Usage

```python
import json

with open('tests/fixtures/valid_payload.json', 'r') as f:
    payload = json.load(f)
```
