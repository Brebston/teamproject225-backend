from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from users.models import User

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "role"]


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "role"]


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Roles.choices)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    role = serializers.ChoiceField(
        choices=[
            (User.Roles.USER, "User"),
            (User.Roles.SPECIALIST, "Specialist"),
        ]
    )

    class Meta:
        model = User
        fields = ["email", "password", "role"]

    def validate(self, data):
        user = User(email=data["email"], role=data["role"])
        try:
            validate_password(data["password"], user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class EmailTokenObtainSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        data = super().validate(attrs)

        if self.user.is_blocked:
            raise AuthenticationFailed("User is blocked")

        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )

        try:
            user_id = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError({"token": "Invalid reset link"})

        token_is_valid = PasswordResetTokenGenerator().check_token(
            user,
            data["token"],
        )

        if not token_is_valid:
            raise serializers.ValidationError(
                {"token": "Invalid or expired token"}
            )

        try:
            validate_password(data["password"], user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        data["user"] = user

        return data
