"""
A seperate script to generate an SVG overlay with colored masks over facial regions
based on MediaPipe Face Mesh landmarks, with an improved forehead extension method.
"""

import base64
from typing import List, Dict
import numpy as np


# MediaPipe Face Mesh 478 landmark indices for facial regions
MEDIAPIPE_FACE_REGIONS = {
    'forehead': [127, 162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251, 389, 301, 293, 334, 296, 336, 9, 107, 66, 105, 63, 70],
    'nose': [55, 8, 285, 417, 412, 437, 420, 429, 279, 358, 294, 327, 326, 2, 97, 98, 64, 129, 49, 209, 198, 236, 196, 122, 193],
    "left_under_eye": [35, 226, 25, 110, 24, 23, 22, 26, 112, 244, 245, 128, 121, 120, 119, 118, 117, 111],
    "right_under_eye": [465, 464, 341, 256, 252, 253, 254, 339, 255, 359, 353, 383, 372, 340, 346, 347, 348, 349, 350, 357],
    'mouth': [234, 116, 36, 203, 165, 167, 164, 393, 391, 423, 266, 330, 345, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93]
}


def landmarks_to_svg_path(landmarks: List[Dict[str, float]], closed: bool = True, smooth: bool = True) -> str:
    """
    Convert a list of landmark points to a smooth SVG path.

    Args:
        landmarks: List of dicts with 'x' and 'y' keys
        closed: Whether to close the path (Z command)
        smooth: Whether to use smooth curves (default: True)

    Returns:
        SVG path string with smooth curves
    """
    if len(landmarks) < 2:
        return ""
    
    if len(landmarks) == 2:
        return f"M {landmarks[0]['x']:.2f},{landmarks[0]['y']:.2f} L {landmarks[1]['x']:.2f},{landmarks[1]['y']:.2f}"
    
    if not smooth or len(landmarks) == 3:
        # Simple path with straight lines
        path_parts = [f"M {landmarks[0]['x']:.2f},{landmarks[0]['y']:.2f}"]
        for point in landmarks[1:]:
            path_parts.append(f"L {point['x']:.2f},{point['y']:.2f}")
        if closed:
            path_parts.append("Z")
        return " ".join(path_parts)

    # Create array of points for easier manipulation
    pts = [(p['x'], p['y']) for p in landmarks]
    if closed:
        # Add first point to end for closed curves
        pts = pts + [pts[0]]
    
    # Start path
    path_parts = [f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"]
    
    # Calculate smooth cubic Bezier curves
    for i in range(len(pts) - 1):
        # Get four points for Catmull-Rom calculation
        if i == 0:
            p0 = pts[0] if not closed else pts[-2]
        else:
            p0 = pts[i - 1]
        
        p1 = pts[i]
        p2 = pts[i + 1]
        
        if i + 2 < len(pts):
            p3 = pts[i + 2]
        else:
            p3 = pts[1] if closed else pts[i + 1]
        
        # Catmull-Rom to Bezier conversion
        # Control points for cubic Bezier curve from p1 to p2
        cp1_x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1_y = p1[1] + (p2[1] - p0[1]) / 6.0
        
        cp2_x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2_y = p2[1] - (p3[1] - p1[1]) / 6.0
        
        # Add cubic Bezier curve segment
        path_parts.append(f"C {cp1_x:.2f},{cp1_y:.2f} {cp2_x:.2f},{cp2_y:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    
    if closed:
        path_parts.append("Z")
    
    return " ".join(path_parts)


def calculate_perpendicular_offset(points: np.ndarray, offset_distance: float) -> np.ndarray:
    """
    Calculate points that are offset perpendicular to the curve.
    For forehead extension, negative offset_distance moves upward (in image coordinates).
    
    Args:
        points: Array of shape (n, 2) containing [x, y] coordinates
        offset_distance: Distance to offset perpendicular to the curve (negative = upward)
        
    Returns:
        Array of shape (n, 2) containing offset points
    """
    extended_points = []
    
    for i in range(len(points)):
        # Calculate tangent vector using neighboring points
        if i == 0:
            # Use forward difference for first point
            tangent = points[i+1] - points[i]
        elif i == len(points) - 1:
            # Use backward difference for last point
            tangent = points[i] - points[i-1]
        else:
            # Use central difference for middle points
            tangent = points[i+1] - points[i-1]
        
        # Normalize tangent vector
        tangent_norm = tangent / np.linalg.norm(tangent)
        
        # Calculate perpendicular vector (rotate 90 degrees counterclockwise)
        # In image coordinates (y increases downward), perpendicular upward is:
        perpendicular = np.array([-tangent_norm[1], tangent_norm[0]])
        
        # Offset the point (negative for upward in image coords)
        new_point = points[i] - perpendicular * offset_distance
        extended_points.append(new_point)
    
    return np.array(extended_points)


def extrapolate_forehead_to_hairline(
    landmarks: List[Dict[str, float]], 
    forehead_indices: List[int],
    extension_ratio: float = 1.0,
    num_hairline_points: int = 12
) -> List[Dict[str, float]]:
    """
    Extrapolate forehead points upward to approximate hairline using perpendicular offset method.
    
    Strategy:
    1. Extract top forehead arc landmarks (162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251)
    2. Calculate perpendicular offset to create extended versions of these points
    3. Replace these specific points in the forehead_indices array with their extended versions
    4. Keep all other points in their original positions
    
    Args:
        landmarks: All 478 MediaPipe facial landmarks
        forehead_indices: Original forehead landmark indices (default order maintained)
        extension_ratio: How far to extend upward (0.5-2.0 typical, default 1.5 = 150%)
        num_hairline_points: Not used in this method (kept for compatibility)
        
    Returns:
        Forehead boundary points with extended top arc points replaced in their original positions
    """
    # Top forehead arc landmarks that need to be extended
    top_forehead_indices = [162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251]
    
    # Extract top arc coordinates
    top_arc = np.array([[landmarks[i]['x'], landmarks[i]['y']] 
                        for i in top_forehead_indices if i < len(landmarks)])
    
    # Eyebrow landmarks (lower reference points for calculating extension distance)
    eyebrow_indices = [70, 63, 105, 66, 107, 336, 296, 334, 293, 300]
    eyebrow_points = np.array([[landmarks[i]['x'], landmarks[i]['y']] 
                               for i in eyebrow_indices if i < len(landmarks)])
    
    # Calculate extension distance based on forehead height
    top_y_avg = np.mean(top_arc[:, 1])
    eyebrow_y_avg = np.mean(eyebrow_points[:, 1])
    forehead_height = eyebrow_y_avg - top_y_avg
    base_extension_distance = forehead_height * extension_ratio
    
    # Extend points directly upward with variable distance
    # Points 162, 21, 54, 103, 67 get MUCH LESS extension (reduce upward movement)
    hairline_arc = top_arc.copy()
    
    # Apply different extension amounts for different points
    reduced_extension_indices = [162, 21, 54, 103]  # Points that need much less extension (67 removed)
    
    for i, idx in enumerate(top_forehead_indices):
        if idx in reduced_extension_indices:
            # Use only 30% of the base extension for these points
            extension = base_extension_distance * 0.3
        elif idx == 67:
            # Point 67 gets much more extension (move much more upward)
            extension = base_extension_distance * 0.8
        else:
            extension = base_extension_distance
        
        hairline_arc[i, 1] = hairline_arc[i, 1] - extension  # Move Y upward
        
        # Adjust X coordinates for specific points
        # Inward means towards center (increase X for left side)
        # Outward means away from center (decrease X for left side, increase for right side)
        if idx == 162:
            hairline_arc[i, 0] += 20  # Move inward (right) by 20px
        elif idx == 21:
            hairline_arc[i, 0] += 15  # Move inward (right) by 15px
        elif idx == 54:
            hairline_arc[i, 0] += 10  # Move inward (right) by 10px
        elif idx == 103:
            hairline_arc[i, 0] -= 10  # Move outward (left) by 10px
        elif idx == 67:
            hairline_arc[i, 0] -= 5  # Move slightly left by 5px
    
    # Create a mapping of index -> extended coordinates
    extended_coords = {}
    for i, idx in enumerate(top_forehead_indices):
        extended_coords[idx] = {
            'x': float(hairline_arc[i][0]),
            'y': float(hairline_arc[i][1])
        }
    
    # Build the forehead boundary, replacing extended points in their original positions
    extended_boundary = []
    
    for idx in forehead_indices:
        if idx in extended_coords:
            # Use extended coordinates for top arc points
            extended_boundary.append(extended_coords[idx])
        else:
            # Use original coordinates for other points
            extended_boundary.append({
                'x': landmarks[idx]['x'],
                'y': landmarks[idx]['y']
            })
    
    return extended_boundary


def generate_svg_mask_overlay(
    dimensions: List[int],
    landmarks: List[Dict[str, float]],
    image_path: str = None,
    image_base64: str = None,
    facial_regions: Dict[str, List[int]] = None,
    region_colors: Dict[str, str] = None,
    region_opacity: Dict[str, float] = None,
    show_labels: bool = True,
    stroke_width: int = 0
) -> str:
    """
    Generate SVG with filled, semi-transparent colored masks over facial regions.

    Args:
        dimensions: [width, height] of the image
        landmarks: List of all facial landmarks with 'x' and 'y' keys (478 for MediaPipe)
        image_path: Path to the portrait image file
        image_base64: Base64 encoded image (alternative to image_path)
        facial_regions: Dict mapping region names to landmark indices
        region_colors: Dict mapping region names to colors (hex format)
        region_opacity: Dict mapping region names to opacity values (0.0-1.0)
        show_labels: Whether to show region labels (numbers)
        stroke_width: Width of stroke around regions (0 for no stroke)

    Returns:
        SVG string with embedded image and colored masks
    """
    width, height = dimensions

    # Use MediaPipe Face Mesh regions by default
    if facial_regions is None:
        facial_regions = {
            'forehead': MEDIAPIPE_FACE_REGIONS['forehead'],
            'nose': MEDIAPIPE_FACE_REGIONS['nose'],
            'left_under_eye': MEDIAPIPE_FACE_REGIONS['left_under_eye'],
            'right_under_eye': MEDIAPIPE_FACE_REGIONS['right_under_eye'],
            'mouth': MEDIAPIPE_FACE_REGIONS['mouth'],
        }

    # Default colors (purple/violet theme like your example)
    if region_colors is None:
        region_colors = {
            'forehead': '#B695C0',           # Purple for forehead (region 1)
            'nose': '#D4A574',               # Beige/tan for nose (region 5)
            'left_under_eye': '#B695C0',     # Purple for left under eye
            'right_under_eye': '#B695C0',
            'mouth': '#B695C0',               # Purple for mouth area
        }

    # Default opacity
    if region_opacity is None:
        region_opacity = {region: 0.6 for region in facial_regions.keys()}

    # Prepare image embedding
    image_data = ""
    if image_base64:
        image_data = image_base64
    elif image_path:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

    # Start SVG
    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
    ]

    # Embed the background image if provided
    if image_data:
        # Detect image format
        img_format = "jpeg"
        if image_path and image_path.lower().endswith('.png'):
            img_format = "png"

        svg_parts.append(
            f'  <image width="{width}" height="{height}" '
            f'xlink:href="data:image/{img_format};base64,{image_data}"/>'
        )

    # Draw each facial region as filled mask
    label_counter = 1
    for region_name, indices in facial_regions.items():
        if region_name not in region_colors:
            continue

        # Extract landmarks for this region
        region_landmarks = []
        
        # Special handling for forehead: use extrapolated hairline
        if region_name == 'forehead':
            region_landmarks = extrapolate_forehead_to_hairline(
                landmarks=landmarks,
                forehead_indices=indices,
                extension_ratio=1.5,  # Extend 150% upward (adjustable)
                num_hairline_points=12
            )
        else:
            # Standard landmark extraction for other regions
            for idx in indices:
                if idx < len(landmarks):
                    region_landmarks.append(landmarks[idx])

        if len(region_landmarks) < 3:
            continue

        # Convert to SVG path
        path_d = landmarks_to_svg_path(region_landmarks, closed=True)
        color = region_colors[region_name]
        opacity = region_opacity.get(region_name, 0.6)

        # Draw filled region
        svg_parts.append(
            f'  <path d="{path_d}" '
            f'fill="{color}" '
            f'fill-opacity="{opacity}" '
        )

        if stroke_width > 0:
            svg_parts[-1] += f'stroke="{color}" stroke-width="{stroke_width}" '

        svg_parts[-1] += '/>'

        # Add label if requested
        if show_labels and len(region_landmarks) > 0:
            # Calculate centroid of the region for label placement
            center_x = sum(p['x'] for p in region_landmarks) / len(region_landmarks)
            center_y = sum(p['y'] for p in region_landmarks) / len(region_landmarks)

            svg_parts.append(
                f'  <text x="{center_x:.2f}" y="{center_y:.2f}" '
                f'font-family="Arial, sans-serif" font-size="40" font-weight="bold" '
                f'fill="white" text-anchor="middle" dominant-baseline="middle" '
                f'opacity="0.9">{label_counter}</text>'
            )
            label_counter += 1

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)

# Example usage with your MediaPipe data
if __name__ == "__main__":

    from landmarks import landmarks_data  # Assuming landmarks_data is a list of dicts with 'x' and 'y' keys

    dimensions = [1101, 1100]

    # Customize regions and colors to match your example
    custom_regions = {
        'forehead': MEDIAPIPE_FACE_REGIONS['forehead'],
        'nose': MEDIAPIPE_FACE_REGIONS['nose'],
        'left_under_eye': MEDIAPIPE_FACE_REGIONS['left_under_eye'],
        'right_under_eye': MEDIAPIPE_FACE_REGIONS['right_under_eye'],
        'mouth': MEDIAPIPE_FACE_REGIONS['mouth'],
    }

    custom_colors = {
        'forehead': '#4A90E2',          # Bright Blue
        'nose': '#7ED321',              # Fresh Green
        'left_under_eye': '#F5A623',    # Warm Amber
        'right_under_eye': '#F5A623',   # Warm Amber
        'mouth': '#D0021B',             # Strong Crimson
}

    custom_opacity = {
        'forehead': 0.65,
        'nose': 0.65,
        'left_under_eye': 0.65,
        'right_under_eye': 0.65,
        'mouth': 0.65,
    }

    svg_content = generate_svg_mask_overlay(
        dimensions=dimensions,
        landmarks=landmarks_data,
        image_path="data/original_image.png",  # CHANGE THIS to your image path
        facial_regions=custom_regions,
        region_colors=custom_colors,
        region_opacity=custom_opacity,
        show_labels=True,
        stroke_width=0
    )

    # Save the SVG
    with open("face_mask_overlay.svg", "w") as f:
        f.write(svg_content)