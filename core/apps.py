from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        import core.tasks  # noqa: F401 — registers @background tasks into the scheduler registry
