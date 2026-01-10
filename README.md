# Book Management Application

A web application for managing purchased books by manually inputting ISBN numbers and retrieving book information from Google Books API.

## Setup

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate.fish  # For fish shell
   # or source venv/bin/activate  # For bash/zsh
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the application (optional):**
   
   The application uses Flask's instance folder for configuration. You can create `instance/config.py` to override default settings:
   
   ```python
   # instance/config.py
   SECRET_KEY = 'your-production-secret-key'
   DATABASE_URL = 'postgresql://user:pass@localhost/bookdb'  # For production
   GOOGLE_BOOKS_API_KEY = 'your-google-books-api-key'  # Optional
   ```

4. **Run the application:**
   ```bash
   python run.py
   ```

5. **Run tests:**
   ```bash
   python -m pytest tests/ -v
   ```

## Configuration

The application supports multiple configuration environments:

- **Development** (default): Uses SQLite database in instance folder
- **Testing**: Uses in-memory SQLite database
- **Production**: Can be configured via environment variables or instance config

### Environment Variables

- `FLASK_ENV`: Set to 'development', 'production', or 'testing'
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection string
- `GOOGLE_BOOKS_API_KEY`: Optional Google Books API key

### Instance Configuration

The `instance/` folder is used for sensitive configuration that shouldn't be in version control. Create `instance/config.py` to override any settings locally.

## Project Structure

```
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes.py            # URL routes
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS, images
├── instance/                # Instance-specific configuration
│   └── config.py            # Local configuration overrides
├── tests/                   # Test files
├── config.py                # Base configuration settings
├── requirements.txt         # Python dependencies
└── run.py                   # Application entry point
```

## Features

- Flask web framework with htmx integration
- SQLAlchemy ORM for database operations
- Instance-relative configuration for security
- UTF-8 character encoding support
- Responsive design for desktop, tablet, and mobile
- Property-based testing with Hypothesis
- Progressive enhancement (works without JavaScript)

## Technology Stack

- **Backend:** Python, Flask, SQLAlchemy
- **Frontend:** HTML, CSS, htmx
- **Database:** SQLite (development), PostgreSQL (production)
- **Testing:** pytest, Hypothesis
- **External API:** Google Books API