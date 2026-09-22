import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def build_database_uri():
    host = os.getenv("DB_HOST")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    port = os.getenv("DB_PORT", "3306")
    if not all((host, name, user, password)):
        return None
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{quote_plus(name)}?charset=utf8mb4"
    )


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")
