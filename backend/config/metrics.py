import time

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

from events.models import Comment, Event, EventLike
from profiles.models import Profile, SpecialistProfile
from users.models import User

USER_REGISTRATIONS = Counter(
    "user_registrations_total",
    "Total number of user registrations",
)
PROFILE_CREATED = Counter(
    "profile_created_total",
    "Total number of profile creations",
)
SPECIALIST_PROFILE_CREATED = Counter(
    "specialist_profile_created_total",
    "Total number of specialist profile creations",
)
PROFILE_CREATION_BY_TYPE = Counter(
    "profile_creation_total",
    "Total profile creations grouped by profile type",
    ["profile_type"],
)
EVENT_CREATED = Counter(
    "event_created_total",
    "Total number of events created",
)
COMMENT_CREATED = Counter(
    "comment_created_total",
    "Total number of comments created",
)
EVENT_LIKED = Counter(
    "event_likes_total",
    "Total number of event likes",
)
LOGIN_SUCCESS = Counter(
    "login_success_total",
    "Total number of successful logins",
)
LOGIN_FAILED = Counter(
    "login_failed_total",
    "Total number of failed logins",
)
PASSWORD_RESET_REQUESTS = Counter(
    "password_reset_requests_total",
    "Total number of password reset requests",
)
REQUESTS_TOTAL = Counter(
    "django_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUESTS_ERRORS_TOTAL = Counter(
    "django_requests_total_errors_total",
    "Total HTTP requests with 4xx/5xx status",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "django_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


@receiver(post_save, sender=User)
def track_user_registration(sender, instance, created, **kwargs):
    if created:
        USER_REGISTRATIONS.inc()


@receiver(post_save, sender=Profile)
def track_profile_created(sender, instance, created, **kwargs):
    if created:
        PROFILE_CREATED.inc()
        PROFILE_CREATION_BY_TYPE.labels(profile_type="user").inc()


@receiver(post_save, sender=SpecialistProfile)
def track_specialist_profile_created(sender, instance, created, **kwargs):
    if created:
        SPECIALIST_PROFILE_CREATED.inc()
        PROFILE_CREATION_BY_TYPE.labels(profile_type="specialist").inc()


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


class PrometheusRequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()
        method = request.method
        skip_metrics = request.path.rstrip("/") == "/metrics"

        try:
            response = self.get_response(request)
            status_code = str(response.status_code)
            return response
        except Exception:
            status_code = "500"
            raise
        finally:
            if not skip_metrics:
                endpoint = self._resolve_endpoint(request)
                duration = time.perf_counter() - start_time

                REQUESTS_TOTAL.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status_code,
                ).inc()

                if status_code.startswith(("4", "5")):
                    REQUESTS_ERRORS_TOTAL.labels(
                        method=method,
                        endpoint=endpoint,
                        status=status_code,
                    ).inc()

                REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(duration)

    @staticmethod
    def _resolve_endpoint(request):
        resolver_match = getattr(request, "resolver_match", None)

        if resolver_match and resolver_match.route:
            return resolver_match.route

        return request.path

