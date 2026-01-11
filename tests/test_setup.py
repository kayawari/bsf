"""
Test basic application setup and configuration.
"""
import pytest
import os
from pathlib import Path
from app import create_app, db

def test_app_creation():
    """Test that the Flask app can be created successfully."""
    app = create_app('testing')
    assert app is not None
    assert app.config['TESTING'] is True

def test_instance_path_configuration():
    """Test that instance path is configured correctly."""
    app = create_app('testing')
    expected_instance_path = Path(__file__).parent.parent / 'instance'
    assert Path(app.instance_path) == expected_instance_path

def test_database_uri_uses_instance_folder():
    """Test that database URI points to instance folder."""
    app = create_app('development')
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    assert 'instance/books.db' in db_uri

def test_health_endpoint():
    """Test the health check endpoint."""
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'Book Management Application' in data['message']

def test_main_route():
    """Test the main route renders correctly."""
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'Book Management' in response.data
        assert b'htmx' in response.data  # Check htmx is included

def test_config_loading():
    """Test that configuration is loaded correctly."""
    app = create_app('testing')
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
    assert app.config['JSON_AS_ASCII'] is False  # UTF-8 support

def test_instance_config_override():
    """Test that instance configuration can override default settings."""
    app = create_app('development')
    
    # Create a temporary instance config for testing
    instance_config_path = Path(app.instance_path) / 'test_override.py'
    instance_config_path.write_text('TEST_OVERRIDE = "instance_value"')
    
    try:
        app.config.from_pyfile('test_override.py')
        assert app.config.get('TEST_OVERRIDE') == 'instance_value'
    finally:
        # Clean up test file
        if instance_config_path.exists():
            instance_config_path.unlink()