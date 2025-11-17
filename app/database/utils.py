"""Database utility functions for caching and key generation."""
import json
import hashlib


def generate_cache_key(
    image_data: str, 
    landmarks: list, 
    segmentation_map: str, 
    show_landmarks: bool = False, 
    region_opacity: float = 0.7
) -> str:
    """
    Generate a consistent cache key from input parameters.
    
    Args:
        image_data: Base64 encoded image string
        landmarks: List of landmark dictionaries
        segmentation_map: Base64 encoded segmentation map
        show_landmarks: Whether landmarks are shown in output
        region_opacity: Opacity value for regions
        
    Returns:
        SHA256 hash string for cache key
    """
    # Create a string representation of all input parameters
    cache_input = {
        'image_hash': hashlib.md5(image_data.encode()).hexdigest()[:16],
        'landmarks_hash': hashlib.md5(str(landmarks).encode()).hexdigest()[:16],
        'segmentation_hash': hashlib.md5(segmentation_map.encode()).hexdigest()[:16],
        'show_landmarks': show_landmarks,
        'region_opacity': round(region_opacity, 2)  # Round to avoid float precision issues
    }
    
    # Create SHA256 hash of the combined input
    cache_string = json.dumps(cache_input, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()
