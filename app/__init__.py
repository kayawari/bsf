from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config

# Initialize extensions
db = SQLAlchemy()

def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Load instance configuration if it exists
    try:
        app.config.from_pyfile('config.py')
    except FileNotFoundError:
        # Instance config is optional
        pass
    
    # Set secret key for flash messages if not already set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Import models to ensure they are registered with SQLAlchemy
    from app.models import Book
    
    # Register blueprints (routes will be added in later tasks)
    from app.routes import main
    app.register_blueprint(main)
    
    return app