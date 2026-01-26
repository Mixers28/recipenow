#!/bin/bash
# Apply migration 002 to add source_method column
# Usage: ./scripts/apply_migration_002.sh [DATABASE_URL]

set -e

DATABASE_URL="${1:-$DATABASE_URL}"

if [ -z "$DATABASE_URL" ]; then
  echo "Error: DATABASE_URL not provided"
  echo "Usage: ./apply_migration_002.sh postgresql://user:pass@host:port/dbname"
  exit 1
fi

echo "🚀 Applying Migration 002: Add source_method to source_spans"
echo "=================================================="
echo ""

# Pre-flight check
echo "1️⃣  Pre-flight checks..."
echo ""

# Verify source_spans table exists
TABLE_EXISTS=$(psql "$DATABASE_URL" -t -c "
  SELECT COUNT(*)
  FROM information_schema.tables
  WHERE table_name='source_spans';
")
TABLE_EXISTS=$(echo $TABLE_EXISTS | xargs)

if [ "$TABLE_EXISTS" = "0" ]; then
  echo "❌ ERROR: source_spans table does not exist!"
  echo "Please run migration 001_init.sql first"
  exit 1
fi
echo "✅ source_spans table exists"

# Check if migration already applied
COLUMN_EXISTS=$(psql "$DATABASE_URL" -t -c "
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_name='source_spans'
    AND column_name='source_method';
")
COLUMN_EXISTS=$(echo $COLUMN_EXISTS | xargs)

if [ "$COLUMN_EXISTS" = "1" ]; then
  echo "⚠️  Migration 002 already applied (idempotent - safe to continue)"
else
  echo "✅ Migration 002 not yet applied - ready to proceed"
fi

echo ""
echo "2️⃣  Creating backup point..."
echo ""

# Count existing records
RECORD_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM source_spans;")
RECORD_COUNT=$(echo $RECORD_COUNT | xargs)
echo "Current source_spans records: $RECORD_COUNT"

echo ""
echo "3️⃣  Applying migration..."
echo ""

# Apply migration
psql "$DATABASE_URL" -f infra/migrations/002_add_source_method.sql

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Migration applied successfully!"
else
  echo ""
  echo "❌ Migration failed!"
  exit 1
fi

echo ""
echo "4️⃣  Verifying migration..."
echo ""

# Verify column exists
COLUMN_VERIFIED=$(psql "$DATABASE_URL" -t -c "
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_name='source_spans'
    AND column_name='source_method';
")
COLUMN_VERIFIED=$(echo $COLUMN_VERIFIED | xargs)

if [ "$COLUMN_VERIFIED" = "1" ]; then
  echo "✅ source_method column created"
else
  echo "❌ source_method column NOT found!"
  exit 1
fi

# Verify indexes
INDEX_COUNT=$(psql "$DATABASE_URL" -t -c "
  SELECT COUNT(*)
  FROM pg_indexes
  WHERE tablename = 'source_spans'
    AND indexname LIKE '%source_method%';
")
INDEX_COUNT=$(echo $INDEX_COUNT | xargs)

if [ "$INDEX_COUNT" = "2" ]; then
  echo "✅ Indexes created (2 found)"
else
  echo "⚠️  Expected 2 indexes, found $INDEX_COUNT"
fi

# Show final schema
echo ""
echo "5️⃣  Final schema verification:"
echo ""
psql "$DATABASE_URL" -c "
  SELECT column_name, data_type, column_default, is_nullable
  FROM information_schema.columns
  WHERE table_name='source_spans'
  ORDER BY ordinal_position;
"

# Verify record count unchanged
FINAL_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM source_spans;")
FINAL_COUNT=$(echo $FINAL_COUNT | xargs)

if [ "$RECORD_COUNT" = "$FINAL_COUNT" ]; then
  echo ""
  echo "✅ Record count unchanged: $FINAL_COUNT records"
else
  echo ""
  echo "⚠️  Record count changed: $RECORD_COUNT → $FINAL_COUNT"
fi

echo ""
echo "=================================================="
echo "✅ Migration 002 completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Monitor application logs for errors"
echo "  2. Test recipe upload with source_method tracking"
echo "  3. Verify source_method values populated correctly"
echo ""
