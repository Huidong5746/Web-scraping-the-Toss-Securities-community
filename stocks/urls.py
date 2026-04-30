from django.urls import path

from . import views


app_name = "stocks"

urlpatterns = [
    path("", views.index, name="index"),
]
