import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from profiles.models import Profile, SpecialistProfile
from users.models import User


# ==============================================================================
# Plain functions, usable anywhere
# ==============================================================================

def make_user(email="user@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_user(
        email=email, password=password, role=User.Roles.USER, **kwargs
    )


def make_specialist(email="specialist@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_user(
        email=email, password=password, role=User.Roles.SPECIALIST, **kwargs
    )


def make_moderator(email="moderator@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_user(
        email=email, password=password, role=User.Roles.MODERATOR, **kwargs
    )


def make_admin(email="admin@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_superuser(email=email, password=password, **kwargs)


def make_client_for(user: User) -> APIClient:
    """Return an APIClient authenticated with a JWT for *user*."""
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


_PROFILE_DEFAULTS = {
    "first_name": "Test",
    "last_name": "User",
    "phone": "+380991234567",
    "city": "Kyiv",
    "birth_date": "1990-01-01",
    "gender": Profile.Gender.PREFER_NOT_TO_SAY,
    "education": Profile.Education.PSYCHOLOGIST,
    "cares_for_children": False,
}

_SPECIALIST_PROFILE_DEFAULTS = {
    "first_name": "Test",
    "last_name": "Specialist",
    "phone": "+380991234568",
    "city": "Kyiv",
    "specialisation": "Psychotherapy",
    "education": "Master of Psychology, Kyiv University",
    "experience": "5 years of clinical practice",
}


def make_profile(user: User, **kwargs) -> Profile:
    return Profile.objects.create(
        user=user,
        data_processing_consent_accepted_at=timezone.now(),
        **{**_PROFILE_DEFAULTS, **kwargs},
    )


def make_specialist_profile(user: User, verified: bool = False, **kwargs) -> SpecialistProfile:
    return SpecialistProfile.objects.create(
        user=user,
        is_verified=verified,
        data_processing_consent_accepted_at=timezone.now(),
        **{**_SPECIALIST_PROFILE_DEFAULTS, **kwargs},
    )


# ==============================================================================
# Pytest fixtures
#
# Naming convention:
#   user_*            — USER-role accounts
#   specialist_*      — SPECIALIST-role accounts
#   verified_*         — SPECIALIST account with a verified SpecialistProfile
#   unverified_*       — SPECIALIST account with an unverified SpecialistProfile
#   moderator_client  — authenticated moderator client
#   admin_client      — authenticated admin client
#   anon_client        — unauthenticated client
#
# Each fixture returns a simple namespace so tests can do:
#   def test_foo(user_with_profile):
#       user_with_profile.profile.first_name
#       user_with_profile.client.get(...)
# ==============================================================================

class _NS:
    """Tiny namespace so fixtures return attribute-accessible objects."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# --- plain authenticated clients ---

@pytest.fixture
def user_client(db):
    """Authenticated client for a fresh USER account (no profile)."""
    user = make_user()
    return _NS(user=user, client=make_client_for(user))


@pytest.fixture
def specialist_client(db):
    """Authenticated client for a fresh SPECIALIST account (no profile)."""
    user = make_specialist()
    return _NS(user=user, client=make_client_for(user))


@pytest.fixture
def moderator_client(db):
    """Authenticated client for a MODERATOR account."""
    user = make_moderator()
    return _NS(user=user, client=make_client_for(user))


@pytest.fixture
def admin_client(db):
    """Authenticated client for an ADMIN account."""
    user = make_admin()
    return _NS(user=user, client=make_client_for(user))


# --- user fixtures ---

@pytest.fixture
def user_with_profile(db):
    """USER account with a fully populated Profile."""
    user = make_user()
    profile = make_profile(user)
    return _NS(user=user, profile=profile, client=make_client_for(user))


@pytest.fixture
def user_without_profile(db):
    """USER account with no Profile."""
    user = make_user(email="noprofile@test.com")
    return _NS(user=user, client=make_client_for(user))

# --- specialist fixtures ---


@pytest.fixture
def specialist_with_profile(db):
    """SPECIALIST account with an *unverified* SpecialistProfile."""
    user = make_specialist()
    profile = make_specialist_profile(user, verified=False)
    return _NS(user=user, profile=profile, client=make_client_for(user))


@pytest.fixture
def unverified_specialist(db):
    """Alias for specialist_with_profile — prefer this name when
    the test is explicitly about the unverified state."""
    user = make_specialist(email="unverified@test.com")
    profile = make_specialist_profile(user, verified=False)
    return _NS(user=user, profile=profile, client=make_client_for(user))


@pytest.fixture
def verified_specialist(db):
    """SPECIALIST account with a *verified* SpecialistProfile."""
    user = make_specialist(email="verified@test.com")
    profile = make_specialist_profile(user, verified=True)
    return _NS(user=user, profile=profile, client=make_client_for(user))


# --- anonymous client (no credentials) ---

@pytest.fixture
def anon_client():
    """Unauthenticated APIClient."""
    return APIClient()
