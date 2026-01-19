from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.book_service import (
    process_and_store_book_with_retry_option,
    get_all_books,
    get_book_by_id,
)
from app.services.barcode_service import process_scanned_barcode

# Create blueprint for main routes
main = Blueprint("main", __name__)


@main.route("/")
def index():
    """Home page route with book collection display."""
    books = get_all_books()
    return render_template("index.html", books=books)


@main.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "Book Management Application is running"}


@main.route("/add-book", methods=["POST"])
def add_book():
    """
    Handle ISBN form submission with htmx support and graceful error handling.
    Returns HTML fragment for htmx or redirects for progressive enhancement.
    """
    isbn = request.form.get("isbn", "").strip()

    if not isbn:
        error_message = "Please enter an ISBN number"
        if request.headers.get("HX-Request"):
            # htmx request - return error fragment
            return render_template(
                "fragments/error_message.html", error=error_message
            ), 400
        else:
            # Progressive enhancement - flash message and redirect
            flash(error_message, "error")
            return redirect(url_for("main.index"))

    # Process the book with fallback handling
    book, error_or_warning, should_retry_later = (
        process_and_store_book_with_retry_option(isbn)
    )

    if not book:
        # Complete failure - no book was created
        if request.headers.get("HX-Request"):
            # htmx request - return error fragment
            return render_template(
                "fragments/error_message.html",
                error=error_or_warning,
                show_retry=should_retry_later,
            ), 400
        else:
            # Progressive enhancement - flash message and redirect
            flash(error_or_warning, "error")
            return redirect(url_for("main.index"))

    # Success case (book was created, but might have warning about fallback data)
    if error_or_warning:
        # Book created with fallback data - show warning
        warning_message = (
            f"Book added successfully, but with limited information: {error_or_warning}"
        )
        if should_retry_later:
            warning_message += " You can try refreshing the book information later when the service is available."

        if request.headers.get("HX-Request"):
            # htmx request - return updated collection with warning
            books = get_all_books()
            return render_template(
                "fragments/book_collection.html", books=books, warning=warning_message
            )
        else:
            # Progressive enhancement - flash warning and redirect
            flash(warning_message, "warning")
            return redirect(url_for("main.index"))
    else:
        # Complete success
        if request.headers.get("HX-Request"):
            # htmx request - return updated book collection fragment
            books = get_all_books()
            return render_template("fragments/book_collection.html", books=books)
        else:
            # Progressive enhancement - flash success and redirect
            flash(f'Successfully added "{book.title}" to your collection!', "success")
            return redirect(url_for("main.index"))


@main.route("/books")
def book_collection():
    """
    Display book collection with htmx fragment support.
    """
    books = get_all_books()

    if request.headers.get("HX-Request"):
        # htmx request - return just the collection fragment
        return render_template("fragments/book_collection.html", books=books)
    else:
        # Regular request - return full page
        return render_template("collection.html", books=books)


@main.route("/book/<int:book_id>")
def book_detail(book_id):
    """
    Display detailed view of a specific book with htmx navigation support.
    """
    book = get_book_by_id(book_id)

    if not book:
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/error_message.html", error="Book not found"
            ), 404
        else:
            flash("Book not found", "error")
            return redirect(url_for("main.index"))

    if request.headers.get("HX-Request"):
        # htmx request - return book detail fragment
        return render_template("fragments/book_detail.html", book=book)
    else:
        # Regular request - return full page
        return render_template("book_detail.html", book=book)


@main.route("/refresh-book/<int:book_id>", methods=["POST"])
def refresh_book(book_id):
    """
    Refresh book metadata from Google Books API.
    """
    from app.services.book_service import refresh_book_from_api

    book, error_or_warning, is_fallback = refresh_book_from_api(book_id)

    if not book:
        # Refresh failed
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/error_message.html", error=error_or_warning
            ), 400
        else:
            flash(error_or_warning, "error")
            return redirect(url_for("main.book_detail", book_id=book_id))

    # Refresh succeeded
    if is_fallback and error_or_warning:
        # Refreshed with fallback data
        warning_message = (
            f"Book information refreshed with limited data: {error_or_warning}"
        )
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/book_detail.html", book=book, warning=warning_message
            )
        else:
            flash(warning_message, "warning")
            return redirect(url_for("main.book_detail", book_id=book_id))
    else:
        # Complete success
        if request.headers.get("HX-Request"):
            return render_template("fragments/book_detail.html", book=book)
        else:
            flash("Book information refreshed successfully!", "success")
            return redirect(url_for("main.book_detail", book_id=book_id))


@main.route("/scan")
def barcode_scanner():
    """Display barcode scanning interface."""
    if request.headers.get("HX-Request"):
        # htmx request - return scanner fragment
        return render_template("fragments/barcode_scanner.html")
    else:
        # Regular request - return full scanner page
        return render_template("barcode_scanner.html")


@main.route("/scan/process", methods=["POST"])
def process_barcode_scan():
    """Process scanned barcode and return book information."""
    scanned_text = request.form.get("scanned_text", "").strip()
    scan_type = request.form.get("scan_type", "camera")  # 'camera' or 'file'
    
    # Process the scanned barcode
    book, error_or_warning, should_retry_later = process_scanned_barcode(
        scanned_text, scan_type
    )
    
    if not book:
        # Processing failed
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/error_message.html",
                error=error_or_warning,
                show_retry=should_retry_later,
            ), 400
        else:
            flash(error_or_warning, "error")
            return redirect(url_for("main.barcode_scanner"))
    
    # Success - show book confirmation
    if request.headers.get("HX-Request"):
        return render_template(
            "fragments/scanned_book_confirmation.html",
            book=book,
            warning=error_or_warning,
            scanned_isbn=scanned_text
        )
    else:
        # Progressive enhancement fallback - redirect to book detail
        if error_or_warning:
            flash(f"Book found with limited information: {error_or_warning}", "warning")
        else:
            flash(f'Found book: "{book.title}"', "success")
        return redirect(url_for("main.book_detail", book_id=book.id))


@main.route("/scan/save", methods=["POST"])
def save_scanned_book():
    """Save confirmed book to database (book already exists from processing)."""
    book_id = request.form.get("book_id")
    
    if not book_id:
        error_message = "No book ID provided"
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/error_message.html", error=error_message
            ), 400
        else:
            flash(error_message, "error")
            return redirect(url_for("main.barcode_scanner"))
    
    # Get the book to confirm it exists
    book = get_book_by_id(int(book_id))
    if not book:
        error_message = "Book not found"
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/error_message.html", error=error_message
            ), 404
        else:
            flash(error_message, "error")
            return redirect(url_for("main.barcode_scanner"))
    
    # Book is already saved, just provide success feedback and return to scanner
    success_message = f'Successfully added "{book.title}" to your collection!'
    
    if request.headers.get("HX-Request"):
        # Return scanner interface with success message
        return render_template(
            "fragments/barcode_scanner.html",
            success=success_message
        )
    else:
        flash(success_message, "success")
        return redirect(url_for("main.barcode_scanner"))
