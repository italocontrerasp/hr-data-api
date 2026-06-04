from fastapi import FastAPI

from app.routers import ingest, load, metrics

app = FastAPI(title="HR Data API", version="0.1.0")

app.include_router(ingest.router)
app.include_router(load.router)
app.include_router(metrics.router)


@app.get("/health")
def health():
    return {"status": "ok"}
