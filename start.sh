#!/bin/bash

# Start script for dadjoke-hotline with Gunicorn

echo "Starting dadjoke-hotline with Gunicorn..."

# Change to the project directory
cd "$(dirname "$0")"

# Run database migrations (if needed)
echo "Running database migrations..."
python manage.py migrate

# Collect static files (if needed in production)
# python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn --config gunicorn_config.py dadjoke_hotline.wsgi:application
