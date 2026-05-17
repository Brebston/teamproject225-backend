from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"

    def ready(self):
<<<<<<< Updated upstream
        import profiles.signals
=======
        from config import metrics  # noqa: F401
>>>>>>> Stashed changes
