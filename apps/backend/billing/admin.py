from django.contrib import admin

from billing.models import PaymentEvent, Subscription

admin.site.register(Subscription)
admin.site.register(PaymentEvent)
