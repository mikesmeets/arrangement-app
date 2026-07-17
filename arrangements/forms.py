from django import forms

from .models import Arrangement


class ArrangementForm(forms.ModelForm):
    class Meta:
        model = Arrangement
        fields = [
            "name",
            "mode",
            "type",
            "subscription",
            "description",
            "photo",
            "shopify_collection",
            "tags",
            "status",
        ]
        widgets = {
            "mode": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"rows": 4}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "tags": forms.TextInput(attrs={"placeholder": "e.g. valentines, red, roses"}),
        }
        labels = {
            "shopify_collection": "Collection",
        }
