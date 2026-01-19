"""
Barcode scanning service for processing and validating scanned barcode results.

This module provides functions for validating scanned barcode text,
processing barcode scan results, and integrating with existing book services
to create book records from scanned ISBNs.
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.book import Book
from app.services.book_service import process_and_store_book_with_retry_option
from app.services.isbn_service import validate_isbn

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ScanningSession:
    """Temporary data structure for managing scanning workflow."""

    scanned_isbn: str
    scan_type: str  # 'camera' or 'file'
    book_metadata: Optional[dict] = None
    timestamp: datetime = None
    session_id: str = ""

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


def validate_barcode_result(scanned_text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that scanned text is a valid ISBN.

    This function validates the scanned barcode text to ensure it represents
    a valid ISBN that can be processed by the book management system.

    Args:
        scanned_text: The text extracted from the scanned barcode

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the scanned text is a valid ISBN
        - error_message: Error message if validation fails, None if valid

    Examples:
        >>> validate_barcode_result("9781234567890")
        (True, None)

        >>> validate_barcode_result("invalid")
        (False, "Invalid ISBN checksum")

        >>> validate_barcode_result("")
        (False, "Scanned text cannot be empty")
    """
    if not scanned_text:
        return False, "Scanned text cannot be empty"

    if not isinstance(scanned_text, str):
        return False, "Scanned text must be a string"

    # Clean and validate the scanned text as an ISBN
    try:
        is_valid, normalized_isbn, validation_error = validate_isbn(scanned_text)

        if not is_valid:
            logger.warning(f"Invalid ISBN scanned: {scanned_text} - {validation_error}")
            return False, validation_error

        logger.info(f"Valid ISBN scanned: {scanned_text} -> {normalized_isbn}")
        return True, None

    except Exception as e:
        error_msg = f"Error validating scanned barcode: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def process_scanned_barcode(
    scanned_text: str, scan_type: str
) -> Tuple[Optional[Book], Optional[str], bool]:
    """
    Process a scanned barcode result and create book record.

    This function takes the scanned barcode text, validates it as an ISBN,
    and uses the existing book service to retrieve metadata and store the book.
    It integrates with the existing Google Books API service and database operations.

    Args:
        scanned_text: The text extracted from barcode scanning
        scan_type: Type of scan performed ('camera' or 'file')

    Returns:
        Tuple of (book_object, error_message, should_retry_later)
        - book_object: Book instance if successful, None if failed
        - error_message: Error message if failed, warning if fallback used, None if successful
        - should_retry_later: True if user should try again later for better data

    Examples:
        >>> process_scanned_barcode("9781234567890", "camera")
        (<Book 9781234567890: Example Title>, None, False)

        >>> process_scanned_barcode("invalid", "camera")
        (None, "Invalid ISBN checksum", False)
    """
    if not scanned_text:
        return None, "Scanned text cannot be empty", False

    if not scan_type:
        scan_type = "unknown"

    # Validate scan type
    if scan_type not in ["camera", "file", "unknown"]:
        logger.warning(f"Unknown scan type: {scan_type}, defaulting to 'unknown'")
        scan_type = "unknown"

    logger.info(f"Processing scanned barcode: {scanned_text} (type: {scan_type})")

    # Step 1: Validate the scanned text as an ISBN
    is_valid, validation_error = validate_barcode_result(scanned_text)
    if not is_valid:
        return None, validation_error, False

    # Step 2: Use existing book service to process and store the book
    try:
        book, error_message, should_retry_later = (
            process_and_store_book_with_retry_option(scanned_text)
        )

        if book:
            # Log successful processing with scan type for analytics
            logger.info(
                f"Successfully processed scanned book: {book.title} "
                f"(ISBN: {book.isbn}, scan_type: {scan_type})"
            )

            # Return success with any warning message from fallback data
            return book, error_message, should_retry_later
        else:
            # Log processing failure
            logger.error(
                f"Failed to process scanned barcode: {scanned_text} "
                f"(scan_type: {scan_type}) - {error_message}"
            )
            return None, error_message, should_retry_later

    except Exception as e:
        error_msg = f"Unexpected error processing scanned barcode: {str(e)}"
        logger.error(error_msg)
        return None, error_msg, False


def create_scanning_session(
    scanned_isbn: str, scan_type: str, session_id: Optional[str] = None
) -> ScanningSession:
    """
    Create a scanning session for tracking workflow state.
    (This function support the core functionaliy based on the desian document and best practices.)

    This function creates a temporary session object to track the scanning
    workflow state. This is useful for maintaining context during the
    scan -> retrieve -> confirm -> save workflow.

    Args:
        scanned_isbn: The validated ISBN from scanning
        scan_type: Type of scan performed ('camera' or 'file')
        session_id: Optional session identifier for tracking

    Returns:
        ScanningSession object with workflow state
    """
    if not session_id:
        # Generate a simple session ID based on timestamp and ISBN
        timestamp = datetime.now(timezone.utc)
        session_id = (
            f"{scan_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{scanned_isbn[:8]}"
        )

    session = ScanningSession(
        scanned_isbn=scanned_isbn,
        scan_type=scan_type,
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
    )

    logger.info(f"Created scanning session: {session_id} for ISBN {scanned_isbn}")
    return session


def log_scanning_error(
    scanned_text: str,
    scan_type: str,
    error_message: str,
    error_type: str = "validation",
) -> None:
    """
    Log scanning errors for debugging and analytics.
    (This function support the core functionaliy based on the desian document and best practices.)

    This function provides centralized error logging for barcode scanning
    operations while maintaining user privacy by not logging sensitive data.

    Args:
        scanned_text: The scanned text (will be truncated for privacy)
        scan_type: Type of scan performed ('camera' or 'file')
        error_message: The error message to log
        error_type: Type of error ('validation', 'processing', 'api', 'database')
    """
    # Truncate scanned text for privacy (keep first 4 and last 4 characters)
    if len(scanned_text) > 8:
        truncated_text = f"{scanned_text[:4]}...{scanned_text[-4:]}"
    else:
        truncated_text = "***"

    logger.error(
        f"Barcode scanning error - Type: {error_type}, "
        f"Scan method: {scan_type}, "
        f"Text: {truncated_text}, "
        f"Error: {error_message}"
    )


def get_scanning_statistics() -> dict:
    """
    Get basic scanning statistics for monitoring.
    (This function support the core functionaliy based on the desian document and best practices.)

    This function provides basic statistics about scanning operations
    for monitoring and debugging purposes. It does not access the database
    directly but provides information about the current session.

    Returns:
        Dictionary with basic scanning statistics
    """
    # This is a placeholder for future analytics implementation
    # In a production system, this might track success rates, error types, etc.
    return {
        "service_status": "active",
        "supported_scan_types": ["camera", "file"],
        "validation_enabled": True,
        "integration_services": ["isbn_service", "book_service", "google_books_api"],
    }
