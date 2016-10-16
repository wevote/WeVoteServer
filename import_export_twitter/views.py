# import_export_twitter/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/twitter/views.py for routines that manage internal twitter data

from config.base import get_environment_variable
from django.http import HttpResponseRedirect
import tweepy
from voter.models import VoterManager
from wevote_functions.functions import positive_value_exists

TWITTER_CONSUMER_KEY = get_environment_variable("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = get_environment_variable("TWITTER_CONSUMER_SECRET")
