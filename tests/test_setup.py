"""
Test basic application setup and configuration.
"""
import pytest
from app import create_app, db

def test_app_creation():
    """Test that the Flask app can be created successfully."""
    app = create_app('testing')
    assert app is not None
    assert app.config['TESTING'] is True

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
        assert b'Book Management Application' in response.data
        assert b'htmx' in response.data  # Check htmx is included

def test_config_loading():
    """Test that configuration is loaded correctly."""
    app = create_app('testing')
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
    assert app.config['JSON_AS_ASCII'] is False  # UTF-8 support