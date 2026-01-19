"""
Health check routes blueprint.
"""

from flask import Blueprint

# Create blueprint for health routes
health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "Book Management Application is running"}