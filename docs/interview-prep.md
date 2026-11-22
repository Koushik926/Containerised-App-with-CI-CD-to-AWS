# Interview Preparation

20 likely questions about this project with concise answers.

## Docker & Containers

### 1. Why use multi-stage Docker builds?

Multi-stage builds separate the build environment from the runtime environment. The builder stage installs compilers and dev dependencies to create wheels, while the runtime stage contains only the final application. This reduces the image from ~1GB to ~328MB and eliminates build tools that could be security risks.

### 2. Why run containers as non-root?

If an attacker exploits a vulnerability in the application, they gain the container's user privileges. Running as root means they could potentially escape to the host. Running as UID 10001 (a non-existent user) limits damage to the container's filesystem and prevents privilege escalation.

### 3. How do health checks work and why have two endpoints?

`/health/live` returns 200 if the process is running - used by Docker to restart crashed containers. `/health/ready` checks database connectivity - used by nginx/load balancers to route traffic only to instances that can serve requests. Separating them prevents restarting a container that's just waiting for the database.

### 4. What's the difference between Docker Compose for dev, test, and prod?

Dev: Mounts code as a volume for hot-reload, exposes all ports, uses local builds. Test: Isolated database on different port, no volumes, ephemeral. Prod: Uses pre-built images from registry, no exposed database port, nginx reverse proxy, resource limits, JSON logging.

## CI/CD Pipeline

### 5. Why this job order: lint → test → build → scan → deploy?

Lint is fastest and catches obvious errors. Tests are more expensive but catch logic bugs. Build only runs if code is correct. Scan checks the final artifact. Deploy only happens after everything passes. This fails fast on cheap checks before expensive ones.

### 6. How does the deploy handle missing AWS secrets?

The deploy job checks if `EC2_HOST`, `EC2_USER`, and `EC2_SSH_KEY` secrets exist. If any are missing, it outputs a helpful message to the job summary and exits successfully, so the overall pipeline stays green. This lets you run the full CI pipeline without AWS setup.

### 7. What happens if deployment fails the health check?

The deploy script waits up to 60 seconds for `/health/ready` to return 200. If it doesn't, it automatically runs `docker compose up` with the previous image tag, prints a clear "ROLLBACK" message, and exits non-zero so the GitHub job goes red - but the old version continues serving traffic.

### 8. Why use OIDC instead of AWS access keys for GitHub Actions?

Long-lived access keys can be leaked, stolen, or forgotten. OIDC generates temporary credentials that last only for the workflow run. The IAM role's trust policy ensures only your repository can assume it, and the attached policy grants only the specific permissions needed (security group ingress rules).

## Database & Migrations

### 9. How do migrations run safely in this setup?

Migrations run in the container entrypoint, after `wait_for_db` confirms PostgreSQL is accepting connections. Alembic's version table prevents re-running migrations. If migrations fail, the container crashes → health check fails → rollback deploys the previous working version. The database schema stays at the last successful migration.

### 10. What are the limitations of this migration strategy?

It assumes single-instance deployment. With multiple instances, migrations could race. Some DDL operations lock tables. There's no automatic migration rollback - if a migration breaks something, you must write a new migration or restore from backup. For high-availability, consider running migrations as a separate step before deployment.

## Security

### 11. How are secrets handled in this project?

Secrets never appear in code or Docker images. GitHub Actions secrets are injected as environment variables at runtime. On EC2, secrets live in `/opt/taskflow/.env` which is loaded by the entrypoint. The `.gitignore` excludes `.env` files, and Trivy scans check for accidentally embedded secrets.

### 12. Why is the database port not exposed in production?

The PostgreSQL container is only accessible within the Docker network. External attackers can't connect directly to port 5432. All database access must go through the FastAPI application, which enforces authentication and authorization. This follows the principle of least privilege.

### 13. What security scanning is in place?

Trivy scans the Docker image for OS and application vulnerabilities. pip-audit checks Python dependencies against the PyPI advisory database. Dependabot creates PRs for vulnerable dependencies. hadolint checks Dockerfile best practices. These run on every build, not just releases.

## Infrastructure

### 14. Why t4g.micro instead of t3.micro?

t4g instances use ARM-based Graviton processors which offer ~40% better price/performance than x86. The t4g.micro is Free Tier eligible (750 hours/month for 12 months). The multi-arch Docker build ensures the image works on both ARM and x86.

### 15. What does the user_data script do?

It runs on first boot via cloud-init: installs Docker and the Compose plugin, creates a `deploy` user in the docker group, sets up `/opt/taskflow` with correct permissions, enables unattended security upgrades, and creates a 1GB swap file (t4g.micro only has 1GB RAM).

### 16. Why use an Elastic IP?

Without an EIP, the public IP changes if you stop/start the instance. This would break GitHub secrets (EC2_HOST) and DNS. An EIP is free while attached to a running instance. It provides a stable endpoint for the deployment pipeline.

## Architecture Decisions

### 17. Why Docker Compose on EC2 instead of ECS or Kubernetes?

For a single-service demo application, Compose provides the right level of abstraction. ECS/EKS add significant complexity (task definitions, services, load balancers, IAM roles) that would obscure the CI/CD concepts this project demonstrates. Compose also runs locally, making development and debugging straightforward.

### 18. What would you change for a production system at scale?

Move PostgreSQL to RDS for managed backups and high availability. Use ECS Fargate or EKS for auto-scaling and rolling deployments. Add an Application Load Balancer for SSL termination and health-check-based routing. Implement centralized logging with CloudWatch or ELK. Add proper monitoring with Prometheus/Grafana.

### 19. How would you achieve true zero-downtime deployments?

Blue-green deployment: run two identical environments, deploy to inactive one, switch traffic after health check. Or use ECS rolling updates with minimum healthy percent set to 100% and an ALB to drain connections. The current ~10-30 second gap happens because Compose stops containers before starting new ones.

### 20. What would break if this application needed to scale horizontally?

Session state (if any) would need to be externalized to Redis. Database connections would need pooling (PgBouncer). The deploy script assumes a single instance - parallel deploys could race. Health checks during rolling deploys need proper load balancer integration. File uploads would need S3 instead of local storage.

---

## Demo Script (5 minutes)

1. **Show the running application** (30 sec)
   - Open `http://<EC2_IP>/docs` - Swagger UI
   - Open `http://<EC2_IP>/version` - shows current commit SHA

2. **Make a visible change** (1 min)
   - Edit `app/api/health.py` - change the welcome message
   - Commit and push to main

3. **Watch the pipeline** (2 min)
   - Open GitHub Actions
   - Show each job completing: lint → test → build → scan → deploy
   - Point out the coverage report and Trivy results

4. **Verify the deployment** (30 sec)
   - Refresh `/version` - new commit SHA
   - Refresh home page - new message

5. **Demonstrate rollback** (1 min)
   - "Now let's see what happens with a bad deploy"
   - Show the Manual Rollback workflow or explain automatic rollback
   - Explain that old version continues serving during failed health checks

**Key points to emphasize:**
- Pipeline runs in ~3 minutes
- No AWS credentials in the repository (OIDC)
- Image is scanned for vulnerabilities before deploy
- Automatic rollback prevents serving broken code
