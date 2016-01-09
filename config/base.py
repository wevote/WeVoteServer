# config/base.py (Settings Base, inherited by local.py)
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
##import logging
import os
from django.core.exceptions import ImproperlyConfigured
# Consider switching to the way that Two Scoops of Django 1.8 suggests file path handling, section 5.6
# from unipath import Path


# SECURITY WARNING: don't run with debug turned on in production!
# Override in local.py for development
DEBUG = False

# Load JSON-based environment_variables if available
json_environment_variables = {}
try:
    with open("config/environment_variables.json") as f:
        json_environment_variables = json.loads(f.read())
except Exception as e:
    pass
    # print "base.py: environment_variables.json missing"
    # Can't use logger in the settings file due to loading sequence


def get_environment_variable(var_name, json_environment_vars=json_environment_variables):
    """
    Get the environment variable or return exception.
    From Two Scoops of Django 1.8, section 5.3.4
    """
    try:
        return json_environment_vars[var_name]  # Loaded from array above
    except KeyError:
        # variable wasn't found in the JSON environment variables file, so now look in the server environment variables
        pass
        # print "base.py: failed to load {} from JSON file".format(var_name)  # Can't use logger in the settings file

    try:
        # Environment variables can be set with this for example: export GOOGLE_CIVIC_API_KEY=<API KEY HERE>
        return os.environ[var_name]
    except KeyError:
        # Can't use logger in the settings file due to loading sequence
        error_msg = "Unable to set the {} variable from os.environ or JSON file".format(var_name)
        raise ImproperlyConfigured(error_msg)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Consider switching to the way that Two Scoops of Django 1.8 suggests file path handling, section 5.6

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_environment_variable("SECRET_KEY")

# Comment out when running Heroku
ALLOWED_HOSTS = [
    'localhost'
]


# Application definition

INSTALLED_APPS = (

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third party
    'bootstrap3',
    'corsheaders', # cross origin requests
    'social.apps.django_app.default',

    # project specific
    'admin_tools',
    'apis_v1',
    'ballot',
    'candidate',
    'config',
    'election',
    'exception',
    'follow',
    'import_export_google_civic',
    'import_export_vote_smart',
    'measure',
    'office',
    'organization',
    'politician',
    'polling_location',
    'position',
    'position_like',
    'quick_info',
    'rest_framework',
    'support_oppose_deciding',
    'star',
    'tag',
    'twitter',
    'voter',  # See also AUTH_USER_MODEL in config/settings.py
    'voter_guide',
    'wevote_functions',
    'wevote_settings',
    'wevote_social',

)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'wevote_social.middleware.SocialMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.twitter.TwitterOAuth',
    'django.contrib.auth.backends.ModelBackend',
)

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',  # Django Cookbook
                'django.template.context_processors.static',  # Django Cookbook
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
                'wevote_social.context_processors.profile_photo',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Described here: https://docs.djangoproject.com/en/1.8/topics/auth/customizing/#a-full-example
AUTH_USER_MODEL = 'voter.Voter'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_PATH, "static", "static")  # Django Cookbook
MEDIA_URL = '/media/'  # Django Cookbook
MEDIA_ROOT = os.path.join(PROJECT_PATH, "static", "media")  # Django Cookbook

# We want to default to cookie storage of messages so we don't overload our app servers with session data
MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

# Default settings described here: http://django-bootstrap3.readthedocs.org/en/latest/settings.html
BOOTSTRAP3 = {

    # The URL to the jQuery JavaScript file
    'jquery_url': '//code.jquery.com/jquery.min.js',

    # The Bootstrap base URL
    'base_url': '//maxcdn.bootstrapcdn.com/bootstrap/3.3.4/',

    # The complete URL to the Bootstrap CSS file (None means derive it from base_url)
    'css_url': None,

    # The complete URL to the Bootstrap CSS file (None means no theme)
    'theme_url': None,

    # The complete URL to the Bootstrap JavaScript file (None means derive it from base_url)
    'javascript_url': None,

    # Put JavaScript in the HEAD section of the HTML document (only relevant if you use bootstrap3.html)
    'javascript_in_head': False,

    # Include jQuery with Bootstrap JavaScript (affects django-bootstrap3 template tags)
    'include_jquery': False,

    # Label class to use in horizontal forms
    'horizontal_label_class': 'col-md-3',

    # Field class to use in horizontal forms
    'horizontal_field_class': 'col-md-9',

    # Set HTML required attribute on required fields
    'set_required': True,

    # Set HTML disabled attribute on disabled fields
    'set_disabled': False,

    # Set placeholder attributes to label if no placeholder is provided
    'set_placeholder': True,

    # Class to indicate required (better to set this in your Django form)
    'required_css_class': '',

    # Class to indicate error (better to set this in your Django form)
    'error_css_class': 'has-error',

    # Class to indicate success, meaning the field has valid input (better to set this in your Django form)
    'success_css_class': 'has-success',

    # Renderers (only set these if you have studied the source and understand the inner workings)
    'formset_renderers': {
        'default': 'bootstrap3.renderers.FormsetRenderer',
    },
    'form_renderers': {
        'default': 'bootstrap3.renderers.FormRenderer',
    },
    'field_renderers': {
        'default': 'bootstrap3.renderers.FieldRenderer',
        'inline': 'bootstrap3.renderers.InlineFieldRenderer',
    },
}

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

LOGIN_URL = '/login/'

LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_FACEBOOK_KEY = get_environment_variable("SOCIAL_AUTH_FACEBOOK_KEY")
SOCIAL_AUTH_FACEBOOK_SECRET = get_environment_variable("SOCIAL_AUTH_FACEBOOK_SECRET")
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email', 'user_friends']
SOCIAL_AUTH_TWITTER_KEY = get_environment_variable("SOCIAL_AUTH_TWITTER_KEY")
SOCIAL_AUTH_TWITTER_SECRET = get_environment_variable("SOCIAL_AUTH_TWITTER_SECRET")
SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'social.pipeline.social_auth.associate_by_email',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details'
)


# ########## Logging configurations ###########
#   LOG_STREAM          Boolean     True will turn on stream handler and write to command line.
#   LOG_FILE            String      Path to file to write to. Make sure executing
#                                   user has permissions.
#   LOG_STREAM_LEVEL    Integer     Log level of stream handler: CRITICAL, ERROR, INFO, WARN, DEBUG
#   LOG_FILE_LEVEL      Integer     Log level of file handler: CRITICAL, ERROR, INFO, WARN, DEBUG
#   NOTE: These should be set in the environment_variables.json file
def convert_logging_level(log_level_text_descriptor):
    import logging
    # Assume error checking has been done and that the string is a valid logging level
    if log_level_text_descriptor == "CRITICAL":
        return logging.CRITICAL
    if log_level_text_descriptor == "ERROR":
        return logging.ERROR
    if log_level_text_descriptor == "INFO":
        return logging.INFO
    if log_level_text_descriptor == "WARN":
        return logging.WARN
    if log_level_text_descriptor == "DEBUG":
        return logging.DEBUG


def lookup_logging_level(log_level_text_descriptor, log_level_default="ERROR"):
    import logging
    available_logging_levels = ["CRITICAL", "ERROR", "INFO", "WARN", "DEBUG"]

    if log_level_text_descriptor.upper() in available_logging_levels:
        # print "log_level_text_descriptor: {}".format(log_level_text_descriptor)
        return convert_logging_level(log_level_text_descriptor)
    else:
        # The log_level_text_descriptor is not a valid level, so use the debug level
        if log_level_default.upper() in available_logging_levels:
            # print "log_level_default: {}".format(log_level_default)
            return convert_logging_level(log_level_default)
        else:
            # print "log_level failure default: {}".format("ERROR")
            return logging.ERROR


# Which level of logging event should get written to the command line?
LOG_STREAM = get_environment_variable('LOG_STREAM')  # Turn command line logging on or off
# print "Current LOG_STREAM_LEVEL setting:"
LOG_STREAM_LEVEL = lookup_logging_level(get_environment_variable("LOG_STREAM_LEVEL"), "DEBUG")
# Which level of logging event should get written to the log file?
LOG_FILE = get_environment_variable('LOG_FILE')  # Location of the log file
LOG_FILE_LEVEL = lookup_logging_level(get_environment_variable("LOG_FILE_LEVEL"), "ERROR")
# print "Current LOG_FILE_LEVEL setting:"

# Using conventions from django.contrib:
# https://docs.djangoproject.com/en/1.8/ref/contrib/gis/geoip/#geoip-settings
GEOIP_PATH = os.path.join(BASE_DIR, 'geo', 'data')
GEOIP_COUNTRY = 'GeoIP.dat'
GEOIP_CITY = 'GeoLiteCity.dat'
