#!/usr/bin/env python3
"""
Main application entry point.
"""

import os
from app import create_app, db

# Create Flask application
app = create_app(os.getenv("FLASK_ENV", "development"))


@app.before_request
def create_tables():
    """Create database tables before first request."""
    if not hasattr(create_tables, "called"):
        db.create_all()
        create_tables.called = True


if __name__ == "__main__":
    # Use port 8000 for development, configurable via PORT environment variable
    port = int(os.environ.get("PORT", 8000))

    # Enable debug mode for development environment
    flask_env = os.environ.get("FLASK_ENV", "development")
    debug = flask_env == "development"

    print(f"Starting Book Management Application on http://localhost:{port}")
    print(f"Environment: {flask_env}, Debug mode: {'on' if debug else 'off'}")
    app.run(host="127.0.0.1", port=port, debug=debug)
