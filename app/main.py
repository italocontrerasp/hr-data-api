from fastapi import FastAPI

from app.routers import ingest, load

app = FastAPI(title="HR Data API", version="0.1.0")

app.include_router(ingest.router)
app.include_router(load.router)


@app.get("/health")
def health():
    return {"status": "ok"}
