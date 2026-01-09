"""
ARQ Worker for RecipeNow background jobs (OCR, parsing, normalization).
"""
import os

from arq.connections import RedisSettings

from jobs import ingest_job, normalize_job, structure_job


class WorkerSettings:
    """ARQ Worker configuration."""

    # Redis connection settings
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        database=int(os.getenv("REDIS_DB", 0)),
    )

    # Worker function imports
    functions = [
        ingest_job,
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
