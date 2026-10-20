from django.urls import path

from . import views

urlpatterns = [
    path("schedule/", views.schedule_list, name="schedule"),
    path("schedule/new/", views.schedule_new, name="schedule_new"),
    path("schedule/<int:pk>/edit/", views.schedule_edit, name="schedule_edit"),
    path("schedule/<int:pk>/delete/", views.schedule_delete, name="schedule_delete"),
]