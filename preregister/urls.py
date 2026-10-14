from django.urls import path

from . import views

urlpatterns = [
    path("preregister/", views.preregister_list, name="preregister"),
    path("preregister/new/", views.preregister_new, name="preregister_new"),
    path("preregister/<int:pk>/", views.preregister_detail, name="preregister_detail"),
    path("preregister/<int:pk>/edit/", views.preregister_edit, name="preregister_edit"),
]