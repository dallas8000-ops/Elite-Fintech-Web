from django.contrib import admin

from .models import RevokedRefreshToken, User

admin.site.register(User)


@admin.register(RevokedRefreshToken)
class RevokedRefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("jti", "revoked_at")
    search_fields = ("jti",)
