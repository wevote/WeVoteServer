# apis_v1/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse
from exception.models import handle_exception
import json
from organization.models import Organization, OrganizationManager
from voter.models import BALLOT_ADDRESS, fetch_google_civic_election_id_for_voter_id, \
    fetch_voter_id_from_voter_device_link, Voter, VoterManager, VoterAddressManager, VoterDeviceLinkManager
from voter_guide.models import VoterGuideList
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def is_voter_device_id_valid(voter_device_id):
    if not voter_device_id \
            or len(voter_device_id) <= 70 \
            or len(voter_device_id) >= 90:
        success = False
        json_data = {
            'status': "VALID_VOTER_DEVICE_ID_MISSING",
            'success': False,
            'voter_device_id': voter_device_id,
        }
    else:
        success = True
        json_data = {
            'status': '',
            'success': True,
            'voter_device_id': voter_device_id,
        }

    results = {
        'success': success,
        'json_data': json_data,
    }
    return results


def organization_count():
    organization_count_all = 0
    try:
        organization_list_all = Organization.objects.all()
        organization_count_all = organization_list_all.count()
        success = True

        # We will want to cache a json file and only refresh it every couple of seconds (so it doesn't become
        # a bottle neck as we grow)
    except Exception as e:
        exception_message = "organizationCount: Unable to count list of Organizations from db."
        handle_exception(e, logger=logger, exception_message=exception_message)
        success = False

    json_data = {
        'success': success,
        'organization_count': organization_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


# We retrieve from only one of the two possible variables

def organization_retrieve(organization_id, we_vote_id):
    organization_id = convert_to_int(organization_id)

    we_vote_id = we_vote_id.strip()
    if not positive_value_exists(organization_id) and not positive_value_exists(we_vote_id):
        json_data = {
            'status': "ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING",
            'success': False,
            'organization_id': organization_id,
            'we_vote_id': we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id, we_vote_id)

    if results['organization_found']:
        organization = results['organization']
        json_data = {
            'organization_id': organization.id,
            'we_vote_id': organization.we_vote_id,
            'organization_name': organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_website': organization.organization_website if positive_value_exists(
                organization.organization_website) else '',
            'organization_twitter': organization.twitter_handle if positive_value_exists(organization.twitter_handle) else '',
            'success': True,
            'status': results['status'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status': results['status'],
            'success': False,
            'organization_id': organization_id,
            'we_vote_id': we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


# We are going to start retrieving only the ballot address
# Eventually we will want to allow saving former addresses, and mailing addresses for overseas voters
def voter_address_retrieve(voter_device_id):
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

    voter_address_manager = VoterAddressManager()
    results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)

    if results['voter_address_found']:
        voter_address = results['voter_address']
        json_data = {
            'voter_device_id': voter_device_id,
            'address_type': voter_address.address_type if voter_address.address_type else '',
            'address': voter_address.address if voter_address.address else '',
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


def voter_address_save(voter_device_id, address_raw_text, address_variable_exists):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if not address_variable_exists:
        json_data = {
                'status': "MISSING_POST_VARIABLE-ADDRESS",
                'success': False,
                'voter_device_id': voter_device_id,
            }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id < 0:
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # At this point, we have a valid voter

    voter_address_manager = VoterAddressManager()
    address_type = BALLOT_ADDRESS

    # We wrap get_or_create because we want to centralize error handling
    results = voter_address_manager.update_or_create_voter_address(voter_id, address_type, address_raw_text.strip())
    if results['success']:
        json_data = {
                'status': "VOTER_ADDRESS_SAVED",
                'success': True,
                'voter_device_id': voter_device_id,
                'address': address_raw_text,
            }
    # elif results['status'] == 'MULTIPLE_MATCHING_ADDRESSES_FOUND':
        # delete all currently matching addresses and save again
    else:
        json_data = {
                'status': results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
            }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_count():
    try:
        voter_list_all = Voter.objects.all()
        # In future, add a filter to only show voters who have actually done something
        # voter_list = voter_list.filter(id=voter_id)
        voter_count_all = voter_list_all.count()
        success = True

        # We will want to cache a json file and only refresh it every couple of seconds (so it doesn't become
        # a bottle neck as we grow)
    except Exception as e:
        exception_message = "voterCount: Unable to count list of Voters from db."
        handle_exception(e, logger=logger, exception_message=exception_message)
        success = False

    json_data = {
        'success': success,
        'voter_count': voter_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_create(voter_device_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = 0
    # Make sure a voter record hasn't already been created for this
    existing_voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if existing_voter_id:
        json_data = {
            'status': "VOTER_ALREADY_EXISTS",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # Create a new voter and return the id
    voter_manager = VoterManager()
    results = voter_manager.create_voter()

    if results['voter_created']:
        voter = results['voter']

        # Now save the voter_device_link
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.save_new_voter_device_link(voter_device_id, voter.id)

        if results['voter_device_link_created']:
            voter_device_link = results['voter_device_link']
            voter_id_found = True if voter_device_link.voter_id > 0 else False

            if voter_id_found:
                voter_id = voter_device_link.voter_id

    if voter_id:
        json_data = {
            'status': "VOTER_CREATED",
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_id': voter_id,  # We may want to remove this after initial testing
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status': "VOTER_NOT_CREATED",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guides_to_follow_retrieve(voter_device_id, google_civic_election_id=0):
    # Get voter_device_id from the voter_device_id so we can figure out which voter_guides to offer
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID',
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # If the google_civic_election_id was found cached in a cookie and passed in, use that
    # If not, fetch it for this voter
    if not positive_value_exists(google_civic_election_id):
        google_civic_election_id = fetch_google_civic_election_id_for_voter_id(voter_id)

    voter_guide_list = []
    voter_guides = []
    status = 'ERROR_RETRIEVING_VOTER_GUIDES'
    try:
        voter_guide_list_object = VoterGuideList()
        results = voter_guide_list_object.retrieve_voter_guides_for_election(google_civic_election_id)
        success = results['success']
        status = results['status']
        voter_guide_list = results['voter_guide_list']

    except Exception as e:
        status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                 '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        for voter_guide in voter_guide_list:
            one_voter_guide = {
                'google_civic_election_id': voter_guide.google_civic_election_id,
                'voter_guide_owner_type': voter_guide.voter_guide_owner_type,
                'organization_we_vote_id': voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id': voter_guide.public_figure_we_vote_id,
                'owner_voter_id': voter_guide.owner_voter_id,
                'last_updated': voter_guide.last_updated.strftime('%Y-%m-%d %H:%M'),
            }
            voter_guides.append(one_voter_guide.copy())

        json_data = {
            'status': 'VOTER_GUIDES_TO_FOLLOW_RETRIEVED',
            'success': True,
            'voter_device_id': voter_device_id,
            'voter_guides': voter_guides,
        }
    else:
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_retrieve_list(voter_device_id):
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
