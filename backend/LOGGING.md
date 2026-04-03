# Application Logging Guide

This guide explains how the Swing Trade Automation Platform API implements and uses structured logging.

## Overview

The application uses Python's `logging` module with environment-specific formatting:

- **Development (DEBUG=true)**: Human-readable format for easy reading
- **Production (DEBUG=false)**: JSON structured format for log aggregation and analysis

## Architecture

### Components

1. **Logging Configuration** (`app/core/logging.py`)
   - Sets up Python logging module
   - Configures formatters and handlers
   - Module-specific logger settings

2. **Logging Middleware** (`app/middleware/logging.py`)
   - Logs all HTTP requests and responses
   - Tracks request duration
   - Generates request IDs for trace correlation
   - Extracts user information from JWT tokens

3. **Monitoring Service** (`app/services/monitoring.py`)
   - Tracks application metrics
   - Provides health status
   - Monitors error rates

4. **Health & Metrics Endpoints** (`app/api/health.py`)
   - GET /api/health - Health status
   - GET /api/metrics - Application metrics
   - GET /api/metrics/detailed - Detailed metrics with health
   - GET /api/metrics/database - Database connectivity status

## Configuration

### Environment Variables

Configure logging via environment variables in `.env`:

```env
# Enable debug mode (development)
DEBUG=true

# Set log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Set environment: development, staging, production
ENVIRONMENT=development
```

### Development Mode

When `DEBUG=true`, logs are printed in human-readable format:

```
2026-04-02 14:30:45,123 - app.api.auth - INFO - Request started
2026-04-02 14:30:45,456 - app.api.auth - INFO - User registered successfully
2026-04-02 14:30:45,789 - app.api.auth - INFO - Request completed: POST /api/auth/register 201
```

### Production Mode

When `DEBUG=false`, logs are in JSON format:

```json
{"timestamp": "2026-04-02 14:30:45,123", "level": "INFO", "logger": "app.api.auth", "message": "Request started", "request_id": "abc-123-def"}
{"timestamp": "2026-04-02 14:30:45,456", "level": "INFO", "logger": "app.api.auth", "message": "User registered successfully", "request_id": "abc-123-def"}
{"timestamp": "2026-04-02 14:30:45,789", "level": "INFO", "logger": "app.api.auth", "message": "Request completed: POST /api/auth/register 201", "request_id": "abc-123-def", "status_code": 201, "duration_ms": 200}
```

## Logging Features

### Request Logging

All HTTP requests are automatically logged by `LoggingMiddleware`:

**Request Start:**
```
method=POST
path=/api/auth/register
query=null
user_id=null (if not authenticated)
client_ip=127.0.0.1
request_id=550e8400-e29b-41d4-a716-446655440000
```

**Request Completion:**
```
method=POST
path=/api/auth/register
status_code=201
duration_seconds=0.123
duration_ms=123.45
user_id=user@example.com (if authenticated)
request_id=550e8400-e29b-41d4-a716-446655440000
```

### Request ID Tracking

Each request gets a unique request ID for trace correlation:

1. If `X-Request-ID` header is provided in request, it's used
2. Otherwise, a UUID is generated automatically
3. The request ID is included in all logs for that request
4. The request ID is returned in the `X-Request-ID` response header

Example usage:

```bash
# Send request with custom request ID
curl -H "X-Request-ID: my-custom-trace-id" http://localhost:8000/api/health

# View logs with that request ID
docker-compose logs backend | grep "my-custom-trace-id"
```

### User Tracking

When a user is authenticated (JWT token present), their user ID is logged:

```bash
curl -H "Authorization: Bearer {token}" http://localhost:8000/api/users/me
```

Logs will include `user_id: user@example.com`

### Error Logging

Errors are logged with full stack traces:

```
ERROR - app.api.auth - Request failed
error=Email already registered
error_type=ValueError
duration_ms=45.23
request_id=550e8400-e29b-41d4-a716-446655440000
Traceback (most recent call last):
  File "app/middleware/logging.py", line 65, in dispatch
    response = await call_next(request)
  File "app/api/auth.py", line 45, in register
    raise ValueError("Email already registered")
ValueError: Email already registered
```

### Module-Specific Logging

Different modules have different log levels in production:

- `app.*`: INFO (application code)
- `uvicorn.access`: WARNING (HTTP access logs)
- `sqlalchemy.engine`: WARNING (SQL queries)
- `sqlalchemy.pool`: WARNING (connection pool)

In development (DEBUG=true):

- `app.*`: DEBUG (all application logs)
- `uvicorn.access`: INFO (HTTP access logs)
- `sqlalchemy.engine`: DEBUG (SQL queries)
- `sqlalchemy.pool`: DEBUG (connection pool debug info)

## Usage in Code

### Getting a Logger

```python
import logging

logger = logging.getLogger(__name__)
```

### Logging at Different Levels

```python
# Debug (development info, low priority)
logger.debug("Database connection established", extra={"host": "localhost"})

# Info (general information)
logger.info("User registered successfully", extra={"email": "user@example.com"})

# Warning (potential issues)
logger.warning("High error rate detected", extra={"rate": "5%"})

# Error (application error)
logger.error("Failed to process payment", extra={"user_id": user_id}, exc_info=True)

# Critical (system failure)
logger.critical("Database connection lost", extra={"service": "postgres"})
```

### Adding Context

Use the `extra` parameter to add structured context:

```python
logger.info(
    "Trade executed successfully",
    extra={
        "user_id": user_id,
        "symbol": "AAPL",
        "action": "BUY",
        "quantity": 100,
        "price": 150.25,
        "request_id": request_id,
    }
)
```

In JSON format, this becomes:

```json
{
    "timestamp": "2026-04-02 14:30:45,123",
    "level": "INFO",
    "logger": "app.services.trading",
    "message": "Trade executed successfully",
    "user_id": "user123",
    "symbol": "AAPL",
    "action": "BUY",
    "quantity": 100,
    "price": 150.25,
    "request_id": "abc-123-def"
}
```

### Exception Logging

Always use `exc_info=True` when logging exceptions:

```python
try:
    # Some operation
    result = risky_operation()
except Exception as exc:
    logger.error(
        "Operation failed",
        extra={"operation": "risky_operation"},
        exc_info=True  # Includes full stack trace
    )
    raise
```

## Health Check Endpoint

### GET /api/health

Returns the health status of the application and its components:

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
    "status": "healthy",
    "timestamp": "2026-04-02T14:30:45.123456",
    "uptime_seconds": 1234.56,
    "components": {
        "database": "healthy",
        "api": "healthy"
    }
}
```

Status values:
- `healthy`: All checks passed
- `unhealthy`: One or more checks failed

## Metrics Endpoints

### GET /api/metrics

Returns application metrics:

```bash
curl http://localhost:8000/api/metrics
```

Response:
```json
{
    "timestamp": "2026-04-02T14:30:45.123456",
    "uptime": {
        "seconds": 1234.56,
        "minutes": 20.58,
        "hours": 0.34
    },
    "requests": {
        "total": 150,
        "rate_per_minute": 7.29
    },
    "errors": {
        "total": 2,
        "rate": 0.013,
        "last_error": null
    },
    "environment": {
        "app_name": "Swing Trade Automation Platform API",
        "app_version": "0.1.0",
        "environment": "development",
        "debug": true
    }
}
```

### GET /api/metrics/detailed

Returns metrics combined with detailed health status (includes component health).

### GET /api/metrics/database

Returns database connectivity status:

```bash
curl http://localhost:8000/api/metrics/database
```

Response:
```json
{
    "status": "connected",
    "database_url": "***hidden***",
    "timestamp": "2026-04-02T14:30:45.123456"
}
```

## Docker Logging

The docker-compose configuration includes log rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

This keeps the last 3 log files, with each file limited to 10MB.

### Viewing Docker Logs

```bash
# View all logs
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend

# View last 50 lines
docker-compose logs backend --tail 50

# View logs from last hour
docker-compose logs --since 1h backend

# Filter logs (grep)
docker-compose logs backend | grep ERROR
```

## Performance Monitoring

### Request Duration Tracking

Each request logs its duration in milliseconds:

```
Request completed: POST /api/auth/register 201
duration_ms=123.45
```

Monitor slow requests by filtering for high duration values:

```bash
docker-compose logs backend | grep duration_ms | awk -F'duration_ms=' '{print $2}' | sort -n
```

### Error Rate Monitoring

The metrics endpoint tracks error rates:

```bash
# Get current error rate
curl http://localhost:8000/api/metrics | jq '.errors.rate'
```

Monitor errors by level:

```bash
# Count errors by level (development)
docker-compose logs backend | grep ERROR | wc -l
docker-compose logs backend | grep CRITICAL | wc -l

# Filter for specific error types
docker-compose logs backend | grep "error_type"
```

## Debugging

### Enable Debug Mode

In `.env`:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Debug mode provides:
- SQL query logging (SQLAlchemy)
- Connection pool debug info
- Detailed application logs
- Stack traces for warnings

### Trace a Request

Use the request ID to follow a request through all services:

```bash
# Make request with custom request ID
curl -H "X-Request-ID: debug-trace-123" http://localhost:8000/api/health

# View all logs for that request
docker-compose logs backend | grep "debug-trace-123"
```

### Common Debug Commands

```bash
# View application startup logs
docker-compose logs backend | grep "Starting"

# View all errors in last hour
docker-compose logs backend --since 1h | grep ERROR

# View slow requests (>1 second)
docker-compose logs backend | grep -E 'duration_ms=[1-9][0-9]{3,}' | head -20

# Monitor error rate in real-time
docker-compose logs -f backend | grep -E "(ERROR|CRITICAL)"

# View database connection issues
docker-compose logs backend | grep -i "database\|connection"

# Count requests by endpoint
docker-compose logs backend | grep "Request completed" | awk -F'path=' '{print $2}' | awk -F' ' '{print $1}' | sort | uniq -c

# View authentication issues
docker-compose logs backend | grep -i "auth\|token"
```

## Best Practices

### 1. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic info (variable values, flow control)
- **INFO**: General informational messages (user actions, state changes)
- **WARNING**: Warning conditions (deprecated features, unusual situations)
- **ERROR**: Error conditions (operation failures, recoverable errors)
- **CRITICAL**: Critical errors (system failures, unrecoverable errors)

### 2. Include Context

Always include relevant context in logs:

```python
# Good
logger.info("User login", extra={"user_id": user_id, "ip": client_ip})

# Bad
logger.info("User login")
```

### 3. Avoid Sensitive Data

Never log sensitive information:

```python
# Bad - logs password
logger.info(f"User login with password {password}")

# Good - logs only user ID
logger.info("User login", extra={"user_id": user_id})
```

### 4. Use Request IDs

Always use request IDs for distributed tracing:

```python
# In middleware or services
request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

# Include in all logs
logger.info("Processing trade", extra={"request_id": request_id})
```

### 5. Log Exceptions Properly

Always include the exception context:

```python
try:
    process_data()
except Exception as exc:
    logger.error("Processing failed", exc_info=True)  # Include stack trace
    raise
```

## Troubleshooting

### Logs Not Appearing

1. Check log level: `LOG_LEVEL=DEBUG`
2. Check debug mode: `DEBUG=true`
3. Verify logger name: use `logging.getLogger(__name__)`
4. Check Docker logs: `docker-compose logs backend`

### High Disk Usage

Log files can grow quickly. The docker-compose configuration limits file size:

```bash
# Check log file sizes
docker inspect swing-trade-backend | grep -A 20 LogPath

# Manual cleanup (caution)
docker container logs --tail 0 swing-trade-backend > /dev/null
```

### Performance Issues

If logging causes performance problems:

1. Increase log level: `LOG_LEVEL=WARNING` (production)
2. Reduce middleware verbosity: adjust module logger levels
3. Use log aggregation: forward logs to external service

## Integration with Log Aggregation

For production deployments, integrate with log aggregation services:

### ELK Stack (Elasticsearch, Logstash, Kibana)

Logs are already in JSON format, compatible with Elasticsearch:

```yaml
# docker-compose.yml addition
logging:
  driver: "awslogs"
  options:
    awslogs-group: "/ecs/swing-trade-api"
    awslogs-region: "us-east-1"
```

### CloudWatch

AWS CloudWatch compatible logging:

```yaml
logging:
  driver: "awslogs"
  options:
    awslogs-group: "/ecs/swing-trade-api"
    awslogs-region: "us-east-1"
    awslogs-stream-prefix: "ecs"
```

### Datadog

Datadog compatible JSON logging (already supported):

```bash
# Logs automatically compatible with Datadog
```

## Metrics and Alerting

### Monitor These Metrics

1. **Error Rate**: `errors.rate` from `/api/metrics`
2. **Request Rate**: `requests.rate_per_minute`
3. **Response Time**: `duration_ms` in request logs
4. **Uptime**: `uptime_seconds` from `/api/health`

### Setup Alerting

Monitor the `/api/metrics` endpoint for:

```bash
# Alert if error rate > 1%
curl http://localhost:8000/api/metrics | jq '.errors.rate > 0.01'

# Alert if error count increasing
# (compare metrics across time)

# Alert if database unhealthy
curl http://localhost:8000/api/health | jq '.components.database'
```

## Summary

The application provides comprehensive logging and monitoring:

- Structured logging with JSON format for production
- Request ID tracking for distributed tracing
- User tracking when authenticated
- Health checks and metrics endpoints
- Performance monitoring
- Error rate tracking
- Database connectivity monitoring

Use these tools to debug issues, monitor performance, and maintain application health.
