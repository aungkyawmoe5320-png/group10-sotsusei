from django.urls import path

from .import views

urlpatterns = [
    path("preregister/", views.preregister_list, name="preregister"),
    path("preregister/<int:pk>/", views.preregister_detail, name="preregister_detail"),
]