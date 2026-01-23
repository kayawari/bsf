from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
import logging
from pathlib import Path

# Initialize extensions
db = SQLAlchemy()


def create_app(config_name="default"):
    """Application factory pattern."""
    app = Flask(__name__, instance_relative_config=True)

    # Load configuration
    app.config.from_object(config[config_name])

    # Load instance configuration if it exists
    try:
        app.config.from_pyfile("config.py")
    except FileNotFoundError:
        # Instance config is optional
        pass

    # Set secret key for flash messages if not already set
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"

    # Configure logging
    configure_logging(app)

    # Initialize extensions with app
    db.init_app(app)

    # Import models to ensure they are registered with SQLAlchemy
    from app.models import Book  # noqa: F401

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    from app.routes import health_bp, book_bp, scan_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(scan_bp)

    return app


def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Configure file handler
        file_handler = logging.FileHandler(logs_dir / "book_manager.log")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("Book Manager application startup")

    # Configure console logging for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        )
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)


def register_error_handlers(app):
    """Register global error handlers."""
    from flask import render_template, request

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        app.logger.warning(f"404 error: {request.url}")

        if request.headers.get("HX-Request"):
            # htmx request - return error fragment
            return render_template(
                "fragments/error_message.html", error="Page not found"
            ), 404
        else:
            # Regular request - return full error page
            return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        app.logger.error(f"500 error: {str(error)}", exc_info=True)

        # Rollback any pending database transactions
        from app import db

        db.session.rollback()

        if request.headers.get("HX-Request"):
            # htmx request - return error fragment
            return render_template(
                "fragments/error_message.html",
                error="An internal error occurred. Please try again.",
            ), 500
        else:
            # Regular request - return full error page
            return render_template("errors/500.html"), 500

    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors."""
        app.logger.warning(f"400 error: {request.url} - {str(error)}")

        if request.headers.get("HX-Request"):
            # htmx request - return error fragment
            return render_template(
                "fragments/error_message.html",
                error="Invalid request. Please check your input.",
            ), 400
        else:
            # Regular request - return full error page
            return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        app.logger.warning(f"403 error: {request.url}")

        if request.headers.get("HX-Request"):
            # htmx request - return error fragment
            return render_template(
                "fragments/error_message.html", error="Access forbidden."
            ), 403
        else:
            # Regular request - return full error page
            return render_template("errors/403.html"), 403

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all other unhandled exceptions."""
        app.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)

        # Rollback any pending database transactions
        from app import db

        db.session.rollback()

        if request.headers.get("HX-Request"):
            # htmx request - return error fragment
            return render_template(
                "fragments/error_message.html",
                error="An unexpected error occurred. Please try again.",
            ), 500
        else:
            # Regular request - return full error page
            return render_template("errors/500.html"), 500
