from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field


class DepartmentRow(BaseModel):
    id: int
    department: str = Field(min_length=1)


class JobRow(BaseModel):
    id: int
    job: str = Field(min_length=1)


class HiredEmployeeRow(BaseModel):
    id: int
    name: str = Field(min_length=1)
    datetime: datetime
    department_id: int
    job_id: int


class RejectedRow(BaseModel):
    row_number: int
    payload: dict[str, Any]
    reason: str


class BatchResponse(BaseModel):
    inserted: int
    rejected: list[RejectedRow]

    @computed_field
    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    @computed_field
    @property
    def total(self) -> int:
        return self.inserted + len(self.rejected)
