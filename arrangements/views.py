from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Invoice, Product

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
            arrangement = form.save()
            # Attaching a subscription pulls its current price into the price field.
            if (
                "subscription" in form.changed_data
                and arrangement.subscription
                and arrangement.subscription.current_price is not None
            ):
                arrangement.price_override = arrangement.subscription.current_price
                arrangement.save(update_fields=["price_override"])
                messages.success(
                    request,
                    f"Arrangement saved. Price set to the subscription's ${arrangement.price_override}.",
                )
            else:
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
            "invoice_rows": _recent_invoice_products(),
        },
    )


def _recent_invoice_products():
    """Recent confirmed invoices paired with the distinct products received on
    each, for the invoice-based picker in the arrangement builder. Buttons are
    labelled with the product's vendor-abbreviated label. Products not sourced
    from a recent invoice (e.g. seeded or manually-added stock) fall into a
    per-vendor group so every product stays addable."""
    invoices = (
        Invoice.objects.select_related("vendor")
        .prefetch_related("inventory_items__product__vendor", "inventory_items__product__flower__variety")
        .filter(inventory_items__isnull=False)
        .distinct()
        .order_by("-date", "-created_at")
    )
    rows = []
    surfaced = set()
    for invoice in invoices:
        products = []
        seen = set()
        for inv_item in invoice.inventory_items.all():
            product = inv_item.product
            if product and product.id not in seen:
                seen.add(product.id)
                products.append(product)
                surfaced.add(product.id)
        if products:
            rows.append({"invoice": invoice, "vendor": invoice.vendor, "products": products})
        if len(rows) >= RECENT_INVOICE_LIMIT:
            break

    leftover = (
        Product.objects.select_related("vendor", "flower__variety")
        .exclude(id__in=surfaced)
        .order_by("vendor__name", "name")
    )
    by_vendor = {}
    for product in leftover:
        by_vendor.setdefault(product.vendor_id, {"vendor": product.vendor, "products": []})
        by_vendor[product.vendor_id]["products"].append(product)
    for group in by_vendor.values():
        rows.append({"invoice": None, "vendor": group["vendor"], "products": group["products"]})

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
        product_id = request.POST.get("product")
        try:
            quantity = Decimal(request.POST.get("quantity") or "1")
        except InvalidOperation:
            quantity = Decimal("1")
        if product_id:
            item, created = ArrangementItem.objects.get_or_create(
                arrangement=arrangement,
                product_id=product_id,
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
