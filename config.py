from dotenv import load_dotenv
import os


load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class DevConfig:
    SECRET_KEY = (
        os.getenv("SECRET_KEY") or "dev-secret-key"
    )  # secret key needs to be set in .env file
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "database.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    DEBUG = True
    PORT = 5000
    HOST = "localhost"

    # Allowed email addresses
    ALLOWED_EMAILS = ["olof.thornell@gmail.com", "test@example.com"]


class ProdConfig:
    SECRET_KEY = os.getenv("SECRET_KEY")
    # secret key needs to be set in the .env file and uploaded to GCP
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "database.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    DEBUG = False
    PORT = 8080
    HOST = "0.0.0.0"

    # Allowed email addresses
    ALLOWED_EMAILS = ["olof.thornell@gmail.com"]
