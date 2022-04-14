#!/usr/bin/env sh

python manage.py makemigrations
python manage.py migrate
python manage.py create_dev_user Joe Smith joe@test.com password1
python manage.py runserver 0.0.0.0:8000

