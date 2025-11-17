"""SVG generation utilities."""
import base64
from typing import List, Dict
from app.core.config import MEDIAPIPE_FACE_REGIONS, DEFAULT_REGION_COLORS


def landmarks_to_svg_path(landmarks: List[Dict[str, float]], closed: bool = True) -> str:
    """
    Convert a list of landmark points to an SVG path.

    Args:
        landmarks: List of dicts with 'x' and 'y' keys
        closed: Whether to close the path (Z command)

    Returns:
        SVG path string
    """
    if len(landmarks) < 2:
        return ""

    # Start with Move command
    path_parts = [f"M {landmarks[0]['x']:.2f},{landmarks[0]['y']:.2f}"]

    # Add Line commands for remaining points
    for point in landmarks[1:]:
        path_parts.append(f"L {point['x']:.2f},{point['y']:.2f}")

    # Close path if requested
    if closed:
        path_parts.append("Z")

    return " ".join(path_parts)


def generate_svg_mask_overlay(
    dimensions: List[int],
    landmarks: List[Dict[str, float]],
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
        image_base64: Base64 encoded image
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

    # Default colors
    if region_colors is None:
        region_colors = DEFAULT_REGION_COLORS.copy()

    # Default opacity
    if region_opacity is None:
        region_opacity = {region: 0.65 for region in facial_regions.keys()}

    # Start SVG
    svg_parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
    ]

    # Embed the background image if provided
    if image_base64:
        # Remove data URL prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Detect image format (default to jpeg)
        img_format = "jpeg"
        try:
            # Try to detect format from base64 data
            img_data = base64.b64decode(image_base64[:100])
            if img_data.startswith(b'\x89PNG'):
                img_format = "png"
        except Exception:
            pass

        svg_parts.append(
            f'  <image width="{width}" height="{height}" '
            f'xlink:href="data:image/{img_format};base64,{image_base64}"/>'
        )

    # Draw each facial region as filled mask
    label_counter = 1
    for region_name, indices in facial_regions.items():
        if region_name not in region_colors:
            continue

        # Extract landmarks for this region
        region_landmarks = []
        for idx in indices:
            if idx < len(landmarks):
                region_landmarks.append(landmarks[idx])

        if len(region_landmarks) < 3:
            continue

        # Convert to SVG path
        path_d = landmarks_to_svg_path(region_landmarks, closed=True)
        color = region_colors[region_name]
        opacity = region_opacity.get(region_name, 0.65)

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
