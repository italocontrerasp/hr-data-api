# hr-data-api

REST API for the Globant Senior Data Engineer challenge. Loads historical HR data (departments, jobs, hired employees) into Postgres and exposes hiring metrics.

## Live

- **API:** https://ca-hr-data-api-dev.kindisland-143838ff.centralus.azurecontainerapps.io
- **Swagger:** [`/docs`](https://ca-hr-data-api-dev.kindisland-143838ff.centralus.azurecontainerapps.io/docs)
- Data loaded: 12 departments, 183 jobs, 1929 employees (70 rows rejected by validation).

```bash
BASE="https://ca-hr-data-api-dev.kindisland-143838ff.centralus.azurecontainerapps.io"
curl "$BASE/metrics/hires-by-quarter?year=2021"
curl "$BASE/metrics/departments-above-average?year=2021"
```

## Architecture

### Application

Layered FastAPI app. Each request flows top-down; the layers don't skip each other.

```
HTTP request
    │
    ▼
┌─────────────┐
│  routers/   │  FastAPI endpoints. Body limits (1-1000), path params.
└─────────────┘
    │
    ▼
┌─────────────┐
│  schemas/   │  Pydantic v2. Per-row validation; bad rows rejected, good rows pass.
└─────────────┘
    │
    ▼
┌─────────────┐
│  services/  │  Business logic: bulk insert, CSV streaming, SQL metrics.
└─────────────┘
    │
    ▼
┌─────────────┐
│  models/    │  SQLAlchemy 2 ORM → Postgres
└─────────────┘
```

### Deployment

```
        push to main
             │
             ▼
   ┌──────────────────┐
   │ GitHub Actions   │  ci.yml: pytest on Postgres service
   │                  │  deploy.yml: alembic → docker build → push → revision
   └──────────────────┘
             │
             ▼
   ┌──────────────────┐         ┌──────────────────────┐
   │ Azure Container  │ ──────► │ Postgres Flexible    │
   │ Registry (ACR)   │  pull   │ Server (B1ms)        │
   └──────────────────┘  image  └──────────────────────┘
             │                            ▲
             ▼                            │ DATABASE_URL (secret)
   ┌──────────────────┐                   │
   │ Container Apps   │ ──────────────────┘
   │ scale-to-zero    │
   │ HTTPS ingress    │
   └──────────────────┘
             │
             ▼
           public URL
```

Provisioned with `infra/terraform/`: RG, Postgres Flex, ACR, Container Apps Environment, Container App, Storage + Blob container (for CSV archival), Log Analytics.

## Quick start (local)

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

`DATABASE_URL` defaults to the docker-compose Postgres; override via `.env`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `POST` | `/departments`, `/jobs`, `/hired_employees` | Batch insert (1-1000 rows, JSON) |
| `POST` | `/load/departments`, `/load/jobs`, `/load/hired_employees` | CSV upload (multipart, streamed in 1000-row chunks) |
| `GET` | `/metrics/hires-by-quarter?year=2021` | Hires per quarter by department/job, ordered alphabetically |
| `GET` | `/metrics/departments-above-average?year=2021` | Departments above the yearly average hires, ordered desc |

Batch endpoints validate row by row: bad rows are reported with `row_number` + `reason`, good rows are committed.

## Tests

```bash
pytest -q
```

13 tests against a real Postgres (`hr_data_test`). TRUNCATE between cases. CI runs the same suite against a Postgres service container.

## Infra

```bash
cd infra/terraform
terraform init
terraform apply
terraform output                    # api_url, acr_name, etc.
terraform output db_admin_password  # sensitive
```

GitHub Actions secrets required: `AZURE_CREDENTIALS`, `ACR_NAME`, `ACR_LOGIN_SERVER`, `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_APP`, `DATABASE_URL`.

## Design decisions

- **Sync FastAPI.** The workload is short batch inserts and SQL aggregations — async adds cognitive overhead with no I/O benefit here.
- **Per-row validation.** One bad row doesn't kill the batch; clients see which rows failed and why.
- **Metrics in SQL.** `COUNT(*) FILTER (...)`, `EXTRACT(QUARTER FROM ...)`, and a CTE keep work in the database, where it belongs.
- **Schemas ≠ models.** Pydantic describes the HTTP contract; SQLAlchemy describes the table. They evolve independently.
- **Postgres for tests, not SQLite.** The metric queries use Postgres-only features — SQLite tests would lie.
- **Alembic for schema.** Versioned, replayable, applied by CI before each deploy. No `create_all()` shortcuts.
- **Multi-stage Dockerfile, non-root user, HEALTHCHECK.** Migrations run in CI, not at container startup.
