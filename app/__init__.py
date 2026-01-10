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
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Register blueprints (routes will be added in later tasks)
    from app.routes import main
    app.register_blueprint(main)
    
    return app