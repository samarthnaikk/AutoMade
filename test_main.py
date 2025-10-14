#!/usr/bin/env python3
"""
Test script for the updated main.py with Pydantic models.
"""
import json
import tempfile
from main import AppBriefRequest, AppBuilder

def create_sample_request():
    """Create a sample request for testing."""
    return {
        "email": "student@example.com",
        "secret": "test-secret-123",
        "task": "captcha-solver-test",
        "round": 1,
        "nonce": "test-nonce-abc123",
        "brief": "Create a captcha solver that handles ?url=https://example.com/image.png. Default to attached sample.",
        "checks": [
            "Repo has MIT license",
            "README.md is professional", 
            "Page displays captcha URL passed at ?url=...",
            "Page displays solved captcha text within 15 seconds"
        ],
        "evaluation_url": "https://example.com/notify",
        "attachments": [
            {
                "name": "sample.png",
                "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
            }
        ]
    }

def test_pydantic_validation():
    """Test Pydantic model validation."""
    print("Testing Pydantic model validation...")
    
    # Test valid request
    sample_data = create_sample_request()
    try:
        request = AppBriefRequest(**sample_data)
        print("✅ Valid request parsed successfully")
        print(f"   Task: {request.task}")
        print(f"   Email: {request.email}")
        print(f"   Checks: {len(request.checks)} items")
        print(f"   Attachments: {len(request.attachments)} files")
    except Exception as e:
        print(f"❌ Failed to parse valid request: {e}")
    
    # Test invalid request (missing required field)
    invalid_data = sample_data.copy()
    del invalid_data["email"]
    try:
        request = AppBriefRequest(**invalid_data)
        print("❌ Invalid request should have failed validation")
    except Exception as e:
        print("✅ Invalid request correctly rejected")

def test_app_builder():
    """Test the AppBuilder functionality."""
    print("\nTesting AppBuilder...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        builder = AppBuilder(work_dir=temp_dir)
        sample_data = create_sample_request()
        request = AppBriefRequest(**sample_data)
        
        # Test app generation
        result = builder.generate_app_structure(request)
        
        if result.success:
            print("✅ App generation successful")
            print(f"   Task ID: {result.task_id}")
            print(f"   Generated files: {len(result.generated_files)}")
            for file in result.generated_files:
                print(f"     - {file}")
        else:
            print(f"❌ App generation failed: {result.error_message}")

def test_attachment_processing():
    """Test attachment processing."""
    print("\nTesting attachment processing...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        builder = AppBuilder(work_dir=temp_dir)
        sample_data = create_sample_request()
        request = AppBriefRequest(**sample_data)
        
        # Test saving attachments
        task_dir = builder.work_dir / request.task
        task_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = builder.process_attachments(request, task_dir)
        print(f"✅ Saved {len(saved_files)} attachments")
        for file_path in saved_files:
            print(f"   - {file_path}")

if __name__ == "__main__":
    print("Testing updated main.py with Pydantic models")
    print("=" * 50)
    
    test_pydantic_validation()
    test_app_builder()
    test_attachment_processing()
    
    print("\n" + "=" * 50)
    print("Test completed!")