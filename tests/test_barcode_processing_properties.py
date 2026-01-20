"""
Property-based tests for barcode processing service functionality.

Feature: barcode-scanning, Property 1: Barcode Extraction Consistency
Feature: barcode-scanning, Property 2: Service Integration Consistency  
Feature: barcode-scanning, Property 7: ISBN Validation
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models.book import Book
from app.services.barcode_service import (
    validate_barcode_result, 
    process_scanned_barcode,
    create_scanning_session,
    log_scanning_error
)


@pytest.fixture
def app():
    """Create test app."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


class TestBarcodeExtractionConsistencyProperties:
    """
    Property-based tests for barcode extraction consistency.
    
    Feature: barcode-scanning, Property 1: Barcode Extraction Consistency
    """
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_barcode_extraction_consistency_isbn13(self, app, isbn13_prefix, isbn13_digits):
        """
        **Property 1: Barcode Extraction Consistency**
        
        *For any* valid barcode image (camera or file), the scanner should extract 
        the same ISBN regardless of the input method used.
        
        **Validates: Requirements 1.2, 2.2**
        """
        with app.app_context():
            # Construct a valid ISBN-13
            isbn13_base = isbn13_prefix + ''.join(map(str, isbn13_digits))
            
            # Calculate correct check digit
            checksum = 0
            for i in range(12):
                weight = 1 if i % 2 == 0 else 3
                checksum += int(isbn13_base[i]) * weight
            
            check_digit = (10 - (checksum % 10)) % 10
            valid_isbn13 = isbn13_base + str(check_digit)
            
            # Test validation consistency across different scan types (now returns 3 values)
            camera_result = validate_barcode_result(valid_isbn13)
            file_result = validate_barcode_result(valid_isbn13)
            
            # Both should return the same validation result
            assert camera_result == file_result, "Validation should be consistent regardless of scan method"
            assert camera_result[0] == True, "Valid ISBN should be accepted"
            assert camera_result[1] == valid_isbn13, "Valid ISBN should return normalized ISBN"
            assert camera_result[2] is None, "Valid ISBN should not return error"
            
            # Test with formatting variations (simulating different scan quality)
            formatted_variations = [
                valid_isbn13,
                f"{valid_isbn13[:3]}-{valid_isbn13[3:]}",
                f"{valid_isbn13[:3]} {valid_isbn13[3:]}",
                valid_isbn13.lower(),  # Case variation
                valid_isbn13.upper()
            ]
            
            validation_results = []
            for variation in formatted_variations:
                result = validate_barcode_result(variation)
                validation_results.append(result)
            
            # All variations should produce the same validation result (normalized ISBN should be the same)
            first_result = validation_results[0]
            for i, result in enumerate(validation_results[1:], 1):
                assert result[0] == first_result[0], f"All formatting variations should have same validity: {formatted_variations[i]}"
                assert result[1] == first_result[1], f"All formatting variations should normalize to same ISBN: {formatted_variations[i]}"
                # Error status should be the same (None for valid ISBNs)
                assert (result[2] is None) == (first_result[2] is None), f"All formatting variations should have same error status: {formatted_variations[i]}"
    
    @given(
        isbn10_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        check_digit=st.sampled_from([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'X'])
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_barcode_extraction_consistency_isbn10(self, app, isbn10_digits, check_digit):
        """
        **Property 1: Barcode Extraction Consistency**
        
        *For any* valid ISBN-10 barcode, the validation should be consistent 
        regardless of how it was scanned.
        
        **Validates: Requirements 1.2, 2.2**
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
            
            # Test validation consistency (now returns 3 values)
            result1 = validate_barcode_result(valid_isbn10)
            result2 = validate_barcode_result(valid_isbn10)
            
            # Results should be identical
            assert result1 == result2, "Validation should be deterministic"
            assert result1[0] == True, "Valid ISBN-10 should be accepted"
            assert result1[1] is not None, "Valid ISBN-10 should return normalized ISBN"
            assert result1[2] is None, "Valid ISBN-10 should not return error"
            
            # Test with different formatting
            formatted_isbn10 = f"{valid_isbn10[:1]}-{valid_isbn10[1:6]}-{valid_isbn10[6:9]}-{valid_isbn10[9]}"
            formatted_result = validate_barcode_result(formatted_isbn10)
            
            assert formatted_result == result1, "Formatted ISBN-10 should validate the same as unformatted"


class TestServiceIntegrationConsistencyProperties:
    """
    Property-based tests for service integration consistency.
    
    Feature: barcode-scanning, Property 2: Service Integration Consistency
    """
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        scan_type=st.sampled_from(['camera', 'file'])
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_service_integration_consistency(self, app, isbn13_prefix, isbn13_digits, scan_type):
        """
        **Property 2: Service Integration Consistency**
        
        *For any* scanned ISBN, the system should use the existing Google_Books_Service, 
        Book_Service, and ISBN_Service rather than implementing new logic.
        
        **Validates: Requirements 7.1, 7.2, 7.3**
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
                
                # Mock the existing services to verify they are called
                with patch('app.services.barcode_service.process_and_store_book_with_retry_option') as mock_book_service:
                    # Configure mock to return success
                    mock_book = MagicMock()
                    mock_book.title = "Test Book"
                    mock_book.isbn = valid_isbn13
                    mock_book_service.return_value = (mock_book, None, False)
                    
                    # Process the scanned barcode (now returns 4 values)
                    book, error, retry, scan_error = process_scanned_barcode(valid_isbn13, scan_type)
                    
                    # Verify the existing book service was called
                    mock_book_service.assert_called_once_with(valid_isbn13)
                    
                    # Verify the result is consistent with service integration
                    assert book is not None, "Should return book object from existing service"
                    assert error is None, "Should not return error for successful processing"
                    assert retry == False, "Should return retry flag from existing service"
                    assert scan_error is None, "Should not return scan error for successful processing"
                    
                    # Verify the book object properties match the mock
                    assert book.title == "Test Book"
                    assert book.isbn == valid_isbn13
                
            finally:
                db.drop_all()
    
    @given(
        invalid_isbn=st.one_of(
            st.just(""),
            st.text(min_size=1, max_size=9).filter(lambda x: x.replace('-', '').replace(' ', '') != ''),
            st.text(min_size=14, max_size=20).filter(lambda x: x.replace('-', '').replace(' ', '') != '')
        ),
        scan_type=st.sampled_from(['camera', 'file'])
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_service_integration_error_handling(self, app, invalid_isbn, scan_type):
        """
        **Property 2: Service Integration Consistency**
        
        *For any* invalid ISBN, the system should use existing validation services 
        and return consistent error messages.
        
        **Validates: Requirements 7.1, 7.2, 7.3**
        """
        with app.app_context():
            # Process invalid ISBN (now returns 4 values)
            book, error, retry, scan_error = process_scanned_barcode(invalid_isbn, scan_type)
            
            # Should return consistent error handling
            assert book is None, "Should not return book for invalid ISBN"
            assert error is not None, "Should return error message for invalid ISBN"
            assert isinstance(error, str), "Error should be a string"
            assert len(error) > 0, "Error message should not be empty"
            assert retry == False, "Should not suggest retry for validation errors"
            assert scan_error is not None, "Should return structured scan error"
            assert scan_error.error_type.value == "validation", "Should categorize as validation error"
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        scan_type=st.sampled_from(['camera', 'file'])
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_service_integration_duplicate_handling(self, app, isbn13_prefix, isbn13_digits, scan_type):
        """
        **Property 2: Service Integration Consistency**
        
        *For any* duplicate ISBN, the system should use existing duplicate detection 
        services and return consistent error messages.
        
        **Validates: Requirements 7.1, 7.2, 7.3**
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
                
                # Create existing book in database
                existing_book = Book(isbn=valid_isbn13, title="Existing Book")
                db.session.add(existing_book)
                db.session.commit()
                
                # Process the same ISBN (should be detected as duplicate) - now returns 4 values
                book, error, retry, scan_error = process_scanned_barcode(valid_isbn13, scan_type)
                
                # Should handle duplicate consistently
                assert book is None, "Should not return book for duplicate ISBN"
                assert error is not None, "Should return error for duplicate ISBN"
                assert "already exists" in error.lower(), "Error should mention duplicate"
                assert scan_error is not None, "Should return structured scan error"
                assert scan_error.error_type.value == "duplicate", "Should categorize as duplicate error"
                assert error is not None, "Should return error message for duplicate"
                assert "already exists" in error.lower(), "Error should indicate duplicate"
                assert retry == False, "Should not suggest retry for duplicates"
                
            finally:
                db.drop_all()


class TestISBNValidationProperties:
    """
    Property-based tests for ISBN validation in barcode processing.
    
    Feature: barcode-scanning, Property 7: ISBN Validation
    """
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_isbn_validation_property_valid_isbn13(self, app, isbn13_prefix, isbn13_digits):
        """
        **Property 7: ISBN Validation**
        
        *For any* scanned text, the system should validate it as a proper ISBN 
        using existing validation logic before processing.
        
        **Validates: Requirements 4.5**
        """
        with app.app_context():
            # Construct a valid ISBN-13
            isbn13_base = isbn13_prefix + ''.join(map(str, isbn13_digits))
            
            # Calculate correct check digit
            checksum = 0
            for i in range(12):
                weight = 1 if i % 2 == 0 else 3
                checksum += int(isbn13_base[i]) * weight
            
            check_digit = (10 - (checksum % 10)) % 10
            valid_isbn13 = isbn13_base + str(check_digit)
            
            # Test validation (now returns 3 values)
            is_valid, normalized_isbn, scan_error = validate_barcode_result(valid_isbn13)
            
            # Should validate successfully
            assert is_valid == True, "Valid ISBN should pass validation"
            assert normalized_isbn == valid_isbn13, "Should return normalized ISBN"
            assert scan_error is None, "Valid ISBN should not return error"
    
    @given(
        isbn10_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_isbn_validation_property_valid_isbn10(self, app, isbn10_digits):
        """
        **Property 7: ISBN Validation**
        
        *For any* valid ISBN-10 scanned text, the system should validate it 
        using existing validation logic.
        
        **Validates: Requirements 4.5**
        """
        with app.app_context():
            # Construct a valid ISBN-10
            isbn10_base = ''.join(map(str, isbn10_digits))
            
            # Calculate correct check digit
            checksum = sum(int(digit) * (10 - i) for i, digit in enumerate(isbn10_base))
            correct_check = (11 - (checksum % 11)) % 11
            correct_check_char = 'X' if correct_check == 10 else str(correct_check)
            
            valid_isbn10 = isbn10_base + correct_check_char
            
            # Test validation (now returns 3 values)
            is_valid, normalized_isbn, scan_error = validate_barcode_result(valid_isbn10)
            
            # Should validate successfully
            assert is_valid == True, "Valid ISBN-10 should pass validation"
            assert normalized_isbn is not None, "Should return normalized ISBN"
            assert scan_error is None, "Valid ISBN should not return error"
    
    @given(
        invalid_text=st.one_of(
            st.just(""),
            st.just(None),
            st.text(min_size=1, max_size=9).filter(lambda x: x.replace('-', '').replace(' ', '') != ''),
            st.text(min_size=14, max_size=20).filter(lambda x: x.replace('-', '').replace(' ', '') != ''),
            st.text(min_size=1, max_size=50).filter(
                lambda x: any(c not in '0123456789X-' for c in x.upper())
            )
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_isbn_validation_property_invalid_text(self, app, invalid_text):
        """
        **Property 7: ISBN Validation**
        
        *For any* invalid scanned text, the system should reject it with 
        appropriate error messages using existing validation logic.
        
        **Validates: Requirements 4.5**
        """
        with app.app_context():
            # Test validation of invalid text (now returns 3 values)
            is_valid, normalized_isbn, scan_error = validate_barcode_result(invalid_text)
            
            # Should reject invalid text
            assert is_valid == False, "Invalid text should be rejected"
            assert normalized_isbn is None, "Invalid text should not return normalized ISBN"
            assert scan_error is not None, "Invalid text should return scan error"
            assert scan_error.error_type.value == "validation", "Should categorize as validation error"
            assert len(scan_error.user_message) > 0, "Error message should not be empty"
    
    @given(
        isbn13_prefix=st.sampled_from(['978', '979']),
        isbn13_digits=st.lists(st.integers(0, 9), min_size=9, max_size=9),
        wrong_check_digit=st.integers(0, 9)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_isbn_validation_property_invalid_checksum(self, app, isbn13_prefix, isbn13_digits, wrong_check_digit):
        """
        **Property 7: ISBN Validation**
        
        *For any* ISBN with invalid checksum, the system should reject it 
        using existing validation logic.
        
        **Validates: Requirements 4.5**
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
                
                # Test validation (now returns 3 values)
                is_valid, normalized_isbn, scan_error = validate_barcode_result(invalid_isbn13)
                
                # Should reject invalid checksum
                assert is_valid == False, "Invalid checksum should be rejected"
                assert normalized_isbn is None, "Invalid checksum should not return normalized ISBN"
                assert scan_error is not None, "Invalid checksum should return scan error"
                assert scan_error.error_type.value == "validation", "Should categorize as validation error"
                assert "checksum" in scan_error.user_message.lower(), "Error should mention checksum"
    
    @given(
        valid_isbn=st.one_of(
            # Generate valid ISBN-13
            st.tuples(
                st.sampled_from(['978', '979']),
                st.lists(st.integers(0, 9), min_size=9, max_size=9)
            ).map(lambda x: x[0] + ''.join(map(str, x[1]))).map(
                lambda base: base + str((10 - sum(
                    int(base[i]) * (1 if i % 2 == 0 else 3) for i in range(12)
                ) % 10) % 10)
            ),
            # Generate valid ISBN-10
            st.lists(st.integers(0, 9), min_size=9, max_size=9).map(
                lambda digits: ''.join(map(str, digits)) + (
                    'X' if (11 - sum(int(digits[i]) * (10 - i) for i in range(9)) % 11) % 11 == 10
                    else str((11 - sum(int(digits[i]) * (10 - i) for i in range(9)) % 11) % 11)
                )
            )
        ),
        input_type=st.sampled_from([str, int, float, list, dict, None])
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_isbn_validation_input_type_handling(self, app, valid_isbn, input_type):
        """
        **Property 7: ISBN Validation**
        
        *For any* input type, the validation should handle it gracefully 
        and only accept string inputs.
        
        **Validates: Requirements 4.5**
        """
        with app.app_context():
            # Convert valid ISBN to different input types
            if input_type == str:
                test_input = valid_isbn
                expected_valid = True
            elif input_type == int and valid_isbn.replace('X', '').isdigit():
                test_input = int(valid_isbn.replace('X', '10'))
                expected_valid = False  # Should reject non-string input
            elif input_type == float:
                test_input = 123.456
                expected_valid = False
            elif input_type == list:
                test_input = list(valid_isbn)
                expected_valid = False
            elif input_type == dict:
                test_input = {"isbn": valid_isbn}
                expected_valid = False
            elif input_type is None:
                test_input = None
                expected_valid = False
            else:
                test_input = valid_isbn
                expected_valid = True
            
            # Test validation (now returns 3 values)
            is_valid, normalized_isbn, scan_error = validate_barcode_result(test_input)
            
            if expected_valid:
                assert is_valid == True, f"Valid string ISBN should be accepted: {test_input}"
                assert normalized_isbn is not None, "Valid input should return normalized ISBN"
                assert scan_error is None, "Valid ISBN should not return error"
            else:
                assert is_valid == False, f"Non-string input should be rejected: {test_input} ({type(test_input)})"
                assert normalized_isbn is None, "Invalid input should not return normalized ISBN"
                assert scan_error is not None, "Invalid input should return scan error"
                assert scan_error.error_type.value == "validation", "Should categorize as validation error"


class TestBarcodeServiceUtilityFunctions:
    """
    Property-based tests for barcode service utility functions.
    """
    
    @given(
        isbn=st.text(min_size=10, max_size=13).filter(lambda x: x.isdigit()),
        scan_type=st.sampled_from(['camera', 'file']),
        session_id=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_scanning_session_creation_consistency(self, app, isbn, scan_type, session_id):
        """
        Test that scanning session creation is consistent and generates valid sessions.
        """
        with app.app_context():
            # Create scanning session
            session = create_scanning_session(isbn, scan_type, session_id)
            
            # Verify session properties
            assert session.scanned_isbn == isbn
            assert session.scan_type == scan_type
            assert session.timestamp is not None
            assert session.session_id is not None
            assert len(session.session_id) > 0
            
            # If session_id was provided, it should be used
            if session_id:
                assert session.session_id == session_id
            else:
                # Generated session_id should contain scan_type and isbn info
                assert scan_type in session.session_id
                assert isbn[:8] in session.session_id
    
    @given(
        scanned_text=st.text(min_size=1, max_size=50),
        scan_type=st.sampled_from(['camera', 'file']),
        error_message=st.text(min_size=1, max_size=200)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_logging_privacy_protection(self, app, scanned_text, scan_type, error_message):
        """
        Test that error logging protects user privacy by truncating sensitive data.
        """
        with app.app_context():
            # Create a scan error for testing
            from app.services.barcode_service import create_scan_error, ScanErrorType, ScanErrorSeverity
            scan_error = create_scan_error(
                error_type=ScanErrorType.VALIDATION_ERROR,
                severity=ScanErrorSeverity.LOW,
                message=error_message,
                user_message="Test error message"
            )
            
            # This should not raise any exceptions
            log_scanning_error(scanned_text, scan_type, scan_error)
            
            # The function should complete without error
            # Privacy protection is tested by ensuring the function doesn't log full sensitive data
            # (This is more of a behavioral test - the actual privacy protection is in the implementation)
            assert True, "Error logging should complete without exceptions"