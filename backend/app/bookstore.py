from __future__ import annotations

from typing import Any

PRODUCT_CATALOG: list[dict[str, Any]] = [
    {
        "id": "book-1",
        "title": "The Last Orion",
        "author": "A. Rowan",
        "genre": "Sci-Fi",
        "price": 18.99,
        "rating": 4.7,
        "reviews": 142,
        "in_stock": True,
        "description": "A lone explorer traverses a collapsing galaxy and uncovers a forgotten star map.",
        "is_reviewed": True,
    },
    {
        "id": "book-2",
        "title": "Signal in the Dust",
        "author": "M. Kline",
        "genre": "Sci-Fi",
        "price": 14.5,
        "rating": 4.2,
        "reviews": 28,
        "in_stock": True,
        "description": "A hidden signal from deep space forces a team to revisit the legacies they left behind.",
        "is_reviewed": False,
    },
]

AVAILABLE_ACTIONS = [
    "search",
    "filter_by_genre",
    "filter_by_price",
    "view_product",
    "add_to_cart",
    "change_quantity",
    "remove_from_cart",
    "checkout",
]

# Only these A-side flags correspond to interactions visibly implemented in the current UI.
VERSION_A_FEATURES = {
    "S1": True,
    "S2": False,
    "S3": True,
    "S4": False,
    "S5": False,
    "S6": False,
    "S7": True,
    "S8": True,
    "S9": False,
    "S10": True,
}
VERSION_B_FEATURES = dict.fromkeys(VERSION_A_FEATURES, False)

def check_catalog_parity(
    products_a: list[dict[str, Any]],
    products_b: list[dict[str, Any]],
    actions_a: list[str],
    actions_b: list[str],
) -> dict[str, Any]:
    checks = {
        "product_count": len(products_a) == len(products_b),
        "product_ids": [product.get("id") for product in products_a]
        == [product.get("id") for product in products_b],
        "names": False,
        "prices": False,
        "authors": False,
        "descriptions": False,
        "ratings": False,
        "review_counts": False,
        "genres": False,
        "review_status": False,
        "stock_status": False,
        "available_actions": sorted(actions_a) == sorted(actions_b),
    }
    by_id_a = {product.get("id"): product for product in products_a}
    by_id_b = {product.get("id"): product for product in products_b}
    shared_ids = by_id_a.keys() & by_id_b.keys()
    field_map = {
        "names": "title",
        "prices": "price",
        "authors": "author",
        "descriptions": "description",
        "ratings": "rating",
        "review_counts": "reviews",
        "genres": "genre",
        "review_status": "is_reviewed",
        "stock_status": "in_stock",
    }
    for check_name, product_field in field_map.items():
        checks[check_name] = checks["product_ids"] and all(
            by_id_a[product_id].get(product_field) == by_id_b[product_id].get(product_field)
            for product_id in shared_ids
        )

    issues = [
        f"A/B parity failed for {check_name.replace('_', ' ')}."
        for check_name, passed in checks.items()
        if not passed
    ]
    return {
        "status": "passed" if not issues else "failed",
        "checks": checks,
        "matched_product_count": len(shared_ids),
        "same_actions": checks["available_actions"],
        "same_prices": checks["prices"],
        "same_descriptions": checks["descriptions"],
        "issues": issues,
        "message": "A/B catalogues and actions match." if not issues else " ".join(issues),
    }


def get_bookstore_versions() -> dict[str, Any]:
    products_a = [dict(product) for product in PRODUCT_CATALOG]
    products_b = [dict(product) for product in PRODUCT_CATALOG]
    actions_a = list(AVAILABLE_ACTIONS)
    actions_b = list(AVAILABLE_ACTIONS)
    parity = check_catalog_parity(products_a, products_b, actions_a, actions_b)
    return {
        "version_a": {
            "name": "Version A",
            "products": products_a,
            "feature_flags": dict(VERSION_A_FEATURES),
            "available_actions": actions_a,
        },
        "version_b": {
            "name": "Version B",
            "products": products_b,
            "feature_flags": dict(VERSION_B_FEATURES),
            "available_actions": actions_b,
        },
        "parity_check": parity,
    }
