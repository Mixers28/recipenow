# RecipeNow Deployment Setup Guide

This guide explains how to configure environment variables for proper communication between the Vercel frontend and Railway backend.

## Overview

- **Frontend**: `https://recipenow-seven.vercel.app` (Vercel)
- **Backend**: `https://recipenow-production.up.railway.app` (Railway)

Both services need proper environment variable configuration to communicate securely.

## Backend Setup (Railway)

### CORS Configuration

The backend needs to know which domains are allowed to make requests to it. This is configured via the `ALLOWED_ORIGINS` environment variable.

**Steps to set on Railway:**

1. Go to your Railway project dashboard
2. Navigate to the `recipenow-api` service
3. Click on the "Variables" tab
4. Add or update the `ALLOWED_ORIGINS` variable with:

```
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://recipenow-seven.vercel.app
```

This allows:
- `http://localhost:3000` - Local development (port 3000)
- `http://localhost:5173` - Vite dev server (port 5173)
- `https://recipenow-seven.vercel.app` - Production Vercel frontend

### Logging Configuration

Optionally, you can control the backend logging level via the `LOG_LEVEL` variable:

```
LOG_LEVEL=INFO
```

Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### How to Update Variables on Railway

1. **Via Railway CLI:**
   ```bash
   railway variables set ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173,https://recipenow-seven.vercel.app"
   ```

2. **Via Railway Dashboard:**
   - Service → Variables → Add variable
   - Name: `ALLOWED_ORIGINS`
   - Value: `http://localhost:3000,http://localhost:5173,https://recipenow-seven.vercel.app`
   - Click "Save"
   - Redeploy service

## Frontend Setup (Vercel)

### API Endpoint Configuration

The frontend needs to know where the backend API is located. This is configured via the `NEXT_PUBLIC_API_URL` environment variable.

**Steps to set on Vercel:**

1. Go to your Vercel project dashboard
2. Navigate to Settings → Environment Variables
3. Add a new environment variable:
   - **Name**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://recipenow-production.up.railway.app/api`
   - **Environments**: Select all (Production, Preview, Development)

4. Click "Save"
5. Trigger a redeployment (Settings → Git → Redeploy or push to main branch)

### How to Update Variables on Vercel

1. **Via Vercel Dashboard:**
   - Project → Settings → Environment Variables
   - Add variable with name `NEXT_PUBLIC_API_URL`
   - Set value to `https://recipenow-production.up.railway.app/api`
   - Apply to all environments

2. **Via Vercel CLI:**
   ```bash
   vercel env add NEXT_PUBLIC_API_URL
   # Follow the prompts to enter the value: https://recipenow-production.up.railway.app/api
   ```

3. **Note**: Any changes require a redeploy to take effect

## Local Development Setup

### Backend (Local)

1. Navigate to `apps/api`
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. (Optional) Modify `.env` if needed for local configuration

4. Start the backend:
   ```bash
   python -m uvicorn main:app --reload
   ```

The backend runs on `http://localhost:8000`

### Frontend (Local)

1. Navigate to `apps/web`
2. Copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```

3. Default value is already set to `http://localhost:8000/api`

4. Start the frontend:
   ```bash
   npm run dev
   ```

The frontend runs on `http://localhost:3000` or `http://localhost:5173` (depending on your setup)

## Verification

### Test Backend CORS

```bash
# Test if CORS is working (should return 200 and not block the request)
curl -X OPTIONS https://recipenow-production.up.railway.app/api/recipes \
  -H "Origin: https://recipenow-seven.vercel.app" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

Look for these headers in the response:
```
Access-Control-Allow-Origin: https://recipenow-seven.vercel.app
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
```

### Test Frontend to Backend Communication

1. Open the Vercel frontend: `https://recipenow-seven.vercel.app`
2. Open browser DevTools → Network tab
3. Try an operation (e.g., navigate to Library)
4. Check that API requests go to `https://recipenow-production.up.railway.app/api`
5. Verify no CORS errors in Console

If you see CORS errors like:
```
Access to XMLHttpRequest at 'https://recipenow-production.up.railway.app/api/recipes'
from origin 'https://recipenow-seven.vercel.app' has been blocked by CORS policy
```

Then check:
1. Backend has `ALLOWED_ORIGINS` variable set correctly
2. Frontend has `NEXT_PUBLIC_API_URL` variable set correctly
3. Both services have been redeployed after variable changes

## Troubleshooting

### CORS Errors in Browser Console

**Problem**: `Access to fetch at '...' from origin '...' has been blocked by CORS policy`

**Solutions:**
1. Verify `ALLOWED_ORIGINS` is set on Railway backend
2. Verify the Vercel domain exactly matches one of the origins in the list
3. Redeploy the Railway backend after changing `ALLOWED_ORIGINS`
4. Wait 2-3 minutes for changes to propagate

### Frontend Can't Find Backend

**Problem**: Requests go to `localhost:8000` instead of production URL

**Solutions:**
1. Verify `NEXT_PUBLIC_API_URL` is set in Vercel dashboard
2. Verify the value is `https://recipenow-production.up.railway.app/api` (note the `/api` suffix)
3. Redeploy the Vercel frontend after changing environment variables
4. Check that `NEXT_PUBLIC_` prefix is present (this makes the variable available in browser)

### 5xx Errors from Backend

**Check backend logs on Railway:**
```bash
railway logs -s recipenow-api
```

Look for errors related to:
- Database connection issues
- Missing required environment variables
- Request processing failures

## Backend Logging

The backend logs all requests and errors. To view logs:

**On Railway:**
```bash
railway logs -s recipenow-api
```

**Logs are written to:**
- Console output (viewed via Railway logs)
- `/var/log/recipe-now/app.log` - All application logs
- `/var/log/recipe-now/error.log` - Error-level logs

See [LOGGING_GUIDE.md](apps/api/LOGGING_GUIDE.md) for detailed logging information.

## Environment Variables Summary

### Backend (Railway) - `apps/api/.env`

| Variable | Example | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:3000,https://recipenow-seven.vercel.app` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `API_TITLE` | `RecipeNow API` | API title (optional) |
| `API_VERSION` | `0.1.0` | API version (optional) |
| `DATABASE_URL` | `postgresql://...` | Database connection string |

### Frontend (Vercel) - Environment Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://recipenow-production.up.railway.app/api` | Backend API endpoint |

**Note**: `NEXT_PUBLIC_` prefix means this variable is accessible in the browser. Never put secrets in variables with this prefix.

## Next Steps

1. ✅ Ensure `ALLOWED_ORIGINS` is set on Railway
2. ✅ Ensure `NEXT_PUBLIC_API_URL` is set on Vercel
3. ✅ Both services should be redeployed
4. ✅ Test frontend-backend communication
5. ✅ Check browser console and backend logs for any errors
