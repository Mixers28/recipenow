# Railway Migration 002 Application Guide

**Migration:** Add `source_method` column to `source_spans` table
**Purpose:** Track whether fields were extracted via OCR or LLM vision
**Status:** Ready to apply (idempotent - safe to run multiple times)
**Risk Level:** 🟢 Low (backward compatible, non-breaking)

---

## Prerequisites

- [ ] Railway CLI installed (`npm i -g @railway/cli` or `brew install railway`)
- [ ] Railway account with access to RecipeNow project
- [ ] `psql` client installed (for database access)
- [ ] Migration scripts executable (`chmod +x scripts/*.sh`)

---

## Option A: Apply via Railway CLI (Recommended)

### Step 1: Login to Railway

```bash
# Login to Railway
railway login

# Link to your RecipeNow project
cd /mnt/e/GD/RecipeNow
railway link
```

### Step 2: Get Database Connection String

```bash
# Get DATABASE_URL from Railway
export DATABASE_URL=$(railway variables get DATABASE_URL)

# Verify connection
echo $DATABASE_URL
# Should look like: postgresql://postgres:****@containers-us-west-xxx.railway.app:6543/railway
```

### Step 3: Test Connection

```bash
# Test database connectivity
psql "$DATABASE_URL" -c "SELECT version();"

# Expected output: PostgreSQL version info
```

### Step 4: Check Current Migration Status

```bash
# Run pre-flight check
./scripts/check_migration_002.sh "$DATABASE_URL"

# Expected outcomes:
# ✅ Migration already applied → Safe to skip (idempotent)
# ⚠️  Migration NOT applied → Proceed to Step 5
```

### Step 5: Apply Migration

```bash
# Apply migration 002
./scripts/apply_migration_002.sh "$DATABASE_URL"

# Script will:
# 1. Verify source_spans table exists
# 2. Check if migration already applied
# 3. Count existing records (backup point)
# 4. Apply migration (add column + indexes)
# 5. Verify column and indexes created
# 6. Confirm record count unchanged
```

**Expected Output:**
```
🚀 Applying Migration 002: Add source_method to source_spans
==================================================

1️⃣  Pre-flight checks...
✅ source_spans table exists
✅ Migration 002 not yet applied - ready to proceed

2️⃣  Creating backup point...
Current source_spans records: 42

3️⃣  Applying migration...
ALTER TABLE
CREATE INDEX
CREATE INDEX
COMMENT

✅ Migration applied successfully!

4️⃣  Verifying migration...
✅ source_method column created
✅ Indexes created (2 found)

5️⃣  Final schema verification:
 column_name    | data_type | column_default | is_nullable
----------------+-----------+----------------+-------------
 id             | uuid      |                | NO
 recipe_id      | uuid      |                | NO
 field_path     | varchar   |                | NO
 asset_id       | uuid      |                | NO
 page           | integer   | 0              | NO
 bbox           | jsonb     |                | NO
 ocr_confidence | double    | 0.0            | NO
 extracted_text | text      |                | YES
 source_method  | varchar   | 'ocr'::varchar | NO
 created_at     | timestamp | CURRENT_TIMESTAMP | NO

✅ Record count unchanged: 42 records

==================================================
✅ Migration 002 completed successfully!
```

### Step 6: Verify Application Health

```bash
# Check Railway service logs
railway logs --service api

# Look for:
# ✅ No errors on startup
# ✅ API endpoints responding
# ✅ No database connection errors
```

### Step 7: Test Source Method Tracking

```bash
# Query source_spans to verify default values
psql "$DATABASE_URL" -c "
  SELECT
    source_method,
    COUNT(*) as count
  FROM source_spans
  GROUP BY source_method;
"

# Expected output:
#  source_method | count
# ---------------+-------
#  ocr           |    42
# (1 row)
```

---

## Option B: Apply via Railway Dashboard (Alternative)

### Step 1: Access Railway Database

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Select your RecipeNow project
3. Click on "Postgres" service
4. Click "Data" tab → "Query" button

### Step 2: Check Current Schema

```sql
-- Check if migration already applied
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name='source_spans'
  AND column_name='source_method';
```

**If returns 0 rows:** Migration NOT applied → proceed to Step 3
**If returns 1 row:** Migration already applied → STOP (idempotent, but no need to re-run)

### Step 3: Apply Migration (Copy-Paste SQL)

Copy the entire contents of [002_add_source_method.sql](../infra/migrations/002_add_source_method.sql) and paste into Railway query editor:

```sql
-- Add source_method column to source_spans table
ALTER TABLE source_spans
ADD COLUMN IF NOT EXISTS source_method VARCHAR(20) DEFAULT 'ocr' NOT NULL;

-- Create index for efficient filtering by source method
CREATE INDEX IF NOT EXISTS idx_source_spans_source_method
ON source_spans(source_method);

-- Create composite index for recipe + source method queries
CREATE INDEX IF NOT EXISTS idx_source_spans_recipe_method
ON source_spans(recipe_id, source_method);

-- Add comment for documentation
COMMENT ON COLUMN source_spans.source_method IS
'Method used to extract this span: "ocr" for OCR extraction, "llm-vision" for LLM vision reader fallback';
```

Click "Run" and verify:
- ✅ `ALTER TABLE` succeeds
- ✅ `CREATE INDEX` succeeds (2 indexes)
- ✅ `COMMENT` succeeds

### Step 4: Verify Schema

```sql
-- Verify column exists
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name='source_spans'
ORDER BY ordinal_position;

-- Verify indexes created
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'source_spans'
  AND indexname LIKE '%source_method%';
```

---

## Option C: Apply via Local Tunnel (Advanced)

If you need to apply migration from local scripts but Railway CLI is unavailable:

### Step 1: Create Railway Tunnel

```bash
# Start tunnel to Railway Postgres
railway connect postgres
# This will print: postgresql://localhost:5432/railway

# In another terminal, set DATABASE_URL
export DATABASE_URL="postgresql://localhost:5432/railway"
```

### Step 2: Apply Migration

```bash
# Run migration script
./scripts/apply_migration_002.sh "$DATABASE_URL"
```

---

## Post-Migration Verification

### Check 1: API Health

```bash
# Test API endpoint
curl https://your-railway-api.railway.app/health

# Expected: {"status": "ok", "version": "0.1"}
```

### Check 2: Upload Test Recipe

```bash
# Upload a test recipe image
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@tests/fixtures/recipe_upright.jpg" \
  https://your-railway-api.railway.app/api/assets/upload

# Verify source_spans created with source_method='ocr'
```

### Check 3: Query Source Spans

```bash
psql "$DATABASE_URL" -c "
  SELECT
    id,
    recipe_id,
    field_path,
    source_method,
    ocr_confidence
  FROM source_spans
  ORDER BY created_at DESC
  LIMIT 5;
"

# Expected: Recent records should have source_method='ocr'
```

### Check 4: Monitor Logs for 24 Hours

```bash
# Watch Railway logs for errors
railway logs --tail --service api

# Look for:
# ❌ Any database errors related to source_method
# ❌ Any SourceSpan creation failures
# ✅ Normal OCR extraction logs
# ✅ Recipe creation logs
```

---

## Rollback Procedure (If Needed)

**⚠️ Only use if migration causes critical issues**

### Step 1: Verify Issue

```bash
# Check error logs
railway logs --service api | grep -i "error\|source_method"

# Confirm source_method is the root cause
```

### Step 2: Execute Rollback

```bash
# Get DATABASE_URL
export DATABASE_URL=$(railway variables get DATABASE_URL)

# Run rollback script
./scripts/rollback_migration_002.sh "$DATABASE_URL"

# Script will:
# 1. Warn about data loss (source_method values)
# 2. Drop indexes
# 3. Drop source_method column
# 4. Verify rollback successful
```

### Step 3: Restart Services

```bash
# Restart API service
railway up --service api

# Monitor logs
railway logs --tail --service api
```

---

## Troubleshooting

### Issue: "psql: command not found"

**Solution:**
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# Windows (WSL)
sudo apt-get install postgresql-client
```

### Issue: "connection refused" to Railway database

**Solution:**
```bash
# Verify DATABASE_URL is correct
echo $DATABASE_URL

# Check Railway service status
railway status

# Try re-authenticating
railway logout
railway login
```

### Issue: "permission denied" on migration scripts

**Solution:**
```bash
# Make scripts executable
chmod +x scripts/check_migration_002.sh
chmod +x scripts/apply_migration_002.sh
chmod +x scripts/rollback_migration_002.sh
```

### Issue: Migration says "already applied" but column missing

**Solution:**
```bash
# Force re-check
psql "$DATABASE_URL" -c "
  SELECT column_name
  FROM information_schema.columns
  WHERE table_name='source_spans';
"

# If source_method truly missing, migration is idempotent - safe to re-run
./scripts/apply_migration_002.sh "$DATABASE_URL"
```

### Issue: Record count changed after migration

**Cause:** This should NOT happen (DDL-only migration)

**Solution:**
```bash
# Investigate
psql "$DATABASE_URL" -c "
  SELECT COUNT(*) FROM source_spans;
"

# If records lost, this is critical - contact database admin
# Migration does not DELETE data, only ADD column
```

---

## Success Criteria Checklist

- [ ] Migration script completes without errors
- [ ] `source_method` column exists in `source_spans` table
- [ ] Default value is `'ocr'` for existing records
- [ ] Two indexes created: `idx_source_spans_source_method`, `idx_source_spans_recipe_method`
- [ ] Record count unchanged (verify before/after)
- [ ] API service starts without errors
- [ ] Test recipe upload creates source_spans with `source_method='ocr'`
- [ ] Railway logs show no database errors for 24 hours
- [ ] GET /recipes/{id} endpoint includes `source_method` in response

---

## Timeline Estimate

- **Option A (Railway CLI):** 10-15 minutes
- **Option B (Dashboard):** 5-10 minutes
- **Option C (Local Tunnel):** 15-20 minutes

**Total downtime:** 0 seconds (migration is non-blocking, backward compatible)

---

## Next Steps After Migration

1. ✅ Mark migration 002 as complete in [NOW.md](NOW.md)
2. ⏭️ Execute QA testing per [TESTING_GUIDE.md](TESTING_GUIDE.md)
3. ⏭️ Implement Sprint 5 UI badges (color-coded source attribution)
4. ⏭️ Test LLM vision fallback creates `source_method='llm-vision'` spans

---

**Last Updated:** 2026-01-26
**Author:** Claude Sonnet 4.5
**Status:** Ready for Production
**Related Docs:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md), [TESTING_GUIDE.md](TESTING_GUIDE.md)
