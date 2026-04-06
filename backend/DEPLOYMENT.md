# Deployment Guide

## Prerequisites

- Python 3.11+
- Docker 24+ and Docker Compose v2
- PostgreSQL 15+ with TimescaleDB extension
- Redis 7+
- (Optional) A working SMTP server for email verification

## Local Development

### Option A — Docker Compose (recommended)

```bash
# Clone the repository
git clone <repo-url>
cd swing-trade-platform

# Copy and edit environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your secrets

# Start all services
docker-compose up --build

# The API is available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Option B — Native Python

```bash
cd backend

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate   # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or create .env file)
export DATABASE_URL="postgresql://postgres:password@localhost:5432/swing_trade"
export SECRET_KEY="change-me"
export ENCRYPTION_MASTER_KEY="change-me"
export REDIS_URL="redis://localhost:6379/0"

# Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable                      | Required | Description                                           |
|-------------------------------|----------|-------------------------------------------------------|
| `DATABASE_URL`                | Yes      | PostgreSQL connection string                          |
| `SECRET_KEY`                  | Yes      | JWT signing secret (min 32 characters in production)  |
| `ENCRYPTION_MASTER_KEY`       | Yes      | AES-256-GCM master key (min 32 characters)            |
| `REDIS_URL`                   | Yes      | Redis connection string                               |
| `SMTP_HOST`                   | No       | SMTP server (omit to use console mock)                |
| `SMTP_PORT`                   | No       | SMTP port (default: 587)                              |
| `SMTP_USER`                   | No       | SMTP username                                         |
| `SMTP_PASSWORD`               | No       | SMTP password                                         |
| `SMTP_FROM_EMAIL`             | No       | From address for outgoing emails                      |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | JWT access token lifetime (default: 60)               |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | No       | Refresh token lifetime in days (default: 7)           |
| `ENVIRONMENT`                 | No       | `development` or `production` (default: development)  |
| `LOG_LEVEL`                   | No       | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: INFO)   |
| `LOG_FORMAT`                  | No       | `json` or `text` (default: json)                      |

## Docker Compose

`docker-compose.yml` at the project root starts three services:

- **api** — the FastAPI application on port 8000
- **db** — PostgreSQL 15 with TimescaleDB on port 5432
- **redis** — Redis 7 on port 6379

Volumes `postgres_data` and `redis_data` are used for persistence.

## Running Migrations

Migrations are managed by Flyway. Files live in `backend/migrations/` using the `V{N}__description.sql` naming convention.

```bash
# Run migrations (requires DATABASE_URL to be set)
flyway -url=jdbc:postgresql://localhost:5432/swing_trade \
       -user=postgres \
       -password=password \
       -locations=filesystem:backend/migrations \
       migrate

# Or via the helper script (if available)
cd backend && python migrations.py
```

## Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_auth.py -v

# Run a single test method
pytest tests/test_auth.py::TestUserRegistration::test_register_success -v

# Run integration tests only
pytest tests/test_integration.py -v

# Skip slow tests
pytest -m "not slow"
```

Test environment notes:
- Without `TEST_DATABASE_URL`, tests use SQLite (in-memory).
- With `TEST_DATABASE_URL=<postgres-url>`, tests use a real PostgreSQL instance with RLS.

## Production Deployment

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Deploy
railway up
```

Set all required environment variables in the Railway dashboard under **Variables**.

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app (first time)
fly launch --dockerfile backend/Dockerfile

# Deploy updates
fly deploy --dockerfile backend/Dockerfile

# Set secrets
fly secrets set SECRET_KEY="..." ENCRYPTION_MASTER_KEY="..." DATABASE_URL="..."
```

### Health Check

The `/health` endpoint returns `200 OK` and is exempt from rate limiting. Use it as a liveness and readiness probe:

```
GET /health
```
