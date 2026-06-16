from rest_framework import serializers

from accounts.models import User
from billing.services.east_africa_constants import EAST_AFRICA_COUNTRIES
from billing.services.regional import is_south_africa, region_choices, registration_labels


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "name", "sa_id_number")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=255)
    organization_name = serializers.CharField(max_length=255)
    country = serializers.CharField(max_length=2, required=False, default="UG")
    province = serializers.CharField(max_length=32)
    industry_sector = serializers.CharField(max_length=255, required=False, allow_blank=True)
    cipc_registration_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    vat_number = serializers.CharField(max_length=16, required=False, allow_blank=True)
    data_consent = serializers.BooleanField()
    # Legacy SA field name — accepted but optional
    popia_consent = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if is_south_africa():
            if not attrs.get("data_consent") and not attrs.get("popia_consent"):
                raise serializers.ValidationError({"data_consent": "Consent is required to register."})
            attrs["data_consent"] = attrs.get("data_consent") or attrs.get("popia_consent")
            valid = {c[0] for c in region_choices()}
            if attrs["province"] not in valid:
                raise serializers.ValidationError({"province": "Invalid province."})
            attrs["country"] = "ZA"
        else:
            if not attrs.get("data_consent"):
                raise serializers.ValidationError({"data_consent": "Data protection consent is required."})
            country = (attrs.get("country") or "UG").upper()
            if country not in EAST_AFRICA_COUNTRIES:
                raise serializers.ValidationError({"country": "Country must be UG, KE, RW, or TZ."})
            attrs["country"] = country
            valid = {c[0] for c in region_choices(country)}
            if attrs["province"] not in valid:
                raise serializers.ValidationError({"province": "Invalid region for selected country."})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    organization_id = serializers.UUIDField(required=False)
