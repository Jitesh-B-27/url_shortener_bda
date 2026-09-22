from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask import (
    Blueprint, current_app, flash, redirect, render_template,
    request, url_for,
)

from app import db
from app.models import Url, utc_now
from app.services.s3_service import upload_url_export
from app.services.shortener import generate_short_code, validate_url

main = Blueprint("main", __name__)
MAX_CODE_ATTEMPTS = 5


@main.get("/")
def index():
    try:
        urls = db.session.execute(
            db.select(Url).order_by(Url.created_at.desc())
        ).scalars().all()
        return render_template(
            "index.html", urls=urls, base_url=current_app.config["BASE_URL"]
        )
    except SQLAlchemyError:
        current_app.logger.exception("Could not load URL records")
        return render_template(
            "index.html", urls=[], base_url=current_app.config["BASE_URL"],
            database_error=True,
        ), 503


@main.post("/shorten")
def shorten():
    original_url, error = validate_url(request.form.get("original_url"))
    if error:
        flash(error, "error")
        return redirect(url_for("main.index"))

    for _ in range(MAX_CODE_ATTEMPTS):
        record = Url(original_url=original_url, short_code=generate_short_code())
        db.session.add(record)
        try:
            db.session.commit()
            short_url = f"{current_app.config['BASE_URL']}/{record.short_code}"
            flash(f"Short URL created: {short_url}", "success")
            return redirect(url_for("main.index"))
        except IntegrityError:
            db.session.rollback()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Could not create short URL")
            flash("The URL could not be saved. Please try again.", "error")
            return redirect(url_for("main.index"))

    flash("A unique short code could not be generated. Please try again.", "error")
    return redirect(url_for("main.index"))


@main.get("/health")
def health():
    return {"status": "ok"}


@main.post("/export")
def export():
    try:
        records = db.session.execute(
            db.select(Url).order_by(Url.id)
        ).scalars().all()
        object_key = upload_url_export(
            records,
            current_app.config.get("S3_BUCKET_NAME"),
            current_app.config["AWS_REGION"],
        )
        flash(f"CSV uploaded to S3 as {object_key}.", "success")
    except Exception:
        current_app.logger.exception("Could not export URL records")
        flash("The CSV export could not be uploaded. Please try again.", "error")
    return redirect(url_for("main.index"))


@main.get("/<short_code>")
def follow_short_url(short_code):
    try:
        record = db.session.execute(
            db.select(Url).where(Url.short_code == short_code)
        ).scalar_one_or_none()
    except SQLAlchemyError:
        current_app.logger.exception("Could not find short URL")
        return "The redirect is temporarily unavailable.", 503
    if record is None:
        return render_template(
            "index.html", urls=[], base_url=current_app.config["BASE_URL"],
            not_found=True,
        ), 404
    record.click_count += 1
    record.last_accessed_at = utc_now()
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not record URL visit")
        return "The redirect is temporarily unavailable.", 503
    return redirect(record.original_url)
