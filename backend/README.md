# Swing Trade Automation Platform — Backend API

REST API for automated swing trading analysis and execution. It handles user authentication, encrypted exchange key management, audit logging, and multi-tenant data isolation using PostgreSQL Row-Level Security (RLS).

## Stack

| Component        | Technology                                   |
|------------------|----------------------------------------------|
| Language         | Python 3.11                                  |
| Framework        | FastAPI                                      |
| Database         | PostgreSQL 15 + TimescaleDB                  |
| Cache / State    | Redis 7                                      |
| ORM              | SQLAlchemy                                   |
| Migrations       | Flyway                                       |
| Auth             | JWT (HS256) + refresh tokens                 |
| Encryption       | AES-256-GCM (per-record IV)                  |

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd swing-trade-platform

# 2. Start all services (API + PostgreSQL + Redis)
docker-compose up --build

# 3. Open the interactive API docs
open http://localhost:8000/docs
```

## Environment Variables

| Variable                   | Description                                          | Default                                                      |
|----------------------------|------------------------------------------------------|--------------------------------------------------------------|
| `DATABASE_URL`             | PostgreSQL connection string                         | `postgresql://postgres:postgres_password@localhost:5432/swing_trade` |
| `SECRET_KEY`               | JWT signing secret (change in production)            | `your-secret-key-change-in-production`                       |
| `ENCRYPTION_MASTER_KEY`    | AES-256-GCM master key (change in production)        | `your-encryption-master-key-change-in-production`            |
| `REDIS_URL`                | Redis connection string                              | `redis://localhost:6379/0`                                   |
| `SMTP_HOST`                | SMTP server hostname                                 | `` (console mock)                                            |
| `SMTP_PORT`                | SMTP server port                                     | `587`                                                        |
| `SMTP_USER`                | SMTP authentication username                         | ``                                                           |
| `SMTP_PASSWORD`            | SMTP authentication password                         | ``                                                           |
| `SMTP_FROM_EMAIL`          | Sender email address                                 | `noreply@swingtrade.local`                                   |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime in minutes              | `60`                                                         |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | JWT refresh token lifetime in days                | `7`                                                          |
| `ENVIRONMENT`              | `development` or `production`                        | `development`                                                |
| `LOG_LEVEL`                | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)  | `INFO`                                                       |
| `LOG_FORMAT`               | `json` for structured logs, `text` for development   | `json`                                                       |

## Running Tests

```bash
cd backend
pytest                          # Run all tests
pytest tests/test_auth.py -v   # Run a single test module verbosely
pytest --cov=app --cov-report=term-missing   # With coverage
```

## Architecture Overview

The backend is a FastAPI application with a layered middleware stack (tenant isolation, logging, audit, rate limiting, CSRF). All data is stored in PostgreSQL with 18 Row-Level Security policies ensuring strict per-user data isolation. See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams and component descriptions.

## API Reference

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
