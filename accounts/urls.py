from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/<str:role>/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("account/new/", views.account_new, name="account_new"),
    path("account/", views.account_detail, name="account_detail"),
    path("account/edit/", views.account_edit, name="account_edit"),
    path("account/delete/", views.account_delete, name="account_delete"),
]
