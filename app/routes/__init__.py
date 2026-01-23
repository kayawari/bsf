"""
Routes package for organizing Flask blueprints.
"""

from .health import health_bp
from .book import book_bp
from .scan import scan_bp

__all__ = ["health_bp", "book_bp", "scan_bp"]