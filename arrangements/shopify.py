"""Push an arrangement to Shopify as a product.

Ported from the Airtable automation, with two changes: credentials come from
the environment (never hard-coded), and a re-push updates the existing product
rather than creating a duplicate — the arrangement remembers its Shopify id.
"""

import base64
import io
from urllib.parse import quote

import httpx
from django.conf import settings
from PIL import Image, ImageOps

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


def _photo_as_jpeg_attachment(arrangement):
    """Re-encode the photo as a plain JPEG and base64-encode it. iPhone HDR
    shots arrive as MPO (multi-frame JPEG), which Shopify rejects; Pillow reads
    the primary frame, and sending the bytes ourselves also means Shopify
    needn't fetch a URL. exif_transpose keeps the orientation upright."""
    arrangement.photo.open("rb")
    try:
        image = Image.open(arrangement.photo)
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
    finally:
        arrangement.photo.close()
    return base64.standard_b64encode(buffer.getvalue()).decode("ascii")


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

    warnings = []
    with httpx.Client(timeout=30) as client:
        # Creating/updating the product is the critical step; if it fails there's
        # nothing to record. Everything after is best-effort — a failure there is
        # a warning, not a reason to abandon (and orphan) the product.
        if is_update:
            existing = _rest(
                client, base, headers, "GET",
                f"/products/{arrangement.shopify_product_id}.json",
            )
            existing_product = existing["product"]
            payload["product"]["id"] = existing_product["id"]
            variants = existing_product.get("variants") or []
            if variants:
                payload["product"]["variants"][0]["id"] = variants[0]["id"]
            result = _rest(
                client, base, headers, "PUT",
                f"/products/{arrangement.shopify_product_id}.json", payload,
            )
            has_image = bool(existing_product.get("images"))
        else:
            result = _rest(client, base, headers, "POST", "/products.json", payload)
            has_image = False

        product_id = result["product"]["id"]

        # Standard category — Fresh Flowers.
        try:
            _graphql(
                client, store, headers, _CATEGORY_MUTATION,
                {"input": {
                    "id": f"gid://shopify/Product/{product_id}",
                    "category": FRESH_FLOWERS_CATEGORY_GID,
                }},
            )
        except ShopifyError as exc:
            warnings.append(f"Category not set: {exc}")

        # Photo — only when the product has none, so re-pushing never stacks
        # duplicate images. Re-encoded to JPEG, so iPhone MPO shots are accepted.
        if arrangement.photo and not has_image:
            try:
                _rest(
                    client, base, headers, "POST",
                    f"/products/{product_id}/images.json",
                    {"image": {
                        "attachment": _photo_as_jpeg_attachment(arrangement),
                        "filename": "arrangement.jpg",
                        "alt": arrangement.name or "",
                    }},
                )
            except Exception as exc:
                warnings.append(f"Photo not uploaded: {exc}")

        if arrangement.shopify_collection:
            try:
                _ensure_in_collection(client, base, headers, product_id, arrangement.shopify_collection)
            except ShopifyError as exc:
                warnings.append(f"Collection not set: {exc}")

    return {
        "product_id": str(product_id),
        "admin_url": f"https://{store}.myshopify.com/admin/products/{product_id}",
        "created": not is_update,
        "warnings": warnings,
    }
