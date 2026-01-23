"""Book model for the book management application."""

from datetime import datetime, date, timezone
from typing import Optional, List
import json
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Index
from sqlalchemy.ext.hybrid import hybrid_property

# Import db with proper typing
from app import db  # type: ignore


class Book(db.Model):  # type: ignore
    """Book model representing a book in the collection."""

    __tablename__ = "books"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)  # type: ignore

    # ISBN - normalized to ISBN-13 format, unique constraint
    isbn = Column(String(13), unique=True, nullable=False, index=True)  # type: ignore

    # Book metadata
    title = Column(String(255), nullable=True)  # type: ignore
    authors = Column(Text, nullable=True)  # type: ignore  # Stored as JSON array
    publisher = Column(String(255), nullable=True)  # type: ignore
    published_date = Column(Date, nullable=True)  # type: ignore  # DATE type as specified
    description = Column(Text, nullable=True)  # type: ignore

    # Image URLs - TEXT type for long URLs as specified
    thumbnail_url = Column(Text, nullable=True)  # type: ignore
    cover_image_url = Column(Text, nullable=True)  # type: ignore

    # Timestamps
    created_at = Column(  # type: ignore
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(  # type: ignore
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
        self.isbn = isbn  # type: ignore
        self.title = title  # type: ignore
        self.authors_list = authors or []  # type: ignore[method-assign]
        self.publisher = publisher  # type: ignore
        self.published_date = published_date  # type: ignore
        self.description = description  # type: ignore
        self.thumbnail_url = thumbnail_url  # type: ignore
        self.cover_image_url = cover_image_url  # type: ignore

    @hybrid_property
    def authors_list(self) -> List[str]:
        """Get authors as a list of strings."""
        if self.authors:
            try:
                return json.loads(self.authors)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @authors_list.setter  # type: ignore[no-redef]
    def authors_list(self, value: Optional[List[str]]):
        """Set authors from a list of strings."""
        if value:
            self.authors = json.dumps(value, ensure_ascii=False)  # type: ignore
        else:
            self.authors = None  # type: ignore

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
