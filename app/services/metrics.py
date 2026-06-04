from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.metrics import DepartmentHires, QuarterlyHires

HIRES_BY_QUARTER_SQL = text(
    """
    SELECT
        d.department,
        j.job,
        COUNT(*) FILTER (WHERE EXTRACT(QUARTER FROM he.datetime) = 1) AS q1,
        COUNT(*) FILTER (WHERE EXTRACT(QUARTER FROM he.datetime) = 2) AS q2,
        COUNT(*) FILTER (WHERE EXTRACT(QUARTER FROM he.datetime) = 3) AS q3,
        COUNT(*) FILTER (WHERE EXTRACT(QUARTER FROM he.datetime) = 4) AS q4
    FROM hired_employees he
    JOIN departments d ON d.id = he.department_id
    JOIN jobs j ON j.id = he.job_id
    WHERE EXTRACT(YEAR FROM he.datetime) = :year
    GROUP BY d.department, j.job
    ORDER BY d.department, j.job
    """
)

DEPARTMENTS_ABOVE_AVG_SQL = text(
    """
    WITH hires AS (
        SELECT d.id, d.department, COUNT(*) AS hired
        FROM hired_employees he
        JOIN departments d ON d.id = he.department_id
        WHERE EXTRACT(YEAR FROM he.datetime) = :year
        GROUP BY d.id, d.department
    )
    SELECT id, department, hired
    FROM hires
    WHERE hired > (SELECT AVG(hired) FROM hires)
    ORDER BY hired DESC
    """
)


def hires_by_quarter(db: Session, year: int) -> list[QuarterlyHires]:
    result = db.execute(HIRES_BY_QUARTER_SQL, {"year": year})
    return [QuarterlyHires(**dict(row._mapping)) for row in result]


def departments_above_average(db: Session, year: int) -> list[DepartmentHires]:
    result = db.execute(DEPARTMENTS_ABOVE_AVG_SQL, {"year": year})
    return [DepartmentHires(**dict(row._mapping)) for row in result]
