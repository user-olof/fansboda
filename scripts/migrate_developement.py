#!/usr/bin/env python3
"""Database migration script for production."""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src import create_app
from flask_migrate import upgrade


def main():
    """Run database migration."""
    app = create_app("development")

    with app.app_context():
        print("Starting database migration...")
        upgrade()
        print("Database migration completed!")


if __name__ == "__main__":
    main()
