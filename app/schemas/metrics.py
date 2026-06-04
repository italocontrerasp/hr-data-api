from pydantic import BaseModel


class QuarterlyHires(BaseModel):
    department: str
    job: str
    q1: int
    q2: int
    q3: int
    q4: int


class DepartmentHires(BaseModel):
    id: int
    department: str
    hired: int
