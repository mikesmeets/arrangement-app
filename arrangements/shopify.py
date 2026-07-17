"""Push an arrangement to Shopify as a product.

Ported from the Airtable automation, with two changes: credentials come from
the environment (never hard-coded), and a re-push updates the existing product
rather than creating a duplicate — the arrangement remembers its Shopify id.
"""

from urllib.parse import quote

import httpx
from django.conf import settings

# Shopify standard taxonomy GID for Fresh Flowers.
FRESH_FLOWERS_CATEGORY_GID = "gid://shopify/TaxonomyCategory/ae-3-1-3"

_CATEGORY_MUTATION = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id category { name } }
    userErrors { field message }
  }
}
"""


class ShopifyNotConfigured(Exception):
    """SHOPIFY_STORE / SHOPIFY_ACCESS_TOKEN aren't set."""


class ShopifyError(Exception):
    """Shopify returned an error."""


def _config():
    store = settings.SHOPIFY_STORE
    token = settings.SHOPIFY_ACCESS_TOKEN
    if not store or not token:
        raise ShopifyNotConfigured(
            "Set SHOPIFY_STORE and SHOPIFY_ACCESS_TOKEN before pushing to Shopify."
        )
    base = f"https://{store}.myshopify.com/admin/api/{settings.SHOPIFY_API_VERSION}"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    return store, base, headers


def _rest(client, base, headers, method, endpoint, json=None):
    resp = client.request(method, f"{base}{endpoint}", headers=headers, json=json)
    if resp.status_code >= 400:
        raise ShopifyError(f"{method} {endpoint} -> {resp.status_code}: {resp.text}")
    return resp.json()


def _graphql(client, store, headers, query, variables):
    url = f"https://{store}.myshopify.com/admin/api/{settings.SHOPIFY_API_VERSION}/graphql.json"
    resp = client.post(url, headers=headers, json={"query": query, "variables": variables})
    data = resp.json()
    if resp.status_code >= 400 or data.get("errors"):
        raise ShopifyError(f"GraphQL error: {data.get('errors')}")
    return data["data"]


def _ensure_in_collection(client, base, headers, product_id, name):
    found = _rest(
        client, base, headers, "GET",
        f"/custom_collections.json?title={quote(name)}&limit=1",
    )
    collections = found.get("custom_collections", [])
    if collections:
        collection_id = collections[0]["id"]
    else:
        created = _rest(
            client, base, headers, "POST", "/custom_collections.json",
            {"custom_collection": {"title": name}},
        )
        collection_id = created["custom_collection"]["id"]

    # Only add the product if it isn't already in the collection.
    membership = _rest(
        client, base, headers, "GET",
        f"/collects.json?product_id={product_id}&collection_id={collection_id}&limit=1",
    )
    if not membership.get("collects"):
        _rest(
            client, base, headers, "POST", "/collects.json",
            {"collect": {"product_id": product_id, "collection_id": collection_id}},
        )


def push_arrangement(arrangement):
    """Create or update the arrangement's Shopify product. Returns
    {"product_id": str, "admin_url": str, "created": bool}."""
    store, base, headers = _config()
    is_update = bool(arrangement.shopify_product_id)

    payload = {
        "product": {
            "title": arrangement.name or "Untitled",
            "body_html": arrangement.description or "",
            "product_type": arrangement.get_type_display(),
            "variants": [
                {
                    "sku": arrangement.sku or "",
                    "price": f"{arrangement.actual_price:.2f}",
                }
            ],
        }
    }

    with httpx.Client(timeout=30) as client:
        if is_update:
            existing = _rest(
                client, base, headers, "GET",
                f"/products/{arrangement.shopify_product_id}.json",
            )
            payload["product"]["id"] = existing["product"]["id"]
            variants = existing["product"].get("variants") or []
            if variants:
                payload["product"]["variants"][0]["id"] = variants[0]["id"]
            result = _rest(
                client, base, headers, "PUT",
                f"/products/{arrangement.shopify_product_id}.json", payload,
            )
        else:
            result = _rest(client, base, headers, "POST", "/products.json", payload)

        product_id = result["product"]["id"]

        # Standard category — Fresh Flowers.
        _graphql(
            client, store, headers, _CATEGORY_MUTATION,
            {"input": {
                "id": f"gid://shopify/Product/{product_id}",
                "category": FRESH_FLOWERS_CATEGORY_GID,
            }},
        )

        # Photo — first push only, so re-pushing doesn't stack duplicate images.
        # Shopify fetches the URL itself, so it must be publicly reachable (a
        # signed S3 URL works; a localhost dev URL does not).
        if not is_update and arrangement.photo:
            _rest(
                client, base, headers, "POST", f"/products/{product_id}/images.json",
                {"image": {"src": arrangement.photo.url, "alt": arrangement.name or ""}},
            )

        if arrangement.shopify_collection:
            _ensure_in_collection(client, base, headers, product_id, arrangement.shopify_collection)

    return {
        "product_id": str(product_id),
        "admin_url": f"https://{store}.myshopify.com/admin/products/{product_id}",
        "created": not is_update,
    }
