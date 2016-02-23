# voter/utils.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Voter
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def authenticate_associate_by_email(**kwargs):
    try:
        # TODO Twitter doesn't verify email addresses? If true then a voter could create a Twitter account with
        #  someone else's email account and take over their We Vote account
        email = kwargs['details']['email']
        kwargs['user'] = Voter.objects.get(email=email)
    except:
        pass
    return kwargs
