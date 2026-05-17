from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from scheduling.models import AvailabilitySlot, Appointment
from scheduling.tests.helpers import (
    create_user_with_profile,
    create_specialist_with_profile,
    create_verified_specialist_with_profile,
    register_and_login_admin,
    register_and_login_user
)
from scheduling.tasks import delete_unbooked_past_slots


SLOTS_URL = "/api/v1/scheduling/slots/"
SLOTS_BULK_URL = "/api/v1/scheduling/slots/bulk_create/"
APPOINTMENTS_URL = "/api/v1/scheduling/appointments/"
COMPLETED_URL = "/api/v1/scheduling/appointments/completed/"


# ── Shared slot-time helpers ──────────────────────────────────────────────────

def future_dt(hours_ahead: int = 24) -> str:
    """Return an ISO-8601 string on the next whole or half hour, N hours from now."""
    dt = timezone.now() + timedelta(hours=hours_ahead)
    # snap to next :00 or :30
    minute = 0 if dt.minute < 30 else 30
    dt = dt.replace(minute=minute, second=0, microsecond=0)
    return dt.isoformat()


def make_slot(specialist_profile, hours_ahead: int = 24, days_ahead=None) -> AvailabilitySlot:
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


# ═════════════════════════════════════════════════════════════════════════════
# 1. Slot management (specialist perspective)
# ═════════════════════════════════════════════════════════════════════════════


class SlotBulkCreateTests(TestCase):

    def test_verified_specialist_can_bulk_create_slots(self):
        _, sp, client = create_verified_specialist_with_profile()
        payload = {"start_times": [future_dt(24), future_dt(25)]}

        response = client.post(SLOTS_BULK_URL, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(AvailabilitySlot.objects.filter(specialist=sp).count(), 2)

    def test_unverified_specialist_cannot_create_slots(self):
        _, _, client = create_specialist_with_profile()
        payload = {"start_times": [future_dt(24)]}

        response = client.post(SLOTS_BULK_URL, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("verified", str(response.data).lower())

    def test_regular_user_cannot_create_slots(self):
        _, _, client = create_user_with_profile()
        payload = {"start_times": [future_dt(24)]}

        response = client.post(SLOTS_BULK_URL, payload, format="json")

        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_create_slots(self):
        from rest_framework.test import APIClient
        payload = {"start_times": [future_dt(24)]}

        response = APIClient().post(SLOTS_BULK_URL, payload, format="json")

        self.assertEqual(response.status_code, 401)

    def test_past_start_time_is_rejected(self):
        _, _, client = create_verified_specialist_with_profile()
        past = (timezone.now() - timedelta(hours=1)).isoformat()
        payload = {"start_times": [past]}

        response = client.post(SLOTS_BULK_URL, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_non_round_start_time_is_rejected(self):
        _, _, client = create_verified_specialist_with_profile()
        # 13 minutes past the hour — not :00 or :30
        bad_time = (timezone.now() + timedelta(hours=24)).replace(
            minute=13, second=0, microsecond=0
        ).isoformat()
        payload = {"start_times": [bad_time]}

        response = client.post(SLOTS_BULK_URL, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_duplicate_start_times_in_same_request_are_rejected(self):
        _, _, client = create_verified_specialist_with_profile()
        t = future_dt(24)
        payload = {"start_times": [t, t]}

        response = client.post(SLOTS_BULK_URL, payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_empty_start_times_list_is_rejected(self):
        _, _, client = create_verified_specialist_with_profile()

        response = client.post(SLOTS_BULK_URL, {"start_times": []}, format="json")

        self.assertEqual(response.status_code, 400)


class SlotDeleteTests(TestCase):

    def test_specialist_can_delete_own_unbooked_slot(self):
        _, sp, client = create_verified_specialist_with_profile()
        slot = make_slot(sp)

        response = client.delete(f"{SLOTS_URL}{slot.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(AvailabilitySlot.objects.filter(id=slot.id).exists())

    def test_specialist_cannot_delete_booked_slot(self):
        _, sp, sp_client = create_verified_specialist_with_profile()
        _, user_profile, user_client = create_user_with_profile(email="u@test.com")
        slot = make_slot(sp)
        # book it
        Appointment.objects.create(
            slot=slot, specialist=sp, user_profile=user_profile
        )
        slot.is_booked = True
        slot.save()

        response = sp_client.delete(f"{SLOTS_URL}{slot.id}/")

        self.assertEqual(response.status_code, 400)

    def test_another_specialist_cannot_delete_foreign_slot(self):
        _, sp, _ = create_verified_specialist_with_profile()
        _, _, other_client = create_verified_specialist_with_profile(
            email="other@test.com"
        )
        slot = make_slot(sp)

        response = other_client.delete(f"{SLOTS_URL}{slot.id}/")

        self.assertEqual(response.status_code, 403)


class SlotListTests(TestCase):

    def test_anonymous_user_sees_only_future_unbooked_slots(self):
        from rest_framework.test import APIClient
        _, sp, _ = create_verified_specialist_with_profile()
        future_slot = make_slot(sp, hours_ahead=24)
        booked_slot = make_slot(sp, hours_ahead=48)
        booked_slot.is_booked = True
        booked_slot.save()

        response = APIClient().get(SLOTS_URL)

        ids = [s["id"] for s in response.data]
        self.assertIn(future_slot.id, ids)
        self.assertNotIn(booked_slot.id, ids)

    def test_filter_by_specialist_id(self):
        from rest_framework.test import APIClient
        _, sp1, _ = create_verified_specialist_with_profile(email="sp1@test.com")
        _, sp2, _ = create_verified_specialist_with_profile(email="sp2@test.com")
        slot1 = make_slot(sp1)
        make_slot(sp2)

        response = APIClient().get(f"{SLOTS_URL}?specialist={sp1.id}")

        ids = [s["id"] for s in response.data]
        self.assertIn(slot1.id, ids)
        self.assertEqual(len(ids), 1)


# ═════════════════════════════════════════════════════════════════════════════
# 2. Booking (user perspective)
# ═════════════════════════════════════════════════════════════════════════════

class AppointmentCreateTests(TestCase):

    def setUp(self):
        _, self.sp, _ = create_verified_specialist_with_profile()
        self.slot = make_slot(self.sp)
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )

    def test_user_with_profile_can_book_a_slot(self):
        response = self.user_client.post(
            APPOINTMENTS_URL, {"slot": self.slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Appointment.objects.count(), 1)
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.is_booked)

    def test_user_without_profile_cannot_book(self):
        _, client = register_and_login_user(email="noprofile@test.com")

        response = client.post(
            APPOINTMENTS_URL, {"slot": self.slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("profile", str(response.data).lower())

    def test_specialist_cannot_book_a_slot(self):
        _, _, sp_client = create_verified_specialist_with_profile(
            email="sp2@test.com"
        )

        response = sp_client.post(
            APPOINTMENTS_URL, {"slot": self.slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_already_booked_slot_cannot_be_booked_again(self):
        self.slot.is_booked = True
        self.slot.save()

        response = self.user_client.post(
            APPOINTMENTS_URL, {"slot": self.slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_booking_nonexistent_slot_returns_400(self):
        response = self.user_client.post(
            APPOINTMENTS_URL, {"slot": 99999}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_anonymous_user_cannot_book(self):
        from rest_framework.test import APIClient

        response = APIClient().post(
            APPOINTMENTS_URL, {"slot": self.slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 401)


# ═════════════════════════════════════════════════════════════════════════════
# 3. Appointment visibility
# ═════════════════════════════════════════════════════════════════════════════

class AppointmentListTests(TestCase):

    def setUp(self):
        _, self.sp, self.sp_client = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )
        slot = make_slot(self.sp)
        self.appointment = Appointment.objects.create(
            slot=slot,
            specialist=self.sp,
            user_profile=self.profile,
        )
        slot.is_booked = True
        slot.save()

    def test_user_sees_only_their_own_appointments(self):
        response = self.user_client.get(APPOINTMENTS_URL)

        self.assertEqual(response.status_code, 200)
        ids = [a["id"] for a in response.data]
        self.assertIn(self.appointment.id, ids)
        self.assertEqual(len(ids), 1)

    def test_user_does_not_see_another_users_appointments(self):
        _, other_profile, other_client = create_user_with_profile(
            email="other@test.com"
        )
        other_slot = make_slot(self.sp, hours_ahead=48)
        other_appt = Appointment.objects.create(
            slot=other_slot,
            specialist=self.sp,
            user_profile=other_profile,
        )

        response = self.user_client.get(APPOINTMENTS_URL)

        ids = [a["id"] for a in response.data]
        self.assertNotIn(other_appt.id, ids)

    def test_specialist_sees_only_their_appointments(self):
        response = self.sp_client.get(APPOINTMENTS_URL)

        self.assertEqual(response.status_code, 200)
        ids = [a["id"] for a in response.data]
        self.assertIn(self.appointment.id, ids)

    def test_admin_sees_all_appointments(self):
        _, admin_client = register_and_login_admin()
        _, other_profile, _ = create_user_with_profile(email="other@test.com")
        _, other_sp, _ = create_verified_specialist_with_profile(email="sp2@test.com")
        other_slot = make_slot(other_sp, hours_ahead=48)
        other_appt = Appointment.objects.create(
            slot=other_slot, specialist=other_sp, user_profile=other_profile
        )

        response = admin_client.get(APPOINTMENTS_URL)

        ids = [a["id"] for a in response.data]
        self.assertIn(self.appointment.id, ids)
        self.assertIn(other_appt.id, ids)


# ═════════════════════════════════════════════════════════════════════════════
# 4. Reschedule (specialist perspective)
# ═════════════════════════════════════════════════════════════════════════════

class AppointmentRescheduleTests(TestCase):

    def setUp(self):
        _, self.sp, self.sp_client = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )
        self.old_slot = make_slot(self.sp, hours_ahead=24)
        self.new_slot = make_slot(self.sp, hours_ahead=48)
        self.appointment = Appointment.objects.create(
            slot=self.old_slot,
            specialist=self.sp,
            user_profile=self.profile,
        )
        self.old_slot.is_booked = True
        self.old_slot.save()

    def _reschedule_url(self):
        return f"{APPOINTMENTS_URL}{self.appointment.id}/reschedule/"

    def test_specialist_can_reschedule_to_free_slot(self):
        response = self.sp_client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.slot, self.new_slot)
        self.old_slot.refresh_from_db()
        self.assertFalse(self.old_slot.is_booked)
        self.new_slot.refresh_from_db()
        self.assertTrue(self.new_slot.is_booked)

    def test_specialist_cannot_reschedule_to_already_booked_slot(self):
        self.new_slot.is_booked = True
        self.new_slot.save()

        response = self.sp_client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_specialist_cannot_reschedule_cancelled_appointment(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save()

        response = self.sp_client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_user_cannot_reschedule(self):
        response = self.user_client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_other_specialist_cannot_reschedule_foreign_appointment(self):
        _, _, other_sp_client = create_verified_specialist_with_profile(
            email="other@test.com"
        )

        response = other_sp_client.patch(
            self._reschedule_url(), {"slot": self.new_slot.id}, format="json"
        )

        self.assertEqual(response.status_code, 404)


# ═════════════════════════════════════════════════════════════════════════════
# 5. Cancellation (specialist perspective)
# ═════════════════════════════════════════════════════════════════════════════

class AppointmentCancelTests(TestCase):

    def setUp(self):
        _, self.sp, self.sp_client = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )
        self.slot = make_slot(self.sp)
        self.appointment = Appointment.objects.create(
            slot=self.slot,
            specialist=self.sp,
            user_profile=self.profile,
        )
        self.slot.is_booked = True
        self.slot.save()

    def _cancel_url(self):
        return f"{APPOINTMENTS_URL}{self.appointment.id}/cancel/"

    def test_specialist_can_cancel_appointment(self):
        response = self.sp_client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.is_booked)

    def test_cancelling_already_cancelled_appointment_returns_400(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save()

        response = self.sp_client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_wrong_status_value_is_rejected(self):
        response = self.sp_client.patch(
            self._cancel_url(), {"status": "completed"}, format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_user_cannot_cancel_appointment(self):
        response = self.user_client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )

        self.assertEqual(response.status_code, 403)

    def test_other_specialist_cannot_cancel_foreign_appointment(self):
        _, _, other_client = create_verified_specialist_with_profile(
            email="other@test.com"
        )

        response = other_client.patch(
            self._cancel_url(), {"status": "cancelled"}, format="json"
        )

        self.assertEqual(response.status_code, 404)


# ═════════════════════════════════════════════════════════════════════════════
# 6. Auto-completion service
# ═════════════════════════════════════════════════════════════════════════════
def make_past_slot(specialist_profile, hours_ago: int = 3) -> AvailabilitySlot:
    """Create a slot that has already ended, bypassing model.clean() via update()."""
    now = timezone.now()
    placeholder_start = now + timedelta(hours=24 + hours_ago)
    placeholder_start = placeholder_start.replace(minute=0, second=0, microsecond=0)
    slot = AvailabilitySlot.objects.create(
        specialist=specialist_profile,
        start_time=placeholder_start,
        end_time=placeholder_start + timedelta(hours=1),
        is_booked=True,
    )
    past_start = (now - timedelta(hours=hours_ago)).replace(minute=0, second=0, microsecond=0)
    AvailabilitySlot.objects.filter(pk=slot.pk).update(
        start_time=past_start,
        end_time=past_start + timedelta(hours=1),
    )
    slot.refresh_from_db()
    return slot


def make_future_slot(specialist_profile, hours_ahead: int = 24) -> AvailabilitySlot:
    start = timezone.now() + timedelta(hours=hours_ahead)
    start = start.replace(minute=0, second=0, microsecond=0)
    return AvailabilitySlot.objects.create(
        specialist=specialist_profile,
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_booked=True,
    )


def make_appointment(slot, specialist, user_profile,
                     status=Appointment.Status.CONFIRMED) -> Appointment:
    appt = Appointment.objects.create(
        slot=slot,
        specialist=specialist,
        user_profile=user_profile,
        status=status,
    )
    return appt


class AutoCompletionTests(TestCase):

    def setUp(self):
        _, self.sp, _ = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )

    def test_past_confirmed_appointment_becomes_completed_on_list(self):
        slot = make_past_slot(self.sp)
        appt = make_appointment(slot, self.sp, self.profile)
        self.assertEqual(appt.status, Appointment.Status.CONFIRMED)

        self.user_client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.COMPLETED)

    def test_future_confirmed_appointment_stays_confirmed_on_list(self):
        slot = make_future_slot(self.sp)
        appt = make_appointment(slot, self.sp, self.profile)

        self.user_client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CONFIRMED)

    def test_cancelled_past_appointment_stays_cancelled(self):
        slot = make_past_slot(self.sp)
        appt = make_appointment(slot, self.sp, self.profile,
                                status=Appointment.Status.CANCELLED)

        self.user_client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CANCELLED)

    def test_already_completed_appointment_stays_completed(self):
        slot = make_past_slot(self.sp)
        appt = make_appointment(slot, self.sp, self.profile,
                                status=Appointment.Status.COMPLETED)

        self.user_client.get(APPOINTMENTS_URL)

        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.COMPLETED)

    def test_multiple_past_appointments_all_completed(self):
        slot1 = make_past_slot(self.sp, hours_ago=3)
        slot2 = make_past_slot(self.sp, hours_ago=5)
        appt1 = make_appointment(slot1, self.sp, self.profile)
        appt2 = make_appointment(slot2, self.sp, self.profile)

        self.user_client.get(APPOINTMENTS_URL)

        appt1.refresh_from_db()
        appt2.refresh_from_db()
        self.assertEqual(appt1.status, Appointment.Status.COMPLETED)
        self.assertEqual(appt2.status, Appointment.Status.COMPLETED)


# ═════════════════════════════════════════════════════════════════════════════
# 7. GET /appointments/completed/ — user perspective
# ═════════════════════════════════════════════════════════════════════════════

class CompletedAppointmentsUserTests(TestCase):

    def setUp(self):
        _, self.sp, _ = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )

    def test_completed_list_returns_only_completed_appointments(self):
        past_slot = make_past_slot(self.sp)
        future_slot = make_future_slot(self.sp)
        make_appointment(past_slot, self.sp, self.profile)
        make_appointment(future_slot, self.sp, self.profile)

        response = self.user_client.get(COMPLETED_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], Appointment.Status.COMPLETED)

    def test_completed_appointment_includes_book_again_url(self):
        slot = make_past_slot(self.sp)
        make_appointment(slot, self.sp, self.profile)

        response = self.user_client.get(COMPLETED_URL)

        self.assertEqual(response.status_code, 200)
        appt = response.data[0]
        self.assertIn("book_again_url", appt)
        self.assertIn(f"specialist={self.sp.id}", appt["book_again_url"])

    def test_completed_appointment_includes_specialist_id(self):
        slot = make_past_slot(self.sp)
        make_appointment(slot, self.sp, self.profile)

        response = self.user_client.get(COMPLETED_URL)

        appt = response.data[0]
        self.assertEqual(appt["specialist_id"], self.sp.id)

    def test_user_does_not_see_other_users_completed_appointments(self):
        _, other_profile, _ = create_user_with_profile(email="other@test.com")
        slot = make_past_slot(self.sp)
        make_appointment(slot, self.sp, other_profile)

        response = self.user_client.get(COMPLETED_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_cancelled_appointments_do_not_appear_in_completed(self):
        slot = make_past_slot(self.sp)
        make_appointment(slot, self.sp, self.profile,
                         status=Appointment.Status.CANCELLED)

        response = self.user_client.get(COMPLETED_URL)

        self.assertEqual(len(response.data), 0)

    def test_anonymous_cannot_access_completed(self):
        from rest_framework.test import APIClient

        response = APIClient().get(COMPLETED_URL)

        self.assertEqual(response.status_code, 401)


# ═════════════════════════════════════════════════════════════════════════════
# 8. GET /appointments/completed/ — specialist perspective
# ═════════════════════════════════════════════════════════════════════════════

class CompletedAppointmentsSpecialistTests(TestCase):

    def setUp(self):
        _, self.sp, self.sp_client = create_verified_specialist_with_profile()
        _, self.profile, _ = create_user_with_profile(email="user@test.com")

    def test_specialist_sees_their_completed_appointments(self):
        slot = make_past_slot(self.sp)
        make_appointment(slot, self.sp, self.profile)

        response = self.sp_client.get(COMPLETED_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], Appointment.Status.COMPLETED)

    def test_specialist_does_not_see_book_again_url(self):
        slot = make_past_slot(self.sp)
        make_appointment(slot, self.sp, self.profile)

        response = self.sp_client.get(COMPLETED_URL)

        # book_again_url is only in the user-facing serializer
        self.assertNotIn("book_again_url", response.data[0])

    def test_specialist_does_not_see_other_specialists_completed(self):
        _, other_sp, _ = create_verified_specialist_with_profile(
            email="other@test.com"
        )
        slot = make_past_slot(other_sp)
        make_appointment(slot, other_sp, self.profile)

        response = self.sp_client.get(COMPLETED_URL)

        self.assertEqual(len(response.data), 0)


# ═════════════════════════════════════════════════════════════════════════════
# 9. Book again — slot calendar path
# ═════════════════════════════════════════════════════════════════════════════

class BookAgainTests(TestCase):
    """
    Confirms that the book_again_url returned in a completed appointment
    actually resolves and returns that specialist's future unbooked slots.
    """

    def setUp(self):
        _, self.sp, _ = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )

    def test_book_again_url_returns_specialist_future_slots(self):
        # Create one completed (past) appointment
        past_slot = make_past_slot(self.sp)
        make_appointment(past_slot, self.sp, self.profile)

        # Specialist has one future available slot
        future_start = timezone.now() + timedelta(hours=24)
        future_start = future_start.replace(minute=0, second=0, microsecond=0)
        future_slot = AvailabilitySlot.objects.create(
            specialist=self.sp,
            start_time=future_start,
            end_time=future_start + timedelta(hours=1),
        )

        completed_response = self.user_client.get(COMPLETED_URL)
        book_again_url = completed_response.data[0]["book_again_url"]

        slots_response = self.user_client.get(book_again_url)

        self.assertEqual(slots_response.status_code, 200)
        slot_ids = [s["id"] for s in slots_response.data]
        self.assertIn(future_slot.id, slot_ids)

    def test_book_again_url_does_not_include_past_slots(self):
        past_slot = make_past_slot(self.sp)
        make_appointment(past_slot, self.sp, self.profile)

        completed_response = self.user_client.get(COMPLETED_URL)
        book_again_url = completed_response.data[0]["book_again_url"]

        slots_response = self.user_client.get(book_again_url)

        slot_ids = [s["id"] for s in slots_response.data]
        self.assertNotIn(past_slot.id, slot_ids)


# ═════════════════════════════════════════════════════════════════════════════
# 10. Delete Unbooked Past Slots
# ═════════════════════════════════════════════════════════════════════════════


class DeleteUnbookedPastSlotsTaskTests(TestCase):

    def setUp(self):
        _, self.sp, _ = create_verified_specialist_with_profile()

    def _make_past_unbooked(self):
        now = timezone.now()
        placeholder = now + timedelta(hours=24)
        placeholder = placeholder.replace(minute=0, second=0, microsecond=0)
        slot = AvailabilitySlot.objects.create(
            specialist=self.sp,
            start_time=placeholder,
            end_time=placeholder + timedelta(hours=1),
        )
        AvailabilitySlot.objects.filter(pk=slot.pk).update(
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=2),
        )
        return slot

    def test_deletes_unbooked_past_slots(self):
        slot = self._make_past_unbooked()
        delete_unbooked_past_slots()
        self.assertFalse(AvailabilitySlot.objects.filter(pk=slot.pk).exists())

    def test_keeps_booked_past_slots(self):
        slot = self._make_past_unbooked()
        AvailabilitySlot.objects.filter(pk=slot.pk).update(is_booked=True)
        delete_unbooked_past_slots()
        self.assertTrue(AvailabilitySlot.objects.filter(pk=slot.pk).exists())

    def test_keeps_future_unbooked_slots(self):
        now = timezone.now()
        future = now + timedelta(hours=24)
        future = future.replace(minute=0, second=0, microsecond=0)
        slot = AvailabilitySlot.objects.create(
            specialist=self.sp,
            start_time=future,
            end_time=future + timedelta(hours=1),
        )
        delete_unbooked_past_slots()
        self.assertTrue(AvailabilitySlot.objects.filter(pk=slot.pk).exists())

    def test_returns_correct_deleted_count(self):
        self._make_past_unbooked()
        self._make_past_unbooked()
        result = delete_unbooked_past_slots()
        self.assertEqual(result, "Deleted 2 unbooked past slot(s).")


# ═════════════════════════════════════════════════════════════════════════════
# 11. Sorting — confirmed & completed appointments
# ═════════════════════════════════════════════════════════════════════════════


class AppointmentSortingTests(TestCase):

    def setUp(self):
        _, self.sp, self.sp_client = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user@test.com"
        )
        # Three future confirmed appointments at different times
        self.slot_24h = make_slot(self.sp, hours_ahead=24)
        self.slot_48h = make_slot(self.sp, hours_ahead=48)
        self.slot_72h = make_slot(self.sp, hours_ahead=72)

        self.appt_24h = Appointment.objects.create(
            slot=self.slot_24h, specialist=self.sp, user_profile=self.profile
        )
        self.appt_48h = Appointment.objects.create(
            slot=self.slot_48h, specialist=self.sp, user_profile=self.profile
        )
        self.appt_72h = Appointment.objects.create(
            slot=self.slot_72h, specialist=self.sp, user_profile=self.profile
        )

    # ── confirmed list ────────────────────────────────────────────────────────

    def test_confirmed_default_sort_is_asc(self):
        """No params → earliest slot comes first."""
        response = self.user_client.get(APPOINTMENTS_URL)

        self.assertEqual(response.status_code, 200)
        ids = [a["id"] for a in response.data]
        self.assertEqual(ids.index(self.appt_24h.id) < ids.index(self.appt_72h.id), True)

    def test_confirmed_sort_date_asc(self):
        response = self.user_client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=asc"
        )

        ids = [a["id"] for a in response.data]
        self.assertLess(ids.index(self.appt_24h.id), ids.index(self.appt_48h.id))
        self.assertLess(ids.index(self.appt_48h.id), ids.index(self.appt_72h.id))

    def test_confirmed_sort_date_desc(self):
        response = self.user_client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=desc"
        )

        ids = [a["id"] for a in response.data]
        self.assertLess(ids.index(self.appt_72h.id), ids.index(self.appt_48h.id))
        self.assertLess(ids.index(self.appt_48h.id), ids.index(self.appt_24h.id))

    def test_confirmed_invalid_sort_direction_falls_back_to_asc(self):
        """An unrecognised direction should not crash — falls back to asc."""
        response = self.user_client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=random"
        )

        self.assertEqual(response.status_code, 200)
        ids = [a["id"] for a in response.data]
        self.assertLess(ids.index(self.appt_24h.id), ids.index(self.appt_72h.id))

    def test_confirmed_unknown_sort_field_falls_back_to_date(self):
        """An unrecognised field should not crash — falls back to date asc."""
        response = self.user_client.get(
            APPOINTMENTS_URL + "?sort_field=price&sort_direction=asc"
        )

        self.assertEqual(response.status_code, 200)

    # ── specialist sees the same sorting ─────────────────────────────────────

    def test_specialist_confirmed_sort_date_desc(self):
        response = self.sp_client.get(
            APPOINTMENTS_URL + "?sort_field=date&sort_direction=desc"
        )

        ids = [a["id"] for a in response.data]
        self.assertLess(ids.index(self.appt_72h.id), ids.index(self.appt_24h.id))

    # ── completed list ────────────────────────────────────────────────────────

    def test_completed_sort_date_asc(self):
        past_slot_3h = make_past_slot(self.sp, hours_ago=3)
        past_slot_6h = make_past_slot(self.sp, hours_ago=6)
        past_slot_9h = make_past_slot(self.sp, hours_ago=9)
        appt_3h = make_appointment(past_slot_3h, self.sp, self.profile)
        appt_6h = make_appointment(past_slot_6h, self.sp, self.profile)
        appt_9h = make_appointment(past_slot_9h, self.sp, self.profile)

        response = self.user_client.get(
            COMPLETED_URL + "?sort_field=date&sort_direction=asc"
        )

        self.assertEqual(response.status_code, 200)
        ids = [a["id"] for a in response.data]
        # 9h-ago slot started earliest → comes first in asc
        self.assertLess(ids.index(appt_9h.id), ids.index(appt_6h.id))
        self.assertLess(ids.index(appt_6h.id), ids.index(appt_3h.id))

    def test_completed_sort_date_desc(self):
        past_slot_3h = make_past_slot(self.sp, hours_ago=3)
        past_slot_9h = make_past_slot(self.sp, hours_ago=9)
        appt_3h = make_appointment(past_slot_3h, self.sp, self.profile)
        appt_9h = make_appointment(past_slot_9h, self.sp, self.profile)

        response = self.user_client.get(
            COMPLETED_URL + "?sort_field=date&sort_direction=desc"
        )

        ids = [a["id"] for a in response.data]
        # most recent completed first
        self.assertLess(ids.index(appt_3h.id), ids.index(appt_9h.id))

    def test_completed_default_sort_is_asc(self):
        past_slot_3h = make_past_slot(self.sp, hours_ago=3)
        past_slot_9h = make_past_slot(self.sp, hours_ago=9)
        appt_3h = make_appointment(past_slot_3h, self.sp, self.profile)
        appt_9h = make_appointment(past_slot_9h, self.sp, self.profile)

        response = self.user_client.get(COMPLETED_URL)

        ids = [a["id"] for a in response.data]
        self.assertLess(ids.index(appt_3h.id), ids.index(appt_9h.id))

    def test_completed_specialist_sort_date_desc(self):
        past_slot_3h = make_past_slot(self.sp, hours_ago=3)
        past_slot_9h = make_past_slot(self.sp, hours_ago=9)
        appt_3h = make_appointment(past_slot_3h, self.sp, self.profile)
        appt_9h = make_appointment(past_slot_9h, self.sp, self.profile)

        response = self.sp_client.get(
            COMPLETED_URL + "?sort_field=date&sort_direction=desc"
        )

        ids = [a["id"] for a in response.data]
        self.assertLess(ids.index(appt_3h.id), ids.index(appt_9h.id))


# ═════════════════════════════════════════════════════════════════════════════
# 12. Date Filtering — confirmed & completed appointments
# ═════════════════════════════════════════════════════════════════════════════

class AppointmentDateFilterTests(TestCase):

    def setUp(self):
        _, self.sp, self.sp_client = create_verified_specialist_with_profile()
        _, self.profile, self.user_client = create_user_with_profile(
            email="user_date@test.com"
        )

        # Create slots on different days
        self.slot_june10 = make_slot(self.sp, days_ahead=30)
        self.slot_june11 = make_slot(self.sp, days_ahead=31)
        self.slot_july01 = make_slot(self.sp, days_ahead=51)

        # Appointments for those slots
        self.appt_june10 = Appointment.objects.create(
            slot=self.slot_june10, specialist=self.sp, user_profile=self.profile
        )
        self.appt_june11 = Appointment.objects.create(
            slot=self.slot_june11, specialist=self.sp, user_profile=self.profile
        )
        self.appt_july01 = Appointment.objects.create(
            slot=self.slot_july01, specialist=self.sp, user_profile=self.profile
        )

    # ── confirmed list ────────────────────────────────────────────────────────

    def test_confirmed_filter_by_exact_date(self):
        """?date=YYYY-MM-DD returns only appointments on that date."""
        date_str = self.slot_june10.start_time.date().isoformat()

        response = self.user_client.get(f"{APPOINTMENTS_URL}?date={date_str}")
        self.assertEqual(response.status_code, 200)

        ids = [a["id"] for a in response.data]
        self.assertIn(self.appt_june10.id, ids)
        self.assertNotIn(self.appt_june11.id, ids)
        self.assertNotIn(self.appt_july01.id, ids)

    def test_confirmed_filter_ignores_invalid_date(self):
        """Invalid date → filter ignored → all confirmed appointments returned."""
        response = self.user_client.get(f"{APPOINTMENTS_URL}?date=2026-13-99")
        self.assertEqual(response.status_code, 200)

        ids = [a["id"] for a in response.data]
        self.assertIn(self.appt_june10.id, ids)
        self.assertIn(self.appt_june11.id, ids)
        self.assertIn(self.appt_july01.id, ids)

    def test_confirmed_filter_with_sorting(self):
        """Date filter works together with sorting."""
        date_str = self.slot_june10.start_time.date().isoformat()

        response = self.user_client.get(
            f"{APPOINTMENTS_URL}?date={date_str}&sort_direction=desc"
        )
        self.assertEqual(response.status_code, 200)

        ids = [a["id"] for a in response.data]
        # Only one appointment on that date
        self.assertEqual(ids, [self.appt_june10.id])

    # ── specialist sees the same filtering ───────────────────────────────────

    def test_specialist_confirmed_filter_by_date(self):
        date_str = self.slot_june11.start_time.date().isoformat()

        response = self.sp_client.get(f"{APPOINTMENTS_URL}?date={date_str}")
        self.assertEqual(response.status_code, 200)

        ids = [a["id"] for a in response.data]
        self.assertIn(self.appt_june11.id, ids)
        self.assertNotIn(self.appt_june10.id, ids)
        self.assertNotIn(self.appt_july01.id, ids)

    # ── completed list ────────────────────────────────────────────────────────

    def test_completed_filter_by_date(self):
        """Completed appointments can also be filtered by date."""
        past_slot_1 = make_past_slot(self.sp, hours_ago=3)
        past_slot_2 = make_past_slot(self.sp, hours_ago=27)

        appt_1 = make_appointment(past_slot_1, self.sp, self.profile)
        appt_2 = make_appointment(past_slot_2, self.sp, self.profile)

        date_str = past_slot_1.start_time.date().isoformat()

        response = self.user_client.get(f"{COMPLETED_URL}?date={date_str}")
        self.assertEqual(response.status_code, 200)

        ids = [a["id"] for a in response.data]
        self.assertIn(appt_1.id, ids)
        self.assertNotIn(appt_2.id, ids)

    def test_completed_filter_with_sorting(self):
        past_slot_1 = make_past_slot(self.sp, hours_ago=3)
        appt_1 = make_appointment(past_slot_1, self.sp, self.profile)

        date_str = past_slot_1.start_time.date().isoformat()

        response = self.user_client.get(
            f"{COMPLETED_URL}?date={date_str}&sort_direction=asc"
        )
        self.assertEqual(response.status_code, 200)

        ids = [a["id"] for a in response.data]
        self.assertEqual(ids, [appt_1.id])

    def test_completed_filter_invalid_date(self):
        """Invalid date → filter ignored → all completed appointments returned."""
        past_slot_1 = make_past_slot(self.sp, hours_ago=3)
        past_slot_2 = make_past_slot(self.sp, hours_ago=6)

        appt_1 = make_appointment(past_slot_1, self.sp, self.profile)
        appt_2 = make_appointment(past_slot_2, self.sp, self.profile)

        response = self.user_client.get(f"{COMPLETED_URL}?date=invalid-date")
        self.assertEqual(response.status_code, 200)

        ids = [a["id"] for a in response.data]
        self.assertIn(appt_1.id, ids)
        self.assertIn(appt_2.id, ids)
