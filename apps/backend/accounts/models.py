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
    """Explicit, hard revocation for refresh tokens — distinct from
    simplejwt's BLACKLIST_AFTER_ROTATION blacklist.

    Rotation-blacklisting (a token being superseded by its own successor
    during a normal /refresh/ call) is given a short grace window to
    tolerate near-simultaneous concurrent refreshes from the same
    legitimate session (e.g. two open tabs). Explicit logout must NOT get
    that same leniency — a token the user deliberately logged out from
    needs to stop working immediately, with no window in which a captured
    copy could still be replayed.
    """

    jti = models.CharField(max_length=255, unique=True, db_index=True)
    revoked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "revoked_refresh_tokens"
