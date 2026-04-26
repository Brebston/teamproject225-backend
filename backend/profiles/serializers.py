from django.utils import timezone
from rest_framework import serializers
from .models import Profile, SpecialistProfile, Document


# ─── Document ──────────────────────────────────────────────────────────────────

class DocumentSerializer(serializers.ModelSerializer):
    specialist_email = serializers.EmailField(
        source="specialist.user.email", read_only=True
    )

    class Meta:
        model = Document
        fields = ["id", "specialist_email", "file", "status", "created_at"]
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


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileCreateSerializer(serializers.ModelSerializer):
    """POST /profiles/ — full validation + consent required"""
    email = serializers.EmailField(source="user.email", read_only=True)
    accept_data_processing_consent = serializers.BooleanField(write_only=True)

    class Meta:
        model = Profile
        fields = [
            "first_name", "last_name", "email", "phone", "city",
            "birth_date", "gender", "education", "education_other",
            "cares_for_children", "avatar", "bio",
            "accept_data_processing_consent",
        ]

    def validate(self, attrs):
        # Consent is mandatory on creation
        if not attrs.get("accept_data_processing_consent"):
            raise serializers.ValidationError({
                "accept_data_processing_consent": "You must accept data processing consent."
            })

        # education_other logic
        education = attrs.get("education")
        education_other = attrs.get("education_other")

        if education == Profile.Education.OTHER and not education_other:
            raise serializers.ValidationError({
                "education_other": "Please specify your education."
            })
        if education != Profile.Education.OTHER and education_other:
            raise serializers.ValidationError({
                "education_other": "Must be empty unless education is 'Other'."
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop("accept_data_processing_consent")
        profile = super().create(validated_data)
        profile.data_processing_consent_accepted_at = timezone.now()
        profile.save(update_fields=["data_processing_consent_accepted_at"])
        return profile


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """PATCH /profiles/<id>/ — no consent, all fields optional"""

    class Meta:
        model = Profile
        fields = [
            "first_name", "last_name", "phone", "city",
            "birth_date", "gender", "education", "education_other",
            "cares_for_children", "avatar", "bio",
        ]

    def validate(self, attrs):
        # Still need education_other logic on updates
        education = attrs.get("education", getattr(self.instance, "education", None))
        education_other = attrs.get("education_other", getattr(
            self.instance, "education_other", None
        ))

        if education == Profile.Education.OTHER and not education_other:
            raise serializers.ValidationError({
                "education_other": "Please specify your education."
            })
        if education != Profile.Education.OTHER and education_other:
            raise serializers.ValidationError({
                "education_other": "Must be empty unless education is 'Other'."
            })

        return attrs


class ProfileListSerializer(serializers.ModelSerializer):
    """GET /profiles/ — minimal public info"""
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = ["id", "first_name", "last_name", "email", "avatar"]


class ProfileDetailSerializer(serializers.ModelSerializer):
    """GET /profiles/<id>/ — full read-only detail"""
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id", "first_name", "last_name", "email", "phone", "city",
            "birth_date", "gender", "education", "education_other",
            "cares_for_children", "avatar", "bio",
            "created_at", "updated_at", "data_processing_consent_accepted_at",
        ]
        read_only_fields = fields


# ─── Specialist Profile ────────────────────────────────────────────────────────

class SpecialistProfileCreateSerializer(serializers.ModelSerializer):
    """POST /specialist-profiles/ — consent required"""
    accept_data_processing_consent = serializers.BooleanField(write_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            "first_name", "last_name", "avatar", "phone", "city",
            "specialisation", "education", "experience", "bio",
            "accept_data_processing_consent",
        ]

    def validate(self, attrs):
        if not attrs.get("accept_data_processing_consent"):
            raise serializers.ValidationError({
                "accept_data_processing_consent": "You must accept data processing consent."
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop("accept_data_processing_consent")
        profile = super().create(validated_data)
        profile.data_processing_consent_accepted_at = timezone.now()
        profile.save(update_fields=["data_processing_consent_accepted_at"])
        return profile


class SpecialistProfileUpdateSerializer(serializers.ModelSerializer):
    """PATCH /specialist-profiles/<id>/ — no consent"""

    class Meta:
        model = SpecialistProfile
        fields = [
            "first_name", "last_name", "avatar", "phone", "city",
            "specialisation", "education", "experience", "bio",
        ]


class SpecialistProfileListSerializer(serializers.ModelSerializer):
    """GET /specialist-profiles/ — public card"""

    class Meta:
        model = SpecialistProfile
        fields = ["id", "first_name", "last_name", "avatar", "specialisation"]


class SpecialistProfileDetailSerializer(serializers.ModelSerializer):
    """GET /specialist-profiles/<id>/ — full public detail"""
    user_email = serializers.EmailField(source="user.email", read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            "id", "user_email", "first_name", "last_name", "avatar",
            "phone", "city", "specialisation", "education", "experience",
            "bio", "is_verified", "documents", "data_processing_consent_accepted_at",
        ]
        read_only_fields = fields


class SpecialistProfileModeratorSerializer(serializers.ModelSerializer):
    """PATCH /specialist-profiles/<id>/verify/ — only is_verified writable"""
    user_email = serializers.EmailField(source="user.email", read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            "id", "user_email", "first_name", "last_name", "avatar",
            "phone", "city", "specialisation", "education", "experience",
            "bio", "is_verified", "documents", "data_processing_consent_accepted_at",
        ]
        read_only_fields = [
            "id", "user_email", "first_name", "last_name", "avatar",
            "phone", "city", "specialisation", "education", "experience",
            "bio", "documents", "data_processing_consent_accepted_at",
        ]
