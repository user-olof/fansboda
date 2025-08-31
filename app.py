from src import app, db


if __name__ == "__main__":
    # Create tables
    with app.app_context():
        db.create_all()
    app.run(port=app.config["PORT"], host=app.config["HOST"], debug=app.config["DEBUG"])
