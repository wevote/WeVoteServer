# voter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BALLOT_ADDRESS, fetch_voter_id_from_voter_device_link, Voter, VoterAddressManager, VoterManager
from django.http import HttpResponse
import json
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# We are going to start retrieving only the ballot address
# Eventually we will want to allow saving former addresses, and mailing addresses for overseas voters
def voter_address_retrieve_for_api(voter_device_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not voter_id > 0:
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # ##################
    # Temp code to test authentication
    # user = PasswordlessAuthBackend.authenticate(username=user.username)
    # login(request, user)
    # ##################

    voter_address_manager = VoterAddressManager()
    results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)

    if results['voter_address_found']:
        voter_address = results['voter_address']
        json_data = {
            'voter_device_id': voter_device_id,
            'address_type': voter_address.address_type if voter_address.address_type else '',
            'text_for_map_search': voter_address.text_for_map_search if voter_address.text_for_map_search else '',
            'latitude': voter_address.latitude if voter_address.latitude else '',
            'longitude': voter_address.longitude if voter_address.longitude else '',
            'normalized_line1': voter_address.normalized_line1 if voter_address.normalized_line1 else '',
            'normalized_line2': voter_address.normalized_line2 if voter_address.normalized_line2 else '',
            'normalized_city': voter_address.normalized_city if voter_address.normalized_city else '',
            'normalized_state': voter_address.normalized_state if voter_address.normalized_state else '',
            'normalized_zip': voter_address.normalized_zip if voter_address.normalized_zip else '',
            'success': True,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status': "VOTER_ADDRESS_NOT_RETRIEVED",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_address_save_for_api(voter_device_id, address_raw_text, address_variable_exists):
    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        results = {
                'status': device_id_results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
            }
        return results

    if not address_variable_exists:
        results = {
                'status': "MISSING_POST_VARIABLE-ADDRESS",
                'success': False,
                'voter_device_id': voter_device_id,
            }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id < 0:
        results = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return results

    # At this point, we have a valid voter

    voter_address_manager = VoterAddressManager()
    address_type = BALLOT_ADDRESS

    # We wrap get_or_create because we want to centralize error handling
    results = voter_address_manager.update_or_create_voter_address(voter_id, address_type, address_raw_text.strip())

    if results['success']:
        if positive_value_exists(address_raw_text):
            status = "VOTER_ADDRESS_SAVED"
        else:
            status = "VOTER_ADDRESS_EMPTY_SAVED"

        results = {
                'status': status,
                'success': True,
                'voter_device_id': voter_device_id,
                'text_for_map_search': address_raw_text,
            }

    # elif results['status'] == 'MULTIPLE_MATCHING_ADDRESSES_FOUND':
        # delete all currently matching addresses and save again
    else:
        results = {
                'status': results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
            }
    return results


def voter_retrieve_list_for_api(voter_device_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results2 = {
            'success': False,
            'json_data': results['json_data'],
        }
        return results2

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id > 0:
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter_id = results['voter_id']
    else:
        # If we are here, the voter_id could not be found from the voter_device_id
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        results = {
            'success': False,
            'json_data': json_data,
        }
        return results

    if voter_id:
        voter_list = Voter.objects.all()
        voter_list = voter_list.filter(id=voter_id)

        if len(voter_list):
            results = {
                'success': True,
                'voter_list': voter_list,
            }
            return results

    # Trying to mimic the Google Civic error codes scheme
    errors_list = [
        {
            'domain':  "TODO global",
            'reason':  "TODO reason",
            'message':  "TODO Error message here",
            'locationType':  "TODO Error message here",
            'location':  "TODO location",
        }
    ]
    error_package = {
        'errors':   errors_list,
        'code':     400,
        'message':  "Error message here",
    }
    json_data = {
        'error': error_package,
        'status': "VOTER_ID_COULD_NOT_BE_RETRIEVED",
        'success': False,
        'voter_device_id': voter_device_id,
    }
    results = {
        'success': False,
        'json_data': json_data,
    }
    return results
