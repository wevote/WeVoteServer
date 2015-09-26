# config/wsgi.py
# Brought to you by We Vote. Be good.
"""
WSGI config for WeVoteServer project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from dj_static import Cling  # For Heroku

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# application = get_wsgi_application() # Without Heroku
application = Cling(get_wsgi_application())  # For Heroku