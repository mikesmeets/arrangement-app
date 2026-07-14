from django.urls import path

from . import views

urlpatterns = [
    path("inventory/", views.inventory_list, name="inventory-list"),
    path("inventory/add/", views.inventory_add, name="inventory-add"),
    path("vendors/", views.vendor_list, name="vendor-list"),
    path("vendors/add/", views.vendor_add, name="vendor-add"),
    path("vendors/options/", views.vendor_options, name="vendor-options"),
    path("vendors/<int:pk>/edit/", views.vendor_edit, name="vendor-edit"),
    path("flowers/", views.flower_list, name="flower-list"),
    path("flowers/add/", views.flower_add, name="flower-add"),
    path("flowers/options/", views.flower_options, name="flower-options"),
    path("flowers/<int:pk>/", views.flower_detail, name="flower-detail"),
    path("flowers/<int:pk>/edit/", views.flower_edit, name="flower-edit"),
    path("invoices/", views.invoice_list, name="invoice-list"),
    path("invoices/add/", views.invoice_create, name="invoice-create"),
    path("invoices/<int:pk>/review/", views.invoice_review, name="invoice-review"),
]
