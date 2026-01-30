# Migration 002 - Quick Start (Railway)

**TL;DR:** Add `source_method` column to track OCR vs LLM-vision extraction

---

## 🚀 Fast Track (5 minutes)

```bash
# 1. Login to Railway
railway login
cd /mnt/e/GD/RecipeNow
railway link

# 2. Get database URL
export DATABASE_URL=$(railway variables get DATABASE_URL)

# 3. Check status
./scripts/check_migration_002.sh "$DATABASE_URL"

# 4. Apply migration
./scripts/apply_migration_002.sh "$DATABASE_URL"

# 5. Verify
railway logs --service api
```

**Done!** ✅

---

## 📋 What Gets Changed

- ✅ Adds `source_method` column (VARCHAR, default `'ocr'`)
- ✅ Creates 2 indexes for performance
- ✅ Backward compatible (all existing records default to `'ocr'`)
- ✅ Zero downtime
- ✅ Idempotent (safe to run multiple times)

---

## 🔍 Verification

```bash
# Check column exists
psql "$DATABASE_URL" -c "
  SELECT column_name, column_default
  FROM information_schema.columns
  WHERE table_name='source_spans'
    AND column_name='source_method';
"

# Expected output:
#  column_name  | column_default
# --------------+----------------
#  source_method| 'ocr'::varchar
```

---

## ⚠️ Rollback (If Needed)

```bash
# Only if critical issues occur
./scripts/rollback_migration_002.sh "$DATABASE_URL"
```

---

## 📚 Full Documentation

See [RAILWAY_MIGRATION_002_GUIDE.md](docs/RAILWAY_MIGRATION_002_GUIDE.md) for:
- Alternative methods (Railway Dashboard, Local Tunnel)
- Troubleshooting guide
- Post-migration verification
- Complete rollback procedure

---

**Risk Level:** 🟢 Low (non-breaking, backward compatible)
**Estimated Time:** 5-10 minutes
**Downtime:** 0 seconds
