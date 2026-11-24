from django.urls import path

from . import views

urlpatterns = [
    path("support/", views.support, name="support"),
    path("support/emergency/", views.support_emergency, name="support_emergency"),
    path("support/emergency/<str:key>/", views.support_emergency_detail, name="support_emergency_detail"),
    path("support/care-steps/", views.care_steps, name="care_steps"),
    path("support/care-steps/result/", views.care_steps_result, name="care_steps_result"),
]
