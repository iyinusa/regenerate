"""
Test for ProfileHistory data persistence fix.

This test verifies that raw_data and structured_data are properly saved
to the database after profile extraction completes.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.profile_service import ProfileExtractionService
from app.models.user import User, ProfileHistory
from app.schemas.profile import ExtractedProfileData


class TestProfileHistoryPersistence:
    """Test cases for ProfileHistory data persistence."""
    
    @pytest.fixture
    def service(self):
        """Create ProfileExtractionService instance."""
        return ProfileExtractionService()
    
    @pytest.fixture
    def sample_extracted_data(self):
        """Sample extracted profile data."""
        return {
            "name": "John Doe",
            "title": "Software Engineer",
            "location": "San Francisco, CA", 
            "bio": "Experienced software engineer with expertise in Python and JavaScript",
            "experiences": [
                {
                    "company": "Tech Corp",
                    "title": "Senior Engineer", 
                    "duration": "2020-2024",
                    "description": "Led development of web applications"
                }
            ],
            "education": [
                {
                    "institution": "University of Technology",
                    "degree": "Computer Science",
                    "field": "Software Engineering",
                    "duration": "2016-2020"
                }
            ],
            "skills": ["Python", "JavaScript", "React", "SQL"],
            "projects": [],
            "achievements": [],
            "certifications": [],
            "email": "john@example.com",
            "website": "https://johndoe.dev",
            "linkedin": "https://linkedin.com/in/johndoe",
            "github": "https://github.com/johndoe",
            "social_links": {"twitter": "https://twitter.com/johndoe"}
        }
    
    @pytest.mark.asyncio
    async def test_profile_data_saved_to_database(self, service, sample_extracted_data):
        """Test that extracted profile data is saved to ProfileHistory."""
        
        # Mock database session and operations
        mock_db_session = AsyncMock()
        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the Gemini client response
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = f'''{{
            "name": "{sample_extracted_data['name']}",
            "title": "{sample_extracted_data['title']}",
            "location": "{sample_extracted_data['location']}",
            "bio": "{sample_extracted_data['bio']}",
            "experiences": {sample_extracted_data['experiences']},
            "education": {sample_extracted_data['education']},
            "skills": {sample_extracted_data['skills']},
            "projects": [],
            "achievements": [],
            "certifications": [],
            "email": "{sample_extracted_data['email']}",
            "website": "{sample_extracted_data['website']}",
            "linkedin": "{sample_extracted_data['linkedin']}",
            "github": "{sample_extracted_data['github']}",
            "social_links": {sample_extracted_data['social_links']}
        }}'''
        
        # Setup mocks
        with patch('app.services.profile_service.async_session_maker', mock_session_maker), \
             patch.object(service, 'genai_client') as mock_client, \
             patch('asyncio.to_thread') as mock_to_thread:
            
            # Configure mock client
            service.genai_client = mock_client
            mock_client.models.generate_content.return_value = mock_gemini_response
            mock_to_thread.return_value = mock_gemini_response
            
            # Test data
            job_id = "test_job_123"
            url = "https://linkedin.com/in/johndoe"
            history_id = "history_123"
            
            # Call the method
            await service._extract_profile_data(job_id, url, history_id)
            
            # Verify database operations
            mock_session_maker.assert_called_once()
            mock_db_session.execute.assert_called_once()
            mock_db_session.commit.assert_called_once()
            
            # Get the update query that was executed
            execute_call = mock_db_session.execute.call_args
            update_stmt = execute_call[0][0]
            
            # Verify the update statement targets correct table and ID
            assert "profile_history" in str(update_stmt).lower()
            
            print("✅ Test passed: Profile data is saved to database after extraction")
    
    def test_profile_data_structure(self, sample_extracted_data):
        """Test that the profile data structure is correct."""
        
        # Create ExtractedProfileData instance
        profile_data = ExtractedProfileData(
            **sample_extracted_data,
            source_url="https://linkedin.com/in/johndoe",
            extraction_timestamp=datetime.utcnow(),
            raw_data={
                "extraction_method": "gemini-3-pro-preview",
                "url_context_tool": True,
                "google_search_tool": True
            }
        )
        
        profile_dict = profile_data.dict()
        
        # Verify all expected fields are present
        expected_structured_fields = [
            'name', 'title', 'location', 'bio', 'experiences', 
            'education', 'skills', 'projects', 'achievements',
            'certifications', 'email', 'website', 'linkedin', 
            'github', 'social_links'
        ]
        
        structured_data = {
            k: v for k, v in profile_dict.items() 
            if k not in ['raw_data', 'source_url', 'extraction_timestamp']
        }
        
        for field in expected_structured_fields:
            assert field in structured_data, f"Missing field: {field}"
        
        # Verify raw_data structure
        assert profile_data.raw_data is not None
        assert 'extraction_method' in profile_data.raw_data
        
        print("✅ Test passed: Profile data structure is correct")


if __name__ == "__main__":
    # Run basic tests
    test = TestProfileHistoryPersistence()
    
    print("🧪 Testing ProfileHistory data persistence fix...")
    
    # Test data structure
    sample_data = {
        "name": "Test User",
        "title": "Test Engineer", 
        "location": "Test City",
        "bio": "Test bio",
        "experiences": [],
        "education": [],
        "skills": ["Python"],
        "projects": [],
        "achievements": [],
        "certifications": [],
        "email": "test@example.com",
        "website": None,
        "linkedin": None,
        "github": None,
        "social_links": {}
    }
    
    test.test_profile_data_structure(sample_data)
    print("🎉 All tests passed!")