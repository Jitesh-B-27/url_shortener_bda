import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()


def create_app(config_override=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_override:
        app.config.from_mapping(config_override)
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError(
            "Database configuration is incomplete. Set DB_HOST, DB_NAME, "
            "DB_USER, and DB_PASSWORD."
        )
    db.init_app(app)
    from app.routes import main
    app.register_blueprint(main)
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
    return app
