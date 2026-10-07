import os
from pathlib import Path

from flask import Flask

from .db import init_db


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "NEXUS_SECRET_KEY",
        "nexus-development-secret-change-me",
    )

    # Production: PostgreSQL via DATABASE_URL (Neon/Render)
    # Local development: SQLite fallback.
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        app.config["DATABASE_URL"] = database_url
        app.config["DATABASE"] = database_url
    else:
        app.config["DATABASE"] = str(
            Path(app.instance_path) / "expense_tracker.db"
        )

        Path(app.instance_path).mkdir(
            parents=True,
            exist_ok=True,
        )

    init_db(app)

    from .routes import main
    app.register_blueprint(main)

    return app
