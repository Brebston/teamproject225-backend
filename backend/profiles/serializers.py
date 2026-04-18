from rest_framework import serializers
from .models import Profile, SpecialistProfile, Document


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["id", "user", "first_name", "last_name", "avatar"]
        read_only_fields = ["user"]


class SpecialistProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            "id",
            "user_email",
            "first_name",
            "last_name",
            "avatar",
            "education",
            "experience",
            "specialisation",
            "is_verified",
        ]
        read_only_fields = ["is_verified"]  # controlled by admins/moderators


class DocumentSerializer(serializers.ModelSerializer):
    specialist = serializers.EmailField(
        source="specialist.user.email", read_only=True
    )

    class Meta:
        model = Document
        fields = ["id", "specialist", "file", "status", "created_at"]
        read_only_fields = ["status", "created_at"]


class DocumentModeratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "specialist", "file", "status", "created_at"]
        read_only_fields = [
            "specialist",
            "file",
            "created_at",
        ]  # only status is editable
