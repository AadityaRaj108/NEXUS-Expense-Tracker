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