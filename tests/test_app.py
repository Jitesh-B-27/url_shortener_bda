from unittest.mock import Mock, patch
from types import SimpleNamespace

import pytest

from app import create_app, db
from app.models import Url
from app.services.s3_service import upload_url_export


@pytest.fixture()
def app():
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {},
        "BASE_URL": "http://localhost",
        "S3_BUCKET_NAME": "test-bucket",
        "AWS_REGION": "ap-south-1",
    })
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"URL Shortener" in response.data


@pytest.mark.parametrize("value", ["", "example.com", "ftp://example.com", "https://"])
def test_invalid_urls_are_rejected(client, value):
    response = client.post("/shorten", data={"original_url": value}, follow_redirects=True)
    assert response.status_code == 200
    assert b"valid URL" in response.data or b"Please enter a URL" in response.data


def test_create_redirect_and_count_click(client, app):
    with patch("app.routes.generate_short_code", return_value="abc1234"):
        response = client.post(
            "/shorten", data={"original_url": "https://example.com/path"}
        )
    assert response.status_code == 302

    response = client.get("/abc1234")
    assert response.status_code == 302
    assert response.location == "https://example.com/path"
    with app.app_context():
        record = db.session.execute(
            db.select(Url).where(Url.short_code == "abc1234")
        ).scalar_one()
        assert record.click_count == 1
        assert record.last_accessed_at is not None


def test_unknown_code_returns_404(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert b"does not exist" in response.data


def test_export_uploads_csv(client, app):
    with app.app_context():
        db.session.add(Url(original_url="https://example.com", short_code="csv1234"))
        db.session.commit()
    with patch("app.routes.upload_url_export", return_value="exports/urls.csv") as upload:
        response = client.post("/export", follow_redirects=True)
    assert response.status_code == 200
    assert b"exports/urls.csv" in response.data
    records, bucket, region = upload.call_args.args
    assert len(records) == 1
    assert bucket == "test-bucket"
    assert region == "ap-south-1"


def test_export_failure_is_safe(client):
    with patch("app.routes.upload_url_export", side_effect=RuntimeError("secret detail")):
        response = client.post("/export", follow_redirects=True)
    assert response.status_code == 200
    assert b"could not be uploaded" in response.data
    assert b"secret detail" not in response.data


def test_s3_service_uploads_csv_content():
    record = SimpleNamespace(
        id=1,
        original_url="https://example.com",
        short_code="csv1234",
        click_count=3,
        created_at=None,
        last_accessed_at=None,
    )
    s3_client = SimpleNamespace()
    s3_client.put_object = Mock()

    object_key = upload_url_export(
        [record], "test-bucket", "ap-south-1", s3_client=s3_client
    )

    uploaded = s3_client.put_object.call_args.kwargs
    assert object_key.startswith("exports/urls-")
    assert uploaded["Bucket"] == "test-bucket"
    assert uploaded["Key"] == object_key
    assert b"original_url,short_code,click_count" in uploaded["Body"]
    assert b"https://example.com,csv1234,3" in uploaded["Body"]
