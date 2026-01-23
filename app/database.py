"""Database initialization and management utilities."""

from pathlib import Path
from app import db, create_app
from app.models import Book


def init_database(app=None):
    """Initialize the database with all tables."""
    if app is None:
        app = create_app()

    with app.app_context():
        # Ensure instance directory exists
        instance_dir = Path(app.instance_path)
        instance_dir.mkdir(exist_ok=True)

        # Create all tables
        db.create_all()
        print("Database tables created successfully.")


def drop_database(app=None):
    """Drop all database tables (use with caution)."""
    if app is None:
        app = create_app()

    with app.app_context():
        db.drop_all()
        print("Database tables dropped successfully.")


def reset_database(app=None):
    """Reset the database by dropping and recreating all tables."""
    if app is None:
        app = create_app()

    with app.app_context():
        # Ensure instance directory exists
        instance_dir = Path(app.instance_path)
        instance_dir.mkdir(exist_ok=True)

        # Drop and recreate tables
        db.drop_all()
        db.create_all()
        print("Database reset successfully.")


def get_database_info(app=None):
    """Get information about the current database."""
    if app is None:
        app = create_app()

    with app.app_context():
        # Get database URI
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]

        # Count books
        try:
            book_count = Book.query.count()
        except Exception:
            book_count = "Unable to query (tables may not exist)"

        info = {
            "database_uri": db_uri,
            "book_count": book_count,
            "tables": db.metadata.tables.keys(),
        }

        return info


if __name__ == "__main__":
    """Command-line interface for database operations."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.database <command>")
        print("Commands:")
        print("  init    - Initialize database tables")
        print("  drop    - Drop all tables")
        print("  reset   - Drop and recreate all tables")
        print("  info    - Show database information")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "init":
        init_database()
    elif command == "drop":
        confirm = input("Are you sure you want to drop all tables? (yes/no): ")
        if confirm.lower() == "yes":
            drop_database()
        else:
            print("Operation cancelled.")
    elif command == "reset":
        confirm = input("Are you sure you want to reset the database? (yes/no): ")
        if confirm.lower() == "yes":
            reset_database()
        else:
            print("Operation cancelled.")
    elif command == "info":
        info = get_database_info()
        print("Database Information:")
        print(f"  URI: {info['database_uri']}")
        print(f"  Book count: {info['book_count']}")
        print(f"  Tables: {list(info['tables'])}")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
