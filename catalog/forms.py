from django import forms

from .models import (
    Customer,
    Flower,
    FlowerCategory,
    FlowerVariety,
    Invoice,
    InvoiceLineItem,
    Product,
    Subscription,
    Vendor,
)


def inline_create_select():
    """A select whose list ends with "+ Create new…"; picking it reveals the
    matching new_<field> input. Paired up client-side by field name."""
    return forms.Select(attrs={"data-inline-create": "1"})


def resolve_inline_create(form, cleaned, field, model, required_message):
    """Use the typed new_<field> name to get-or-create the record, otherwise
    fall back to whatever was picked in the select."""
    typed = (cleaned.get(f"new_{field}") or "").strip()
    chosen = cleaned.get(field)
    if typed:
        chosen, _ = model.objects.get_or_create(name=typed)
        cleaned[field] = chosen
    if not chosen:
        form.add_error(field, required_message)
    return chosen


class ManualStockForm(forms.Form):
    """Hand-entered stock. There's no inventory table — this is saved as a
    one-line invoice for the vendor, which is what stock is derived from."""

    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.all(), required=False, widget=inline_create_select()
    )
    new_vendor = forms.CharField(required=False, label="New vendor name")
    name = forms.CharField(max_length=150, label="Product name")
    kind = forms.ChoiceField(choices=Product.KIND_CHOICES, label="Type")
    flower = forms.ModelChoiceField(
        queryset=Flower.objects.select_related("variety"),
        required=False,
        label="Flower (taxonomy, optional)",
    )
    size = forms.CharField(max_length=50, required=False)
    grade = forms.CharField(max_length=50, required=False)
    quantity = forms.IntegerField(min_value=0)
    per_stem_cost = forms.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    date_received = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned = super().clean()
        resolve_inline_create(
            self, cleaned, "vendor", Vendor, "Choose a vendor or create a new one."
        )
        return cleaned


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "abbreviation", "contact_name", "phone", "email", "website", "address", "notes"]
        labels = {"abbreviation": "Abbreviation"}


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "address"]


class SubscriptionForm(forms.ModelForm):
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(), required=False, widget=inline_create_select()
    )
    new_customer = forms.CharField(required=False, label="New customer name")

    class Meta:
        model = Subscription
        fields = ["customer", "new_customer", "sub_name", "current_price"]
        labels = {"sub_name": "Sub-name (business or personal)"}

    def clean(self):
        cleaned = super().clean()
        resolve_inline_create(
            self, cleaned, "customer", Customer, "Choose a customer or create a new one."
        )
        return cleaned


class InvoiceForm(forms.ModelForm):
    new_vendor = forms.CharField(required=False, label="New vendor name")

    class Meta:
        model = Invoice
        fields = ["vendor", "new_vendor", "vendor_invoice_number", "date"]
        labels = {
            "vendor_invoice_number": "Vendor invoice #",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "vendor": inline_create_select(),
        }

    def clean(self):
        cleaned = super().clean()
        # The vendor stays optional on an invoice, so only create when typed.
        typed = (cleaned.get("new_vendor") or "").strip()
        if typed:
            vendor, _ = Vendor.objects.get_or_create(name=typed)
            cleaned["vendor"] = vendor
        return cleaned


class FlowerPickerField(forms.ModelChoiceField):
    """Lists flowers as "category - variety - color" rather than the model's
    shorter default, so they're identifiable when mapping invoice lines."""

    def label_from_instance(self, obj):
        return obj.picker_label


class InvoiceLineItemForm(forms.ModelForm):
    flower = FlowerPickerField(
        queryset=Flower.objects.select_related("category", "variety"),
        required=False,
    )

    class Meta:
        model = InvoiceLineItem
        fields = ["name", "kind", "quantity", "total_cost", "flower", "size", "grade"]


class InvoiceFileForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["file"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"accept": "image/*,.pdf"}),
        }


class FlowerForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=FlowerCategory.objects.all(),
        required=False,
        label="Category",
        widget=inline_create_select(),
    )
    new_category = forms.CharField(required=False, label="New category name")
    variety = forms.ModelChoiceField(
        queryset=FlowerVariety.objects.select_related("category"),
        required=False,
        label="Variety",
        widget=inline_create_select(),
    )
    new_variety = forms.CharField(required=False, label="New variety name")

    class Meta:
        model = Flower
        fields = [
            "category",
            "new_category",
            "variety",
            "new_variety",
            "color",
            "type",
            "design_category",
            "image",
        ]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean(self):
        cleaned = super().clean()

        category = cleaned.get("category")
        new_category_name = cleaned.get("new_category", "").strip()
        if new_category_name:
            category, _ = FlowerCategory.objects.get_or_create(name=new_category_name)
        if not category:
            self.add_error("category", "Choose an existing category or enter a new one.")
        cleaned["category"] = category

        variety = cleaned.get("variety")
        new_variety_name = cleaned.get("new_variety", "").strip()
        if new_variety_name and category:
            variety, _ = FlowerVariety.objects.get_or_create(
                category=category, name=new_variety_name
            )
        if not variety:
            self.add_error("variety", "Choose an existing variety or enter a new one.")
        cleaned["variety"] = variety

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.category = self.cleaned_data["category"]
        instance.variety = self.cleaned_data["variety"]
        if commit:
            instance.save()
        return instance
