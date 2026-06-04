# hr-data-api

REST API to migrate historical HR data (departments, jobs, hired employees) into a relational database and expose hiring metrics. Built as a solution for the Globant Senior Data Engineer technical challenge.

## Stack

- Python 3.11, FastAPI, Uvicorn
- PostgreSQL 16, SQLAlchemy 2, Alembic
- Pydantic v2 for request/response validation
- Pytest for tests
- Docker (multi-stage build) and docker-compose
- Terraform for Azure infrastructure (Container Apps, PostgreSQL Flexible Server, Container Registry, Blob Storage)
- GitHub Actions for CI/CD

## Project layout

```
app/
  config.py            Settings loaded from environment (.env)
  database.py          SQLAlchemy engine, session, base
  models/              ORM models (departments, jobs, hired_employees)
  schemas/             Pydantic schemas (request/response contracts)
  services/            Business logic (ingest, csv_loader, metrics)
  routers/             FastAPI routers (ingest, load, metrics)
  main.py              App factory
alembic/               Migrations
tests/                 Pytest suite (uses a separate Postgres DB)
data/                  Historical CSVs provided with the challenge
infra/terraform/       Azure infrastructure as code
.github/workflows/     CI (tests) and CD (build, migrate, deploy)
Dockerfile             Multi-stage image for the API
docker-compose.yml     Local Postgres for development
```

## Local development

Hybrid setup: Python runs locally in a venv (fast reload, native debugger), PostgreSQL runs in Docker.

### Prerequisites

- Python 3.11
- Docker Desktop
- Git Bash (on Windows) or any POSIX shell

### Setup

```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows (Git Bash). On Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                 # then edit DATABASE_URL if needed
docker compose up -d                 # starts Postgres on localhost:5432
alembic upgrade head                 # applies schema migrations
uvicorn app.main:app --reload        # API at http://localhost:8000
```

OpenAPI docs are served at `http://localhost:8000/docs`.

### Environment variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL for PostgreSQL | `postgresql+psycopg2://hr_admin:hr_admin@localhost:5432/hr_data` |

## Endpoints

Health check.

```
GET /health
```

### Section 1 — Data ingestion

Batch insert (1 to 1000 rows). Each row is validated independently: invalid rows are rejected with a reason, valid rows are inserted. The response summarizes how many were inserted, how many rejected, and the failing rows.

```
POST /departments
POST /jobs
POST /hired_employees
```

CSV upload (no header expected; columns are positional). Streams the file in chunks of 1000 rows and reuses the same per-row validation. Suitable for the historical CSVs provided with the challenge.

```
POST /load/departments       multipart file: id,department
POST /load/jobs              multipart file: id,job
POST /load/hired_employees   multipart file: id,name,datetime,department_id,job_id
```

### Section 2 — Metrics

Hires per quarter for a given year, grouped by department and job, ordered alphabetically.

```
GET /metrics/hires-by-quarter?year=2021
```

Departments that hired more than the average number of employees in a given year, ordered by hires desc.

```
GET /metrics/departments-above-average?year=2021
```

## Example requests

Batch insert:

```bash
curl -X POST http://localhost:8000/departments \
  -H "Content-Type: application/json" \
  -d '[{"id":1,"department":"Engineering"},{"id":2,"department":"Sales"}]'
```

CSV upload (the historical files provided with the challenge are committed under `data/`):

```bash
curl -X POST http://localhost:8000/load/departments     -F "file=@data/departments.csv"
curl -X POST http://localhost:8000/load/jobs            -F "file=@data/jobs.csv"
curl -X POST http://localhost:8000/load/hired_employees -F "file=@data/hired_employees.csv"
```

Metrics:

```bash
curl "http://localhost:8000/metrics/hires-by-quarter?year=2021"
curl "http://localhost:8000/metrics/departments-above-average?year=2021"
```

## Tests

Tests use a separate database (`hr_data_test`) and run real Alembic migrations against it. Each test truncates the tables before running to keep cases isolated.

```bash
pytest -q
```

The `TEST_DB_URL` is derived from `DATABASE_URL` by swapping the database name. If the test database does not exist, `conftest.py` creates it automatically.

## Docker

Build and run the API image locally against the Postgres started by docker-compose:

```bash
docker build -t hr-data-api .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg2://hr_admin:hr_admin@host.docker.internal:5432/hr_data" \
  hr-data-api
```

The image is multi-stage, runs as a non-root user, and exposes a `HEALTHCHECK` against `/health`. Migrations are not part of `CMD`; they run in CI before each deploy.

## Azure infrastructure

Defined in `infra/terraform/`. One `terraform apply` provisions everything needed to run the API:

- Resource Group
- PostgreSQL Flexible Server (B_Standard_B1ms, public access with firewall rule for Azure services)
- Azure Container Registry (Basic, admin enabled)
- Storage Account + private Blob container for historical CSVs
- Log Analytics Workspace
- Container Apps Environment
- Container App (scale-to-zero, external ingress on port 8000, `DATABASE_URL` injected as secret)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
terraform output                  # api_url, acr_name, container_app_name, etc.
terraform output db_admin_password   # sensitive
```

State is local by default. For production, switch to the `azurerm` backend (a commented stub is in `versions.tf`).

## CI/CD

Two workflows under `.github/workflows/`.

**`ci.yml`** — runs on every pull request and push to `main`. Spins up a Postgres service container and runs the pytest suite.

**`deploy.yml`** — runs on push to `main`:
1. Applies Alembic migrations against the Azure Postgres instance.
2. Authenticates to Azure and Azure Container Registry.
3. Builds the image, tags it with the commit SHA and `latest`, and pushes to ACR.
4. Updates the Container App to the new image (rolling revision).

### Required GitHub secrets

| Secret | Description |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON (`az ad sp create-for-rbac --json-auth`) scoped to the resource group |
| `ACR_NAME` | `terraform output -raw acr_name` |
| `ACR_LOGIN_SERVER` | `terraform output -raw acr_login_server` |
| `AZURE_RESOURCE_GROUP` | `terraform output -raw resource_group_name` |
| `AZURE_CONTAINER_APP` | `terraform output -raw container_app_name` |
| `DATABASE_URL` | Built from `postgres_fqdn` and `db_admin_password` outputs, with `?sslmode=require` |

## Design notes

- **Sync FastAPI**, not async. The workload is short batch inserts and SQL aggregations; async would add cognitive overhead with no I/O concurrency benefit.
- **Per-row validation** at the Pydantic layer keeps a single bad row from failing an entire batch. The service layer wraps the bulk insert in a transaction and rolls back on integrity errors, reporting the conflicting rows.
- **Models vs schemas** are kept separate. SQLAlchemy models describe the database; Pydantic schemas describe the HTTP contract. They evolve independently.
- **Metrics in SQL**, not in Python. `EXTRACT(QUARTER FROM ...)`, `COUNT(*) FILTER (WHERE ...)` and a CTE for the above-average query keep the work in the database, where it belongs.
- **Tests against real Postgres**, not SQLite. The metrics queries use Postgres-specific features that SQLite does not implement.
