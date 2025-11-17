# Testing Guide: Facial Region API

## 📚 Overview

This guide explains how to test the Facial Region SVG Service in different environments and with different types of data.

## 🎯 Two API Endpoints Available

### 1. **Synchronous Endpoint** (`/api/v1/frontal/crop/submit`)
- **Type**: Synchronous processing
- **Use Case**: Immediate response needed
- **Regions**: Legacy 10 facial regions (eyes, eyebrows, nose, lips, cheeks, face oval)
- **Response Time**: 2-5 seconds (or ~50-100ms with cache hit)

### 2. **Asynchronous Endpoint** (`/api/v1/frontal/crop/submit_async`)
- **Type**: Background task processing
- **Use Case**: Long-running tasks, queue management
- **Regions**: **NEW MediaPipe 5 facial regions** (forehead, nose, left_under_eye, right_under_eye, mouth)
- **Features**: Numbered labels, customizable colors, embedded image in SVG
- **Response Time**: Task ID returned immediately, poll for results

## 🧪 Testing Methods

### Method 1: Quick Test (Outside Docker)

**Requirements:**
- API server running locally or in Docker
- Python 3.12+ with `requests` installed

```bash
# Start the API server
make up

# Run the test script
python test_api_format.py
```

**What it tests:**
- Health endpoint
- Synchronous API endpoint with synthetic data
- Input/output format validation
- Response structure

### Method 2: Docker Environment Testing

**Run comprehensive tests inside Docker:**

```bash
# Start services
make up

# Test API in Docker (with synthetic data)
make test-docker-api

# Test with cache functionality
make test-cache

# Test Docker setup
make test-docker
```

**What it tests:**
- API endpoint with synthetic and real image data
- SVG generation and base64 encoding
- Mask contours generation
- Results saved to files
- Cache performance

### Method 3: Manual Testing with `curl`

#### Test Synchronous Endpoint

```bash
# Prepare test data
python3 << EOF
import json
import base64
from PIL import Image
import io

# Create test image
img = Image.new('RGB', (512, 512), color='lightblue')
buffer = io.BytesIO()
img.save(buffer, format='PNG')
img_b64 = base64.b64encode(buffer.getvalue()).decode()

# Create 478 landmarks
landmarks = [{"x": float(50 + (i % 20) * 20), "y": float(50 + (i // 20) * 10)} for i in range(478)]

# Save payload
payload = {
    "image": img_b64,
    "landmarks": landmarks,
    "segmentation_map": img_b64
}

with open('test_payload.json', 'w') as f:
    json.dump(payload, f)

print("Test payload created: test_payload.json")
EOF

# Test the synchronous API
curl -X POST http://localhost:8000/api/v1/frontal/crop/submit \
  -H "Content-Type: application/json" \
  -d @test_payload.json \
  | python3 -m json.tool
```

#### Test Asynchronous Endpoint (NEW)

```bash
# Submit task
TASK_ID=$(curl -X POST http://localhost:8000/api/v1/frontal/crop/submit_async \
  -H "Content-Type: application/json" \
  -d @test_payload.json \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")

echo "Task ID: $TASK_ID"

# Poll for status
curl http://localhost:8000/api/v1/frontal/crop/status/$TASK_ID \
  | python3 -m json.tool
```

## 🖼️ Testing with Real Images

### Prepare Your Data

1. **Image File**: Place your facial image as `test_image.jpg` or `test_image.png`
2. **Landmarks File**: Create `landmarks.json` with 478 MediaPipe landmarks
3. **Segmentation Map**: Place segmentation map as `segmentation_map.png`

**Landmarks Format** (`landmarks.json`):
```json
[
  {"x": 123.45, "y": 67.89},
  {"x": 124.56, "y": 68.90},
  ...  // 478 total points
]
```

**Generate Sample Landmarks:**
```bash
python3 generate_landmarks.py
```

### Test with Real Data

```python
#!/usr/bin/env python3
"""Test with real image data."""
import requests
import json
import base64

# Load your image
with open('test_image.jpg', 'rb') as f:
    image_b64 = base64.b64encode(f.read()).decode()

# Load landmarks
with open('landmarks.json', 'r') as f:
    landmarks = json.load(f)

# Load segmentation map
with open('segmentation_map.png', 'rb') as f:
    seg_map_b64 = base64.b64encode(f.read()).decode()

# Prepare payload
payload = {
    "image": image_b64,
    "landmarks": landmarks,
    "segmentation_map": seg_map_b64
}

# Test synchronous endpoint
print("Testing synchronous endpoint...")
response = requests.post(
    'http://localhost:8000/api/v1/frontal/crop/submit',
    json=payload
)

if response.status_code == 200:
    result = response.json()
    
    # Save SVG
    svg_content = base64.b64decode(result['svg']).decode()
    with open('result_sync.svg', 'w') as f:
        f.write(svg_content)
    print("✅ Synchronous test passed! SVG saved as result_sync.svg")
else:
    print(f"❌ Synchronous test failed: {response.status_code}")
    print(response.text)

# Test asynchronous endpoint (NEW MediaPipe regions)
print("\nTesting asynchronous endpoint...")
response = requests.post(
    'http://localhost:8000/api/v1/frontal/crop/submit_async',
    json=payload
)

if response.status_code == 200:
    task_data = response.json()
    task_id = task_data['task_id']
    print(f"Task submitted: {task_id}")
    
    # Poll for result
    import time
    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        status_response = requests.get(
            f'http://localhost:8000/api/v1/frontal/crop/status/{task_id}'
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            
            if status_data['status'] == 'SUCCESS':
                # Save SVG with embedded image and numbered regions
                svg_content = base64.b64decode(status_data['result']['svg']).decode()
                with open('result_async.svg', 'w') as f:
                    f.write(svg_content)
                print("✅ Asynchronous test passed! SVG saved as result_async.svg")
                print(f"   Regions detected: {len(status_data['result']['mask_contours'])}")
                break
            elif status_data['status'] == 'FAILURE':
                print(f"❌ Task failed: {status_data['error']}")
                break
            else:
                print(f"   Status: {status_data['status']}...")
        else:
            print(f"❌ Status check failed: {status_response.status_code}")
            break
else:
    print(f"❌ Asynchronous test failed: {response.status_code}")
    print(response.text)
```

## 📊 Expected Outputs

### Synchronous Endpoint Output
```json
{
  "svg": "PHN2ZyB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMi...",
  "mask_contours": {
    "1": [[x1, y1], [x2, y2], ...],
    "2": [[x1, y1], [x2, y2], ...],
    ...
  }
}
```

### Asynchronous Endpoint Output (Task Submission)
```json
{
  "task_id": "abc123-def456-...",
  "status": "PENDING",
  "message": "Task submitted successfully and is queued for processing",
  "submitted_at": "2025-11-17T10:30:45.123456",
  "estimated_completion_time": 30
}
```

### Asynchronous Endpoint Output (Status Check - SUCCESS)
```json
{
  "task_id": "abc123-def456-...",
  "status": "SUCCESS",
  "result": {
    "svg": "PHN2ZyB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMi...",
    "mask_contours": {
      "1": [[x1, y1], [x2, y2], ...],  // Forehead
      "2": [[x1, y1], [x2, y2], ...],  // Nose
      "3": [[x1, y1], [x2, y2], ...],  // Left under eye
      "4": [[x1, y1], [x2, y2], ...],  // Right under eye
      "5": [[x1, y1], [x2, y2], ...]   // Mouth
    }
  },
  "processing_time_ms": 2340.56
}
```

## 🎨 SVG Output Features

### Synchronous Endpoint SVG:
- 10 facial regions (legacy)
- Semi-transparent colored masks
- Optional landmark points
- No embedded image

### Asynchronous Endpoint SVG (NEW):
- 5 MediaPipe facial regions
- **Embedded original image** in the SVG
- **Numbered labels** (1-5) on each region
- Customizable colors and opacity
- Purple/violet theme by default
- Can be opened directly in browser

## 🔍 Troubleshooting

### API Server Not Running
```bash
# Check if services are up
make status

# View logs
make logs

# Restart services
make down
make up
```

### Invalid Landmarks Count
- **Requirement**: Exactly 478 landmarks
- **Solution**: Use `generate_landmarks.py` to create sample data

### Image Dimensions Mismatch
- **Error**: "Image and segmentation map dimensions must match"
- **Solution**: Ensure image and segmentation map have same width/height

### Base64 Encoding Issues
```python
# Correct way to encode
with open('image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Don't include data URL prefix unless API expects it
# payload = {"image": image_data}  # Just the base64 string
```

### Cache Issues
```bash
# Check cache stats
make cache-stats

# Clean cache if needed
make cache-clean

# View database
make db-shell
```

## 📈 Performance Testing

```bash
# Test cache performance
python3 << 'EOF'
import requests
import json
import time

# Load test payload
with open('test_payload.json', 'r') as f:
    payload = json.load(f)

# First request (cache miss)
start = time.time()
response1 = requests.post('http://localhost:8000/api/v1/frontal/crop/submit', json=payload)
time1 = time.time() - start

# Second request (cache hit)
start = time.time()
response2 = requests.post('http://localhost:8000/api/v1/frontal/crop/submit', json=payload)
time2 = time.time() - start

print(f"First request (cache miss): {time1:.3f}s")
print(f"Second request (cache hit): {time2:.3f}s")
print(f"Speedup: {time1/time2:.1f}x faster")
EOF
```

## 🎯 Next Steps

1. **View SVG Output**: Open `result_async.svg` in a web browser to see the embedded image with numbered regions
2. **Customize Colors**: Modify `DEFAULT_REGION_COLORS` in `tasks.py` for different color schemes
3. **Adjust Opacity**: Change `region_opacity` parameter (0.0-1.0) for more/less transparency
4. **Toggle Labels**: Set `show_labels=False` to hide region numbers
5. **Monitor Performance**: Use Grafana dashboard at http://localhost:3000 (when monitoring stack is enabled)

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Prometheus Metrics**: http://localhost:8000/metrics
- **Cache Statistics**: http://localhost:8000/api/v1/cache/stats
- **Recent Tasks**: http://localhost:8000/api/v1/cache/recent

## 💡 Tips

- Use **synchronous endpoint** for immediate responses and simple use cases
- Use **asynchronous endpoint** for production workflows with MediaPipe regions and embedded images
- The async endpoint generates SVGs with embedded images - perfect for standalone viewing
- Cache automatically improves performance for repeated requests
- Both endpoints support the same input format for easy switching