"""
Book service for processing and storing book data.

This module provides functions for processing Google Books API responses,
creating book records, and managing book data storage with graceful
handling of external service failures.
"""

import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import date
from app import db
from app.models.book import Book
from app.services.google_books_api import get_book_metadata_with_fallback
from app.services.isbn_service import validate_isbn, is_duplicate_isbn

# Configure logging
logger = logging.getLogger(__name__)


def process_and_store_book(isbn: str) -> Tuple[Optional[Book], Optional[str]]:
    """
    Process ISBN, fetch book data from API, and store in database with fallback handling.

    Args:
        isbn: Raw ISBN string

    Returns:
        Tuple of (book_object, error_message)
        If successful: (Book, None)
        If failed: (None, error_message)
    """
    if not isbn:
        return None, "ISBN cannot be empty"

    # Step 1: Validate and normalize ISBN
    is_valid, normalized_isbn, validation_error = validate_isbn(isbn)
    if not is_valid or normalized_isbn is None:
        return None, validation_error or "Invalid ISBN format"

    # Step 2: Check for duplicates
    is_duplicate, _, duplicate_error = is_duplicate_isbn(isbn)
    if duplicate_error:
        return None, duplicate_error
    if is_duplicate:
        return (
            None,
            f"Book with ISBN {normalized_isbn} already exists in your collection",
        )

    # Step 3: Fetch book metadata from Google Books API with fallback
    metadata, is_fallback, warning_message = get_book_metadata_with_fallback(
        normalized_isbn
    )

    # Step 4: Process and store book data
    book, storage_error = create_book_from_metadata(normalized_isbn, metadata)
    if storage_error:
        return None, storage_error

    # At this point, book should not be None since storage_error is None
    assert book is not None, "Book should not be None when storage_error is None"

    # Log success with appropriate message
    if is_fallback:
        logger.warning(
            f"Stored book with fallback data: {book.title} (ISBN: {normalized_isbn}) - {warning_message}"
        )
    else:
        logger.info(
            f"Successfully processed and stored book: {book.title} (ISBN: {normalized_isbn})"
        )

    return book, None


def process_and_store_book_with_retry_option(
    isbn: str,
) -> Tuple[Optional[Book], Optional[str], bool]:
    """
    Process ISBN with fallback handling and return retry recommendation.

    Args:
        isbn: Raw ISBN string

    Returns:
        Tuple of (book_object, error_message, should_retry_later)
        - book_object: Book if successful, None if failed
        - error_message: Error message if failed, None if successful
        - should_retry_later: True if user should try again later for better data
    """
    if not isbn:
        return None, "ISBN cannot be empty", False

    # Step 1: Validate and normalize ISBN
    is_valid, normalized_isbn, validation_error = validate_isbn(isbn)
    if not is_valid or normalized_isbn is None:
        return None, validation_error or "Invalid ISBN format", False

    # Step 2: Check for duplicates
    is_duplicate, _, duplicate_error = is_duplicate_isbn(isbn)
    if duplicate_error:
        return None, duplicate_error, False
    if is_duplicate:
        return (
            None,
            f"Book with ISBN {normalized_isbn} already exists in your collection",
            False,
        )

    # Step 3: Fetch book metadata from Google Books API with fallback
    metadata, is_fallback, warning_message = get_book_metadata_with_fallback(
        normalized_isbn
    )

    # Step 4: Process and store book data
    book, storage_error = create_book_from_metadata(normalized_isbn, metadata)
    if storage_error:
        return None, storage_error, False

    # At this point, book should not be None since storage_error is None
    assert book is not None, "Book should not be None when storage_error is None"

    # Determine if user should retry later
    should_retry_later = (
        is_fallback and "unavailable" in (warning_message or "").lower()
    )

    # Log success with appropriate message
    if is_fallback:
        logger.warning(
            f"Stored book with fallback data: {book.title} (ISBN: {normalized_isbn}) - {warning_message}"
        )
    else:
        logger.info(
            f"Successfully processed and stored book: {book.title} (ISBN: {normalized_isbn})"
        )

    return book, warning_message if is_fallback else None, should_retry_later


def create_book_from_metadata(
    isbn: str, metadata: Dict[str, Any]
) -> Tuple[Optional[Book], Optional[str]]:
    """
    Create and save a Book object from API metadata.

    Args:
        isbn: Normalized ISBN-13 string
        metadata: Book metadata dictionary from API

    Returns:
        Tuple of (book_object, error_message)
        If successful: (Book, None)
        If failed: (None, error_message)
    """
    if not isbn:
        return None, "ISBN cannot be empty"

    if not metadata:
        return None, "Metadata cannot be empty"

    try:
        # Extract and validate metadata fields
        title = metadata.get("title")
        authors = metadata.get("authors", [])
        publisher = metadata.get("publisher")
        published_date = metadata.get("published_date")
        description = metadata.get("description")
        thumbnail_url = metadata.get("thumbnail_url")
        cover_image_url = metadata.get("cover_image_url")

        # Handle missing or incomplete data gracefully
        if not title:
            logger.warning(f"No title found for ISBN {isbn}, using placeholder")
            title = f"Unknown Title (ISBN: {isbn})"

        if not authors:
            logger.warning(f"No authors found for ISBN {isbn}")
            authors = []

        # Ensure published_date is a date object or None
        if published_date and not isinstance(published_date, date):
            logger.warning(
                f"Invalid published_date type for ISBN {isbn}: {type(published_date)}"
            )
            published_date = None

        # Create Book object
        book = Book(
            isbn=isbn,
            title=title,
            authors=authors,
            publisher=publisher,
            published_date=published_date,
            description=description,
            thumbnail_url=thumbnail_url,
            cover_image_url=cover_image_url,
        )

        # Save to database with error handling
        try:
            db.session.add(book)
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            error_msg = f"Database error while saving book: {str(db_error)}"
            logger.error(error_msg)
            return None, error_msg

        logger.info(
            f"Successfully created book record: {title} by {', '.join(authors)}"
        )
        return book, None

    except Exception as e:
        # Rollback transaction on error
        try:
            db.session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        error_msg = f"Failed to create book record: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def get_all_books() -> List[Book]:
    """
    Retrieve all books from the database with error handling.

    Returns:
        List of Book objects ordered by creation date (newest first)
    """
    try:
        books = Book.query.order_by(Book.created_at.desc()).all()
        logger.info(f"Retrieved {len(books)} books from database")
        return books
    except Exception as e:
        logger.error(f"Failed to retrieve books: {str(e)}")
        return []


def get_book_by_id(book_id: int) -> Optional[Book]:
    """
    Retrieve a specific book by ID with error handling.

    Args:
        book_id: Book ID

    Returns:
        Book object or None if not found
    """
    if not book_id or book_id <= 0:
        logger.warning(f"Invalid book ID: {book_id}")
        return None

    try:
        book = Book.query.get(book_id)
        if book:
            logger.info(f"Retrieved book: {book.title}")
        else:
            logger.warning(f"Book with ID {book_id} not found")
        return book
    except Exception as e:
        logger.error(f"Failed to retrieve book with ID {book_id}: {str(e)}")
        return None


def get_book_by_isbn(isbn: str) -> Optional[Book]:
    """
    Retrieve a specific book by ISBN with error handling.

    Args:
        isbn: ISBN string (will be normalized)

    Returns:
        Book object or None if not found
    """
    if not isbn:
        return None

    try:
        # Normalize ISBN for consistent lookup
        is_valid, normalized_isbn, _ = validate_isbn(isbn)
        if not is_valid or normalized_isbn is None:
            return None

        book = Book.query.filter_by(isbn=normalized_isbn).first()
        if book:
            logger.info(f"Retrieved book by ISBN: {book.title}")
        else:
            logger.info(f"Book with ISBN {normalized_isbn} not found")
        return book
    except Exception as e:
        logger.error(f"Failed to retrieve book with ISBN {isbn}: {str(e)}")
        return None


def update_book_metadata(
    book_id: int, metadata: Dict[str, Any]
) -> Tuple[Optional[Book], Optional[str]]:
    """
    Update book metadata (useful for refreshing data from API) with error handling.

    Args:
        book_id: Book ID to update
        metadata: New metadata dictionary

    Returns:
        Tuple of (updated_book, error_message)
        If successful: (Book, None)
        If failed: (None, error_message)
    """
    if not book_id or book_id <= 0:
        return None, "Invalid book ID"

    try:
        book = Book.query.get(book_id)
        if not book:
            return None, f"Book with ID {book_id} not found"

        # Update fields if provided in metadata
        if "title" in metadata and metadata["title"]:
            book.title = metadata["title"]

        if "authors" in metadata:
            book.authors_list = metadata["authors"] or []

        if "publisher" in metadata:
            book.publisher = metadata["publisher"]

        if "published_date" in metadata:
            book.published_date = metadata["published_date"]

        if "description" in metadata:
            book.description = metadata["description"]

        if "thumbnail_url" in metadata:
            book.thumbnail_url = metadata["thumbnail_url"]

        if "cover_image_url" in metadata:
            book.cover_image_url = metadata["cover_image_url"]

        # Save changes with error handling
        try:
            db.session.commit()
        except Exception as db_error:
            db.session.rollback()
            error_msg = f"Database error while updating book: {str(db_error)}"
            logger.error(error_msg)
            return None, error_msg

        logger.info(f"Successfully updated book: {book.title}")
        return book, None

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        error_msg = f"Failed to update book: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def refresh_book_from_api(book_id: int) -> Tuple[Optional[Book], Optional[str], bool]:
    """
    Refresh book metadata from Google Books API with fallback handling.

    Args:
        book_id: Book ID to refresh

    Returns:
        Tuple of (updated_book, error_message, is_fallback_data)
        If successful: (Book, None, False)
        If failed: (None, error_message, False)
        If fallback used: (Book, warning_message, True)
    """
    if not book_id or book_id <= 0:
        return None, "Invalid book ID", False

    try:
        book = Book.query.get(book_id)
        if not book:
            return None, f"Book with ID {book_id} not found", False

        # Get fresh metadata from API
        metadata, is_fallback, warning_message = get_book_metadata_with_fallback(
            book.isbn
        )

        # Update book with new metadata
        updated_book, update_error = update_book_metadata(book_id, metadata)
        if update_error:
            return None, update_error, False

        return updated_book, warning_message if is_fallback else None, is_fallback

    except Exception as e:
        error_msg = f"Failed to refresh book from API: {str(e)}"
        logger.error(error_msg)
        return None, error_msg, False
