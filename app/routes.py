from flask import Blueprint, render_template

# Create blueprint for main routes
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page route."""
    return render_template('index.html')

@main.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'ok', 'message': 'Book Management Application is running'}