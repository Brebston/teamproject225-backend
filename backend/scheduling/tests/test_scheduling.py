from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from scheduling.models import AvailabilitySlot, Appointment
from scheduling.tasks import delete_unbooked_past_slots
from conftest import (
    make_client_for,
    make_user,
    make_specialist,
    make_profile,
    make_specialist_profile,
)

SLOTS_URL = "/api/v1/scheduling/slots/"
SLOTS_BULK_URL = "/api/v1/scheduling/slots/bulk_create/"
APPOINTMENTS_URL = "/api/v1/scheduling/appointments/"
COMPLETED_URL = "/api/v1/scheduling/appointments/completed/"


# ==============================================================================
# Helpers
# ==============================================================================


def future_dt(hours_ahead: int = 24) -> str:
    """Return an ISO-8601 string snapped to the next :00 or :30, N hours ahead."""
    dt = timezone.now() + timedelta(hours=hours_ahead)
    minute = 0 if dt.minute < 30 else 30
    dt = dt.replace(minute=minute, second=0, microsecond=0)
    return dt.isoformat()


def make_slot(
    specialist_profile, hours_ahead: int = 24, days_ahead=None
) -> AvailabilitySlot:
    """Create an AvailabilitySlot directly in the DB, bypassing the API."""
    start = timezone.now()
    if days_ahead is not None:
        start += timedelta(days=days_ahead)
    else:
        start += timedelta(hours=hours_ahead)
    start = start.replace(minute=0, second=0, microsecond=0)
    return AvailabilitySlot.objects.create(
        specialist=specialist_profile,
        start_time=start,
        end_time=start + timedelta(hours=1),
    )


def make_past_slot(specialist_profile, hours_ago: int = 3) -> AvailabilitySlot:
    """Create a slot that has already ended (bypasses model.clean() via update)."""
    now = timezone.now()
    placeholder_start = now + timedelta(hours=24 + hours_ago)
    placeholder_start = placeholder_start.replace(
        minute=0, second=0, microsecond=0
    )
    slot = AvailabilitySlot.objects.create(
        specialist=specialist_profile,
        start_time=placeholder_start,
        end_time=placeholder_start + timedelta(hours=1),
        is_booked=True,
    )
    past_start = (now - timedelta(hours=hours_ago)).replace(
        minute=0, second=0, microsecond=0
    )
    AvailabilitySlot.objects.filter(pk=slot.pk).update(
        start_time=past_start,
        end_time=past_start + timedelta(hours=1),
    )
    slot.refresh_from_db()
    return slot


def make_future_slot(
    specialist_profile, hours_ahead: int = 24
) -> AvailabilitySlot:
    start = timezone.now() + timedelta(hours=hours_ahead)
    start = start.replace(minute=0, second=0, microsecond=0)
    return AvailabilitySlot.objects.create(
        specialist=specialist_profile,
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_booked=True,
    )


def make_appointment(
    slot, specialist, user_profile, status=Appointment.Status.CONFIRMED
) -> Appointment:
    return Appointment.objects.create(
        slot=slot,
        specialist=specialist,
        user_profile=user_profile,
        status=status,
    )


# ==============================================================================
# 1. Slot management — bulk create
# ==============================================================================


@pytest.mark.django_db
class TestSlotBulkCreate:
    def test_verified_specialist_can_bulk_create_slots(
        self, verified_specialist
    ):
        payload = {"start_times": [future_dt(24), future_dt(25)]}
        resp = verified_specialist.client.post(
            SLOTS_BULK_URL, payload, format="json"
        )
        assert resp.status_code == 201
        assert len(resp.data) == 2
        assert (
            AvailabilitySlot.objects.filter(
                specialist=verified_specialist.profile
            ).count()
            == 2
        )

    def test_bulk_create_response_includes_ids(self, verified_specialist):
        payload = {"start_times": [future_dt(24), future_dt(25)]}
        resp = verified_specialist.client.post(
            SLOTS_BULK_URL, payload, format="json"
        )
        assert resp.status_code == 201
        for slot in resp.data:
            assert slot["id"] is not None
            assert isinstance(slot["id"], int)

    def test_unverified_specialist_cannot_create_slots(
        self, unverified_specialist
    ):
        resp = unverified_specialist.client.post(
            SLOTS_BULK_URL, {"start_times": [future_dt(24)]}, format="json"
        )
        assert resp.status_code == 403

    def test_regular_user_cannot_create_slots(self, user_with_profile):
        resp = user_with_profile.client.post(
            SLOTS_BULK_URL, {"start_times": [future_dt(24)]}, format="json"
        )
        assert resp.status_code == 403

    def test_anonymous_cannot_create_slots(self, anon_client):
        resp = anon_client.post(
            SLOTS_BULK_URL, {"start_times": [future_dt(24)]}, format="json"
        )
        assert resp.status_code == 401

    def test_past_start_time_is_rejected(self, verified_specialist):
        past = (timezone.now() - timedelta(hours=1)).isoformat()
        resp = verified_specialist.client.post(
            SLOTS_BULK_URL, {"start_times": [past]}, format="json"
        )
        assert resp.status_code == 400

    def test_non_round_start_time_is_rejected(self, verified_specialist):
        bad_time = (
            (timezone.now() + timedelta(hours=24))
            .replace(minute=13, second=0, microsecond=0)
            .isoformat()
        )
        resp = verified_specialist.client.post(
            SLOTS_BULK_URL, {"start_times": [bad_time]}, format="json"
        )
        assert resp.status_code == 400

    def test_duplicate_start_times_in_same_request_are_rejected(
        self, verified_specialist
    ):
        t = future_dt(24)
        resp = verified_specialist.client.post(
            SLOTS_BULK_URL, {"start_times": [t, t]}, format="json"
        )
        assert resp.status_code == 400

    def test_empty_start_times_list_is_rejected(self, verified_specialist):
        resp = verified_specialist.client.post(
            SLOTS_BULK_URL, {"start_times": []}, format="json"
        )
        assert resp.status_code == 400


# ==============================================================================
# 2. Slot management — delete
# ==============================================================================


@pytest.mark.django_db
class TestSlotDelete:
    def test_specialist_can_delete_own_unbooked_slot(
        self, verified_specialist
    ):
        slot = make_slot(verified_specialist.profile)
        resp = verified_specialist.client.delete(f"{SLOTS_URL}{slot.id}/")
        assert resp.status_code == 204
        assert not AvailabilitySlot.objects.filter(id=slot.id).exists()

    def test_specialist_cannot_delete_booked_slot(
        self, verified_specialist, user_with_profile
    ):
        slot = make_slot(verified_specialist.profile)
        Appointment.objects.create(
            slot=slot,
            specialist=verified_specialist.profile,
            user_profile=user_with_profile.profile,
        )
        slot.is_booked = True
        slot.save()
        resp = verified_specialist.client.delete(f"{SLOTS_URL}{slot.id}/")
        assert resp.status_code == 400

    def test_another_specialist_cannot_delete_foreign_slot(
        self, verified_specialist, db
    ):
        slot = make_slot(verified_specialist.profile)
        other_user = make_specialist(email="other_sp@test.com")
        make_specialist_profile(other_user, verified=True)
        other_client = make_client_for(other_user)
        resp = other_client.delete(f"{SLOTS_URL}{slot.id}/")
        assert resp.status_code == 403


# ==============================================================================
# 3. Slot management — list
# ==============================================================================


@pytest.mark.django_db
class TestSlotList:
    def test_anonymous_user_sees_only_future_unbooked_slots(
        self, verified_specialist, anon_client
    ):
        future_slot = make_slot(verified_specialist.profile, hours_ahead=24)
        booked_slot = make_slot(verified_specialist.profile, hours_ahead=48)
        booked_slot.is_booked = True
        booked_slot.save()

        resp = anon_client.get(SLOTS_URL)

        ids = [s["id"] for s in resp.data["results"]]
        assert future_slot.id in ids
        assert booked_slot.id not in ids

    def test_filter_by_specialist_id(self, db, anon_client):
        sp1_user = make_specialist(email="sp1@test.com")
        sp1_profile = make_specialist_profile(sp1_user, verified=True)
        sp2_user = make_specialist(email="sp2@test.com")
        sp2_profile = make_specialist_profile(sp2_user, verified=True)

        slot1 = make_slot(sp1_profile)
        make_slot(sp2_profile)

        resp = anon_client.get(f"{SLOTS_URL}?specialist={sp1_profile.id}")

        ids = [s["id"] for s in resp.data["results"]]
        assert slot1.id in ids
        assert len(ids) == 1


# ==============================================================================
# 4. Booking — create appointment
# ==============================================================================


@pytest.mark.django_db
class TestAppointmentCreate:
    def test_user_with_profile_can_book_a_slot(
        self, verified_specialist, user_with_profile
    ):
        slot = make_slot(verified_specialist.profile)
        resp = user_with_profile.client.post(
            APPOINTMENTS_URL, {"slot": slot.id}, format="json"
        )
        assert resp.status_code == 201
        assert Appointment.objects.count() == 1
        slot.refresh_from_db()
        assert slot.is_booked is True

    def test_user_without_profile_cannot_book(
        self, verified_specialist, user_without_profile
    ):
        slot = make_slot(verified_specialist.profile)
        resp = user_without_profile.client.post(
            APPOINTMENTS_URL, {"slot": slot.id}, format="json"
        )
        assert resp.status_code == 400
        assert "profile" in str(resp.data).lower()

    def test_specialist_cannot_book_a_slot(self, verified_specialist, db):
        slot = make_slot(verified_specialist.profile)
        other_user = make_specialist(email="sp2@test.com")
        make_specialist_profile(other_user, verified=True)
        other_client = make_client_for(other_user)
        resp = other_client.post(
            APPOINTMENTS_URL, {"slot": slot.id}, format="json"
        )
        assert resp.status_code == 400

    def test_already_booked_slot_cannot_be_booked_again(
        self, verified_specialist, user_with_profile
    ):
        slot = make_slot(verified_specialist.profile)
        slot.is_booked = True
        slot.save()
        resp = user_with_profile.client.post(
            APPOINTMENTS_URL, {"slot": slot.id}, format="json"
        )
        assert resp.status_code == 400

    def test_booking_nonexistent_slot_returns_400(self, user_with_profile):
        resp = user_with_profile.client.post(
            APPOINTMENTS_URL, {"slot": 99999}, format="json"
        )
        assert resp.status_code == 400

    def test_anonymous_user_cannot_book(
        self, verified_specialist, anon_client
    ):
        slot = make_slot(verified_specialist.profile)
        resp = anon_client.post(
            APPOINTMENTS_URL, {"slot": slot.id}, format="json"
        )
        assert resp.status_code == 401


# ==============================================================================
# 5. Appointment visibility — list
# ==============================================================================


@pytest.mark.django_db
class TestAppointmentList:
    def test_user_sees_only_their_own_appointments(
        self, verified_specialist, user_with_profile
    ):
        slot = make_slot(verified_specialist.profile)
        appointment = Appointment.objects.create(
            slot=slot,
            specialist=verified_specialist.profile,
            user_profile=user_with_profile.profile,
        )
        slot.is_booked = True
        slot.save()

        resp = user_with_profile.client.get(APPOINTMENTS_URL)

        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert appointment.id in ids
        assert len(ids) == 1

    def test_user_does_not_see_another_users_appointments(
        self, verified_specialist, user_with_profile, db
    ):
        slot = make_slot(verified_specialist.profile)
        Appointment.objects.create(
            slot=slot,
            specialist=verified_specialist.profile,
            user_profile=user_with_profile.profile,
        )
        other_user = make_user(email="other@test.com")
        other_profile = make_profile(other_user)
        other_slot = make_slot(verified_specialist.profile, hours_ahead=48)
        other_appt = Appointment.objects.create(
            slot=other_slot,
            specialist=verified_specialist.profile,
            user_profile=other_profile,
        )

        resp = user_with_profile.client.get(APPOINTMENTS_URL)

        ids = [a["id"] for a in resp.data["results"]]
        assert other_appt.id not in ids

    def test_specialist_sees_only_their_appointments(
        self, verified_specialist, user_with_profile
    ):
        slot = make_slot(verified_specialist.profile)
        appointment = Appointment.objects.create(
            slot=slot,
            specialist=verified_specialist.profile,
            user_profile=user_with_profile.profile,
        )

        resp = verified_specialist.client.get(APPOINTMENTS_URL)

        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert appointment.id in ids

    def test_admin_sees_all_appointments(
        self, verified_specialist, user_with_profile, admin_client
    ):
        slot = make_slot(verified_specialist.profile)
        appointment = Appointment.objects.create(
            slot=slot,
            specialist=verified_specialist.profile,
            user_profile=user_with_profile.profile,
        )
        other_user = make_user(email="other@test.com")
        other_profile = make_profile(other_user)
        other_sp_user = make_specialist(email="sp2@test.com")
        other_sp_profile = make_specialist_profile(
            other_sp_user, verified=True
        )
        other_slot = make_slot(other_sp_profile, hours_ahead=48)
        other_appt = Appointment.objects.create(
            slot=other_slot,
            specialist=other_sp_profile,
            user_profile=other_profile,
        )

        resp = admin_client.client.get(APPOINTMENTS_URL)

        ids = [a["id"] for a in resp.data["results"]]
        assert appointment.id in ids
        assert other_appt.id in ids


# ==============================================================================
# 6. Reschedule
# ==============================================================================


@pytest.mark.django_db
class TestAppointmentReschedule:
    @pytest.fixture(autouse=True)
    def setup(self, verified_specialist, user_with_profile):
        self.sp = verified_specialist
        self.user = user_with_profile
        self.old_slot = make_slot(self.sp.profile, hours_ahead=24)
        self.new_slot = make_slot(self.sp.profile, hours_ahead=48)
        self.appointment = Appointment.objects.create(
            slot=self.old_slot,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )
        self.old_slot.is_booked = True
        self.old_slot.save()

    def _reschedule_url(self):
        return f"{APPOINTMENTS_URL}{self.appointment.id}/reschedule/"

    def test_specialist_can_reschedule_to_free_slot(self):
        resp = self.sp.client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )
        assert resp.status_code == 200
        self.appointment.refresh_from_db()
        assert self.appointment.slot == self.new_slot
        self.old_slot.refresh_from_db()
        assert self.old_slot.is_booked is False
        self.new_slot.refresh_from_db()
        assert self.new_slot.is_booked is True

    def test_reschedule_is_atomic_and_old_slot_becomes_available(self):
        resp = self.sp.client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )
        assert resp.status_code == 200
        self.old_slot.refresh_from_db()
        self.new_slot.refresh_from_db()
        assert self.old_slot.is_booked is False
        assert self.new_slot.is_booked is True
        self.appointment.refresh_from_db()
        assert self.appointment.slot == self.new_slot

    def test_cannot_reschedule_to_slot_booked_concurrently(self, db):
        other_user = make_user(email="other@test.com")
        other_profile = make_profile(other_user)
        Appointment.objects.create(
            slot=self.new_slot,
            specialist=self.sp.profile,
            user_profile=other_profile,
        )
        self.new_slot.is_booked = True
        self.new_slot.save()

        resp = self.sp.client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )
        assert resp.status_code == 400
        self.appointment.refresh_from_db()
        assert self.appointment.slot == self.old_slot

    def test_specialist_cannot_reschedule_to_already_booked_slot(self):
        self.new_slot.is_booked = True
        self.new_slot.save()
        resp = self.sp.client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )
        assert resp.status_code == 400

    def test_specialist_cannot_reschedule_cancelled_appointment(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save()
        resp = self.sp.client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )
        assert resp.status_code == 400

    def test_user_cannot_reschedule(self):
        resp = self.user.client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )
        assert resp.status_code == 403

    def test_other_specialist_cannot_reschedule_foreign_appointment(self, db):
        other_user = make_specialist(email="other_sp@test.com")
        make_specialist_profile(other_user, verified=True)
        other_client = make_client_for(other_user)
        resp = other_client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )
        assert resp.status_code == 404


# ==============================================================================
# 7. Cancellation
# ==============================================================================


@pytest.mark.django_db
class TestAppointmentCancel:
    @pytest.fixture(autouse=True)
    def setup(self, verified_specialist, user_with_profile):
        self.sp = verified_specialist
        self.user = user_with_profile
        self.slot = make_slot(self.sp.profile)
        self.appointment = Appointment.objects.create(
            slot=self.slot,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )
        self.slot.is_booked = True
        self.slot.save()

    def _cancel_url(self):
        return f"{APPOINTMENTS_URL}{self.appointment.id}/cancel/"

    def test_specialist_can_cancel_appointment(self):
        resp = self.sp.client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )
        assert resp.status_code == 200
        self.appointment.refresh_from_db()
        assert self.appointment.status == Appointment.Status.CANCELLED
        self.slot.refresh_from_db()
        assert self.slot.is_booked is False

    def test_cancelling_already_cancelled_appointment_returns_400(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save()
        resp = self.sp.client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )
        assert resp.status_code == 400

    def test_wrong_status_value_is_rejected(self):
        resp = self.sp.client.patch(
            self._cancel_url(), {"status": "completed"}, format="json"
        )
        assert resp.status_code == 400

    def test_user_cannot_cancel_appointment(self):
        resp = self.user.client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )
        assert resp.status_code == 403

    def test_other_specialist_cannot_cancel_foreign_appointment(self, db):
        other_user = make_specialist(email="other_sp@test.com")
        make_specialist_profile(other_user, verified=True)
        other_client = make_client_for(other_user)
        resp = other_client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )
        assert resp.status_code == 404

    def test_cancelled_slot_can_be_booked_again(self, db):
        self.sp.client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )

        other_user = make_user(email="other@test.com")
        make_profile(other_user)
        other_client = make_client_for(other_user)
        resp = other_client.post(
            APPOINTMENTS_URL, {"slot": self.slot.id}, format="json"
        )

        assert resp.status_code == 201
        self.slot.refresh_from_db()
        assert self.slot.is_booked is True

    def test_cancelled_slot_has_multiple_appointments(self, db):
        self.sp.client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )

        other_user = make_user(email="other@test.com")
        make_profile(other_user)
        other_client = make_client_for(other_user)
        other_client.post(
            APPOINTMENTS_URL, {"slot": self.slot.id}, format="json"
        )

        assert Appointment.objects.filter(slot=self.slot).count() == 2


# ==============================================================================
# 8. Auto-completion service
# ==============================================================================


@pytest.mark.django_db
class TestAutoCompletion:
    def test_past_confirmed_appointment_becomes_completed_on_list(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        appt = make_appointment(
            slot, verified_specialist.profile, user_with_profile.profile
        )
        assert appt.status == Appointment.Status.CONFIRMED

        user_with_profile.client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.COMPLETED

    def test_future_confirmed_appointment_stays_confirmed_on_list(
        self, verified_specialist, user_with_profile
    ):
        slot = make_future_slot(verified_specialist.profile)
        appt = make_appointment(
            slot, verified_specialist.profile, user_with_profile.profile
        )

        user_with_profile.client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CONFIRMED

    def test_cancelled_past_appointment_stays_cancelled(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        appt = make_appointment(
            slot,
            verified_specialist.profile,
            user_with_profile.profile,
            status=Appointment.Status.CANCELLED,
        )

        user_with_profile.client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CANCELLED

    def test_already_completed_appointment_stays_completed(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        appt = make_appointment(
            slot,
            verified_specialist.profile,
            user_with_profile.profile,
            status=Appointment.Status.COMPLETED,
        )

        user_with_profile.client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.COMPLETED

    def test_multiple_past_appointments_all_completed(
        self, verified_specialist, user_with_profile
    ):
        slot1 = make_past_slot(verified_specialist.profile, hours_ago=3)
        slot2 = make_past_slot(verified_specialist.profile, hours_ago=5)
        appt1 = make_appointment(
            slot1, verified_specialist.profile, user_with_profile.profile
        )
        appt2 = make_appointment(
            slot2, verified_specialist.profile, user_with_profile.profile
        )

        user_with_profile.client.get(APPOINTMENTS_URL)

        appt1.refresh_from_db()
        appt2.refresh_from_db()
        assert appt1.status == Appointment.Status.COMPLETED
        assert appt2.status == Appointment.Status.COMPLETED


# ==============================================================================
# 9. GET /appointments/completed/ — user perspective
# ==============================================================================


@pytest.mark.django_db
class TestCompletedAppointmentsUser:
    def test_completed_list_returns_only_completed_appointments(
        self, verified_specialist, user_with_profile
    ):
        past_slot = make_past_slot(verified_specialist.profile)
        future_slot = make_future_slot(verified_specialist.profile)
        make_appointment(
            past_slot, verified_specialist.profile, user_with_profile.profile
        )
        make_appointment(
            future_slot, verified_specialist.profile, user_with_profile.profile
        )

        resp = user_with_profile.client.get(COMPLETED_URL)

        assert resp.status_code == 200
        assert len(resp.data["results"]) == 1
        assert (
            resp.data["results"][0]["status"] == Appointment.Status.COMPLETED
        )

    def test_completed_appointment_includes_book_again_url(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        make_appointment(
            slot, verified_specialist.profile, user_with_profile.profile
        )

        resp = user_with_profile.client.get(COMPLETED_URL)

        assert resp.status_code == 200
        appt = resp.data["results"][0]
        assert "book_again_url" in appt
        assert (
            f"specialist={verified_specialist.profile.id}"
            in appt["book_again_url"]
        )

    def test_completed_appointment_includes_specialist_id(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        make_appointment(
            slot, verified_specialist.profile, user_with_profile.profile
        )

        resp = user_with_profile.client.get(COMPLETED_URL)

        appt = resp.data["results"][0]
        assert appt["specialist_id"] == verified_specialist.profile.id

    def test_user_does_not_see_other_users_completed_appointments(
        self, verified_specialist, user_with_profile, db
    ):
        other_user = make_user(email="other@test.com")
        other_profile = make_profile(other_user)
        slot = make_past_slot(verified_specialist.profile)
        make_appointment(slot, verified_specialist.profile, other_profile)

        resp = user_with_profile.client.get(COMPLETED_URL)

        assert resp.status_code == 200
        assert len(resp.data["results"]) == 0

    def test_cancelled_appointments_do_not_appear_in_completed(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        make_appointment(
            slot,
            verified_specialist.profile,
            user_with_profile.profile,
            status=Appointment.Status.CANCELLED,
        )

        resp = user_with_profile.client.get(COMPLETED_URL)

        assert len(resp.data["results"]) == 0

    def test_anonymous_cannot_access_completed(self, anon_client):
        resp = anon_client.get(COMPLETED_URL)
        assert resp.status_code == 401


# ==============================================================================
# 10. GET /appointments/completed/ — specialist perspective
# ==============================================================================


@pytest.mark.django_db
class TestCompletedAppointmentsSpecialist:
    def test_specialist_sees_their_completed_appointments(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        make_appointment(
            slot, verified_specialist.profile, user_with_profile.profile
        )

        resp = verified_specialist.client.get(COMPLETED_URL)

        assert resp.status_code == 200
        assert len(resp.data["results"]) == 1
        assert (
            resp.data["results"][0]["status"] == Appointment.Status.COMPLETED
        )

    def test_specialist_does_not_see_book_again_url(
        self, verified_specialist, user_with_profile
    ):
        slot = make_past_slot(verified_specialist.profile)
        make_appointment(
            slot, verified_specialist.profile, user_with_profile.profile
        )

        resp = verified_specialist.client.get(COMPLETED_URL)

        assert "book_again_url" not in resp.data["results"][0]

    def test_specialist_does_not_see_other_specialists_completed(
        self, verified_specialist, user_with_profile, db
    ):
        other_user = make_specialist(email="other_sp@test.com")
        other_profile = make_specialist_profile(other_user, verified=True)
        slot = make_past_slot(other_profile)
        make_appointment(slot, other_profile, user_with_profile.profile)

        resp = verified_specialist.client.get(COMPLETED_URL)

        assert len(resp.data["results"]) == 0


# ==============================================================================
# 11. Book again — slot calendar path
# ==============================================================================


@pytest.mark.django_db
class TestBookAgain:
    def test_book_again_url_returns_specialist_future_slots(
        self, verified_specialist, user_with_profile
    ):
        past_slot = make_past_slot(verified_specialist.profile)
        make_appointment(
            past_slot, verified_specialist.profile, user_with_profile.profile
        )

        future_start = timezone.now() + timedelta(hours=24)
        future_start = future_start.replace(minute=0, second=0, microsecond=0)
        future_slot = AvailabilitySlot.objects.create(
            specialist=verified_specialist.profile,
            start_time=future_start,
            end_time=future_start + timedelta(hours=1),
        )

        completed_resp = user_with_profile.client.get(COMPLETED_URL)
        book_again_url = completed_resp.data["results"][0]["book_again_url"]

        slots_resp = user_with_profile.client.get(book_again_url)

        assert slots_resp.status_code == 200
        slot_ids = [s["id"] for s in slots_resp.data["results"]]
        assert future_slot.id in slot_ids

    def test_book_again_url_does_not_include_past_slots(
        self, verified_specialist, user_with_profile
    ):
        past_slot = make_past_slot(verified_specialist.profile)
        make_appointment(
            past_slot, verified_specialist.profile, user_with_profile.profile
        )

        completed_resp = user_with_profile.client.get(COMPLETED_URL)
        book_again_url = completed_resp.data["results"][0]["book_again_url"]

        slots_resp = user_with_profile.client.get(book_again_url)

        slot_ids = [s["id"] for s in slots_resp.data["results"]]
        assert past_slot.id not in slot_ids


# ==============================================================================
# 12. Delete unbooked past slots task
# ==============================================================================


@pytest.mark.django_db
class TestDeleteUnbookedPastSlotsTask:
    def _make_past_unbooked(self, specialist_profile):
        now = timezone.now()
        placeholder = now + timedelta(hours=24)
        placeholder = placeholder.replace(minute=0, second=0, microsecond=0)
        slot = AvailabilitySlot.objects.create(
            specialist=specialist_profile,
            start_time=placeholder,
            end_time=placeholder + timedelta(hours=1),
        )
        AvailabilitySlot.objects.filter(pk=slot.pk).update(
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=2),
        )
        return slot

    def test_deletes_unbooked_past_slots(self, verified_specialist):
        slot = self._make_past_unbooked(verified_specialist.profile)
        delete_unbooked_past_slots()
        assert not AvailabilitySlot.objects.filter(pk=slot.pk).exists()

    def test_keeps_booked_past_slots(self, verified_specialist):
        slot = self._make_past_unbooked(verified_specialist.profile)
        AvailabilitySlot.objects.filter(pk=slot.pk).update(is_booked=True)
        delete_unbooked_past_slots()
        assert AvailabilitySlot.objects.filter(pk=slot.pk).exists()

    def test_keeps_future_unbooked_slots(self, verified_specialist):
        now = timezone.now()
        future = now + timedelta(hours=24)
        future = future.replace(minute=0, second=0, microsecond=0)
        slot = AvailabilitySlot.objects.create(
            specialist=verified_specialist.profile,
            start_time=future,
            end_time=future + timedelta(hours=1),
        )
        delete_unbooked_past_slots()
        assert AvailabilitySlot.objects.filter(pk=slot.pk).exists()

    def test_returns_correct_deleted_count(self, verified_specialist):
        self._make_past_unbooked(verified_specialist.profile)
        self._make_past_unbooked(verified_specialist.profile)
        result = delete_unbooked_past_slots()
        assert result == "Deleted 2 unbooked past slot(s)."


# ==============================================================================
# 13. Sorting — confirmed & completed appointments
# ==============================================================================


@pytest.mark.django_db
class TestAppointmentSorting:
    @pytest.fixture(autouse=True)
    def setup(self, verified_specialist, user_with_profile):
        self.sp = verified_specialist
        self.user = user_with_profile
        self.slot_24h = make_slot(self.sp.profile, hours_ahead=24)
        self.slot_48h = make_slot(self.sp.profile, hours_ahead=48)
        self.slot_72h = make_slot(self.sp.profile, hours_ahead=72)
        self.appt_24h = Appointment.objects.create(
            slot=self.slot_24h,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )
        self.appt_48h = Appointment.objects.create(
            slot=self.slot_48h,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )
        self.appt_72h = Appointment.objects.create(
            slot=self.slot_72h,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )

    # confirmed list

    def test_confirmed_default_sort_is_asc(self):
        resp = self.user.client.get(APPOINTMENTS_URL)
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(self.appt_24h.id) < ids.index(self.appt_72h.id)

    def test_confirmed_sort_date_asc(self):
        resp = self.user.client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=asc"
        )
        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(self.appt_24h.id) < ids.index(self.appt_48h.id)
        assert ids.index(self.appt_48h.id) < ids.index(self.appt_72h.id)

    def test_confirmed_sort_date_desc(self):
        resp = self.user.client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=desc"
        )
        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(self.appt_72h.id) < ids.index(self.appt_48h.id)
        assert ids.index(self.appt_48h.id) < ids.index(self.appt_24h.id)

    def test_confirmed_invalid_sort_direction_falls_back_to_asc(self):
        resp = self.user.client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=random"
        )
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(self.appt_24h.id) < ids.index(self.appt_72h.id)

    def test_confirmed_unknown_sort_field_falls_back_to_date(self):
        resp = self.user.client.get(
            APPOINTMENTS_URL + "?sort_field=price&sort_direction=asc"
        )
        assert resp.status_code == 200

    def test_specialist_confirmed_sort_date_desc(self):
        resp = self.sp.client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=desc"
        )
        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(self.appt_72h.id) < ids.index(self.appt_24h.id)

    # completed list

    def test_completed_sort_date_asc(self):
        past_slot_3h = make_past_slot(self.sp.profile, hours_ago=3)
        past_slot_6h = make_past_slot(self.sp.profile, hours_ago=6)
        past_slot_9h = make_past_slot(self.sp.profile, hours_ago=9)
        appt_3h = make_appointment(
            past_slot_3h, self.sp.profile, self.user.profile
        )
        appt_6h = make_appointment(
            past_slot_6h, self.sp.profile, self.user.profile
        )
        appt_9h = make_appointment(
            past_slot_9h, self.sp.profile, self.user.profile
        )

        resp = self.user.client.get(
            COMPLETED_URL + "?sort_field=date&sort_direction=asc"
        )

        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(appt_9h.id) < ids.index(appt_6h.id)
        assert ids.index(appt_6h.id) < ids.index(appt_3h.id)

    def test_completed_sort_date_desc(self):
        past_slot_3h = make_past_slot(self.sp.profile, hours_ago=3)
        past_slot_9h = make_past_slot(self.sp.profile, hours_ago=9)
        appt_3h = make_appointment(
            past_slot_3h, self.sp.profile, self.user.profile
        )
        appt_9h = make_appointment(
            past_slot_9h, self.sp.profile, self.user.profile
        )

        resp = self.user.client.get(
            COMPLETED_URL + "?sort_field=date&sort_direction=desc"
        )

        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(appt_3h.id) < ids.index(appt_9h.id)

    def test_completed_default_sort_is_desc(self):
        past_slot_3h = make_past_slot(self.sp.profile, hours_ago=3)
        past_slot_9h = make_past_slot(self.sp.profile, hours_ago=9)
        appt_3h = make_appointment(
            past_slot_3h, self.sp.profile, self.user.profile
        )
        appt_9h = make_appointment(
            past_slot_9h, self.sp.profile, self.user.profile
        )

        resp = self.user.client.get(COMPLETED_URL)

        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(appt_3h.id) < ids.index(appt_9h.id)

    def test_completed_specialist_sort_date_desc(self):
        past_slot_3h = make_past_slot(self.sp.profile, hours_ago=3)
        past_slot_9h = make_past_slot(self.sp.profile, hours_ago=9)
        appt_3h = make_appointment(
            past_slot_3h, self.sp.profile, self.user.profile
        )
        appt_9h = make_appointment(
            past_slot_9h, self.sp.profile, self.user.profile
        )

        resp = self.sp.client.get(
            COMPLETED_URL + "?sort_field=date&sort_direction=desc"
        )

        ids = [a["id"] for a in resp.data["results"]]
        assert ids.index(appt_3h.id) < ids.index(appt_9h.id)


# ==============================================================================
# 14. Date filtering — confirmed & completed appointments
# ==============================================================================


@pytest.mark.django_db
class TestAppointmentDateFilter:
    @pytest.fixture(autouse=True)
    def setup(self, verified_specialist, user_with_profile):
        self.sp = verified_specialist
        self.user = user_with_profile
        self.slot_june10 = make_slot(self.sp.profile, days_ahead=30)
        self.slot_june11 = make_slot(self.sp.profile, days_ahead=31)
        self.slot_july01 = make_slot(self.sp.profile, days_ahead=51)
        self.appt_june10 = Appointment.objects.create(
            slot=self.slot_june10,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )
        self.appt_june11 = Appointment.objects.create(
            slot=self.slot_june11,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )
        self.appt_july01 = Appointment.objects.create(
            slot=self.slot_july01,
            specialist=self.sp.profile,
            user_profile=self.user.profile,
        )

    # confirmed list

    def test_confirmed_filter_by_exact_date(self):
        date_str = self.slot_june10.start_time.date().isoformat()
        resp = self.user.client.get(f"{APPOINTMENTS_URL}?date={date_str}")
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert self.appt_june10.id in ids
        assert self.appt_june11.id not in ids
        assert self.appt_july01.id not in ids

    def test_confirmed_filter_ignores_invalid_date(self):
        resp = self.user.client.get(f"{APPOINTMENTS_URL}?date=2026-13-99")
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert self.appt_june10.id in ids
        assert self.appt_june11.id in ids
        assert self.appt_july01.id in ids

    def test_confirmed_filter_with_sorting(self):
        date_str = self.slot_june10.start_time.date().isoformat()
        resp = self.user.client.get(
            f"{APPOINTMENTS_URL}?date={date_str}&sort_direction=desc"
        )
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert ids == [self.appt_june10.id]

    def test_specialist_confirmed_filter_by_date(self):
        date_str = self.slot_june11.start_time.date().isoformat()
        resp = self.sp.client.get(f"{APPOINTMENTS_URL}?date={date_str}")
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert self.appt_june11.id in ids
        assert self.appt_june10.id not in ids
        assert self.appt_july01.id not in ids

    # completed list

    def test_completed_filter_by_date(self):
        past_slot_1 = make_past_slot(self.sp.profile, hours_ago=3)
        past_slot_2 = make_past_slot(self.sp.profile, hours_ago=27)
        appt_1 = make_appointment(
            past_slot_1, self.sp.profile, self.user.profile
        )
        appt_2 = make_appointment(
            past_slot_2, self.sp.profile, self.user.profile
        )
        date_str = past_slot_1.start_time.date().isoformat()

        resp = self.user.client.get(f"{COMPLETED_URL}?date={date_str}")

        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert appt_1.id in ids
        assert appt_2.id not in ids

    def test_completed_filter_with_sorting(self):
        past_slot_1 = make_past_slot(self.sp.profile, hours_ago=3)
        appt_1 = make_appointment(
            past_slot_1, self.sp.profile, self.user.profile
        )
        date_str = past_slot_1.start_time.date().isoformat()

        resp = self.user.client.get(
            f"{COMPLETED_URL}?date={date_str}&sort_direction=asc"
        )

        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert ids == [appt_1.id]

    def test_completed_filter_invalid_date(self):
        past_slot_1 = make_past_slot(self.sp.profile, hours_ago=3)
        past_slot_2 = make_past_slot(self.sp.profile, hours_ago=6)
        appt_1 = make_appointment(
            past_slot_1, self.sp.profile, self.user.profile
        )
        appt_2 = make_appointment(
            past_slot_2, self.sp.profile, self.user.profile
        )

        resp = self.user.client.get(f"{COMPLETED_URL}?date=invalid-date")

        assert resp.status_code == 200
        ids = [a["id"] for a in resp.data["results"]]
        assert appt_1.id in ids
        assert appt_2.id in ids
