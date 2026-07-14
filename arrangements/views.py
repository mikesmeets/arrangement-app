from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Invoice

from .forms import ArrangementForm
from .models import Arrangement, ArrangementItem

RECENT_INVOICE_LIMIT = 10


@login_required
def arrangement_list(request):
    arrangements = Arrangement.objects.all()
    return render(request, "arrangements/arrangement_list.html", {"arrangements": arrangements})


@login_required
def arrangement_create(request):
    arrangement = Arrangement.objects.create(name="New Arrangement")
    return redirect("arrangement-edit", pk=arrangement.pk)


@login_required
def arrangement_edit(request, pk):
    arrangement = get_object_or_404(Arrangement, pk=pk)
    if request.method == "POST":
        form = ArrangementForm(request.POST, request.FILES, instance=arrangement)
        if form.is_valid():
            form.save()
            messages.success(request, "Arrangement saved.")
            return redirect("arrangement-edit", pk=arrangement.pk)
    else:
        form = ArrangementForm(instance=arrangement)
    return render(
        request,
        "arrangements/arrangement_edit.html",
        {
            "arrangement": arrangement,
            "form": form,
            "invoice_rows": _recent_invoice_flowers(),
        },
    )


def _recent_invoice_flowers():
    """Recent invoices paired with their mapped line items, for the invoice-based
    flower picker in the arrangement builder. Each button is labelled with the
    vendor's product name (the line item), and adds the flower it maps to."""
    invoices = (
        Invoice.objects.select_related("vendor")
        .prefetch_related("line_items__flower__variety", "line_items__flower__category")
        .order_by("-date", "-created_at")
    )
    rows = []
    for invoice in invoices:
        line_items = [li for li in invoice.line_items.all() if li.flower_id]
        if line_items:
            rows.append({"invoice": invoice, "line_items": line_items})
        if len(rows) >= RECENT_INVOICE_LIMIT:
            break
    return rows


def _items_response(request, arrangement):
    return render(
        request,
        "arrangements/_items_and_price.html",
        {"arrangement": arrangement},
    )


@login_required
def arrangement_add_item(request, pk):
    arrangement = get_object_or_404(Arrangement, pk=pk)
    if request.method == "POST":
        flower_id = request.POST.get("flower")
        try:
            quantity = Decimal(request.POST.get("quantity") or "1")
        except InvalidOperation:
            quantity = Decimal("1")
        if flower_id:
            item, created = ArrangementItem.objects.get_or_create(
                arrangement=arrangement,
                flower_id=flower_id,
                defaults={"quantity": quantity},
            )
            if not created:
                item.quantity += quantity
                item.save()
    return _items_response(request, arrangement)


@login_required
def arrangement_set_price(request, pk):
    arrangement = get_object_or_404(Arrangement, pk=pk)
    if request.method == "POST":
        raw = request.POST.get("price_override", "").strip()
        if raw:
            try:
                arrangement.price_override = Decimal(raw)
            except InvalidOperation:
                pass
            else:
                arrangement.save()
        else:
            arrangement.price_override = None
            arrangement.save()
    return _items_response(request, arrangement)


@login_required
def arrangement_update_item_quantity(request, pk, item_id):
    arrangement = get_object_or_404(Arrangement, pk=pk)
    item = get_object_or_404(ArrangementItem, pk=item_id, arrangement=arrangement)
    if request.method == "POST":
        delta = Decimal(request.POST.get("delta") or "0")
        item.quantity += delta
        if item.quantity <= 0:
            item.delete()
        else:
            item.save()
    return _items_response(request, arrangement)


@login_required
def arrangement_set_item_quantity(request, pk, item_id):
    arrangement = get_object_or_404(Arrangement, pk=pk)
    item = get_object_or_404(ArrangementItem, pk=item_id, arrangement=arrangement)
    if request.method == "POST":
        try:
            quantity = Decimal(request.POST.get("quantity") or "0")
        except InvalidOperation:
            quantity = item.quantity
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
    return _items_response(request, arrangement)


@login_required
def arrangement_remove_item(request, pk, item_id):
    arrangement = get_object_or_404(Arrangement, pk=pk)
    ArrangementItem.objects.filter(pk=item_id, arrangement=arrangement).delete()
    return _items_response(request, arrangement)


@login_required
def arrangement_delete(request, pk):
    arrangement = get_object_or_404(Arrangement, pk=pk)
    if request.method == "POST":
        arrangement.delete()
        messages.success(request, "Arrangement deleted.")
        return redirect("arrangement-list")
    return redirect("arrangement-edit", pk=pk)
