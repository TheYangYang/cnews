"""S3 / MinIO object store for Opus audio."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig


class S3Store:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        endpoint: str | None,
        access_key: str | None,
        secret_key: str | None,
        force_path_style: bool,
        prefix: str,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        kwargs: dict = {
            "service_name": "s3",
            "region_name": region,
            "config": BotoConfig(s3={"addressing_style": "path" if force_path_style else "auto"}),
        }
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        self._client = boto3.client(**kwargs)

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def put_file(self, key: str, path: Path, content_type: str) -> str:
        full_key = f"{self.prefix}/{key}" if self.prefix else key
        self._client.upload_file(
            str(path),
            self.bucket,
            full_key,
            ExtraArgs={"ContentType": content_type, "CacheControl": "public, max-age=31536000"},
        )
        return full_key

    def delete_keys(self, keys: list[str]) -> None:
        """Delete full object keys (as stored in Mongo). Raises if S3 reports any failure,
        so the caller keeps the Mongo docs and retries next round."""
        for start in range(0, len(keys), 1000):
            chunk = keys[start : start + 1000]
            response = self._client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True},
            )
            errors = response.get("Errors") or []
            if errors:
                raise RuntimeError(f"S3 delete failed for {len(errors)} objects: {errors[0]}")

    def audio_key_for(self, story_id: str, when: datetime, ext: str = "opus") -> str:
        return f"{when.year:04d}/{when.month:02d}/{when.day:02d}/{story_id}.{ext}"
