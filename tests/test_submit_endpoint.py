"""
Test cases for /api/v1/frontal/crop/submit endpoint.
Tests both successful submissions and various error conditions.
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app


client = TestClient(app)


# Test fixtures will be loaded from JSON file
@pytest.fixture
def valid_payload():
    """Load valid test payload from JSON file."""
    # This will be updated with your actual payload
    with open('tests/fixtures/valid_payload.json', 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_celery_task():
    """Mock Celery task to avoid actual processing during tests."""
    with patch('app.api.routes.process_facial_regions_task') as mock:
        mock_result = MagicMock()
        mock_result.id = 'test-task-id-12345'
        mock.delay.return_value = mock_result
        yield mock


class TestSubmitFacialProcessingTask:
    """Test suite for the facial processing task submission endpoint."""
    
    def test_successful_submission(self, valid_payload, mock_celery_task):
        """Test successful task submission with valid payload."""
        response = client.post(
            "/api/v1/frontal/crop/submit",
            json=valid_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'task_id' in data
        assert 'status' in data
        assert 'message' in data
        assert 'submitted_at' in data
        assert 'estimated_completion_time' in data
        
        # Verify response values
        assert data['status'] == 'PENDING'
        assert data['task_id'] == 'test-task-id-12345'
        assert 'successfully' in data['message'].lower()
        assert data['estimated_completion_time'] > 0
        
        # Verify Celery task was called
        mock_celery_task.delay.assert_called_once()
    
    def test_submission_with_custom_parameters(self, valid_payload, mock_celery_task):
        """Test submission with custom query parameters."""
        response = client.post(
            "/api/v1/frontal/crop/submit",
            json=valid_payload,
            params={
                'show_labels': False,
                'region_opacity': 0.8,
                'stroke_width': 2
            }
        )
        
        assert response.status_code == 200
        
        # Verify parameters were passed to task
        call_kwargs = mock_celery_task.delay.call_args[1]
        assert call_kwargs['show_labels'] is False
        assert call_kwargs['region_opacity'] == 0.8
        assert call_kwargs['stroke_width'] == 2
    
    def test_missing_image_field(self, valid_payload):
        """Test request with missing image field."""
        payload = valid_payload.copy()
        del payload['image']
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422  # Validation error
    
    def test_missing_landmarks_field(self, valid_payload):
        """Test request with missing landmarks field."""
        payload = valid_payload.copy()
        del payload['landmarks']
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
    
    def test_missing_segmentation_map(self, valid_payload):
        """Test request with missing segmentation_map field."""
        payload = valid_payload.copy()
        del payload['segmentation_map']
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
    
    def test_invalid_landmarks_count(self, valid_payload):
        """Test request with incorrect number of landmarks."""
        payload = valid_payload.copy()
        payload['landmarks'] = payload['landmarks'][:100]  # Only 100 landmarks
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
        assert '478' in response.text
    
    def test_invalid_landmark_format(self, valid_payload):
        """Test request with invalid landmark structure."""
        payload = valid_payload.copy()
        payload['landmarks'][0] = {"x": "invalid", "y": 200.0}  # String instead of float
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
    
    def test_invalid_segmentation_map_type(self, valid_payload):
        """Test request with segmentation_map as wrong type."""
        payload = valid_payload.copy()
        payload['segmentation_map'] = "not_a_dict"
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
    
    def test_invalid_segmentation_map_indices(self, valid_payload):
        """Test request with invalid landmark indices in segmentation_map."""
        payload = valid_payload.copy()
        payload['segmentation_map']['invalid_region'] = [500, 600]  # Invalid indices
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
        assert 'invalid landmark indices' in response.text.lower()
    
    def test_segmentation_map_with_non_list_values(self, valid_payload):
        """Test segmentation_map with non-list values."""
        payload = valid_payload.copy()
        payload['segmentation_map']['bad_region'] = "not_a_list"
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
    
    def test_segmentation_map_with_non_integer_indices(self, valid_payload):
        """Test segmentation_map with non-integer values in lists."""
        payload = valid_payload.copy()
        payload['segmentation_map']['bad_region'] = [10, 20, "30", 40]
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
    
    def test_invalid_image_base64(self, valid_payload, mock_celery_task):
        """Test request with invalid base64 image data."""
        payload = valid_payload.copy()
        payload['image'] = "not_valid_base64!!!"
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 400
        assert 'invalid image data' in response.text.lower()
    
    def test_region_opacity_out_of_range(self, valid_payload, mock_celery_task):
        """Test with region_opacity outside valid range."""
        # Too high
        response = client.post(
            "/api/v1/frontal/crop/submit",
            json=valid_payload,
            params={'region_opacity': 1.5}
        )
        assert response.status_code == 422
        
        # Too low
        response = client.post(
            "/api/v1/frontal/crop/submit",
            json=valid_payload,
            params={'region_opacity': -0.1}
        )
        assert response.status_code == 422
    
    def test_negative_stroke_width(self, valid_payload, mock_celery_task):
        """Test with negative stroke_width."""
        response = client.post(
            "/api/v1/frontal/crop/submit",
            json=valid_payload,
            params={'stroke_width': -1}
        )
        assert response.status_code == 422
    
    def test_custom_regions(self, valid_payload, mock_celery_task):
        """Test with custom region definitions."""
        payload = valid_payload.copy()
        payload['segmentation_map'] = {
            'custom_region_1': [10, 20, 30, 40, 50],
            'custom_region_2': [100, 110, 120, 130]
        }
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 200
        
        # Verify custom regions were passed to task
        call_kwargs = mock_celery_task.delay.call_args[1]
        assert 'segmentation_map' in call_kwargs
        assert 'custom_region_1' in call_kwargs['segmentation_map']
        assert 'custom_region_2' in call_kwargs['segmentation_map']
    
    def test_single_region(self, valid_payload, mock_celery_task):
        """Test with single region in segmentation_map."""
        payload = valid_payload.copy()
        payload['segmentation_map'] = {
            'nose_only': [55, 8, 285, 417, 412, 437]
        }
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 200
    
    def test_empty_segmentation_map(self, valid_payload):
        """Test with empty segmentation_map."""
        payload = valid_payload.copy()
        payload['segmentation_map'] = {}
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        # Should still succeed but won't produce any regions
        assert response.status_code == 200
    
    def test_negative_landmark_coordinates(self, valid_payload):
        """Test with negative landmark coordinates."""
        payload = valid_payload.copy()
        payload['landmarks'][0] = {"x": -10.0, "y": 20.0}
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 422
    
    def test_boundary_values(self, valid_payload, mock_celery_task):
        """Test boundary values for parameters."""
        # Min values
        response = client.post(
            "/api/v1/frontal/crop/submit",
            json=valid_payload,
            params={
                'region_opacity': 0.0,
                'stroke_width': 0
            }
        )
        assert response.status_code == 200
        
        # Max values
        response = client.post(
            "/api/v1/frontal/crop/submit",
            json=valid_payload,
            params={
                'region_opacity': 1.0,
                'stroke_width': 100
            }
        )
        assert response.status_code == 200
    
    def test_large_landmark_values(self, valid_payload, mock_celery_task):
        """Test with very large landmark coordinate values."""
        payload = valid_payload.copy()
        payload['landmarks'][0] = {"x": 10000.0, "y": 10000.0}
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        # Should succeed - coordinates can be large
        assert response.status_code == 200
    
    @patch('app.api.routes.decode_base64_image')
    def test_image_decode_failure(self, mock_decode, valid_payload):
        """Test handling of image decode failure."""
        mock_decode.side_effect = Exception("Decode failed")
        
        response = client.post("/api/v1/frontal/crop/submit", json=valid_payload)
        assert response.status_code == 400
        assert 'invalid image data' in response.text.lower()
    
    def test_concurrent_submissions(self, valid_payload, mock_celery_task):
        """Test multiple concurrent task submissions."""
        responses = []
        for i in range(5):
            mock_celery_task.delay.return_value.id = f'task-{i}'
            response = client.post("/api/v1/frontal/crop/submit", json=valid_payload)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Each should have unique task ID
        task_ids = [r.json()['task_id'] for r in responses]
        assert len(set(task_ids)) == 5
    
    def test_response_schema(self, valid_payload, mock_celery_task):
        """Test that response matches expected schema."""
        response = client.post("/api/v1/frontal/crop/submit", json=valid_payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check all required fields exist
        required_fields = [
            'task_id', 'status', 'message', 
            'submitted_at', 'estimated_completion_time'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Check field types
        assert isinstance(data['task_id'], str)
        assert isinstance(data['status'], str)
        assert isinstance(data['message'], str)
        assert isinstance(data['submitted_at'], str)
        assert isinstance(data['estimated_completion_time'], int)


class TestEdgeCases:
    """Test edge cases and unusual inputs."""
    
    def test_unicode_region_names(self, valid_payload, mock_celery_task):
        """Test with unicode characters in region names."""
        payload = valid_payload.copy()
        payload['segmentation_map'] = {
            'région_française': [10, 20, 30],
            '日本語': [40, 50, 60],
            'región_española': [70, 80, 90]
        }
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 200
    
    def test_very_long_region_name(self, valid_payload, mock_celery_task):
        """Test with very long region name."""
        payload = valid_payload.copy()
        long_name = 'region_' + 'x' * 1000
        payload['segmentation_map'] = {long_name: [10, 20, 30]}
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        assert response.status_code == 200
    
    def test_duplicate_indices_in_region(self, valid_payload, mock_celery_task):
        """Test with duplicate indices in a region."""
        payload = valid_payload.copy()
        payload['segmentation_map'] = {
            'test_region': [10, 20, 10, 30, 20, 10]  # Duplicates
        }
        
        response = client.post("/api/v1/frontal/crop/submit", json=payload)
        # Should still work - duplicates are harmless
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
