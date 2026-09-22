from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db


def main():
    app = create_app()
    try:
        with app.app_context():
            db.create_all()
    except SQLAlchemyError:
        print(
            "Database initialization failed. Check that MySQL is running and "
            "that DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD are correct.",
            file=sys.stderr,
        )
        return 1
    print("Database tables are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
