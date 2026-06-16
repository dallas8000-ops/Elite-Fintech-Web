from django.urls import path

from realtime.consumers import BillingConsumer

websocket_urlpatterns = [
    path("ws/billing/", BillingConsumer.as_asgi()),
]
