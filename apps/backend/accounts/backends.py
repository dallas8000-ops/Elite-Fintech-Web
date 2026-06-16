from django.contrib.auth.backends import ModelBackend

from accounts.models import User


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        try:
            user = User.objects.get(email=email or username)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
