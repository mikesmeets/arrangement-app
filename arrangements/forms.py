from django import forms

from .models import Arrangement


class ArrangementForm(forms.ModelForm):
    class Meta:
        model = Arrangement
        fields = [
            "name",
            "type",
            "description",
            "photo",
            "shopify_collection",
            "tags",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*", "capture": "environment"}),
            "tags": forms.TextInput(attrs={"placeholder": "e.g. valentines, red, roses"}),
        }
        labels = {
            "shopify_collection": "Collection",
        }
