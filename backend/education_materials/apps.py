from django.apps import AppConfig


class EducationMaterialsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "education_materials"

    def ready(self):

        import education_materials.signals
