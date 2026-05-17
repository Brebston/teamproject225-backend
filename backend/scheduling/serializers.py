from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import AvailabilitySlot, Appointment


# ── Availability slots ────────────────────────────────────────────────────────

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    """Read-only: used for calendar display (users + specialists viewing slots)."""

    class Meta:
        model = AvailabilitySlot
        fields = ["id", "start_time", "end_time", "is_booked"]


class AvailabilitySlotBulkCreateSerializer(serializers.Serializer):
    """Specialist creates multiple slots at once."""

    start_times = serializers.ListField(
        child=serializers.DateTimeField(),
        min_length=1,
        max_length=100,
    )

    def validate_start_times(self, values):
        now = timezone.now()
        errors = []
        for dt in values:
            if dt < now:
                errors.append(f"{dt} is in the past.")
            if dt.minute not in (0, 30) or dt.second != 0:
                errors.append(f"{dt} does not start on the hour or half-hour.")
        if errors:
            raise serializers.ValidationError(errors)
        if len(values) != len(set(values)):
            raise serializers.ValidationError("Duplicate start times are not allowed.")
        return values

    def create(self, validated_data):
        from datetime import timedelta
        specialist = self.context["specialist"]
        slots = [
            AvailabilitySlot(
                specialist=specialist,
                start_time=dt,
                end_time=dt + timedelta(hours=1),
            )
            for dt in validated_data["start_times"]
        ]

        AvailabilitySlot.objects.bulk_create(slots, ignore_conflicts=True)
        return AvailabilitySlot.objects.filter(
            specialist=specialist,
            start_time__in= validated_data["start_times"],
        ).order_by("start_time")

# ── Appointments ──────────────────────────────────────────────────────────────

class AppointmentCreateSerializer(serializers.ModelSerializer):
    """User books a slot by providing its ID."""

    slot = serializers.PrimaryKeyRelatedField(
        queryset=AvailabilitySlot.objects.filter(is_booked=False)
    )

    class Meta:
        model = Appointment
        fields = ["id", "slot"]

    def validate_slot(self, slot):
        if slot.is_booked:
            raise serializers.ValidationError("This slot is already booked.")
        if slot.start_time < timezone.now():
            raise serializers.ValidationError("This slot is in the past.")
        return slot

    def create(self, validated_data):
        with transaction.atomic():
            slot = (
                AvailabilitySlot.objects
                .select_for_update()
                .get(pk=validated_data["slot"].pk)
            )

            if slot.is_booked:
                raise serializers.ValidationError("This slot is already booked.")

            appointment = Appointment.objects.create(
                specialist=slot.specialist,
                slot=slot,
                user_profile=validated_data["user_profile"],
            )
            slot.is_booked = True
            slot.save(update_fields=["is_booked"])
        return appointment


class AppointmentUserViewSerializer(serializers.ModelSerializer):
    """What a user sees in their cabinet."""

    specialist_name = serializers.CharField(
        source="specialist.__str__", read_only=True
    )
    start_time = serializers.DateTimeField(source="slot.start_time", read_only=True)
    end_time = serializers.DateTimeField(source="slot.end_time",   read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "specialist_name", "start_time", "end_time",
            "status", "created_at",
        ]
        read_only_fields = fields  # users can only view, not edit


class CompletedAppointmentUserSerializer(serializers.ModelSerializer):
    """
    Completed appointment as seen by the user.
    Includes specialist_id so the frontend can build the
    'book again' link: GET /api/v1/scheduling/slots/?specialist=<specialist_id>
    """

    specialist_name = serializers.CharField(
        source="specialist.__str__", read_only=True
    )
    specialist_id = serializers.IntegerField(
        source="specialist.id", read_only=True
    )
    start_time = serializers.DateTimeField(source="slot.start_time", read_only=True)
    end_time = serializers.DateTimeField(source="slot.end_time", read_only=True)
    # Convenience field so the frontend doesn't have to construct the URL itself
    book_again_url = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id", "specialist_name", "specialist_id",
            "start_time", "end_time", "status", "created_at",
            "book_again_url",
        ]
        read_only_fields = fields

    def get_book_again_url(self, obj):
        return f"/api/v1/scheduling/slots/?specialist={obj.specialist.id}"


class AppointmentSpecialistViewSerializer(serializers.ModelSerializer):
    """What a specialist sees in their cabinet — read only."""

    user_name = serializers.CharField(source="user_profile.__str__", read_only=True)
    start_time = serializers.DateTimeField(source="slot.start_time", read_only=True)
    end_time = serializers.DateTimeField(source="slot.end_time",   read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "user_name", "start_time", "end_time",
            "status", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CompletedAppointmentSpecialistSerializer(serializers.ModelSerializer):
    """
    Completed appointment as seen by the specialist.
    Read-only history view — no actions available.
    """

    user_name = serializers.CharField(source="user_profile.__str__", read_only=True)
    start_time = serializers.DateTimeField(source="slot.start_time", read_only=True)
    end_time = serializers.DateTimeField(source="slot.end_time", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "user_name", "start_time", "end_time",
            "status", "created_at", "updated_at",
        ]
        read_only_fields = fields


class AppointmentRescheduleSerializer(serializers.ModelSerializer):
    """Specialist reschedules an appointment to one of their own free slots."""

    slot = serializers.PrimaryKeyRelatedField(
        queryset=AvailabilitySlot.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request:
            return

        from django.db.models import Q
        user = request.user
        qs = AvailabilitySlot.objects.filter(is_booked=False)

        if hasattr(user, "specialist_profile"):
            qs = qs.filter(specialist=user.specialist_profile)

        self.fields["slot"].queryset = qs

    class Meta:
        model = Appointment
        fields = ["slot"]

    def update(self, instance, validated_data):
        new_slot = validated_data["slot"]
        with transaction.atomic():
            instance.slot.is_booked = False
            instance.slot.save(update_fields=["is_booked"])
            new_slot.is_booked = True
            new_slot.save(update_fields=["is_booked"])
            instance.slot = new_slot
            instance.save(update_fields=["slot"])
        return instance


class AppointmentCancelSerializer(serializers.ModelSerializer):
    """Specialist cancels an appointment."""

    class Meta:
        model = Appointment
        fields = ["status"]

    def validate_status(self, value):
        if value != Appointment.Status.CANCELLED:
            raise serializers.ValidationError(
                "This endpoint only accepts 'cancelled'."
            )
        return value

    def update(self, instance, validated_data):
        request = self.context.get("request")
        with transaction.atomic():
            instance.slot.is_booked = False
            instance.slot.save(update_fields=["is_booked"])
            instance.status = Appointment.Status.CANCELLED
            instance.cancelled_by = request.user
            instance.cancelled_at = timezone.now()
            instance.save(update_fields=["status", "cancelled_by", "cancelled_at"])
            return instance


class AppointmentAdminSerializer(serializers.ModelSerializer):
    """Full read access for moderators/admins."""

    specialist_name = serializers.CharField(source="specialist.__str__", read_only=True)
    user_name = serializers.CharField(source="user_profile.__str__", read_only=True)
    start_time = serializers.DateTimeField(source="slot.start_time", read_only=True)
    end_time = serializers.DateTimeField(source="slot.end_time",   read_only=True)
    cancelled_by_email = serializers.EmailField(
        source="cancelled_by.email", read_only=True, default=None
    )

    class Meta:
        model = Appointment
        fields = "__all__"
