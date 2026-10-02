import pytest
from fastapi.testclient import TestClient

from app.main import app, catalog


@pytest.fixture(scope="module")
def client():
    # El bloque "with" ejecuta el arranque de la app, que carga el catálogo.
    with TestClient(app) as test_client:
        yield test_client


def test_list_products(client):
    response = client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 12
    assert {"id", "name", "category", "price", "currency", "stock"} <= products[0].keys()


def test_list_products_filters_by_category(client):
    response = client.get("/products", params={"category": "deportes"})
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 3
    assert all(product["category"] == "deportes" for product in products)


def test_list_products_unknown_category_is_empty(client):
    response = client.get("/products", params={"category": "no-existe"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_products_pagination(client):
    response = client.get("/products", params={"limit": 5, "offset": 10})
    assert response.status_code == 200
    assert [product["id"] for product in response.json()] == [11, 12]


def test_list_products_rejects_invalid_limit(client):
    assert client.get("/products", params={"limit": 0}).status_code == 422
    assert client.get("/products", params={"limit": 1000}).status_code == 422


def test_get_product(client):
    response = client.get("/products/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Audífonos inalámbricos"


def test_get_product_not_found(client):
    response = client.get("/products/999")
    assert response.status_code == 404


def test_get_product_rejects_non_numeric_id(client):
    assert client.get("/products/abc").status_code == 422


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz(client):
    response = client.get("/readyz")
    assert response.status_code == 200


def test_readyz_fails_when_catalog_is_empty(client, monkeypatch):
    monkeypatch.setattr(catalog, "_products", [])
    assert client.get("/readyz").status_code == 503


def test_metrics_counts_requests_by_route_template(client):
    client.get("/products/1")
    client.get("/products/2")
    body = client.get("/metrics").text
    assert 'path="/products/{product_id}"' in body
    assert 'path="/products/1"' not in body
    assert 'path="/healthz"' not in body
