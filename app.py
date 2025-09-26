from src import create_app

app = create_app()

if __name__ == "__main__":
    # Create tables
    app.run(
        port=app.config["PORT"],
        host=app.config["HOST"],
        debug=app.config["DEBUG"],
        ssl_context=app.config["SSL_CONTEXT"],
    )
