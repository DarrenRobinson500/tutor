#!/bin/sh
if [ "$SERVICE_TYPE" = "worker" ]; then
    celery -A config worker -l info
elif [ "$SERVICE_TYPE" = "beat" ]; then
    celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
else
    gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
fi
