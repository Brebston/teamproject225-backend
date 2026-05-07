from datetime import datetime

from django.shortcuts import render
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from rest_framework import viewsets, permissions, serializers, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from users.api.v1.permissions import IsNotBlocked, IsOwnerOrStaff
from users.models import User
from profiles.models import Profile
from .models import AvailabilitySlot, Appointment
from .serializers import (
    AvailabilitySlotSerializer,
    AvailabilitySlotBulkCreateSerializer,
    AppointmentCreateSerializer,
    AppointmentUserViewSerializer,
    AppointmentSpecialistViewSerializer,
    AppointmentAdminSerializer,
    AppointmentRescheduleSerializer,
    AppointmentCancelSerializer,
    CompletedAppointmentSpecialistSerializer,
    CompletedAppointmentUserSerializer,
)
from .services import mark_past_appointments_completed

ADMIN_ROLES = [User.Roles.ADMIN, User.Roles.MODERATOR]


class AvailabilitySlotViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /slots/              — public; returns all future unbooked slots
                                (filtered by ?specialist=<id> for calendar display)
    POST /slots/bulk_create/  — specialist only; create many slots at once
    DELETE /slots/<id>/       — specialist only (owner); delete an unbooked slot
    """

    def get_permissions(self):
        if self.action == "list":
            return [IsNotBlocked()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsNotBlocked(), IsOwnerOrStaff()]
        return [permissions.IsAuthenticated(), IsNotBlocked()]

    def get_queryset(self):
        qs = AvailabilitySlot.objects.select_related("specialist")
        specialist_id = self.request.query_params.get("specialist")
        if specialist_id:
            qs = qs.filter(specialist_id=specialist_id)

        user = self.request.user
        if user.is_authenticated and user.role in ADMIN_ROLES:
            return qs  # admins see everything
        if user.is_authenticated and user.role == User.Roles.SPECIALIST:
            # Specialist sees their own (all) + others' unbooked future slots
            from django.db.models import Q
            from django.utils import timezone
            return qs.filter(
                Q(specialist__user=user) |
                Q(is_booked=False, start_time__gte=timezone.now())
            )
        # Anonymous / regular users: only future unbooked
        from django.utils import timezone
        return qs.filter(is_booked=False, start_time__gte=timezone.now())

    def get_serializer_class(self):
        return AvailabilitySlotSerializer

    def destroy(self, request, *args, **kwargs):
        slot = self.get_object()
        if slot.is_booked:
            return Response(
                {"detail": "Cannot delete a booked slot."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="bulk_create")
    def bulk_create(self, request):
        user = request.user
        if not user.is_authenticated or user.role != User.Roles.SPECIALIST:
            return Response(status=status.HTTP_403_FORBIDDEN)
        specialist = getattr(user, "specialist_profile", None)
        if specialist is None:
            return Response(
                {"detail": "You need a specialist profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not specialist.is_verified:
            raise serializers.ValidationError(
                {"detail": "Your specialist profile must be verified before creating slots."}
            )
        serializer = AvailabilitySlotBulkCreateSerializer(
            data=request.data,
            context={"specialist": specialist, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        slots = serializer.save()
        out = AvailabilitySlotSerializer(slots, many=True)
        return Response(out.data, status=status.HTTP_201_CREATED)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="user",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Filter appointments by user_profile ID (specialists & admins only)",
        ),
        OpenApiParameter(
            name="sort_field",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Field to sort by. Allowed: date",
            enum=["date"],
        ),
        OpenApiParameter(
            name="sort_direction",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Sort direction: asc (default) or desc",
            enum=["asc", "desc"],
        ),
        OpenApiParameter(
            name="date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter appointments by date (YYYY-MM-DD)",
            examples=[
                OpenApiExample(
                    "Example",
                    value="2026-06-10",
                )
            ],
        ),
    ]
)
class AppointmentViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,  # no UpdateModelMixin — actions handle it explicitly
):

    def get_permissions(self):
        if self.action in ("reschedule", "cancel"):
            return [permissions.IsAuthenticated(), IsNotBlocked(), IsOwnerOrStaff()]
        return [permissions.IsAuthenticated(), IsNotBlocked()]

    def _get_scoped_queryset(self):
        """Returns all appointments scoped to the current user, without status filtering."""
        user = self.request.user
        qs = Appointment.objects.select_related(
            "slot", "specialist", "user_profile", "cancelled_by"
        )

        if user.role in ADMIN_ROLES:
            return qs
        if user.role == User.Roles.SPECIALIST:
            qs = qs.filter(specialist__user=user)

            # Optional filtering by user profile
            user_filter = self.request.query_params.get("user")
            if user_filter:
                qs = qs.filter(user_profile_id=user_filter)

            return qs

        return qs.filter(user_profile__user=user)

    def _apply_sorting(self, qs, default_direction="asc"):
        sort_field = self.request.query_params.get("sort_field", "date")
        sort_direction = self.request.query_params.get("sort_direction", default_direction)

        allowed_fields = {"date": "slot__start_time"}
        orm_field = allowed_fields.get(sort_field, "slot__start_time")

        if sort_direction == "desc":
            orm_field = f"-{orm_field}"

        return qs.order_by(orm_field)

    def _apply_date_filter(self, qs):
        date_str = self.request.query_params.get("date")
        if not date_str:
            return qs
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return qs  # silently ignore invalid date

        return qs.filter(slot__start_time__date=date)

    def get_queryset(self):
        scoped = self._get_scoped_queryset()
        mark_past_appointments_completed(scoped)
        if self.request.user.role in ADMIN_ROLES:
            return scoped
        if self.action in ("reschedule", "cancel"):
            return scoped
        confirmed = scoped.filter(status=Appointment.Status.CONFIRMED)
        confirmed = self._apply_date_filter(confirmed)
        return self._apply_sorting(confirmed)

    def get_serializer_class(self):
        user = self.request.user

        action_map = {
            "create": AppointmentCreateSerializer,
            "reschedule": AppointmentRescheduleSerializer,
            "cancel": AppointmentCancelSerializer,
        }
        if self.action in action_map:
            return action_map[self.action]

        if self.action == "completed":
            return (
                CompletedAppointmentSpecialistSerializer
                if user.role == User.Roles.SPECIALIST
                else CompletedAppointmentUserSerializer
            )

        role_map = {
            User.Roles.ADMIN: AppointmentAdminSerializer,
            User.Roles.MODERATOR: AppointmentAdminSerializer,
            User.Roles.SPECIALIST: AppointmentSpecialistViewSerializer,
        }
        return role_map.get(user.role, AppointmentUserViewSerializer)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != User.Roles.USER:
            raise serializers.ValidationError(
                {"detail": "Only regular users can book appointments."}
            )
        profile = getattr(user, "profile", None)
        if profile is None:
            raise serializers.ValidationError(
                {"detail": "You need a user profile to book appointments."}
            )
        serializer.save(user_profile=profile)

    @action(detail=True, methods=["patch"], url_path="reschedule")
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status == Appointment.Status.CANCELLED:
            return Response(
                {"detail": "Cannot reschedule a cancelled appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            appointment, data=request.data, partial=False
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AppointmentSpecialistViewSerializer(appointment).data)

    @action(detail=True, methods=["patch"], url_path="cancel")
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status == Appointment.Status.CANCELLED:
            return Response(
                {"detail": "Appointment is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(
            appointment, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AppointmentSpecialistViewSerializer(appointment).data)

    @action(detail=False, methods=["get"], url_path="completed")
    def completed(self, request):
        scoped = self._get_scoped_queryset()
        mark_past_appointments_completed(scoped)
        completed_qs = scoped.filter(status=Appointment.Status.COMPLETED)
        completed_qs = self._apply_date_filter(completed_qs)
        completed_qs = self._apply_sorting(completed_qs, default_direction="desc")

        serializer = self.get_serializer(completed_qs, many=True)

        return Response(serializer.data)
