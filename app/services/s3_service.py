import csv
import io
from datetime import datetime, timezone

import boto3


def build_csv(records):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "id", "original_url", "short_code", "click_count",
        "created_at_utc", "last_accessed_at_utc",
    ])
    for record in records:
        writer.writerow([
            record.id, record.original_url, record.short_code, record.click_count,
            _format_datetime(record.created_at),
            _format_datetime(record.last_accessed_at),
        ])
    return output.getvalue()


def upload_url_export(records, bucket_name, region_name, s3_client=None):
    if not bucket_name:
        raise ValueError("S3 bucket is not configured")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    object_key = f"exports/urls-{timestamp}.csv"
    client = s3_client or boto3.client("s3", region_name=region_name)
    client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=build_csv(records).encode("utf-8"),
        ContentType="text/csv; charset=utf-8",
    )
    return object_key


def _format_datetime(value):
    return value.isoformat(timespec="seconds") if value else ""
