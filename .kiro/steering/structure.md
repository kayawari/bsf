---
inclusion: always
---

# Project Structure & Architecture

## Directory Organization

```
├── app/                     # Main application package
│   ├── __init__.py         # Flask app factory, extensions, error handlers
│   ├── routes.py           # URL routes and view functions
│   ├── database.py         # Database management utilities
│   ├── models/             # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── book.py         # Book model with hybrid properties
│   ├── services/           # Business logic layer
│   │   ├── __init__.py
│   │   ├── book_service.py      # Core book operations
│   │   ├── google_books_api.py  # External API integration
│   │   └── isbn_service.py      # ISBN validation utilities
│   ├── templates/          # Jinja2 HTML templates
│   │   ├── base.html       # Base template with common layout
│   │   ├── index.html      # Home page with book collection
│   │   ├── book_detail.html # Individual book view
│   │   ├── collection.html  # Full collection view
│   │   ├── errors/         # Error page templates
│   │   └── fragments/      # htmx partial templates
│   └── static/             # Static assets
│       └── css/            # Stylesheets
├── instance/               # Instance-specific configuration
│   ├── config.py          # Local configuration overrides
│   └── books.db           # SQLite database (development)
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_setup.py      # Test configuration and fixtures
│   ├── test_book_service.py        # Service layer tests
│   ├── test_book_model_properties.py    # Model property tests
│   ├── test_isbn_service.py            # ISBN validation tests
│   └── test_*_properties.py            # Hypothesis property tests
├── scripts/               # Utility scripts
│   └── check_port.py     # Port availability checker
├── config.py             # Base configuration classes
├── run.py               # Application entry point
├── manage_db.py         # Database management CLI
└── requirements.txt     # Python dependencies
```

## Architecture Patterns

### Application Factory Pattern
- `app/__init__.py` contains `create_app()` function
- Supports multiple configurations (development, testing, production)
- Extensions initialized with `init_app()` pattern

### Service Layer Architecture
- **Models** (`app/models/`) - Data layer with SQLAlchemy ORM
- **Services** (`app/services/`) - Business logic and external integrations
- **Routes** (`app/routes.py`) - HTTP request handling and response formatting

### Progressive Enhancement
- **Base Templates** - Full HTML pages that work without JavaScript
- **htmx Fragments** - Partial templates for dynamic updates
- **Dual Response Pattern** - Routes return fragments for htmx, full pages otherwise

### Error Handling Strategy
- **Global Error Handlers** - Registered in app factory
- **Service Layer Errors** - Return tuples of (result, error_message)
- **Graceful Degradation** - Fallback data when external services fail

## Key Conventions

### File Naming
- **Snake case** for Python files: `book_service.py`
- **Lowercase with hyphens** for templates: `book-detail.html`
- **Test files** prefixed with `test_`: `test_book_service.py`

### Code Organization
- **One class per file** in models directory
- **Related functions grouped** in service modules
- **Blueprint organization** for routes (currently single `main` blueprint)

### Database Patterns
- **Hybrid properties** for computed fields (e.g., `authors_list` in Book model)
- **UTC timestamps** with timezone-aware datetime objects
- **Indexes** defined in model `__table_args__` for performance

### Template Structure
- **Base template** with blocks for title, content, scripts
- **Fragment templates** in `fragments/` for htmx responses
- **Error templates** in `errors/` for HTTP error codes

### Testing Patterns
- **Pytest fixtures** for app, client, and test data
- **Property-based tests** with Hypothesis for edge cases
- **Mocking external services** to ensure test isolation
- **Integration tests** covering full request/response cycles

### Configuration Management
- **Environment-based configs** in `config.py`
- **Instance folder** for sensitive/local configuration
- **Environment variables** for deployment settings

### Import Conventions
- **Absolute imports** from app package: `from app.models.book import Book`
- **Service imports** in routes: `from app.services.book_service import get_all_books`
- **Extension imports** from app: `from app import db`