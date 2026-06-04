from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = "events"

    def ready(self):
        from config import metrics  # noqa: F401
        import events.signals  # noqa: F401
