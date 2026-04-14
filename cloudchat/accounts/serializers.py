from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'dob']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
