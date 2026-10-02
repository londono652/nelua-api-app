"""nelua-api: API de catálogo de productos (solo lectura)."""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.catalog import Catalog, Product

APP_VERSION = os.getenv("APP_VERSION", "dev")

catalog = Catalog()

REQUESTS = Counter(
    "http_requests_total",
    "Total de peticiones HTTP",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Duración de las peticiones HTTP en segundos",
    ["method", "path"],
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)

# Rutas que no se miden: las llaman Kubernetes y Prometheus, no los clientes.
UNMEASURED_PATHS = {"/healthz", "/readyz", "/metrics"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    catalog.load()
    yield


app = FastAPI(title="nelua-api", version=APP_VERSION, lifespan=lifespan)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)

    # Se usa la plantilla de la ruta (/products/{product_id}) y no la URL real,
    # para que cada id no genere una serie nueva en Prometheus.
    route = request.scope.get("route")
    path = route.path if route else "unmatched"
    if path not in UNMEASURED_PATHS:
        REQUESTS.labels(request.method, path, response.status_code).inc()
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    return response


@app.get("/products", response_model=list[Product], tags=["products"])
def list_products(
    category: str | None = Query(default=None, description="Filtra por categoría"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lista los productos del catálogo, con filtro y paginación opcionales."""
    return catalog.list(category)[offset : offset + limit]


@app.get("/products/{product_id}", response_model=Product, tags=["products"])
def get_product(product_id: int):
    """Devuelve un producto por su id."""
    product = catalog.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@app.get("/healthz", tags=["ops"])
def healthz():
    """Liveness: el proceso está vivo. Si falla, Kubernetes reinicia el pod."""
    return {"status": "ok", "version": APP_VERSION}


@app.get("/readyz", tags=["ops"])
def readyz():
    """Readiness: el pod puede recibir tráfico. Si falla, sale del balanceo."""
    if not catalog.ready:
        raise HTTPException(status_code=503, detail="Catálogo no cargado")
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Métricas en formato Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
