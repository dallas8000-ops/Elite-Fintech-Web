from django.urls import path

from billing.webhooks import PayfastWebhookView, StripeWebhookView

urlpatterns = [
    path("payfast/", PayfastWebhookView.as_view()),
    path("stripe/", StripeWebhookView.as_view()),
]
