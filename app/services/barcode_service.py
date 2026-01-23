"""
Barcode scanning service for processing and validating scanned barcode results.

This module provides functions for validating scanned barcode text,
processing barcode scan results, and integrating with existing book services
to create book records from scanned ISBNs with comprehensive error handling.
"""

import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.models.book import Book
from app.services.book_service import process_and_store_book_with_retry_option
from app.services.isbn_service import validate_isbn

# Configure logging
logger = logging.getLogger(__name__)


class ScanErrorType(Enum):
    """Enumeration of different types of scanning errors."""
    VALIDATION_ERROR = "validation"
    CAMERA_PERMISSION_ERROR = "camera_permission"
    CAMERA_NOT_FOUND_ERROR = "camera_not_found"
    CAMERA_NOT_SUPPORTED_ERROR = "camera_not_supported"
    NETWORK_ERROR = "network"
    API_ERROR = "api"
    DATABASE_ERROR = "database"
    BARCODE_DETECTION_ERROR = "barcode_detection"
    FILE_FORMAT_ERROR = "file_format"
    FILE_SIZE_ERROR = "file_size"
    DUPLICATE_ERROR = "duplicate"
    UNKNOWN_ERROR = "unknown"


class ScanErrorSeverity(Enum):
    """Enumeration of error severity levels."""
    LOW = "low"          # User can continue with alternative methods
    MEDIUM = "medium"    # User should try again or use fallback
    HIGH = "high"        # User needs to take corrective action
    CRITICAL = "critical"  # System-level issue requiring admin attention


@dataclass
class ScanError:
    """Structured error information for barcode scanning operations."""
    error_type: ScanErrorType
    severity: ScanErrorSeverity
    message: str
    user_message: str
    suggested_action: str
    show_retry: bool = False
    show_file_fallback: bool = False
    show_manual_entry: bool = False
    technical_details: Optional[str] = None


@dataclass
class ScanningSession:
    """Temporary data structure for managing scanning workflow."""

    scanned_isbn: str
    scan_type: str  # 'camera' or 'file'
    book_metadata: Optional[dict] = None
    timestamp: Optional[datetime] = None
    session_id: str = ""

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


def create_scan_error(
    error_type: ScanErrorType,
    severity: ScanErrorSeverity,
    message: str,
    user_message: Optional[str] = None,
    suggested_action: Optional[str] = None,
    technical_details: Optional[str] = None,
    **options
) -> ScanError:
    """
    Create a structured scan error with appropriate user messaging and actions.
    
    Args:
        error_type: Type of error that occurred
        severity: Severity level of the error
        message: Technical error message for logging
        user_message: User-friendly error message
        suggested_action: Suggested action for the user
        technical_details: Additional technical information
        **options: Additional options (show_retry, show_file_fallback, etc.)
    
    Returns:
        ScanError object with structured error information
    """
    # Generate user-friendly message if not provided
    if not user_message:
        user_message = _generate_user_message(error_type, message)
    
    # Generate suggested action if not provided
    if not suggested_action:
        suggested_action = _generate_suggested_action(error_type, severity)
    
    return ScanError(
        error_type=error_type,
        severity=severity,
        message=message,
        user_message=user_message,
        suggested_action=suggested_action,
        technical_details=technical_details,
        show_retry=options.get('show_retry', False),
        show_file_fallback=options.get('show_file_fallback', False),
        show_manual_entry=options.get('show_manual_entry', True)
    )


def _generate_user_message(error_type: ScanErrorType, technical_message: str) -> str:
    """Generate user-friendly error messages based on error type."""
    error_messages = {
        ScanErrorType.VALIDATION_ERROR: "The scanned barcode is not a valid ISBN.",
        ScanErrorType.CAMERA_PERMISSION_ERROR: "Camera access is required to scan barcodes. Please allow camera access and try again.",
        ScanErrorType.CAMERA_NOT_FOUND_ERROR: "No camera was found on this device.",
        ScanErrorType.CAMERA_NOT_SUPPORTED_ERROR: "Camera scanning is not supported in this browser.",
        ScanErrorType.NETWORK_ERROR: "Unable to connect to the book information service. Please check your internet connection.",
        ScanErrorType.API_ERROR: "The book information service is temporarily unavailable.",
        ScanErrorType.DATABASE_ERROR: "Unable to save the book to your collection. Please try again.",
        ScanErrorType.BARCODE_DETECTION_ERROR: "Could not detect a barcode in the image. Please try a clearer image or better lighting.",
        ScanErrorType.FILE_FORMAT_ERROR: "Please select a valid image file (JPEG, PNG, or WebP).",
        ScanErrorType.FILE_SIZE_ERROR: "The image file is too large. Please select an image smaller than 10MB.",
        ScanErrorType.DUPLICATE_ERROR: "This book is already in your collection.",
        ScanErrorType.UNKNOWN_ERROR: "An unexpected error occurred while scanning."
    }
    
    return error_messages.get(error_type, f"An error occurred: {technical_message}")


def _generate_suggested_action(error_type: ScanErrorType, severity: ScanErrorSeverity) -> str:
    """Generate suggested actions based on error type and severity."""
    action_map = {
        ScanErrorType.VALIDATION_ERROR: "Please scan a valid book barcode or enter the ISBN manually.",
        ScanErrorType.CAMERA_PERMISSION_ERROR: "Allow camera access in your browser settings, or use the file upload option.",
        ScanErrorType.CAMERA_NOT_FOUND_ERROR: "Use the file upload option to scan an image of the barcode.",
        ScanErrorType.CAMERA_NOT_SUPPORTED_ERROR: "Use the file upload option or enter the ISBN manually.",
        ScanErrorType.NETWORK_ERROR: "Check your internet connection and try again, or enter the ISBN manually.",
        ScanErrorType.API_ERROR: "Try again in a few minutes, or enter the ISBN manually for basic book information.",
        ScanErrorType.DATABASE_ERROR: "Try again in a moment. If the problem persists, please contact support.",
        ScanErrorType.BARCODE_DETECTION_ERROR: "Ensure good lighting and hold the barcode steady, or try uploading a clearer image.",
        ScanErrorType.FILE_FORMAT_ERROR: "Select a JPEG, PNG, or WebP image file.",
        ScanErrorType.FILE_SIZE_ERROR: "Reduce the image size or select a different image.",
        ScanErrorType.DUPLICATE_ERROR: "This book is already in your collection. You can view it in your book list.",
        ScanErrorType.UNKNOWN_ERROR: "Please try again or contact support if the problem persists."
    }
    
    return action_map.get(error_type, "Please try again or contact support.")


def handle_camera_permission_error(error_details: str) -> ScanError:
    """
    Handle camera permission errors with appropriate fallback options.
    
    Args:
        error_details: Technical details about the permission error
    
    Returns:
        ScanError with camera permission handling
    """
    return create_scan_error(
        error_type=ScanErrorType.CAMERA_PERMISSION_ERROR,
        severity=ScanErrorSeverity.MEDIUM,
        message=f"Camera permission denied: {error_details}",
        show_file_fallback=True,
        show_manual_entry=True,
        technical_details=error_details
    )


def handle_camera_not_found_error(error_details: str) -> ScanError:
    """
    Handle camera not found errors with file upload fallback.
    
    Args:
        error_details: Technical details about the camera error
    
    Returns:
        ScanError with camera not found handling
    """
    return create_scan_error(
        error_type=ScanErrorType.CAMERA_NOT_FOUND_ERROR,
        severity=ScanErrorSeverity.MEDIUM,
        message=f"No camera found: {error_details}",
        show_file_fallback=True,
        show_manual_entry=True,
        technical_details=error_details
    )


def handle_network_error(error_details: str, is_retryable: bool = True) -> ScanError:
    """
    Handle network errors with existing fallback mechanisms.
    
    Args:
        error_details: Technical details about the network error
        is_retryable: Whether the user should retry the operation
    
    Returns:
        ScanError with network error handling
    """
    return create_scan_error(
        error_type=ScanErrorType.NETWORK_ERROR,
        severity=ScanErrorSeverity.MEDIUM,
        message=f"Network error: {error_details}",
        show_retry=is_retryable,
        show_manual_entry=True,
        technical_details=error_details
    )


def handle_database_error(error_details: str, is_retryable: bool = True) -> ScanError:
    """
    Handle database errors with retry options.
    
    Args:
        error_details: Technical details about the database error
        is_retryable: Whether the user should retry the operation
    
    Returns:
        ScanError with database error handling
    """
    return create_scan_error(
        error_type=ScanErrorType.DATABASE_ERROR,
        severity=ScanErrorSeverity.HIGH,
        message=f"Database error: {error_details}",
        show_retry=is_retryable,
        show_manual_entry=True,
        technical_details=error_details
    )


def handle_barcode_detection_error(error_details: str, scan_type: str) -> ScanError:
    """
    Handle barcode detection errors with clear messaging.
    
    Args:
        error_details: Technical details about the detection error
        scan_type: Type of scan that failed ('camera' or 'file')
    
    Returns:
        ScanError with barcode detection error handling
    """
    show_file_fallback = scan_type == "camera"
    
    return create_scan_error(
        error_type=ScanErrorType.BARCODE_DETECTION_ERROR,
        severity=ScanErrorSeverity.LOW,
        message=f"Barcode detection failed ({scan_type}): {error_details}",
        show_retry=True,
        show_file_fallback=show_file_fallback,
        show_manual_entry=True,
        technical_details=error_details
    )
def validate_barcode_result(scanned_text: str) -> Tuple[bool, Optional[str], Optional[ScanError]]:
    """
    Validate that scanned text is a valid ISBN with enhanced error handling.

    This function validates the scanned barcode text to ensure it represents
    a valid ISBN that can be processed by the book management system.

    Args:
        scanned_text: The text extracted from the scanned barcode

    Returns:
        Tuple of (is_valid, normalized_isbn, scan_error)
        - is_valid: True if the scanned text is a valid ISBN
        - normalized_isbn: Normalized ISBN if valid, None if invalid
        - scan_error: ScanError object if validation fails, None if valid

    Examples:
        >>> validate_barcode_result("9781234567890")
        (True, "9781234567890", None)

        >>> validate_barcode_result("invalid")
        (False, None, ScanError(...))

        >>> validate_barcode_result("")
        (False, None, ScanError(...))
    """
    if not scanned_text:
        error = create_scan_error(
            error_type=ScanErrorType.VALIDATION_ERROR,
            severity=ScanErrorSeverity.LOW,
            message="Scanned text cannot be empty",
            user_message="No barcode data was received. Please try scanning again.",
            show_retry=True,
            show_manual_entry=True
        )
        return False, None, error

    if not isinstance(scanned_text, str):
        error = create_scan_error(
            error_type=ScanErrorType.VALIDATION_ERROR,
            severity=ScanErrorSeverity.LOW,
            message="Scanned text must be a string",
            user_message="Invalid barcode data format. Please try scanning again.",
            show_retry=True,
            show_manual_entry=True
        )
        return False, None, error

    # Clean and validate the scanned text as an ISBN
    try:
        is_valid, normalized_isbn, validation_error = validate_isbn(scanned_text)

        if not is_valid:
            logger.warning("Invalid ISBN scanned: %s - %s", scanned_text, validation_error)
            error = create_scan_error(
                error_type=ScanErrorType.VALIDATION_ERROR,
                severity=ScanErrorSeverity.LOW,
                message=f"Invalid ISBN: {validation_error}",
                user_message=f"The scanned barcode is not a valid ISBN: {validation_error}",
                show_retry=True,
                show_manual_entry=True,
                technical_details=validation_error
            )
            return False, None, error

        logger.info("Valid ISBN scanned: %s -> %s", scanned_text, normalized_isbn)
        return True, normalized_isbn, None

    except Exception as e:
        error_msg = f"Error validating scanned barcode: {str(e)}"
        logger.error(error_msg)
        error = create_scan_error(
            error_type=ScanErrorType.UNKNOWN_ERROR,
            severity=ScanErrorSeverity.MEDIUM,
            message=error_msg,
            user_message="An unexpected error occurred while validating the barcode.",
            show_retry=True,
            show_manual_entry=True,
            technical_details=str(e)
        )
        return False, None, error


def process_scanned_barcode(
    scanned_text: str, scan_type: str
) -> Tuple[Optional[Book], Optional[str], bool, Optional[ScanError]]:
    """
    Process a scanned barcode result and create book record with comprehensive error handling.

    This function takes the scanned barcode text, validates it as an ISBN,
    and uses the existing book service to retrieve metadata and store the book.
    It integrates with the existing Google Books API service and database operations
    with enhanced error handling for all failure scenarios.

    Args:
        scanned_text: The text extracted from barcode scanning
        scan_type: Type of scan performed ('camera' or 'file')

    Returns:
        Tuple of (book_object, error_message, should_retry_later, scan_error)
        - book_object: Book instance if successful, None if failed
        - error_message: Error message if failed, warning if fallback used, None if successful
        - should_retry_later: True if user should try again later for better data
        - scan_error: ScanError object for structured error handling, None if successful

    Examples:
        >>> process_scanned_barcode("9781234567890", "camera")
        (<Book 9781234567890: Example Title>, None, False, None)

        >>> process_scanned_barcode("invalid", "camera")
        (None, "Invalid ISBN checksum", False, ScanError(...))
    """
    if not scanned_text:
        error = create_scan_error(
            error_type=ScanErrorType.VALIDATION_ERROR,
            severity=ScanErrorSeverity.LOW,
            message="Scanned text cannot be empty",
            show_retry=True,
            show_manual_entry=True
        )
        return None, "Scanned text cannot be empty", False, error

    if not scan_type:
        scan_type = "unknown"

    # Validate scan type
    if scan_type not in ["camera", "file", "unknown"]:
        logger.warning("Unknown scan type: %s, defaulting to 'unknown'", scan_type)
        scan_type = "unknown"

    logger.info("Processing scanned barcode: %s (type: %s)", scanned_text, scan_type)

    # Step 1: Validate the scanned text as an ISBN
    is_valid, normalized_isbn, validation_error = validate_barcode_result(scanned_text)
    if not is_valid or not normalized_isbn:
        return None, validation_error.message if validation_error else "Validation failed", False, validation_error

    # Step 2: Use existing book service to process and store the book
    try:
        book, error_message, should_retry_later = (
            process_and_store_book_with_retry_option(normalized_isbn)
        )

        if book:
            # Log successful processing with scan type for analytics
            logger.info(
                "Successfully processed scanned book: %s (ISBN: %s, scan_type: %s)",
                book.title, book.isbn, scan_type
            )

            # Return success with any warning message from fallback data
            return book, error_message, should_retry_later, None

        # Log processing failure and determine error type
        logger.error(
            "Failed to process scanned barcode: %s (scan_type: %s) - %s",
            scanned_text, scan_type, error_message
        )

        # Categorize the error for better handling
        scan_error = _categorize_processing_error(error_message or "Unknown error", should_retry_later)
        return None, error_message, should_retry_later, scan_error

    except Exception as e:
        error_msg = f"Unexpected error processing scanned barcode: {str(e)}"
        logger.error(error_msg)
        
        # Create a generic error for unexpected exceptions
        scan_error = create_scan_error(
            error_type=ScanErrorType.UNKNOWN_ERROR,
            severity=ScanErrorSeverity.HIGH,
            message=error_msg,
            show_retry=True,
            show_manual_entry=True,
            technical_details=str(e)
        )
        return None, error_msg, False, scan_error


def _categorize_processing_error(error_message: str, should_retry_later: bool) -> ScanError:
    """
    Categorize processing errors into appropriate ScanError types.
    
    Args:
        error_message: The error message from book processing
        should_retry_later: Whether the user should retry later
    
    Returns:
        ScanError with appropriate categorization
    """
    error_lower = error_message.lower() if error_message else ""
    
    # Check for duplicate errors
    if "already exists" in error_lower or "duplicate" in error_lower:
        return create_scan_error(
            error_type=ScanErrorType.DUPLICATE_ERROR,
            severity=ScanErrorSeverity.LOW,
            message=error_message,
            show_manual_entry=False  # No need for manual entry if duplicate
        )
    
    # Check for network/API errors
    if any(keyword in error_lower for keyword in ["network", "connection", "timeout", "unavailable", "api"]):
        return handle_network_error(error_message, should_retry_later)
    
    # Check for database errors
    if any(keyword in error_lower for keyword in ["database", "save", "storage", "commit"]):
        return handle_database_error(error_message, should_retry_later)
    
    # Default to unknown error
    return create_scan_error(
        error_type=ScanErrorType.UNKNOWN_ERROR,
        severity=ScanErrorSeverity.MEDIUM,
        message=error_message,
        show_retry=should_retry_later,
        show_manual_entry=True
    )


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
    scan_error: ScanError,
) -> None:
    """
    Log scanning errors for debugging and analytics with enhanced error information.
    
    This function provides centralized error logging for barcode scanning
    operations while maintaining user privacy by not logging sensitive data.

    Args:
        scanned_text: The scanned text (will be truncated for privacy)
        scan_type: Type of scan performed ('camera' or 'file')
        scan_error: ScanError object with structured error information
    """
    # Truncate scanned text for privacy (keep first 4 and last 4 characters)
    if len(scanned_text) > 8:
        truncated_text = f"{scanned_text[:4]}...{scanned_text[-4:]}"
    else:
        truncated_text = "***"

    logger.error(
        "Barcode scanning error - Type: %s, Severity: %s, Scan method: %s, "
        "Text: %s, Error: %s, Technical: %s",
        scan_error.error_type.value,
        scan_error.severity.value,
        scan_type,
        truncated_text,
        scan_error.message,
        scan_error.technical_details or "None"
    )


def get_scanning_statistics() -> Dict[str, Any]:
    """
    Get basic scanning statistics for monitoring with error tracking.
    
    This function provides basic statistics about scanning operations
    for monitoring and debugging purposes. It does not access the database
    directly but provides information about the current session.

    Returns:
        Dictionary with basic scanning statistics and error handling info
    """
    return {
        "service_status": "active",
        "supported_scan_types": ["camera", "file"],
        "validation_enabled": True,
        "integration_services": ["isbn_service", "book_service", "google_books_api"],
        "error_handling": {
            "structured_errors": True,
            "fallback_options": ["file_upload", "manual_entry"],
            "retry_support": True,
            "severity_levels": [level.value for level in ScanErrorSeverity]
        },
        "supported_error_types": [error_type.value for error_type in ScanErrorType]
    }


def validate_file_for_scanning(file_data: Dict[str, Any]) -> Tuple[bool, Optional[ScanError]]:
    """
    Validate uploaded file for barcode scanning.
    
    Args:
        file_data: Dictionary containing file information (type, size, name)
    
    Returns:
        Tuple of (is_valid, scan_error)
        - is_valid: True if file is valid for scanning
        - scan_error: ScanError if validation fails, None if valid
    """
    if not file_data:
        return False, create_scan_error(
            error_type=ScanErrorType.FILE_FORMAT_ERROR,
            severity=ScanErrorSeverity.LOW,
            message="No file data provided",
            show_retry=True,
            show_manual_entry=True
        )
    
    # Check file type
    file_type = file_data.get('type', '').lower()
    valid_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    
    if file_type not in valid_types:
        return False, create_scan_error(
            error_type=ScanErrorType.FILE_FORMAT_ERROR,
            severity=ScanErrorSeverity.LOW,
            message=f"Invalid file type: {file_type}",
            user_message="Please select a valid image file (JPEG, PNG, or WebP).",
            show_retry=True,
            show_manual_entry=True,
            technical_details=f"Received type: {file_type}, Expected: {', '.join(valid_types)}"
        )
    
    # Check file size (max 10MB)
    file_size = file_data.get('size', 0)
    max_size = 10 * 1024 * 1024  # 10MB
    
    if file_size > max_size:
        return False, create_scan_error(
            error_type=ScanErrorType.FILE_SIZE_ERROR,
            severity=ScanErrorSeverity.LOW,
            message=f"File too large: {file_size} bytes (max: {max_size})",
            user_message=f"File size too large ({file_size // (1024*1024)}MB). Please select an image smaller than 10MB.",
            show_retry=True,
            show_manual_entry=True,
            technical_details=f"File size: {file_size} bytes, Max allowed: {max_size} bytes"
        )
    
    return True, None


def get_error_recovery_options(scan_error: ScanError) -> Dict[str, Any]:
    """
    Get recovery options for a specific scan error.
    
    Args:
        scan_error: ScanError object
    
    Returns:
        Dictionary with recovery options and UI guidance
    """
    return {
        "show_retry_button": scan_error.show_retry,
        "show_file_fallback": scan_error.show_file_fallback,
        "show_manual_entry": scan_error.show_manual_entry,
        "suggested_action": scan_error.suggested_action,
        "user_message": scan_error.user_message,
        "severity": scan_error.severity.value,
        "error_type": scan_error.error_type.value,
        "can_continue": scan_error.severity in [ScanErrorSeverity.LOW, ScanErrorSeverity.MEDIUM]
    }
