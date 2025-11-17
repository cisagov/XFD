"""Load env variables from S3 or local env.json."""
# Standard Python Libraries
import json
import logging
import os
import time

# Third-Party Libraries
import boto3

LOGGER = logging.getLogger(__name__)


def load_django_env_config(ttl_seconds: int = 3600):
    """Load Django configuration from S3 or local file."""
    is_local = str(os.getenv("IS_LOCAL", "")).lower() in {"1", "true", "yes"}
    cache_path = "/tmp/env.json"  # nosec B108

    # --- Local / backend/xfd_django/env.json ---
    if is_local:
        local_path = "/app/env.json"

        try:
            with open(local_path, encoding="utf-8") as f:
                data = json.load(f)
            LOGGER.info("Loaded Django config from local file: %s", local_path)
        except FileNotFoundError:
            LOGGER.info("Local env.json not found at %s", local_path)
            data = {}
        _inject_env(data)
        return

    # --- Lambda / S3 path ---
    bucket = os.getenv("DJANGO_CONFIG_BUCKET")
    key = "env.json"
    if not bucket or not key:
        LOGGER.warning(
            "DJANGO_CONFIG_BUCKET or DJANGO_CONFIG_KEY not set — skipping S3 config load."
        )
        return

    # Use cached file if still fresh
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        age = time.time() - mtime
        if age < ttl_seconds:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            LOGGER.info(
                "Loaded Django config from cache (%s); age %.1f sec (TTL %s sec)",
                cache_path,
                age,
                ttl_seconds,
            )
            _inject_env(data)
            return
        else:
            LOGGER.info(
                "Cached env.json found at %s but expired (age %.1f sec > TTL %s sec)",
                cache_path,
                age,
                ttl_seconds,
            )

    # Fetch from S3 and cache
    try:
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        data = json.loads(body)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(body)
        LOGGER.info("Fetched Django config from S3 and cached at %s", cache_path)
    except Exception as e:
        LOGGER.error("Failed to load Django config from S3: %s", e)
        # fallback: stale cache if available
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            LOGGER.warning("Using stale cached config from %s", cache_path)
        else:
            # TODO: CRASM: 3166
            # Create Cloudwatch or ADOT Alarm so admins can be notified of this immediately
            raise
    _inject_env(data)


def _inject_env(data):
    """Flatten nested dicts into os.environ."""

    def flatten(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from flatten(f"{prefix}_{k}" if prefix else k, v)
        else:
            yield prefix, str(obj)

    for key, value in flatten("", data):
        os.environ[key.upper()] = value
    LOGGER.info("Loaded %d environment variables from config", len(data))
    LOGGER.info("Example keys loaded: %s", list(data.keys())[:10])
