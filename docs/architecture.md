# Architecture Deep Dive

## Why Docker Compose on EC2?

This project intentionally uses Docker Compose on a single EC2 instance instead of ECS, EKS, or other managed container services. Here's why:

| Consideration | Docker Compose on EC2 | ECS/EKS |
|--------------|----------------------|---------|
| **Complexity** | Minimal - one YAML file | Significant - task definitions, services, ALB, etc. |
| **Cost** | t4g.micro is Free Tier eligible | ECS/EKS add control plane costs |
| **Learning curve** | Familiar Docker patterns | AWS-specific concepts |
| **This project's scale** | Perfect fit | Overkill |
| **Resume demonstration** | Shows core CI/CD concepts | May obscure the pipeline focus |

**When to upgrade to ECS/EKS:**
- Multiple services that scale independently
- Need for auto-scaling based on load
- Zero-downtime rolling deployments (beyond simple health checks)
- Multiple environments (staging, production) with identical infrastructure

## Why GHCR Instead of ECR?

GitHub Container Registry (GHCR) was chosen over Amazon ECR for several reasons:

1. **Tight GitHub integration** - `GITHUB_TOKEN` works automatically; no additional credentials
2. **Free for public images** - No storage or transfer costs
3. **Simplified permissions** - Repository collaborators automatically have access
4. **Multi-platform support** - Works seamlessly with buildx for arm64/amd64

**When ECR makes sense:**
- Private images in AWS-heavy organizations
- Need for ECR scanning integration
- Cross-account image sharing with AWS Organizations

## Multi-Architecture Builds

The CI pipeline builds for both `linux/amd64` and `linux/arm64`:

```yaml
platforms: linux/amd64,linux/arm64
```

**Why both?**
- EC2 t4g instances are ARM-based (Graviton) - better price/performance
- Local development might be on Intel Macs or Linux x86
- Future flexibility for different deployment targets

**How it works:**
1. Docker buildx creates a manifest list
2. Each platform has its own image layer
3. `docker pull` automatically selects the correct architecture
4. The registry handles the complexity

## Migration Strategy

Database migrations run automatically on container startup:

```bash
# docker/entrypoint.sh
if is_server_command "$1"; then
    wait_for_db
    run_migrations  # alembic upgrade head
fi
exec "$@"
```

**Safety mechanisms:**
1. `wait_for_db` - Ensures PostgreSQL is accepting connections
2. Alembic's migration history table prevents duplicate runs
3. If migrations fail, the container fails to start → health check fails → rollback

**Limitations:**
- Migrations lock the database briefly during schema changes
- Not suitable for multi-instance deployments without coordination
- No automatic rollback of migrations (manual intervention required)

## Zero-Downtime Deployment Limits

The current approach has a brief downtime window:

```bash
docker compose down --timeout 30
# <-- Gap here
docker compose up -d
# <-- Health check period
```

**Current downtime: ~10-30 seconds**

**How to achieve true zero-downtime:**

1. **Blue-Green Deployment**
   - Spin up new containers alongside old ones
   - Switch nginx upstream after health check passes
   - Stop old containers

2. **ECS with rolling updates**
   - Minimum healthy percent ensures old tasks serve while new start
   - Application Load Balancer drains connections gracefully

3. **Kubernetes rolling deployment**
   - `maxUnavailable: 0` ensures old pods run until new are ready
   - Service load balances between old and new during transition

## Database Considerations

### Why PostgreSQL in a Container?

For this demo/portfolio project, containerized PostgreSQL is appropriate:
- Simple setup with docker-compose
- Data persists in a named volume
- Easy to reset for testing

### Production Recommendations

For real production workloads, use Amazon RDS:

| Feature | Container PostgreSQL | Amazon RDS |
|---------|---------------------|------------|
| Backups | Manual | Automated daily |
| High availability | None | Multi-AZ option |
| Maintenance | Your responsibility | AWS-managed |
| Scaling | Requires downtime | Storage auto-scaling |
| Cost | EC2 resources only | Additional RDS pricing |

**Migration path:**
1. Create RDS instance with same PostgreSQL version
2. Use `pg_dump`/`pg_restore` to migrate data
3. Update `DATABASE_URL` in environment
4. Test thoroughly before switching

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Internet                             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              AWS Security Group                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Ingress: 80/443 from 0.0.0.0/0                  │   │
│  │ Ingress: 22 from var.my_ip_cidr only            │   │
│  │ Egress: All                                      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   EC2 Instance                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │                 nginx :80                        │   │
│  │  - Rate limiting                                 │   │
│  │  - Security headers                              │   │
│  │  - Request size limits                           │   │
│  └─────────────────────┬───────────────────────────┘   │
│                        │                                 │
│                        ▼                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │            FastAPI Container :8000               │   │
│  │  - Non-root user (UID 10001)                    │   │
│  │  - No shell, minimal packages                    │   │
│  │  - JWT authentication                            │   │
│  └─────────────────────┬───────────────────────────┘   │
│                        │                                 │
│                        ▼                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │          PostgreSQL Container :5432              │   │
│  │  - Internal network only                         │   │
│  │  - No exposed ports                              │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Monitoring & Observability

### Current Implementation

- **Health endpoints**: `/health/live` and `/health/ready`
- **Version endpoint**: `/version` with git SHA
- **Structured logging**: JSON format in production
- **Optional CloudWatch alarm**: CPU > 80%

### Recommendations for Production

1. **Centralized logging**: Send logs to CloudWatch Logs or ELK
2. **APM**: Add OpenTelemetry or Datadog for tracing
3. **Metrics**: Prometheus + Grafana for dashboards
4. **Alerting**: PagerDuty or Opsgenie integration

## Evolution Path

As the application grows, here's the recommended evolution:

```
Current                     → Medium Scale              → Large Scale
─────────────────────────────────────────────────────────────────────
Docker Compose on EC2       → ECS Fargate               → EKS
Container PostgreSQL        → RDS PostgreSQL            → Aurora PostgreSQL
nginx in container          → Application Load Balancer → ALB + CloudFront
Manual secrets              → AWS Secrets Manager       → HashiCorp Vault
GitHub Actions              → GitHub Actions            → ArgoCD + GitOps
Single AZ                   → Multi-AZ                  → Multi-Region
```

Each transition should be driven by actual needs, not premature optimization.
