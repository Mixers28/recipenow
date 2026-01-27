# Ollama Deployment to Railway - Step-by-Step Guide

## Overview

This guide walks you through deploying Ollama + LLaVA-7B to Railway as a separate service that your RecipeNow API can use for LLM vision extraction.

## Prerequisites

- Railway account with active project (you already have this)
- Railway CLI installed (optional but helpful)
- Your RecipeNow project already deployed to Railway

---

## Step 1: Create Ollama Service in Railway

### Via Railway Dashboard:

1. **Go to your Railway project dashboard**
   - Navigate to https://railway.app
   - Open your RecipeNow project

2. **Add a new service**
   - Click **"+ New"** button
   - Select **"Empty Service"**
   - Name it: `recipenow-ollama`

3. **Configure the service**
   - Go to the service settings
   - Under **"Source"**, select **"Deploy from Docker Image"**
   - Enter Docker image: `ollama/ollama:latest`

4. **Set environment variables**
   - Click **"Variables"** tab
   - Add the following variables:

   ```bash
   OLLAMA_HOST=0.0.0.0:11434
   ```

5. **Configure resources** (Important!)
   - Click **"Settings"** tab
   - Scroll to **"Resources"**
   - Set minimum memory: **2048 MB** (2 GB)
   - Set minimum CPU: **1 vCPU**

   > **Note:** LLaVA-7B requires at least 8GB RAM ideally, but Railway may limit this. Start with 2GB and increase if needed. The model will be slower but functional.

6. **Deploy the service**
   - Click **"Deploy"**
   - Wait for deployment to complete (check logs)

---

## Step 2: Pull LLaVA Model into Ollama Service

Once the Ollama service is running, you need to pull the LLaVA model.

### Option A: Via Railway Shell (Recommended)

1. **Open Railway Shell**
   - In your `recipenow-ollama` service
   - Click **"..."** menu → **"Shell"**

2. **Pull the LLaVA model**
   ```bash
   ollama pull llava:7b
   ```

   This will take 5-10 minutes (downloads ~4.5GB model)

3. **Verify model is installed**
   ```bash
   ollama list
   ```

   You should see:
   ```
   NAME           ID              SIZE      MODIFIED
   llava:7b       abc123...       4.5 GB    2 minutes ago
   ```

### Option B: Via Railway CLI

If you have Railway CLI installed:

```bash
# Login to Railway
railway login

# Link to your project
railway link

# Connect to Ollama service shell
railway run -s recipenow-ollama -- sh

# Pull model
ollama pull llava:7b

# Exit
exit
```

---

## Step 3: Get Ollama Service Internal URL

Railway services can communicate internally using private networking.

1. **Find the internal URL**
   - In your `recipenow-ollama` service
   - Click **"Settings"** tab
   - Look for **"Private Networking"** section
   - Copy the internal URL (format: `recipenow-ollama.railway.internal:11434`)

   OR

   - Railway auto-generates a public URL
   - Go to **"Settings"** → **"Networking"**
   - Copy the generated domain (format: `recipenow-ollama-production.up.railway.app`)

2. **Choose the right URL format:**
   - **Internal (recommended):** `http://recipenow-ollama.railway.internal:11434`
   - **Public:** `https://recipenow-ollama-production.up.railway.app`

---

## Step 4: Configure RecipeNow API to Use Ollama

1. **Go to your RecipeNow API service**
   - Navigate to `recipenow-api` service in Railway

2. **Add Ollama environment variable**
   - Click **"Variables"** tab
   - Add new variable:

   ```bash
   OLLAMA_HOST=http://recipenow-ollama.railway.internal:11434
   ```

   OR if using public URL:

   ```bash
   OLLAMA_HOST=https://recipenow-ollama-production.up.railway.app
   ```

3. **Optional: Configure LLM fallback** (for redundancy)
   - Add these variables if you want cloud backup:

   ```bash
   LLM_FALLBACK_ENABLED=true
   LLM_FALLBACK_PROVIDER=claude
   LLM_FALLBACK_API_KEY=your-anthropic-api-key
   ```

4. **Redeploy API service**
   - Railway should auto-redeploy when you save variables
   - Or manually trigger: Click **"..."** → **"Redeploy"**

---

## Step 5: Verify LLM Vision is Working

### Test the Integration

1. **Check API logs**
   - Go to `recipenow-api` service
   - Click **"Deployments"** → **"View Logs"**

2. **Upload a test recipe image**
   - Go to your RecipeNow frontend (Vercel URL)
   - Upload a recipe image

3. **Look for these log messages:**
   ```
   INFO - Running LLM vision extraction for asset <asset_id>
   INFO - LLM vision extracted: ['title', 'ingredients', 'steps']
   INFO - LLM vision extraction successful: title=True, ingredients=10, steps=5
   ```

4. **If successful, you'll also see:**
   ```
   INFO - Recipe <recipe_id> created with X source spans
   ```

### Check Source Method Attribution

1. **View the recipe in the UI**
   - Go to the Review page
   - Check the recipe fields

2. **Verify source attribution**
   - All fields should show `source_method: "llm-vision"` in the database
   - You can verify via Railway database query or API response

---

## Step 6: Monitor Performance

### Check Ollama Service Health

```bash
# Via Railway Shell in recipenow-ollama service
curl http://localhost:11434/api/tags
```

Expected response:
```json
{
  "models": [
    {
      "name": "llava:7b",
      "modified_at": "...",
      "size": 4733363936
    }
  ]
}
```

### Monitor API Logs

Watch for these patterns:

**Success:**
```
INFO - LLM vision extraction successful
```

**Fallback to OCR:**
```
WARNING - LLM vision extraction failed, falling back to OCR parser
```

**Timeout Issues:**
```
ERROR - Ollama request timeout
```

---

## Troubleshooting

### Issue 1: Ollama Service Out of Memory

**Symptoms:**
- Service crashes
- Logs show `OOMKilled`

**Solution:**
1. Increase memory in Railway service settings
2. Or use a smaller model: `ollama pull llava:13b-q4` (quantized, smaller)

### Issue 2: Model Not Found

**Symptoms:**
```
ERROR - model 'llava:7b' not found
```

**Solution:**
1. Shell into Ollama service
2. Run `ollama pull llava:7b` again
3. Verify with `ollama list`

### Issue 3: Connection Refused

**Symptoms:**
```
ERROR - Connection refused to Ollama
```

**Solution:**
1. Verify `OLLAMA_HOST` environment variable is correct
2. Check internal networking is enabled
3. Try using public URL instead of internal

### Issue 4: Slow Responses

**Symptoms:**
- LLM vision takes > 60 seconds
- Timeouts occur

**Solution:**
1. Increase memory allocation (more RAM = faster inference)
2. Enable async jobs so extraction doesn't block HTTP requests
3. Consider using cloud fallback (Claude Haiku is much faster)

---

## Cost Estimates

### Railway Pricing (as of 2026)

**Ollama Service:**
- **Hobby Plan:** $5/month base + resource usage
- **Pro Plan:** Usage-based
  - Memory: ~$0.000231/GB-hour
  - CPU: ~$0.000463/vCPU-hour

**Estimated Monthly Cost:**
- With 2GB RAM, 1 vCPU, 24/7 uptime:
  - Memory: 2 GB × 730 hours × $0.000231 = ~$3.37
  - CPU: 1 vCPU × 730 hours × $0.000463 = ~$3.38
  - **Total:** ~$6.75/month

**Alternative: Cloud LLM Fallback**
- Claude 3 Haiku: $0.25 per million input tokens (~$0.003 per recipe)
- 1000 recipes/month = ~$3/month
- Faster, no infrastructure management

---

## Alternative: Local Development Setup

For local testing before Railway deployment:

1. **Install Ollama locally**
   ```bash
   curl https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama**
   ```bash
   ollama serve
   ```

3. **Pull LLaVA model**
   ```bash
   ollama pull llava:7b
   ```

4. **Update your local .env**
   ```bash
   OLLAMA_HOST=http://localhost:11434
   ```

5. **Test extraction**
   - Upload recipe via frontend
   - Check API logs for LLM vision extraction

---

## Next Steps After Deployment

1. **Enable Async Jobs** (if not already enabled)
   - Follow [docs/RAILWAY_ASYNC_JOBS_SETUP.md](RAILWAY_ASYNC_JOBS_SETUP.md)
   - This moves LLM extraction to background workers
   - Prevents HTTP timeout issues

2. **Test with Various Recipe Images**
   - Two-column layouts
   - Rotated images
   - Handwritten recipes
   - Complex layouts

3. **Monitor Extraction Quality**
   - Compare LLM vision vs OCR results
   - Check source_method attribution
   - Verify field completeness

4. **Optimize if Needed**
   - Adjust memory/CPU resources
   - Enable cloud fallback for reliability
   - Consider caching common extractions

---

## Summary Checklist

- [ ] Create Ollama service in Railway
- [ ] Pull LLaVA-7B model into Ollama
- [ ] Get Ollama internal URL
- [ ] Configure API service with OLLAMA_HOST
- [ ] Test recipe upload and verify LLM extraction
- [ ] Monitor logs for success/errors
- [ ] Optional: Enable async jobs for background processing
- [ ] Optional: Configure cloud fallback for redundancy

**Estimated Setup Time:** 20-30 minutes

**Ready to Deploy!** Follow the steps above and your RecipeNow app will use LLM vision for primary extraction.
