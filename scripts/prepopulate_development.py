#!/usr/bin/env python3
"""Production database prepopulation script."""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src import create_app, db


def prepopulate_database(app):
    """Initialize database and add default data."""
    try:
        # Check if the database exists

        # Import User model here to avoid circular imports
        from src.models.user import User

        # Check if we already have any users
        try:
            user_count = db.session.query(User).count()
            print(f"Current user count: {user_count}")

            if user_count == 0:
                # No users exist, create the default admin user
                user = User(email="admin@test.com")
                user.password_hash = "123456"
                db.session.add(user)
                print(f"Added user {user.email} to database")
                db.session.commit()
                print("Default admin user created successfully")
            else:
                print("Users already exist in database, skipping user creation")
        except Exception as e:
            print(f"Error checking/creating users: {e}")
            db.session.rollback()

    except Exception as e:
        print(f"Error in prepopulate_database: {e}")


def main():
    """Run prepopulation."""
    app = create_app("development")

    with app.app_context():
        print("Starting production database prepopulation...")
        prepopulate_database(app)
        print("Production database prepopulation completed!")


if __name__ == "__main__":
    main()
