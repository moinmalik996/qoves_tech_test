"""
Example payload for the updated /api/v1/frontal/crop/submit endpoint
with custom segmentation_map.
"""

import requests


# Example 1: Using the default MediaPipe regions
example_request_default = {
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",  # Your base64 image
    "landmarks": [
        {"x": 100.5, "y": 200.3},
        {"x": 101.2, "y": 201.1},
        # ... 476 more landmarks (total 478)
    ],
    "segmentation_map": {
        "forehead": [127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389, 301, 293, 334, 296, 336, 9, 107, 66, 105, 63, 70],
        "nose": [55, 8, 285, 417, 412, 437, 420, 429, 279, 358, 294, 327, 326, 2, 97, 98, 64, 129, 49, 209, 198, 236, 196, 122, 193],
        "left_under_eye": [35, 226, 25, 110, 24, 23, 22, 26, 112, 244, 245, 128, 121, 120, 119, 118, 117, 111],
        "right_under_eye": [465, 464, 341, 256, 252, 253, 254, 339, 255, 359, 353, 383, 372, 340, 346, 347, 348, 349, 350, 357],
        "mouth": [234, 116, 36, 203, 165, 167, 164, 393, 391, 423, 266, 330, 345, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93]
    }
}

# Example 2: Using custom regions
example_request_custom = {
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "landmarks": [
        {"x": 100.5, "y": 200.3},
        # ... 477 more landmarks
    ],
    "segmentation_map": {
        "upper_face": [10, 21, 54, 103, 67, 109, 127, 162, 338, 297, 332, 284],
        "mid_face": [8, 55, 285, 417, 412, 437],
        "lower_face": [234, 116, 36, 203, 165, 167, 164, 393, 391, 423],
        "left_cheek": [50, 101, 118, 119, 120, 121, 128],
        "right_cheek": [280, 330, 347, 348, 349, 350, 357]
    }
}

# Example 3: Single region analysis
example_request_single_region = {
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "landmarks": [
        {"x": 100.5, "y": 200.3},
        # ... 477 more landmarks
    ],
    "segmentation_map": {
        "nose_only": [55, 8, 285, 417, 412, 437, 420, 429, 279, 358, 294, 327, 326, 2, 97, 98, 64, 129, 49, 209, 198, 236, 196, 122, 193]
    }
}

# URL parameters (query string)
query_params = {
    "show_labels": True,        # Show numbered labels on regions
    "region_opacity": 0.65,     # Opacity of region masks (0.0 to 1.0)
    "stroke_width": 0           # Width of stroke around regions (0 for no stroke)
}

# Full request example using requests library

def submit_facial_processing_task(image_base64, landmarks, segmentation_map, 
                                   show_labels=True, region_opacity=0.65, stroke_width=0):
    """
    Submit a facial processing task to the API.
    
    Args:
        image_base64: Base64 encoded image string
        landmarks: List of 478 landmark dicts with 'x' and 'y' keys
        segmentation_map: Dict mapping region names to lists of landmark indices
        show_labels: Whether to show region labels
        region_opacity: Opacity of region masks (0.0-1.0)
        stroke_width: Stroke width around regions (0 for no stroke)
    
    Returns:
        Response with task_id and status
    """
    url = "http://localhost:8000/api/v1/frontal/crop/submit"
    
    payload = {
        "image": image_base64,
        "landmarks": landmarks,
        "segmentation_map": segmentation_map
    }
    
    params = {
        "show_labels": show_labels,
        "region_opacity": region_opacity,
        "stroke_width": stroke_width
    }
    
    response = requests.post(url, json=payload, params=params)
    return response.json()


def get_task_status(task_id):
    """
    Poll the status of a submitted task.
    
    Args:
        task_id: Task ID returned from submit endpoint
    
    Returns:
        Task status and results
    """
    url = f"http://localhost:8000/api/v1/frontal/crop/status/{task_id}"
    response = requests.get(url)
    return response.json()


# Usage example
if __name__ == "__main__":
    # Prepare your data
    from landmarks import landmarks_data  # Your 478 landmarks
    import base64
    
    # Read and encode image
    with open("path/to/your/image.jpg", "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    # Define custom segmentation map
    custom_regions = {
        "forehead": [127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389],
        "eyes_region": [35, 226, 25, 110, 465, 464, 341, 256],
        "nose": [55, 8, 285, 417, 412, 437, 420, 429],
        "mouth": [234, 116, 36, 203, 165, 167, 164, 393, 391, 423]
    }
    
    # Submit task
    result = submit_facial_processing_task(
        image_base64=image_base64,
        landmarks=landmarks_data,
        segmentation_map=custom_regions,
        show_labels=True,
        region_opacity=0.7,
        stroke_width=2
    )
    
    print(f"Task submitted: {result['task_id']}")
    print(f"Status: {result['status']}")
    
    # Poll for results
    import time
    task_id = result['task_id']
    
    while True:
        status = get_task_status(task_id)
        print(f"Current status: {status['status']}")
        
        if status['status'] == 'SUCCESS':
            print("Task completed!")
            print(f"SVG data: {status['result']['svg_base64'][:100]}...")
            print(f"Regions detected: {list(status['result']['region_data'].keys())}")
            break
        elif status['status'] == 'FAILURE':
            print(f"Task failed: {status['error']}")
            break
        
        time.sleep(2)  # Wait 2 seconds before polling again
