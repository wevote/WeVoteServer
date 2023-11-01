#!/usr/bin/env sh

if [ ! -e ./config/environment_variables.json ]; then
    cp ./config/environment_variables-template.json ./config/environment_variables.json
fi
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --no-input || echo "Superuser already created."
python manage.py runserver 0.0.0.0:8000
