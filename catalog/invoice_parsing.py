from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.conf import settings


@dataclass
class ParsedLineItem:
    name: str
    size: str = ""
    grade: str = ""
    total_cost: Optional[Decimal] = None
    quantity: int = 1


@dataclass
class ParsedInvoice:
    vendor_name: str = ""
    invoice_number: str = ""
    date: str = ""
    line_items: list = field(default_factory=list)
    error: Optional[str] = None


def parse_invoice(uploaded_file) -> ParsedInvoice:
    """Extract vendor + line items from an invoice photo/PDF.

    Swappable AI backend: this module only defines the interface. The actual
    call lives in claude_invoice_parser.py so switching providers later means
    writing a new module and changing the import below, not touching callers.
    """
    if not settings.ANTHROPIC_API_KEY:
        return ParsedInvoice(
            error="No ANTHROPIC_API_KEY configured — add line items manually below."
        )
    from . import claude_invoice_parser

    return claude_invoice_parser.parse(uploaded_file)
