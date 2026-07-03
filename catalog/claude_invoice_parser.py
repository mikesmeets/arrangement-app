import base64
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


def _content_block(uploaded_file):
    uploaded_file.seek(0)
    data = base64.standard_b64encode(uploaded_file.read()).decode("utf-8")
    media_type = uploaded_file.content_type or "image/jpeg"
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
