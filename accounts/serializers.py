from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, Country


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            "id", "name", "code", "currency_code", "currency_symbol",
            "is_international_bucket", "activation_fee",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles registration exactly per your field list: username, email,
    phone_number, country, password. `referral_code` is optional — if the
    signup link included one, we look up the owning user and set
    referred_by so the 70% commission chain works from their first plan
    purchase onward.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "country", "password", "referral_code"]

    def validate_referral_code(self, value):
        if not value:
            return value
        if not User.objects.filter(referral_code=value).exists():
            raise serializers.ValidationError("Invalid referral code.")
        return value

    def create(self, validated_data):
        referral_code = validated_data.pop("referral_code", None)
        referred_by = User.objects.filter(referral_code=referral_code).first() if referral_code else None

        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
            phone_number=validated_data["phone_number"],
            country=validated_data.get("country"),
            referred_by=referred_by,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone_number", "country", "referral_code",
            "date_joined", "is_activated", "activated_at",
        ]
        read_only_fields = fields


class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    PATCH-only fields for the profile page. Deliberately excludes
    username (it's the login identifier) and country (activation fees,
    plan pricing, and payout currency all key off it) — changing either
    has knock-on effects elsewhere that a simple profile edit shouldn't
    trigger. Email/phone are safe to self-serve.
    """

    class Meta:
        model = User
        fields = ["email", "phone_number"]

    def validate_phone_number(self, value):
        if User.objects.exclude(pk=self.instance.pk).filter(phone_number=value).exists():
            raise serializers.ValidationError("That phone number is already in use.")
        return value

    def validate_email(self, value):
        if User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
            raise serializers.ValidationError("That email is already in use.")
        return value