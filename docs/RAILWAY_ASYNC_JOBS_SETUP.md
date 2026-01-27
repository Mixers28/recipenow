# Railway Async Jobs Setup Guide

## Problem: 500 Errors on Upload Due to OCR Timeout

When uploading images, the synchronous OCR processing can exceed Railway's request timeout limits (typically 100 seconds), causing:
- 500 Internal Server Error responses
- SIGTERM process kills (visible in logs as `FatalError: Termination signal`)
- Poor user experience with failed uploads

## Solution: Enable Async Job Processing with Redis

The application supports background job processing using Redis and ARQ (Asynchronous Request Queue). This moves OCR processing out of the HTTP request cycle into background workers.

## Architecture

```
┌─────────────┐     HTTP     ┌──────────────┐     Queue     ┌──────────────┐
│   Client    │────────────▶ │  API Server  │──────────────▶│ Redis Queue  │
│  (Upload)   │  200 OK      │   (FastAPI)  │   Job         └──────────────┘
└─────────────┘  Immediate   └──────────────┘                       │
                                                                     │
                                                                     ▼
                                                             ┌──────────────┐
                                                             │ ARQ Worker   │
                                                             │   (OCR)      │
                                                             └──────────────┘
```

## Steps to Enable Async Jobs in Railway

### 1. Add Redis Service to Railway Project

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Database"** → **"Add Redis"**
3. Railway will automatically:
   - Provision a Redis instance
   - Create a `REDIS_URL` environment variable
   - Link it to your API service

### 2. Enable Async Jobs in API Service

In your Railway API service environment variables, add:

```bash
ENABLE_ASYNC_JOBS=true
```

The `REDIS_URL` should already be set automatically by Railway when you added Redis.

### 3. Deploy ARQ Worker Service (Optional but Recommended)

For production, run a dedicated worker service:

1. In Railway project, click **"+ New"** → **"Empty Service"**
2. Name it `recipenow-worker`
3. Connect the same GitHub repo
4. Set the following environment variables:
   ```bash
   DATABASE_URL=${{recipenow-api.DATABASE_URL}}
   REDIS_URL=${{recipenow-redis.REDIS_URL}}
   ```
5. Set the **Start Command** to:
   ```bash
   cd apps/api && python -m arq worker.jobs.WorkerSettings
   ```
6. Deploy

### 4. Verify Setup

After deployment, test an upload:

1. Upload a recipe image through the frontend
2. Check the API response - it should include:
   ```json
   {
     "asset_id": "...",
     "recipe_id": "...",
     "job_id": "abc123...",
     "ocr_status": "queued",
     "warning": null
   }
   ```
3. The recipe will be populated in the background (typically 10-30 seconds)
4. Check Railway logs for the worker service to see OCR processing

## Fallback Behavior

The application gracefully handles various scenarios:

### Scenario 1: Async Jobs Enabled + Redis Available
- ✅ Jobs queued to Redis
- ✅ Worker processes in background
- ✅ Fast HTTP response (< 1 second)

### Scenario 2: Async Jobs Enabled + Redis Unavailable
- ⚠️ Falls back to sync OCR with timeout (90 seconds)
- ⚠️ Returns warning if timeout exceeded
- ✅ Asset still saved, can retry OCR later

### Scenario 3: Async Jobs Disabled (Local Development)
- ⚠️ Runs sync OCR with timeout
- ✅ Good for testing
- ⚠️ Not recommended for production

## Timeout Protection

Even when running synchronously (fallback mode), the application now has timeout protection:

- **Timeout**: 90 seconds (configurable via `OCR_TIMEOUT_SECONDS`)
- **Behavior on timeout**:
  - Asset and recipe are still created
  - Returns `ocr_status: "timeout"`
  - Returns warning message
  - User can retry OCR processing later via `/assets/{asset_id}/ocr` endpoint

## Response Fields

The `/assets/upload` endpoint now returns:

```typescript
{
  asset_id: string;          // Asset UUID
  recipe_id: string;         // Recipe UUID
  storage_path: string;      // File storage path
  sha256: string;            // File hash
  job_id?: string;           // ARQ job ID (if async)
  ocr_status?: string;       // "queued" | "completed" | "timeout" | "failed"
  warning?: string;          // Error message if OCR failed/timed out
}
```

## Monitoring

### Check Redis Connection
In Railway API logs, you should see:
```
INFO - Redis URL configured: redis://...
INFO - Async jobs enabled: True
```

### Check Job Queue
```bash
# SSH into Railway container
railway shell

# Check Redis
redis-cli -u $REDIS_URL
> KEYS arq:*
> LLEN arq:queue
```

### Check Worker Logs
In Railway worker service logs, you should see:
```
INFO - Starting ARQ worker
INFO - Processing job: ingest_job(asset_id=...)
INFO - OCR extracted 45 lines from asset ...
```

## Cost Considerations

### Redis Pricing (Railway)
- **Hobby Plan**: ~$5/month for small Redis instance
- **Pro Plan**: Scales with usage

### Worker Service
- Can run on the same service as API (no extra cost)
- Or run dedicated worker for better resource isolation

## Troubleshooting

### Issue: "Failed to enqueue async job"
- Check `REDIS_URL` is set correctly
- Verify Redis service is running in Railway
- Check Railway logs for connection errors

### Issue: Jobs queued but not processing
- Ensure worker service is running
- Check worker has correct `DATABASE_URL` and `REDIS_URL`
- Verify start command is correct

### Issue: Still getting timeouts
- If using sync fallback, increase `OCR_TIMEOUT_SECONDS` in code
- Add more memory to Railway service (Settings → Resources)
- Enable async jobs to move OCR to background

## Related Files

- [apps/api/routers/assets.py](../apps/api/routers/assets.py) - Upload endpoint with timeout handling
- [apps/api/worker/jobs.py](../apps/api/worker/jobs.py) - ARQ worker jobs and configuration
- [apps/api/config.py](../apps/api/config.py) - Configuration settings
- [apps/api/requirements.txt](../apps/api/requirements.txt) - Dependencies (arq, redis)

## Next Steps

1. Enable async jobs in Railway (follow steps above)
2. Monitor upload performance and success rates
3. Consider adding retry logic for failed jobs
4. Add user notifications when OCR completes
