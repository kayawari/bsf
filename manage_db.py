#!/usr/bin/env python3
"""Database management script for the book management application."""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import init_database, drop_database, reset_database, get_database_info


def main():
    """Main CLI interface for database management."""
    if len(sys.argv) < 2:
        print("Book Management Database Tool")
        print("Usage: python manage_db.py <command>")
        print()
        print("Commands:")
        print("  init    - Initialize database tables")
        print("  drop    - Drop all tables (requires confirmation)")
        print("  reset   - Drop and recreate all tables (requires confirmation)")
        print("  info    - Show database information")
        print()
        print("Examples:")
        print("  python manage_db.py init")
        print("  python manage_db.py info")
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "init":
            print("Initializing database...")
            init_database()
            print("✓ Database initialization complete.")

        elif command == "drop":
            print("⚠️  WARNING: This will permanently delete all data!")
            confirm = input(
                "Are you sure you want to drop all tables? Type 'yes' to confirm: "
            )
            if confirm.lower() == "yes":
                drop_database()
                print("✓ Database tables dropped.")
            else:
                print("Operation cancelled.")

        elif command == "reset":
            print(
                "⚠️  WARNING: This will permanently delete all data and recreate tables!"
            )
            confirm = input(
                "Are you sure you want to reset the database? Type 'yes' to confirm: "
            )
            if confirm.lower() == "yes":
                reset_database()
                print("✓ Database reset complete.")
            else:
                print("Operation cancelled.")

        elif command == "info":
            print("Database Information:")
            print("-" * 40)
            info = get_database_info()
            print(f"URI: {info['database_uri']}")
            print(f"Book count: {info['book_count']}")
            print(f"Tables: {', '.join(info['tables']) if info['tables'] else 'None'}")

        else:
            print(f"❌ Unknown command: {command}")
            print("Run 'python manage_db.py' for usage information.")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
