"""
Barcode service for processing scanned barcode results.

This module provides functions for validating and processing barcode scan results,
integrating with existing book services to create book records from scanned ISBNs.
"""

import logging
from typing import Optional, Tuple
from app.models.book import Book
from app.services.book_service import process_and_store_book_with_retry_option
from app.services.isbn_service import validate_isbn

# Configure logging
logger = logging.getLogger(__name__)


def validate_barcode_result(scanned_text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that scanned text is a valid ISBN.
    
    Args:
        scanned_text: The text extracted from barcode
        
    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, None)
        If invalid: (False, error_message)
    """
    if not scanned_text or not scanned_text.strip():
        return False, "Scanned text is empty"
    
    # ISBN validation service
    is_valid, normalized_isbn, validation_error = validate_isbn(scanned_text.strip())
    
    if not is_valid:
        return False, f"Invalid ISBN format: {validation_error}"
    
    logger.info("Barcode validation successful: %s -> %s", scanned_text, normalized_isbn)
    return True, None


def process_scanned_barcode(
    scanned_text: str, 
    scan_type: str
) -> Tuple[Optional[Book], Optional[str], bool]:
    """
    Process a scanned barcode result and create book record.
    
    Args:
        scanned_text: The text extracted from barcode
        scan_type: 'camera' or 'file' for tracking purposes
        
    Returns:
        Tuple of (book_object, error_message, should_retry_later)
        If successful: (Book, None, False) or (Book, warning_message, False)
        If failed: (None, error_message, should_retry_later)
    """
    # Step 1: Validate the scanned text as an ISBN
    is_valid, validation_error = validate_barcode_result(scanned_text)
    if not is_valid:
        logger.warning("Barcode validation failed: %s", validation_error)
        return None, validation_error, False
    
    # Step 2: Use existing book service to process and store the book
    try:
        book, error_or_warning, should_retry_later = process_and_store_book_with_retry_option(
            scanned_text.strip()
        )
        
        if book:
            return book, error_or_warning, should_retry_later
        else:
            logger.error("Failed to process scanned barcode: %s", error_or_warning)
            return None, error_or_warning, should_retry_later
            
    except Exception as e:
        logger.error("Unexpected error processing scanned barcode: %s", str(e), exc_info=True)
        return None, f"An unexpected error occurred while processing the scanned barcode: {str(e)}", False