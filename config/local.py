# config/local.py (Local Settings)
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .base import *  # Needed to bring in settings like: settings.ROOT_URLCONF
from config.environment_variable_functions import get_environment_variable, get_environment_variable_default
from wevote_functions.functions import positive_value_exists


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = positive_value_exists(get_environment_variable('SERVER_IN_DEBUG_MODE'))

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
        'ENGINE':   get_environment_variable('DATABASE_ENGINE_READONLY'),
        'NAME':     get_environment_variable('DATABASE_NAME_READONLY'),
        'USER':     get_environment_variable('DATABASE_USER_READONLY'),
        'PASSWORD': get_environment_variable('DATABASE_PASSWORD_READONLY'),
        'HOST':     get_environment_variable('DATABASE_HOST_READONLY'),
        'PORT':     get_environment_variable('DATABASE_PORT_READONLY'),
        'TEST': {
            'MIRROR': 'default',
        }
    },
    'analytics': {
        'ENGINE':   get_environment_variable('DATABASE_ENGINE_ANALYTICS'),
        'NAME':     get_environment_variable('DATABASE_NAME_ANALYTICS'),
        'USER':     get_environment_variable('DATABASE_USER_ANALYTICS'),
        'PASSWORD': get_environment_variable('DATABASE_PASSWORD_ANALYTICS'),
        'HOST':     get_environment_variable('DATABASE_HOST_ANALYTICS'),
        'PORT':     get_environment_variable('DATABASE_PORT_ANALYTICS'),
        'TEST': {
            'MIRROR': 'default',
        }
    }
}

if DEBUG:
    cache_backend_name = get_environment_variable_default('DATABASE_ENGINE_CACHE', 'django.core.cache.backends.db.DatabaseCache')
    cache_table_name = 'cache_table_debug_' + get_environment_variable_default('DATABASE_CACHE_LOCATION', 'dev_wevote_server')
    ALLOWED_HOSTS = ['*']
else:
    cache_backend_name = get_environment_variable('DATABASE_ENGINE_CACHE')
    cache_table_name = get_environment_variable('DATABASE_CACHE_LOCATION')

CACHES = {
    "default": {
        "BACKEND": cache_backend_name,
        "LOCATION": cache_table_name,
    }
}

# ########## Logging configurations ###########
# Logging is configured in the config/environment_variables.json file
