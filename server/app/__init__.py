"""Flask application factory for the monitoring dashboard.

This module creates and configures the Flask application.

It registers:
- file logging
- Amazon OAuth client
- Flask blueprint routes

The application factory pattern makes the project easier to test and keeps
application initialization separate from route logic.
"""

import logging
import os

from authlib.integrations.flask_client import OAuth
from flask import Flask

from config import (
    LOG_DIR,
    SERVER_LOG,
    SECRET_KEY,
    AMAZON_CLIENT_ID,
    AMAZON_CLIENT_SECRET,
)

oauth = OAuth()


def create_app():
    """Create and configure the Flask application.

    Returns:
        Flask:
            Configured Flask application instance.

    Notes:
        This function registers the Amazon OAuth provider and the main blueprint.
        It also configures basic file logging for the server.
    """
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    os.makedirs(LOG_DIR, exist_ok=True)

    logging.basicConfig(
        filename=SERVER_LOG,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    oauth.init_app(app)

    oauth.register(
        name="amazon",
        client_id=AMAZON_CLIENT_ID,
        client_secret=AMAZON_CLIENT_SECRET,
        authorize_url="https://www.amazon.com/ap/oa",
        access_token_url="https://api.amazon.com/auth/o2/token",
        client_kwargs={
            "scope": "profile"
        }
    )

    from app.routes import main
    app.register_blueprint(main)

    return app