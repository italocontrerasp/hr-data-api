from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Department, HiredEmployee, Job
from app.schemas.ingest import (
    BatchResponse,
    DepartmentRow,
    HiredEmployeeRow,
    JobRow,
    RejectedRow,
)


def insert_departments(db: Session, rows: list[dict[str, Any]]) -> BatchResponse:
    valid, rejected = _validate(rows, DepartmentRow)
    models = [Department(id=r.id, department=r.department) for r in valid]
    inserted = _flush(db, models, rows, rejected)
    return BatchResponse(inserted=inserted, rejected=rejected)


def insert_jobs(db: Session, rows: list[dict[str, Any]]) -> BatchResponse:
    valid, rejected = _validate(rows, JobRow)
    models = [Job(id=r.id, job=r.job) for r in valid]
    inserted = _flush(db, models, rows, rejected)
    return BatchResponse(inserted=inserted, rejected=rejected)


def insert_hired_employees(
    db: Session, rows: list[dict[str, Any]]
) -> BatchResponse:
    valid, rejected = _validate(rows, HiredEmployeeRow)
    models = [
        HiredEmployee(
            id=r.id,
            name=r.name,
            hired_at=r.datetime,
            department_id=r.department_id,
            job_id=r.job_id,
        )
        for r in valid
    ]
    inserted = _flush(db, models, rows, rejected)
    return BatchResponse(inserted=inserted, rejected=rejected)


def _validate(
    rows: list[dict[str, Any]],
    schema_cls: type[BaseModel],
) -> tuple[list[BaseModel], list[RejectedRow]]:
    valid: list[BaseModel] = []
    rejected: list[RejectedRow] = []
    for idx, row in enumerate(rows, start=1):
        payload = row if isinstance(row, dict) else {}
        try:
            valid.append(schema_cls(**payload))
        except ValidationError as e:
            reason = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in e.errors()
            )
            rejected.append(
                RejectedRow(row_number=idx, payload=payload, reason=reason)
            )
    return valid, rejected


def _flush(
    db: Session,
    models: list[Base],
    original_rows: list[dict[str, Any]],
    rejected: list[RejectedRow],
) -> int:
    if not models:
        return 0
    try:
        db.add_all(models)
        db.commit()
        return len(models)
    except IntegrityError as e:
        db.rollback()
        already_rejected = {r.row_number for r in rejected}
        for idx, row in enumerate(original_rows, start=1):
            if idx in already_rejected:
                continue
            rejected.append(
                RejectedRow(
                    row_number=idx,
                    payload=row if isinstance(row, dict) else {},
                    reason=f"db integrity error: {str(e.orig).strip()}",
                )
            )
        return 0
