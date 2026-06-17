from django.urls import path

from billing.webhooks import PayfastWebhookView, StripeWebhookView
from sacco.webhooks import FlutterwaveWebhookView

urlpatterns = [
    path("payfast/", PayfastWebhookView.as_view()),
    path("stripe/", StripeWebhookView.as_view()),
    path("flutterwave/", FlutterwaveWebhookView.as_view()),
]
