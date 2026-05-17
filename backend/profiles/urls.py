from django.urls import path
from .views import (
    ProfileListCreateView,
    ProfileDetailView,
    SpecialistProfileListCreateView,
    SpecialistProfileDetailView,
    DocumentListCreateView,
    DocumentDetailView,
)

urlpatterns = [
    # Profiles
    path("", ProfileListCreateView.as_view(), name="profile-list-create"),
    path("<int:pk>/", ProfileDetailView.as_view(), name="profile-detail"),
    # Specialist Profiles
    path(
        "specialists/",
        SpecialistProfileListCreateView.as_view(),
        name="specialist-list-create",
    ),
    path(
        "specialists/<int:pk>/",
        SpecialistProfileDetailView.as_view(),
        name="specialist-detail",
    ),
    # Documents
    path(
        "documents/",
        DocumentListCreateView.as_view(),
        name="document-list-create"
    ),
    path(
        "documents/<int:pk>/",
        DocumentDetailView.as_view(),
        name="document-detail"
    ),
]
