from django.core.management.base import BaseCommand

from core.tasks import generate_monthly_cycle


class Command(BaseCommand):
    help = 'Schedule the monthly contribution cycle generation task to run immediately.'

    def handle(self, *args, **options):
        generate_monthly_cycle(schedule=0)
        self.stdout.write(self.style.SUCCESS(
            'Cycle task queued. Run "python manage.py process_tasks" to execute it.'
        ))
