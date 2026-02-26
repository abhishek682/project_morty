# Rick and Morty API Integration

Production-grade REST API that ingests the Rick and Morty API, filters for alive human characters from any Earth variant, caches results, and persists data to PostgreSQL. Designed for high availability and operational excellence in Kubernetes.

## Architecture

```mermaid
flowchart LR
    client[API Consumers] --> ingress[Ingress TLS]
    ingress --> svc[ClusterIP Service]
    svc --> app[FastAPI Deployment]
    app --> redis[(Redis Cache)]
    app --> pg[(PostgreSQL)]
    app --> rick[Upstream Rick & Morty API]
    app --> metrics[/metrics]
    app --> health[/healthcheck]
    app --> tracing[OTel Collector/Jaeger]
    app --> logs[Fluent Bit Sidecar]
```

## Features

- Upstream pagination + retry handling with exponential backoff
- Redis caching with configurable TTL and sync interval
- PostgreSQL persistence with idempotent upserts
- Rate limiting for API consumers
- Deep health checks (DB and cache)
- Prometheus metrics + OpenTelemetry tracing
- Kubernetes deployment with HPA, TLS Ingress, RBAC, and Fluent Bit sidecar

## API Endpoints

- `GET /characters?page=1&limit=10&sort=id` (sort by `id` or `name`)
- `GET /healthcheck`
- `GET /metrics`

OpenAPI spec: `configs/openapi.yaml`

## Local Setup

1. Start dependencies:

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name postgres -e POSTGRES_DB=rickmorty -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -p 5432:5432 postgres:15-alpine
```

2. Install and run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
export RM_DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/rickmorty
export RM_REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload
```

## Docker

```bash
docker build -t rick-morty-api:local .
docker run -p 8000:8000 \
  -e RM_DATABASE_URL=postgresql+psycopg2://app:app@host.docker.internal:5432/rickmorty \
  -e RM_REDIS_URL=redis://host.docker.internal:6379/0 \
  rick-morty-api:local
```

## Kubernetes (Raw Manifests)

```bash
kubectl apply -f k8s/dependencies.yaml
kubectl apply -f k8s/app-configmap.yaml
kubectl apply -f k8s/app-secret.yaml
kubectl apply -f k8s/fluent-bit-config.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml
```

Create TLS secret (self-signed):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt -subj "/CN=rick-morty.local"
kubectl create secret tls rick-morty-tls --cert=tls.crt --key=tls.key
```

## Helm Deployment

```bash
helm upgrade --install rick-morty ./helm/rick-morty-api \
  --set image.repository=your-dockerhub-username/rick-morty-api \
  --set image.tag=latest \
  --set secrets.databaseUrl=postgresql+psycopg2://app:app@postgres:5432/rickmorty \
  --set secrets.redisUrl=redis://redis:6379/0
```

For external secrets, set `secrets.existingSecret` and disable `secrets.create`.

## Observability

- Prometheus metrics: `GET /metrics`
- Grafana dashboard: `configs/grafana-dashboard.json`
- OpenTelemetry: set `RM_OTEL_EXPORTER_OTLP_ENDPOINT` to your collector
- Rate limiting storage can be overridden with `RM_RATE_LIMIT_STORAGE_URI`

### Alerts (PrometheusRule)

- High error rate: protects against upstream or app failures
- High latency: catches overload or degraded dependencies
- Crash looping: detects pod instability

Templates: `helm/rick-morty-api/templates/alerts.yaml`

## CI/CD

Workflow: `.github/workflows/ci.yml`

- Builds and tests image
- Runs lint + Bandit
- Creates kind cluster and deploys Helm chart
- Runs integration tests
- Pushes to Docker Hub on `main` (requires `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`)

Add a badge (after first run):

```md
![ci](https://github.com/<org>/<repo>/actions/workflows/ci.yml/badge.svg)
```

## Testing

```bash
pytest tests/test_character_service.py
BASE_URL=http://localhost:8000 pytest tests/test_api.py
```

## Notes

- Access granting to `abregman@akamai.com` must be performed by repo owners.
- Evidence of a successful GitHub Actions run can be added via the CI badge or attaching workflow logs after the first run.
