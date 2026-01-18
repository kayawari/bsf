---
inclusion: always
---

# Technology Stack & Development Guidelines

## Core Technologies

### Backend Stack
- **Python 3.x** - Primary language with type hints required
- **Flask 3.0+** - Web framework using application factory pattern
- **SQLAlchemy 2.0+** - ORM with declarative models and hybrid properties
- **Flask-SQLAlchemy 3.1+** - Flask integration for SQLAlchemy

### Frontend Approach
- **HTML5** with semantic markup and accessibility compliance
- **CSS3** with mobile-first responsive design
- **htmx** - Progressive enhancement for dynamic interactions
- **No JavaScript frameworks** - Vanilla JS only when absolutely necessary

### Data Layer
- **SQLite** - Development database (instance/books.db)
- **PostgreSQL** - Production database (via DATABASE_URL)
- **UTC timestamps** - All datetime fields must be timezone-aware

### External Integrations
- **Google Books API** - Primary metadata source with graceful fallback
- **Requests** - HTTP client with proper error handling and timeouts

### Quality Assurance
- **pytest 7.4+** - Testing framework with fixtures and parametrization
- **Hypothesis 6.92+** - Property-based testing for edge cases
- **ruff 0.14+** - Linting and code formatting (must pass before commits)
- **mypy** - Static type checking (strict mode enabled)

### Deployment
- **Gunicorn 23.0+** - Production WSGI server

## Development Conventions

### Code Style Requirements
- **Type hints** - All function signatures must include type annotations
- **Docstrings** - Use Google-style docstrings for public functions and classes
- **Snake case** - Variables, functions, and file names (e.g., `book_service.py`)
- **PascalCase** - Class names (e.g., `BookService`, `GoogleBooksAPI`)
- **UPPER_CASE** - Constants and environment variables
- **Line length** - Maximum 88 characters (ruff default)

### Error Handling Patterns
- **Service layer** - Return tuples of `(result, error_message)` for operations
- **External APIs** - Always implement graceful fallback for service failures
- **Database operations** - Use try/except with proper rollback handling
- **Validation** - Validate inputs at service layer, not just routes

### Testing Requirements
- **Property-based tests** - Use Hypothesis for testing edge cases and invariants
- **Unit tests** - Test individual functions and methods in isolation
- **Integration tests** - Test full request/response cycles with test client
- **Mock external services** - Never make real API calls in tests
- **Test coverage** - Aim for >90% coverage on business logic

### Database Conventions
- **Hybrid properties** - Use for computed fields (e.g., `authors_list`)
- **Indexes** - Define in `__table_args__` for performance-critical queries
- **Migrations** - Use Flask-Migrate for schema changes (when added)
- **UTC timestamps** - Store all datetime fields in UTC with timezone info

### Template Patterns
- **Progressive enhancement** - Pages must work without JavaScript
- **htmx fragments** - Use partial templates in `fragments/` directory
- **Dual response** - Routes return fragments for htmx, full pages otherwise
- **Semantic HTML** - Use proper HTML5 semantic elements

### API Integration Guidelines
- **Timeout handling** - Set reasonable timeouts for external API calls
- **Rate limiting** - Respect API rate limits and implement backoff
- **Data validation** - Validate all external data before database storage
- **Fallback data** - Provide meaningful defaults when APIs are unavailable

## Essential Commands

### Development Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv/bin/activate.fish

# Install dependencies
pip install -r requirements.txt

# Run development server
python run.py
# Or with custom port
PORT=5000 python run.py
```

### Database Management
```bash
# Initialize database
python manage_db.py init

# Reset database (with confirmation)
python manage_db.py reset

# View database info
python manage_db.py info
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_book_service.py -v

# Run with coverage
python -m pytest tests/ --cov=app
```

### Code Quality (Required Before Commits)
```bash
# Format code (must pass)
ruff format .

# Lint code (must pass)
ruff check .

# Type checking (must pass)
mypy .

# Run all quality checks
ruff check . && ruff format . && mypy .
```

### Production Deployment
```bash
# Basic gunicorn
gunicorn run:app

# With workers and custom bind
gunicorn --workers 4 --bind 0.0.0.0:8000 run:app
```

### Utilities
```bash
# Check port availability
python scripts/check_port.py 8000
```

## Configuration Management

### Environment Variables (Required)
- `FLASK_ENV` - Application environment (development/production/testing)
- `SECRET_KEY` - Flask secret key (must be secure in production)
- `DATABASE_URL` - Database connection string (PostgreSQL for production)
- `GOOGLE_BOOKS_API_KEY` - Optional API key for enhanced rate limits
- `PORT` - Application port (default: 8000)

### Instance Configuration Pattern
Create `instance/config.py` for environment-specific overrides:
```python
# Production example
SECRET_KEY = 'your-secure-production-key'
DATABASE_URL = 'postgresql://user:pass@localhost/bookdb'
GOOGLE_BOOKS_API_KEY = 'your-api-key'

# Development example  
SECRET_KEY = 'dev-key-not-for-production'
# DATABASE_URL defaults to SQLite in development
```

### Security Requirements
- **Never commit secrets** - Use environment variables or instance config
- **Secure secret keys** - Generate cryptographically secure keys for production
- **Database credentials** - Store in environment variables, not code
- **API keys** - Optional but recommended for production use

## Architecture Patterns

### Service Layer Pattern
- **Routes** handle HTTP concerns only (request/response)
- **Services** contain all business logic and external integrations
- **Models** define data structure and basic validation
- **Database operations** isolated in service layer

### Error Handling Strategy
```python
# Service layer pattern
def get_book_by_isbn(isbn: str) -> tuple[Book | None, str | None]:
    """Return (book, error_message) tuple."""
    try:
        # Business logic here
        return book, None
    except Exception as e:
        return None, str(e)
```

### Progressive Enhancement
- **Base functionality** works without JavaScript
- **htmx enhancements** provide better UX
- **Graceful degradation** when external services fail