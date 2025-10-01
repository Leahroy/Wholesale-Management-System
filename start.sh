#!/usr/bin/env bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn my_webapp.wsgi:application
