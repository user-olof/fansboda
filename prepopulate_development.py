#!/usr/bin/env python3
"""Production database prepopulation script."""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src import create_app, prepopulate_database


def main():
    """Run prepopulation for production."""
    app = create_app("development")

    with app.app_context():
        print("Starting production database prepopulation...")
        prepopulate_database(app)
        print("Production database prepopulation completed!")


if __name__ == "__main__":
    main()
