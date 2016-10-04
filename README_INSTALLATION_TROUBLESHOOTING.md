# README for API Installation Troubleshooting

[Back to root README](README.md)

[Back to README for API Installation](README_API_INSTALL.md)

## Unable to set the SECRET_KEY variable

Problem: I see this error when I run this `python manage.py runserver`:

    django.core.exceptions.ImproperlyConfigured: Unable to set the SECRET_KEY variable from os.environ or JSON file
    
Solution: 

1. Look in WeVoteServer/config

2. Make sure you made a copy from `environment_variables-template.json` to `environment_variables.json`