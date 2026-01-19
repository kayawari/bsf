"""
Barcode scanning routes blueprint.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services.barcode_service import process_scanned_barcode
from app.services.book_service import get_book_by_id

# Create blueprint for scan routes
scan_bp = Blueprint("scan", __name__)


@scan_bp.route("/scan")
def barcode_scanner():
    """Display barcode scanning interface."""
    if request.headers.get("HX-Request"):
        # htmx request - return scanner fragment
        return render_template("fragments/barcode_scanner.html")
    else:
        # Regular request - return full scanner page
        return render_template("barcode_scanner.html")


@scan_bp.route("/scan/process", methods=["POST"])
def process_barcode_scan():
    """Process scanned barcode and return book information."""
    scanned_text = request.form.get("scanned_text", "").strip()
    scan_type = request.form.get("scan_type", "camera")  # 'camera' or 'file'
    
    if not scanned_text:
        error_message = "No barcode data received"
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/error_message.html", error=error_message
            ), 400
        else:
            flash(error_message, "error")
            return redirect(url_for("scan.barcode_scanner"))
    
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
            return redirect(url_for("scan.barcode_scanner"))
    
    # Success - show book confirmation
    try:
        # Try htmx request first
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/scanned_book_confirmation.html",
                book=book,
                warning=error_or_warning,
                scanned_isbn=scanned_text
            )
        else:
            raise ValueError("Not an htmx request")
    except (ValueError, Exception):
        # Progressive enhancement fallback - redirect to book detail
        if error_or_warning:
            flash(f"Book found with limited information: {error_or_warning}", "warning")
        else:
            flash(f'Found book: "{book.title}"', "success")
        return redirect(url_for("book.book_detail", book_id=book.id))


@scan_bp.route("/scan/save", methods=["POST"])
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
            return redirect(url_for("scan.barcode_scanner"))
    
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
            return redirect(url_for("scan.barcode_scanner"))
    
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
        return redirect(url_for("scan.barcode_scanner"))