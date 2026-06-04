from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.metrics import DepartmentHires, QuarterlyHires
from app.services import metrics as metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/hires-by-quarter", response_model=list[QuarterlyHires])
def hires_by_quarter(
    year: int = Query(2021, ge=1900, le=2100),
    db: Session = Depends(get_db),
) -> list[QuarterlyHires]:
    return metrics_service.hires_by_quarter(db, year)


@router.get("/departments-above-average", response_model=list[DepartmentHires])
def departments_above_average(
    year: int = Query(2021, ge=1900, le=2100),
    db: Session = Depends(get_db),
) -> list[DepartmentHires]:
    return metrics_service.departments_above_average(db, year)
