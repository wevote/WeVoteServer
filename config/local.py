# config/local.py (Local Settings)
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .base import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_environment_variable('SERVER_IN_DEBUG_MODE')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

# Multiple Databases
# See https://docs.djangoproject.com/en/1.10/topics/db/multi-db/#defining-your-databases
# August 2017: Not setting DATABASE_ROUTERS at this time, instead going with ".using('readonly')" on individual queries

DATABASES = {
    'default': {
        'ENGINE':   get_environment_variable('DATABASE_ENGINE'),
        'NAME':     get_environment_variable('DATABASE_NAME'),
        'USER':     get_environment_variable('DATABASE_USER'),
        'PASSWORD': get_environment_variable('DATABASE_PASSWORD'),
        'HOST':     get_environment_variable('DATABASE_HOST'),  # localhost
        'PORT':     get_environment_variable('DATABASE_PORT'),  # 5432
    },
    'readonly': {
        'ENGINE': get_environment_variable('DATABASE_ENGINE_READONLY'),
        'NAME': get_environment_variable('DATABASE_NAME_READONLY'),
        'USER': get_environment_variable('DATABASE_USER_READONLY'),
        'PASSWORD': get_environment_variable('DATABASE_PASSWORD_READONLY'),
        'HOST': get_environment_variable('DATABASE_HOST_READONLY'),
        'PORT': get_environment_variable('DATABASE_PORT_READONLY'),
    }
}

ALLOWED_HOSTS = ['*']

# ########## Logging configurations ###########
# Logging is configured in the config/environment_variables.json file
