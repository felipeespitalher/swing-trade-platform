# Docker & Local Development Guide

This guide explains how to set up and run the Swing Trade Platform using Docker for local development.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- At least 4GB RAM allocated to Docker
- 2GB free disk space

## Quick Start

### Automated Setup (Recommended)

Run the automated setup script which handles everything:

```bash
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

This script will:
- Validate Docker installation
- Check docker-compose configuration
- Create .env.local file if missing
- Build all Docker images
- Start all services
- Wait for services to be healthy
- Run connection tests

### Manual Setup

If you prefer manual setup or the script fails:

1. **Create environment file:**
   ```bash
   cp .env.example .env.local
   ```

2. **Validate docker-compose configuration:**
   ```bash
   docker-compose config
   ```

3. **Build Docker images:**
   ```bash
   docker-compose build
   ```

4. **Start all services:**
   ```bash
   docker-compose up -d
   ```

5. **Check service status:**
   ```bash
   docker-compose ps
   ```

6. **Wait for services to be ready:**
   - PostgreSQL: `docker-compose exec postgres pg_isready -U postgres`
   - Redis: `docker-compose exec redis redis-cli ping`
   - Backend API: `curl http://localhost:8000/health`

## Services

### PostgreSQL (Port 5432)

The database service with TimescaleDB extension for time-series data.

**Connection Details:**
- Host: `localhost` (or `postgres` from inside Docker network)
- Port: `5432`
- User: `postgres`
- Password: `postgres_password` (development only)
- Database: `swing_trade`

**Connect with psql:**
```bash
docker-compose exec postgres psql -U postgres -d swing_trade
```

**View tables:**
```bash
docker-compose exec postgres psql -U postgres -d swing_trade -c "\dt"
```

### Redis (Port 6379)

In-memory cache and real-time data store.

**Connection Details:**
- Host: `localhost` (or `redis` from inside Docker network)
- Port: `6379`

**Test Redis connection:**
```bash
docker-compose exec redis redis-cli ping
```

**Interactive Redis CLI:**
```bash
docker-compose exec redis redis-cli
```

### Backend API (Port 8000)

FastAPI application for trading automation logic.

**Access endpoints:**
- Health: `http://localhost:8000/health`
- API Root: `http://localhost:8000/`
- Interactive Docs: `http://localhost:8000/docs` (Swagger UI)
- Alternative Docs: `http://localhost:8000/redoc` (ReDoc)

**Test API:**
```bash
curl http://localhost:8000/health
# Expected response: {"status":"ok"}

curl http://localhost:8000/
# Expected response: {"message":"Swing Trade Automation Platform API","version":"0.1.0","docs":"/docs"}
```

### Frontend (Port 5173)

React/Vite development server for the web interface.

**Access in browser:**
- http://localhost:5173

The frontend is configured to communicate with the backend at `http://localhost:8000`.

## Common Operations

### View Logs

View logs for all services:
```bash
docker-compose logs -f
```

View logs for specific service:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f redis
```

View logs with timestamps:
```bash
docker-compose logs -f --timestamps
```

### Rebuild Images

Rebuild all images:
```bash
docker-compose build
```

Rebuild without cache (force fresh build):
```bash
docker-compose build --no-cache
```

Rebuild specific service:
```bash
docker-compose build backend
docker-compose build frontend
```

### Restart Services

Restart all services:
```bash
docker-compose restart
```

Restart specific service:
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Stop Services

Stop all services (preserve data):
```bash
docker-compose stop
```

Stop specific service:
```bash
docker-compose stop backend
```

### Remove Services

Remove all containers and networks (preserve volumes):
```bash
docker-compose down
```

Remove everything including volumes (clean slate):
```bash
docker-compose down -v
```

### Execute Commands in Containers

Run a command in a running container:

```bash
# Run Python command in backend
docker-compose exec backend python -c "import sys; print(sys.version)"

# Run npm command in frontend
docker-compose exec frontend npm list

# Run psql in PostgreSQL
docker-compose exec postgres psql -U postgres -d swing_trade
```

### Run with Specific Environment

Use custom environment file:
```bash
docker-compose --env-file .env.production up -d
```

## Development Workflow

### Hot Reload

Both backend and frontend are configured with hot reload for development:

- **Backend:** Uvicorn with `--reload` flag detects changes in `/app/app` directory
- **Frontend:** Vite dev server detects changes in `/app/src` directory

Simply edit your source files, and changes will be automatically picked up!

### Database Migrations

The migrations are stored in `backend/migrations/` and run during startup.

View migration status:
```bash
docker-compose exec backend python migrations.py status
```

Run migrations manually:
```bash
docker-compose exec backend python migrations.py upgrade
```

Rollback migrations:
```bash
docker-compose exec backend python migrations.py downgrade
```

### Install Python Dependencies

If you add new dependencies to `backend/requirements.txt`:

```bash
docker-compose build backend
docker-compose up -d backend
```

Or install in running container:
```bash
docker-compose exec backend pip install package-name
```

### Install Frontend Dependencies

If you add new dependencies to `frontend/package.json`:

```bash
docker-compose build frontend
docker-compose up -d frontend
```

Or install in running container:
```bash
docker-compose exec frontend npm install
```

## Troubleshooting

### Services Won't Start

1. Check if ports are already in use:
   ```bash
   # Check which process is using ports
   lsof -i :5432    # PostgreSQL
   lsof -i :6379    # Redis
   lsof -i :8000    # Backend
   lsof -i :5173    # Frontend
   ```

2. Check Docker disk space:
   ```bash
   docker system df
   docker system prune  # Clean up unused images/containers
   ```

3. View detailed error logs:
   ```bash
   docker-compose logs
   ```

### PostgreSQL Connection Fails

1. Wait longer for PostgreSQL to start:
   ```bash
   docker-compose logs postgres
   ```

2. Check health status:
   ```bash
   docker-compose ps postgres
   ```

3. Try connecting directly:
   ```bash
   docker-compose exec postgres psql -U postgres -d postgres
   ```

### Backend API Not Responding

1. Check container logs:
   ```bash
   docker-compose logs backend
   ```

2. Check if it's still starting:
   ```bash
   docker-compose ps backend
   ```

3. Verify dependencies are healthy:
   ```bash
   docker-compose ps
   ```

### Frontend Shows Blank Page

1. Check browser console for errors (F12)
2. Verify API connection:
   ```bash
   curl http://localhost:8000/health
   ```
3. Check frontend logs:
   ```bash
   docker-compose logs frontend
   ```

### Port Already in Use

If a port is already in use, modify the port mapping in `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Use 8001 instead of 8000
```

Then restart:
```bash
docker-compose restart backend
```

### Memory Issues

If Docker runs out of memory:

1. Increase Docker memory allocation in Docker Desktop settings
2. Or reduce services running simultaneously:
   ```bash
   docker-compose stop frontend  # Stop frontend if not needed
   ```

### Clean Reset

If everything is broken, do a complete reset:

```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker-compose rm -f

# Rebuild from scratch
docker-compose build --no-cache

# Start fresh
docker-compose up -d

# Run setup script
./scripts/docker-setup.sh
```

## Environment Variables

### Development Configuration

The `.env.local` file contains development settings:

```
DATABASE_URL=postgresql://postgres:postgres_password@postgres:5432/swing_trade
REDIS_URL=redis://redis:6379/0
SECRET_KEY=dev-secret-key-change-in-prod
ENCRYPTION_KEY=dev-encryption-key-change-in-prod
FRONTEND_URL=http://localhost:5173
API_DEBUG=true
```

### Production Considerations

For production deployment:

1. Use strong, unique keys for `SECRET_KEY` and `ENCRYPTION_KEY`
2. Use proper SMTP credentials for email
3. Configure AWS credentials if using S3
4. Update all default passwords
5. Use proper database backup strategies
6. Configure proper logging and monitoring

## Volume Structure

- `postgres_data`: PostgreSQL data persistence
- `redis_data`: Redis data persistence (optional)
- `./backend/app`: Backend source code (mounted for hot reload)
- `./frontend/src`: Frontend source code (mounted for hot reload)

## Network

All services communicate through the `swing-trade-network` bridge network. Internal service names for communication:

- Backend: `http://backend:8000`
- Frontend: `http://frontend:5173`
- PostgreSQL: `postgres:5432`
- Redis: `redis:6379`

## Performance Tips

1. **Use volumes for database:** Reduces I/O overhead
2. **Hot reload enabled:** Change detection is automatic
3. **Multi-stage builds:** Frontend uses optimized Alpine image
4. **Resource limits:** Consider adding memory/CPU limits in docker-compose
5. **Network:** All services on same bridge network for fast communication

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)

## Support

For issues or questions:

1. Check logs: `docker-compose logs`
2. Run diagnostics: `./scripts/docker-setup.sh`
3. Review this guide's troubleshooting section
4. Check Docker Desktop status and resource allocation
