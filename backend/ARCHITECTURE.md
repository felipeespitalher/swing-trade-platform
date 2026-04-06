# Architecture

## Overview

The Swing Trade Automation Platform backend is a FastAPI monorepo backed by PostgreSQL with the TimescaleDB extension for time-series trade data, and Redis for rate limiting and CSRF token storage. All user data is strictly isolated at the database level using PostgreSQL Row-Level Security (RLS) policies.

## Components Diagram

```
           Client (browser / bot)
                    |
                    | HTTPS
                    v
         +---------------------+
         |   FastAPI (uvicorn)  |
         |                     |
         |  Middleware stack:  |
         |  1. LoggingMW       |
         |  2. AuditMW         |
         |  3. CSRF MW         |
         |  4. RateLimitMW     |
         |  5. CORS MW         |
         |                     |
         |  Routers:           |
         |  /api/auth          |
         |  /api/users         |
         |  /api/exchange-keys |
         |  /api/audit         |
         |  /health            |
         +---------------------+
              |           |          |
              v           v          v
       PostgreSQL       Redis    SMTP / Email
       + TimescaleDB   (rate      (console mock
       (users, keys,    limit,     in dev)
        trades,         CSRF
        audit_logs,     tokens)
        strategies,
        ohlcv,
        backtest_results)
```

## Database Schema

| Table              | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `users`            | User accounts with hashed passwords and email verification tokens           |
| `exchange_keys`    | Encrypted exchange API credentials (AES-256-GCM per record)                 |
| `strategies`       | Automated trading strategy configurations per user                          |
| `trades`           | Trade execution records linked to strategies and users                      |
| `ohlcv`            | TimescaleDB hypertable for OHLCV candlestick market data                    |
| `backtest_results` | Historical backtest performance results per strategy                         |
| `audit_logs`       | Append-only audit trail for all mutating API actions                        |

## Authentication Flow

```
Register ──> (email verification sent)
    |
    v
Verify Email ──> user.is_email_verified = true
    |
    v
Login ──> JWT access_token (15–60 min) + refresh_token (7 days)
    |
    v
Authenticated requests ──> Bearer <access_token> in Authorization header
    |
    v
Token expired ──> POST /api/auth/refresh ──> new access_token
```

## Security Layers

| Layer            | Mechanism                                                                        |
|------------------|----------------------------------------------------------------------------------|
| Authentication   | JWT HS256, configurable expiry, refresh token rotation                           |
| Encryption       | AES-256-GCM with unique IV per encryption operation, PBKDF2 key derivation       |
| Authorization    | PostgreSQL RLS (18 policies), user_id filter on every query                      |
| Rate Limiting    | Redis sliding-window counter: 5 req/min on `/login`, 3/5min on `/register`       |
| CSRF Protection  | One-time Redis-backed tokens, `X-CSRF-Token` header, consumed on use             |
| Audit            | Append-only `audit_logs` table, all POST/PATCH/DELETE actions recorded           |

## Middleware Stack

Middleware is applied in reverse order (last added = outermost):

1. **CORSMiddleware** — allows configured origins, methods, headers
2. **RateLimitMiddleware** — enforces per-endpoint request rate limits via Redis
3. **CSRFMiddleware** — validates one-time CSRF tokens on state-changing requests
4. **AuditMiddleware** — records successful mutating operations to audit_logs
5. **LoggingMiddleware** — structured request/response logging with trace IDs

## Multi-Tenant Architecture

Each `User` is treated as a tenant. Isolation is enforced at three levels:

1. **PostgreSQL RLS**: Every table that stores user data has `ENABLE ROW LEVEL SECURITY` and `USING (user_id = current_setting('app.current_user_id')::uuid)` policies. The application calls `SET LOCAL app.current_user_id = '<uuid>'` at the start of each authenticated request.

2. **Service layer**: All service methods accept `user_id` and include it in every query predicate. Data is never filtered in application memory.

3. **Defence-in-depth**: `TenantValidator` provides explicit ownership checks as a secondary safeguard.

This multi-layer approach ensures that even if one layer has a bug, the others prevent data leakage between users.
