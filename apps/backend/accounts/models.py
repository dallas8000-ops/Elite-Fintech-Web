from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Extended user with optional SA ID for FICA workflows."""

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    sa_id_number = models.CharField(max_length=13, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.email


class RevokedRefreshToken(models.Model):
    """Hard revocation for refresh tokens on explicit logout.

    Distinct from simplejwt's rotation blacklist, which tolerates a short grace
    window for concurrent tab refreshes. Logout must invalidate immediately.
    """

    jti = models.CharField(max_length=255, unique=True, db_index=True)
    revoked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "revoked_refresh_tokens"
