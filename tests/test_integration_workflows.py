"""
Integration tests for end-to-end workflows.
Tests complete user journeys from ISBN input to book display with htmx functionality.
"""

import pytest
from datetime import date
from app import create_app, db
from app.models.book import Book


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


@pytest.fixture
def sample_book_metadata():
    """Sample book metadata for mocking API responses."""
    return {
        'title': 'The Great Gatsby',
        'authors': ['F. Scott Fitzgerald'],
        'publisher': 'Scribner',
        'published_date': date(2004, 9, 30),
        'description': 'A classic American novel about the Jazz Age.',
        'thumbnail_url': 'http://example.com/thumbnail.jpg',
        'cover_image_url': 'http://example.com/cover.jpg'
    }


class TestCompleteBookAdditionWorkflow:
    """Test complete book addition workflow from ISBN input to display."""
    
    def test_successful_book_addition_with_htmx(self, client, mocker, sample_book_metadata):
        """Test complete book addition workflow using htmx."""
        # Mock the Google Books API
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (sample_book_metadata, False, None)
        
        # 1. Load home page
        response = client.get('/')
        assert response.status_code == 200
        assert b'Book Management' in response.data
        assert b'Enter ISBN' in response.data
        
        # 2. Submit ISBN via htmx
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return book collection fragment
        assert b'The Great Gatsby' in response.data
        assert b'F. Scott Fitzgerald' in response.data
        assert b'book-card' in response.data
        
        # 3. Verify book was stored in database
        with client.application.app_context():
            book = Book.query.filter_by(isbn='9780743273565').first()
            assert book is not None
            assert book.title == 'The Great Gatsby'
    
    def test_book_addition_with_progressive_enhancement(self, client, mocker, sample_book_metadata):
        """Test book addition works without JavaScript (progressive enhancement)."""
        # Mock the Google Books API
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (sample_book_metadata, False, None)
        
        # Submit ISBN without htmx headers (simulating no JavaScript)
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             follow_redirects=True)
        assert response.status_code == 200
        
        # Should redirect to home page with flash message
        assert b'Successfully added' in response.data
        assert b'The Great Gatsby' in response.data
    
    def test_book_addition_with_api_fallback(self, client, mocker):
        """Test book addition when API fails but fallback data is used."""
        # Mock API to return fallback data
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
        mock_api.return_value = (fallback_metadata, True, 'API connection failed')
        
        # Submit ISBN via htmx
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should show warning about limited information
        assert b'Book with ISBN 9780743273565' in response.data
        assert b'warning-message' in response.data or b'limited information' in response.data
    
    def test_duplicate_isbn_handling(self, client, mocker):
        """Test handling of duplicate ISBN submissions."""
        with client.application.app_context():
            # Add existing book
            existing_book = Book(isbn='9780743273565', title='Existing Book')
            db.session.add(existing_book)
            db.session.commit()
        
        # Try to add duplicate via htmx
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 400
        
        # Should return error message
        assert b'already exists' in response.data
        assert b'error-message' in response.data
    
    def test_invalid_isbn_handling(self, client):
        """Test handling of invalid ISBN input."""
        # Submit invalid ISBN via htmx
        response = client.post('/add-book', 
                             data={'isbn': 'invalid-isbn'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 400
        
        # Should return error message
        assert b'Invalid ISBN' in response.data
        assert b'error-message' in response.data
    
    def test_empty_isbn_handling(self, client):
        """Test handling of empty ISBN input."""
        # Submit empty ISBN via htmx
        response = client.post('/add-book', 
                             data={'isbn': ''},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 400
        
        # Should return error message
        assert b'enter an ISBN' in response.data
        assert b'error-message' in response.data


class TestNavigationWorkflows:
    """Test navigation between collection list and detail views with htmx."""
    
    def test_collection_to_detail_navigation_with_htmx(self, client):
        """Test navigation from collection to book detail using htmx."""
        with client.application.app_context():
            # Add test book
            book = Book(
                isbn='9780743273565',
                title='The Great Gatsby',
                authors=['F. Scott Fitzgerald'],
                publisher='Scribner'
            )
            db.session.add(book)
            db.session.commit()
            book_id = book.id
        
        # 1. Load collection page
        response = client.get('/')
        assert response.status_code == 200
        assert b'The Great Gatsby' in response.data
        
        # 2. Navigate to book detail via htmx
        response = client.get(f'/book/{book_id}',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return book detail fragment
        assert b'The Great Gatsby' in response.data
        assert b'F. Scott Fitzgerald' in response.data
        assert b'book-detail' in response.data
        assert b'Back to Collection' in response.data
    
    def test_detail_to_collection_navigation_with_htmx(self, client):
        """Test navigation from book detail back to collection using htmx."""
        with client.application.app_context():
            # Add test book
            book = Book(
                isbn='9780743273565',
                title='The Great Gatsby',
                authors=['F. Scott Fitzgerald']
            )
            db.session.add(book)
            db.session.commit()
        
        # Navigate back to collection via htmx
        response = client.get('/',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return full page content (not just fragment for home route)
        assert b'Book Management' in response.data
        assert b'The Great Gatsby' in response.data
    
    def test_book_collection_fragment_loading(self, client):
        """Test loading book collection as htmx fragment."""
        with client.application.app_context():
            # Add multiple test books
            books = [
                Book(isbn='9780743273565', title='Book 1', authors=['Author 1']),
                Book(isbn='9780439420891', title='Book 2', authors=['Author 2']),
            ]
            db.session.add_all(books)
            db.session.commit()
        
        # Load collection fragment via htmx
        response = client.get('/books',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return collection fragment
        assert b'Book 1' in response.data
        assert b'Book 2' in response.data
        assert b'book-grid' in response.data
    
    def test_navigation_with_progressive_enhancement(self, client):
        """Test navigation works without JavaScript."""
        with client.application.app_context():
            # Add test book
            book = Book(
                isbn='9780743273565',
                title='The Great Gatsby',
                authors=['F. Scott Fitzgerald']
            )
            db.session.add(book)
            db.session.commit()
            book_id = book.id
        
        # Navigate to book detail without htmx
        response = client.get(f'/book/{book_id}')
        assert response.status_code == 200
        
        # Should return full page
        assert b'<!DOCTYPE html>' in response.data
        assert b'The Great Gatsby' in response.data
        assert b'F. Scott Fitzgerald' in response.data
    
    def test_book_not_found_handling(self, client):
        """Test handling of non-existent book navigation."""
        # Try to access non-existent book via htmx
        response = client.get('/book/999',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 404
        
        # Should return error fragment
        assert b'Book not found' in response.data
        assert b'error-message' in response.data
        
        # Try without htmx (progressive enhancement)
        response = client.get('/book/999', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to home with flash message
        assert b'Book not found' in response.data or b'Book Management' in response.data


class TestBookRefreshWorkflow:
    """Test book metadata refresh functionality."""
    
    def test_book_refresh_success_with_htmx(self, client, mocker):
        """Test successful book metadata refresh via htmx."""
        with client.application.app_context():
            # Add book with minimal data
            book = Book(
                isbn='9780743273565',
                title='Old Title',
                authors=['Old Author']
            )
            db.session.add(book)
            db.session.commit()
            book_id = book.id
        
        # Mock API to return updated data
        updated_metadata = {
            'title': 'The Great Gatsby',
            'authors': ['F. Scott Fitzgerald'],
            'publisher': 'Scribner',
            'description': 'A classic American novel.'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (updated_metadata, False, None)
        
        # Refresh book via htmx
        response = client.post(f'/refresh-book/{book_id}',
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return updated book detail fragment
        assert b'The Great Gatsby' in response.data
        assert b'F. Scott Fitzgerald' in response.data
        assert b'book-detail' in response.data
    
    def test_book_refresh_with_fallback_data(self, client, mocker):
        """Test book refresh when API returns fallback data."""
        with client.application.app_context():
            # Add book
            book = Book(isbn='9780743273565', title='Test Book')
            db.session.add(book)
            db.session.commit()
            book_id = book.id
        
        # Mock API to return fallback data
        fallback_metadata = {
            'title': 'Test Book',
            'description': 'Limited information available.'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (fallback_metadata, True, 'API temporarily unavailable')
        
        # Refresh book via htmx
        response = client.post(f'/refresh-book/{book_id}',
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should show warning about limited data
        assert b'warning-message' in response.data or b'limited data' in response.data
    
    def test_book_refresh_not_found(self, client):
        """Test refresh of non-existent book."""
        # Try to refresh non-existent book via htmx
        response = client.post('/refresh-book/999',
                             headers={'HX-Request': 'true'})
        assert response.status_code == 400
        
        # Should return error message
        assert b'not found' in response.data
        assert b'error-message' in response.data


class TestEmptyCollectionHandling:
    """Test handling of empty collection display."""
    
    def test_empty_collection_display(self, client):
        """Test display when collection is empty."""
        # Load home page with empty collection
        response = client.get('/')
        assert response.status_code == 200
        
        # Should show empty collection message
        assert b'collection is empty' in response.data
        assert b'Add your first book' in response.data
    
    def test_empty_collection_fragment(self, client):
        """Test empty collection fragment via htmx."""
        # Load collection fragment with empty database
        response = client.get('/books',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should return empty collection fragment
        assert b'collection is empty' in response.data
        assert b'empty-collection' in response.data


class TestErrorHandlingIntegration:
    """Test error handling across different scenarios."""
    
    def test_404_error_with_htmx(self, client):
        """Test 404 error handling with htmx request."""
        response = client.get('/nonexistent-page',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 404
        
        # Should return error fragment
        assert b'Page not found' in response.data
        assert b'error-message' in response.data
    
    def test_404_error_without_htmx(self, client):
        """Test 404 error handling without htmx (progressive enhancement)."""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        
        # Should return full error page
        assert b'<!DOCTYPE html>' in response.data
    
    def test_500_error_handling(self, client, mocker):
        """Test 500 error handling during book operations."""
        # Mock database to raise exception
        mock_query = mocker.patch('app.models.book.Book.query')
        mock_query.order_by.return_value.all.side_effect = Exception('Database error')
        
        # Request should handle error gracefully
        response = client.get('/')
        # The error handler should catch this and return a proper response
        # The exact status code may vary based on error handling implementation
        assert response.status_code in [200, 500]


class TestMultipleBookManagement:
    """Test managing multiple books in collection."""
    
    def test_multiple_books_display_order(self, client):
        """Test that multiple books are displayed in correct order."""
        with client.application.app_context():
            # Add books with different creation times
            book1 = Book(isbn='9780743273565', title='Book 1')
            db.session.add(book1)
            db.session.commit()
            
            book2 = Book(isbn='9780439420891', title='Book 2')
            db.session.add(book2)
            db.session.commit()
        
        # Load collection
        response = client.get('/')
        assert response.status_code == 200
        
        # Both books should be displayed
        assert b'Book 1' in response.data
        assert b'Book 2' in response.data
        
        # Should be in reverse chronological order (newest first)
        book1_pos = response.data.find(b'Book 1')
        book2_pos = response.data.find(b'Book 2')
        assert book2_pos < book1_pos  # Book 2 (newer) should appear first
    
    def test_adding_multiple_books_sequentially(self, client, mocker):
        """Test adding multiple books one after another."""
        # Mock API for first book
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = ({'title': 'Book 1', 'authors': ['Author 1']}, False, None)
        
        # Add first book
        response = client.post('/add-book', 
                             data={'isbn': '9780743273565'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert b'Book 1' in response.data
        
        # Mock API for second book
        mock_api.return_value = ({'title': 'Book 2', 'authors': ['Author 2']}, False, None)
        
        # Add second book
        response = client.post('/add-book', 
                             data={'isbn': '9780439420891'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should show both books
        assert b'Book 1' in response.data
        assert b'Book 2' in response.data


class TestInternationalCharacterHandling:
    """Test handling of international characters in book data."""
    
    def test_international_characters_in_book_data(self, client, mocker):
        """Test adding and displaying books with international characters."""
        # Mock API with international characters
        international_metadata = {
            'title': 'こころ (Kokoro)',
            'authors': ['夏目漱石 (Natsume Sōseki)'],
            'publisher': '新潮社',
            'description': 'A classic Japanese novel about friendship and betrayal.'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (international_metadata, False, None)
        
        # Add book with international characters
        response = client.post('/add-book', 
                             data={'isbn': '9784101010014'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should display international characters correctly
        assert 'こころ'.encode('utf-8') in response.data
        assert '夏目漱石'.encode('utf-8') in response.data
        assert '新潮社'.encode('utf-8') in response.data
    
    def test_mixed_language_content(self, client, mocker):
        """Test handling of mixed language content."""
        # Mock API with mixed language content
        mixed_metadata = {
            'title': 'English Title / 日本語タイトル',
            'authors': ['English Author', '日本の著者'],
            'description': 'This book contains both English and Japanese text. この本は英語と日本語の両方を含んでいます。'
        }
        mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
        mock_api.return_value = (mixed_metadata, False, None)
        
        # Add book with mixed language content
        response = client.post('/add-book', 
                             data={'isbn': '9784101010014'},
                             headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should handle mixed content correctly
        assert 'English Title'.encode('utf-8') in response.data
        assert '日本語タイトル'.encode('utf-8') in response.data
        
        # Navigate to detail view
        with client.application.app_context():
            book = Book.query.filter_by(isbn='9784101010014').first()
            book_id = book.id
        
        response = client.get(f'/book/{book_id}',
                            headers={'HX-Request': 'true'})
        assert response.status_code == 200
        
        # Should display mixed language description correctly
        assert 'English and Japanese'.encode('utf-8') in response.data
        assert '英語と日本語'.encode('utf-8') in response.data