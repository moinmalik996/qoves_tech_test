"""Image processing utilities."""
import base64
import numpy as np
from io import BytesIO
from PIL import Image
from typing import List


def decode_base64_image(base64_str: str) -> np.ndarray:
    """
    Decode base64 string to numpy array image with error handling.
    
    Args:
        base64_str: Base64 encoded image string
        
    Returns:
        NumPy array of the decoded image
        
    Raises:
        ValueError: If image data is invalid
    """
    try:
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        img_data = base64.b64decode(base64_str)
        img = Image.open(BytesIO(img_data))
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return np.array(img)
    except Exception as e:
        raise ValueError(f"Invalid image data: {str(e)}")


def encode_svg_to_base64(svg_content: str) -> str:
    """
    Encode SVG string to base64.
    
    Args:
        svg_content: SVG content as string
        
    Returns:
        Base64 encoded SVG string
    """
    return base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')


def get_region_contours(landmarks, region_indices: List[int]) -> List[List[float]]:
    """
    Extract contour points for a specific facial region.
    
    Args:
        landmarks: List of landmark dicts with 'x' and 'y' keys or Landmark objects
        region_indices: List of landmark indices for this region
        
    Returns:
        List of [x, y] coordinate pairs
    """
    contour = []
    for idx in region_indices:
        if idx < len(landmarks):
            lm = landmarks[idx]
            # Support both dict and object formats
            if isinstance(lm, dict):
                contour.append([lm['x'], lm['y']])
            else:
                contour.append([lm.x, lm.y])
    return contour
