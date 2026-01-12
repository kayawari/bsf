"""
Tests for book service functionality.
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch
from app import create_app, db
from app.models.book import Book
from app.services.book_service import (
    process_and_store_book, create_book_from_metadata, get_all_books,
    get_book_by_id, get_book_by_isbn, update_book_metadata
)


@pytest.fixture
def app():
    """Create test app."""
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
    """Sample book metadata for testing."""
    return {
        'title': 'The Great Gatsby',
        'authors': ['F. Scott Fitzgerald'],
        'publisher': 'Scribner',
        'published_date': date(2004, 9, 30),
        'description': 'A classic American novel about the Jazz Age.',
        'thumbnail_url': 'http://example.com/thumbnail.jpg',
        'cover_image_url': 'http://example.com/cover.jpg'
    }


@pytest.fixture
def incomplete_book_metadata():
    """Incomplete book metadata for testing."""
    return {
        'title': None,
        'authors': [],
        'publisher': None,
        'published_date': None,
        'description': None,
        'thumbnail_url': None,
        'cover_image_url': None
    }


class TestProcessAndStoreBook:
    """Test the main process_and_store_book function."""
    
    def test_process_and_store_book_success(self, app, mocker, sample_book_metadata):
        """Test successful book processing and storage."""
        with app.app_context():
            # Mock the Google Books API call
            mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
            mock_api.return_value = (sample_book_metadata, False, None)
            
            # Process and store book
            book, error = process_and_store_book('9780743273565')
            
            # Verify success
            assert error is None
            assert book is not None
            assert book.isbn == '9780743273565'
            assert book.title == 'The Great Gatsby'
            assert book.authors_list == ['F. Scott Fitzgerald']
            
            # Verify book was saved to database
            saved_book = Book.query.filter_by(isbn='9780743273565').first()
            assert saved_book is not None
            assert saved_book.title == 'The Great Gatsby'
    
    def test_process_and_store_book_empty_isbn(self, app):
        """Test processing with empty ISBN."""
        with app.app_context():
            book, error = process_and_store_book('')
            assert book is None
            assert 'cannot be empty' in error
    
    def test_process_and_store_book_invalid_isbn(self, app):
        """Test processing with invalid ISBN."""
        with app.app_context():
            book, error = process_and_store_book('invalid-isbn')
            assert book is None
            assert 'Invalid ISBN' in error
    
    def test_process_and_store_book_duplicate_isbn(self, app, mocker):
        """Test processing with duplicate ISBN."""
        with app.app_context():
            # Add existing book
            existing_book = Book(isbn='9780743273565', title='Existing Book')
            db.session.add(existing_book)
            db.session.commit()
            
            # Try to add duplicate
            book, error = process_and_store_book('9780743273565')
            assert book is None
            assert 'already exists' in error
    
    def test_process_and_store_book_api_error(self, app, mocker):
        """Test processing when API returns error."""
        with app.app_context():
            # Mock API to return fallback data with error
            fallback_metadata = {
                'title': 'Book with ISBN 9780743273565',
                'authors': [],
                'publisher': None,
                'published_date': None,
                'description': 'Book information could not be retrieved from Google Books API. You can edit this information later.',
                'thumbnail_url': None,
                'cover_image_url': None,
            }
            mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
            mock_api.return_value = (fallback_metadata, True, 'API connection failed')
            
            book, error = process_and_store_book('9780743273565')
            # With fallback, book should be created but with warning
            assert book is not None
            assert error is None  # No error, just fallback data used
    
    def test_process_and_store_book_storage_error(self, app, mocker):
        """Test processing when storage fails."""
        with app.app_context():
            # Mock API to return valid data
            mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
            mock_api.return_value = ({'title': 'Test Book'}, False, None)
            
            # Mock database commit to raise exception
            mock_commit = mocker.patch.object(db.session, 'commit')
            mock_commit.side_effect = Exception('Database error')
            
            book, error = process_and_store_book('9780743273565')
            assert book is None
            assert 'Database error while saving book' in error


class TestCreateBookFromMetadata:
    """Test book creation from metadata."""
    
    def test_create_book_from_metadata_success(self, app, sample_book_metadata):
        """Test successful book creation from complete metadata."""
        with app.app_context():
            book, error = create_book_from_metadata('9780743273565', sample_book_metadata)
            
            assert error is None
            assert book is not None
            assert book.isbn == '9780743273565'
            assert book.title == 'The Great Gatsby'
            assert book.authors_list == ['F. Scott Fitzgerald']
            assert book.publisher == 'Scribner'
            assert book.published_date == date(2004, 9, 30)
            assert book.description == 'A classic American novel about the Jazz Age.'
            assert book.thumbnail_url == 'http://example.com/thumbnail.jpg'
            assert book.cover_image_url == 'http://example.com/cover.jpg'
    
    def test_create_book_from_metadata_incomplete_data(self, app, incomplete_book_metadata):
        """Test book creation with incomplete metadata."""
        with app.app_context():
            book, error = create_book_from_metadata('9780743273565', incomplete_book_metadata)
            
            assert error is None
            assert book is not None
            assert book.isbn == '9780743273565'
            assert book.title == 'Unknown Title (ISBN: 9780743273565)'  # Placeholder title
            assert book.authors_list == []
            assert book.publisher is None
            assert book.published_date is None
    
    def test_create_book_from_metadata_empty_isbn(self, app, sample_book_metadata):
        """Test book creation with empty ISBN."""
        with app.app_context():
            book, error = create_book_from_metadata('', sample_book_metadata)
            assert book is None
            assert 'cannot be empty' in error
    
    def test_create_book_from_metadata_empty_metadata(self, app):
        """Test book creation with empty metadata."""
        with app.app_context():
            book, error = create_book_from_metadata('9780743273565', None)
            assert book is None
            assert 'cannot be empty' in error
    
    def test_create_book_from_metadata_invalid_date_type(self, app):
        """Test book creation with invalid date type."""
        with app.app_context():
            metadata = {
                'title': 'Test Book',
                'authors': ['Test Author'],
                'published_date': 'invalid-date-string'  # Invalid type
            }
            
            book, error = create_book_from_metadata('9780743273565', metadata)
            
            assert error is None
            assert book is not None
            assert book.published_date is None  # Should be set to None for invalid type
    
    def test_create_book_from_metadata_database_error(self, app, mocker, sample_book_metadata):
        """Test book creation when database commit fails."""
        with app.app_context():
            # Mock database commit to raise exception
            mock_commit = mocker.patch.object(db.session, 'commit')
            mock_commit.side_effect = Exception('Database connection lost')
            
            book, error = create_book_from_metadata('9780743273565', sample_book_metadata)
            
            assert book is None
            assert 'Database error while saving book' in error


class TestBookRetrieval:
    """Test book retrieval functions."""
    
    def test_get_all_books_empty_database(self, app):
        """Test retrieving books from empty database."""
        with app.app_context():
            books = get_all_books()
            assert books == []
    
    def test_get_all_books_with_data(self, app):
        """Test retrieving books with data in database."""
        with app.app_context():
            # Add test books
            book1 = Book(isbn='9780743273565', title='Book 1')
            book2 = Book(isbn='9780439420891', title='Book 2')
            db.session.add_all([book1, book2])
            db.session.commit()
            
            books = get_all_books()
            assert len(books) == 2
            # Should be ordered by created_at desc (newest first)
            assert books[0].title == 'Book 2'
            assert books[1].title == 'Book 1'
    
    def test_get_all_books_database_error(self, app, mocker):
        """Test get_all_books when database query fails."""
        with app.app_context():
            # Mock query to raise exception
            mock_query = mocker.patch.object(Book, 'query')
            mock_query.order_by.return_value.all.side_effect = Exception('Database error')
            
            books = get_all_books()
            assert books == []
    
    def test_get_book_by_id_success(self, app):
        """Test retrieving book by ID successfully."""
        with app.app_context():
            book = Book(isbn='9780743273565', title='Test Book')
            db.session.add(book)
            db.session.commit()
            
            retrieved_book = get_book_by_id(book.id)
            assert retrieved_book is not None
            assert retrieved_book.title == 'Test Book'
    
    def test_get_book_by_id_not_found(self, app):
        """Test retrieving book by non-existent ID."""
        with app.app_context():
            book = get_book_by_id(999)
            assert book is None
    
    def test_get_book_by_id_database_error(self, app, mocker):
        """Test get_book_by_id when database query fails."""
        with app.app_context():
            # Mock query to raise exception
            mock_query = mocker.patch.object(Book.query, 'get')
            mock_query.side_effect = Exception('Database error')
            
            book = get_book_by_id(1)
            assert book is None
    
    def test_get_book_by_isbn_success(self, app):
        """Test retrieving book by ISBN successfully."""
        with app.app_context():
            book = Book(isbn='9780743273565', title='Test Book')
            db.session.add(book)
            db.session.commit()
            
            retrieved_book = get_book_by_isbn('978-0-7432-7356-5')  # With hyphens
            assert retrieved_book is not None
            assert retrieved_book.title == 'Test Book'
    
    def test_get_book_by_isbn_not_found(self, app):
        """Test retrieving book by non-existent ISBN."""
        with app.app_context():
            book = get_book_by_isbn('9780439420891')
            assert book is None
    
    def test_get_book_by_isbn_empty_isbn(self, app):
        """Test retrieving book with empty ISBN."""
        with app.app_context():
            book = get_book_by_isbn('')
            assert book is None
    
    def test_get_book_by_isbn_invalid_isbn(self, app):
        """Test retrieving book with invalid ISBN."""
        with app.app_context():
            book = get_book_by_isbn('invalid-isbn')
            assert book is None


class TestBookUpdate:
    """Test book update functionality."""
    
    def test_update_book_metadata_success(self, app):
        """Test successful book metadata update."""
        with app.app_context():
            # Create initial book
            book = Book(isbn='9780743273565', title='Old Title')
            db.session.add(book)
            db.session.commit()
            book_id = book.id
            
            # Update metadata
            new_metadata = {
                'title': 'New Title',
                'authors': ['New Author'],
                'publisher': 'New Publisher'
            }
            
            updated_book, error = update_book_metadata(book_id, new_metadata)
            
            assert error is None
            assert updated_book is not None
            assert updated_book.title == 'New Title'
            assert updated_book.authors_list == ['New Author']
            assert updated_book.publisher == 'New Publisher'
    
    def test_update_book_metadata_not_found(self, app):
        """Test updating non-existent book."""
        with app.app_context():
            updated_book, error = update_book_metadata(999, {'title': 'New Title'})
            assert updated_book is None
            assert 'not found' in error
    
    def test_update_book_metadata_partial_update(self, app):
        """Test partial metadata update."""
        with app.app_context():
            # Create initial book
            book = Book(isbn='9780743273565', title='Original Title', publisher='Original Publisher')
            db.session.add(book)
            db.session.commit()
            book_id = book.id
            
            # Update only title
            new_metadata = {'title': 'Updated Title'}
            
            updated_book, error = update_book_metadata(book_id, new_metadata)
            
            assert error is None
            assert updated_book.title == 'Updated Title'
            assert updated_book.publisher == 'Original Publisher'  # Should remain unchanged
    
    def test_update_book_metadata_database_error(self, app, mocker):
        """Test update when database commit fails."""
        with app.app_context():
            # Create initial book
            book = Book(isbn='9780743273565', title='Test Book')
            db.session.add(book)
            db.session.commit()
            book_id = book.id
            
            # Mock database commit to raise exception
            mock_commit = mocker.patch.object(db.session, 'commit')
            mock_commit.side_effect = Exception('Database error')
            
            updated_book, error = update_book_metadata(book_id, {'title': 'New Title'})
            
            assert updated_book is None
            assert 'Database error while updating book' in error


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple functions."""
    
    def test_full_book_lifecycle(self, app, mocker, sample_book_metadata):
        """Test complete book lifecycle: add, retrieve, update."""
        with app.app_context():
            # Mock API for adding book
            mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
            mock_api.return_value = (sample_book_metadata, False, None)
            
            # 1. Add book
            book, error = process_and_store_book('9780743273565')
            assert error is None
            assert book is not None
            book_id = book.id
            
            # 2. Retrieve by ID
            retrieved_book = get_book_by_id(book_id)
            assert retrieved_book is not None
            assert retrieved_book.title == 'The Great Gatsby'
            
            # 3. Retrieve by ISBN
            retrieved_book = get_book_by_isbn('9780743273565')
            assert retrieved_book is not None
            assert retrieved_book.title == 'The Great Gatsby'
            
            # 4. Update metadata
            new_metadata = {'description': 'Updated description'}
            updated_book, error = update_book_metadata(book_id, new_metadata)
            assert error is None
            assert updated_book.description == 'Updated description'
    
    def test_multiple_books_management(self, app, mocker):
        """Test managing multiple books."""
        with app.app_context():
            # Mock API for different books
            mock_api = mocker.patch('app.services.book_service.get_book_metadata_with_fallback')
            
            # Add first book
            mock_api.return_value = ({'title': 'Book 1', 'authors': ['Author 1']}, False, None)
            book1, _ = process_and_store_book('9780743273565')
            
            # Add second book
            mock_api.return_value = ({'title': 'Book 2', 'authors': ['Author 2']}, False, None)
            book2, _ = process_and_store_book('9780439420891')
            
            # Retrieve all books
            all_books = get_all_books()
            assert len(all_books) == 2