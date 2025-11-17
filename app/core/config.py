"""Core configuration and constants."""
import os
from typing import Dict, List


# API Configuration
API_TITLE = "Facial Region SVG Service"
API_VERSION = "1.0.0"
API_DESCRIPTION = "Processes facial landmarks and segmentation maps to generate SVG masks"

# Environment
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Redis/Celery Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://postgres:postgres@postgres:5432/facial_processing'
)
DEBUG_SQL = os.getenv('DEBUG_SQL', 'false').lower() == 'true'
CACHE_TTL_HOURS = int(os.getenv('CACHE_TTL_HOURS', '24'))

# Metrics Configuration
ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'

# Processing Configuration
LANDMARKS_COUNT = 478
DEFAULT_REGION_OPACITY = 0.65

# MediaPipe Face Mesh 478 landmark indices for facial regions
MEDIAPIPE_FACE_REGIONS: Dict[str, List[int]] = {
    'forehead': [127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389, 301, 293, 334, 296, 336, 9, 107, 66, 105, 63, 70],
    'nose': [55, 8, 285, 417, 412, 437, 420, 429, 279, 358, 294, 327, 326, 2, 97, 98, 64, 129, 49, 209, 198, 236, 196, 122, 193],
    "left_under_eye": [35, 226, 25, 110, 24, 23, 22, 26, 112, 244, 245, 128, 121, 120, 119, 118, 117, 111],
    "right_under_eye": [465, 464, 341, 256, 252, 253, 254, 339, 255, 359, 353, 383, 372, 340, 346, 347, 348, 349, 350, 357],
    'mouth': [234, 116, 36, 203, 165, 167, 164, 393, 391, 423, 266, 330, 345, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93]
}

# Default colors for regions
DEFAULT_REGION_COLORS: Dict[str, str] = {
    'forehead': '#B695C0',           # Purple for forehead
    'nose': '#D4A574',               # Beige/tan for nose
    'left_under_eye': '#B695C0',     # Purple for left under eye
    'right_under_eye': '#B695C0',    # Purple for right under eye
    'mouth': '#B695C0',              # Purple for mouth area
}

# Legacy facial regions (for backward compatibility)
LEGACY_FACIAL_REGIONS: Dict[str, Dict] = {
    "left_eye": {
        "indices": [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
        "color": "#FF6B6B80",
        "name": "Left Eye"
    },
    "right_eye": {
        "indices": [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466],
        "color": "#4ECDC480",
        "name": "Right Eye"
    },
    "left_eyebrow": {
        "indices": [70, 63, 105, 66, 107, 55, 65, 52, 53, 46],
        "color": "#45B7D180",
        "name": "Left Eyebrow"
    },
    "right_eyebrow": {
        "indices": [300, 293, 334, 296, 336, 285, 295, 282, 283, 276],
        "color": "#FFA07A80",
        "name": "Right Eyebrow"
    },
    "nose": {
        "indices": [168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 326, 327, 294, 278, 344, 440, 275, 4],
        "color": "#98D8C880",
        "name": "Nose"
    },
    "upper_lip": {
        "indices": [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78],
        "color": "#F7DC6F80",
        "name": "Upper Lip"
    },
    "lower_lip": {
        "indices": [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78],
        "color": "#BB8FCE80",
        "name": "Lower Lip"
    },
    "face_oval": {
        "indices": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109],
        "color": "#85C1E980",
        "name": "Face Oval"
    },
    "left_cheek": {
        "indices": [50, 101, 36, 205, 123, 203],
        "color": "#F8B88B80",
        "name": "Left Cheek"
    },
    "right_cheek": {
        "indices": [280, 330, 266, 425, 352, 423],
        "color": "#ABEBC680",
        "name": "Right Cheek"
    }
}
