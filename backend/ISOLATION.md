# Multi-Tenant Data Isolation

Complete guide to Row-Level Security (RLS) implementation for multi-tenant data isolation in the Swing Trade Platform.

## Overview

This document describes:
1. How RLS works at the database level
2. Application-level implementation
3. Query patterns for safe data access
4. Testing and verification
5. Debugging and monitoring

## Architecture

### Defense-in-Depth

Data isolation is enforced at two levels:

1. **Database Level (RLS Policies)**: PostgreSQL Row-Level Security policies prevent users from accessing other users' data, even if application logic is bypassed.

2. **Application Level (Explicit Filters)**: All service methods explicitly filter queries by `user_id` for safety and clarity.

### Multi-Tenant Data Model

Tables are divided into two categories:

#### User-Owned Tables (RLS Enabled)
- `users`: Each user only sees themselves
- `exchange_keys`: Each user only sees their own keys
- `strategies`: Each user only sees their own strategies
- `trades`: Each user only sees trades from their own strategies
- `audit_logs`: Each user only sees their own action logs

#### Shared/System Tables (RLS Not Needed)
- `ohlcv`: Public market data (no RLS needed)
- `flyway_schema_history`: System table (no RLS)

## How RLS Works

### Context Function

RLS policies reference `current_user_id()` function which returns the current user's UUID:

```sql
CREATE OR REPLACE FUNCTION current_user_id() RETURNS UUID AS $$
BEGIN
  RETURN current_setting('app.current_user_id')::UUID;
EXCEPTION WHEN OTHERS THEN
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

### Setting User Context

The application must set this context **at the start of each transaction**:

```python
# In every route that accesses user data:
from app.db.rls import set_user_context

@app.get("/keys")
async def list_keys(
    user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Set RLS context for this transaction
    set_user_context(db, user_id)

    # Now all queries are filtered by RLS
    keys = db.query(ExchangeKey).all()  # Only user's keys
    return keys
```

### Policy Types

Each user-owned table has four RLS policies:

#### SELECT Policy
```sql
CREATE POLICY exchange_keys_select ON exchange_keys
  FOR SELECT
  USING (user_id = current_user_id());
```

Allows a user to SELECT only rows where `user_id` matches `current_user_id()`.

#### INSERT Policy
```sql
CREATE POLICY exchange_keys_insert ON exchange_keys
  FOR INSERT
  WITH CHECK (user_id = current_user_id());
```

Allows INSERT only when the new row's `user_id` matches `current_user_id()`.

#### UPDATE Policy
```sql
CREATE POLICY exchange_keys_update ON exchange_keys
  FOR UPDATE
  USING (user_id = current_user_id())
  WITH CHECK (user_id = current_user_id());
```

- `USING`: User can only UPDATE rows where `user_id` matches
- `WITH CHECK`: Updated row must still have `user_id` matching

Prevents: changing ownership of resources, escalating privileges.

#### DELETE Policy
```sql
CREATE POLICY exchange_keys_delete ON exchange_keys
  FOR DELETE
  USING (user_id = current_user_id());
```

Allows DELETE only for rows the user owns.

### Special Cases

#### Trades → Strategies → Users

Trades don't have `user_id` directly. They're filtered via the strategy relationship:

```sql
CREATE POLICY trades_select ON trades
  FOR SELECT
  USING (
    -- Allow access if strategy belongs to current user
    COALESCE(
      (SELECT user_id FROM strategies WHERE id = strategy_id),
      NULL
    ) = current_user_id()
  );
```

#### Audit Logs (Append-Only)

Audit logs only support SELECT and INSERT (no UPDATE/DELETE):

```sql
CREATE POLICY audit_logs_select ON audit_logs
  FOR SELECT
  USING (user_id = current_user_id());

CREATE POLICY audit_logs_insert ON audit_logs
  FOR INSERT
  WITH CHECK (user_id = current_user_id());
```

## Implementation Patterns

### Basic Query Pattern

```python
from app.db.rls import set_user_context

async def get_user_exchange_keys(db: Session, user_id: UUID) -> list[ExchangeKey]:
    """Get all exchange keys for a user."""
    # Set RLS context (required for every query)
    set_user_context(db, user_id)

    # Query is automatically filtered by RLS
    keys = db.query(ExchangeKey).all()

    return keys
```

### With Application-Level Filter (Defense-in-Depth)

```python
async def get_exchange_key(db: Session, user_id: UUID, key_id: UUID) -> Optional[ExchangeKey]:
    """Get a specific exchange key."""
    set_user_context(db, user_id)

    # Both RLS and explicit filter applied
    key = (
        db.query(ExchangeKey)
        .filter(
            ExchangeKey.id == key_id,
            ExchangeKey.user_id == user_id  # Explicit filter for safety
        )
        .first()
    )

    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    return key
```

### Update Pattern

```python
async def deactivate_exchange_key(
    db: Session, user_id: UUID, key_id: UUID
) -> Optional[ExchangeKey]:
    """Deactivate an exchange key."""
    set_user_context(db, user_id)

    key = (
        db.query(ExchangeKey)
        .filter(
            ExchangeKey.id == key_id,
            ExchangeKey.user_id == user_id
        )
        .first()
    )

    if not key:
        # Not found - either doesn't exist or belongs to another user
        raise HTTPException(status_code=404, detail="Key not found")

    # RLS ensures we can only update our own key
    key.is_active = False
    db.commit()
    db.refresh(key)

    return key
```

### Cascading Delete Pattern

```python
async def delete_strategy(db: Session, user_id: UUID, strategy_id: UUID) -> bool:
    """Delete a strategy (cascades to trades)."""
    set_user_context(db, user_id)

    strategy = (
        db.query(Strategy)
        .filter(
            Strategy.id == strategy_id,
            Strategy.user_id == user_id
        )
        .first()
    )

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Cascading delete (defined in model)
    # Trades will be deleted via foreign key cascade
    db.delete(strategy)
    db.commit()

    return True
```

### Context Manager Pattern

```python
from app.db.rls import user_context

async def get_full_user_profile(db: Session, user_id: UUID):
    """Get user's full profile including all resources."""

    with user_context(db, user_id) as session:
        user = session.query(User).filter(User.id == user_id).first()
        keys = session.query(ExchangeKey).all()
        strategies = session.query(Strategy).all()

        return {
            "user": user,
            "keys": keys,
            "strategies": strategies
        }
        # RLS context automatically cleared
```

## Testing

### Test Setup

Tests use the test isolation utilities:

```python
import pytest
from app.db.rls import set_user_context

@pytest.fixture
def two_users(db: Session):
    """Create two test users."""
    user_a = User(...)
    user_b = User(...)
    db.add(user_a)
    db.add(user_b)
    db.commit()
    return user_a, user_b
```

### Test Pattern: Data Visibility

```python
def test_user_cannot_see_other_users_keys(db: Session, two_users):
    """Verify User A cannot see User B's keys."""
    user_a, user_b = two_users

    # Create keys for both users
    key_a = ExchangeKey(user_id=user_a.id, ...)
    key_b = ExchangeKey(user_id=user_b.id, ...)
    db.add(key_a)
    db.add(key_b)
    db.commit()

    # User B queries with RLS context
    set_user_context(db, user_b.id)
    user_b_keys = db.query(ExchangeKey).all()

    # User B should see only their key
    assert len(user_b_keys) == 1
    assert user_b_keys[0].user_id == user_b.id

    # Verify User B does NOT see User A's key
    for key in user_b_keys:
        assert key.user_id != user_a.id
```

### Test Pattern: Modification Prevention

```python
def test_user_cannot_modify_other_users_key(db: Session, two_users):
    """Verify User A cannot modify User B's key."""
    user_a, user_b = two_users

    key_b = ExchangeKey(user_id=user_b.id, ...)
    db.add(key_b)
    db.commit()

    # User A tries to find and modify User B's key
    set_user_context(db, user_a.id)

    query = db.query(ExchangeKey).filter(ExchangeKey.id == key_b.id)
    found_key = query.first()

    # With RLS, found_key should be None
    # Or application logic should prevent modification
    if found_key:
        assert found_key.user_id == user_a.id
```

### Run Tests

```bash
# Run isolation tests
cd backend && pytest tests/test_isolation.py -v

# Run specific test
pytest tests/test_isolation.py::TestExchangeKeyIsolation::test_user_cannot_read_other_users_exchange_keys -v

# Run with coverage
pytest tests/test_isolation.py --cov=app --cov-report=html
```

## Verification

### Verify RLS is Enabled

```python
from app.db.rls import verify_rls_enabled, check_rls_health

# Check RLS status
status = verify_rls_enabled(db)
for table, info in status.items():
    print(f"{table}: RLS={info['rls_enabled']}, Policies={info['policy_count']}")

# Quick health check
is_healthy, message = check_rls_health(db)
if not is_healthy:
    print(f"RLS Health Check Failed: {message}")
```

### SQL Verification

```sql
-- Check RLS is enabled on all user-owned tables
SELECT schemaname, tablename, rowsecurity FROM pg_tables
WHERE tablename IN ('users', 'exchange_keys', 'strategies', 'trades', 'audit_logs')
AND schemaname = 'public';

-- Expected output: all should show "t" for rowsecurity enabled

-- List all RLS policies
SELECT policyname, tablename, permissive, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Test RLS in action (as superuser)
SET app.current_user_id = '550e8400-e29b-41d4-a716-446655440001';
SELECT COUNT(*) FROM exchange_keys;  -- Should show user's keys only

SET app.current_user_id = '550e8400-e29b-41d4-a716-446655440002';
SELECT COUNT(*) FROM exchange_keys;  -- Should show different user's keys

RESET app.current_user_id;
```

## Debugging

### Common Issues

#### 1. RLS Context Not Set

**Symptom**: All users see all data

**Solution**:
```python
# Every database transaction must set context
set_user_context(db, user_id)

# Check if context is set
current_context = db.execute(text("SELECT current_setting('app.current_user_id')")).scalar()
if not current_context:
    logger.error("RLS context not set!")
```

#### 2. RLS Not Enabled on Table

**Symptom**: RLS policies have no effect

**Solution**:
```sql
-- Check status
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'exchange_keys';

-- If rowsecurity = FALSE, enable it
ALTER TABLE exchange_keys ENABLE ROW LEVEL SECURITY;
```

#### 3. Policies Too Restrictive

**Symptom**: Legitimate access denied

**Solution**:
```sql
-- Check which policies exist
SELECT policyname FROM pg_policies WHERE tablename = 'exchange_keys';

-- Test individual policies
SET app.current_user_id = 'user-uuid';
SELECT * FROM exchange_keys;  -- If empty, policy blocking access

-- Verify policy condition
SELECT * FROM exchange_keys WHERE user_id = 'user-uuid';  -- Should match above
```

#### 4. SQLite Test Database (No RLS)

**Symptom**: RLS tests pass but isolation not enforced in tests

**Reason**: SQLite doesn't support RLS. Tests use application-level filtering.

**Solution**: For full RLS testing, use PostgreSQL test database.

## Migration Path

### For Existing Deployments

1. **Backup database**:
   ```bash
   pg_dump swing_trade > backup.sql
   ```

2. **Run migration**:
   ```bash
   python migrations.py --migrate
   ```

3. **Verify RLS**:
   ```bash
   psql -c "SELECT tablename, rowsecurity FROM pg_tables WHERE rowsecurity;"
   ```

4. **Test isolation**:
   ```bash
   pytest tests/test_isolation.py -v
   ```

5. **Monitor logs** for any RLS-related errors

## Best Practices

### DO

✅ **Always set RLS context** at the start of every database transaction
```python
set_user_context(db, user_id)
```

✅ **Verify ownership** before returning user data
```python
if resource.user_id != current_user_id:
    raise HTTPException(status_code=403, detail="Not authorized")
```

✅ **Use application-level filters** alongside RLS for defense-in-depth
```python
.filter(ExchangeKey.user_id == user_id)
```

✅ **Test isolation** in every relevant test
```python
def test_user_cannot_see_other_user_data():
    ...
```

✅ **Log access attempts** with user context
```python
logger.info(f"Accessed exchange_keys for user={user_id}")
```

### DON'T

❌ **Forget to set RLS context**
```python
# BAD - no RLS context
keys = db.query(ExchangeKey).all()  # May return other users' keys
```

❌ **Trust only application filtering** without RLS
```python
# BAD - if app filter is bypassed, RLS prevents data leak, but don't rely on it
keys = db.query(ExchangeKey).all()  # Without RLS context
if keys:
    # Filtering would happen here, but RLS should have prevented this
```

❌ **Allow direct SQL without RLS context**
```python
# BAD - RLS not enforced on raw SQL
db.execute(text("SELECT * FROM exchange_keys"))

# GOOD - still won't help with raw SQL. Use ORM queries instead.
db.query(ExchangeKey).all()
```

❌ **Hardcode user_id in queries**
```python
# BAD - if admin needs to see all data, hardcoding breaks flexibility
if admin:
    db.execute(text("SELECT * FROM exchange_keys WHERE user_id = 'hardcoded'"))
```

❌ **Expose user_id in error messages**
```python
# BAD - information disclosure
raise HTTPException(detail=f"Access denied for user {user_id}")

# GOOD
raise HTTPException(detail="Access denied")
```

## Performance Considerations

### RLS Overhead

- RLS policies add a **small overhead** (~1-5%) to query performance
- Index usage is unaffected
- Policies are optimized by PostgreSQL query planner

### Optimization Tips

1. **Indexes on user_id**: Essential for fast filtering
```sql
CREATE INDEX idx_exchange_keys_user ON exchange_keys(user_id);
```

2. **Compound indexes** for multi-column filters
```sql
CREATE INDEX idx_strategies_user_active ON strategies(user_id, is_active);
```

3. **Avoid complex policy conditions** - keep them simple
```sql
-- GOOD - simple condition
WHERE user_id = current_user_id()

-- BAD - complex subqueries
WHERE (SELECT user_id FROM ...) = current_user_id()
```

## Admin Considerations

### Superuser Bypass

PostgreSQL superusers **bypass RLS policies**. For admin access:

1. **Create a dedicated admin role** (not superuser)
2. **Grant selective privileges** without RLS bypass
3. **Audit all admin access** with application logs

```sql
-- Create admin role (not superuser)
CREATE ROLE admin_role LOGIN PASSWORD 'secure_password';

-- Grant access to specific tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO admin_role;

-- RLS still applies to admin_role
-- This prevents accidental data leaks
```

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Swing Trade Platform Architecture](./README.md)
- [Authentication Guide](./AUTHENTICATION_GUIDE.md)
- [Database Setup](./DOCKER.md)

## Support

For issues or questions about isolation:

1. Check this guide's debugging section
2. Review test examples in `tests/test_isolation.py`
3. Check database logs: `psql -U postgres -d swing_trade -c "SELECT * FROM pg_stat_statements WHERE query LIKE '%RLS%'"`
4. Review application logs for `RLSLogger` entries
