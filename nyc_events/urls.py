"""URL configuration for the NYC Event Explorer project."""

from django.contrib import admin
from django.urls import include, path

from . import views

admin.site.site_header = "NYC Event Explorer Administration"
admin.site.site_title = "NYC Event Explorer Admin"

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("admin/", admin.site.urls),
]
