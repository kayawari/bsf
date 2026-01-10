#!/usr/bin/env python3
"""
Main application entry point.
"""
import os
from app import create_app, db

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.before_first_request
def create_tables():
    """Create database tables before first request."""
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)