from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ingest import BatchResponse
from app.services import csv_loader
from app.services import ingest as ingest_service

router = APIRouter(prefix="/load", tags=["load"])

DEPARTMENT_COLUMNS = ["id", "department"]
JOB_COLUMNS = ["id", "job"]
HIRED_EMPLOYEE_COLUMNS = ["id", "name", "datetime", "department_id", "job_id"]


@router.post("/departments", response_model=BatchResponse)
def load_departments(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BatchResponse:
    return csv_loader.load_csv(
        db, file.file, DEPARTMENT_COLUMNS, ingest_service.insert_departments
    )


@router.post("/jobs", response_model=BatchResponse)
def load_jobs(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BatchResponse:
    return csv_loader.load_csv(
        db, file.file, JOB_COLUMNS, ingest_service.insert_jobs
    )


@router.post("/hired_employees", response_model=BatchResponse)
def load_hired_employees(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BatchResponse:
    return csv_loader.load_csv(
        db,
        file.file,
        HIRED_EMPLOYEE_COLUMNS,
        ingest_service.insert_hired_employees,
    )
