import pytest


@pytest.fixture
def seeded(client):
    """Seed deterministic data:
    - 2 departments: Engineering(1), Sales(2)
    - 2 jobs: VP(1), Analyst(2)
    - Engineering: 3 hires in Q1, 1 in Q3  -> 4 total
    - Sales:       1 hire in Q1            -> 1 total
    avg = (4 + 1) / 2 = 2.5
    Only Engineering is above the average.
    """
    client.post(
        "/departments",
        json=[{"id": 1, "department": "Engineering"}, {"id": 2, "department": "Sales"}],
    )
    client.post(
        "/jobs",
        json=[{"id": 1, "job": "VP"}, {"id": 2, "job": "Analyst"}],
    )
    client.post(
        "/hired_employees",
        json=[
            {"id": 1, "name": "a", "datetime": "2021-01-15T00:00:00Z", "department_id": 1, "job_id": 1},
            {"id": 2, "name": "b", "datetime": "2021-02-15T00:00:00Z", "department_id": 1, "job_id": 1},
            {"id": 3, "name": "c", "datetime": "2021-03-15T00:00:00Z", "department_id": 1, "job_id": 2},
            {"id": 4, "name": "d", "datetime": "2021-08-15T00:00:00Z", "department_id": 1, "job_id": 2},
            {"id": 5, "name": "e", "datetime": "2021-01-20T00:00:00Z", "department_id": 2, "job_id": 1},
        ],
    )


def test_hires_by_quarter_returns_expected_breakdown(client, seeded):
    response = client.get("/metrics/hires-by-quarter")
    assert response.status_code == 200
    data = response.json()

    by_key = {(r["department"], r["job"]): r for r in data}

    eng_vp = by_key[("Engineering", "VP")]
    assert (eng_vp["q1"], eng_vp["q2"], eng_vp["q3"], eng_vp["q4"]) == (2, 0, 0, 0)

    eng_analyst = by_key[("Engineering", "Analyst")]
    assert (eng_analyst["q1"], eng_analyst["q2"], eng_analyst["q3"], eng_analyst["q4"]) == (1, 0, 1, 0)

    sales_vp = by_key[("Sales", "VP")]
    assert (sales_vp["q1"], sales_vp["q2"], sales_vp["q3"], sales_vp["q4"]) == (1, 0, 0, 0)


def test_hires_by_quarter_is_alphabetically_ordered(client, seeded):
    data = client.get("/metrics/hires-by-quarter").json()
    keys = [(r["department"], r["job"]) for r in data]
    assert keys == sorted(keys)


def test_departments_above_average_returns_only_engineering(client, seeded):
    response = client.get("/metrics/departments-above-average")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["department"] == "Engineering"
    assert data[0]["hired"] == 4


def test_metrics_empty_for_year_without_data(client, seeded):
    assert client.get("/metrics/hires-by-quarter?year=2030").json() == []
    assert client.get("/metrics/departments-above-average?year=2030").json() == []


def test_year_out_of_range_returns_422(client):
    assert client.get("/metrics/hires-by-quarter?year=1500").status_code == 422
    assert client.get("/metrics/hires-by-quarter?year=3000").status_code == 422
