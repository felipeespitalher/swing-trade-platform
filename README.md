# Swing Trade Automation Platform

A comprehensive platform for automated swing trading analysis, execution, and portfolio management. Built with FastAPI (Python) backend and React (TypeScript) frontend, running on PostgreSQL with TimescaleDB extension for time-series data.

## Project Overview

The Swing Trade Automation Platform provides:

- **Automated Analysis**: Real-time technical analysis and pattern recognition
- **Execution Engine**: Automated trade execution with risk management
- **Portfolio Management**: Multi-account portfolio tracking and analytics
- **Market Data**: Time-series data storage with TimescaleDB
- **WebSocket Support**: Real-time market updates and notifications
- **API-First Design**: RESTful API with comprehensive documentation

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | FastAPI | 0.104.1 |
| Server | Uvicorn | 0.24.0 |
| Database | PostgreSQL + TimescaleDB | 15 |
| Cache | Redis | 7 |
| Frontend | React | 18 |
| Frontend Build | Vite | Latest |
| Language | Python 3.11+ / TypeScript |

## Project Structure

```
swing-trade-platform/
├── backend/
│   ├── app/
│   │   ├── api/                 # API route definitions
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── core/                # Configuration and utilities
│   │   ├── db/                  # Database setup and session management
│   │   ├── services/            # Business logic layer
│   │   ├── middleware/          # Custom middleware
│   │   ├── migrations/          # Alembic migrations (future)
│   │   └── main.py              # FastAPI application entry point
│   ├── tests/                   # Unit and integration tests
│   ├── requirements.txt         # Python dependencies
│   └── pyproject.toml           # Python project metadata (future)
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API client services
│   │   ├── hooks/               # Custom React hooks
│   │   ├── types/               # TypeScript type definitions
│   │   ├── styles/              # Global styles
│   │   └── App.tsx              # Root component
│   ├── package.json             # Node dependencies
│   ├── tsconfig.json            # TypeScript configuration
│   └── vite.config.ts           # Vite configuration
├── docker-compose.yml           # Container orchestration
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## Prerequisites

- **Python 3.11+** (for backend development)
- **Node.js 18+** (for frontend development)
- **Docker & Docker Compose** (for containerized development)
- **Git** (for version control)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd swing-trade-platform
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your local configuration
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` with docs at `http://localhost:8000/docs`

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Docker Compose Setup

Start all services with a single command:

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379

Verify services are running:

```bash
docker-compose ps
```

Stop all services:

```bash
docker-compose down
```

### Database Access

Connect to PostgreSQL:

```bash
# Using psql directly
psql -h localhost -U postgres -d swing_trade

# Using Docker
docker exec -it swing-trade-postgres psql -U postgres -d swing_trade
```

Default credentials:
- Username: `postgres`
- Password: `postgres_password`
- Database: `swing_trade`

## API Documentation

### Health Check

```bash
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

### API Documentation (Swagger)

Interactive API docs available at: `http://localhost:8000/docs`

Alternative (ReDoc): `http://localhost:8000/redoc`

## Frontend Development

### Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npm run type-check

# Format code
npm run format

# Lint code
npm run lint
```

## Backend Development

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_main.py

# Run specific test function
pytest tests/test_main.py::test_health_check
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/db` |
| `SECRET_KEY` | JWT signing key | 32+ character random string |
| `ENCRYPTION_KEY` | Data encryption key | 32+ character random string |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `VITE_API_URL` | Backend API URL (frontend) | `http://localhost:8000` |
| `ENVIRONMENT` | Runtime environment | `development` or `production` |

## Git Workflow

### Branch Naming

- `feat/<feature-name>` - New features
- `fix/<bug-name>` - Bug fixes
- `chore/<task-name>` - Maintenance tasks

### Commit Message Format

```
<type>: <description>

<optional detailed explanation>
```

Types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`

Example:
```
feat: add user authentication endpoints

Implement JWT-based authentication with refresh token rotation
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes and commit
3. Push to remote
4. Create pull request with description
5. Code review and CI checks must pass
6. Merge to `main`

## Deployment

### Production Build

Backend:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
npm run build
npm run preview
```

### Docker Deployment

Build and run production containers:

```bash
docker-compose -f docker-compose.yml up -d
```

## Troubleshooting

### Port Already in Use

If port 8000 or 5173 is already in use:

```bash
# Kill process on port 8000
# On Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### Database Connection Error

Ensure PostgreSQL is running:

```bash
docker-compose ps postgres

# If not running
docker-compose up -d postgres
```

### Module Import Errors

Ensure virtual environment is activated and dependencies installed:

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Contributing

1. Follow the branch naming conventions
2. Ensure all tests pass before pushing
3. Run code formatters before committing
4. Write meaningful commit messages
5. Keep PRs focused and reasonably sized

## License

[Add your license here]

## Support

For issues and questions, please create a GitHub issue or contact the development team.

---

**Last Updated**: 2024
