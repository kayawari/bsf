"""
Tests for ISBN validation and processing service.
"""

import pytest
from app import create_app, db
from app.models.book import Book
from app.services.isbn_service import (
    clean_isbn, validate_isbn10, validate_isbn13, isbn10_to_isbn13,
    normalize_isbn, validate_isbn, check_isbn_exists, is_duplicate_isbn
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


class TestISBNValidation:
    """Test ISBN validation functions."""
    
    def test_clean_isbn(self):
        """Test ISBN cleaning function."""
        assert clean_isbn("978-0-123456-78-9") == "9780123456789"
        assert clean_isbn("0-123456-78-X") == "012345678X"
        assert clean_isbn("  978 0 123456 78 9  ") == "9780123456789"
        assert clean_isbn("") == ""
        assert clean_isbn(None) == ""
    
    def test_validate_isbn10_valid(self):
        """Test valid ISBN-10 validation."""
        # Valid ISBN-10 examples
        assert validate_isbn10("0306406152")
        assert validate_isbn10("043942089X")
        assert validate_isbn10("0201530821")
    
    def test_validate_isbn10_invalid(self):
        """Test invalid ISBN-10 validation."""
        assert not validate_isbn10("0306406153")  # Wrong checksum
        assert not validate_isbn10("030640615")   # Too short
        assert not validate_isbn10("03064061522") # Too long
        assert not validate_isbn10("030640615A")  # Invalid character
        assert not validate_isbn10("")
        assert not validate_isbn10(None)
    
    def test_validate_isbn13_valid(self):
        """Test valid ISBN-13 validation."""
        # Valid ISBN-13 examples starting with 978
        assert validate_isbn13("9780306406157")
        assert validate_isbn13("9780439420891")
        assert validate_isbn13("9780201530827")
        # Valid ISBN-13 example starting with 979
        assert validate_isbn13("9791234567896")  # Valid 979 ISBN with correct checksum
    
    def test_validate_isbn13_invalid(self):
        """Test invalid ISBN-13 validation."""
        assert not validate_isbn13("9780306406158")  # Wrong checksum
        assert not validate_isbn13("978030640615")   # Too short
        assert not validate_isbn13("97803064061577") # Too long
        assert not validate_isbn13("978030640615A")  # Invalid character
        assert not validate_isbn13("1234567890123")  # Doesn't start with 978/979
        assert not validate_isbn13("9770306406157")  # Starts with 977 (not valid)
        assert not validate_isbn13("")
        assert not validate_isbn13(None)
    
    def test_isbn10_to_isbn13_conversion(self):
        """Test ISBN-10 to ISBN-13 conversion."""
        assert isbn10_to_isbn13("0306406152") == "9780306406157"
        assert isbn10_to_isbn13("043942089X") == "9780439420891"
        assert isbn10_to_isbn13("0201530821") == "9780201530827"
        
        # Test invalid ISBN-10 raises error
        with pytest.raises(ValueError):
            isbn10_to_isbn13("0306406153")  # Invalid checksum
    
    def test_normalize_isbn_success(self):
        """Test successful ISBN normalization."""
        # ISBN-13 normalization
        isbn13, error = normalize_isbn("978-0-306-40615-7")
        assert isbn13 == "9780306406157"
        assert error is None
        
        # ISBN-10 normalization (converts to ISBN-13)
        isbn13, error = normalize_isbn("0-306-40615-2")
        assert isbn13 == "9780306406157"
        assert error is None
    
    def test_normalize_isbn_failure(self):
        """Test failed ISBN normalization."""
        # Empty ISBN
        isbn13, error = normalize_isbn("")
        assert isbn13 is None
        assert "cannot be empty" in error
        
        # Invalid length
        isbn13, error = normalize_isbn("123456789")
        assert isbn13 is None
        assert "Invalid ISBN length" in error
        
        # Invalid checksum
        isbn13, error = normalize_isbn("9780306406158")
        assert isbn13 is None
        assert "Invalid ISBN-13 checksum" in error
    
    def test_validate_isbn_function(self):
        """Test the main validate_isbn function."""
        # Valid cases
        is_valid, normalized, error = validate_isbn("978-0-306-40615-7")
        assert is_valid
        assert normalized == "9780306406157"
        assert error is None
        
        is_valid, normalized, error = validate_isbn("0-306-40615-2")
        assert is_valid
        assert normalized == "9780306406157"
        assert error is None
        
        # Invalid case
        is_valid, normalized, error = validate_isbn("invalid")
        assert not is_valid
        assert normalized is None
        assert error is not None


class TestDuplicateDetection:
    """Test duplicate detection functionality."""
    
    def test_check_isbn_exists_empty_db(self, app):
        """Test checking ISBN existence in empty database."""
        with app.app_context():
            assert not check_isbn_exists("9780306406157")
            assert not check_isbn_exists("")
            assert not check_isbn_exists(None)
    
    def test_check_isbn_exists_with_data(self, app):
        """Test checking ISBN existence with data in database."""
        with app.app_context():
            # Add a book to the database
            book = Book(isbn="9780306406157", title="Test Book")
            db.session.add(book)
            db.session.commit()
            
            # Check existing ISBN
            assert check_isbn_exists("9780306406157")
            
            # Check non-existing ISBN
            assert not check_isbn_exists("9780439420891")
    
    def test_is_duplicate_isbn(self, app):
        """Test comprehensive duplicate checking."""
        with app.app_context():
            # Add a book to the database
            book = Book(isbn="9780306406157", title="Test Book")
            db.session.add(book)
            db.session.commit()
            
            # Test duplicate detection
            is_dup, normalized, error = is_duplicate_isbn("978-0-306-40615-7")
            assert is_dup
            assert normalized == "9780306406157"
            assert error is None
            
            # Test non-duplicate
            is_dup, normalized, error = is_duplicate_isbn("978-0-439-42089-1")
            assert not is_dup
            assert normalized == "9780439420891"
            assert error is None
            
            # Test invalid ISBN
            is_dup, normalized, error = is_duplicate_isbn("invalid")
            assert not is_dup
            assert normalized is None
            assert error is not None