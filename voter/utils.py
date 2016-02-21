# voter/utils.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Voter, VoterDeviceLinkManager
from wevote_functions.functions import get_voter_api_device_id
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


def transfer_voter_device_id_to_different_voter_account(request):  # TODO DALE Not working yet
    try:
        voter_api_device_id = get_voter_api_device_id(request)

        # Relink this voter_api_device_id to this Voter account
        voter_device_manager = VoterDeviceLinkManager()
        voter_device_link_results = voter_device_manager.retrieve_voter_device_link(voter_api_device_id)
        voter_device_link = voter_device_link_results['voter_device_link']

        update_voter_device_link_results = voter_device_manager.update_voter_device_link(
            voter_device_link, kwargs['user'])
        # if update_voter_device_link_results['voter_device_link_updated']:
        #     status += "FACEBOOK_SIGN_IN-ALREADY_LINKED_TO_OTHER_ACCOUNT-TRANSFERRED "
        #     success = True
        # else:
        #     status = "FACEBOOK_SIGN_IN-ALREADY_LINKED_TO_OTHER_ACCOUNT-COULD_NOT_TRANSFER "
        #     success = False
    except:
        pass
    return kwargs
