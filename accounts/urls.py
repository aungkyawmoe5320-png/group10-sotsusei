from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("account/new/", views.account_new, name="account_new"),
    path("account/", views.account_detail, name="account_detail"),
    path("account/edit/", views.account_edit, name="account_edit"),
    path("account/delete/", views.account_delete, name="account_delete"),
    path("care-recipient/new/", views.care_recipient_new, name="care_recipient_new"),
    path("care-recipient/<int:pk>/edit/", views.care_recipient_edit, name="care_recipient_edit"),
    path("care-recipient/<int:pk>/delete/", views.care_recipient_delete, name="care_recipient_delete"),
    path("care-recipient/select/", views.care_recipient_select, name="care_recipient_select"),
]
