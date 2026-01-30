"""
ARQ Worker for RecipeNow background jobs (OCR, parsing, normalization).
"""
import os
from urllib.parse import urlparse

from arq.connections import RedisSettings

from jobs import ingest_job, normalize_job, structure_job, extract_job


class WorkerSettings:
    """ARQ Worker configuration."""

    # Redis connection settings
    _redis_url = os.getenv("REDIS_URL")
    if _redis_url:
        _parsed = urlparse(_redis_url)
        _db = int(_parsed.path.lstrip("/")) if _parsed.path and _parsed.path != "/" else 0
        redis_settings = RedisSettings(
            host=_parsed.hostname or "redis",
            port=_parsed.port or 6379,
            password=_parsed.password,
            database=_db,
        )
    else:
        redis_settings = RedisSettings(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            database=int(os.getenv("REDIS_DB", 0)),
        )

    # Worker function imports
    functions = [
        ingest_job,
        extract_job,
        structure_job,
        normalize_job,
    ]

    # Job default timeout (30 minutes for OCR jobs)
    max_jobs = 10
    job_timeout = 30 * 60

    # Result retention (24 hours)
    result_ttl = 86400


async def health_check() -> str:
    """Health check job for verifying worker connectivity."""
    return "ok"
