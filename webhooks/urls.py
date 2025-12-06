"""
URL Configuration for webhooks app
"""
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"webhooks", views.WebhookViewSet, basename="webhook")
router.register(
    r"webhook-deliveries", views.WebhookDeliveryViewSet, basename="webhook-delivery"
)

urlpatterns = router.urls

