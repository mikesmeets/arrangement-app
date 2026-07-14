import base64
import mimetypes
from decimal import Decimal, InvalidOperation

import anthropic
from django.conf import settings
from pydantic import BaseModel

from .invoice_parsing import ParsedInvoice, ParsedLineItem

MODEL = "claude-opus-4-8"

PROMPT = (
    "This is a photo or scan of a flower wholesaler invoice. Extract the vendor's name, "
    "the invoice date (YYYY-MM-DD if you can determine it, otherwise an empty string), "
    "and every line item on the invoice.\n\n"
    "For each line item:\n"
    "- name: the product name/description as printed on the invoice (required)\n"
    "- size: stem length such as '50cm', empty string if not shown\n"
    "- grade: empty string if not shown\n"
    "- total_cost: the TOTAL/EXTENDED price printed for that line (quantity x unit price), "
    "as a plain number — not the per-stem or per-unit price.\n"
    "- quantity: integer count of stems\n\n"
    "If a value truly is not on the invoice, use an empty string (or 0 for numbers) rather than guessing."
)


class _LineItem(BaseModel):
    name: str
    size: str
    grade: str
    total_cost: float
    quantity: int


class _Invoice(BaseModel):
    vendor_name: str
    date: str
    line_items: list[_LineItem]


def _media_type_for(f):
    # A fresh request upload (UploadedFile) exposes content_type, but a saved
    # FieldFile does not — so fall back to guessing from the file name. Browser
    # content_type is also often a generic octet-stream, so prefer the extension.
    content_type = getattr(f, "content_type", None)
    if not content_type or content_type == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(f.name)
        content_type = guessed or content_type
    return content_type or "image/jpeg"


def _content_block(uploaded_file):
    media_type = _media_type_for(uploaded_file)
    uploaded_file.open("rb")
    try:
        raw = uploaded_file.read()
    finally:
        uploaded_file.close()
    data = base64.standard_b64encode(raw).decode("utf-8")
    if media_type == "application/pdf":
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        }
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def parse(uploaded_file) -> ParsedInvoice:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=8192,
            thinking={"type": "adaptive"},
            messages=[
                {
                    "role": "user",
                    "content": [_content_block(uploaded_file), {"type": "text", "text": PROMPT}],
                }
            ],
            output_format=_Invoice,
        )
    except Exception as exc:
        return ParsedInvoice(error=str(exc))

    if response.stop_reason == "refusal":
        return ParsedInvoice(error="Claude declined to process this invoice.")

    parsed = response.parsed_output
    line_items = []
    for item in parsed.line_items:
        try:
            cost = Decimal(str(item.total_cost))
        except InvalidOperation:
            cost = None
        line_items.append(
            ParsedLineItem(
                name=item.name.strip(),
                size=item.size.strip(),
                grade=item.grade.strip(),
                total_cost=cost,
                quantity=item.quantity or 1,
            )
        )
    return ParsedInvoice(
        vendor_name=parsed.vendor_name.strip(),
        date=parsed.date.strip(),
        line_items=line_items,
    )
