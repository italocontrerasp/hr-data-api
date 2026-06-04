# hr-data-api

API REST para el reto técnico de Senior Data Engineer de Globant. Carga datos históricos de RR.HH. (departamentos, puestos, empleados contratados) en Postgres y expone métricas de contratación.

## Live

- **API:** https://ca-hr-data-api-dev.kindisland-143838ff.centralus.azurecontainerapps.io
- **Swagger:** [`/docs`](https://ca-hr-data-api-dev.kindisland-143838ff.centralus.azurecontainerapps.io/docs)
- Datos cargados: 12 departamentos, 183 puestos, 1929 empleados (70 filas rechazadas por validación).

```bash
BASE="https://ca-hr-data-api-dev.kindisland-143838ff.centralus.azurecontainerapps.io"
curl "$BASE/metrics/hires-by-quarter?year=2021"
curl "$BASE/metrics/departments-above-average?year=2021"
```

## Arquitectura

### Aplicación

App FastAPI por capas. Cada request fluye de arriba abajo; las capas no se saltan.

```
HTTP request
    │
    ▼
┌─────────────┐
│  routers/   │  Endpoints FastAPI. Límites del body (1-1000), path params.
└─────────────┘
    │
    ▼
┌─────────────┐
│  schemas/   │  Pydantic v2. Validación por fila; las malas se rechazan, las buenas pasan.
└─────────────┘
    │
    ▼
┌─────────────┐
│  services/  │  Lógica de negocio: bulk insert, streaming de CSV, métricas en SQL.
└─────────────┘
    │
    ▼
┌─────────────┐
│  models/    │  ORM SQLAlchemy 2 → Postgres
└─────────────┘
```

### Despliegue

```
        push a main
             │
             ▼
   ┌──────────────────┐
   │ GitHub Actions   │  ci.yml: pytest sobre Postgres service
   │                  │  deploy.yml: alembic → docker build → push → nueva revisión
   └──────────────────┘
             │
             ▼
   ┌──────────────────┐         ┌──────────────────────┐
   │ Azure Container  │ ──────► │ Postgres Flexible    │
   │ Registry (ACR)   │  pull   │ Server (B1ms)        │
   └──────────────────┘  imagen └──────────────────────┘
             │                            ▲
             ▼                            │ DATABASE_URL (secret)
   ┌──────────────────┐                   │
   │ Container Apps   │ ──────────────────┘
   │ scale-to-zero    │
   │ ingress HTTPS    │
   └──────────────────┘
             │
             ▼
          URL pública
```

Provisionado con `infra/terraform/`: Resource Group, Postgres Flex, ACR, Container Apps Environment, Container App, Storage + Blob container (archival de CSVs), Log Analytics.

## Quick start (local)

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"
docker compose up -d
alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

`DATABASE_URL` apunta por defecto al Postgres del docker-compose; se sobreescribe con `.env`.

## Endpoints

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `POST` | `/departments`, `/jobs`, `/hired_employees` | Inserción por lote (1-1000 filas, JSON) |
| `POST` | `/load/departments`, `/load/jobs`, `/load/hired_employees` | Subida de CSV (multipart, streamed en chunks de 1000 filas) |
| `GET` | `/metrics/hires-by-quarter?year=2021` | Contrataciones por trimestre, por departamento/puesto, ordenadas alfabéticamente |
| `GET` | `/metrics/departments-above-average?year=2021` | Departamentos por encima del promedio anual de contrataciones, ordenados desc |

Los endpoints de lote validan fila por fila: las filas inválidas se reportan con `row_number` + `reason`, las válidas se persisten.

## Tests

```bash
pytest -q
```

13 tests contra un Postgres real (`hr_data_test`). TRUNCATE entre casos. El CI corre el mismo suite contra un Postgres en service container.

## Infra

```bash
cd infra/terraform
terraform init
terraform apply
terraform output                    # api_url, acr_name, etc.
terraform output db_admin_password  # sensitive
```

Secrets requeridos en GitHub Actions: `AZURE_CREDENTIALS`, `ACR_NAME`, `ACR_LOGIN_SERVER`, `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_APP`, `DATABASE_URL`.

## Decisiones de diseño

- **FastAPI síncrono.** El workload son inserts cortos y agregaciones SQL — async sumaría complejidad sin beneficio de I/O acá.
- **Validación por fila.** Una fila mala no tumba el batch; el cliente ve qué filas fallaron y por qué.
- **Métricas en SQL.** `COUNT(*) FILTER (...)`, `EXTRACT(QUARTER FROM ...)` y un CTE mantienen el trabajo en la base de datos, donde corresponde.
- **Schemas ≠ modelos.** Pydantic describe el contrato HTTP; SQLAlchemy describe la tabla. Evolucionan independientemente.
- **Postgres para tests, no SQLite.** Las queries de métricas usan features exclusivas de Postgres — testear en SQLite mentiría.
- **Alembic para el schema.** Versionado, reproducible, aplicado por el CI antes de cada deploy. Sin atajos con `create_all()`.
- **Dockerfile multi-stage, usuario non-root, HEALTHCHECK.** Las migraciones corren en CI, no al arrancar el contenedor.
