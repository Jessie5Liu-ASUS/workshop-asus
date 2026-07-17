import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.lab2


def test_sales_report_returns_matching_category(client: TestClient) -> None:
    response = client.get("/reports/sales", params={"category": "Laptop"})

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "Laptop"
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Zenbook 14 OLED"
    assert body["total"] == 42900


def test_sales_report_empty_category_returns_zero_total(client: TestClient) -> None:
    response = client.get("/reports/sales", params={"category": "Nonexistent"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


# --- SQL injection regression ---
def test_sql_injection_in_category_does_not_leak_all_rows(client: TestClient) -> None:
    """A classic UNION-based injection must not return extra rows."""
    payload = "Laptop' OR '1'='1"
    response = client.get("/reports/sales", params={"category": payload})

    assert response.status_code == 200
    # The injected value finds no exact-match category so items must be empty
    assert response.json()["items"] == []


def test_sql_injection_with_comment_does_not_leak_rows(client: TestClient) -> None:
    """Comment-based injection must not return extra rows."""
    payload = "Laptop'--"
    response = client.get("/reports/sales", params={"category": payload})

    assert response.status_code == 200
    assert response.json()["items"] == []


# --- eval / code injection regression ---
def test_formula_parameter_is_no_longer_accepted(client: TestClient) -> None:
    """The insecure `formula` query parameter must be ignored or rejected."""
    response = client.get(
        "/reports/sales",
        params={"category": "Laptop", "formula": "__import__('os').getenv('SECRET','pwned')"},
    )

    # The endpoint either ignores the extra param (200) or rejects it (422).
    # Either way the evaluated string must NOT appear in the response body.
    assert "pwned" not in response.text
    assert "__import__" not in response.text


# --- Stack-trace disclosure regression ---
def test_error_response_does_not_expose_traceback(client: TestClient) -> None:
    """Empty category must return 422; even a 500 must not expose a stack trace."""
    response = client.get("/reports/sales", params={"category": ""})

    # FastAPI validation rejects empty string (min_length=1)
    assert response.status_code == 422
    assert "Traceback" not in response.text
    assert "traceback" not in response.text


# --- Input validation ---
def test_missing_category_returns_422(client: TestClient) -> None:
    response = client.get("/reports/sales")

    assert response.status_code == 422
