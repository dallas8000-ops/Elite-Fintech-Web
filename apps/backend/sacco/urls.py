from django.urls import path

from sacco.views import (
    CollectionProductListCreateView,
    CollectionsStatsView,
    InitiateCollectionView,
    PaymentIntentCancelView,
    PaymentIntentDetailView,
    PaymentIntentListView,
    PaymentIntentReceiptView,
)

urlpatterns = [
    path("products/", CollectionProductListCreateView.as_view()),
    path("initiate/", InitiateCollectionView.as_view()),
    path("intents/", PaymentIntentListView.as_view()),
    path("intents/<uuid:intent_id>/", PaymentIntentDetailView.as_view()),
    path("intents/<uuid:intent_id>/cancel/", PaymentIntentCancelView.as_view()),
    path("intents/<uuid:intent_id>/receipt/", PaymentIntentReceiptView.as_view()),
    path("stats/", CollectionsStatsView.as_view()),
]
