from django.contrib import admin

from sacco.models import CollectionProduct, LedgerEntry, PaymentIntent, SaccoMember


@admin.register(SaccoMember)
class SaccoMemberAdmin(admin.ModelAdmin):
    list_display = ("member_number", "full_name", "phone", "organization", "status")
    search_fields = ("member_number", "full_name", "phone")
    list_filter = ("status", "momo_network")


@admin.register(CollectionProduct)
class CollectionProductAdmin(admin.ModelAdmin):
    list_display = ("name", "amount_minor", "organization", "is_active")
    list_filter = ("is_active",)


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ("provider_reference", "status", "amount_minor", "member", "organization", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("provider_reference", "phone", "purpose")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_type", "amount_minor", "balance_after", "member", "created_at")
    list_filter = ("entry_type",)
