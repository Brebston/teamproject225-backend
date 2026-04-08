from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "role"]


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email"]


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Roles.choices)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class EmailTokenObtainSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        data = super().validate(attrs)

        if self.user.is_blocked:
            raise AuthenticationFailed("User is blocked")

        return data
