from rest_framework import serializers

from .models import WheelSpin


class WheelSpinSerializer(serializers.ModelSerializer):
    class Meta:
        model = WheelSpin
        fields = ["id", "date", "credited_amount", "currency_code", "created_at"]