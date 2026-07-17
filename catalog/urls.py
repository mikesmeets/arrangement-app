from django.urls import path

from . import views

urlpatterns = [
    path("inventory/", views.inventory_list, name="inventory-list"),
    path("inventory/add/", views.inventory_add, name="inventory-add"),
    path("inventory/expire/", views.inventory_expire, name="inventory-expire"),
    path("vendors/", views.vendor_list, name="vendor-list"),
    path("vendors/add/", views.vendor_add, name="vendor-add"),
    path("vendors/options/", views.vendor_options, name="vendor-options"),
    path("vendors/<int:pk>/edit/", views.vendor_edit, name="vendor-edit"),
    path("customers/", views.customer_list, name="customer-list"),
    path("customers/add/", views.customer_add, name="customer-add"),
    path("customers/options/", views.customer_options, name="customer-options"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer-edit"),
    path("subscriptions/", views.subscription_list, name="subscription-list"),
    path("subscriptions/add/", views.subscription_add, name="subscription-add"),
    path("subscriptions/<int:pk>/edit/", views.subscription_edit, name="subscription-edit"),
    path("flowers/", views.flower_list, name="flower-list"),
    path("flowers/add/", views.flower_add, name="flower-add"),
    path("flowers/options/", views.flower_options, name="flower-options"),
    path("flowers/<int:pk>/", views.flower_detail, name="flower-detail"),
    path("flowers/<int:pk>/edit/", views.flower_edit, name="flower-edit"),
    path("invoices/", views.invoice_list, name="invoice-list"),
    path("invoices/add/", views.invoice_create, name="invoice-create"),
    path("invoices/<int:pk>/review/", views.invoice_review, name="invoice-review"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice-delete"),
]
