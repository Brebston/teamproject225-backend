import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from profiles.models import Document, Profile, SpecialistProfile
from conftest import (
    make_admin,
    make_client_for,
    make_moderator,
    make_profile,
    make_specialist,
    make_specialist_profile,
    make_user,
)


PROFILES_URL = "/api/v1/profiles/user-profiles/"
SPECIALIST_PROFILES_URL = "/api/v1/profiles/specialist-profiles/"
DOCUMENTS_URL = "/api/v1/profiles/documents/"

VALID_PROFILE_PAYLOAD = {
    "first_name": "Jane",
    "last_name": "Doe",
    "phone": "+380991234567",
    "city": "Kyiv",
    "birth_date": "1990-05-15",
    "gender": "female",
    "education": "other",
    "education_other": "Social Worker",
    "cares_for_children": False,
    "accept_data_processing_consent": True,
}

VALID_SPECIALIST_PAYLOAD = {
    "first_name": "John",
    "last_name": "Smith",
    "phone": "+380991234568",
    "city": "Lviv",
    "specialisation": "CBT Therapy",
    "education": "Master of Psychology",
    "experience": "7 years of clinical practice",
    "accept_data_processing_consent": True,
}


def _make_image_file(name="test.jpg"):
    """Return a SimpleUploadedFile containing a tiny JPEG."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


def _create_document(specialist_profile, status_val=Document.DocumentStatus.PENDING):
    return Document.objects.create(
        specialist=specialist_profile,
        file=_make_image_file(),
        status=status_val,
    )


# ==============================================================================
# Profile ViewSet Tests
# ==============================================================================


@pytest.mark.django_db
class TestProfileCreate:
    def test_user_can_create_profile(self, user_client):
        resp = user_client.client.post(PROFILES_URL, VALID_PROFILE_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Profile.objects.filter(user=user_client.user).exists()

    def test_profile_stores_consent_timestamp(self, user_client):
        user_client.client.post(PROFILES_URL, VALID_PROFILE_PAYLOAD, format="json")
        profile = Profile.objects.get(user=user_client.user)
        assert profile.data_processing_consent_accepted_at is not None

    def test_create_fails_without_consent(self, user_client):
        payload = {**VALID_PROFILE_PAYLOAD, "accept_data_processing_consent": False}
        resp = user_client.client.post(PROFILES_URL, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "accept_data_processing_consent" in resp.data

    def test_create_fails_education_other_missing(self, user_client):
        payload = {**VALID_PROFILE_PAYLOAD, "education": "other", "education_other": ""}
        resp = user_client.client.post(PROFILES_URL, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "education_other" in resp.data

    def test_create_fails_education_other_set_for_non_other(self, user_client):
        payload = {**VALID_PROFILE_PAYLOAD, "education": "psychologist", "education_other": "Something"}
        resp = user_client.client.post(PROFILES_URL, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "education_other" in resp.data

    def test_create_fails_if_profile_already_exists(self, user_with_profile):
        resp = user_with_profile.client.post(PROFILES_URL, VALID_PROFILE_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_specialist_cannot_create_user_profile(self, specialist_client):
        resp = specialist_client.client.post(PROFILES_URL, VALID_PROFILE_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_cannot_create_profile(self, anon_client):
        resp = anon_client.post(PROFILES_URL, VALID_PROFILE_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProfileRetrieve:
    def test_user_can_retrieve_own_profile(self, user_with_profile):
        resp = user_with_profile.client.get(f"{PROFILES_URL}{user_with_profile.profile.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["first_name"] == user_with_profile.profile.first_name

    def test_user_cannot_retrieve_another_users_profile(self, user_client):
        other_profile = make_profile(make_user(email="other@test.com"))
        resp = user_client.client.get(f"{PROFILES_URL}{other_profile.id}/")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_any_profile(self, admin_client):
        other_profile = make_profile(make_user(email="other@test.com"))
        resp = admin_client.client.get(f"{PROFILES_URL}{other_profile.id}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_moderator_can_retrieve_any_profile(self, moderator_client):
        other_profile = make_profile(make_user(email="other@test.com"))
        resp = moderator_client.client.get(f"{PROFILES_URL}{other_profile.id}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_detail_response_includes_expected_fields(self, user_with_profile):
        resp = user_with_profile.client.get(f"{PROFILES_URL}{user_with_profile.profile.id}/")
        for field in ("id", "first_name", "last_name", "email", "phone", "city", "birth_date"):
            assert field in resp.data


@pytest.mark.django_db
class TestProfileList:
    def test_user_sees_only_own_profile_in_list(self, user_with_profile):
        make_profile(make_user(email="other@test.com"))
        resp = user_with_profile.client.get(PROFILES_URL)
        assert resp.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in resp.data["results"]]
        assert user_with_profile.profile.id in ids
        assert len(ids) == 1

    def test_admin_sees_all_profiles(self, admin_client):
        make_profile(make_user(email="u1@test.com"))
        make_profile(make_user(email="u2@test.com"))
        resp = admin_client.client.get(PROFILES_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) >= 2

    def test_list_returns_minimal_fields(self, user_with_profile):
        resp = user_with_profile.client.get(PROFILES_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data["results"][0].keys()) == {"id", "first_name", "last_name", "email", "avatar"}


@pytest.mark.django_db
class TestProfileUpdate:
    def test_user_can_update_own_profile(self, user_with_profile):
        resp = user_with_profile.client.patch(
            f"{PROFILES_URL}{user_with_profile.profile.id}/",
            {"first_name": "Updated"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        user_with_profile.profile.refresh_from_db()
        assert user_with_profile.profile.first_name == "Updated"

    def test_user_cannot_update_another_users_profile(self, user_with_profile):
        other_profile = make_profile(make_user(email="other@test.com"))
        resp = user_with_profile.client.patch(
            f"{PROFILES_URL}{other_profile.id}/",
            {"first_name": "Hacked"},
            format="json",
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_update_education_other_validation_on_patch(self, user_with_profile):
        resp = user_with_profile.client.patch(
            f"{PROFILES_URL}{user_with_profile.profile.id}/",
            {"education": "psychologist", "education_other": "Something"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "education_other" in resp.data

    def test_admin_can_update_any_profile(self, admin_client):
        other_profile = make_profile(make_user(email="other@test.com"))
        resp = admin_client.client.patch(
            f"{PROFILES_URL}{other_profile.id}/",
            {"city": "Odesa"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProfileDelete:
    def test_user_can_delete_own_profile(self, user_with_profile):
        resp = user_with_profile.client.delete(f"{PROFILES_URL}{user_with_profile.profile.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Profile.objects.filter(id=user_with_profile.profile.id).exists()

    def test_user_cannot_delete_another_users_profile(self, user_with_profile):
        other_profile = make_profile(make_user(email="other@test.com"))
        resp = user_with_profile.client.delete(f"{PROFILES_URL}{other_profile.id}/")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_any_profile(self, admin_client):
        other_profile = make_profile(make_user(email="other@test.com"))
        resp = admin_client.client.delete(f"{PROFILES_URL}{other_profile.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# ==============================================================================
# SpecialistProfile ViewSet Tests
# ==============================================================================


@pytest.mark.django_db
class TestSpecialistProfileCreate:
    def test_specialist_can_create_profile(self, specialist_client):
        resp = specialist_client.client.post(SPECIALIST_PROFILES_URL, VALID_SPECIALIST_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert SpecialistProfile.objects.filter(user=specialist_client.user).exists()

    def test_new_specialist_profile_is_unverified(self, specialist_client):
        specialist_client.client.post(SPECIALIST_PROFILES_URL, VALID_SPECIALIST_PAYLOAD, format="json")
        profile = SpecialistProfile.objects.get(user=specialist_client.user)
        assert profile.is_verified is False

    def test_specialist_profile_stores_consent_timestamp(self, specialist_client):
        specialist_client.client.post(SPECIALIST_PROFILES_URL, VALID_SPECIALIST_PAYLOAD, format="json")
        profile = SpecialistProfile.objects.get(user=specialist_client.user)
        assert profile.data_processing_consent_accepted_at is not None

    def test_create_fails_without_consent(self, specialist_client):
        payload = {**VALID_SPECIALIST_PAYLOAD, "accept_data_processing_consent": False}
        resp = specialist_client.client.post(SPECIALIST_PROFILES_URL, payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_regular_user_cannot_create_specialist_profile(self, user_client):
        resp = user_client.client.post(SPECIALIST_PROFILES_URL, VALID_SPECIALIST_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_specialist_profile_rejected(self, specialist_with_profile):
        resp = specialist_with_profile.client.post(SPECIALIST_PROFILES_URL, VALID_SPECIALIST_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_cannot_create_specialist_profile(self, anon_client):
        resp = anon_client.post(SPECIALIST_PROFILES_URL, VALID_SPECIALIST_PAYLOAD, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSpecialistProfileRetrieve:
    def test_anyone_can_retrieve_verified_specialist(self, verified_specialist, anon_client):
        resp = anon_client.get(f"{SPECIALIST_PROFILES_URL}{verified_specialist.profile.id}/")
        assert resp.status_code == status.HTTP_200_OK

    def test_owner_can_retrieve_own_unverified_profile(self, specialist_with_profile):
        resp = specialist_with_profile.client.get(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/"
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_other_user_cannot_retrieve_unverified_specialist(self, user_client, specialist_with_profile):
        resp = user_client.client.get(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/"
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_unverified_specialist(self, admin_client, specialist_with_profile):
        resp = admin_client.client.get(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/"
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_detail_includes_documents_field(self, specialist_with_profile):
        resp = specialist_with_profile.client.get(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/"
        )
        assert "documents" in resp.data

    def test_moderator_serializer_includes_is_verified(self, moderator_client, specialist_with_profile):
        resp = moderator_client.client.get(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "is_verified" in resp.data


@pytest.mark.django_db
class TestSpecialistProfileList:
    def test_unauthenticated_sees_only_verified_specialists(self, verified_specialist, specialist_with_profile):
        resp = APIClient().get(SPECIALIST_PROFILES_URL)
        ids = [s["id"] for s in resp.data["results"]]
        assert verified_specialist.profile.id in ids
        assert specialist_with_profile.profile.id not in ids

    def test_specialist_sees_own_unverified_profile_in_list(self, specialist_with_profile):
        resp = specialist_with_profile.client.get(SPECIALIST_PROFILES_URL)
        ids = [s["id"] for s in resp.data["results"]]
        assert specialist_with_profile.profile.id in ids

    def test_admin_sees_all_specialist_profiles(self, admin_client, verified_specialist, specialist_with_profile):
        resp = admin_client.client.get(SPECIALIST_PROFILES_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) >= 2

    def test_list_returns_card_fields(self, verified_specialist):
        resp = APIClient().get(SPECIALIST_PROFILES_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data["results"][0].keys()) == {
            "id", "first_name", "last_name", "avatar", "specialisation"
        }


@pytest.mark.django_db
class TestSpecialistProfileUpdate:
    def test_owner_can_update_own_profile(self, specialist_with_profile):
        resp = specialist_with_profile.client.patch(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/",
            {"city": "Odesa"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        specialist_with_profile.profile.refresh_from_db()
        assert specialist_with_profile.profile.city == "Odesa"

    def test_other_specialist_cannot_update_profile(self, specialist_with_profile):
        other_user = make_specialist(email="other@test.com")
        other_client = make_client_for(other_user)
        resp = other_client.patch(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/",
            {"city": "Hacked"},
            format="json",
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_admin_can_update_specialist_profile(self, admin_client, specialist_with_profile):
        resp = admin_client.client.patch(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/",
            {"city": "Kharkiv"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_owner_cannot_set_is_verified(self, specialist_with_profile):
        specialist_with_profile.client.patch(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/",
            {"is_verified": True},
            format="json",
        )
        specialist_with_profile.profile.refresh_from_db()
        assert specialist_with_profile.profile.is_verified is False


@pytest.mark.django_db
class TestSpecialistProfileVerify:
    def test_moderator_can_verify_specialist(self, moderator_client, specialist_with_profile):
        resp = moderator_client.client.patch(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/",
            {"is_verified": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        specialist_with_profile.profile.refresh_from_db()
        assert specialist_with_profile.profile.is_verified is True

    def test_moderator_can_revoke_verification(self, moderator_client, verified_specialist):
        resp = moderator_client.client.patch(
            f"{SPECIALIST_PROFILES_URL}{verified_specialist.profile.id}/",
            {"is_verified": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        verified_specialist.profile.refresh_from_db()
        assert verified_specialist.profile.is_verified is False


@pytest.mark.django_db
class TestSpecialistProfileDelete:
    def test_owner_can_delete_own_profile(self, specialist_with_profile):
        profile_id = specialist_with_profile.profile.id
        resp = specialist_with_profile.client.delete(f"{SPECIALIST_PROFILES_URL}{profile_id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not SpecialistProfile.objects.filter(id=profile_id).exists()

    def test_other_user_cannot_delete_specialist_profile(self, specialist_with_profile, user_client):
        resp = user_client.client.delete(
            f"{SPECIALIST_PROFILES_URL}{specialist_with_profile.profile.id}/"
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_any_specialist_profile(self, admin_client, specialist_with_profile):
        profile_id = specialist_with_profile.profile.id
        resp = admin_client.client.delete(f"{SPECIALIST_PROFILES_URL}{profile_id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# ==============================================================================
# Document ViewSet Tests
# ==============================================================================


@pytest.mark.django_db
class TestDocumentCreate:
    def test_specialist_with_profile_can_upload_document(self, specialist_with_profile):
        resp = specialist_with_profile.client.post(
            DOCUMENTS_URL, {"file": _make_image_file()}, format="multipart"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert Document.objects.filter(specialist=specialist_with_profile.profile).exists()

    def test_new_document_has_pending_status(self, specialist_with_profile):
        specialist_with_profile.client.post(
            DOCUMENTS_URL, {"file": _make_image_file()}, format="multipart"
        )
        doc = Document.objects.get(specialist=specialist_with_profile.profile)
        assert doc.status == Document.DocumentStatus.PENDING

    def test_regular_user_cannot_upload_document(self, user_client):
        resp = user_client.client.post(
            DOCUMENTS_URL, {"file": _make_image_file()}, format="multipart"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_specialist_without_profile_cannot_upload(self, specialist_client):
        resp = specialist_client.client.post(
            DOCUMENTS_URL, {"file": _make_image_file()}, format="multipart"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDocumentList:
    def test_specialist_sees_only_own_documents(self, specialist_with_profile):
        other_user = make_specialist(email="other@test.com")
        other_profile = make_specialist_profile(other_user)
        doc = _create_document(specialist_with_profile.profile)
        _create_document(other_profile)
        resp = specialist_with_profile.client.get(DOCUMENTS_URL)
        assert resp.status_code == status.HTTP_200_OK
        ids = [d["id"] for d in resp.data["results"]]
        assert doc.id in ids
        assert len(ids) == 1

    def test_admin_sees_all_documents(self, admin_client, specialist_with_profile):
        other_user = make_specialist(email="other@test.com")
        other_profile = make_specialist_profile(other_user)
        _create_document(specialist_with_profile.profile)
        _create_document(other_profile)
        resp = admin_client.client.get(DOCUMENTS_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) >= 2


@pytest.mark.django_db
class TestDocumentModeration:
    def test_moderator_can_approve_document(self, moderator_client, specialist_with_profile):
        doc = _create_document(specialist_with_profile.profile)
        resp = moderator_client.client.patch(
            f"{DOCUMENTS_URL}{doc.id}/",
            {"status": Document.DocumentStatus.APPROVED},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.status == Document.DocumentStatus.APPROVED

    def test_moderator_can_reject_document(self, moderator_client, specialist_with_profile):
        doc = _create_document(specialist_with_profile.profile)
        resp = moderator_client.client.patch(
            f"{DOCUMENTS_URL}{doc.id}/",
            {"status": Document.DocumentStatus.REJECTED},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.status == Document.DocumentStatus.REJECTED

    def test_specialist_cannot_change_own_document_status(self, specialist_with_profile):
        doc = _create_document(specialist_with_profile.profile)
        specialist_with_profile.client.patch(
            f"{DOCUMENTS_URL}{doc.id}/",
            {"status": Document.DocumentStatus.APPROVED},
            format="json",
        )
        doc.refresh_from_db()
        assert doc.status == Document.DocumentStatus.PENDING

    def test_document_serializer_differs_for_moderator(self, moderator_client, specialist_with_profile):
        doc = _create_document(specialist_with_profile.profile)
        resp = moderator_client.client.get(f"{DOCUMENTS_URL}{doc.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert "specialist" in resp.data


@pytest.mark.django_db
class TestDocumentDelete:
    def test_owner_can_delete_own_document(self, specialist_with_profile):
        doc = _create_document(specialist_with_profile.profile)
        resp = specialist_with_profile.client.delete(f"{DOCUMENTS_URL}{doc.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_other_specialist_cannot_delete_document(self, specialist_with_profile):
        other_user = make_specialist(email="other@test.com")
        other_profile = make_specialist_profile(other_user)
        other_client = make_client_for(other_user)
        doc = _create_document(specialist_with_profile.profile)
        resp = other_client.delete(f"{DOCUMENTS_URL}{doc.id}/")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_admin_can_delete_any_document(self, admin_client, specialist_with_profile):
        doc = _create_document(specialist_with_profile.profile)
        resp = admin_client.client.delete(f"{DOCUMENTS_URL}{doc.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
