import datetime
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import modelformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CustomerForm,
    FlowerForm,
    InvoiceFileForm,
    InvoiceForm,
    ManualStockForm,
    SubscriptionForm,
    VendorForm,
)
from .invoice_parsing import parse_invoice
from .models import (
    Customer,
    Flower,
    FlowerCategory,
    Invoice,
    InvoiceLineItem,
    Product,
    Subscription,
    Vendor,
)
from .thumbnails import render_thumbnail


def _inventory_vendor_rows():
    """The inventory report. Nothing is stored: each product's stock is what its
    invoice line items brought in (ignoring expired invoices) less what
    arrangements consumed. Grouped by vendor for the collapsible screen."""
    products = (
        Product.objects.select_related("vendor", "flower__variety")
        .prefetch_related("line_items__invoice", "arrangement_items")
        .order_by("vendor__name", "name")
    )
    vendor_rows = []
    current = None
    for product in products:
        came_in = product.quantity_in
        used = product.quantity_used
        if not came_in and not used:
            continue
        if current is None or current["vendor"] != product.vendor:
            current = {
                "vendor": product.vendor,
                "products": [],
                "on_hand": Decimal("0"),
                "value_in": Decimal("0.00"),
                "value_used": Decimal("0.00"),
            }
            vendor_rows.append(current)
        value_in = product.value_in
        value_used = product.value_used
        current["products"].append(
            {
                "product": product,
                "came_in": came_in,
                "used": used,
                "on_hand": came_in - used,
                "avg_cost": product.current_avg_cost,
            }
        )
        current["on_hand"] += came_in - used
        current["value_in"] += value_in
        current["value_used"] += value_used

    for row in vendor_rows:
        row["usage_pct"] = (
            row["value_used"] / row["value_in"] * 100 if row["value_in"] else None
        )
    return vendor_rows


@login_required
def inventory_list(request):
    return render(
        request,
        "catalog/inventory_list.html",
        {"vendor_rows": _inventory_vendor_rows()},
    )


def _product_for(vendor, name, flower=None):
    """Get-or-create the vendor's Product for this name, keeping its optional
    flower mapping current."""
    product, _ = Product.objects.get_or_create(
        vendor=vendor, name=name, defaults={"flower": flower}
    )
    if flower is not None and product.flower_id != flower.id:
        product.flower = flower
        product.save(update_fields=["flower"])
    return product


@login_required
def inventory_add(request):
    """Hand-entered stock is saved as a one-line invoice — invoices are the only
    source of stock, so there's nowhere else for it to live."""
    if request.method == "POST":
        form = ManualStockForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            product = _product_for(data["vendor"], data["name"], data["flower"])
            invoice = Invoice.objects.create(
                vendor=data["vendor"],
                date=data["date_received"],
                status=Invoice.STATUS_CONFIRMED,
            )
            quantity = data["quantity"]
            InvoiceLineItem.objects.create(
                invoice=invoice,
                product=product,
                name=data["name"],
                quantity=quantity,
                total_cost=data["per_stem_cost"] * quantity,
                flower=data["flower"],
                size=data["size"],
                grade=data["grade"],
            )
            messages.success(request, "Stock added as a one-line invoice.")
            return redirect("inventory-list")
    else:
        form = ManualStockForm()
    return render(request, "catalog/inventory_form.html", {"form": form})


@login_required
def vendor_add(request):
    is_modal = bool(request.htmx)
    if request.method == "POST":
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor = form.save()
            if is_modal:
                response = HttpResponse("")
                response["HX-Trigger"] = json.dumps(
                    {"vendor-added": {"id": vendor.id, "label": str(vendor)}}
                )
                return response
            messages.success(request, "Vendor added.")
            return redirect("vendor-list")
    else:
        form = VendorForm(initial={"name": request.GET.get("name", "").strip()})
    template = "catalog/_vendor_form_modal.html" if is_modal else "catalog/vendor_form.html"
    return render(request, template, {"form": form, "title": "Add Vendor"})


@login_required
def vendor_list(request):
    vendors = Vendor.objects.all()
    return render(request, "catalog/vendor_list.html", {"vendors": vendors})


@login_required
def vendor_edit(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == "POST":
        form = VendorForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, "Vendor updated.")
            return redirect("vendor-list")
    else:
        form = VendorForm(instance=vendor)
    return render(
        request,
        "catalog/vendor_form.html",
        {"form": form, "title": "Edit Vendor", "vendor": vendor},
    )


@login_required
def vendor_options(request):
    vendors = Vendor.objects.all()
    return render(request, "catalog/_vendor_options.html", {"vendors": vendors})


@login_required
def customer_add(request):
    is_modal = bool(request.htmx)
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            if is_modal:
                response = HttpResponse("")
                response["HX-Trigger"] = json.dumps(
                    {"customer-added": {"id": customer.id, "label": str(customer)}}
                )
                return response
            messages.success(request, "Customer added.")
            return redirect("customer-list")
    else:
        form = CustomerForm(initial={"name": request.GET.get("name", "").strip()})
    template = "catalog/_customer_form_modal.html" if is_modal else "catalog/customer_form.html"
    return render(request, template, {"form": form, "title": "Add Customer"})


@login_required
def customer_list(request):
    customers = Customer.objects.all()
    return render(request, "catalog/customer_list.html", {"customers": customers})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated.")
            return redirect("customer-list")
    else:
        form = CustomerForm(instance=customer)
    return render(
        request,
        "catalog/customer_form.html",
        {"form": form, "title": "Edit Customer", "customer": customer},
    )


@login_required
def customer_options(request):
    customers = Customer.objects.all()
    return render(request, "catalog/_customer_options.html", {"customers": customers})


@login_required
def subscription_list(request):
    subscriptions = Subscription.objects.select_related("customer")
    return render(
        request, "catalog/subscription_list.html", {"subscriptions": subscriptions}
    )


@login_required
def subscription_add(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription added.")
            return redirect("subscription-list")
    else:
        form = SubscriptionForm()
    return render(
        request,
        "catalog/subscription_form.html",
        {"form": form, "title": "Add Subscription"},
    )


@login_required
def subscription_edit(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if request.method == "POST":
        form = SubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription updated.")
            return redirect("subscription-list")
    else:
        form = SubscriptionForm(instance=subscription)
    return render(
        request,
        "catalog/subscription_form.html",
        {"form": form, "title": "Edit Subscription", "subscription": subscription},
    )


SORT_FIELDS = {
    "category": lambda row: row["variety"].category.name.lower(),
    "variety": lambda row: row["variety"].name.lower(),
    "design_category": lambda row: row["design_categories"].lower(),
    "on_hand": lambda row: row["total_on_hand"],
    "avg_cost": lambda row: row["avg_cost"],
}


def _sort_url(request, field, current_sort):
    params = request.GET.copy()
    params["sort"] = f"-{field}" if current_sort == field else field
    return f"?{params.urlencode()}"


@login_required
def flower_list(request):
    flowers = Flower.objects.select_related("category", "variety")

    category_id = request.GET.get("category", "").strip()
    if category_id:
        flowers = flowers.filter(category_id=category_id)

    variety_query = request.GET.get("variety", "").strip()
    if variety_query:
        flowers = flowers.filter(variety__name__icontains=variety_query)

    design_category = request.GET.get("design_category", "").strip()
    if design_category:
        flowers = flowers.filter(design_category=design_category)

    color_query = request.GET.get("color", "").strip()
    if color_query:
        flowers = flowers.filter(color__icontains=color_query)

    variety_rows = []
    seen_variety_ids = {}
    for flower in flowers:
        row = seen_variety_ids.get(flower.variety_id)
        if row is None:
            row = {"variety": flower.variety, "flowers": []}
            seen_variety_ids[flower.variety_id] = row
            variety_rows.append(row)
        row["flowers"].append(flower)

    for row in variety_rows:
        flist = row["flowers"]
        row["total_on_hand"] = sum(f.quantity_on_hand for f in flist)
        costs = [f.current_avg_cost for f in flist if f.current_avg_cost]
        row["avg_cost"] = sum(costs) / len(costs) if costs else Decimal("0.00")
        row["design_categories"] = ", ".join(
            sorted({f.get_design_category_display() for f in flist})
        )

    on_hand_min = request.GET.get("on_hand_min", "").strip()
    if on_hand_min:
        try:
            threshold = Decimal(on_hand_min)
        except InvalidOperation:
            pass
        else:
            variety_rows = [r for r in variety_rows if r["total_on_hand"] >= threshold]

    avg_cost_min = request.GET.get("avg_cost_min", "").strip()
    if avg_cost_min:
        try:
            threshold = Decimal(avg_cost_min)
        except InvalidOperation:
            pass
        else:
            variety_rows = [r for r in variety_rows if r["avg_cost"] >= threshold]

    sort = request.GET.get("sort", "").strip()
    sort_field = sort.lstrip("-")
    if sort_field in SORT_FIELDS:
        variety_rows.sort(key=SORT_FIELDS[sort_field], reverse=sort.startswith("-"))

    sort_urls = {field: _sort_url(request, field, sort) for field in SORT_FIELDS}
    sort_indicators = {
        field: ("▼" if sort == f"-{field}" else "▲" if sort == field else "")
        for field in SORT_FIELDS
    }

    return render(
        request,
        "catalog/flower_list.html",
        {
            "variety_rows": variety_rows,
            "categories": FlowerCategory.objects.all(),
            "design_category_choices": Flower.DESIGN_CATEGORY_CHOICES,
            "selected_category": category_id,
            "variety_query": variety_query,
            "selected_design_category": design_category,
            "color_query": color_query,
            "on_hand_min": on_hand_min,
            "avg_cost_min": avg_cost_min,
            "current_sort": sort,
            "sort_urls": sort_urls,
            "sort_indicators": sort_indicators,
            "any_filter_active": bool(
                category_id
                or variety_query
                or design_category
                or color_query
                or on_hand_min
                or avg_cost_min
            ),
        },
    )


@login_required
def flower_detail(request, pk):
    flower = get_object_or_404(
        Flower.objects.select_related("category", "variety"), pk=pk
    )
    history = list(
        InvoiceLineItem.objects.filter(product__flower=flower)
        .select_related("invoice__vendor")
        .order_by("invoice__date")
    )
    rows = []
    prev_cost = None
    for item in history:
        direction = None
        delta_abs = None
        if prev_cost is not None:
            diff = item.per_stem_cost - prev_cost
            delta_abs = abs(diff)
            if diff > 0:
                direction = "up"
            elif diff < 0:
                direction = "down"
            else:
                direction = "flat"
        rows.append({"item": item, "direction": direction, "delta_abs": delta_abs})
        prev_cost = item.per_stem_cost
    rows.reverse()

    return render(
        request, "catalog/flower_detail.html", {"flower": flower, "rows": rows}
    )


@login_required
def flower_add(request):
    is_modal = bool(request.htmx)
    if request.method == "POST":
        form = FlowerForm(request.POST, request.FILES)
        if form.is_valid():
            flower = form.save()
            if not flower.image:
                content = render_thumbnail(flower)
                flower.image.save(content.name, content, save=True)
            if is_modal:
                response = HttpResponse("")
                response["HX-Trigger"] = json.dumps(
                    {"flower-added": {"id": flower.id, "label": str(flower)}}
                )
                return response
            messages.success(request, "Flower added.")
            return redirect("flower-detail", pk=flower.pk)
    else:
        form = FlowerForm()
    template = "catalog/_flower_form_modal.html" if is_modal else "catalog/flower_form.html"
    return render(request, template, {"form": form, "title": "Add Flower"})


@login_required
def flower_options(request):
    flowers = Flower.objects.select_related("category", "variety")
    return render(request, "catalog/_flower_options.html", {"flowers": flowers})


@login_required
def flower_edit(request, pk):
    flower = get_object_or_404(Flower, pk=pk)
    if request.method == "POST":
        form = FlowerForm(request.POST, request.FILES, instance=flower)
        if form.is_valid():
            form.save()
            messages.success(request, "Flower updated.")
            return redirect("flower-detail", pk=flower.pk)
    else:
        form = FlowerForm(instance=flower)
    return render(
        request,
        "catalog/flower_form.html",
        {"form": form, "title": "Edit Flower", "flower": flower},
    )


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related("vendor").prefetch_related("line_items")
    return render(request, "catalog/invoice_list.html", {"invoices": invoices})


@login_required
def invoice_expire(request, pk):
    """Mark a delivery perished (or restore it). An expired invoice's line items
    stop counting toward stock and arrangement pricing."""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == "POST":
        if request.POST.get("restore") == "1":
            invoice.expired = False
            invoice.expired_on = None
        else:
            invoice.expired = True
            invoice.expired_on = timezone.localdate()
        invoice.save(update_fields=["expired", "expired_on"])
    invoices = Invoice.objects.select_related("vendor").prefetch_related("line_items")
    return render(request, "catalog/_invoice_rows.html", {"invoices": invoices})


def _suggest_flower(name):
    """Best-effort match of an invoice line item's name against the flower taxonomy."""
    name_lower = name.lower()
    candidates = list(Flower.objects.select_related("variety", "category"))
    for flower in candidates:
        if flower.variety.name.lower() in name_lower and flower.color.lower() in name_lower:
            return flower
    for flower in candidates:
        if flower.variety.name.lower() in name_lower:
            return flower
    return None


def _suggest_vendor(name):
    """Best-effort match of an extracted vendor name against existing vendors."""
    name = (name or "").strip()
    if not name:
        return None
    match = Vendor.objects.filter(name__iexact=name).first()
    if match:
        return match
    match = Vendor.objects.filter(name__icontains=name).first()
    if match:
        return match
    # The printed name may carry extra words (e.g. "Mayesh Wholesale" for a
    # vendor saved as "Mayesh"), so also look for an on-file name inside it.
    lowered = name.lower()
    for vendor in Vendor.objects.all():
        if vendor.name.lower() in lowered:
            return vendor
    return None


@login_required
def invoice_create(request):
    if request.method == "POST":
        invoice = Invoice.objects.create()
        return redirect("invoice-review", pk=invoice.pk)
    return redirect("invoice-list")


def _run_extraction(invoice):
    result = parse_invoice(invoice.file)
    invoice.raw_extracted_data = {
        "vendor_name": result.vendor_name,
        "invoice_number": result.invoice_number,
        "date": result.date,
        "line_items": [
            {
                "name": li.name,
                "size": li.size,
                "grade": li.grade,
                "total_cost": str(li.total_cost) if li.total_cost is not None else None,
                "quantity": li.quantity,
            }
            for li in result.line_items
        ],
        "error": result.error,
    }
    # Auto-fill the vendor invoice number (a plain string, no matching needed)
    # without clobbering anything already entered by hand.
    if result.invoice_number and not invoice.vendor_invoice_number:
        invoice.vendor_invoice_number = result.invoice_number
    # Pull the invoice date if Claude returned a parseable one.
    if result.date:
        try:
            invoice.date = datetime.date.fromisoformat(result.date)
        except ValueError:
            pass
    # Match the extracted vendor name to one on file (if any) and select it.
    # When nothing matches, the review page offers a one-click "create vendor".
    if not invoice.vendor_id:
        matched = _suggest_vendor(result.vendor_name)
        if matched:
            invoice.vendor = matched
    invoice.save()
    return result


InvoiceLineItemFormSet = modelformset_factory(
    InvoiceLineItem,
    fields=["name", "quantity", "total_cost", "flower", "size", "grade"],
    extra=1,
    can_delete=True,
)


@login_required
def invoice_review(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("vendor"), pk=pk)
    queryset = invoice.line_items.select_related("flower")

    if request.method == "POST" and "save_details" in request.POST:
        details_form = InvoiceForm(request.POST, instance=invoice)
        if details_form.is_valid():
            invoice = details_form.save()
            messages.success(request, "Details saved.")
            return redirect("invoice-review", pk=invoice.pk)
        file_form = InvoiceFileForm(instance=invoice)
        formset = InvoiceLineItemFormSet(queryset=queryset)

    elif request.method == "POST" and "extract_file" in request.POST:
        details_form = InvoiceForm(instance=invoice)
        file_form = InvoiceFileForm(request.POST, request.FILES, instance=invoice)
        formset = InvoiceLineItemFormSet(queryset=queryset)
        if file_form.is_valid() and file_form.cleaned_data.get("file"):
            invoice = file_form.save()
            result = _run_extraction(invoice)
            if result.error:
                messages.warning(
                    request,
                    f"Automatic extraction didn't run: {result.error} Add line items manually below.",
                )
            else:
                for li in result.line_items:
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        name=li.name,
                        size=li.size,
                        grade=li.grade,
                        total_cost=li.total_cost or Decimal("0.00"),
                        quantity=li.quantity,
                        flower=_suggest_flower(li.name),
                    )
                messages.success(
                    request,
                    f"Extracted {len(result.line_items)} line item(s) below.",
                )
            return redirect("invoice-review", pk=invoice.pk)
        if not file_form.errors:
            file_form.add_error("file", "Choose a file to extract.")

    elif request.method == "POST" and "confirm" in request.POST:
        details_form = InvoiceForm(instance=invoice)
        file_form = InvoiceFileForm(instance=invoice)
        formset = InvoiceLineItemFormSet(request.POST, queryset=queryset)
        if not invoice.vendor_id:
            messages.error(request, "Pick a vendor before confirming.")
        elif formset.is_valid():
            new_and_changed = formset.save(commit=False)
            for obj in formset.deleted_objects:
                obj.delete()
            for line_item in new_and_changed:
                line_item.invoice = invoice
                line_item.save()
            # Stock is derived from these line items — nothing is copied into a
            # separate table, so re-confirming an edited invoice can't duplicate.
            added = 0
            for line_item in invoice.line_items.select_related("flower"):
                line_item.product = _product_for(
                    invoice.vendor, line_item.name, line_item.flower
                )
                line_item.save(update_fields=["product"])
                added += 1
            invoice.status = Invoice.STATUS_CONFIRMED
            invoice.save()
            messages.success(request, f"Confirmed. {added} line item(s) in stock.")
            return redirect("inventory-list")

    else:
        details_form = InvoiceForm(instance=invoice)
        file_form = InvoiceFileForm(instance=invoice)
        formset = InvoiceLineItemFormSet(queryset=queryset)

    return render(
        request,
        "catalog/invoice_review.html",
        {"invoice": invoice, "form": details_form, "file_form": file_form, "formset": formset},
    )
