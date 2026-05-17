from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from events.models import Comment, Event, EventLike
from profiles.models import Profile, SpecialistProfile
from users.models import User

USER_REGISTRATIONS = Counter(
	"wdoc_user_registrations_total",
	"Total number of user registrations",
)
PROFILE_CREATED = Counter(
	"wdoc_profile_created_total",
	"Total number of profile creations",
)
SPECIALIST_PROFILE_CREATED = Counter(
	"wdoc_specialist_profile_created_total",
	"Total number of specialist profile creations",
)
EVENT_CREATED = Counter(
	"wdoc_event_created_total",
	"Total number of events created",
)
COMMENT_CREATED = Counter(
	"wdoc_comment_created_total",
	"Total number of comments created",
)
EVENT_LIKED = Counter(
	"wdoc_event_likes_total",
	"Total number of event likes",
)
LOGIN_SUCCESS = Counter(
	"wdoc_login_success_total",
	"Total number of successful logins",
)
PASSWORD_RESET_REQUESTS = Counter(
	"wdoc_password_reset_requests_total",
	"Total number of password reset requests",
)


@receiver(post_save, sender=User)
def track_user_registration(sender, instance, created, **kwargs):
	if created:
		USER_REGISTRATIONS.inc()


@receiver(post_save, sender=Profile)
def track_profile_created(sender, instance, created, **kwargs):
	if created:
		PROFILE_CREATED.inc()


@receiver(post_save, sender=SpecialistProfile)
def track_specialist_profile_created(sender, instance, created, **kwargs):
	if created:
		SPECIALIST_PROFILE_CREATED.inc()


@receiver(post_save, sender=Event)
def track_event_created(sender, instance, created, **kwargs):
	if created:
		EVENT_CREATED.inc()


@receiver(post_save, sender=Comment)
def track_comment_created(sender, instance, created, **kwargs):
	if created:
		COMMENT_CREATED.inc()


@receiver(post_save, sender=EventLike)
def track_event_like(sender, instance, created, **kwargs):
	if created:
		EVENT_LIKED.inc()


def metrics_view(request):
	return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
