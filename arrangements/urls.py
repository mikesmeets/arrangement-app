from django.urls import path

from . import views

urlpatterns = [
    path("", views.arrangement_list, name="arrangement-list"),
    path("new/", views.arrangement_create, name="arrangement-create"),
    path("<int:pk>/edit/", views.arrangement_edit, name="arrangement-edit"),
    path("<int:pk>/delete/", views.arrangement_delete, name="arrangement-delete"),
    path("<int:pk>/items/add/", views.arrangement_add_item, name="arrangement-add-item"),
    path("<int:pk>/price/", views.arrangement_set_price, name="arrangement-set-price"),
    path(
        "<int:pk>/items/<int:item_id>/remove/",
        views.arrangement_remove_item,
        name="arrangement-remove-item",
    ),
    path(
        "<int:pk>/items/<int:item_id>/qty/",
        views.arrangement_update_item_quantity,
        name="arrangement-update-item-qty",
    ),
    path(
        "<int:pk>/items/<int:item_id>/qty/set/",
        views.arrangement_set_item_quantity,
        name="arrangement-set-item-qty",
    ),
]
