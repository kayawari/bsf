"""
Barcode scanning routes blueprint with comprehensive error handling.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.services.barcode_service import (
    process_scanned_barcode, 
    validate_file_for_scanning,
    get_error_recovery_options,
    log_scanning_error,
    ScanErrorType
)
from app.services.book_service import get_book_by_id

# Create blueprint for scan routes
scan_bp = Blueprint("scan", __name__)


@scan_bp.route("/scan")
def barcode_scanner():
    """Display barcode scanning interface."""
    if request.headers.get("HX-Request"):
        # htmx request - return scanner fragment
        return render_template("fragments/barcode_scanner.html")
    # Regular request - return full scanner page
    return render_template("barcode_scanner.html")


@scan_bp.route("/scan/process", methods=["POST"])
def process_barcode_scan():
    """Process scanned barcode and return book information with enhanced error handling."""
    scanned_text = request.form.get("scanned_text", "").strip()
    scan_type = request.form.get("scan_type", "camera")  # 'camera' or 'file'
    error_data_json = request.form.get("error_data")

    # Handle client-side errors (from JavaScript)
    if error_data_json and not scanned_text:
        try:
            import json
            error_data = json.loads(error_data_json)
            
            if request.headers.get("HX-Request"):
                return render_template(
                    "fragments/enhanced_error_message.html",
                    error_message=error_data.get("error_message", "An error occurred"),
                    suggested_action=error_data.get("suggested_action", "Please try again"),
                    show_retry=error_data.get("show_retry", True),
                    show_file_fallback=error_data.get("show_file_fallback", True),
                    show_manual_entry=error_data.get("show_manual_entry", True),
                    error_type=error_data.get("error_type", "unknown"),
                    severity=error_data.get("severity", "medium")
                ), 400
            
            # Progressive enhancement fallback
            flash(error_data.get("error_message", "An error occurred"), "error")
            return redirect(url_for("scan.barcode_scanner"))
            
        except (json.JSONDecodeError, KeyError):
            # Invalid error data, fall through to normal processing
            pass

    if not scanned_text:
        error_message = "No barcode data received"
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/enhanced_error_message.html", 
                error_message=error_message,
                suggested_action="Please try scanning again or use the file upload option.",
                show_retry=True,
                show_file_fallback=True,
                show_manual_entry=True,
                error_type="validation_error",
                severity="low"
            ), 400
        flash(error_message, "error")
        return redirect(url_for("scan.barcode_scanner"))

    # Process the scanned barcode with enhanced error handling
    book, error_or_warning, should_retry_later, scan_error = process_scanned_barcode(
        scanned_text, scan_type
    )

    if not book:
        # Processing failed - use structured error handling
        if scan_error:
            # Log the error for debugging
            log_scanning_error(scanned_text, scan_type, scan_error)
            
            # Get recovery options
            recovery_options = get_error_recovery_options(scan_error)
            
            if request.headers.get("HX-Request"):
                return render_template(
                    "fragments/enhanced_error_message.html",
                    error_message=scan_error.user_message,
                    suggested_action=scan_error.suggested_action,
                    show_retry=recovery_options["show_retry_button"],
                    show_file_fallback=recovery_options["show_file_fallback"],
                    show_manual_entry=recovery_options["show_manual_entry"],
                    error_type=scan_error.error_type.value,
                    severity=scan_error.severity.value,
                    can_continue=recovery_options["can_continue"]
                ), 400
            
            # Progressive enhancement fallback
            flash(scan_error.user_message, "error")
            return redirect(url_for("scan.barcode_scanner"))
        else:
            # Fallback to original error handling
            if request.headers.get("HX-Request"):
                return render_template(
                    "fragments/error_message.html",
                    error=error_or_warning,
                    show_retry=should_retry_later,
                ), 400
            flash(error_or_warning, "error")
            return redirect(url_for("scan.barcode_scanner"))

    # Success - show book confirmation
    if request.headers.get("HX-Request"):
        return render_template(
            "fragments/scanned_book_confirmation.html",
            book=book,
            warning=error_or_warning,
            scanned_isbn=scanned_text,
            should_retry_later=should_retry_later
        )
    else:
        # Progressive enhancement fallback - redirect to book detail
        if error_or_warning:
            flash(f"Book found with limited information: {error_or_warning}", "warning")
        else:
            flash(f'Found book: "{book.title}"', "success")
        return redirect(url_for("book.book_detail", book_id=book.id))


@scan_bp.route("/scan/save", methods=["POST"])
def save_scanned_book():
    """Save confirmed book to database with enhanced error handling."""
    book_id = request.form.get("book_id")

    if not book_id:
        error_message = "No book ID provided"
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/enhanced_error_message.html", 
                error_message=error_message,
                suggested_action="Please try scanning again.",
                show_retry=True,
                show_manual_entry=True
            ), 400
        flash(error_message, "error")
        return redirect(url_for("scan.barcode_scanner"))

    try:
        book_id_int = int(book_id)
    except (ValueError, TypeError):
        error_message = "Invalid book ID format"
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/enhanced_error_message.html",
                error_message=error_message,
                suggested_action="Please try scanning again.",
                show_retry=True,
                show_manual_entry=True
            ), 400
        flash(error_message, "error")
        return redirect(url_for("scan.barcode_scanner"))

    # Get the book to confirm it exists
    try:
        book = get_book_by_id(book_id_int)
        if not book:
            error_message = "Book not found in database"
            if request.headers.get("HX-Request"):
                return render_template(
                    "fragments/enhanced_error_message.html",
                    error_message=error_message,
                    suggested_action="The book may have been removed. Please try scanning again.",
                    show_retry=True,
                    show_manual_entry=True
                ), 404
            flash(error_message, "error")
            return redirect(url_for("scan.barcode_scanner"))
    except Exception:
        error_message = "Database error while retrieving book"
        if request.headers.get("HX-Request"):
            return render_template(
                "fragments/enhanced_error_message.html",
                error_message=error_message,
                suggested_action="Please try again in a moment. If the problem persists, contact support.",
                show_retry=True,
                show_manual_entry=True,
                error_type="database_error"
            ), 500
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
    flash(success_message, "success")
    return redirect(url_for("scan.barcode_scanner"))


@scan_bp.route("/scan/validate-file", methods=["POST"])
def validate_scan_file():
    """Validate uploaded file for barcode scanning."""
    if 'file' not in request.files:
        return jsonify({
            'valid': False,
            'error': 'No file uploaded',
            'error_type': 'file_format_error'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'valid': False,
            'error': 'No file selected',
            'error_type': 'file_format_error'
        }), 400
    
    # Prepare file data for validation
    file_data = {
        'type': file.content_type,
        'size': len(file.read()),
        'name': file.filename
    }
    file.seek(0)  # Reset file pointer
    
    # Validate the file
    is_valid, scan_error = validate_file_for_scanning(file_data)
    
    if not is_valid and scan_error:
        recovery_options = get_error_recovery_options(scan_error)
        return jsonify({
            'valid': False,
            'error': scan_error.user_message,
            'error_type': scan_error.error_type.value,
            'suggested_action': scan_error.suggested_action,
            'recovery_options': recovery_options
        }), 400
    
    return jsonify({
        'valid': True,
        'message': 'File is valid for scanning'
    })


@scan_bp.route("/scan/error-info/<error_type>")
def get_error_info(error_type):
    """Get detailed information about a specific error type."""
    try:
        error_enum = ScanErrorType(error_type)
        
        # Create a sample error for this type to get standard messaging
        sample_error = None
        if error_enum == ScanErrorType.CAMERA_PERMISSION_ERROR:
            from app.services.barcode_service import handle_camera_permission_error
            sample_error = handle_camera_permission_error("Sample permission error")
        elif error_enum == ScanErrorType.NETWORK_ERROR:
            from app.services.barcode_service import handle_network_error
            sample_error = handle_network_error("Sample network error")
        elif error_enum == ScanErrorType.DATABASE_ERROR:
            from app.services.barcode_service import handle_database_error
            sample_error = handle_database_error("Sample database error")
        
        if sample_error:
            recovery_options = get_error_recovery_options(sample_error)
            return jsonify({
                'error_type': error_type,
                'user_message': sample_error.user_message,
                'suggested_action': sample_error.suggested_action,
                'severity': sample_error.severity.value,
                'recovery_options': recovery_options
            })
        
        return jsonify({
            'error_type': error_type,
            'message': 'Error information not available'
        }), 404
        
    except ValueError:
        return jsonify({
            'error': 'Invalid error type'
        }), 400