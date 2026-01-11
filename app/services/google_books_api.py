"""
Google Books API client for retrieving book metadata.

This module provides functions for querying the Google Books API,
handling responses, and extracting book information.
"""

import time
import requests
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Google Books API configuration
GOOGLE_BOOKS_API_BASE_URL = "https://www.googleapis.com/books/v1/volumes"
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
RATE_LIMIT_DELAY = 0.1  # seconds between requests


class GoogleBooksAPIError(Exception):
    """Custom exception for Google Books API errors."""
    pass


class RateLimitError(GoogleBooksAPIError):
    """Exception raised when API rate limit is exceeded."""
    pass


class APIClient:
    """Google Books API client with rate limiting and retry logic."""
    
    def __init__(self):
        """Initialize the API client."""
        self.session = requests.Session()
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Implement basic rate limiting."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < RATE_LIMIT_DELAY:
            sleep_time = RATE_LIMIT_DELAY - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict[str, Any]) -> requests.Response:
        """
        Make HTTP request with rate limiting and error handling.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Returns:
            Response object
            
        Raises:
            GoogleBooksAPIError: For API-related errors
            RateLimitError: When rate limit is exceeded
        """
        self._rate_limit()
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=DEFAULT_TIMEOUT,
                headers={'User-Agent': 'BookManager/1.0'}
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
            
            # Handle other HTTP errors
            if response.status_code >= 400:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                raise GoogleBooksAPIError(f"API request failed with status {response.status_code}")
            
            return response
            
        except requests.exceptions.Timeout:
            raise GoogleBooksAPIError("Request timeout")
        except requests.exceptions.ConnectionError:
            raise GoogleBooksAPIError("Connection error")
        except requests.exceptions.RequestException as e:
            raise GoogleBooksAPIError(f"Request failed: {str(e)}")
    
    def search_by_isbn(self, isbn: str) -> Dict[str, Any]:
        """
        Search for a book by ISBN.
        
        Args:
            isbn: ISBN string (10 or 13 digits)
            
        Returns:
            API response as dictionary
            
        Raises:
            GoogleBooksAPIError: For API-related errors
        """
        if not isbn:
            raise GoogleBooksAPIError("ISBN cannot be empty")
        
        params = {
            'q': f'isbn:{isbn}',
            'maxResults': 1,
            'printType': 'books'
        }
        
        response = self._make_request(GOOGLE_BOOKS_API_BASE_URL, params)
        return response.json()


def search_book_by_isbn_with_retry(isbn: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Search for book by ISBN with retry logic.
    
    Args:
        isbn: ISBN string
        
    Returns:
        Tuple of (api_response_dict, error_message)
        If successful: (response_dict, None)
        If failed: (None, error_message)
    """
    if not isbn:
        return None, "ISBN cannot be empty"
    
    client = APIClient()
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.search_by_isbn(isbn)
            logger.info(f"Successfully retrieved book data for ISBN {isbn}")
            return response, None
            
        except RateLimitError:
            if attempt < MAX_RETRIES - 1:
                # Exponential backoff for rate limiting
                sleep_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Rate limit exceeded, retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                continue
            else:
                error_msg = "API rate limit exceeded after multiple retries"
                logger.error(error_msg)
                return None, error_msg
                
        except GoogleBooksAPIError as e:
            if attempt < MAX_RETRIES - 1:
                sleep_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"API request failed (attempt {attempt + 1}), retrying in {sleep_time} seconds: {str(e)}")
                time.sleep(sleep_time)
                continue
            else:
                error_msg = f"API request failed after {MAX_RETRIES} attempts: {str(e)}"
                logger.error(error_msg)
                return None, error_msg
    
    return None, "Unexpected error in retry logic"


def extract_book_metadata(api_response: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Extract book metadata from Google Books API response.
    
    Args:
        api_response: Raw API response dictionary
        
    Returns:
        Tuple of (book_metadata_dict, error_message)
        If successful: (metadata_dict, None)
        If failed: (None, error_message)
    """
    if not api_response:
        return None, "API response is empty"
    
    try:
        # Check if any books were found
        total_items = api_response.get('totalItems', 0)
        if total_items == 0:
            return None, "No books found for this ISBN"
        
        # Get the first book item
        items = api_response.get('items', [])
        if not items:
            return None, "No book items in API response"
        
        book_item = items[0]
        volume_info = book_item.get('volumeInfo', {})
        
        # Extract basic information
        title = volume_info.get('title')
        authors = volume_info.get('authors', [])
        publisher = volume_info.get('publisher')
        published_date = volume_info.get('publishedDate')
        description = volume_info.get('description')
        
        # Extract image links
        image_links = volume_info.get('imageLinks', {})
        thumbnail_url = image_links.get('thumbnail')
        
        # Try to get higher resolution cover image
        cover_image_url = (
            image_links.get('large') or 
            image_links.get('medium') or 
            image_links.get('small') or 
            thumbnail_url
        )
        
        # Parse published date (can be year only, year-month, or full date)
        parsed_date = None
        if published_date:
            try:
                # Try different date formats
                if len(published_date) == 4:  # Year only
                    parsed_date = datetime.strptime(published_date, '%Y').date()
                elif len(published_date) == 7:  # Year-month
                    parsed_date = datetime.strptime(published_date, '%Y-%m').date()
                else:  # Full date
                    parsed_date = datetime.strptime(published_date, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Could not parse published date: {published_date}")
                parsed_date = None
        
        # Build metadata dictionary
        metadata = {
            'title': title,
            'authors': authors,
            'publisher': publisher,
            'published_date': parsed_date,
            'description': description,
            'thumbnail_url': thumbnail_url,
            'cover_image_url': cover_image_url,
        }
        
        logger.info(f"Successfully extracted metadata for book: {title}")
        return metadata, None
        
    except Exception as e:
        error_msg = f"Error extracting book metadata: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def get_book_metadata_by_isbn(isbn: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Get book metadata by ISBN - main public function.
    
    Args:
        isbn: ISBN string
        
    Returns:
        Tuple of (book_metadata_dict, error_message)
        If successful: (metadata_dict, None)
        If failed: (None, error_message)
    """
    if not isbn:
        return None, "ISBN cannot be empty"
    
    # Search for book by ISBN
    api_response, search_error = search_book_by_isbn_with_retry(isbn)
    if search_error:
        return None, search_error
    
    # Extract metadata from response
    metadata, extract_error = extract_book_metadata(api_response)
    if extract_error:
        return None, extract_error
    
    return metadata, None