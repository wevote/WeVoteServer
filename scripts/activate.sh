#!/bin/zsh
# For now, this script assumes your PythonEnvironments folder
# is setup according to README.md
source ../../PythonEnvironments/WeVoteServer3.4/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
