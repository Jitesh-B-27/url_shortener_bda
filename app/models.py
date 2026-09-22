from datetime import datetime, timezone

from app import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Url(db.Model):
    __tablename__ = "urls"
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(8), nullable=False, unique=True, index=True)
    click_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    last_accessed_at = db.Column(db.DateTime, nullable=True)
