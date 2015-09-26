# config/local.py (Local Settings)
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .base import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': get_environment_variable('DATABASE_ENGINE'),
        'NAME': get_environment_variable('DATABASE_NAME'),
        'USER': get_environment_variable('DATABASE_USER'),
        'PASSWORD': get_environment_variable('DATABASE_PASSWORD'),
        'HOST': get_environment_variable('DATABASE_HOST'),  # localhost
        'PORT': get_environment_variable('DATABASE_PORT'),  # 5432
    }
}

# ########## Logging configurations ###########
# Logging is configured in the config/environment_variables.json file
