from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from profiles.models import Profile, SpecialistProfile

User = get_user_model()


# --- Factory helpers ---

def create_user(email="user@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_user(
        email=email,
        password=password,
        role=User.Roles.USER,
        **kwargs,
    )


def create_specialist(email="specialist@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_user(
        email=email,
        password=password,
        role=User.Roles.SPECIALIST,
        **kwargs,
    )


def create_moderator(email="moderator@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_user(
        email=email,
        password=password,
        role=User.Roles.MODERATOR,
        **kwargs,
    )


def create_admin(email="admin@test.com", password="TestPass123!", **kwargs) -> User:
    return User.objects.create_superuser(
        email=email,
        password=password,
        **kwargs,
    )


# --- Auth helpers ---

def get_tokens_for_user(user: User) -> dict:
    """Return JWT access + refresh tokens for a user without going through the API."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def get_authenticated_client(user: User) -> APIClient:
    """Return an APIClient already authenticated with the given user's JWT."""
    client = APIClient()
    tokens = get_tokens_for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


# --- Registration via API ---

def api_register(client: APIClient, email: str, password: str, role: str) -> dict:
    """
    POST /api/v1/users/register/ and return the response object.
    role must be one of: 'user', 'specialist'
    """
    return client.post(
        "/api/v1/users/register/",
        {
            "email": email,
            "password": password,
            "confirm_password": password,
            "role": role,
        },
        format="json",
    )


def api_login(client: APIClient, email: str, password: str) -> dict:
    """POST /api/v1/users/login/ and return the response object."""
    return client.post(
        "/api/v1/users/login/",
        {"email": email, "password": password},
        format="json",
    )


# --- Combined shortcuts ---

def register_and_login_user(
    email="user@test.com", password="TestPass123!"
) -> tuple[User, APIClient]:
    """Create a USER in the DB and return (user, authenticated_client)."""
    user = create_user(email=email, password=password)
    client = get_authenticated_client(user)
    return user, client


def register_and_login_specialist(
    email="specialist@test.com", password="TestPass123!"
) -> tuple[User, APIClient]:
    """Create a SPECIALIST in the DB and return (user, authenticated_client)."""
    user = create_specialist(email=email, password=password)
    client = get_authenticated_client(user)
    return user, client


def register_and_login_moderator(
    email="moderator@test.com", password="TestPass123!"
) -> tuple[User, APIClient]:
    """Create a MODERATOR in the DB and return (user, authenticated_client)."""
    user = create_moderator(email=email, password=password)
    client = get_authenticated_client(user)
    return user, client


def register_and_login_admin(
    email="admin@test.com", password="TestPass123!"
) -> tuple[User, APIClient]:
    """Create an ADMIN in the DB and return (user, authenticated_client)."""
    user = create_admin(email=email, password=password)
    client = get_authenticated_client(user)
    return user, client


# --- Profile factories ---

USER_PROFILE_DEFAULTS = {
    "first_name": "Test",
    "last_name": "User",
    "phone": "+380991234567",
    "city": "Kyiv",
    "birth_date": "1990-01-01",
    "gender": Profile.Gender.PREFER_NOT_TO_SAY,
    "education": Profile.Education.OTHER,
    "cares_for_children": False,
}

SPECIALIST_PROFILE_DEFAULTS = {
    "first_name": "Test",
    "last_name": "Specialist",
    "phone": "+380991234568",
    "city": "Kyiv",
    "specialisation": "Psychotherapy",
    "education": "Master of Psychology, Kyiv University",
    "experience": "5 years of clinical practice",
}


def create_profile(user: User, **kwargs) -> Profile:
    """Create a Profile for a USER-role account directly in the DB."""
    fields = {**USER_PROFILE_DEFAULTS, **kwargs}
    return Profile.objects.create(
        user=user,
        data_processing_consent_accepted_at=timezone.now(),
        **fields,
    )


def create_specialist_profile(user: User, verified: bool = False, **kwargs) -> SpecialistProfile:
    """Create a SpecialistProfile for a SPECIALIST-role account directly in the DB."""
    fields = {**SPECIALIST_PROFILE_DEFAULTS, **kwargs}
    return SpecialistProfile.objects.create(
        user=user,
        is_verified=verified,
        data_processing_consent_accepted_at=timezone.now(),
        **fields,
    )


# --- Combined profile shortcuts ---

def create_user_with_profile(
    email="user@test.com", password="TestPass123!", **profile_kwargs
) -> tuple[User, Profile, APIClient]:
    """
    Create a USER with a filled Profile.
    Returns (user, profile, authenticated_client).
    """
    user = create_user(email=email, password=password)
    profile = create_profile(user, **profile_kwargs)
    client = get_authenticated_client(user)
    return user, profile, client


def create_specialist_with_profile(
    email="specialist@test.com", password="TestPass123!", **profile_kwargs
) -> tuple[User, SpecialistProfile, APIClient]:
    """
    Create a SPECIALIST with an unverified SpecialistProfile.
    Returns (user, specialist_profile, authenticated_client).
    """
    user = create_specialist(email=email, password=password)
    profile = create_specialist_profile(user, verified=False, **profile_kwargs)
    client = get_authenticated_client(user)
    return user, profile, client


def create_verified_specialist_with_profile(
    email="verified@test.com", password="TestPass123!", **profile_kwargs
) -> tuple[User, SpecialistProfile, APIClient]:
    """
    Create a SPECIALIST with a verified SpecialistProfile.
    Returns (user, specialist_profile, authenticated_client).
    """
    user = create_specialist(email=email, password=password)
    profile = create_specialist_profile(user, verified=True, **profile_kwargs)
    client = get_authenticated_client(user)
    return user, profile, client
