from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User


@database_sync_to_async
def get_user(user_id: int):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token_list = query.get("token", [])
        scope["user"] = AnonymousUser()
        scope["organization_id"] = None
        scope["role"] = None

        if token_list:
            try:
                access = AccessToken(token_list[0])
                scope["user"] = await get_user(access["user_id"])
                scope["organization_id"] = access.get("organization_id")
                scope["role"] = access.get("role")
            except Exception:
                pass

        return await super().__call__(scope, receive, send)
