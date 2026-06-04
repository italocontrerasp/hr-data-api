import csv
from io import TextIOWrapper
from typing import IO, Any, Callable

from sqlalchemy.orm import Session

from app.schemas.ingest import BatchResponse, RejectedRow

CHUNK_SIZE = 1000

InsertFn = Callable[[Session, list[dict[str, Any]]], BatchResponse]


def load_csv(
    db: Session,
    stream: IO[bytes],
    columns: list[str],
    insert_fn: InsertFn,
) -> BatchResponse:
    """Stream-parse a headerless CSV and bulk-insert in chunks of CHUNK_SIZE."""
    total_inserted = 0
    all_rejected: list[RejectedRow] = []
    csv_row_offset = 0
    buffer: list[dict[str, Any]] = []

    reader = csv.reader(TextIOWrapper(stream, encoding="utf-8"))

    for raw_row in reader:
        buffer.append(_row_to_dict(raw_row, columns))
        if len(buffer) >= CHUNK_SIZE:
            response = insert_fn(db, buffer)
            total_inserted += response.inserted
            all_rejected.extend(_offset_rejected(response.rejected, csv_row_offset))
            csv_row_offset += len(buffer)
            buffer.clear()

    if buffer:
        response = insert_fn(db, buffer)
        total_inserted += response.inserted
        all_rejected.extend(_offset_rejected(response.rejected, csv_row_offset))

    return BatchResponse(inserted=total_inserted, rejected=all_rejected)


def _row_to_dict(values: list[str], columns: list[str]) -> dict[str, Any]:
    # Empty strings become None so Pydantic reports "field required"
    # instead of confusing type errors.
    return {col: (val if val != "" else None) for col, val in zip(columns, values)}


def _offset_rejected(
    rejected: list[RejectedRow], offset: int
) -> list[RejectedRow]:
    return [
        RejectedRow(
            row_number=r.row_number + offset,
            payload=r.payload,
            reason=r.reason,
        )
        for r in rejected
    ]
