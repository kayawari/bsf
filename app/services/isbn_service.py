"""
ISBN validation and processing service.

This module provides functions for validating ISBN-10 and ISBN-13 formats,
normalizing ISBNs, and checking for duplicates in the database.
"""

import re
from typing import Optional, Tuple
from app.models.book import Book


def clean_isbn(isbn: str) -> str:
    """
    Clean ISBN by removing hyphens, spaces, and converting to uppercase.

    Args:
        isbn: Raw ISBN string

    Returns:
        Cleaned ISBN string with only digits and X
    """
    if not isbn:
        return ""

    # Remove hyphens, spaces, and convert to uppercase
    cleaned = re.sub(r"[-\s]", "", isbn.strip().upper())
    return cleaned


def validate_isbn10(isbn: str) -> bool:
    """
    Validate ISBN-10 format with checksum verification.

    Args:
        isbn: ISBN-10 string (should be cleaned)

    Returns:
        True if valid ISBN-10, False otherwise
    """
    if not isbn or len(isbn) != 10:
        return False

    # Check format: 9 digits followed by digit or X
    if not re.match(r"^\d{9}[\dX]$", isbn):
        return False

    # Calculate checksum
    checksum = 0
    for i in range(9):
        checksum += int(isbn[i]) * (10 - i)

    # Handle check digit (X = 10)
    check_digit = 10 if isbn[9] == "X" else int(isbn[9])
    checksum += check_digit

    # Valid if checksum is divisible by 11
    return checksum % 11 == 0


def validate_isbn13(isbn: str) -> bool:
    """
    Validate ISBN-13 format with checksum verification.

    Args:
        isbn: ISBN-13 string (should be cleaned)

    Returns:
        True if valid ISBN-13, False otherwise
    """
    if not isbn or len(isbn) != 13:
        return False

    # Check format: 13 digits starting with 978 or 979
    # about isbn: https://www.isbn-international.org/
    if not re.match(r"^(978|979)\d{10}$", isbn):
        return False

    # Calculate checksum using alternating weights of 1 and 3
    checksum = 0
    for i in range(12):
        weight = 1 if i % 2 == 0 else 3
        checksum += int(isbn[i]) * weight

    # Calculate check digit
    check_digit = (10 - (checksum % 10)) % 10

    # Valid if calculated check digit matches the last digit
    return check_digit == int(isbn[12])


def isbn10_to_isbn13(isbn10: str) -> str:
    """
    Convert ISBN-10 to ISBN-13 format.
    TODOあり

    Args:
        isbn10: Valid ISBN-10 string (should be cleaned and validated)

    Returns:
        ISBN-13 string

    Raises:
        ValueError: If ISBN-10 is invalid
    """
    if not validate_isbn10(isbn10):
        raise ValueError(f"Invalid ISBN-10: {isbn10}")

    # Remove check digit and add 978 prefix
    # TODO: isbn13は978以外に979も使われるパターンが国外にあるらしいので、そのパターンを気にすると厳密になる
    isbn12 = "978" + isbn10[:9]

    # Calculate new check digit for ISBN-13
    checksum = 0
    for i in range(12):
        weight = 1 if i % 2 == 0 else 3
        checksum += int(isbn12[i]) * weight

    check_digit = (10 - (checksum % 10)) % 10

    return isbn12 + str(check_digit)


def normalize_isbn(isbn: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize ISBN to ISBN-13 format with validation.

    Args:
        isbn: Raw ISBN string

    Returns:
        Tuple of (normalized_isbn13, error_message)
        If successful: (isbn13_string, None)
        If failed: (None, error_message)
    """
    if not isbn:
        return None, "ISBN cannot be empty"

    cleaned = clean_isbn(isbn)

    if not cleaned:
        return None, "Invalid ISBN format"

    # Try ISBN-13 first
    if len(cleaned) == 13:
        if validate_isbn13(cleaned):
            return cleaned, None
        else:
            return None, "Invalid ISBN-13 checksum"

    # Try ISBN-10
    elif len(cleaned) == 10:
        if validate_isbn10(cleaned):
            try:
                isbn13 = isbn10_to_isbn13(cleaned)
                return isbn13, None
            except ValueError as e:
                return None, str(e)
        else:
            return None, "Invalid ISBN-10 checksum"

    else:
        return None, f"Invalid ISBN length: {len(cleaned)}. Must be 10 or 13 characters"


def validate_isbn(isbn: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and normalize ISBN.

    Args:
        isbn: Raw ISBN string

    Returns:
        Tuple of (is_valid, normalized_isbn13, error_message)
    """
    normalized, error = normalize_isbn(isbn)
    if normalized:
        return True, normalized, None
    else:
        return False, None, error


def check_isbn_exists(isbn: str) -> bool:
    """
    Check if ISBN already exists in the database.

    Args:
        isbn: ISBN string (should be normalized to ISBN-13)

    Returns:
        True if ISBN exists, False otherwise
    """
    if not isbn:
        return False

    # Query database for existing book with this ISBN
    existing_book = Book.query.filter_by(isbn=isbn).first()
    return existing_book is not None


def is_duplicate_isbn(isbn: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if ISBN is a duplicate after validation and normalization.

    Args:
        isbn: Raw ISBN string

    Returns:
        Tuple of (is_duplicate, normalized_isbn13, error_message)
        - If invalid ISBN: (False, None, error_message)
        - If valid but duplicate: (True, normalized_isbn13, None)
        - If valid and not duplicate: (False, normalized_isbn13, None)
    """
    # First validate and normalize the ISBN
    is_valid, normalized, error = validate_isbn(isbn)

    if not is_valid:
        return False, None, error

    # Check if it exists in database
    if check_isbn_exists(normalized):
        return True, normalized, None

    return False, normalized, None
