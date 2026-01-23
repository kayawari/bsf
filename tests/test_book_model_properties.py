"""
Property-based tests for Book model functionality.
"""

from datetime import date, datetime
from hypothesis import given, strategies as st, settings, HealthCheck
from app import create_app, db
from app.models.book import Book


def create_test_app():
    """Create and configure test app."""
    app = create_app('testing')
    return app


class TestBookModelDataPersistence:
    """
    Property-based tests for Book model data persistence.
    Feature: book-management, Property 3: Data Persistence
    """
    
    @given(
        isbn=st.text(min_size=10, max_size=13).filter(lambda x: x.isdigit()),
        title=st.one_of(st.none(), st.text(min_size=1, max_size=255)),
        authors=st.one_of(
            st.none(), 
            st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5)
        ),
        publisher=st.one_of(st.none(), st.text(min_size=1, max_size=255)),
        published_date=st.one_of(
            st.none(),
            st.dates(min_value=date(1000, 1, 1), max_value=date(2030, 12, 31))
        ),
        description=st.one_of(st.none(), st.text(min_size=1, max_size=1000)),
        thumbnail_url=st.one_of(st.none(), st.text(min_size=10, max_size=500)),
        cover_image_url=st.one_of(st.none(), st.text(min_size=10, max_size=500))
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_book_data_persistence_round_trip(self, isbn, title, authors, publisher, 
                                            published_date, description, thumbnail_url, 
                                            cover_image_url):
        """
        **Property 3: Data Persistence**
        *For any* valid ISBN submission, the book information should be immediately 
        persisted to storage and be retrievable afterwards.
        **Validates: Requirements 1.3**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                # Create a book with the generated data
                book = Book(
                    isbn=isbn,
                    title=title,
                    authors=authors,
                    publisher=publisher,
                    published_date=published_date,
                    description=description,
                    thumbnail_url=thumbnail_url,
                    cover_image_url=cover_image_url
                )
                
                # Persist to database
                db.session.add(book)
                db.session.commit()
                
                # Verify the book was persisted by retrieving it
                retrieved_book = Book.query.filter_by(isbn=isbn).first()
                
                # Assert the book was successfully persisted and retrieved
                assert retrieved_book is not None, "Book should be persisted and retrievable"
                
                # Verify all data was persisted correctly
                assert retrieved_book.isbn == isbn
                assert retrieved_book.title == title
                assert retrieved_book.authors_list == (authors or [])
                assert retrieved_book.publisher == publisher
                assert retrieved_book.published_date == published_date
                assert retrieved_book.description == description
                assert retrieved_book.thumbnail_url == thumbnail_url
                assert retrieved_book.cover_image_url == cover_image_url
                
                # Verify timestamps were set
                assert retrieved_book.created_at is not None
                assert retrieved_book.updated_at is not None
                assert isinstance(retrieved_book.created_at, datetime)
                assert isinstance(retrieved_book.updated_at, datetime)
                
                # Verify the book can be retrieved by ID as well
                retrieved_by_id = db.session.get(Book, retrieved_book.id)
                assert retrieved_by_id is not None
                assert retrieved_by_id.isbn == isbn
                
            finally:
                db.drop_all()
    
    @given(
        isbn=st.text(min_size=10, max_size=13).filter(lambda x: x.isdigit()),
        initial_title=st.text(min_size=1, max_size=255),
        title_suffix=st.text(min_size=1, max_size=10)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_book_data_update_persistence(self, isbn, initial_title, title_suffix):
        """
        **Property 3: Data Persistence**
        *For any* book update operation, the changes should be immediately 
        persisted to storage and be retrievable afterwards.
        **Validates: Requirements 1.3**
        """
        # Ensure titles are different by appending suffix
        updated_title = initial_title + title_suffix
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                # Create and persist initial book
                book = Book(isbn=isbn, title=initial_title)
                db.session.add(book)
                db.session.commit()
                
                # Get the book ID for later retrieval
                book_id = book.id
                initial_updated_at = book.updated_at
                
                # Update the book
                book.title = updated_title
                db.session.commit()
                
                # Retrieve the book again to verify persistence
                retrieved_book = db.session.get(Book, book_id)
                
                # Verify the update was persisted
                assert retrieved_book is not None
                assert retrieved_book.title == updated_title
                assert retrieved_book.isbn == isbn
                
                # Verify updated_at timestamp was changed
                assert retrieved_book.updated_at > initial_updated_at
                
            finally:
                db.drop_all()
    
    @given(
        books_data=st.lists(
            st.tuples(
                st.text(min_size=10, max_size=13).filter(lambda x: x.isdigit()),
                st.text(min_size=1, max_size=255)
            ),
            min_size=1,
            max_size=10,
            unique_by=lambda x: x[0]  # Ensure unique ISBNs
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_books_data_persistence(self, books_data):
        """
        **Property 3: Data Persistence**
        *For any* collection of books, all should be persistable and retrievable 
        independently without data corruption.
        **Validates: Requirements 1.3**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                created_books = []
                
                # Create and persist multiple books
                for isbn, title in books_data:
                    book = Book(isbn=isbn, title=title)
                    db.session.add(book)
                    created_books.append((isbn, title))
                
                db.session.commit()
                
                # Verify all books were persisted correctly
                for isbn, title in created_books:
                    retrieved_book = Book.query.filter_by(isbn=isbn).first()
                    assert retrieved_book is not None, f"Book with ISBN {isbn} should be retrievable"
                    assert retrieved_book.title == title, f"Title should match for ISBN {isbn}"
                
                # Verify total count matches
                total_books = Book.query.count()
                assert total_books == len(books_data), "All books should be persisted"
                
            finally:
                db.drop_all()
    
    @given(
        isbn=st.text(min_size=10, max_size=13).filter(lambda x: x.isdigit()),
        authors=st.lists(
            st.text(min_size=1, max_size=100, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'),
                whitelist_characters=' '
            )), 
            min_size=1, 
            max_size=5
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_authors_list_persistence(self, isbn, authors):
        """
        **Property 3: Data Persistence**
        *For any* list of authors, the data should be correctly serialized, 
        persisted, and deserializable upon retrieval.
        **Validates: Requirements 1.3**
        """
        app = create_test_app()
        with app.app_context():
            db.create_all()
            try:
                # Create book with authors list
                book = Book(isbn=isbn, authors=authors)
                db.session.add(book)
                db.session.commit()
                
                # Retrieve and verify authors list persistence
                retrieved_book = Book.query.filter_by(isbn=isbn).first()
                assert retrieved_book is not None
                
                # Verify authors list was correctly serialized and deserialized
                assert retrieved_book.authors_list == authors
                
                # Verify authors display string is correctly generated
                expected_display = ', '.join(authors)
                assert retrieved_book.authors_display == expected_display
                
            finally:
                db.drop_all()