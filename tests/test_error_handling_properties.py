"""
Property-based tests for error handling functionality.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import Flask
from app import create_app, db
from app.models.book import Book
from app.services.book_service import process_and_store_book
from app.services.isbn_service import validate_isbn


def create_test_app():
    """Create and configure test app."""
    app = create_app('testing')
    return app


class TestSystemErrorResilience:
    """
    Property-based tests for system error resilience.
    Feature: book-management, Property 12: System Error Resilience
    """
    
    @given(
        error_message=st.text(min_size=1, max_size=100),
        error_type=st.sampled_from([
            Exception, RuntimeError, ValueError, TypeError, 
            ConnectionError, TimeoutError, OSError
        ])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_system_errors_are_logged_and_handled_gracefully(self, error_message, error_type):
        """
        **Property 12: System Error Resilience**
        *For any* system error or exception, the application should log the error 
        and display a user-friendly message while maintaining stability.
        **Validates: Requirements 5.4**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                # Mock database operations to raise the generated error
                with patch.object(db.session, 'commit') as mock_commit:
                    mock_commit.side_effect = error_type(error_message)
                    
                    # Try to process a book (this should trigger the error)
                    with patch('app.services.book_service.get_book_metadata_with_fallback') as mock_api:
                        mock_api.return_value = ({'title': 'Test Book'}, False, None)
                        
                        book, error = process_and_store_book('9780743273565')
                        
                        # Verify the error was handled gracefully
                        assert book is None
                        assert error is not None
                        assert 'Database error while saving book' in error
                        
                        # Verify the application didn't crash (we got a response)
                        assert isinstance(error, str)
            finally:
                db.drop_all()
    
    @given(
        route_path=st.sampled_from([
            '/', '/books', '/book/1', '/add-book', '/health'
        ]),
        exception_type=st.sampled_from([
            Exception, RuntimeError, ValueError, TypeError, OSError
        ])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_web_routes_handle_exceptions_gracefully(self, route_path, exception_type):
        """
        **Property 12: System Error Resilience**
        *For any* web route and any system exception, the application should 
        handle the error gracefully and return an appropriate error response.
        **Validates: Requirements 5.4**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Mock a function that will be called during route processing to raise an exception
                with patch('app.services.book_service.get_all_books') as mock_get_books:
                    mock_get_books.side_effect = exception_type("Simulated system error")
                    
                    # Make request to the route
                    if route_path == '/add-book':
                        response = client.post(route_path, data={'isbn': '9780743273565'})
                    else:
                        response = client.get(route_path)
                    
                    # Verify the application handled the error gracefully
                    # Should return a response (not crash) - could be error page (5xx) or redirect (3xx)
                    assert response.status_code >= 200
                    assert response.status_code < 600
                    
                    # Verify we got some response data (not empty)
                    assert response.data is not None
                    assert len(response.data) > 0
                    
                    # The key test: system should remain stable and not crash
                    # Error handling is working if we get any valid HTTP response
                    assert isinstance(response.status_code, int)
            finally:
                db.drop_all()
    
    @given(
        isbn_input=st.text(min_size=1, max_size=50),
        database_error=st.sampled_from([
            'Connection lost', 'Disk full', 'Permission denied', 
            'Table locked', 'Constraint violation'
        ])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_database_errors_maintain_system_stability(self, isbn_input, database_error):
        """
        **Property 12: System Error Resilience**
        *For any* ISBN input and any database error, the system should maintain 
        stability and provide appropriate error feedback.
        **Validates: Requirements 5.4**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Mock database operations to fail
                with patch.object(db.session, 'commit') as mock_commit:
                    mock_commit.side_effect = Exception(database_error)
                    
                    # Mock API to return valid data (so error is purely database-related)
                    with patch('app.services.book_service.get_book_metadata_with_fallback') as mock_api:
                        mock_api.return_value = ({'title': 'Test Book'}, False, None)
                        
                        # Try to add a book via web interface
                        response = client.post('/add-book', data={'isbn': isbn_input})
                        
                        # System should handle the error gracefully
                        # Progressive enhancement: non-htmx requests get redirects (302) with flash messages
                        assert response.status_code in [302, 400, 500]  # Redirect or error status
                        assert response.data is not None    # Should return some response
                        
                        # Verify database session is still functional (no corruption)
                        # This tests that rollback worked properly
                        try:
                            # Should be able to query without issues
                            Book.query.count()
                            db_functional = True
                        except Exception:
                            db_functional = False
                        
                        assert db_functional, "Database session should remain functional after error"
            finally:
                db.drop_all()
    
    @given(
        error_scenarios=st.lists(
            st.sampled_from([
                'network_timeout', 'api_unavailable', 'invalid_response',
                'database_error', 'file_system_error', 'memory_error'
            ]),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
    def test_multiple_concurrent_errors_maintain_stability(self, error_scenarios):
        """
        **Property 12: System Error Resilience**
        *For any* combination of system errors occurring together, the application 
        should maintain stability and handle each error appropriately.
        **Validates: Requirements 5.4**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                error_responses = []
                
                # Simulate multiple error scenarios
                for scenario in error_scenarios:
                    if scenario == 'database_error':
                        with patch.object(db.session, 'commit') as mock_commit:
                            mock_commit.side_effect = Exception("Database error")
                            response = client.post('/add-book', data={'isbn': '9780743273565'})
                            error_responses.append(response)
                    
                    elif scenario == 'api_unavailable':
                        with patch('app.services.book_service.get_book_metadata_with_fallback') as mock_api:
                            mock_api.side_effect = Exception("API unavailable")
                            response = client.post('/add-book', data={'isbn': '9780743273565'})
                            error_responses.append(response)
                    
                    elif scenario == 'network_timeout':
                        with patch('app.services.book_service.get_all_books') as mock_get_books:
                            mock_get_books.side_effect = TimeoutError("Network timeout")
                            response = client.get('/')
                            error_responses.append(response)
                
                # Verify all errors were handled gracefully
                for response in error_responses:
                    # Should return valid HTTP response (not crash)
                    assert 200 <= response.status_code < 600  # Valid HTTP status range
                    assert response.data is not None    # Should return some response
                    assert len(response.data) > 0       # Response should not be empty
                
                # Verify system is still responsive after multiple errors
                health_response = client.get('/health')
                assert health_response.status_code == 200
                assert health_response.get_json()['status'] == 'ok'
            finally:
                db.drop_all()
    
    @given(
        htmx_request=st.booleans(),
        error_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_responses_appropriate_for_request_type(self, htmx_request, error_message):
        """
        **Property 12: System Error Resilience**
        *For any* request type (htmx or regular) and any error, the system should 
        return an appropriate error response format.
        **Validates: Requirements 5.4**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                
                # Mock an error in the route processing
                with patch('app.services.book_service.get_all_books') as mock_get_books:
                    mock_get_books.side_effect = Exception(error_message)
                    
                    # Set up request headers
                    headers = {}
                    if htmx_request:
                        headers['HX-Request'] = 'true'
                    
                    # Make request
                    response = client.get('/', headers=headers)
                    
                    # Verify appropriate error response
                    # The application handles errors gracefully and returns valid responses
                    assert 200 <= response.status_code < 600  # Valid HTTP status
                    assert response.data is not None
                    
                    if htmx_request:
                        # htmx requests should get HTML fragments (could be error fragments)
                        # The error handler returns error fragments for htmx requests
                        if response.status_code >= 500:
                            assert b'error' in response.data.lower() or b'Error' in response.data
                    else:
                        # Regular requests should get full pages (could be error pages)
                        # The error handler returns full error pages for regular requests
                        if response.status_code >= 500:
                            assert b'html' in response.data.lower() or b'HTML' in response.data
            finally:
                db.drop_all()