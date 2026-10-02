"""Catálogo de productos en memoria.

El catálogo se carga una sola vez al arrancar, desde un JSON empaquetado en la
imagen. No hay base de datos: cada pod responde exactamente lo mismo, así que
la API es stateless y escala horizontalmente sin coordinación.
"""

import json
from pathlib import Path

from pydantic import BaseModel

DATA_FILE = Path(__file__).parent / "data" / "products.json"


class Product(BaseModel):
    id: int
    name: str
    category: str
    price: int
    currency: str
    stock: int


class Catalog:
    def __init__(self) -> None:
        self._products: list[Product] = []
        self._by_id: dict[int, Product] = {}

    def load(self, path: Path = DATA_FILE) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._products = [Product(**item) for item in raw]
        self._by_id = {product.id: product for product in self._products}

    @property
    def ready(self) -> bool:
        return bool(self._products)

    def list(self, category: str | None = None) -> list[Product]:
        if category is None:
            return self._products
        return [product for product in self._products if product.category == category]

    def get(self, product_id: int) -> Product | None:
        return self._by_id.get(product_id)
