"""Application entry point for the monitoring web server.

This file starts the Flask application and initializes the database before the
web server begins accepting requests.

The Flask application itself is created in the app package. Database setup is
handled by app.db.init_db(), so the application can automatically create the
required SQLite tables when it starts.
"""

from config import HOST, PORT, USE_ADHOC_SSL
from app import create_app
from app.db import metrics_db

app = create_app()

with app.app_context():
    metrics_db.init()

if __name__ == "__main__":
    if USE_ADHOC_SSL:
        print(f"Server start op https://{HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=False, ssl_context="adhoc")
    else:
        print(f"Server start op http://{HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=False)