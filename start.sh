#!/usr/bin/env bash

# This script runs database migrations and collects static files
# before starting the Gunicorn server.

# 1. Run database migrations (Fixes "column ... does not exist" errors)
echo "Applying database migrations..."
# Using 'exec' to ensure python is found
exec python manage.py migrate || { echo "MIGRATION FAILED. Check logs."; exit 1; }

# 2. Collect static files (Essential for CSS/JS/Images in production)
echo "Collecting static files..."
exec python manage.py collectstatic --noinput || { echo "COLLECTSTATIC FAILED. Check logs."; exit 1; }

# 3. Start the Gunicorn server
echo "Starting Gunicorn server..."
exec gunicorn my_webapp.wsgi:application
