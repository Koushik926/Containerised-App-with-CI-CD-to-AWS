# Testing & Results

## Test Case Table

| ID | Test | Steps | Expected Result | Actual Result |
|----|------|-------|-----------------|---------------|
| TC1 | Unit/Integration tests pass | Run `make test` | All tests pass, coverage ≥ 85% | |
| TC2 | Local development works | Run `make dev`, open `/docs` | Swagger UI loads, can register/login/CRUD | |
| TC3 | Task ownership enforced | User B tries to access User A's task | 404 Not Found | |
| TC4 | Docker image is production-ready | Check `docker images`, run `docker run --rm <img> id` | Image < 200MB, runs as non-root | |
| TC5 | Feature branch triggers CI only | Push to `feature/xyz` | lint/test/build run, deploy does NOT run | |
| TC6 | PR builds but doesn't push | Open PR to main | Image built, NOT pushed to GHCR | |
| TC7 | Main push without secrets | Push to main (no EC2 secrets) | Pipeline green, deploy skipped with message | |
| TC8 | Main push with secrets | Push to main (secrets configured) | Deploy succeeds, `/version` shows commit SHA | |
| TC9 | Automatic rollback | Deploy broken `/health/ready` | Rollback triggered, old version serves | |
| TC10 | Manual rollback | Trigger Manual Rollback workflow | Previous version deployed, health check passes | |
| TC11 | Trivy scan results | Check Security tab after build | Vulnerabilities listed (or clean) | |
| TC12 | Data persists across deploys | Create task, deploy new version, check task | Task still exists | |
| TC13 | Local EC2 rehearsal | Run `make sim-up && make sim-deploy` | Full deploy flow works on Multipass VM | |
| TC14 | Terraform validates | Run `terraform validate` and `tflint` | No errors or warnings | |

## Running the Test Suite

### Prerequisites

- Docker and Docker Compose installed
- Python 3.12 with virtualenv
- Make

### Local Testing

```bash
# Install dependencies
make install

# Run tests with coverage
make test
```

The test suite:
1. Starts a PostgreSQL container (`docker-compose.test.yml`)
2. Runs Alembic migrations
3. Executes pytest with coverage
4. Tears down the test database

### Coverage Report

After running tests, view the coverage report:

```bash
# Terminal summary is shown automatically

# For HTML report:
coverage html
open htmlcov/index.html
```

### Test Categories

| Category | Description | Files |
|----------|-------------|-------|
| Auth | Registration, login, token validation | `tests/test_auth.py` |
| Tasks | CRUD operations, filters, ownership | `tests/test_tasks.py` |
| Health | Liveness, readiness probes | `tests/test_health.py` |

### Database Isolation

Tests use:
- Separate PostgreSQL container on port 5433
- Unique UUIDs in test data to avoid conflicts
- Transaction rollback or fresh data per test

## CI/CD Pipeline Testing

### Test Locally Before Push

```bash
# Run the same checks as CI
make lint      # ruff check, ruff format --check, mypy
make test      # pytest with coverage gate

# Build image locally
make build

# Test production stack
make run-prod-local
curl http://localhost:8081/health/ready
make stop-prod-local
```

### Verifying Pipeline Behavior

| Scenario | How to Test |
|----------|-------------|
| Lint failure | Introduce a ruff error, push, observe failure |
| Test failure | Add a failing test, push, observe failure |
| Coverage failure | Remove tests to drop below 85%, push |
| Build failure | Break the Dockerfile, push |
| Deploy skip | Remove EC2 secrets, push to main |
| Deploy success | Configure secrets, push to main |
| Rollback | Deploy code that fails health check |

## Security Testing

### Trivy Scan

The CI pipeline runs Trivy on every build:

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@0.28.0
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:sha-${{ github.sha }}
    severity: 'CRITICAL,HIGH'
```

Results appear in the GitHub Security tab.

### pip-audit

Dependency vulnerabilities are checked:

```yaml
- name: Run pip-audit
  run: |
    pip install pip-audit
    pip-audit -r requirements.txt --desc || true
```

### Manual Security Checks

```bash
# Check container runs as non-root
docker run --rm ghcr.io/koushik926/taskflow-api:latest id
# Should output: uid=10001 gid=10001

# Verify no DB port exposed in production
docker compose -f docker-compose.prod.yml config | grep -A5 "ports:"
# PostgreSQL should have no ports section

# Check for secrets in image
docker history ghcr.io/koushik926/taskflow-api:latest
# No secrets should appear in layer commands
```

## Load Testing (Optional)

For basic load testing:

```bash
# Install hey
brew install hey

# Test health endpoint
hey -n 1000 -c 50 http://localhost:8000/health/ready

# Test authenticated endpoint (requires token)
hey -n 1000 -c 50 -H "Authorization: Bearer $TOKEN" http://localhost:8000/tasks
```

Expected results on t4g.micro:
- Health endpoint: >500 req/sec
- Task list: >100 req/sec (database-bound)

## Troubleshooting Test Failures

| Symptom | Cause | Solution |
|---------|-------|----------|
| `connection refused` | Test DB not running | Check `docker compose -f docker-compose.test.yml ps` |
| `permission denied` | Socket permissions | Restart Docker daemon |
| Coverage below 85% | Missing tests | Add tests for uncovered code paths |
| `asyncpg` errors | Connection pool exhausted | Increase pool size or reduce test parallelism |
| Flaky tests | Race conditions | Add proper async handling, use unique test data |
