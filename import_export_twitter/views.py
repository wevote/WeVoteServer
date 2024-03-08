# import_export_twitter/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/views.py for routines that manage internal twitter data

from config.base import get_environment_variable

TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
