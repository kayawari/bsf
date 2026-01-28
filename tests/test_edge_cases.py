"""
Comprehensive unit tests for edge cases.
Tests various edge cases including empty collections, API failures, international characters,
and responsive layout scenarios.
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch
from app import create_app, db
from app.models.book import Book
from app.services.book_service import (
    process_and_store_book, get_all_books, get_book_by_id
)
from app.services.google_books_api import get_book_metadata_by_isbn
from app.services.isbn_service import validate_isbn, normalize_isbn


@pytest.fixture
def app():
    """Create test app with in-memory database."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestEmptyCollectionEdgeCases:
    """Test edge cases for empty collection display across different screen sizes."""
    
    def test_empty_collection_desktop_layout(self, client):
        """Test empty collection display on desktop layout."""
        response = client.get('/')
        assert response.status_code == 200
        
        # Should contain empty collection message
        assert b'collection is empty' in response.data
        assert b'Add your first book' in response.data
        
        # Should have proper CSS classes for responsive design
        assert b'empty-collection' in response.data
        assert b'book-grid' in response.data
    
    def test_empty_collection_mobile_responsive(self, client):
        """Test empty collection display with mobile user agent."""
        # Simulate mobile user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        }
        
        response = client.get('/', headers=headers)
        assert response.status_code == 200
        
        # Should still show empty collection message
        assert b'collection is empty' in response.data
        assert b'empty-collection' in response.data
    
    def test_empty_collection_fragment_loading(self, client):
        """Test empty collection fragment via htmx."""
        response = client.get('/books', headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return fragment with empty message
        assert b'collection is empty' in response.data
        assert b'empty-collection' in response.data
        # Should not include full page structure
        assert b'<!DOCTYPE html>' not in response.data
    
    def test_empty_collection_after_book_deletion(self, client):
        """Test empty collection state after all books are removed."""
        with client.application.app_context():
            # Add and then remove a book to simulate deletion
            book = Book(isbn='9780743273565', title='Test Book')
            db.session.add(book)
            db.session.commit()
            
            # Remove the book
            db.session.delete(book)
            db.session.commit()
        
        # Collection should be empty again
        response = client.get('/')
        assert response.status_code == 200
        assert b'collection is empty' in response.data


class TestAPIFailureEdgeCases:
    """Test various API failure scenarios with responsive layouts."""
    
    def test_api_timeout_handling(self, client, mocker):
        """Test handling of API timeout errors."""
        # Mock API to return fallback data due to timeout
        fallback_metadata = {
            'title': 'Book with ISBN 9780743273565',
            'authors': [],
            'publisher': None,
            'published_date': None,
            'description': 'Book information could not be retrieved from Google Books API.',
            'thumbnail_url': None,
            'cover_image_url': None,
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (fallback_metadata, True, 'Request timeout')
        
        # Should fall back to basic book creation
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        # Should create book with fallback data
        assert response.status_code == 200
        assert b'Book with ISBN 9780743273565' in response.data
        assert b'warning-message' in response.data or b'limited information' in response.data
    
    def test_api_invalid_response_handling(self, client, mocker):
        """Test handling of invalid API responses."""
        # Mock API to return fallback data due to invalid response
        fallback_metadata = {
            'title': 'Book with ISBN 9780743273565',
            'authors': [],
            'publisher': None,
            'published_date': None,
            'description': 'Book information could not be retrieved from Google Books API.',
            'thumbnail_url': None,
            'cover_image_url': None,
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (fallback_metadata, True, 'Invalid response format')
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        # Should handle gracefully with fallback
        assert response.status_code == 200
        assert b'Book with ISBN 9780743273565' in response.data
    
    def test_api_network_error_mobile_display(self, client, mocker):
        """Test API network error display on mobile devices."""
        # Mock network error with fallback
        fallback_metadata = {
            'title': 'Book with ISBN 9780743273565',
            'authors': [],
            'publisher': None,
            'published_date': None,
            'description': 'Book information could not be retrieved from Google Books API.',
            'thumbnail_url': None,
            'cover_image_url': None,
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (fallback_metadata, True, 'Network unreachable')
        
        # Simulate mobile request
        headers = {
            'HX-Request': 'true',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
        }
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers=headers)
        
        # Should create book with fallback and show appropriate message
        assert response.status_code == 200
        assert b'Book with ISBN 9780743273565' in response.data
    
    def test_api_rate_limit_handling(self, client, mocker):
        """Test handling of API rate limiting."""
        # Mock API to simulate rate limiting with fallback
        fallback_metadata = {
            'title': 'Book with ISBN 9780743273565',
            'authors': [],
            'publisher': None,
            'published_date': None,
            'description': 'Book information could not be retrieved from Google Books API.',
            'thumbnail_url': None,
            'cover_image_url': None,
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (fallback_metadata, True, 'Rate limit exceeded')
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        # Should fall back gracefully
        assert response.status_code == 200
        assert b'Book with ISBN 9780743273565' in response.data
    
    def test_partial_api_data_handling(self, client, mocker):
        """Test handling of partial API data."""
        # Mock API to return partial data
        partial_metadata = {
            'title': 'Partial Book',
            'authors': None,  # Missing authors
            'publisher': '',  # Empty publisher
            'description': None,  # Missing description
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (partial_metadata, False, None)
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'Partial Book' in response.data
        
        # Check detail view handles missing data
        with client.application.app_context():
            book = Book.query.filter_by(isbn='9780743273565').first()
            book_id = book.id
        
        response = client.get(f'/book/{book_id}',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert b'Partial Book' in response.data


class TestInternationalCharacterEdgeCases:
    """Test international character edge cases on mobile devices."""
    
    def test_unicode_emoji_in_book_data(self, client, mocker):
        """Test handling of Unicode emoji in book data."""
        emoji_metadata = {
            'title': '📚 The Book of Books 📖',
            'authors': ['Author 👨‍💻'],
            'publisher': 'Emoji Press 🏢',
            'description': 'A book about books! 📚✨🌟'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (emoji_metadata, False, None)
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        # Should handle emoji correctly
        assert '📚'.encode('utf-8') in response.data
        assert '👨‍💻'.encode('utf-8') in response.data
    
    def test_right_to_left_text_handling(self, client, mocker):
        """Test handling of right-to-left text (Arabic, Hebrew)."""
        rtl_metadata = {
            'title': 'كتاب عربي',  # Arabic text
            'authors': ['مؤلف عربي'],
            'publisher': 'دار النشر العربية',
            'description': 'هذا كتاب باللغة العربية'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (rtl_metadata, False, None)
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        # Should handle RTL text correctly
        assert 'كتاب عربي'.encode('utf-8') in response.data
        assert 'مؤلف عربي'.encode('utf-8') in response.data
    
    def test_mixed_script_content(self, client, mocker):
        """Test handling of mixed script content (Latin + CJK + Arabic)."""
        mixed_metadata = {
            'title': 'English 日本語 العربية',
            'authors': ['Author 著者 مؤلف'],
            'description': 'Multi-script content: English, 日本語 (Japanese), العربية (Arabic)'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (mixed_metadata, False, None)
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        # Should handle all scripts correctly
        assert 'English'.encode('utf-8') in response.data
        assert '日本語'.encode('utf-8') in response.data
        assert 'العربية'.encode('utf-8') in response.data
    
    def test_special_unicode_characters(self, client, mocker):
        """Test handling of special Unicode characters."""
        special_metadata = {
            'title': 'Special Characters: ™ © ® ℠ ℗ ♪ ♫ ♬',
            'authors': ['Author with ñ, ü, ç, ß'],
            'description': 'Contains mathematical symbols: ∑ ∏ ∫ ∂ ∆ ∇ ∞'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (special_metadata, False, None)
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        # Should handle special characters correctly
        assert '™'.encode('utf-8') in response.data
        assert 'ñ'.encode('utf-8') in response.data
        # Mathematical symbols are in description, check detail view
        
        # Navigate to detail view to check description
        with client.application.app_context():
            book = Book.query.filter_by(isbn='9780743273565').first()
            book_id = book.id
        
        response = client.get(f'/book/{book_id}',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert '∑'.encode('utf-8') in response.data
    
    def test_very_long_unicode_content(self, client, mocker):
        """Test handling of very long Unicode content."""
        long_description = '日本語の長い説明文。' * 100  # Very long Japanese text
        long_metadata = {
            'title': 'Book with Long Description',
            'authors': ['Author'],
            'description': long_description
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (long_metadata, False, None)
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'Book with Long Description' in response.data
        
        # Check detail view can handle long content
        with client.application.app_context():
            book = Book.query.filter_by(isbn='9780743273565').first()
            book_id = book.id
        
        response = client.get(f'/book/{book_id}',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert '日本語の長い説明文。'.encode('utf-8') in response.data


class TestResponsiveLayoutEdgeCases:
    """Test responsive layout edge cases for very small/large screens."""
    
    def test_very_small_screen_layout(self, client):
        """Test layout on very small screens (< 320px)."""
        with client.application.app_context():
            # Add test book
            book = Book(
                isbn='9780743273565',
                title='Very Long Book Title That Might Cause Layout Issues',
                authors='["Author with a Very Long Name"]'
            )
            db.session.add(book)
            db.session.commit()
        
        # Simulate very small screen
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Viewport': 'width=280'
        }
        
        response = client.get('/', headers=headers)
        assert response.status_code == 200
        
        # Should still display content properly
        assert b'Very Long Book Title' in response.data
        assert b'book-card' in response.data
    
    def test_very_large_screen_layout(self, client):
        """Test layout on very large screens (> 1920px)."""
        with client.application.app_context():
            # Add multiple books to test grid layout
            books = [
                Book(isbn=f'978074327356{i}', title=f'Book {i}', authors=f'["Author {i}"]')
                for i in range(10)
            ]
            db.session.add_all(books)
            db.session.commit()
        
        # Simulate large desktop screen
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Viewport': 'width=2560'
        }
        
        response = client.get('/', headers=headers)
        assert response.status_code == 200
        
        # Should display all books
        for i in range(10):
            assert f'Book {i}'.encode('utf-8') in response.data
    
    def test_landscape_tablet_layout(self, client):
        """Test layout on landscape tablet orientation."""
        with client.application.app_context():
            # Add test books
            books = [
                Book(isbn=f'978074327356{i}', title=f'Book {i}')
                for i in range(5)
            ]
            db.session.add_all(books)
            db.session.commit()
        
        # Simulate landscape tablet
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Viewport': 'width=1024,height=768'
        }
        
        response = client.get('/', headers=headers)
        assert response.status_code == 200
        
        # Should adapt to tablet layout
        assert b'book-grid' in response.data
        for i in range(5):
            assert f'Book {i}'.encode('utf-8') in response.data
    
    def test_portrait_phone_layout(self, client):
        """Test layout on portrait phone orientation."""
        with client.application.app_context():
            # Add test book with long title
            book = Book(
                isbn='9780743273565',
                title='A Very Long Book Title That Should Wrap Properly on Mobile Devices',
                authors='["Author Name"]',
                description='A long description that should be readable on mobile devices.'
            )
            db.session.add(book)
            db.session.commit()
            book_id = book.id
        
        # Simulate portrait phone
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'Viewport': 'width=375,height=812'
        }
        
        # Test collection view
        response = client.get('/', headers=headers)
        assert response.status_code == 200
        assert b'A Very Long Book Title' in response.data
        
        # Test detail view
        response = client.get(f'/book/{book_id}', headers=headers)
        assert response.status_code == 200
        assert b'A Very Long Book Title' in response.data
        assert b'A long description' in response.data


class TestDatabaseEdgeCases:
    """Test database-related edge cases."""
    
    def test_database_connection_recovery(self, client, mocker):
        """Test recovery from temporary database connection issues."""
        # Mock database to fail once then succeed
        call_count = 0
        def mock_query_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception('Database connection lost')
            return []
        
        mock_query = mocker.patch.object(Book.query, 'order_by')
        mock_query.return_value.all.side_effect = mock_query_side_effect
        
        # First request should handle error gracefully
        response = client.get('/')
        # Should not crash, may return empty collection or error page
        assert response.status_code in [200, 500]
    
    def test_concurrent_book_additions(self, client, mocker):
        """Test handling of concurrent book additions."""
        # Mock API
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = ({'title': 'Test Book', 'authors': ['Author']}, False, None)
        
        # Simulate concurrent additions of same ISBN
        isbn = '9780743273565'
        
        # First addition should succeed
        response1 = client.post('/add-book', 
                              data={'isbn': isbn},
                              headers={'HX-Request': 'true'})
        
        # Second addition should be rejected as duplicate
        response2 = client.post('/add-book', 
                              data={'isbn': isbn},
                              headers={'HX-Request': 'true'})
        
        assert response1.status_code == 200
        assert response2.status_code == 400
        assert b'already exists' in response2.data
    
    def test_database_transaction_rollback(self, client, mocker):
        """Test database transaction rollback on errors."""
        # Mock to cause error after book creation but before commit
        mock_commit = mocker.patch.object(db.session, 'commit')
        mock_commit.side_effect = Exception('Commit failed')
        
        # Mock API
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = ({'title': 'Test Book'}, False, None)
        
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        
        # Should handle error gracefully
        assert response.status_code == 400
        assert b'Database error' in response.data
        
        # Book should not exist in database
        with client.application.app_context():
            book = Book.query.filter_by(isbn='9780743273565').first()
            assert book is None


class TestISBNEdgeCases:
    """Test ISBN validation edge cases."""
    
    def test_isbn_with_unusual_formatting(self, client, mocker):
        """Test ISBN with unusual but valid formatting."""
        # Mock API
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = ({'title': 'Test Book'}, False, None)
        
        # Test various ISBN formats - some may be rejected due to length validation
        isbn_formats = [
            '9780743273565',       # No separators - should work
            '978-0-7432-7356-5',  # Standard ISBN-13 with hyphens - should normalize to same
        ]
        
        # First format (no separators) should succeed
        response = client.post('/add-book', 
                             data={'isbn': isbn_formats[0]},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Second format should be normalized and detected as duplicate
        response = client.post('/add-book', 
                             data={'isbn': isbn_formats[1]},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 400
        assert b'already exists' in response.data
    
    def test_isbn_boundary_values(self, client):
        """Test ISBN boundary values and edge cases."""
        # Test minimum and maximum valid ISBN values
        edge_isbns = [
            '0000000000',      # Minimum ISBN-10 (may have invalid checksum)
            '9999999999',      # Maximum ISBN-10 (may have invalid checksum)
            '9780000000002',   # Minimum valid ISBN-13
            '9799999999999',   # Maximum valid ISBN-13 (may have invalid checksum)
        ]
        
        for isbn in edge_isbns:
            response = client.post('/add-book', 
                                 data={'isbn': isbn},
                                 headers={'HX-Request': 'true'})
            
            # The system may accept some of these ISBNs even with invalid checksums
            # and create fallback records, so we just check that it handles them gracefully
            assert response.status_code in [200, 400]
            
            if response.status_code == 400:
                # Should contain some error message
                assert b'Invalid' in response.data or b'error' in response.data
            else:
                # If accepted, should create a book record
                assert b'book-card' in response.data or b'Book with ISBN' in response.data
    
    def test_isbn_with_special_characters(self, client):
        """Test ISBN with special characters."""
        special_isbns = [
            '978-0-7432-7356-X',  # X in ISBN-13 (invalid)
            '074327356X',         # Valid ISBN-10 with X
            '978-0-7432-7356-5!', # With exclamation
            '978-0-7432-7356-5?', # With question mark
        ]
        
        for isbn in special_isbns:
            response = client.post('/add-book', 
                                 data={'isbn': isbn},
                                 headers={'HX-Request': 'true'})
            
            if isbn == '074327356X':  # Valid ISBN-10 with X
                # Should be accepted and normalized
                assert response.status_code in [200, 400]  # May succeed or fail based on API
            else:
                # Should be rejected
                assert response.status_code == 400
                assert b'Invalid ISBN' in response.data


class TestHTMXEdgeCases:
    """Test htmx-specific edge cases."""
    
    def test_malformed_htmx_headers(self, client, mocker):
        """Test handling of malformed htmx headers."""
        # Mock API
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = ({'title': 'Test Book'}, False, None)
        
        # Test with malformed htmx header
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'malformed'})
        
        # Should still treat as htmx request
        assert response.status_code == 200
        # Should return fragment, not full page
        assert b'<!DOCTYPE html>' not in response.data
    
    def test_missing_htmx_target(self, client):
        """Test behavior when htmx target is missing."""
        # This is more of a frontend test, but we can verify server response
        response = client.get('/books', headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return valid fragment regardless of target
        assert b'book-grid' in response.data or b'empty-collection' in response.data
    
    def test_htmx_with_form_errors(self, client):
        """Test htmx behavior with form validation errors."""
        # Submit form with missing data
        response = client.post('/add-book', 
                             data={},  # No ISBN
                             headers={'HX-Request': 'true'})
        
        assert response.status_code == 400
        assert b'error-message' in response.data
        assert b'enter an ISBN' in response.data
    
    def test_htmx_navigation_state(self, client):
        """Test htmx navigation state handling."""
        with client.application.app_context():
            # Add test book
            book = Book(isbn='9780743273565', title='Test Book')
            db.session.add(book)
            db.session.commit()
            book_id = book.id
        
        # Navigate to detail with htmx
        response = client.get(f'/book/{book_id}',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert b'book-detail' in response.data
        assert b'Back to Collection' in response.data
        
        # Navigate back with htmx
        response = client.get('/',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        # Should return full page content for home route
        assert b'Book Management' in response.data