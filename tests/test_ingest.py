def test_insert_departments_happy_path(client):
    response = client.post(
        "/departments",
        json=[
            {"id": 1, "department": "Engineering"},
            {"id": 2, "department": "Sales"},
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inserted"] == 2
    assert body["rejected_count"] == 0
    assert body["total"] == 2


def test_insert_hired_employees_rejects_missing_job_id(client):
    client.post("/departments", json=[{"id": 1, "department": "Engineering"}])
    client.post("/jobs", json=[{"id": 1, "job": "VP Sales"}])

    response = client.post(
        "/hired_employees",
        json=[
            {
                "id": 1,
                "name": "John",
                "datetime": "2021-11-07T02:48:42Z",
                "department_id": 1,
                "job_id": 1,
            },
            {
                "id": 2,
                "name": "Jane",
                "datetime": "2021-05-30T05:43:46Z",
                "department_id": 1,
            },
        ],
    )
    body = response.json()
    assert body["inserted"] == 1
    assert body["rejected_count"] == 1
    assert body["rejected"][0]["row_number"] == 2
    assert "job_id" in body["rejected"][0]["reason"]


def test_empty_batch_returns_422(client):
    response = client.post("/departments", json=[])
    assert response.status_code == 422


def test_batch_over_1000_returns_422(client):
    payload = [{"id": i, "department": f"Dept {i}"} for i in range(1001)]
    response = client.post("/departments", json=payload)
    assert response.status_code == 422


def test_duplicate_id_is_rejected_with_integrity_error(client):
    client.post("/departments", json=[{"id": 1, "department": "Engineering"}])
    response = client.post(
        "/departments", json=[{"id": 1, "department": "Sales"}]
    )
    body = response.json()
    assert body["inserted"] == 0
    assert body["rejected_count"] == 1
    assert "integrity" in body["rejected"][0]["reason"].lower()


def test_invalid_fk_is_rejected(client):
    client.post("/departments", json=[{"id": 1, "department": "Engineering"}])
    client.post("/jobs", json=[{"id": 1, "job": "VP Sales"}])
    response = client.post(
        "/hired_employees",
        json=[
            {
                "id": 1,
                "name": "X",
                "datetime": "2021-01-01T00:00:00Z",
                "department_id": 999,
                "job_id": 1,
            }
        ],
    )
    body = response.json()
    assert body["inserted"] == 0
    assert body["rejected_count"] == 1
