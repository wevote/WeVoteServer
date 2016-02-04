# config/settings.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

"""
Django settings for WeVoteServer project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

try:
    # If the WeVoteServer/config/production.py file exists, use it
    from config.production import *
except ImportError as e:
    try:
        from config.local import *
    except ImportError as e:
        pass
