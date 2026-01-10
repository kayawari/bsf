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

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Run tests:**
   ```bash
   python -m pytest tests/ -v
   ```

## Project Structure

```
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes.py            # URL routes
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS, images
├── tests/                   # Test files
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
└── run.py                   # Application entry point
```

## Features

- Flask web framework with htmx integration
- SQLAlchemy ORM for database operations
- UTF-8 character encoding support
- Responsive design for desktop, tablet, and mobile
- Property-based testing with Hypothesis
- Progressive enhancement (works without JavaScript)

## Technology Stack

- **Backend:** Python, Flask, SQLAlchemy
- **Frontend:** HTML, CSS, htmx
- **Database:** SQLite
- **Testing:** pytest, Hypothesis
- **External API:** Google Books API