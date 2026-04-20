#!/bin/sh
set -e

python manage.py migrate --noinput

python manage.py start_cycle_task
python manage.py start_penalty_task

python manage.py process_tasks &

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
