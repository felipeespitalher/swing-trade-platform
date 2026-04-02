# Flyway Database Migrations

This directory contains all Flyway migrations for the Swing Trade Platform database.

## Overview

Flyway is a database migration tool that automatically versions and applies SQL schema changes. All migrations are applied in order using version numbers.

**Database:** PostgreSQL 15 with TimescaleDB extension
**Database Name:** swing_trade
**Location:** migrations/ directory (tracked by git)

## Migration Files

| File | Version | Description | Status |
|------|---------|-------------|--------|
| V1__init_schema.sql | 1 | Initial schema with all core tables | Applied |

## How to Run Migrations

### Prerequisites

- PostgreSQL 15 or higher
- TimescaleDB extension installed
- Flyway CLI (if running manually)
- Docker (recommended for local development)

### Automatic (Docker Compose)

Migrations run automatically when the backend service starts:

```bash
docker-compose up -d postgres
docker-compose up -d backend
```

The backend service will automatically run Flyway migrations on startup (configured in application properties).

### Manual (Flyway CLI)

If running Flyway directly:

```bash
export FLYWAY_DB_URL=jdbc:postgresql://localhost:5432/swing_trade
export FLYWAY_DB_USER=postgres
export FLYWAY_DB_PASSWORD=postgres_password

flyway migrate
```

### Via Python Application

Migrations are automatically applied when the FastAPI backend starts (see backend configuration).

## Writing New Migrations

### Naming Convention

All migration files must follow the Flyway naming convention:

```
V{VERSION}__{DESCRIPTION}.sql
```

Where:
- **VERSION**: Sequential number (V1, V2, V3, etc.)
- **DESCRIPTION**: Snake_case description of changes (no spaces)

### Examples

```
V2__add_user_preferences_table.sql
V3__add_index_on_trades_symbol.sql
V4__add_cascade_delete_on_exchange_keys.sql
```

### Rules

1. **Never modify existing migrations** - Flyway tracks which migrations have been applied
2. **Always create new migrations** for schema changes, even if small
3. **Test locally first** - Run against local docker-compose database
4. **Use IF NOT EXISTS** for safe idempotent statements
5. **Keep migrations small and focused** - One logical change per migration
6. **Use TIMESTAMP WITH TIME ZONE** for all timestamps
7. **Add comments** explaining the purpose and impact

### Template for New Migrations

```sql
-- Migration Title
-- Purpose: Describe what this migration does
-- Impact: Any breaking changes or considerations

-- ============================================================================
-- YOUR CHANGES HERE
-- ============================================================================

CREATE TABLE IF NOT EXISTS new_table (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- columns...
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_new_table_created ON new_table(created_at DESC);

-- ============================================================================
-- COMMENTS (optional but recommended)
-- ============================================================================
COMMENT ON TABLE new_table IS 'Purpose of this table';
```

## Migration History

After running migrations, verify with:

```bash
# Check migration history in database
docker-compose exec postgres psql -U postgres -d swing_trade -c "SELECT * FROM flyway_schema_history ORDER BY version;"

# Expected output:
# version | description | type | script | installed_by | installed_on | execution_time | success
# --------|-------------|------|--------|--------------|--------------|----------------|--------
# 1       | init schema | SQL  | V1__init_schema.sql | postgres | ... | ... | t
```

## Reverting Migrations

**IMPORTANT:** Flyway Community Edition does NOT support automatic rollback.

If you need to revert:
1. Create a new migration that undoes changes (recommended)
2. Use Flyway Pro (paid feature) for automatic undo
3. Manually revert in development only

Example rollback migration:

```sql
-- V2__rollback_previous_change.sql
DROP TABLE IF EXISTS problematic_table;
-- add back what was removed
```

## Troubleshooting

### Migration Fails to Apply

1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Check database exists: `docker-compose exec postgres psql -U postgres -l`
3. Check migration syntax: Test SQL in psql directly
4. Check migration history: `docker-compose exec postgres psql -U postgres -d swing_trade -c "SELECT * FROM flyway_schema_history;"`

### Lost Track of Applied Migrations

If the flyway_schema_history table gets out of sync:

```bash
# Reset (DEVELOPMENT ONLY - destroys all data!)
docker-compose exec postgres psql -U postgres -d swing_trade -c "DROP TABLE IF EXISTS flyway_schema_history;"

# Re-apply migrations from scratch
docker-compose down -v
docker-compose up postgres
```

## Best Practices

1. **Version Control:** Always commit migrations to git
2. **Testing:** Test locally with docker-compose before pushing
3. **Code Review:** Have team review SQL changes before merge
4. **Schema Backups:** Backup production database before migrations
5. **Monitoring:** Monitor migration execution time in production
6. **Documentation:** Document breaking changes and impact
7. **Dry Run:** Run migrations in staging first
8. **Rollback Plan:** Have a rollback migration ready for each change

## Performance Considerations

- **Large table changes:** Use `ALTER TABLE ... CONCURRENTLY` when possible
- **Indexes:** Create indexes during low-traffic periods
- **Data migration:** Batch large data migrations to avoid long locks
- **TimescaleDB:** Compressions policies improve storage but may affect query speed

## TimescaleDB Specific

The OHLCV table is a TimescaleDB hypertable. When adding time-series data:

1. Always include timestamp in WHERE clause for best performance
2. Use appropriate time intervals for data retention
3. Enable compression for historical data
4. Monitor chunk size and compression ratio

```sql
-- Check hypertable info
SELECT * FROM timescaledb_information.hypertables;

-- Check chunk info
SELECT * FROM timescaledb_information.chunks WHERE hypertable_name = 'ohlcv';
```

## References

- [Flyway Documentation](https://flywaydb.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
