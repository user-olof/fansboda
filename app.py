from src import app, db, prepopulate_database


if __name__ == "__main__":
    # Create tables
    # prepopulate_database()
    app.run(port=app.config["PORT"], host=app.config["HOST"], debug=app.config["DEBUG"])
