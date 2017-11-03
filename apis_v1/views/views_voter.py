# apis_v1/views/views_voter.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from apis_v1.controllers import voter_count
from ballot.controllers import choose_election_from_existing_data, voter_ballot_items_retrieve_for_api
from config.base import get_environment_variable
from django.http import HttpResponse
from django_user_agents.utils import get_user_agent
from email_outbound.controllers import voter_email_address_save_for_api, voter_email_address_retrieve_for_api, \
    voter_email_address_sign_in_for_api, voter_email_address_verify_for_api
from wevote_functions.functions import extract_first_name_from_full_name, extract_last_name_from_full_name
from follow.controllers import voter_issue_follow_for_api
from geoip.controllers import voter_location_retrieve_from_ip_for_api
from image.controllers import TWITTER, FACEBOOK, cache_master_and_resized_image
from import_export_facebook.controllers import voter_facebook_sign_in_retrieve_for_api, \
    voter_facebook_sign_in_save_for_api
from import_export_google_civic.controllers import voter_ballot_items_retrieve_from_google_civic_for_api
from import_export_twitter.controllers import voter_twitter_save_to_current_account_for_api
import json
from position.controllers import voter_all_positions_retrieve_for_api, \
    voter_position_retrieve_for_api, voter_position_comment_save_for_api, voter_position_visibility_save_for_api
from position_like.controllers import voter_position_like_off_save_for_api, \
    voter_position_like_on_save_for_api, voter_position_like_status_retrieve_for_api
from ballot.controllers import choose_election_and_prepare_ballot_data, voter_ballot_list_retrieve_for_api
from ballot.models import OFFICE, CANDIDATE, MEASURE, VoterBallotSavedManager
from bookmark.controllers import voter_all_bookmarks_status_retrieve_for_api, voter_bookmark_off_save_for_api, \
    voter_bookmark_on_save_for_api, voter_bookmark_status_retrieve_for_api
from support_oppose_deciding.controllers import voter_opposing_save, voter_stop_opposing_save, \
    voter_stop_supporting_save, voter_supporting_save_for_api
from voter.controllers import voter_address_retrieve_for_api, voter_create_for_api, voter_merge_two_accounts_for_api, \
    voter_photo_save_for_api, voter_retrieve_for_api, voter_retrieve_list_for_api, voter_sign_out_for_api, \
    voter_split_into_two_accounts_for_api
from voter.models import BALLOT_ADDRESS, fetch_voter_id_from_voter_device_link, VoterAddress, \
    VoterAddressManager, VoterDeviceLink, VoterDeviceLinkManager, VoterManager
from voter_guide.controllers import voter_guide_possibility_retrieve_for_api, voter_guide_possibility_save_for_api, \
    voter_guides_followed_retrieve_for_api, voter_guides_ignored_retrieve_for_api, \
    voter_guides_to_follow_retrieve_for_api, voter_guides_followed_by_organization_retrieve_for_api, \
    voter_guide_followers_retrieve_for_api, voter_follow_all_organizations_followed_by_organization_for_api
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_maximum_number_to_retrieve_from_request, \
    get_voter_device_id, is_voter_device_id_valid, positive_value_exists
from donate.controllers import donation_history_for_a_voter

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def voter_address_retrieve_view(request):  # voterAddressRetrieve
    """
    Retrieve an address for this voter so we can figure out which ballot to display
    :param request:
    :return:
    """
    voter_address_manager = VoterAddressManager()
    voter_device_link_manager = VoterDeviceLinkManager()

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if voter_device_link_results['voter_device_link_found']:
        voter_device_link = voter_device_link_results['voter_device_link']
        voter_id = voter_device_link.voter_id
    else:
        voter_device_link = VoterDeviceLink()
        voter_id = 0

    guess_if_no_address_saved = request.GET.get('guess_if_no_address_saved', True)
    if guess_if_no_address_saved == 'false':
        guess_if_no_address_saved = False
    elif guess_if_no_address_saved == 'False':
        guess_if_no_address_saved = False
    elif guess_if_no_address_saved == '0':
        guess_if_no_address_saved = False
    status = ''

    voter_address_retrieve_results = voter_address_retrieve_for_api(voter_device_id)

    if voter_address_retrieve_results['address_found']:
        status += voter_address_retrieve_results['status']
        if positive_value_exists(voter_address_retrieve_results['google_civic_election_id']):
            google_civic_election_id = voter_address_retrieve_results['google_civic_election_id']
        else:
            # This block of code helps us if the google_civic_election_id hasn't been saved in the voter_address table
            # We retrieve voter_device_link
            google_civic_election_id = 0

        # Retrieve the voter_address
        voter_address_results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
        if voter_address_results['voter_address_found']:
            voter_address = voter_address_results['voter_address']
        else:
            voter_address = VoterAddress()

        results = choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id,
                                                          voter_address)
        status += results['status']
        if results['voter_ballot_saved_found']:
            google_civic_election_id = results['google_civic_election_id']

        json_data = {
            'voter_device_id': voter_address_retrieve_results['voter_device_id'],
            'address_type': voter_address_retrieve_results['address_type'],
            'text_for_map_search': voter_address_retrieve_results['text_for_map_search'],
            'google_civic_election_id': google_civic_election_id,
            'ballot_location_display_name': voter_address_retrieve_results['ballot_location_display_name'],
            'ballot_returned_we_vote_id': voter_address_retrieve_results['ballot_returned_we_vote_id'],
            'voter_entered_address': voter_address_retrieve_results['voter_entered_address'],
            'voter_specific_ballot_from_google_civic':
                voter_address_retrieve_results['voter_specific_ballot_from_google_civic'],
            'latitude': voter_address_retrieve_results['latitude'],
            'longitude': voter_address_retrieve_results['longitude'],
            'normalized_line1': voter_address_retrieve_results['normalized_line1'],
            'normalized_line2': voter_address_retrieve_results['normalized_line2'],
            'normalized_city': voter_address_retrieve_results['normalized_city'],
            'normalized_state': voter_address_retrieve_results['normalized_state'],
            'normalized_zip': voter_address_retrieve_results['normalized_zip'],
            'success': voter_address_retrieve_results['success'],
            'status': voter_address_retrieve_results['status'],
            'address_found': voter_address_retrieve_results['address_found'],
            'guess_if_no_address_saved': guess_if_no_address_saved,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    status += voter_address_retrieve_results['status'] + ", "

    # If we are here, then an address wasn't found, and we either want to return that info, or take a guess
    #  at the voter's location by looking it up by IP address
    if not positive_value_exists(guess_if_no_address_saved):
        # Do not guess at an address
        status += 'DO_NOT_GUESS_IF_NO_ADDRESS_SAVED'
        json_data = {
            'voter_device_id': voter_device_id,
            'address_type': '',
            'text_for_map_search': '',
            'google_civic_election_id': 0,
            'ballot_location_display_name': '',
            'voter_entered_address': False,
            'voter_specific_ballot_from_google_civic': False,
            'ballot_returned_we_vote_id': '',
            'latitude': '',
            'longitude': '',
            'normalized_line1': '',
            'normalized_line2': '',
            'normalized_city': '',
            'normalized_state': '',
            'normalized_zip': '',
            'success': voter_address_retrieve_results['success'],
            'status': voter_address_retrieve_results['status'],
            'address_found': voter_address_retrieve_results['address_found'],
            'guess_if_no_address_saved': guess_if_no_address_saved,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    else:
        status += 'GUESS_IF_NO_ADDRESS_SAVED' + ", "
        # If here, we are going to guess at the voter's location based on IP address
        voter_location_results = voter_location_retrieve_from_ip_for_api(request)
        # # TODO DALE TEMP
        # voter_location_results['voter_location_found'] = True
        # voter_location_results['voter_location'] = "New York, NY"
        # voter_location_results['status'] = "TODO DALE Temp setting of voter_location to New York"

        if voter_location_results['voter_location_found']:
            status += 'VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_FOUND_FROM_IP '
            # Since a new location was found, we need to save the address and then reach out to Google Civic
            text_for_map_search = voter_location_results['voter_location']
            status += '*** ' + text_for_map_search + ' ***, '

            google_civic_election_id = 0

            voter_address_save_results = voter_address_manager.update_or_create_voter_address(
                voter_id, BALLOT_ADDRESS, text_for_map_search)
            status += voter_address_save_results['status'] + ", "

            if voter_address_save_results['success'] and voter_address_save_results['voter_address_found']:
                voter_address = voter_address_save_results['voter_address']
                use_test_election = False
                # Reach out to Google and populate ballot items in the database with fresh ballot data
                # NOTE: 2016-05-26 Google civic NEVER returns a ballot for City, State ZIP, so we could change this
                google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
                    voter_device_id, text_for_map_search, use_test_election)
                status += google_retrieve_results['status'] + ", "

                if positive_value_exists(google_retrieve_results['google_civic_election_id']):
                    # Update voter_address with the google_civic_election_id retrieved from Google Civic
                    # and clear out ballot_saved information
                    google_civic_election_id = google_retrieve_results['google_civic_election_id']

                    voter_address.google_civic_election_id = google_civic_election_id
                    voter_address_update_results = voter_address_manager.update_existing_voter_address_object(
                        voter_address)

                    if voter_address_update_results['success']:
                        # Replace the former google_civic_election_id from this voter_device_link
                        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(
                            voter_device_id)
                        if voter_device_link_results['voter_device_link_found']:
                            voter_device_link = voter_device_link_results['voter_device_link']
                            voter_device_link_manager.update_voter_device_link_with_election_id(
                                voter_device_link, google_retrieve_results['google_civic_election_id'])

                else:
                    # This block of code helps us if the google_civic_election_id wasn't found when we reached out
                    # to the Google Civic API, following finding the voter's location from IP address.
                    google_civic_election_id = 0

            # We retrieve voter_device_link
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            if voter_device_link_results['voter_device_link_found']:
                voter_device_link = voter_device_link_results['voter_device_link']
            else:
                voter_device_link = VoterDeviceLink()

            # Retrieve the voter_address
            voter_address_results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
            if voter_address_results['voter_address_found']:
                voter_address = voter_address_results['voter_address']
            else:
                voter_address = VoterAddress()

            results = choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id,
                                                              voter_address)
            status += results['status']

            if results['voter_ballot_saved_found']:
                google_civic_election_id = results['google_civic_election_id']

            voter_address_retrieve_results = voter_address_retrieve_for_api(voter_device_id)

            status += voter_address_retrieve_results['status']
            if voter_address_retrieve_results['address_found']:
                json_data = {
                    'voter_device_id': voter_device_id,
                    'address_type': voter_address_retrieve_results['address_type'],
                    'text_for_map_search': voter_address_retrieve_results['text_for_map_search'],
                    'google_civic_election_id': google_civic_election_id,
                    'ballot_location_display_name': voter_address_retrieve_results['ballot_location_display_name'],
                    'ballot_returned_we_vote_id': voter_address_retrieve_results['ballot_returned_we_vote_id'],
                    'voter_entered_address': voter_address_retrieve_results['voter_entered_address'],
                    'voter_specific_ballot_from_google_civic':
                        voter_address_retrieve_results['voter_specific_ballot_from_google_civic'],
                    'latitude': voter_address_retrieve_results['latitude'],
                    'longitude': voter_address_retrieve_results['longitude'],
                    'normalized_line1': voter_address_retrieve_results['normalized_line1'],
                    'normalized_line2': voter_address_retrieve_results['normalized_line2'],
                    'normalized_city': voter_address_retrieve_results['normalized_city'],
                    'normalized_state': voter_address_retrieve_results['normalized_state'],
                    'normalized_zip': voter_address_retrieve_results['normalized_zip'],
                    'success': voter_address_retrieve_results['success'],
                    'status': status,
                    'address_found': voter_address_retrieve_results['address_found'],
                    'guess_if_no_address_saved': guess_if_no_address_saved,
                }
            else:
                # Address not found from IP address
                status += 'VOTER_ADDRESS_RETRIEVE_PART2_NO_ADDRESS'
                json_data = {
                    'voter_device_id': voter_device_id,
                    'address_type': '',
                    'text_for_map_search': '',
                    'google_civic_election_id': google_civic_election_id,
                    'ballot_location_display_name': '',
                    'ballot_returned_we_vote_id': '',
                    'voter_entered_address': False,
                    'voter_specific_ballot_from_google_civic': False,
                    'latitude': '',
                    'longitude': '',
                    'normalized_line1': '',
                    'normalized_line2': '',
                    'normalized_city': '',
                    'normalized_state': '',
                    'normalized_zip': '',
                    'success': voter_address_retrieve_results['success'],
                    'status': voter_address_retrieve_results['status'],
                    'address_found': voter_address_retrieve_results['address_found'],
                    'guess_if_no_address_saved': guess_if_no_address_saved,
                }

            return HttpResponse(json.dumps(json_data), content_type='application/json')
        else:
            status += 'VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_NOT_FOUND_FROM_IP: '
            status += voter_location_results['status']

            json_data = {
                'voter_device_id': voter_device_id,
                'address_type': '',
                'text_for_map_search': '',
                'google_civic_election_id': 0,
                'ballot_location_display_name': '',
                'ballot_returned_we_vote_id': '',
                'voter_entered_address': False,
                'voter_specific_ballot_from_google_civic': False,
                'latitude': '',
                'longitude': '',
                'normalized_line1': '',
                'normalized_line2': '',
                'normalized_city': '',
                'normalized_state': '',
                'normalized_zip': '',
                'success': False,
                'status': status,
                'address_found': False,
                'guess_if_no_address_saved': guess_if_no_address_saved,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_address_save_view(request):  # voterAddressSave
    """
    Save or update an address for this voter. Once the address is saved, update the ballot information.
    :param request:
    :return:
    """
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    simple_save = positive_value_exists(request.GET.get('simple_save', False))
    ballot_location_display_name = ''
    ballot_returned_we_vote_id = ''
    text_for_map_search_saved = ''
    voter_entered_address = True
    voter_specific_ballot_from_google_civic = False

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    try:
        text_for_map_search = request.GET['text_for_map_search']
        text_for_map_search = text_for_map_search.strip()
        address_variable_exists = True
    except KeyError:
        text_for_map_search = ''
        address_variable_exists = False

    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
            'status':               device_id_results['status'],
            'success':              False,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not address_variable_exists:
        json_data = {
            'status':               "MISSING_GET_VARIABLE-ADDRESS",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if voter_device_link_results['voter_device_link_found']:
        voter_device_link = voter_device_link_results['voter_device_link']
        voter_id = voter_device_link.voter_id
    else:
        json_data = {
            'status':               "VOTER_DEVICE_LINK_NOT_FOUND_FROM_DEVICE_ID",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not positive_value_exists(voter_id):
        json_data = {
            'status':               "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success':              False,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # Save the address value, and clear out ballot_saved information
    voter_address_manager = VoterAddressManager()
    voter_address_save_results = voter_address_manager.update_or_create_voter_address(
        voter_id, BALLOT_ADDRESS, text_for_map_search, google_civic_election_id, voter_entered_address)
    # TODO DALE 2017-07-17 This needs a fresh look:
    # , google_civic_election_id

    # If simple_save is passed in only save address and then send response (you must pass in a google_civic_election_id)
    if positive_value_exists(simple_save) and positive_value_exists(google_civic_election_id):
        success = voter_address_save_results['success'] and voter_address_save_results['voter_address_found']

        json_data = {
            'status':               "SIMPLE_ADDRESS_SAVE",
            'success':              success,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
            'google_civic_election_id': google_civic_election_id
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if voter_address_save_results['success'] and voter_address_save_results['voter_address_found']:
        # # Remove the former google_civic_election_id from this voter_device_id
        # voter_device_link_manager.update_voter_device_link_with_election_id(voter_device_link, 0)
        voter_address = voter_address_save_results['voter_address']
        use_test_election = False

        # Reach out to Google and populate ballot items in the database with fresh ballot data
        google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
            voter_device_id, text_for_map_search, use_test_election)

        # Update voter_address with the google_civic_election_id retrieved from Google Civic
        # and clear out ballot_saved information IFF we got a valid google_civic_election_id back
        if google_retrieve_results['google_civic_election_id']:
            google_civic_election_id = convert_to_int(google_retrieve_results['google_civic_election_id'])
        else:
            # Leave google_civic_election_id as it was at the top of this function
            pass

        if google_retrieve_results['ballot_location_display_name']:
            ballot_location_display_name = google_retrieve_results['ballot_location_display_name']

        if google_retrieve_results['ballot_returned_we_vote_id']:
            ballot_returned_we_vote_id = google_retrieve_results['ballot_returned_we_vote_id']

        # At this point proceed to update google_civic_election_id whether it is a positive integer or zero
        # First retrieve the latest address, since it gets saved when we retrieve from google civic
        updated_address_results = voter_address_manager.retrieve_address(voter_address.id)
        if updated_address_results['voter_address_found']:
            voter_address = updated_address_results['voter_address']
            voter_address.google_civic_election_id = google_civic_election_id
            voter_address.ballot_location_display_name = ballot_location_display_name
            voter_address.ballot_returned_we_vote_id = ballot_returned_we_vote_id
            voter_entered_address = voter_address.voter_entered_address
            voter_specific_ballot_from_google_civic = voter_address.refreshed_from_google
            voter_address_update_results = voter_address_manager.update_existing_voter_address_object(voter_address)

            if voter_address_update_results['success']:
                # Replace the former google_civic_election_id from this voter_device_link
                voter_device_link_manager = VoterDeviceLinkManager()
                voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
                if voter_device_link_results['voter_device_link_found']:
                    voter_device_link = voter_device_link_results['voter_device_link']
                    voter_device_link_manager.update_voter_device_link_with_election_id(
                        voter_device_link, google_civic_election_id)
                if voter_address_update_results['voter_address_found']:
                    voter_address = voter_address_update_results['voter_address']
                    text_for_map_search_saved = voter_address.text_for_map_search

    json_data = voter_ballot_items_retrieve_for_api(voter_device_id, google_civic_election_id,
                                                    ballot_returned_we_vote_id)
    json_data['simple_save'] = simple_save
    json_data['address'] = {
        'text_for_map_search':          text_for_map_search_saved,
        'google_civic_election_id':     google_civic_election_id,
        'ballot_returned_we_vote_id':   ballot_returned_we_vote_id,
        'ballot_location_display_name': ballot_location_display_name,
        'voter_entered_address':        voter_entered_address,
        'voter_specific_ballot_from_google_civic':    voter_specific_ballot_from_google_civic,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_ballot_items_retrieve_view(request):  # voterBallotItemsRetrieve
    """
    Request the ballot data requested by the voter
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    # If passed in, we want to look at
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    ballot_returned_we_vote_id = request.GET.get('ballot_returned_we_vote_id', '')
    ballot_location_shortcut = request.GET.get('ballot_location_shortcut', '')

    use_test_election = positive_value_exists(request.GET.get('use_test_election', False))

    if use_test_election:
        google_civic_election_id = 2000  # The Google Civic test election

    json_data = voter_ballot_items_retrieve_for_api(voter_device_id, google_civic_election_id,
                                                    ballot_returned_we_vote_id, ballot_location_shortcut)

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_ballot_items_retrieve_from_google_civic_view(request):  # voterBallotItemsRetrieveFromGoogleCivic
    voter_device_id = get_voter_device_id(request)
    text_for_map_search = request.GET.get('text_for_map_search', '')
    use_test_election = positive_value_exists(request.GET.get('use_test_election', False))

    voter_id = 0

    google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
        voter_device_id, text_for_map_search, use_test_election)

    if google_retrieve_results['google_civic_election_id'] and not use_test_election:
        # After the ballot is retrieved from google we want to save some info about it for the voter
        if positive_value_exists(voter_device_id):
            voter_device_link_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            if voter_device_link_results['voter_device_link_found']:
                voter_device_link = voter_device_link_results['voter_device_link']
                voter_id = voter_device_link.voter_id

        if positive_value_exists(voter_id):
            voter_ballot_saved_manager = VoterBallotSavedManager()
            is_from_substituted_address = False
            substituted_address_nearby = ''
            is_from_test_address = False
            polling_location_we_vote_id_source = ""  # Not used when retrieving directly from Google Civic

            # We don't update the voter_address because this view might be used independent of the voter_address

            # Save the meta information for this ballot data. If it fails, ignore the failure
            voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                voter_id,
                google_retrieve_results['google_civic_election_id'],
                google_retrieve_results['state_code'],
                google_retrieve_results['election_day_text'],
                google_retrieve_results['election_description_text'],
                google_retrieve_results['text_for_map_search'],
                substituted_address_nearby,
                is_from_substituted_address,
                is_from_test_address,
                polling_location_we_vote_id_source,
                google_retrieve_results['ballot_location_display_name'],
                google_retrieve_results['ballot_returned_we_vote_id'],
                google_retrieve_results['ballot_location_shortcut'],
            )

    return HttpResponse(json.dumps(google_retrieve_results), content_type='application/json')


def voter_ballot_list_retrieve_view(request):  # voterBallotListRetrieve
    """
    (voterBallotListRetrieve) Retrieve a list of election ballots per voter_id.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_id = 0

    if positive_value_exists(voter_device_id):
        voter_device_link_manager = VoterDeviceLinkManager()
        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
        voter_device_link = voter_device_link_results['voter_device_link']
        if voter_device_link_results['voter_device_link_found']:
            voter_id = voter_device_link.voter_id

    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_ID_MISSING",
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_ballot_list_found': False,
            'voter_ballot_list': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = voter_ballot_list_retrieve_for_api(voter_id)

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'voter_ballot_list_found': results['voter_ballot_list_found'],
        'voter_ballot_list': results['voter_ballot_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_count_view(request):  # voterCount
    return voter_count()


def voter_create_view(request):  # voterCreate
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return voter_create_for_api(voter_device_id)


def voter_email_address_retrieve_view(request):  # voterEmailAddressRetrieve
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = voter_email_address_retrieve_for_api(voter_device_id=voter_device_id)

    json_data = {
        'status':                   results['status'],
        'success':                  results['success'],
        'voter_device_id':          voter_device_id,
        'email_address_list_found': results['email_address_list_found'],
        'email_address_list':       results['email_address_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_email_address_save_view(request):  # voterEmailAddressSave
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    text_for_email_address = request.GET.get('text_for_email_address', '')
    incoming_email_we_vote_id = request.GET.get('email_we_vote_id', '')
    resend_verification_email = positive_value_exists(request.GET.get('resend_verification_email', False))
    send_link_to_sign_in = positive_value_exists(request.GET.get('send_link_to_sign_in', False))
    make_primary_email = positive_value_exists(request.GET.get('make_primary_email', False))
    delete_email = positive_value_exists(request.GET.get('delete_email', ""))

    results = voter_email_address_save_for_api(voter_device_id=voter_device_id,
                                               text_for_email_address=text_for_email_address,
                                               incoming_email_we_vote_id=incoming_email_we_vote_id,
                                               send_link_to_sign_in=send_link_to_sign_in,
                                               resend_verification_email=resend_verification_email,
                                               make_primary_email=make_primary_email,
                                               delete_email=delete_email,
                                               )

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
        'text_for_email_address':           text_for_email_address,
        'make_primary_email':               make_primary_email,
        'delete_email':                     delete_email,
        'email_address_we_vote_id':         results['email_address_we_vote_id'],
        'email_address_saved_we_vote_id':   results['email_address_saved_we_vote_id'],
        'email_address_already_owned_by_other_voter':   results['email_address_already_owned_by_other_voter'],
        'email_address_created':            results['email_address_created'],
        'email_address_deleted':            results['email_address_deleted'],
        'verification_email_sent':          results['verification_email_sent'],
        'link_to_sign_in_email_sent':       results['link_to_sign_in_email_sent'],
        'email_address_found':              results['email_address_found'],
        'email_address_list_found':         results['email_address_list_found'],
        'email_address_list':               results['email_address_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_email_address_sign_in_view(request):  # voterEmailAddressSignIn
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    email_secret_key = request.GET.get('email_secret_key', '')
    yes_please_merge_accounts = request.GET.get('yes_please_merge_accounts', '')
    yes_please_merge_accounts = positive_value_exists(yes_please_merge_accounts)

    results = voter_email_address_sign_in_for_api(voter_device_id=voter_device_id,
                                                  email_secret_key=email_secret_key)

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
        'email_ownership_is_verified':      results['email_ownership_is_verified'],
        'email_secret_key_belongs_to_this_voter':   results['email_secret_key_belongs_to_this_voter'],
        'email_sign_in_attempted':          True,
        'email_address_found':              results['email_address_found'],
        'yes_please_merge_accounts':        yes_please_merge_accounts,
        'voter_we_vote_id_from_secret_key': results['voter_we_vote_id_from_secret_key'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_email_address_verify_view(request):  # voterEmailAddressVerify
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    email_secret_key = request.GET.get('email_secret_key', '')

    results = voter_email_address_verify_for_api(voter_device_id=voter_device_id,
                                                 email_secret_key=email_secret_key)

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
        'email_ownership_is_verified':      results['email_ownership_is_verified'],
        'email_secret_key_belongs_to_this_voter':   results['email_secret_key_belongs_to_this_voter'],
        'email_verify_attempted':           True,
        'email_address_found':              results['email_address_found'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_facebook_sign_in_retrieve_view(request):  # voterFacebookSignInRetrieve
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    results = voter_facebook_sign_in_retrieve_for_api(voter_device_id=voter_device_id)

    json_data = {
        'status':                                   results['status'],
        'success':                                  results['success'],
        'voter_device_id':                          voter_device_id,
        'existing_facebook_account_found':          results['existing_facebook_account_found'],
        'voter_we_vote_id_attached_to_facebook':    results['voter_we_vote_id_attached_to_facebook'],
        'voter_we_vote_id_attached_to_facebook_email':  results['voter_we_vote_id_attached_to_facebook_email'],
        'facebook_retrieve_attempted':              True,
        'facebook_sign_in_found':                   results['facebook_sign_in_found'],
        'facebook_sign_in_verified':                results['facebook_sign_in_verified'],
        'facebook_sign_in_failed':                  results['facebook_sign_in_failed'],
        'facebook_secret_key':                      results['facebook_secret_key'],
        'voter_has_data_to_preserve':               results['voter_has_data_to_preserve'],
        'facebook_user_id':                         results['facebook_user_id'],
        'facebook_profile_image_url_https':         results['facebook_profile_image_url_https'],
        'we_vote_hosted_profile_image_url_large':   results['we_vote_hosted_profile_image_url_large'],
        'we_vote_hosted_profile_image_url_medium':  results['we_vote_hosted_profile_image_url_medium'],
        'we_vote_hosted_profile_image_url_tiny':    results['we_vote_hosted_profile_image_url_tiny']
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_facebook_sign_in_save_view(request):  # voterFacebookSignInSave
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    save_auth_data = request.GET.get('save_auth_data', False)
    save_auth_data = positive_value_exists(save_auth_data)
    facebook_access_token = request.GET.get('facebook_access_token', '')
    facebook_user_id = request.GET.get('facebook_user_id', '')
    facebook_expires_in = request.GET.get('facebook_expires_in', 0)
    facebook_signed_request = request.GET.get('facebook_signed_request', '')
    save_profile_data = request.GET.get('save_profile_data', False)
    save_profile_data = positive_value_exists(save_profile_data)
    save_photo_data = request.GET.get('save_photo_data', False)
    save_photo_data = positive_value_exists(save_photo_data)
    facebook_email = request.GET.get('facebook_email', '')
    facebook_first_name = request.GET.get('facebook_first_name', '')
    facebook_middle_name = request.GET.get('facebook_middle_name', '')
    facebook_last_name = request.GET.get('facebook_last_name', '')
    facebook_profile_image_url_https = request.GET.get('facebook_profile_image_url_https', '')
    facebook_background_image_url_https = request.GET.get('facebook_background_image_url_https', '')
    facebook_background_image_offset_x = request.GET.get('facebook_background_image_offset_x', '')
    facebook_background_image_offset_y = request.GET.get('facebook_background_image_offset_y', '')

    results = voter_facebook_sign_in_save_for_api(
        voter_device_id=voter_device_id,
        save_auth_data=save_auth_data,
        facebook_access_token=facebook_access_token,
        facebook_user_id=facebook_user_id,
        facebook_expires_in=facebook_expires_in,
        facebook_signed_request=facebook_signed_request,
        save_profile_data=save_profile_data,
        facebook_email=facebook_email,
        facebook_first_name=facebook_first_name,
        facebook_middle_name=facebook_middle_name,
        facebook_last_name=facebook_last_name,
        save_photo_data=save_photo_data,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
        facebook_background_image_url_https=facebook_background_image_url_https,
        facebook_background_image_offset_x=facebook_background_image_offset_x,
        facebook_background_image_offset_y=facebook_background_image_offset_y,
        )

    json_data = {
        'status':                   results['status'],
        'success':                  results['success'],
        'voter_device_id':          voter_device_id,
        'facebook_save_attempted':  True,
        'facebook_sign_in_saved':   results['facebook_sign_in_saved'],
        'save_auth_data':           save_auth_data,
        'save_profile_data':        save_profile_data,
        'save_photo_data':          save_photo_data,
        'minimum_data_saved':       results['minimum_data_saved'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_possibility_retrieve_view(request):  # voterGuidePossibilityRetrieve
    """
    Retrieve a previously saved website that may contain a voter guide (voterGuidePossibilityRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_possibility_url = request.GET.get('voter_guide_possibility_url', '')
    return voter_guide_possibility_retrieve_for_api(voter_device_id=voter_device_id,
                                                    voter_guide_possibility_url=voter_guide_possibility_url)


def voter_guide_possibility_save_view(request):  # voterGuidePossibilitySave
    """
    Save a website that may contain a voter guide (voterGuidePossibilitySave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_possibility_url = request.GET.get('voter_guide_possibility_url', '')
    return voter_guide_possibility_save_for_api(voter_device_id=voter_device_id,
                                                voter_guide_possibility_url=voter_guide_possibility_url)


def voter_guides_followed_retrieve_view(request):  # voterGuidesFollowedRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_followed_retrieve_for_api(voter_device_id=voter_device_id,
                                                  maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_follow_all_organizations_followed_by_organization_view(request):
    # voterFollowAllOrganizationsFollowedByOrganization
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_follow = get_maximum_number_to_retrieve_from_request(request)
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    return voter_follow_all_organizations_followed_by_organization_for_api(
        voter_device_id,
        organization_we_vote_id=organization_we_vote_id,
        maximum_number_to_follow=maximum_number_to_follow, user_agent_string=user_agent_string,
        user_agent_object=user_agent_object)


def voter_guides_followed_by_organization_retrieve_view(request):  # voterGuidesFollowedByOrganizationRetrieve
    voter_linked_organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    filter_by_this_google_civic_election_id = request.GET.get('filter_by_this_google_civic_election_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_followed_by_organization_retrieve_for_api(
        voter_device_id,
        voter_linked_organization_we_vote_id=voter_linked_organization_we_vote_id,
        filter_by_this_google_civic_election_id=filter_by_this_google_civic_election_id,
        maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guide_followers_retrieve_view(request):  # voterGuideFollowersRetrieve
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guide_followers_retrieve_for_api(
        voter_device_id, organization_we_vote_id=organization_we_vote_id,
        maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guides_ignored_retrieve_view(request):  # voterGuidesIgnoredRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_ignored_retrieve_for_api(voter_device_id=voter_device_id,
                                                 maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guides_to_follow_retrieve_view(request):  # voterGuidesToFollowRetrieve
    """
    Retrieve a list of voter_guides that a voter might want to follow (voterGuidesToFollow)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', '')
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    search_string = request.GET.get('search_string', '')
    use_test_election = positive_value_exists(request.GET.get('use_test_election', False))
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    filter_voter_guides_by_issue = positive_value_exists(request.GET.get('filter_voter_guides_by_issue', False))
    # If we want to show voter guides associated with election first, but then show more after those are exhausted,
    #  set add_voter_guides_not_from_election to True
    add_voter_guides_not_from_election = request.GET.get('add_voter_guides_not_from_election', False)
    add_voter_guides_not_from_election = positive_value_exists(add_voter_guides_not_from_election)

    if positive_value_exists(ballot_item_we_vote_id):
        # We don't need both ballot_item and google_civic_election_id
        google_civic_election_id = 0
    else:
        if positive_value_exists(use_test_election):
            google_civic_election_id = 2000  # The Google Civic API Test election
        elif positive_value_exists(google_civic_election_id) or google_civic_election_id == 0:
            # If an election was specified, we can skip down to retrieving the voter_guides
            pass
        else:
            # If here we don't have either a ballot_item or a google_civic_election_id.
            # Look in the places we cache google_civic_election_id
            google_civic_election_id = 0
            voter_device_link_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            voter_device_link = voter_device_link_results['voter_device_link']
            if voter_device_link_results['voter_device_link_found']:
                voter_id = voter_device_link.voter_id
                voter_address_manager = VoterAddressManager()
                voter_address_results = voter_address_manager.retrieve_address(0, voter_id)
                if voter_address_results['voter_address_found']:
                    voter_address = voter_address_results['voter_address']
                else:
                    voter_address = VoterAddress()
            else:
                voter_address = VoterAddress()
            results = choose_election_from_existing_data(voter_device_link, google_civic_election_id, voter_address)
            google_civic_election_id = results['google_civic_election_id']

        # In order to return voter_guides that are independent of an election or ballot_item, we need to pass in
        # google_civic_election_id as 0

    results = voter_guides_to_follow_retrieve_for_api(voter_device_id, kind_of_ballot_item, ballot_item_we_vote_id,
                                                      google_civic_election_id, search_string,
                                                      maximum_number_to_retrieve, filter_voter_guides_by_issue,
                                                      add_voter_guides_not_from_election)
    return HttpResponse(json.dumps(results['json_data']), content_type='application/json')


def voter_issue_follow_view(request):  # issueFollow
    voter_device_id = request.GET.get('voter_device_id', False)
    issue_we_vote_id = request.GET.get('issue_we_vote_id', False)
    follow_value = positive_value_exists(request.GET.get('follow', False))
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    ignore_value = positive_value_exists(request.GET.get('ignore', False))

    return voter_issue_follow_for_api(voter_device_id=voter_device_id,
                                      issue_we_vote_id=issue_we_vote_id,
                                      follow_value=follow_value,
                                      ignore_value=ignore_value, user_agent_string=user_agent_string,
                                      user_agent_object=user_agent_object)


def voter_location_retrieve_from_ip_view(request):  # voterLocationRetrieveFromIP - GeoIP geo location
    """
    Take the IP address and return a location (voterLocationRetrieveFromIP)
    :param request:
    :return:
    """
    ip_address = request.GET.get('ip_address', '')
    voter_location_results = voter_location_retrieve_from_ip_for_api(request, ip_address)

    json_data = {
        'success': voter_location_results['success'],
        'status': voter_location_results['status'],
        'voter_location_found': voter_location_results['voter_location_found'],
        'voter_location': voter_location_results['voter_location'],
        'ip_address': voter_location_results['ip_address'],
        'x_forwarded_for': voter_location_results['x_forwarded_for'],
        'http_x_forwarded_for': voter_location_results['http_x_forwarded_for'],
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_merge_two_accounts_view(request):  # voterMergeTwoAccounts
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    email_secret_key = request.GET.get('email_secret_key', '')
    facebook_secret_key = request.GET.get('facebook_secret_key', '')
    twitter_secret_key = request.GET.get('twitter_secret_key', '')
    invitation_secret_key = request.GET.get('invitation_secret_key', '')

    results = voter_merge_two_accounts_for_api(voter_device_id=voter_device_id,
                                               email_secret_key=email_secret_key,
                                               facebook_secret_key=facebook_secret_key,
                                               twitter_secret_key=twitter_secret_key,
                                               invitation_secret_key=invitation_secret_key)

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_photo_save_view(request):  # voterPhotoSave
    """
    Save or update a photo for this voter
    :param request:
    :return:
    """

    status = ''

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    try:
        facebook_profile_image_url_https = request.GET['facebook_profile_image_url_https']
        facebook_profile_image_url_https = facebook_profile_image_url_https.strip()
        facebook_photo_variable_exists = True
    except KeyError:
        facebook_profile_image_url_https = ''
        facebook_photo_variable_exists = False

    results = voter_photo_save_for_api(voter_device_id,
                                       facebook_profile_image_url_https, facebook_photo_variable_exists)
    voter_photo_saved = True if results['success'] else False

    if not positive_value_exists(facebook_profile_image_url_https):
        json_data = {
            'status': results['status'],
            'success': results['success'],
            'voter_device_id': voter_device_id,
            'facebook_profile_image_url_https': facebook_profile_image_url_https,
            'voter_photo_saved': voter_photo_saved,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')

        return response

    status += results['status'] + ", "
    # If here, we saved a valid photo

    json_data = {
        'status': status,
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'facebook_profile_image_url_https': facebook_profile_image_url_https,
        'voter_photo_saved': voter_photo_saved,
    }

    response = HttpResponse(json.dumps(json_data), content_type='application/json')

    return response


def voter_position_retrieve_view(request):
    """
    Retrieve all of the details about a single position based on unique identifier. voterPositionRetrieve
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    # ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_we_vote_id = ballot_item_we_vote_id
        candidate_we_vote_id = ''
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_we_vote_id = ''
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_we_vote_id = ''
        candidate_we_vote_id = ''
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_we_vote_id = ''
        candidate_we_vote_id = ''
        measure_we_vote_id = ''
    return voter_position_retrieve_for_api(
        voter_device_id=voter_device_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id
    )


def voter_position_visibility_save_view(request):  # voterPositionVisibilitySave
    """
    Change the visibility (between public vs. friends-only) for a single measure or candidate for one voter
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    visibility_setting = request.GET.get('visibility_setting', False)

    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)

    if kind_of_ballot_item == CANDIDATE:
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_we_vote_id = None
        office_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_we_vote_id = None
        measure_we_vote_id = ballot_item_we_vote_id
        office_we_vote_id = None
    elif kind_of_ballot_item == OFFICE:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = None

    results = voter_position_visibility_save_for_api(
        voter_device_id=voter_device_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        visibility_setting=visibility_setting,
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_all_positions_retrieve_view(request):  # voterAllPositionsRetrieve
    """
    Retrieve a list of all positions for one voter, including "is_support", "is_oppose" and "statement_text".
    Note that these can either be public positions or private positions.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    return voter_all_positions_retrieve_for_api(
        voter_device_id=voter_device_id,
        google_civic_election_id=google_civic_election_id
    )


def voter_position_like_off_save_view(request):
    """
    Un-mark the position_like for a single position for one voter (voterPositionLikeOffSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_like_id = request.GET.get('position_like_id', 0)
    position_entered_id = request.GET.get('position_entered_id', 0)
    return voter_position_like_off_save_for_api(
        voter_device_id=voter_device_id, position_like_id=position_like_id, position_entered_id=position_entered_id)


def voter_position_like_on_save_view(request):
    """
    Mark the position_like for a single position for one voter (voterPositionLikeOnSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    return voter_position_like_on_save_for_api(
        voter_device_id=voter_device_id, position_entered_id=position_entered_id)


def voter_position_like_status_retrieve_view(request):
    """
    Retrieve whether or not a position_like is marked for position (voterPositionLikeStatusRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    return voter_position_like_status_retrieve_for_api(
        voter_device_id=voter_device_id, position_entered_id=position_entered_id)


def voter_position_comment_save_view(request):  # voterPositionCommentSave
    """
    Save comment for a single measure or candidate for one voter
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_we_vote_id = request.GET.get('position_we_vote_id', "")

    statement_text = request.GET.get('statement_text', False)
    statement_html = request.GET.get('statement_html', False)

    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)

    if kind_of_ballot_item == CANDIDATE:
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_we_vote_id = None
        office_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_we_vote_id = None
        measure_we_vote_id = ballot_item_we_vote_id
        office_we_vote_id = None
    elif kind_of_ballot_item == OFFICE:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = None

    results = voter_position_comment_save_for_api(
        voter_device_id=voter_device_id,
        position_we_vote_id=position_we_vote_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        statement_text=statement_text,
        statement_html=statement_html,
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_opposing_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterOpposingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_opposing_save(voter_device_id=voter_device_id,
                               candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                               measure_id=measure_id, measure_we_vote_id=measure_we_vote_id,
                               user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def voter_split_into_two_accounts_view(request):  # voterSplitIntoTwoAccounts
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    split_off_twitter = request.GET.get('split_off_twitter', True)

    results = voter_split_into_two_accounts_for_api(voter_device_id=voter_device_id,
                                                    split_off_twitter=split_off_twitter)

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_retrieve_view(request):  # voterRetrieve
    """
    Retrieve a single voter based on voter_device
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)

    # Figure out the city & state from IP address
    voter_location_results = voter_location_retrieve_from_ip_for_api(request)
    state_code_from_ip_address = voter_location_results['region']

    results = voter_retrieve_for_api(voter_device_id=voter_device_id,
                                     state_code_from_ip_address=state_code_from_ip_address,
                                     user_agent_string=user_agent_string, user_agent_object=user_agent_object)
    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_sign_out_view(request):  # voterSignOut
    """
    Sign out from this device. (Delete this voter_device_id from the database, OR if sign_out_all_devices is True,
    sign out from all devices.)
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    sign_out_all_devices = request.GET.get('sign_out_all_devices', 0)

    if not positive_value_exists(voter_device_id):
        success = False
        status = "VOTER_SIGN_OUT_VOTER_DEVICE_ID_DOES_NOT_EXIST"
        json_data = {
            'voter_device_id':      voter_device_id,
            'sign_out_all_devices': sign_out_all_devices,
            'success':              success,
            'status':               status,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = voter_sign_out_for_api(voter_device_id=voter_device_id, sign_out_all_devices=sign_out_all_devices)

    json_data = {
        'voter_device_id':      voter_device_id,
        'sign_out_all_devices': sign_out_all_devices,
        'success':              results['success'],
        'status':               results['status'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_stop_opposing_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopOpposingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_stop_opposing_save(voter_device_id=voter_device_id,
                                    candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                                    measure_id=measure_id, measure_we_vote_id=measure_we_vote_id,
                                    user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def voter_stop_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopSupportingSave)
    Default to set this as a position for your friends only.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_stop_supporting_save(voter_device_id=voter_device_id,
                                      candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                                      measure_id=measure_id, measure_we_vote_id=measure_we_vote_id,
                                      user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def voter_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterSupportingSave)
    Default to set this as a position for your friends only.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_supporting_save_for_api(voter_device_id=voter_device_id,
                                         candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                                         measure_id=measure_id, measure_we_vote_id=measure_we_vote_id,
                                         user_agent_string=user_agent_string, user_agent_object=user_agent_object)


def voter_bookmark_off_save_view(request):
    """
    Un-mark the bookmark for a single measure, office or candidate for one voter (voterBookmarkOffSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return voter_bookmark_off_save_for_api(
        voter_device_id=voter_device_id,
        office_id=office_id, office_we_vote_id=office_we_vote_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_bookmark_on_save_view(request):
    """
    Mark the bookmark for a single measure, office or candidate for one voter (voterBookmarkOnSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return voter_bookmark_on_save_for_api(
        voter_device_id=voter_device_id,
        office_id=office_id, office_we_vote_id=office_we_vote_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_bookmark_status_retrieve_view(request):
    """
    Retrieve whether or not a bookmark is marked for an office, candidate or measure based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return voter_bookmark_status_retrieve_for_api(
        voter_device_id=voter_device_id,
        office_id=office_id, office_we_vote_id=office_we_vote_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_all_bookmarks_status_retrieve_view(request):  # voterAllBookmarksStatusRetrieve
    """
    A list of all of the bookmarks that the voter has marked.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return voter_all_bookmarks_status_retrieve_for_api(
        voter_device_id=voter_device_id)


def voter_twitter_save_to_current_account_view(request):  # voterTwitterSaveToCurrentAccount
    """
    Saving the results of signing in with Twitter
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = voter_twitter_save_to_current_account_for_api(voter_device_id)
    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_update_view(request):  # voterUpdate
    """
    Update profile-related information for this voter
    :param request:
    :return:
    """

    voter_updated = False

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    # If we have an incoming GET value for a variable, use it. If we don't pass "False" into voter_update_for_api
    # as a signal to not change the variable. (To set variables to False, pass in the string "False".)
    try:
        facebook_email = request.GET['facebook_email']
        facebook_email = facebook_email.strip()
        if facebook_email.lower() == 'false':
            facebook_email = False
    except KeyError:
        facebook_email = False

    try:
        facebook_profile_image_url_https = request.GET['facebook_profile_image_url_https']
        facebook_profile_image_url_https = facebook_profile_image_url_https.strip()
        if facebook_profile_image_url_https.lower() == 'false':
            facebook_profile_image_url_https = False
    except KeyError:
        facebook_profile_image_url_https = False

    try:
        first_name = request.GET['first_name']
        first_name = first_name.strip()
        if first_name.lower() == 'false':
            first_name = False
    except KeyError:
        first_name = False

    try:
        middle_name = request.GET['middle_name']
        middle_name = middle_name.strip()
        if middle_name.lower() == 'false':
            middle_name = False
    except KeyError:
        middle_name = False

    try:
        last_name = request.GET['last_name']
        last_name = last_name.strip()
        if last_name.lower() == 'false':
            last_name = False
    except KeyError:
        last_name = False

    try:
        full_name = request.GET['full_name']
        full_name = full_name.strip()
        if full_name.lower() == 'false':
            full_name = False
    except KeyError:
        full_name = False

    try:
        name_save_only_if_no_existing_names = request.GET['name_save_only_if_no_existing_names']
        name_save_only_if_no_existing_names = name_save_only_if_no_existing_names.strip()
        if name_save_only_if_no_existing_names.lower() == 'false':
            name_save_only_if_no_existing_names = False
    except KeyError:
        name_save_only_if_no_existing_names = False

    try:
        twitter_profile_image_url_https = request.GET['twitter_profile_image_url_https']
        twitter_profile_image_url_https = twitter_profile_image_url_https.strip()
        if twitter_profile_image_url_https.lower() == 'false':
            twitter_profile_image_url_https = False
    except KeyError:
        twitter_profile_image_url_https = False

    try:
        interface_status_flags = request.GET['interface_status_flags']
        interface_status_flags = interface_status_flags.strip()
        interface_status_flags = convert_to_int(interface_status_flags)
    except KeyError:
        interface_status_flags = False

    try:
        flag_integer_to_set = request.GET['flag_integer_to_set']
        flag_integer_to_set = flag_integer_to_set.strip()
        flag_integer_to_set = convert_to_int(flag_integer_to_set)
    except KeyError:
        flag_integer_to_set = False

    try:
        flag_integer_to_unset = request.GET['flag_integer_to_unset']
        flag_integer_to_unset = flag_integer_to_unset.strip()
        flag_integer_to_unset = convert_to_int(flag_integer_to_unset)
    except KeyError:
        flag_integer_to_unset = False

    try:
        notification_settings_flags = request.GET['notification_settings_flags']
        notification_settings_flags = notification_settings_flags.strip()
        notification_settings_flags = convert_to_int(notification_settings_flags)
    except KeyError:
        notification_settings_flags = False

    try:
        notification_flag_integer_to_set = request.GET['notification_flag_integer_to_set']
        notification_flag_integer_to_set = notification_flag_integer_to_set.strip()
        notification_flag_integer_to_set = convert_to_int(notification_flag_integer_to_set)
    except KeyError:
        notification_flag_integer_to_set = False

    try:
        notification_flag_integer_to_unset = request.GET['notification_flag_integer_to_unset']
        notification_flag_integer_to_unset = notification_flag_integer_to_unset.strip()
        notification_flag_integer_to_unset = convert_to_int(notification_flag_integer_to_unset)
    except KeyError:
        notification_flag_integer_to_unset = False

    try:
        send_journal_list = request.GET['send_journal_list']
    except KeyError:
        send_journal_list = False

    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
                'status':                           device_id_results['status'],
                'success':                          False,
                'voter_device_id':                  voter_device_id,
                'facebook_email':                   facebook_email,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
                'first_name':                       first_name,
                'middle_name':                      middle_name,
                'last_name':                        last_name,
                'twitter_profile_image_url_https':  twitter_profile_image_url_https,
                'voter_updated':                    voter_updated,
                'interface_status_flags':           interface_status_flags,
                'flag_integer_to_set':              flag_integer_to_set,
                'flag_integer_to_unset':            flag_integer_to_unset,
                'notification_settings_flags':      notification_settings_flags,
                'notification_flag_integer_to_set': notification_flag_integer_to_set,
                'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
                'voter_donation_history_list':      None,
            }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    at_least_one_variable_has_changed = True if \
        facebook_email or facebook_profile_image_url_https \
        or first_name or middle_name or last_name \
        or full_name \
        or interface_status_flags or flag_integer_to_unset \
        or flag_integer_to_set \
        or notification_settings_flags or notification_flag_integer_to_unset \
        or notification_flag_integer_to_set \
        or send_journal_list \
        else False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                           "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'facebook_email':                   facebook_email,
            'facebook_profile_image_url_https': facebook_profile_image_url_https,
            'first_name':                       first_name,
            'middle_name':                      middle_name,
            'last_name':                        last_name,
            'twitter_profile_image_url_https':  twitter_profile_image_url_https,
            'voter_updated':                    voter_updated,
            'interface_status_flags':           interface_status_flags,
            'flag_integer_to_set':              flag_integer_to_set,
            'flag_integer_to_unset':            flag_integer_to_unset,
            'notification_settings_flags':      notification_settings_flags,
            'notification_flag_integer_to_set': notification_flag_integer_to_set,
            'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
            'voter_donation_history_list':      None,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    voter = voter_results['voter']

    # At this point, we have a valid voter
    donation_list = donation_history_for_a_voter(voter.we_vote_id)

    if not at_least_one_variable_has_changed:
        # If here, we want to return the latest data from the voter object
        json_data = {
                'status':                           "MISSING_VARIABLE-NO_VARIABLES_PASSED_IN_TO_CHANGE",
                'success':                          True,
                'voter_device_id':                  voter_device_id,
                'facebook_email':                   voter.facebook_email,
                'facebook_profile_image_url_https': voter.facebook_profile_image_url_https,
                'first_name':                       voter.first_name,
                'middle_name':                      voter.middle_name,
                'last_name':                        voter.last_name,
                'twitter_profile_image_url_https':  voter.twitter_profile_image_url_https,
                'voter_updated':                    voter_updated,
                'interface_status_flags':           voter.interface_status_flags,
                'flag_integer_to_set':              flag_integer_to_set,
                'flag_integer_to_unset':            flag_integer_to_unset,
                'notification_settings_flags':      voter.notification_settings_flags,
                'notification_flag_integer_to_set': notification_flag_integer_to_set,
                'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
                'voter_donation_history_list':      donation_list,
            }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    we_vote_hosted_profile_image_url_large = None
    we_vote_hosted_profile_image_url_medium = None
    we_vote_hosted_profile_image_url_tiny = None

    if twitter_profile_image_url_https:
        # Cache original and resized images
        # TODO: Replace voter.twitter_id with value from twitter link to voter
        cache_results = cache_master_and_resized_image(
            voter_we_vote_id=voter.we_vote_id,
            twitter_id=voter.twitter_id,
            twitter_screen_name=voter.twitter_screen_name,
            twitter_profile_image_url_https=twitter_profile_image_url_https,
            image_source=TWITTER)
        cached_twitter_profile_image_url_https = cache_results['cached_twitter_profile_image_url_https']
        we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']
        if positive_value_exists(cached_twitter_profile_image_url_https):
            twitter_profile_image_url_https = cached_twitter_profile_image_url_https

    if facebook_profile_image_url_https:
        # Cache original and resized images
        # TODO: Replace voter.facebook_id with value from facebook link to voter
        cache_results = cache_master_and_resized_image(
            voter_we_vote_id=voter.we_vote_id,
            facebook_user_id=voter.facebook_id,
            facebook_profile_image_url_https=facebook_profile_image_url_https,
            image_source=FACEBOOK)
        cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
        we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']
        if positive_value_exists(cached_facebook_profile_image_url_https):
            facebook_profile_image_url_https = cached_facebook_profile_image_url_https

    if positive_value_exists(voter.first_name) or positive_value_exists(voter.last_name):
        saved_first_or_last_name_exists = True
    else:
        saved_first_or_last_name_exists = False

    incoming_first_or_last_name = positive_value_exists(first_name) or positive_value_exists(last_name)
    # If a first_name or last_name is coming in, we want to ignore the full_name
    if positive_value_exists(full_name) and not positive_value_exists(incoming_first_or_last_name):
        incoming_full_name_can_be_processed = True
    else:
        incoming_full_name_can_be_processed = False

    if incoming_full_name_can_be_processed:
        # If here we want to parse full_name into first and last
        first_name = extract_first_name_from_full_name(full_name)
        last_name = extract_last_name_from_full_name(full_name)

    if name_save_only_if_no_existing_names:
        if saved_first_or_last_name_exists:
            first_name = False
            last_name = False

    voter_manager = VoterManager()
    results = voter_manager.update_voter_by_id(
        voter_id, facebook_email, facebook_profile_image_url_https,
        first_name, middle_name, last_name,
        interface_status_flags,
        flag_integer_to_set, flag_integer_to_unset,
        notification_settings_flags,
        notification_flag_integer_to_set, notification_flag_integer_to_unset,
        twitter_profile_image_url_https, we_vote_hosted_profile_image_url_large,
        we_vote_hosted_profile_image_url_medium, we_vote_hosted_profile_image_url_tiny)
    voter = results['voter']
    json_data = {
        'status':                                   results['status'],
        'success':                                  results['success'],
        'voter_device_id':                          voter_device_id,
        'facebook_email':                           facebook_email,
        'facebook_profile_image_url_https':         facebook_profile_image_url_https,
        'first_name':                               first_name,
        'middle_name':                              middle_name,
        'last_name':                                last_name,
        'twitter_profile_image_url_https':          twitter_profile_image_url_https,
        'we_vote_hosted_profile_image_url_large':   we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':  we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':    we_vote_hosted_profile_image_url_tiny,
        'voter_updated':                            results['voter_updated'],
        'interface_status_flags':                   voter.interface_status_flags,
        'flag_integer_to_set':                      flag_integer_to_set,
        'flag_integer_to_unset':                    flag_integer_to_unset,
        'notification_settings_flags':              voter.notification_settings_flags,
        'notification_flag_integer_to_set':         notification_flag_integer_to_set,
        'notification_flag_integer_to_unset':       notification_flag_integer_to_unset,
        'voter_donation_history_list':              donation_list,
    }

    response = HttpResponse(json.dumps(json_data), content_type='application/json')
    return response
