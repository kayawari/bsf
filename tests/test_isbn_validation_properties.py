"""
Property-based tests for ISBN validation functionality.

Feature: book-management, Property 1: ISBN Validation and Format Support
Feature: book-management, Property 2: Invalid ISBN Rejection
Feature: book-management, Property 4: Duplicate Prevention
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from app import create_app, db
from app.models.book import Book
from app.services.isbn_service import (
    validate_isbn, isbn10_to_isbn13, is_duplicate_isbn
)


@pytest.fixture
def app():
    """Create test app."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


class TestISBNValidationProperties:
    """
    Property-based tests for ISBN validation and format support.
    
    Feature: book-management, Property 1: ISBN Validation and Format Support
    Feature: book-management, Property 2: Invalid ISBN Rejection
    """
    
    @given(
        isbn10_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        check_digit=st.sampled_from([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'X'])
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_isbn10_format_support(self, app, isbn10_digits, check_digit):
        """
        **Property 1: ISBN Validation and Format Support**
        
        *For any* valid ISBN-10 format, the system should accept and normalize it 
        for storage, ensuring both formats are supported consistently.
        
        **Validates: Requirements 1.1, 1.4**
        """
        with app.app_context():
            # Construct a potentially valid ISBN-10
            isbn10_base = ''.join(map(str, isbn10_digits))
            
            # Calculate correct check digit
            checksum = sum(int(digit) * (10 - i) for i, digit in enumerate(isbn10_base))
            correct_check = (11 - (checksum % 11)) % 11
            correct_check_char = 'X' if correct_check == 10 else str(correct_check)
            
            # Create valid ISBN-10
            valid_isbn10 = isbn10_base + correct_check_char
            
            # Test validation
            is_valid, normalized, error = validate_isbn(valid_isbn10)
            
            # Should be valid and normalized to ISBN-13
            assert is_valid
            assert normalized is not None
            assert len(normalized) == 13
            assert normalized.startswith('978')
            assert error is None
            
            # Test with formatting (hyphens and spaces)
            formatted_isbn = f"{valid_isbn10[:1]}-{valid_isbn10[1:6]}-{valid_isbn10[6:9]}-{valid_isbn10[9]}"
            is_valid_formatted, normalized_formatted, error_formatted = validate_isbn(formatted_isbn)
            
            assert is_valid_formatted
            assert normalized_formatted == normalized
            assert error_formatted is None
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_isbn13_format_support(self, app, isbn13_prefix, isbn13_digits):
        """
        **Property 1: ISBN Validation and Format Support**
        
        *For any* valid ISBN-13 format, the system should accept and normalize it 
        for storage, ensuring both formats are supported consistently.
        
        **Validates: Requirements 1.1, 1.4**
        """
        with app.app_context():
            # Construct a potentially valid ISBN-13
            isbn13_base = isbn13_prefix + ''.join(map(str, isbn13_digits))
            
            # Calculate correct check digit
            checksum = 0
            for i in range(12):
                weight = 1 if i % 2 == 0 else 3
                checksum += int(isbn13_base[i]) * weight
            
            check_digit = (10 - (checksum % 10)) % 10
            valid_isbn13 = isbn13_base + str(check_digit)
            
            # Test validation
            is_valid, normalized, error = validate_isbn(valid_isbn13)
            
            # Should be valid and normalized (same as input for ISBN-13)
            assert is_valid
            assert normalized == valid_isbn13
            assert error is None
            
            # Test with formatting (hyphens and spaces)
            formatted_isbn = f"{valid_isbn13[:3]}-{valid_isbn13[3:4]}-{valid_isbn13[4:9]}-{valid_isbn13[9:12]}-{valid_isbn13[12]}"
            is_valid_formatted, normalized_formatted, error_formatted = validate_isbn(formatted_isbn)
            
            assert is_valid_formatted
            assert normalized_formatted == valid_isbn13
            assert error_formatted is None


class TestISBNDuplicatePreventionProperties:
    """
    Property-based tests for ISBN duplicate prevention.
    
    Feature: book-management, Property 4: Duplicate Prevention
    """
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        title=st.text(min_size=1, max_size=255)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_duplicate_isbn_prevention(self, app, isbn13_prefix, isbn13_digits, title):
        """
        **Property 4: Duplicate Prevention**
        
        *For any* ISBN that already exists in the collection, attempting to add it 
        again should be rejected with a notification to the user.
        
        **Validates: Requirements 1.5**
        """
        with app.app_context():
            db.create_all()
            try:
                # Construct a valid ISBN-13
                isbn13_base = isbn13_prefix + ''.join(map(str, isbn13_digits))
                
                # Calculate correct check digit
                checksum = 0
                for i in range(12):
                    weight = 1 if i % 2 == 0 else 3
                    checksum += int(isbn13_base[i]) * weight
                
                check_digit = (10 - (checksum % 10)) % 10
                valid_isbn13 = isbn13_base + str(check_digit)
                
                # First, create and store a book with this ISBN
                book = Book(isbn=valid_isbn13, title=title)
                db.session.add(book)
                db.session.commit()
                
                # Verify the book was stored
                stored_book = Book.query.filter_by(isbn=valid_isbn13).first()
                assert stored_book is not None, "Book should be stored in database"
                
                # Now test duplicate detection
                is_duplicate, normalized_isbn, error = is_duplicate_isbn(valid_isbn13)
                
                # Should detect as duplicate
                assert is_duplicate, "Should detect ISBN as duplicate"
                assert normalized_isbn == valid_isbn13, "Should return normalized ISBN"
                assert error is None, "Should not return error for valid ISBN"
                
                # Test with different formatting of the same ISBN
                formatted_isbn = f"{valid_isbn13[:3]}-{valid_isbn13[3:4]}-{valid_isbn13[4:9]}-{valid_isbn13[9:12]}-{valid_isbn13[12]}"
                is_duplicate_formatted, normalized_formatted, error_formatted = is_duplicate_isbn(formatted_isbn)
                
                assert is_duplicate_formatted, "Should detect formatted ISBN as duplicate"
                assert normalized_formatted == valid_isbn13, "Should normalize formatted ISBN correctly"
                assert error_formatted is None, "Should not return error for valid formatted ISBN"
                
            finally:
                db.drop_all()
    
    @given(
        isbn10_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        title=st.text(min_size=1, max_size=255)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_duplicate_isbn10_to_isbn13_prevention(self, app, isbn10_digits, title):
        """
        **Property 4: Duplicate Prevention**
        
        *For any* ISBN-10 that converts to an existing ISBN-13 in the collection, 
        attempting to add it should be rejected as a duplicate.
        
        **Validates: Requirements 1.5**
        """
        with app.app_context():
            db.create_all()
            try:
                # Construct a valid ISBN-10
                isbn10_base = ''.join(map(str, isbn10_digits))
                
                # Calculate correct check digit for ISBN-10
                checksum = sum(int(digit) * (10 - i) for i, digit in enumerate(isbn10_base))
                correct_check = (11 - (checksum % 11)) % 11
                correct_check_char = 'X' if correct_check == 10 else str(correct_check)
                
                valid_isbn10 = isbn10_base + correct_check_char
                
                # Convert to ISBN-13
                isbn13_equivalent = isbn10_to_isbn13(valid_isbn10)
                
                # Store book with ISBN-13 format
                book = Book(isbn=isbn13_equivalent, title=title)
                db.session.add(book)
                db.session.commit()
                
                # Verify the book was stored
                stored_book = Book.query.filter_by(isbn=isbn13_equivalent).first()
                assert stored_book is not None, "Book should be stored in database"
                
                # Now test duplicate detection with ISBN-10 format
                is_duplicate, normalized_isbn, error = is_duplicate_isbn(valid_isbn10)
                
                # Should detect as duplicate (ISBN-10 normalizes to existing ISBN-13)
                assert is_duplicate, "Should detect ISBN-10 as duplicate of existing ISBN-13"
                assert normalized_isbn == isbn13_equivalent, "Should normalize ISBN-10 to equivalent ISBN-13"
                assert error is None, "Should not return error for valid ISBN-10"
                
            finally:
                db.drop_all()
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        title1=st.text(min_size=1, max_size=255),
        title2=st.text(min_size=1, max_size=255)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_non_duplicate_isbn_acceptance(self, app, isbn13_prefix, isbn13_digits, title1, title2):
        """
        **Property 4: Duplicate Prevention**
        
        *For any* ISBN that does not exist in the collection, it should not be 
        detected as a duplicate and should be acceptable for addition.
        
        **Validates: Requirements 1.5**
        """
        with app.app_context():
            db.create_all()
            try:
                # Construct first valid ISBN-13
                isbn13_base1 = isbn13_prefix + ''.join(map(str, isbn13_digits))
                
                # Calculate correct check digit
                checksum1 = 0
                for i in range(12):
                    weight = 1 if i % 2 == 0 else 3
                    checksum1 += int(isbn13_base1[i]) * weight
                
                check_digit1 = (10 - (checksum1 % 10)) % 10
                valid_isbn13_1 = isbn13_base1 + str(check_digit1)
                
                # Construct second valid ISBN-13 (different from first)
                # Modify the last digit of the base to ensure different ISBN
                modified_digits = isbn13_digits.copy()
                if modified_digits:
                    modified_digits[-1] = (modified_digits[-1] + 1) % 10
                
                isbn13_base2 = isbn13_prefix + ''.join(map(str, modified_digits))
                
                # Calculate correct check digit for second ISBN
                checksum2 = 0
                for i in range(12):
                    weight = 1 if i % 2 == 0 else 3
                    checksum2 += int(isbn13_base2[i]) * weight
                
                check_digit2 = (10 - (checksum2 % 10)) % 10
                valid_isbn13_2 = isbn13_base2 + str(check_digit2)
                
                # Ensure the two ISBNs are different
                if valid_isbn13_1 == valid_isbn13_2:
                    return  # Skip this test case if ISBNs ended up the same
                
                # Store first book
                book1 = Book(isbn=valid_isbn13_1, title=title1)
                db.session.add(book1)
                db.session.commit()
                
                # Verify first book was stored
                stored_book1 = Book.query.filter_by(isbn=valid_isbn13_1).first()
                assert stored_book1 is not None, "First book should be stored in database"
                
                # Test that second ISBN is not detected as duplicate
                is_duplicate, normalized_isbn, error = is_duplicate_isbn(valid_isbn13_2)
                
                # Should NOT detect as duplicate
                assert not is_duplicate, "Should not detect different ISBN as duplicate"
                assert normalized_isbn == valid_isbn13_2, "Should return normalized ISBN"
                assert error is None, "Should not return error for valid ISBN"
                
                # Verify we can store the second book without issues
                book2 = Book(isbn=valid_isbn13_2, title=title2)
                db.session.add(book2)
                db.session.commit()
                
                # Verify both books are stored
                stored_book2 = Book.query.filter_by(isbn=valid_isbn13_2).first()
                assert stored_book2 is not None, "Second book should be stored in database"
                
                total_books = Book.query.count()
                assert total_books == 2, "Should have two different books stored"
                
            finally:
                db.drop_all()
    
    @given(
        invalid_isbn=st.one_of(
            st.just(""),
            st.just(None),
            st.text(min_size=1, max_size=9).filter(lambda x: x.replace('-', '').replace(' ', '') != ''),
            st.text(min_size=14, max_size=20).filter(lambda x: x.replace('-', '').replace(' ', '') != '')
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_isbn_duplicate_check_error_handling(self, app, invalid_isbn):
        """
        **Property 4: Duplicate Prevention**
        
        *For any* invalid ISBN format, the duplicate check should return appropriate 
        error information without crashing.
        
        **Validates: Requirements 1.5**
        """
        with app.app_context():
            db.create_all()
            try:
                # Test duplicate check with invalid ISBN
                is_duplicate, normalized_isbn, error = is_duplicate_isbn(invalid_isbn)
                
                # Should not detect as duplicate (because it's invalid)
                assert not is_duplicate, "Invalid ISBN should not be detected as duplicate"
                assert normalized_isbn is None, "Should not return normalized ISBN for invalid input"
                assert error is not None, "Should return error message for invalid ISBN"
                assert isinstance(error, str), "Error should be a string"
                assert len(error) > 0, "Error message should not be empty"
                
            finally:
                db.drop_all()


class TestISBNInvalidRejectionProperties:
    """
    Property-based tests for invalid ISBN rejection.
    
    Feature: book-management, Property 2: Invalid ISBN Rejection
    """
    
    @given(
        invalid_input=st.one_of(
            # Empty or None inputs
            st.just(""),
            st.just(None),
            # Wrong length inputs
            st.text(min_size=1, max_size=9).filter(lambda x: x.replace('-', '').replace(' ', '') != ''),
            st.text(min_size=11, max_size=12).filter(lambda x: x.replace('-', '').replace(' ', '') != ''),
            st.text(min_size=14, max_size=20).filter(lambda x: x.replace('-', '').replace(' ', '') != ''),
            # Invalid characters
            st.text(min_size=10, max_size=13).filter(
                lambda x: any(c not in '0123456789X-' for c in x.upper()) and len(x.replace('-', '').replace(' ', '')) in [10, 13]
            ),
            # Invalid ISBN-13 prefixes (not 978 or 979)
            st.text(min_size=13, max_size=13).filter(
                lambda x: x.isdigit() and not x.startswith(('978', '979'))
            )
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_isbn_rejection(self, app, invalid_input):
        """
        **Property 2: Invalid ISBN Rejection**
        
        *For any* invalid ISBN format or malformed input, the system should reject 
        the input and display an appropriate error message.
        
        **Validates: Requirements 1.2**
        """
        with app.app_context():
            # Test validation of invalid input
            is_valid, normalized, error = validate_isbn(invalid_input)
            
            # Should be invalid
            assert not is_valid
            assert normalized is None
            assert error is not None
            assert isinstance(error, str)
            assert len(error) > 0
    
    @given(
        isbn10_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        wrong_check_digit=st.integers(0, 9)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_isbn10_checksum_rejection(self, app, isbn10_digits, wrong_check_digit):
        """
        **Property 2: Invalid ISBN Rejection**
        
        *For any* ISBN-10 with invalid checksum, the system should reject it.
        
        **Validates: Requirements 1.2**
        """
        with app.app_context():
            # Construct ISBN-10 with wrong checksum
            isbn10_base = ''.join(map(str, isbn10_digits))
            
            # Calculate correct check digit
            checksum = sum(int(digit) * (10 - i) for i, digit in enumerate(isbn10_base))
            correct_check = (11 - (checksum % 11)) % 11
            correct_check_digit = correct_check if correct_check < 10 else 10
            
            # Use a different check digit (ensure it's wrong)
            if wrong_check_digit != correct_check_digit:
                invalid_isbn10 = isbn10_base + str(wrong_check_digit)
                
                # Test validation
                is_valid, normalized, error = validate_isbn(invalid_isbn10)
                
                # Should be invalid
                assert not is_valid
                assert normalized is None
                assert error is not None
                assert "checksum" in error.lower()
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        wrong_check_digit=st.integers(0, 9)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_isbn13_checksum_rejection(self, app, isbn13_prefix, isbn13_digits, wrong_check_digit):
        """
        **Property 2: Invalid ISBN Rejection**
        
        *For any* ISBN-13 with invalid checksum, the system should reject it.
        
        **Validates: Requirements 1.2**
        """
        with app.app_context():
            # Construct ISBN-13 with wrong checksum
            isbn13_base = isbn13_prefix + ''.join(map(str, isbn13_digits))
            
            # Calculate correct check digit
            checksum = 0
            for i in range(12):
                weight = 1 if i % 2 == 0 else 3
                checksum += int(isbn13_base[i]) * weight
            
            correct_check_digit = (10 - (checksum % 10)) % 10
            
            # Use a different check digit (ensure it's wrong)
            if wrong_check_digit != correct_check_digit:
                invalid_isbn13 = isbn13_base + str(wrong_check_digit)
                
                # Test validation
                is_valid, normalized, error = validate_isbn(invalid_isbn13)
                
                # Should be invalid
                assert not is_valid
                assert normalized is None
                assert error is not None
                assert "checksum" in error.lower()
    
    @given(
        formatting_chars=st.text(min_size=0, max_size=5).filter(
            lambda x: all(c in ' -.' for c in x)
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_isbn_formatting_normalization(self, app, formatting_chars):
        """
        **Property 1: ISBN Validation and Format Support**
        
        *For any* valid ISBN with various formatting characters (spaces, hyphens),
        the system should normalize it correctly.
        
        **Validates: Requirements 1.1, 1.4**
        """
        with app.app_context():
            # Use a known valid ISBN-13
            base_isbn = "9780306406157"
            
            # Insert formatting characters at random positions
            formatted_isbn = ""
            for i, char in enumerate(base_isbn):
                if i > 0 and i < len(base_isbn) - 1:  # Don't add at start/end
                    formatted_isbn += formatting_chars[:1] if formatting_chars else ""
                formatted_isbn += char
            
            # Test validation
            is_valid, normalized, error = validate_isbn(formatted_isbn)
            
            # Should be valid and normalized to clean ISBN
            if formatted_isbn.replace(' ', '').replace('-', '').replace('.', '') == base_isbn:
                assert is_valid
                assert normalized == base_isbn
                assert error is None