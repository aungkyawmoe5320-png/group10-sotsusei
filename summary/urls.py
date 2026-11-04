from django.urls import path

from . import views

urlpatterns = [
    path("summary/", views.summary, name="summary"),
    path("summary/save/", views.summary_save, name="summary_save"),
    path("summary/survey/", views.summary_survey, name="summary_survey"),
    path("summary/pdf/", views.summary_detail, name="summary_detail"),
    path("summary/pdf/download/", views.summary_download, name="summary_download"),
    path("summary/pdf/delete/", views.summary_delete, name="summary_delete"),
]