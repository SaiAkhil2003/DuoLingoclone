from __future__ import annotations

from pathlib import Path

from flask import Flask

from config import Config

from .extensions import db, login_manager


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .models import all_models  # noqa: F401
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .services.seed import seed_database

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        seed_database()

    @app.cli.command("init-db")
    def init_db() -> None:
        db.create_all()
        print("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db_command() -> None:
        seed_database()
        print("Seed data loaded.")

    @app.context_processor
    def inject_globals() -> dict[str, int]:
        from datetime import datetime, timezone

        return {"current_year": datetime.now(timezone.utc).year}

    return app
