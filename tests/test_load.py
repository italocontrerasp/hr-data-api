import io


def test_load_departments_csv(client):
    csv_bytes = b"1,Engineering\n2,Sales\n3,Research and Development\n"
    response = client.post(
        "/load/departments",
        files={"file": ("departments.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inserted"] == 3
    assert body["rejected_count"] == 0


def test_load_hired_employees_rejects_rows_with_empty_fk(client):
    client.post(
        "/load/departments",
        files={"file": ("d.csv", io.BytesIO(b"1,Engineering\n"), "text/csv")},
    )
    client.post(
        "/load/jobs",
        files={"file": ("j.csv", io.BytesIO(b"1,VP Sales\n"), "text/csv")},
    )

    # 2nd row: empty job_id (matches what we see in the real CSV).
    csv_bytes = (
        b"1,John,2021-11-07T02:48:42Z,1,1\n"
        b"2,Jane,2021-05-30T05:43:46Z,1,\n"
    )
    response = client.post(
        "/load/hired_employees",
        files={"file": ("he.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    body = response.json()
    assert body["inserted"] == 1
    assert body["rejected_count"] == 1
    assert body["rejected"][0]["row_number"] == 2
    assert "job_id" in body["rejected"][0]["reason"]
