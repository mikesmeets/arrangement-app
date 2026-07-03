from django import forms

from .models import Flower, FlowerCategory, FlowerVariety, InventoryItem, Invoice, Vendor


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "vendor",
            "flower",
            "name",
            "size",
            "grade",
            "quantity",
            "per_stem_cost",
            "date_received",
        ]
        widgets = {
            "date_received": forms.DateInput(attrs={"type": "date"}),
        }


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "contact_name", "phone", "email", "address", "notes"]


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["vendor", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class InvoiceFileForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["file"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"accept": "image/*,.pdf", "capture": "environment"}),
        }


class FlowerForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=FlowerCategory.objects.all(), required=False, label="Category"
    )
    new_category = forms.CharField(required=False, label="Or new category")
    variety = forms.ModelChoiceField(
        queryset=FlowerVariety.objects.select_related("category"),
        required=False,
        label="Variety",
    )
    new_variety = forms.CharField(required=False, label="Or new variety")

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
            "image": forms.ClearableFileInput(attrs={"accept": "image/*", "capture": "environment"}),
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
