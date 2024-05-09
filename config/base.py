# config/base.py (Settings Base, inherited by local.py)
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json
import os

from django.core.exceptions import ImproperlyConfigured

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


def get_environment_variable(var_name, json_environment_vars=json_environment_variables, no_exception=False):
    """
    Get the environment variable or return exception. Don't return exception if no_exception is True
    """
    try:
        # Environment variables can be set with this for example: export GOOGLE_CIVIC_API_KEY=<API KEY HERE>
        val = os.environ[var_name]
        # handle boolean variables; return bool value when string is "true" or "false"
        try:
            if val.lower() == 'true':
                return True
            elif val.lower() == 'false':
                return False
        except Exception as e:
            pass
        return val
    except KeyError:
        pass

    if json_environment_vars:
        if var_name in json_environment_vars:
            val = json_environment_vars[var_name]
            # handle boolean variables; return bool value when string is "true" or "false"
            try:
                if val.lower() == 'true':
                    return True
                elif val.lower() == 'false':
                    return False
            except Exception as e:
                pass
            return val
        else:
            variable_not_found = True
    else:
        variable_not_found = True

    if variable_not_found:
        # Can't use logger in the settings file due to loading sequence
        error_message = "ERROR: Unable to set the {} variable from os.environ or JSON file".format(var_name)
        try:
            import logging
            logging.error(error_message)
        except Exception as e:
            pass
        if no_exception:
            return ''
        else:
            raise ImproperlyConfigured(error_message)
    else:
        return ''


def get_environment_variable_default(var_name, default_value):
    if var_name in json_environment_variables:
        return json_environment_variables[var_name]

    try:
        return os.environ[var_name]
    except KeyError:
        return default_value


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_STATIC_DIR = BASE_DIR + '/static'

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Consider switching to the way that Two Scoops of Django 1.8 suggests file path handling, section 5.6

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_environment_variable("SECRET_KEY")

# Comment out when running Heroku
ALLOWED_HOSTS = [
    'api.wevoteusa.org',
    'localhost',
    'wevotedeveloper.com',
    '127.0.0.1'
]

# Application definition
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.humanize',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # only used for developer environments
    'sslserver',

    # third party
    # 'background_task',
    'bootstrap3',
    'corsheaders',  # cross origin requests
    'mathfilters',
    'social_django',  # Installed with `pip install social-auth-app-django`

    # project specific
    'activity',
    'admin_tools',
    'analytics',
    'api_internal_cache',
    'apis_v1',
    'apple',
    'aws',
    'ballot',
    'bookmark',
    'campaign',
    'candidate',
    'config',
    'donate',
    'election',
    'electoral_district',
    'email_outbound',
    'exception',
    'follow',
    'friend',
    'geoip',
    'google_custom_search',
    'googlebot_site_map',
    'image',
    'import_export_ballotpedia',
    'import_export_batches',
    'import_export_ctcl',
    'import_export_endorsements',
    'import_export_facebook',
    'import_export_google_civic',
    'import_export_maplight',
    'import_export_open_people',
    'import_export_snovio',
    'import_export_targetsmart',
    'import_export_twitter',  # See also twitter (below)
    'import_export_vertex',
    'import_export_vote_smart',
    'import_export_vote_usa',
    'import_export_wikipedia',
    'issue',
    'measure',
    'office',
    'office_held',
    'organization',
    'party',
    'pledge_to_vote',
    'politician',
    'polling_location',
    'position',
    'quick_info',
    'reaction',
    'representative',
    'rest_framework',    # Jan 2019, looks abandoned
    'retrieve_tables',
    # 'scheduled_tasks',  # April 2024, Disabled for Python 11, could be revived
    'search',
    'share',
    'sms',
    'stripe_donations',
    'stripe_ip_history',
    'support_oppose_deciding',
    'tag',
    'twitter',  # See also import_export_twitter
    'volunteer_task',
    'voter',  # See also AUTH_USER_MODEL in config/settings.py
    'voter_guide',
    'wevote_functions',
    'wevote_settings',
    'wevote_social',
)

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    # 'corsheaders.middleware.CorsPostCsrfMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'wevote_social.middleware.SocialMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'social_core.backends.facebook.FacebookOAuth2',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.twitter.TwitterOAuth',
    'django.contrib.auth.backends.ModelBackend',
)

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'templates/candidate'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',  # Django Cookbook
                'django.template.context_processors.static',  # Django Cookbook
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'wevote_social.context_processors.profile_photo',
            ],
        },
    },
]

# WSGI_APPLICATION = 'config.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = get_environment_variable("TIME_ZONE")

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Described here: https://docs.djangoproject.com/en/1.8/topics/auth/customizing/#a-full-example
AUTH_USER_MODEL = 'voter.Voter'

# Static files (CSS, JavaScript, Images) Django 5+
STATIC_URL = 'static/'      # April 2024, don't think this is correct, but can't run without it
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'apis_v1', 'static'),
]

MEDIA_URL = '/media/'  # Django Cookbook
MEDIA_ROOT = os.path.join(PROJECT_PATH, "static", "media")  # Django Cookbook
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'        # Added for Django 3.2, June 2021

# We want to default to cookie storage of messages so we don't overload our app servers with session data
MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'

# Default settings described here: http://django-bootstrap3.readthedocs.org/en/latest/settings.html
BOOTSTRAP3 = {

    # The URL to the jQuery JavaScript file
    'jquery_url': '//code.jquery.com/jquery.min.js',

    # The Bootstrap base URL
    'base_url': '//maxcdn.bootstrapcdn.com/bootstrap/3.3.4/',

    # The complete URL to the Bootstrap CSS file (None means derive it from base_url)
    'css_url': '//maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css',

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

CORS_ORIGIN_ALLOW_ALL = True  # CORS_ORIGIN_ALLOW_ALL: if True, the whitelist will not be used & all origins accepted
CORS_ALLOW_CREDENTIALS = True
# specify whether to replace the HTTP_REFERER header if CORS checks pass so that CSRF django middleware checks
# will work with https
# April 2024: 4.0.0 (2023-05-12) drops the following two settings
# CORS_REPLACE_HTTPS_REFERER = True
CSRF_TRUSTED_ORIGINS = [
    'https://api.wevoteusa.org',
    'http://localhost:8000', 'https://localhost:8000',
    'http://wevotedeveloper.com', 'https://wevotedeveloper.com',
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 6000000
DATA_UPLOAD_MAX_NUMBER_FIELDS = 4096

CORS_ORIGIN_WHITELIST = (
    'https://api.wevoteusa.org',
    'http://localhost:8000', 'https://localhost:8000',
    'http://wevotedeveloper.com', 'https://wevotedeveloper.com',
)
# CORS_ALLOW_HEADERS = (
#     'access-control-allow-headers',
#     'access-control-allow-methods',
#     'access-control-allow-origin',
#     'x-requested-with',
#     'content-type',
#     'accept',
#     'origin',
#     'authorization',
#     'x-csrftoken',
#     'x-api-key'
# )

SOCIAL_AUTH_FACEBOOK_KEY = get_environment_variable_default(            # for social-auth app
                "SOCIAL_AUTH_FACEBOOK_APP_ID", get_environment_variable_default("SOCIAL_AUTH_FACEBOOK_KEY", ""))
SOCIAL_AUTH_FACEBOOK_SECRET = get_environment_variable_default(         # for social-auth app
                "SOCIAL_AUTH_FACEBOOK_APP_SECRET", get_environment_variable_default("SOCIAL_AUTH_FACEBOOK_SECRET", ""))
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']  # , 'user_friends'

SOCIAL_AUTH_TWITTER_KEY = get_environment_variable("SOCIAL_AUTH_TWITTER_KEY")
SOCIAL_AUTH_TWITTER_SECRET = get_environment_variable("SOCIAL_AUTH_TWITTER_SECRET")

SOCIAL_AUTH_LOGIN_ERROR_URL = get_environment_variable("SOCIAL_AUTH_LOGIN_ERROR_URL")
SOCIAL_AUTH_LOGIN_REDIRECT_URL = get_environment_variable("SOCIAL_AUTH_LOGIN_REDIRECT_URL")
SOCIAL_AUTH_LOGIN_URL = get_environment_variable("SOCIAL_AUTH_LOGIN_URL")
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

LOGIN_REDIRECT_URL = get_environment_variable("LOGIN_REDIRECT_URL")
LOGIN_ERROR_URL = get_environment_variable("LOGIN_ERROR_URL")
LOGIN_URL = get_environment_variable("LOGIN_URL")

SOCIAL_AUTH_URL_NAMESPACE = 'social'

# See description of authentication pipeline:
# https://github.com/omab/python-social-auth/blob/master/docs/pipeline.rst
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    # 'social_core.pipeline.social_auth.social_user',
    'wevote_social.utils.social_user',  # Order in this pipeline matters
    'wevote_social.utils.authenticate_associate_by_email',  # Order in this pipeline matters
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'wevote_social.utils.switch_user'  # Order in this pipeline matters
)

SOCIAL_AUTH_FACEBOOK_EXTRA_DATA = [
    ('name', 'name'),
    ('email', 'email'),
    ('picture', 'picture'),
    ('link', 'profile_url'),
]

EMAIL_BACKEND = get_environment_variable("EMAIL_BACKEND")
SENDGRID_API_KEY = get_environment_variable("SENDGRID_API_KEY")
# ADMIN_EMAIL_ADDRESSES = get_environment_variable("ADMIN_EMAIL_ADDRESSES")
# # Expecting a space delimited string of emails like "jane@wevote.us" or "jane@wevote.us bill@wevote.us"
# ADMIN_EMAIL_ADDRESSES_ARRAY = []
# if ADMIN_EMAIL_ADDRESSES:
#     # ADMINS is used by lib/python3.6/lib/site-packages/django/core/mail/INIT.py
#     ADMINS = [[email.split('@')[0], email] for email in ADMIN_EMAIL_ADDRESSES.split()]


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
GEOIP_PATH = os.path.join(BASE_DIR, 'geoip', 'import_data')
GEOIP_COUNTRY = 'GeoIP.dat'
if os.path.exists(os.path.join(GEOIP_PATH, 'GeoIPCity.dat')):
    GEOIP_CITY = 'GeoIPCity.dat'  # use the paid db
else:
    GEOIP_CITY = 'GeoLiteCity.dat'  # use the free db
