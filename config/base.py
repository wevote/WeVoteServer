# config/base.py (Settings Base, inherited by local.py)
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import os
import re

from config.environment_variable_functions import get_environment_variable, get_environment_variable_default, \
    get_we_vote_server_root_url, convert_logging_level
from wevote_functions.functions import positive_value_exists

# SECURITY WARNING: don't run with debug turned on in production!
# Override in local.py for development
DEBUG = False

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
    'wevotedeveloper.com',
    'localhost',
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
    'challenge',
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
    'import_export_apple_app_store',
    'import_export_ballotpedia',
    'import_export_batches',
    'import_export_bigquery',
    'import_export_ctcl',
    'import_export_endorsements',
    'import_export_facebook',
    'import_export_google_civic',
    'import_export_google_play_store',
    'import_export_jira',
    'import_export_maplight',
    'import_export_open_people',
    'import_export_openreplay',
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
    # 'scheduled_tasks', # April 2024, Disabled for Python 11, could be revived
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
    'wevote_tokens',  # Used for token authentication
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

# Password rules, applied wherever a password is set, including the password reset flow.
# See admin_tools/views_password_reset.py
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# How long a password reset link stays usable. Django's default is 3 days, which is a long time
# for a link that can take over a staff account.
PASSWORD_RESET_TIMEOUT = 60 * 60  # one hour

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
    'http://localhost:8000', 'https://localhost:8000', 'app://localhost',
    'http://wevotedeveloper.com', 'https://wevotedeveloper.com',
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 22000000  # MAX_IMAGE_SIZE (room for 21MB file), but this does not seem to have any effect
DATA_UPLOAD_MAX_NUMBER_FIELDS = 4096

CORS_ORIGIN_WHITELIST = (
    'https://api.wevoteusa.org',
    'http://localhost:8000', 'https://localhost:8000', 'app://localhost',
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


def convert_to_https_dev_url_if_configured(env_var_value):
    try:
        # Production runs in HTTP and takes care of itself, but if running in developer mode, and the default value of a
        # variable (probably from environment_variables-template.json) in http:// is pulled in, this converts them to
        # https if we are running in https mode, (which is the default).
        RUNNING_IN_DEVELOPER_MODE = get_environment_variable_default("RUNNING_IN_DEVELOPER_MODE", False)
        if RUNNING_IN_DEVELOPER_MODE:
            protocol = get_environment_variable('WE_VOTE_SERVER_PROTOCOL', 'https')
            if protocol == 'https' and not env_var_value.startswith('https'):
                pattern = r"http.*?0+(.*?)$"
                match = re.search(pattern, env_var_value)
                if match:
                    path = match.group(1)
                    url_new = f"{get_we_vote_server_root_url()}{path}"
                    # print('url_new', url_new)
                    return url_new
                else:
                    print('Error parsing ' + env_var_value)
                    return env_var_value
    except Exception as e:
        print('Error in convert_to_https_dev_url_if_configured: ' + str(e))
    # print('HTTP Passing on  ' + env_var_value)
    return env_var_value


os.environ["WE_VOTE_SERVER_ROOT_URL"] = get_we_vote_server_root_url()

SOCIAL_AUTH_LOGIN_ERROR_URL = \
    convert_to_https_dev_url_if_configured(get_environment_variable("SOCIAL_AUTH_LOGIN_ERROR_URL"))
os.environ["SOCIAL_AUTH_LOGIN_ERROR_URL"] = SOCIAL_AUTH_LOGIN_ERROR_URL
SOCIAL_AUTH_LOGIN_REDIRECT_URL = \
    convert_to_https_dev_url_if_configured(get_environment_variable("SOCIAL_AUTH_LOGIN_REDIRECT_URL"))
os.environ["SOCIAL_AUTH_LOGIN_REDIRECT_URL"] = SOCIAL_AUTH_LOGIN_REDIRECT_URL
SOCIAL_AUTH_LOGIN_URL = convert_to_https_dev_url_if_configured(get_environment_variable("SOCIAL_AUTH_LOGIN_URL"))
os.environ["SOCIAL_AUTH_LOGIN_URL"] = SOCIAL_AUTH_LOGIN_URL
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

LOGIN_REDIRECT_URL = convert_to_https_dev_url_if_configured(get_environment_variable("LOGIN_REDIRECT_URL"))
os.environ["LOGIN_REDIRECT_URL"] = LOGIN_REDIRECT_URL
LOGIN_ERROR_URL = convert_to_https_dev_url_if_configured(get_environment_variable("LOGIN_ERROR_URL"))
os.environ["LOGIN_ERROR_URL"] = LOGIN_ERROR_URL
LOGIN_URL = convert_to_https_dev_url_if_configured(get_environment_variable("LOGIN_URL"))
os.environ["LOGIN_URL"] = LOGIN_URL


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
SENDGRID_SANDBOX_MODE = \
    positive_value_exists(get_environment_variable("SENDGRID_SANDBOX_MODE", no_exception=True))
SENDGRID_SANDBOX_MODE_IN_DEBUG = \
    positive_value_exists(get_environment_variable("SENDGRID_SANDBOX_MODE_IN_DEBUG", no_exception=True))
SYSTEM_SENDER_EMAIL_ADDRESS = get_environment_variable("SYSTEM_SENDER_EMAIL_ADDRESS", no_exception=True)
# ADMIN_EMAIL_ADDRESSES = get_environment_variable("ADMIN_EMAIL_ADDRESSES")
# # Expecting a space delimited string of emails like "jane@wevote.us" or "jane@wevote.us bill@wevote.us"
# ADMIN_EMAIL_ADDRESSES_ARRAY = []
# if ADMIN_EMAIL_ADDRESSES:
#     # ADMINS is used by lib/python3.6/lib/site-packages/django/core/mail/INIT.py
#     ADMINS = [[email.split('@')[0], email] for email in ADMIN_EMAIL_ADDRESSES.split()]


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
