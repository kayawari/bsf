"""Book model for the book management application."""

from datetime import datetime, date, timezone
from typing import Optional, List
import json
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Index
from sqlalchemy.ext.hybrid import hybrid_property
from app import db


class Book(db.Model):
    """Book model representing a book in the collection."""

    __tablename__ = "books"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ISBN - normalized to ISBN-13 format, unique constraint
    isbn = Column(String(13), unique=True, nullable=False, index=True)

    # Book metadata
    title = Column(String(255), nullable=True)
    authors = Column(Text, nullable=True)  # Stored as JSON array
    publisher = Column(String(255), nullable=True)
    published_date = Column(Date, nullable=True)  # DATE type as specified
    description = Column(Text, nullable=True)

    # Image URLs - TEXT type for long URLs as specified
    thumbnail_url = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_books_isbn", "isbn"),
        Index("idx_books_title", "title"),
        Index("idx_books_created_at", "created_at"),
    )

    def __init__(
        self,
        isbn: str,
        title: Optional[str] = None,
        authors: Optional[List[str]] = None,
        publisher: Optional[str] = None,
        published_date: Optional[date] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        cover_image_url: Optional[str] = None,
    ):
        """Initialize a new Book instance."""
        self.isbn = isbn
        self.title = title
        self.authors_list = authors or []
        self.publisher = publisher
        self.published_date = published_date
        self.description = description
        self.thumbnail_url = thumbnail_url
        self.cover_image_url = cover_image_url

    @hybrid_property
    def authors_list(self) -> List[str]:
        """Get authors as a list of strings."""
        if self.authors:
            try:
                return json.loads(self.authors)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @authors_list.setter
    def authors_list(self, value: Optional[List[str]]):
        """Set authors from a list of strings."""
        if value:
            self.authors = json.dumps(value, ensure_ascii=False)
        else:
            self.authors = None

    @property
    def authors_display(self) -> str:
        """Get authors as a comma-separated string for display."""
        authors = self.authors_list
        if authors:
            return ", ".join(authors)
        return ""

    def to_dict(self) -> dict:
        """Convert book to dictionary representation."""
        return {
            "id": self.id,
            "isbn": self.isbn,
            "title": self.title,
            "authors": self.authors_list,
            "authors_display": self.authors_display,
            "publisher": self.publisher,
            "published_date": self.published_date.isoformat()
            if self.published_date
            else None,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "cover_image_url": self.cover_image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """String representation of the Book."""
        return f"<Book {self.isbn}: {self.title}>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"{self.title} by {self.authors_display}"
            if self.title
            else f"Book {self.isbn}"
        )
