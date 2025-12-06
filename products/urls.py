"""
URL Configuration for products app
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"products", views.ProductViewSet, basename="product")
router.register(r"imports", views.ImportViewSet, basename="import")

urlpatterns = [
    # Local storage upload (dev only)
    path("storage/upload/", views.local_storage_upload, name="local-storage-upload"),
] + router.urls
