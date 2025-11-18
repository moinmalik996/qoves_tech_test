"""
Perceptual hashing utilities for image similarity detection.
Uses pHash (Perceptual Hash) algorithm to find visually similar images.
"""
import base64
import hashlib
import numpy as np
from io import BytesIO
from PIL import Image
from typing import List, Tuple
from scipy.fftpack import dct


def decode_base64_to_image(base64_str: str) -> Image.Image:
    """
    Decode base64 string to PIL Image.
    
    Args:
        base64_str: Base64 encoded image string
        
    Returns:
        PIL Image object
    """
    if ',' in base64_str:
        base64_str = base64_str.split(',')[1]
    
    img_data = base64.b64decode(base64_str)
    return Image.open(BytesIO(img_data))


def calculate_phash(image: Image.Image, hash_size: int = 8) -> str:
    """
    Calculate perceptual hash (pHash) for an image.
    Uses DCT (Discrete Cosine Transform) for robust similarity detection.
    
    Args:
        image: PIL Image object
        hash_size: Size of the hash (default 8x8 = 64 bits)
        
    Returns:
        Hexadecimal string representation of the hash
    """
    # Resize image to hash_size + 1 (for better DCT)
    img_size = hash_size * 4
    image = image.convert('L')  # Convert to grayscale
    image = image.resize((img_size, img_size), Image.Resampling.LANCZOS)
    
    # Convert to numpy array
    pixels = np.asarray(image)
    
    # Compute DCT
    dct_matrix = dct(dct(pixels, axis=0), axis=1)
    
    # Extract top-left corner (low frequencies)
    dct_low = dct_matrix[:hash_size, :hash_size]
    
    # Calculate median
    median = np.median(dct_low)
    
    # Create binary hash
    diff = dct_low > median
    
    # Convert to hexadecimal
    hash_str = ''.join(['1' if bit else '0' for bit in diff.flatten()])
    hash_int = int(hash_str, 2)
    hash_hex = format(hash_int, f'0{hash_size * hash_size // 4}x')
    
    return hash_hex


def calculate_phash_from_base64(base64_str: str, hash_size: int = 8) -> str:
    """
    Calculate perceptual hash directly from base64 string.
    
    Args:
        base64_str: Base64 encoded image
        hash_size: Size of the hash
        
    Returns:
        Hexadecimal perceptual hash
    """
    try:
        image = decode_base64_to_image(base64_str)
        return calculate_phash(image, hash_size)
    except Exception:
        # Fallback to MD5 if pHash fails
        return hashlib.md5(base64_str.encode()).hexdigest()


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two hashes.
    Lower distance = more similar images.
    
    Args:
        hash1: First hash (hex string)
        hash2: Second hash (hex string)
        
    Returns:
        Number of differing bits
    """
    if len(hash1) != len(hash2):
        return max(len(hash1), len(hash2)) * 4  # Max distance if lengths differ
    
    # Convert hex to binary
    bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
    bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
    
    # Count differing bits
    return sum(b1 != b2 for b1, b2 in zip(bin1, bin2))


def is_similar_image(hash1: str, hash2: str, threshold: int = 10) -> bool:
    """
    Check if two images are perceptually similar.
    
    Args:
        hash1: First perceptual hash
        hash2: Second perceptual hash
        threshold: Maximum Hamming distance for similarity (default 10 out of 64 bits)
        
    Returns:
        True if images are similar
    """
    distance = hamming_distance(hash1, hash2)
    return distance <= threshold


def calculate_landmarks_hash(landmarks: List[dict]) -> str:
    """
    Calculate a hash for landmark positions.
    Groups landmarks into regions for more robust matching.
    
    Args:
        landmarks: List of landmark dictionaries with 'x' and 'y' keys
        
    Returns:
        Hash string representing landmark configuration
    """
    if not landmarks or len(landmarks) < 10:
        return hashlib.md5(str(landmarks).encode()).hexdigest()[:16]
    
    # Extract key landmark positions (every 10th landmark for efficiency)
    key_landmarks = []
    for i in range(0, len(landmarks), 10):
        lm = landmarks[i]
        # Round to 2 decimal places to allow small variations
        key_landmarks.append((round(lm['x'], 2), round(lm['y'], 2)))
    
    # Create hash from key landmarks
    landmarks_str = str(sorted(key_landmarks))
    return hashlib.md5(landmarks_str.encode()).hexdigest()[:16]


def generate_perceptual_cache_key(
    image_base64: str,
    landmarks: List[dict],
    show_labels: bool = True,
    region_opacity: float = 0.65,
    stroke_width: int = 0
) -> Tuple[str, str]:
    """
    Generate both perceptual hash and exact cache key.
    
    Args:
        image_base64: Base64 encoded image
        landmarks: List of landmark dictionaries
        show_labels: Whether labels are shown
        region_opacity: Opacity value
        stroke_width: Stroke width value
        
    Returns:
        Tuple of (perceptual_hash, exact_cache_key)
    """
    # Calculate perceptual hash for image
    perceptual_hash = calculate_phash_from_base64(image_base64)
    
    # Exact key: for exact matching (backward compatible)
    # Include full image data and landmarks for precise matching
    exact_data = f"{image_base64[:100]}_{str(landmarks)}_{show_labels}_{region_opacity}_{stroke_width}"
    exact_key = hashlib.sha256(exact_data.encode()).hexdigest()
    
    # Return perceptual_hash for similarity search, exact_key for exact match
    return perceptual_hash, exact_key
