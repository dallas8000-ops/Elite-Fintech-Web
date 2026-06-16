from django.urls import path

from billing.views import CheckoutView, EventsView, PlansView, PortalView, RailsView, StatsView, SubscriptionView
from billing.views_region import FxRatesView, RegionConfigView

urlpatterns = [
    path("region/", RegionConfigView.as_view()),
    path("rates/", FxRatesView.as_view()),
    path("plans/", PlansView.as_view()),
    path("rails/", RailsView.as_view()),
    path("subscription/", SubscriptionView.as_view()),
    path("events/", EventsView.as_view()),
    path("stats/", StatsView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("portal/", PortalView.as_view()),
]
