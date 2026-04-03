# GitHub Actions Workflows Documentation

This document explains the GitHub Actions CI/CD pipelines for the Swing Trade Automation Platform.

## Overview

All workflows are configured to:
- Trigger on pushes to `main`, `develop`, and `master` branches
- Trigger on pull requests to those branches
- Run tests, linting, security scans, and build verification
- Require branch protection to pass all checks before merging

## Workflows

### 1. Backend Tests & Coverage (`backend-test.yml`)

**Runs:** Every push and pull request affecting backend code

**What it does:**
- Sets up Python 3.11
- Starts a PostgreSQL/TimescaleDB test database
- Installs backend dependencies from `requirements.txt`
- Runs pytest with coverage reporting
- Enforces minimum 80% code coverage
- Uploads coverage reports to Codecov (optional)

**Key metrics:**
- Coverage must be ≥80%
- All tests must pass
- Database is available at `postgresql://postgres:postgres_password@localhost:5432/swing_trade_test`

**Configuration in the workflow:**
```yaml
- pytest tests/ --cov=app --cov-fail-under=80
```

**Failure handling:**
- If any test fails, the workflow fails
- If coverage drops below 80%, the workflow fails
- Codecov upload failures are non-blocking

**Local equivalent:**
```bash
cd backend
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80
```

---

### 2. Backend Linting & Formatting (`backend-lint.yml`)

**Runs:** Every push and pull request affecting backend code

**What it does:**
- Sets up Python 3.11
- Installs linting tools: black, isort, flake8, pylint, mypy
- Checks code formatting with **black** (must match style)
- Checks import sorting with **isort** (must be sorted correctly)
- Checks style violations with **flake8**
- Reports pylint scores

**Tools and their purposes:**

| Tool   | Purpose | Enforced |
|--------|---------|----------|
| black  | Code formatting | Yes (check mode) |
| isort  | Import sorting | Yes (check mode) |
| flake8 | Style violations (PEP 8) | Yes (check mode) |
| pylint | Code quality score | No (informational) |
| mypy   | Type checking | Can be enabled |

**Configuration:**
- **black**: Uses default 88-character line length
- **isort**: Standard Python import grouping
- **flake8**: Max line length 120, ignores E203, W503
- **pylint**: Requires score ≥8 (informational only)

**Local equivalent (fixing issues):**
```bash
cd backend
black app tests           # Auto-format code
isort app tests           # Auto-sort imports
flake8 app tests          # Show style issues
pylint app --disable=R,C  # Show quality score
```

**Note:** Continue-on-error is set to `true` for linting workflows to report all issues without blocking. Fix linting issues before pushing to main.

---

### 3. Backend Security Scan (`backend-security.yml`)

**Runs:**
- Every push and pull request affecting backend code
- Weekly on Sunday at 00:00 UTC (scheduled scan)

**What it does:**
- Sets up Python 3.11
- Installs dependencies and security tools: **bandit**, **pip-audit**
- Runs **bandit** to scan for common Python security issues
- Runs **pip-audit** to check for known vulnerabilities in dependencies
- Reports critical and high-severity findings

**Tools and their purposes:**

| Tool | Purpose |
|------|---------|
| bandit | Scans code for security issues (hardcoded secrets, insecure functions, etc.) |
| pip-audit | Checks installed packages for known CVEs |

**Configuration:**
- **bandit**: `-ll` flag = low confidence level (reports more issues)
- **pip-audit**: Checks all packages except editable installs

**Local equivalent:**
```bash
cd backend
bandit -r app -ll          # Scan for security issues
pip-audit --skip-editable  # Check for vulnerable dependencies
```

**Common findings:**
- Hardcoded secrets (use environment variables instead)
- Use of insecure cryptography
- SQL injection risks
- Known CVEs in dependencies

**How to fix:**
1. For bandit findings: Update code to use secure patterns
2. For pip-audit findings: Update vulnerable packages (`pip install --upgrade [package]`)
3. Commit and push — workflow will re-run automatically

---

### 4. Frontend Tests & Build (`frontend-test.yml`)

**Runs:** Every push and pull request affecting frontend code

**What it does:**
- Sets up Node 20
- Installs dependencies with `npm ci` (clean install)
- Runs ESLint for code quality
- Builds the application for production

**Key steps:**

1. **Dependency Installation:**
   ```bash
   cd frontend
   npm ci  # Clean install (respects package-lock.json)
   ```

2. **Linting:**
   ```bash
   npm run lint  # Runs ESLint
   ```

3. **Build:**
   ```bash
   npm run build  # TypeScript + Vite build
   ```

**Local equivalent:**
```bash
cd frontend
npm ci
npm run lint
npm run build
```

**What gets built:**
- TypeScript compiled to JavaScript
- Assets optimized and minified
- Output to `dist/` directory

**Failure conditions:**
- Linting errors (reported but non-blocking with `|| true`)
- Build failures (blocking)
- Missing dependencies (blocking)

---

### 5. Docker Build & Push (`docker-build.yml`)

**Runs:**
- Every push to `main` or `master` branch
- On release publications

**What it does:**
- Sets up Docker Buildx for multi-platform builds
- Builds backend Docker image from `backend/Dockerfile`
- Builds frontend Docker image from `frontend/Dockerfile`
- Uses GitHub Actions cache to speed up builds
- Validates docker-compose configuration

**Key features:**

1. **Build caching:** Leverages GitHub Actions cache layer for faster builds
2. **No push (by default):** Images are built but not pushed to registry
3. **Docker Compose validation:** Ensures `docker-compose.yml` is valid YAML

**Local equivalent:**
```bash
docker build -f backend/Dockerfile -t swing-trade-backend:latest ./backend
docker build -f frontend/Dockerfile -t swing-trade-frontend:latest ./frontend
docker-compose config  # Validate config
```

**To enable image pushing:**

If you want to push images to a container registry (Docker Hub, GitHub Container Registry, etc.), modify the workflow:

```yaml
- name: Build and push backend
  uses: docker/build-push-action@v5
  with:
    context: ./backend
    file: ./backend/Dockerfile
    push: true  # Enable pushing
    tags: your-registry/swing-trade-backend:latest
    registry: docker.io
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}
```

---

## Setup Instructions

### 1. Push Workflows to GitHub

```bash
git add .github/
git commit -m "ci: add GitHub Actions CI/CD workflows"
git push origin [your-branch]
```

### 2. Configure Branch Protection Rules

1. Go to your GitHub repository
2. **Settings** → **Branches**
3. Click **Add rule** under "Branch protection rules"
4. Configure for branch `main`:

   **Basic settings:**
   - Branch name pattern: `main`
   - ✓ Require a pull request before merging
   - ✓ Require status checks to pass before merging

   **Status checks:**
   - ✓ Require branches to be up to date before merging
   - Select these checks:
     - `Backend Tests & Coverage` (backend-test)
     - `Backend Linting & Formatting` (backend-lint)
     - `Backend Security Scan` (backend-security)
     - `Frontend Tests & Build` (frontend-test)
     - `Docker Build & Push` (docker-build)

   **Additional settings:**
   - ✓ Require code reviews before merging (at least 1)
   - ✓ Require approval of the most recent reviewable push
   - ✓ Dismiss stale pull request approvals when new commits are pushed

5. Click **Create**

### 3. Add Secrets (Optional)

For Docker registry pushes and Codecov uploads, add secrets:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**

**For Codecov:**
- Name: `CODECOV_TOKEN`
- Value: Your Codecov API token

**For Docker Registry:**
- Name: `DOCKER_USERNAME`
- Value: Your Docker Hub username
- Name: `DOCKER_PASSWORD`
- Value: Your Docker Hub token (not password)

### 4. Configure Database Credentials

Backend tests use these credentials (hardcoded in workflow, safe for test environment):
- Host: `localhost:5432`
- User: `postgres`
- Password: `postgres_password`
- Database: `swing_trade_test`

To customize, update the `postgres` service in `backend-test.yml`:

```yaml
services:
  postgres:
    env:
      POSTGRES_PASSWORD: your_password
```

---

## Troubleshooting

### "Backend Tests & Coverage" fails

**Issue: Tests fail**
```
FAILED tests/test_something.py::test_feature
```

**Solution:**
1. Run locally: `cd backend && pytest tests/ -v`
2. Check for missing dependencies: `pip install -r requirements.txt`
3. Check database connection: Is PostgreSQL running?
4. Fix the failing test and commit

**Issue: Coverage below 80%**
```
FAILED -- coverage dropped below 80%
```

**Solution:**
1. Check coverage report: `pytest tests/ --cov=app --cov-report=term-missing`
2. Add tests for uncovered code
3. If coverage is intentionally lower, adjust `--cov-fail-under=80` to a lower threshold

**Issue: PostgreSQL service won't start**
```
ERROR: could not translate host name "postgres" to address
```

**Solution:**
1. Service must be defined in the `services:` section of the workflow
2. Check the health check configuration
3. Verify environment variables are correct

---

### "Backend Linting & Formatting" fails

**Issue: Black formatting check fails**
```
ERROR: would reformat backend/app/main.py
```

**Solution:**
```bash
cd backend
black app tests  # Auto-format code
git add app tests
git commit -m "style: format code with black"
git push
```

**Issue: isort import sorting fails**
```
ERROR: Imports are incorrectly sorted
```

**Solution:**
```bash
cd backend
isort app tests  # Auto-sort imports
git add app tests
git commit -m "style: sort imports with isort"
git push
```

**Issue: flake8 style violations**
```
E501 line too long (121 > 120 characters)
```

**Solution:**
1. Reduce line length or split into multiple lines
2. If line must be long, add `# noqa: E501` comment
3. Commit and push

---

### "Backend Security Scan" fails

**Issue: Bandit finds security issues**
```
[MEDIUM] Use of insecure MD5 hash function
```

**Solution:**
1. Review the finding in the workflow logs
2. Fix the security issue in your code
3. For false positives, add `# noqa: B303` comment
4. Commit and push

**Issue: pip-audit finds vulnerable dependency**
```
Found 1 known vulnerability in requests==2.25.0
```

**Solution:**
```bash
cd backend
pip install --upgrade requests  # Or the vulnerable package
pip freeze > requirements.txt
git add requirements.txt
git commit -m "chore: update vulnerable dependencies"
git push
```

---

### "Frontend Tests & Build" fails

**Issue: Build fails with TypeScript errors**
```
TS2322: Type '"button"' is not assignable to type '"submit"'
```

**Solution:**
1. Run locally: `cd frontend && npm run build`
2. Fix TypeScript errors
3. Commit and push

**Issue: ESLint finds violations**
```
error: Unexpected any in foo.ts
```

**Solution:**
1. Fix the violation in your code
2. Or add `// eslint-disable-line rule-name` if necessary
3. Commit and push

**Issue: npm ci fails**
```
ERR! code ERESOLVE
```

**Solution:**
1. Update package-lock.json locally: `npm ci`
2. Commit the updated `package-lock.json`
3. Push

---

### "Docker Build & Push" fails

**Issue: Dockerfile build error**
```
ERROR: failed to solve with frontend dockerfile.v0
```

**Solution:**
1. Test locally: `docker build -f backend/Dockerfile ./backend`
2. Fix the Dockerfile
3. Commit and push

**Issue: docker-compose config validation fails**
```
ERROR: invalid compose file
```

**Solution:**
1. Validate locally: `docker-compose config`
2. Fix the YAML syntax in docker-compose.yml
3. Commit and push

---

## Monitoring Workflow Runs

### View Workflow Runs

1. Go to your GitHub repository
2. Click **Actions** tab
3. Select a workflow from the left sidebar
4. View all runs with status (✓ passed, ✗ failed, ⏳ in progress)

### View Detailed Logs

1. Click on a workflow run
2. Click on the failed job
3. Expand any step to see the full output
4. Search for error messages and stack traces

### Re-run a Failed Workflow

1. Click the failed run
2. Click **Re-run failed jobs** (top right)
3. The workflow will run again with the same code

---

## Performance & Cost

### Execution Times (typical)

| Workflow | Time |
|----------|------|
| Backend Tests | 60-90 seconds |
| Backend Linting | 20-30 seconds |
| Backend Security | 30-45 seconds |
| Frontend Tests | 40-60 seconds |
| Docker Build | 90-120 seconds |

### GitHub Actions Billing

- **Free tier:** 2,000 minutes/month on ubuntu-latest
- **With Actions Pro:** Higher limits
- Most CI/CD pipelines stay well within free tier

### Optimization Tips

1. Use caching (`cache: 'pip'` for Python, `cache: 'npm'` for Node)
2. Filter workflows by paths to avoid unnecessary runs
3. Use `continue-on-error: true` for non-critical checks
4. Consider scheduled security scans instead of running on every commit

---

## Extending Workflows

### Add a new workflow

1. Create `.github/workflows/new-workflow.yml`
2. Define triggers, jobs, and steps
3. Test locally with [act](https://github.com/nektos/act)
4. Commit and push

### Example: Add a scheduled nightly build

```yaml
name: Nightly Build

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run full test suite
        run: ./scripts/full-test.sh
```

### Add a custom status check

```yaml
- name: Custom validation
  run: |
    ./scripts/validate.sh
    if [ $? -ne 0 ]; then
      echo "Validation failed"
      exit 1
    fi
```

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python testing with pytest](https://docs.pytest.org/)
- [Node.js testing with npm](https://docs.npmjs.com/cli/v9/commands/npm-test)
- [Docker best practices](https://docs.docker.com/develop/dev-best-practices/)
- [Branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
