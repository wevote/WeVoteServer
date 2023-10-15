#!/usr/bin/env sh

cp ./config/environment_variables-template.json ./config/environment_variables.json
python manage.py makemigrations
python manage.py migrate
python manage.py create_dev_user Joe Smith joe@test.com password1
python manage.py runserver 0.0.0.0:8000

