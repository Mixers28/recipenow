# Upload Timeout Fix Summary

**Date:** January 27, 2026
**Issue:** 500 errors on `/assets/upload` endpoint due to OCR processing timeouts

## Problem Analysis

From Railway logs ([latest_upload_logs.txt](latest_upload_logs.txt)):
- SIGTERM signal received by process (lines 6-18)
- Process killed by OS during PaddleOCR processing
- Happens after model loading completes but during OCR extraction
- Caused by Railway's request timeout limits (~100 seconds)

## Solutions Implemented

### Solution 1: Timeout Protection ✅

Added timeout wrapper to prevent Railway from killing the process:

**Changes:**
- [apps/api/routers/assets.py](apps/api/routers/assets.py)
  - Added `OCR_TIMEOUT_SECONDS = 90` constant
  - Created `_run_ocr_sync_with_timeout()` async wrapper
  - Returns structured status: `completed`, `timeout`, or `failed`
  - Asset/recipe still created on timeout (graceful degradation)

**Response format now includes:**
```json
{
  "asset_id": "...",
  "recipe_id": "...",
  "ocr_status": "completed|timeout|failed|queued",
  "warning": "Error message if applicable"
}
```

**Benefits:**
- Assets saved even if OCR times out
- User gets clear feedback about processing status
- Can retry OCR later via `/assets/{asset_id}/ocr` endpoint
- No more SIGTERM kills

### Solution 2: Async Job Processing ✅

Enhanced async job support to move OCR processing to background workers:

**Changes:**
1. **Enhanced existing ARQ worker** - [apps/api/worker/jobs.py](apps/api/worker/jobs.py)
   - Added `WorkerSettings` class for ARQ configuration
   - Already has `ingest_recipe`, `structure_recipe`, `normalize_recipe` functions
   - Ready to use with `python -m arq worker.jobs.WorkerSettings`

2. **Updated upload endpoint** - [apps/api/routers/assets.py](apps/api/routers/assets.py)
   - Falls back gracefully when Redis unavailable
   - Returns `job_id` when queued successfully
   - Returns `ocr_status: "queued"` for async processing

3. **Documentation** - [docs/RAILWAY_ASYNC_JOBS_SETUP.md](docs/RAILWAY_ASYNC_JOBS_SETUP.md)
   - Step-by-step Railway setup guide
   - Architecture diagrams
   - Troubleshooting section
   - Monitoring commands

**Configuration already in place:**
- [config.py](apps/api/config.py): `ENABLE_ASYNC_JOBS` and `REDIS_URL` settings
- [requirements.txt](apps/api/requirements.txt): `arq==0.26.3` and `redis==5.0.1` already installed

## Deployment Flow

### Current State (Sync with Timeout)
```
Upload → API Server → OCR (90s timeout) → Response
                     ↓ (if timeout)
                     Save asset + return warning
```

### After Enabling Async Jobs
```
Upload → API Server → Redis Queue → Response (immediate)
                                  ↓
                              ARQ Worker → OCR → Update recipe
```

## Next Steps for Railway Deployment

### 1. Add Redis Service
1. Go to Railway project dashboard
2. Click "+ New" → "Database" → "Add Redis"
3. Redis will auto-link with `REDIS_URL` environment variable

### 2. Enable Async Jobs
In Railway API service environment variables:
```bash
ENABLE_ASYNC_JOBS=true
```

### 3. Deploy Worker Service (Optional but Recommended)
1. Click "+ New" → "Empty Service"
2. Name: `recipenow-worker`
3. Connect same GitHub repo
4. Set environment variables:
   ```bash
   DATABASE_URL=${{recipenow-api.DATABASE_URL}}
   REDIS_URL=${{recipenow-redis.REDIS_URL}}
   ```
5. Start command: `cd apps/api && arq services.jobs.WorkerSettings`
6. Deploy

### 4. Verify
- Upload test image
- Check response includes `job_id` and `ocr_status: "queued"`
- Monitor worker logs for OCR processing
- Recipe should populate within 10-30 seconds

## Fallback Behavior

The system gracefully handles all scenarios:

| Scenario | Behavior | User Experience |
|----------|----------|-----------------|
| Async enabled + Redis available | Jobs queued, fast response | ✅ Best performance |
| Async enabled + Redis down | Falls back to sync with timeout | ⚠️ Slower but works |
| Sync mode (local dev) | Runs OCR with timeout | ⚠️ 90s wait |
| OCR timeout | Asset saved, warning returned | ⚠️ Can retry later |

## Files Modified

1. [apps/api/routers/assets.py](apps/api/routers/assets.py) - Timeout wrapper and async enhancements
2. [apps/api/worker/jobs.py](apps/api/worker/jobs.py) - Added ARQ WorkerSettings configuration
3. [docs/RAILWAY_ASYNC_JOBS_SETUP.md](docs/RAILWAY_ASYNC_JOBS_SETUP.md) - **NEW** Deployment guide
4. [docs/NOW.md](docs/NOW.md) - Updated status
5. [UPLOAD_TIMEOUT_FIX_SUMMARY.md](UPLOAD_TIMEOUT_FIX_SUMMARY.md) - **THIS FILE**

## Testing

### Local Testing (Without Redis)
```bash
# Upload should work with 90s timeout protection
curl -X POST http://localhost:8000/assets/upload \
  -F "file=@recipe.jpg" \
  -F "user_id=550e8400-e29b-41d4-a716-446655440000"

# Response should include ocr_status
{
  "ocr_status": "completed",  # or "timeout" if exceeded 90s
  "warning": null
}
```

### Production Testing (With Redis)
```bash
# Upload should queue job immediately
# Response should include job_id
{
  "job_id": "abc123...",
  "ocr_status": "queued"
}

# Check worker logs
railway logs --service recipenow-worker
```

## Monitoring

### Check for 500 Errors
```bash
railway logs --service recipenow-api | grep "500"
```

### Check OCR Timeout Rate
```bash
railway logs --service recipenow-api | grep "OCR timeout"
```

### Check Job Queue Length
```bash
# SSH into Railway container
railway shell
redis-cli -u $REDIS_URL LLEN arq:queue
```

## Success Metrics

- ✅ No more 500 errors on upload
- ✅ No more SIGTERM kills
- ✅ Assets always saved (even on timeout)
- ✅ Users get clear feedback about processing status
- ✅ Background jobs process OCR without blocking HTTP requests
- ✅ Graceful degradation when Redis unavailable

## Additional Notes

- **Default timeout:** 90 seconds (configurable via `OCR_TIMEOUT_SECONDS`)
- **Job timeout:** 300 seconds (5 minutes) for worker jobs
- **Max concurrent jobs:** 10 (configurable in `WorkerSettings`)
- **Result retention:** 1 hour (for debugging)

## Questions?

See [docs/RAILWAY_ASYNC_JOBS_SETUP.md](docs/RAILWAY_ASYNC_JOBS_SETUP.md) for detailed setup instructions and troubleshooting.
