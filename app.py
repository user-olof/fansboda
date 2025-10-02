import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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
