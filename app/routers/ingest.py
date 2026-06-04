from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ingest import BatchResponse
from app.services import ingest as ingest_service

router = APIRouter(tags=["ingest"])


@router.post("/departments", response_model=BatchResponse)
def insert_departments(
    rows: list[dict[str, Any]] = Body(..., min_length=1, max_length=1000),
    db: Session = Depends(get_db),
) -> BatchResponse:
    return ingest_service.insert_departments(db, rows)


@router.post("/jobs", response_model=BatchResponse)
def insert_jobs(
    rows: list[dict[str, Any]] = Body(..., min_length=1, max_length=1000),
    db: Session = Depends(get_db),
) -> BatchResponse:
    return ingest_service.insert_jobs(db, rows)


@router.post("/hired_employees", response_model=BatchResponse)
def insert_hired_employees(
    rows: list[dict[str, Any]] = Body(..., min_length=1, max_length=1000),
    db: Session = Depends(get_db),
) -> BatchResponse:
    return ingest_service.insert_hired_employees(db, rows)
