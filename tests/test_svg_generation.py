"""
Test cases for SVG generation functionality.
"""
import pytest
import base64
import numpy as np
from app.utils.svg_generation import (
    landmarks_to_svg_path,
    calculate_perpendicular_offset,
    extrapolate_forehead_to_hairline,
    generate_svg_mask_overlay
)
from app.core.config import MEDIAPIPE_FACE_REGIONS, DEFAULT_REGION_COLORS


@pytest.fixture
def sample_landmarks():
    """Create sample landmarks for testing."""
    landmarks = []
    # Create 478 landmarks in a simple grid pattern
    for i in range(478):
        landmarks.append({
            'x': float(100 + (i % 20) * 10),
            'y': float(100 + (i // 20) * 10)
        })
    return landmarks


@pytest.fixture
def simple_path_landmarks():
    """Create a simple set of landmarks for path testing."""
    return [
        {'x': 10.0, 'y': 10.0},
        {'x': 20.0, 'y': 15.0},
        {'x': 30.0, 'y': 10.0},
        {'x': 40.0, 'y': 20.0}
    ]


@pytest.fixture
def two_point_landmarks():
    """Create a two-point landmark set."""
    return [
        {'x': 5.0, 'y': 5.0},
        {'x': 15.0, 'y': 15.0}
    ]


@pytest.fixture
def three_point_landmarks():
    """Create a three-point landmark set."""
    return [
        {'x': 10.0, 'y': 10.0},
        {'x': 20.0, 'y': 20.0},
        {'x': 30.0, 'y': 10.0}
    ]


@pytest.fixture
def sample_image_base64():
    """Create a minimal base64 encoded image for testing."""
    # Create a small 10x10 PNG image
    from io import BytesIO
    try:
        from PIL import Image
        img = Image.new('RGB', (10, 10), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    except ImportError:
        # If PIL not available, return a dummy base64 string
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


class TestLandmarksToSvgPath:
    """Test cases for landmarks_to_svg_path function."""
    
    def test_empty_landmarks(self):
        """Test with empty landmarks list."""
        result = landmarks_to_svg_path([])
        assert result == ""
    
    def test_single_landmark(self):
        """Test with single landmark."""
        landmarks = [{'x': 10.0, 'y': 20.0}]
        result = landmarks_to_svg_path(landmarks)
        assert result == ""
    
    def test_two_landmarks(self, two_point_landmarks):
        """Test with two landmarks (should create a simple line)."""
        result = landmarks_to_svg_path(two_point_landmarks)
        assert result.startswith("M 5.00,5.00 L 15.00,15.00")
        assert "C" not in result  # Should not have curves
    
    def test_three_landmarks_not_smooth(self, three_point_landmarks):
        """Test with three landmarks without smoothing."""
        result = landmarks_to_svg_path(three_point_landmarks, smooth=False)
        assert result.startswith("M 10.00,10.00")
        assert "L 20.00,20.00" in result
        assert "L 30.00,10.00" in result
        assert "Z" in result  # Should be closed by default
    
    def test_three_landmarks_smooth(self, three_point_landmarks):
        """Test with three landmarks with smoothing (should still use lines)."""
        result = landmarks_to_svg_path(three_point_landmarks, smooth=True)
        # With only 3 points, should fall back to straight lines
        assert result.startswith("M 10.00,10.00")
        assert "L" in result
    
    def test_four_landmarks_smooth_closed(self, simple_path_landmarks):
        """Test with four landmarks with smooth curves and closed path."""
        result = landmarks_to_svg_path(simple_path_landmarks, closed=True, smooth=True)
        assert result.startswith("M 10.00,10.00")
        assert "C" in result  # Should have cubic bezier curves
        assert "Z" in result  # Should be closed
    
    def test_four_landmarks_smooth_open(self, simple_path_landmarks):
        """Test with four landmarks with smooth curves and open path."""
        result = landmarks_to_svg_path(simple_path_landmarks, closed=False, smooth=True)
        assert result.startswith("M 10.00,10.00")
        assert "C" in result  # Should have cubic bezier curves
        assert not result.endswith("Z")  # Should not be closed
    
    def test_path_coordinates_format(self, simple_path_landmarks):
        """Test that coordinates are formatted to 2 decimal places."""
        result = landmarks_to_svg_path(simple_path_landmarks)
        # Check that all numbers have proper decimal formatting
        import re
        # Find all numbers in the path
        numbers = re.findall(r'\d+\.\d+', result)
        # Verify all numbers have exactly 2 decimal places
        for num in numbers:
            assert len(num.split('.')[1]) == 2
    
    def test_not_smooth_closed(self, simple_path_landmarks):
        """Test non-smooth path with closed option."""
        result = landmarks_to_svg_path(simple_path_landmarks, closed=True, smooth=False)
        assert result.startswith("M 10.00,10.00")
        assert "L" in result
        assert "C" not in result  # Should not have curves
        assert result.endswith("Z")
    
    def test_not_smooth_open(self, simple_path_landmarks):
        """Test non-smooth path with open option."""
        result = landmarks_to_svg_path(simple_path_landmarks, closed=False, smooth=False)
        assert result.startswith("M 10.00,10.00")
        assert "L" in result
        assert "C" not in result  # Should not have curves
        assert not result.endswith("Z")


class TestCalculatePerpendicularOffset:
    """Test cases for calculate_perpendicular_offset function."""
    
    def test_horizontal_line_offset_up(self):
        """Test offsetting a horizontal line upward."""
        points = np.array([[0.0, 100.0], [100.0, 100.0], [200.0, 100.0]])
        offset_distance = -10.0  # Negative = upward
        result = calculate_perpendicular_offset(points, offset_distance)
        
        # For a horizontal line, perpendicular upward should decrease y
        assert result.shape == (3, 2)
        assert result[0][1] < points[0][1]  # y should decrease
        assert result[1][1] < points[1][1]
        assert result[2][1] < points[2][1]
    
    def test_horizontal_line_offset_down(self):
        """Test offsetting a horizontal line downward."""
        points = np.array([[0.0, 100.0], [100.0, 100.0], [200.0, 100.0]])
        offset_distance = 10.0  # Positive = downward
        result = calculate_perpendicular_offset(points, offset_distance)
        
        # For a horizontal line, perpendicular downward should increase y
        assert result.shape == (3, 2)
        assert result[0][1] > points[0][1]  # y should increase
        assert result[1][1] > points[1][1]
        assert result[2][1] > points[2][1]
    
    def test_vertical_line_offset(self):
        """Test offsetting a vertical line."""
        points = np.array([[100.0, 0.0], [100.0, 100.0], [100.0, 200.0]])
        offset_distance = 10.0
        result = calculate_perpendicular_offset(points, offset_distance)
        
        # For a vertical line, perpendicular offset should change x
        assert result.shape == (3, 2)
        assert result[0][0] != points[0][0]  # x should change
    
    def test_diagonal_line_offset(self):
        """Test offsetting a diagonal line."""
        points = np.array([[0.0, 0.0], [100.0, 100.0], [200.0, 200.0]])
        offset_distance = 10.0
        result = calculate_perpendicular_offset(points, offset_distance)
        
        # Offset should create parallel line
        assert result.shape == (3, 2)
        assert not np.array_equal(result, points)
    
    def test_single_point_offset(self):
        """Test offsetting with single point (edge case)."""
        # This might raise an error or handle gracefully
        points = np.array([[100.0, 100.0]])
        with pytest.raises(IndexError):
            calculate_perpendicular_offset(points, 10.0)
    
    def test_two_points_offset(self):
        """Test offsetting with exactly two points."""
        points = np.array([[0.0, 0.0], [100.0, 0.0]])
        offset_distance = -10.0
        result = calculate_perpendicular_offset(points, offset_distance)
        
        assert result.shape == (2, 2)
        # For horizontal line, y should decrease with negative offset
        assert result[0][1] < points[0][1]
        assert result[1][1] < points[1][1]
    
    def test_output_shape_matches_input(self):
        """Test that output shape matches input shape."""
        points = np.array([[i * 10.0, i * 5.0] for i in range(10)])
        offset_distance = 15.0
        result = calculate_perpendicular_offset(points, offset_distance)
        
        assert result.shape == points.shape
    
    def test_zero_offset(self):
        """Test with zero offset (should return similar but not identical due to calculation)."""
        points = np.array([[0.0, 0.0], [100.0, 100.0], [200.0, 200.0]])
        offset_distance = 0.0
        result = calculate_perpendicular_offset(points, offset_distance)
        
        # With zero offset, points should be very close to original
        assert np.allclose(result, points, atol=1e-10)


class TestExtrapolateForeheadToHairline:
    """Test cases for extrapolate_forehead_to_hairline function."""
    
    def test_basic_extrapolation(self, sample_landmarks):
        """Test basic forehead extrapolation."""
        forehead_indices = MEDIAPIPE_FACE_REGIONS['forehead']
        result = extrapolate_forehead_to_hairline(
            sample_landmarks, 
            forehead_indices,
            extension_ratio=1.0
        )
        
        assert len(result) == len(forehead_indices)
        # Check that all points have x and y keys
        for point in result:
            assert 'x' in point
            assert 'y' in point
    
    def test_extension_ratio_effect(self, sample_landmarks):
        """Test that extension ratio affects the output."""
        forehead_indices = MEDIAPIPE_FACE_REGIONS['forehead']
        
        result_small = extrapolate_forehead_to_hairline(
            sample_landmarks, 
            forehead_indices,
            extension_ratio=0.5
        )
        
        result_large = extrapolate_forehead_to_hairline(
            sample_landmarks, 
            forehead_indices,
            extension_ratio=2.0
        )
        
        # Extract top arc points that get modified
        top_forehead_indices = [162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251]
        
        # Find positions in forehead_indices
        for top_idx in top_forehead_indices:
            if top_idx in forehead_indices:
                pos = forehead_indices.index(top_idx)
                # Larger extension ratio should move points further up (smaller y)
                # Unless it's one of the edge cases
                if pos < len(result_small) and pos < len(result_large):
                    # Y values should generally be different
                    assert result_small[pos]['y'] != result_large[pos]['y']
    
    def test_preserves_non_top_arc_points(self, sample_landmarks):
        """Test that non-top-arc points are preserved."""
        forehead_indices = MEDIAPIPE_FACE_REGIONS['forehead']
        top_forehead_indices = [162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251]
        
        result = extrapolate_forehead_to_hairline(
            sample_landmarks, 
            forehead_indices,
            extension_ratio=1.0
        )
        
        # Check that non-top-arc points match original landmarks
        for i, idx in enumerate(forehead_indices):
            if idx not in top_forehead_indices:
                assert result[i]['x'] == sample_landmarks[idx]['x']
                assert result[i]['y'] == sample_landmarks[idx]['y']
    
    def test_output_length_matches_input(self, sample_landmarks):
        """Test that output length matches forehead_indices length."""
        forehead_indices = MEDIAPIPE_FACE_REGIONS['forehead']
        result = extrapolate_forehead_to_hairline(
            sample_landmarks, 
            forehead_indices
        )
        
        assert len(result) == len(forehead_indices)
    
    def test_custom_forehead_indices(self, sample_landmarks):
        """Test with custom forehead indices."""
        custom_indices = [10, 20, 30, 40, 50]
        result = extrapolate_forehead_to_hairline(
            sample_landmarks, 
            custom_indices,
            extension_ratio=1.5
        )
        
        assert len(result) == len(custom_indices)
        for point in result:
            assert 'x' in point
            assert 'y' in point
    
    def test_minimal_landmarks(self):
        """Test with minimal number of landmarks."""
        minimal_landmarks = [{'x': float(i), 'y': float(i)} for i in range(400)]
        forehead_indices = [10, 20, 30]
        
        result = extrapolate_forehead_to_hairline(
            minimal_landmarks,
            forehead_indices,
            extension_ratio=1.0
        )
        
        assert len(result) == len(forehead_indices)
    
    def test_default_extension_ratio(self, sample_landmarks):
        """Test with default extension ratio."""
        forehead_indices = MEDIAPIPE_FACE_REGIONS['forehead']
        result = extrapolate_forehead_to_hairline(
            sample_landmarks,
            forehead_indices
        )
        
        assert len(result) == len(forehead_indices)
    
    def test_top_arc_points_moved_upward(self, sample_landmarks):
        """Test that top arc points are moved upward (decreased y)."""
        forehead_indices = MEDIAPIPE_FACE_REGIONS['forehead']
        top_forehead_indices = [162, 21, 54, 103, 67, 109, 10, 338, 297, 332, 284, 251]
        
        result = extrapolate_forehead_to_hairline(
            sample_landmarks,
            forehead_indices,
            extension_ratio=1.0
        )
        
        # Check that top arc points have moved upward
        for i, idx in enumerate(forehead_indices):
            if idx in top_forehead_indices and idx < len(sample_landmarks):
                original_y = sample_landmarks[idx]['y']
                new_y = result[i]['y']
                # Y should decrease (move upward) for top arc points
                assert new_y < original_y, f"Point {idx} should move upward"


class TestGenerateSvgMaskOverlay:
    """Test cases for generate_svg_mask_overlay function."""
    
    def test_basic_svg_generation(self, sample_landmarks):
        """Test basic SVG mask generation."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        assert isinstance(result, str)
        assert result.startswith('<svg')
        assert '</svg>' in result
        assert 'width="640"' in result
        assert 'height="480"' in result
    
    def test_svg_with_image(self, sample_landmarks, sample_image_base64):
        """Test SVG generation with embedded image."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(
            dimensions, 
            sample_landmarks,
            image_base64=sample_image_base64
        )
        
        assert '<image' in result
        assert 'data:image/' in result
        assert 'xlink:href=' in result
    
    def test_svg_with_data_url_prefix(self, sample_landmarks):
        """Test SVG generation with image that has data URL prefix."""
        dimensions = [640, 480]
        image_with_prefix = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            image_base64=image_with_prefix
        )
        
        assert '<image' in result
        # Should strip the prefix and use clean base64
        assert 'data:image/' in result
    
    def test_default_facial_regions(self, sample_landmarks):
        """Test that default facial regions are used."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Should contain paths for default regions
        assert result.count('<path') >= 5  # forehead, nose, left_under_eye, right_under_eye, mouth
    
    def test_custom_facial_regions(self, sample_landmarks):
        """Test with custom facial regions."""
        dimensions = [640, 480]
        custom_regions = {
            'test_region': [10, 20, 30, 40, 50]
        }
        custom_colors = {
            'test_region': '#FF0000'
        }
        
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            facial_regions=custom_regions,
            region_colors=custom_colors
        )
        
        assert '<path' in result
        assert 'fill="#FF0000"' in result
    
    def test_custom_region_colors(self, sample_landmarks):
        """Test with custom region colors."""
        dimensions = [640, 480]
        custom_colors = {
            'forehead': '#123456',
            'nose': '#ABCDEF'
        }
        
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            region_colors=custom_colors
        )
        
        assert '#123456' in result
        assert '#ABCDEF' in result
    
    def test_custom_region_opacity(self, sample_landmarks):
        """Test with custom region opacity."""
        dimensions = [640, 480]
        custom_opacity = {
            'forehead': 0.8,
            'nose': 0.3
        }
        
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            region_opacity=custom_opacity
        )
        
        assert 'fill-opacity="0.8"' in result
        assert 'fill-opacity="0.3"' in result
    
    def test_show_labels_true(self, sample_landmarks):
        """Test with labels enabled."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            show_labels=True
        )
        
        assert '<text' in result
        assert 'font-family=' in result
        # Should have numbered labels
        assert '>1<' in result or '>2<' in result
    
    def test_show_labels_false(self, sample_landmarks):
        """Test with labels disabled."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            show_labels=False
        )
        
        assert '<text' not in result
    
    def test_stroke_width_zero(self, sample_landmarks):
        """Test with no stroke."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            stroke_width=0
        )
        
        # Should not have stroke attributes
        assert 'stroke=' not in result or 'stroke-width="0"' in result
    
    def test_stroke_width_positive(self, sample_landmarks):
        """Test with stroke width."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            stroke_width=2
        )
        
        assert 'stroke=' in result
        assert 'stroke-width="2"' in result
    
    def test_forehead_uses_extrapolation(self, sample_landmarks):
        """Test that forehead region uses hairline extrapolation."""
        dimensions = [640, 480]
        
        # Generate SVG
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Should contain path for forehead
        assert '<path' in result
        # Forehead should have the default color
        assert DEFAULT_REGION_COLORS['forehead'] in result
    
    def test_region_without_color_skipped(self, sample_landmarks):
        """Test that regions without colors are skipped."""
        dimensions = [640, 480]
        custom_regions = {
            'test_region': [10, 20, 30, 40]
        }
        # Don't provide color for test_region
        custom_colors = {}
        
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            facial_regions=custom_regions,
            region_colors=custom_colors
        )
        
        # Should not have paths since no colors provided
        assert '<path' not in result or result.count('<path') == 0
    
    def test_region_with_insufficient_landmarks(self, sample_landmarks):
        """Test that regions with less than 3 landmarks are skipped."""
        dimensions = [640, 480]
        custom_regions = {
            'tiny_region': [10, 20]  # Only 2 points
        }
        custom_colors = {
            'tiny_region': '#FF0000'
        }
        
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            facial_regions=custom_regions,
            region_colors=custom_colors
        )
        
        # Should not create path for region with < 3 points
        # The SVG will still be created but without this region
        assert '<svg' in result
    
    def test_output_is_valid_svg_structure(self, sample_landmarks):
        """Test that output has valid SVG structure."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Check basic SVG structure
        assert result.startswith('<svg')
        assert result.endswith('</svg>')
        assert 'xmlns="http://www.w3.org/2000/svg"' in result
        assert 'xmlns:xlink="http://www.w3.org/1999/xlink"' in result
    
    def test_label_positioning(self, sample_landmarks):
        """Test that labels are positioned at region centroids."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(
            dimensions,
            sample_landmarks,
            show_labels=True
        )
        
        # Check that text elements have x, y coordinates
        if '<text' in result:
            assert 'x=' in result
            assert 'y=' in result
            assert 'text-anchor="middle"' in result
            assert 'dominant-baseline="middle"' in result
    
    def test_default_opacity_value(self, sample_landmarks):
        """Test that default opacity is 0.65."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Should contain default opacity value
        assert 'fill-opacity="0.65"' in result
    
    def test_multiple_regions_rendered(self, sample_landmarks):
        """Test that multiple regions are all rendered."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Should have multiple path elements for different regions
        path_count = result.count('<path')
        assert path_count >= 5  # At least 5 default regions
    
    def test_dimensions_affect_svg_size(self, sample_landmarks):
        """Test that dimensions parameter affects SVG size."""
        dimensions1 = [640, 480]
        result1 = generate_svg_mask_overlay(dimensions1, sample_landmarks)
        
        dimensions2 = [1920, 1080]
        result2 = generate_svg_mask_overlay(dimensions2, sample_landmarks)
        
        assert 'width="640"' in result1
        assert 'height="480"' in result1
        assert 'width="1920"' in result2
        assert 'height="1080"' in result2


class TestSvgGenerationIntegration:
    """Integration tests for SVG generation workflow."""
    
    def test_full_workflow_with_all_parameters(self, sample_landmarks, sample_image_base64):
        """Test complete workflow with all parameters specified."""
        dimensions = [800, 600]
        custom_regions = {
            'forehead': MEDIAPIPE_FACE_REGIONS['forehead'],
            'nose': MEDIAPIPE_FACE_REGIONS['nose']
        }
        custom_colors = {
            'forehead': '#FF5733',
            'nose': '#33FF57'
        }
        custom_opacity = {
            'forehead': 0.7,
            'nose': 0.5
        }
        
        result = generate_svg_mask_overlay(
            dimensions=dimensions,
            landmarks=sample_landmarks,
            image_base64=sample_image_base64,
            facial_regions=custom_regions,
            region_colors=custom_colors,
            region_opacity=custom_opacity,
            show_labels=True,
            stroke_width=3
        )
        
        # Verify all elements are present
        assert '<svg' in result
        assert '</svg>' in result
        assert '<image' in result
        assert '<path' in result
        assert '<text' in result
        assert '#FF5733' in result
        assert '#33FF57' in result
        assert 'fill-opacity="0.7"' in result
        assert 'fill-opacity="0.5"' in result
        assert 'stroke-width="3"' in result
    
    def test_minimal_workflow(self, sample_landmarks):
        """Test minimal workflow with only required parameters."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Should still produce valid SVG
        assert '<svg' in result
        assert '</svg>' in result
        assert '<path' in result
    
    def test_svg_is_well_formed_xml(self, sample_landmarks):
        """Test that generated SVG is well-formed XML."""
        dimensions = [640, 480]
        result = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Basic XML well-formedness checks
        assert result.count('<svg') == result.count('</svg>')
        assert result.count('<path') == result.count('/>')
    
    def test_path_generation_consistency(self, sample_landmarks):
        """Test that path generation is consistent across multiple calls."""
        dimensions = [640, 480]
        result1 = generate_svg_mask_overlay(dimensions, sample_landmarks)
        result2 = generate_svg_mask_overlay(dimensions, sample_landmarks)
        
        # Should produce identical output for same input
        assert result1 == result2
