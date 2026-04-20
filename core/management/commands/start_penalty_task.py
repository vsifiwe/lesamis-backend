from background_task.models import Task
from django.core.management.base import BaseCommand

from core.tasks import generate_penalties

TASK_NAME = 'core.tasks.generate_penalties'


class Command(BaseCommand):
    help = 'Schedule the daily penalty generation task to run immediately.'

    def handle(self, *args, **options):
        if Task.objects.filter(task_name=TASK_NAME).exists():
            self.stdout.write(self.style.WARNING('Penalty task is already queued — skipping.'))
            return
        generate_penalties(schedule=0)
        self.stdout.write(self.style.SUCCESS(
            'Penalty task queued. Run "python manage.py process_tasks" to execute it.'
        ))
