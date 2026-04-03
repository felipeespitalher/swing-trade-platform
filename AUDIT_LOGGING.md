# Audit Logging Guide

## Overview

The Swing Trade Automation Platform includes comprehensive audit logging for compliance, security, and debugging purposes. Every user action is tracked in an append-only audit log that cannot be modified after creation.

## Audit Log Model

The `AuditLog` model stores audit trail entries with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier for the audit log entry |
| `user_id` | UUID | User who performed the action (nullable for system actions) |
| `action` | String(100) | Type of action performed (e.g., 'LOGIN', 'STRATEGY_CREATE') |
| `resource_type` | String(50) | Type of resource affected (e.g., 'strategy', 'exchange_key') |
| `resource_id` | UUID | ID of the resource affected |
| `old_values` | JSON | Previous values before the action (for updates) |
| `new_values` | JSON | New values after the action (for creates/updates) |
| `ip_address` | INET | Client IP address |
| `user_agent` | String | Client user agent string |
| `created_at` | DateTime(UTC) | When the action occurred |

### Key Characteristics

- **Append-only**: Audit logs cannot be modified or deleted
- **Immutable**: Once created, the record is permanent
- **Comprehensive**: Captures before/after values for change tracking
- **User-isolated**: Users can only query their own audit logs
- **Indexed**: Multiple indexes for fast querying by user, action, resource

## Automatic Logging

### Middleware Auto-Logging

The `AuditMiddleware` automatically logs all POST, PATCH, and DELETE requests:

```python
# Automatically logged mutations
POST   /api/strategies          # Create strategy
PATCH  /api/strategies/{id}    # Update strategy
DELETE /api/strategies/{id}    # Delete strategy
POST   /api/exchange-keys      # Add exchange key
DELETE /api/exchange-keys/{id} # Remove exchange key
```

**What gets captured:**
- User ID (from JWT token)
- Client IP address
- User agent
- Request path and method
- Response status code

**Only successful requests (status < 400) are logged.**

## Manual Logging

For critical business actions, use the `AuditService` to log manually:

```python
from app.services.audit_service import AuditService

# Log a login event
AuditService.log_action(
    db=db,
    user_id=user.id,
    action="LOGIN",
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)

# Log a password change
AuditService.log_action(
    db=db,
    user_id=user.id,
    action="PASSWORD_CHANGE",
    old_values={"password_hash": old_hash},
    new_values={"password_hash": new_hash}
)

# Log email change
AuditService.log_action(
    db=db,
    user_id=user.id,
    action="EMAIL_CHANGE",
    old_values={"email": old_email},
    new_values={"email": new_email}
)

# Log exchange key addition
AuditService.log_action(
    db=db,
    user_id=user.id,
    action="EXCHANGE_KEY_ADD",
    resource_type="exchange_key",
    resource_id=key.id,
    new_values={"exchange": "binance"}
)

# Log strategy creation with details
AuditService.log_action(
    db=db,
    user_id=user.id,
    action="STRATEGY_CREATE",
    resource_type="strategy",
    resource_id=strategy.id,
    new_values={
        "name": strategy.name,
        "symbol": strategy.symbol,
        "entry_points": strategy.entry_points
    }
)
```

## Querying Audit Logs

### API Endpoints

#### 1. Get Current User's Audit Logs

```bash
GET /api/audit/me?limit=100&offset=0

# Response
{
  "logs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "action": "LOGIN",
      "resource_type": null,
      "resource_id": null,
      "old_values": null,
      "new_values": null,
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0",
      "created_at": "2026-04-02T10:30:45.123456"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

#### 2. Filter by Action Type

```bash
GET /api/audit/me/actions?action=LOGIN&limit=50

# Get all LOGIN actions for current user
```

#### 3. Filter by Date Range

```bash
GET /api/audit/me/date-range?start_date=2026-04-01&end_date=2026-04-02

# Get all actions within date range
```

#### 4. Get Resource Change History

```bash
GET /api/audit/strategy/550e8400-e29b-41d4-a716-446655440000

# Response shows all changes to a specific strategy
{
  "logs": [
    {
      "action": "STRATEGY_UPDATE",
      "old_values": {"max_risk": 2.0},
      "new_values": {"max_risk": 2.5},
      "created_at": "2026-04-02T10:45:00"
    },
    {
      "action": "STRATEGY_CREATE",
      "new_values": {"name": "My Strategy", "max_risk": 2.0},
      "created_at": "2026-04-02T09:30:00"
    }
  ],
  "total": 2,
  "resource_type": "strategy",
  "resource_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Service Layer

```python
from app.services.audit_service import AuditService
from datetime import datetime, timedelta

# Get user's audit logs
logs, total = AuditService.get_user_audit_logs(
    db=db,
    user_id=user_id,
    limit=100,
    offset=0
)

# Filter by action
logs, total = AuditService.get_user_audit_logs(
    db=db,
    user_id=user_id,
    action_filter="LOGIN"
)

# Filter by date range
start = datetime(2026, 4, 1)
end = datetime(2026, 4, 2)
logs, total = AuditService.get_user_audit_logs(
    db=db,
    user_id=user_id,
    start_date=start,
    end_date=end
)

# Get resource history
logs, total = AuditService.get_resource_audit_history(
    db=db,
    resource_type="strategy",
    resource_id=strategy_id
)

# Get recent actions (last 24 hours)
logs = AuditService.get_recent_user_actions(
    db=db,
    user_id=user_id,
    hours=24
)

# Get all actions of a type
logs, total = AuditService.get_audit_logs_by_action(
    db=db,
    action="LOGIN"
)

# Get actions in date range
logs, total = AuditService.get_audit_logs_by_date_range(
    db=db,
    start_date=start,
    end_date=end,
    user_id=user_id  # Optional
)
```

## User Isolation

Users can only access their own audit logs. The API endpoints enforce this:

- `GET /api/audit/me` - Always returns current user's logs
- `GET /api/audit/me/actions` - Filtered by current user
- `GET /api/audit/me/date-range` - Filtered by current user

Database-level Row Level Security (RLS) ensures users cannot query other users' logs even with SQL.

## Common Audit Actions

### Authentication Actions

| Action | Trigger | Fields |
|--------|---------|--------|
| `LOGIN` | Successful user login | ip_address, user_agent |
| `LOGOUT` | User logout | ip_address, user_agent |
| `PASSWORD_CHANGE` | User changes password | old_values, new_values |
| `EMAIL_CHANGE` | User changes email | old_values, new_values |
| `EMAIL_VERIFIED` | User verifies email | - |
| `REGISTRATION` | New user registration | - |

### Exchange Key Actions

| Action | Trigger | Fields |
|--------|---------|--------|
| `EXCHANGE_KEY_ADD` | User adds exchange API key | resource_type, resource_id, new_values |
| `EXCHANGE_KEY_UPDATE` | User updates exchange key | resource_type, resource_id, old_values, new_values |
| `EXCHANGE_KEY_DELETE` | User removes exchange key | resource_type, resource_id, old_values |

### Strategy Actions

| Action | Trigger | Fields |
|--------|---------|--------|
| `STRATEGY_CREATE` | User creates new strategy | resource_type, resource_id, new_values |
| `STRATEGY_UPDATE` | User updates strategy | resource_type, resource_id, old_values, new_values |
| `STRATEGY_DELETE` | User deletes strategy | resource_type, resource_id, old_values |
| `STRATEGY_ACTIVATE` | User activates strategy | resource_type, resource_id |
| `STRATEGY_DEACTIVATE` | User deactivates strategy | resource_type, resource_id |

### Trade Actions

| Action | Trigger | Fields |
|--------|---------|--------|
| `TRADE_EXECUTE` | Strategy executes a trade | resource_type, resource_id, new_values |
| `TRADE_CLOSE` | Trade position closed | resource_type, resource_id, old_values, new_values |

## Compliance & Retention

### Data Retention

- Audit logs are retained indefinitely
- No automatic deletion or archiving
- Manual deletion requires database admin access
- All deletions should be logged separately

### Compliance Requirements

- **SOC 2**: Complete audit trail of all user actions
- **GDPR**: User can request their audit log as part of data export
- **PCI DSS**: If processing payments, audit logs retain payment-related actions
- **Internal Audit**: Complete change history for each resource

### Audit Log Export

Users can export their complete audit log:

```bash
GET /api/audit/me?limit=10000&offset=0

# Returns all audit logs in JSON format
# Can be saved to file for compliance reporting
```

## Performance Considerations

### Indexes

Audit logs have three indexes for fast querying:

```sql
-- User and creation time (most common query)
CREATE INDEX idx_audit_logs_user_created ON audit_logs (user_id, created_at);

-- Action type and creation time
CREATE INDEX idx_audit_logs_action_created ON audit_logs (action, created_at);

-- Resource type and ID
CREATE INDEX idx_audit_logs_resource ON audit_logs (resource_type, resource_id);
```

### Query Optimization

- Always use pagination (limit/offset)
- Filter by date range when possible
- Use action_filter to reduce result set
- Avoid full table scans on large audit logs

### Storage Considerations

- Average audit log entry: ~500 bytes
- 1000 users × 100 actions/user/month = 100,000 logs/month
- 100,000 logs × 500 bytes = 50 MB/month
- Annual storage: ~600 MB

## Testing

The audit logging system includes 25+ test cases:

```bash
# Run all audit tests
TEST_DATABASE_URL=postgresql://... pytest tests/test_audit.py -v

# Test specific class
pytest tests/test_audit.py::TestAuditLogCreation -v

# Test specific method
pytest tests/test_audit.py::TestAuditLogCreation::test_log_action_created -v
```

### Test Coverage

- ✅ Audit log creation with all fields
- ✅ JSON value serialization
- ✅ Append-only enforcement
- ✅ User isolation
- ✅ API endpoint authentication
- ✅ Pagination
- ✅ Date range filtering
- ✅ Action filtering
- ✅ Resource history tracking
- ✅ Middleware auto-logging
- ✅ Successful response filtering
- ✅ Data integrity

## Examples

### Example 1: Track Strategy Changes

```python
# Before update
strategy = db.query(Strategy).get(strategy_id)
old_values = {
    "name": strategy.name,
    "max_risk": float(strategy.max_risk)
}

# Update strategy
strategy.name = "Updated Strategy"
strategy.max_risk = 2.5
db.commit()

# Log the change
AuditService.log_action(
    db=db,
    user_id=current_user.id,
    action="STRATEGY_UPDATE",
    resource_type="strategy",
    resource_id=strategy_id,
    old_values=old_values,
    new_values={
        "name": strategy.name,
        "max_risk": float(strategy.max_risk)
    }
)
```

### Example 2: Generate Compliance Report

```python
from datetime import datetime, timedelta

# Get last 30 days of all user actions
thirty_days_ago = datetime.utcnow() - timedelta(days=30)
logs, total = AuditService.get_audit_logs_by_date_range(
    db=db,
    start_date=thirty_days_ago,
    end_date=datetime.utcnow()
)

# Generate report
report = {
    "period": "Last 30 days",
    "total_actions": total,
    "actions_by_type": {},
    "high_risk_actions": []
}

for log in logs:
    # Count actions by type
    action = log.action
    report["actions_by_type"][action] = report["actions_by_type"].get(action, 0) + 1

    # Flag sensitive actions
    if log.action in ["PASSWORD_CHANGE", "EXCHANGE_KEY_ADD", "EXCHANGE_KEY_DELETE"]:
        report["high_risk_actions"].append({
            "user_id": str(log.user_id),
            "action": log.action,
            "timestamp": log.created_at.isoformat()
        })

return report
```

### Example 3: Detect Suspicious Activity

```python
# Get user's login actions in last hour
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
logs, _ = AuditService.get_user_audit_logs(
    db=db,
    user_id=user_id,
    action_filter="LOGIN",
    start_date=one_hour_ago
)

if len(logs) > 5:
    # Alert: Multiple logins in short time period
    logger.warning(f"Suspicious activity: {len(logs)} logins in 1 hour for user {user_id}")
    # Could trigger MFA requirement, password reset, etc.
```

## Troubleshooting

### Audit log not appearing

1. Check that the request returned a successful status code (< 400)
2. Verify the user is authenticated (JWT token is valid)
3. Ensure the middleware is registered in `app/main.py`
4. Check database connection and permissions

### Performance issues querying audit logs

1. Add date range filter to limit result set
2. Use pagination (limit + offset)
3. Filter by action type to reduce results
4. Check that indexes exist on audit_logs table

### Cannot access other user's logs

This is intentional - users are isolated to their own audit logs. To view all audit logs, use database admin access and bypass the API.

## Future Enhancements

- [ ] Audit log export to CSV/Excel
- [ ] Advanced filtering by multiple criteria
- [ ] Real-time alerts for suspicious actions
- [ ] Audit log archival to cold storage (S3)
- [ ] GraphQL API for audit queries
- [ ] Dashboard showing recent user actions
- [ ] Automated compliance report generation

## Related Documentation

- [Authentication Guide](./AUTHENTICATION_GUIDE.md)
- [Database Schema](./docs/DATABASE_SCHEMA.md)
- [API Documentation](./docs/API.md)
