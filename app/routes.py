from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.services.book_service import process_and_store_book, get_all_books, get_book_by_id

# Create blueprint for main routes
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page route with book collection display."""
    books = get_all_books()
    return render_template('index.html', books=books)

@main.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'ok', 'message': 'Book Management Application is running'}

@main.route('/add-book', methods=['POST'])
def add_book():
    """
    Handle ISBN form submission with htmx support.
    Returns HTML fragment for htmx or redirects for progressive enhancement.
    """
    isbn = request.form.get('isbn', '').strip()
    
    if not isbn:
        error_message = "Please enter an ISBN number"
        if request.headers.get('HX-Request'):
            # htmx request - return error fragment
            return render_template('fragments/error_message.html', error=error_message), 400
        else:
            # Progressive enhancement - flash message and redirect
            flash(error_message, 'error')
            return redirect(url_for('main.index'))
    
    # Process the book
    book, error = process_and_store_book(isbn)
    
    if error:
        if request.headers.get('HX-Request'):
            # htmx request - return error fragment
            return render_template('fragments/error_message.html', error=error), 400
        else:
            # Progressive enhancement - flash message and redirect
            flash(error, 'error')
            return redirect(url_for('main.index'))
    
    # Success case
    if request.headers.get('HX-Request'):
        # htmx request - return updated book collection fragment
        books = get_all_books()
        return render_template('fragments/book_collection.html', books=books)
    else:
        # Progressive enhancement - flash success and redirect
        flash(f'Successfully added "{book.title}" to your collection!', 'success')
        return redirect(url_for('main.index'))

@main.route('/books')
def book_collection():
    """
    Display book collection with htmx fragment support.
    """
    books = get_all_books()
    
    if request.headers.get('HX-Request'):
        # htmx request - return just the collection fragment
        return render_template('fragments/book_collection.html', books=books)
    else:
        # Regular request - return full page
        return render_template('collection.html', books=books)

@main.route('/book/<int:book_id>')
def book_detail(book_id):
    """
    Display detailed view of a specific book with htmx navigation support.
    """
    book = get_book_by_id(book_id)
    
    if not book:
        if request.headers.get('HX-Request'):
            return render_template('fragments/error_message.html', 
                                 error="Book not found"), 404
        else:
            flash("Book not found", 'error')
            return redirect(url_for('main.index'))
    
    if request.headers.get('HX-Request'):
        # htmx request - return book detail fragment
        return render_template('fragments/book_detail.html', book=book)
    else:
        # Regular request - return full page
        return render_template('book_detail.html', book=book)