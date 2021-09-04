# apis_v1/views/views_voter.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from apis_v1.controllers import voter_count
from ballot.controllers import choose_election_and_prepare_ballot_data,voter_ballot_items_retrieve_for_api, \
    voter_ballot_list_retrieve_for_api
from ballot.models import BallotItemListManager, BallotReturnedManager, find_best_previously_stored_ballot_returned, \
    OFFICE, CANDIDATE, MEASURE, VoterBallotSavedManager
from bookmark.controllers import voter_all_bookmarks_status_retrieve_for_api, voter_bookmark_off_save_for_api, \
    voter_bookmark_on_save_for_api, voter_bookmark_status_retrieve_for_api
from config.base import get_environment_variable
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django_user_agents.utils import get_user_agent
from email_outbound.controllers import voter_email_address_save_for_api, voter_email_address_retrieve_for_api, \
    voter_email_address_sign_in_for_api, voter_email_address_verify_for_api
from email_outbound.models import EmailAddress, EmailManager
from wevote_functions.functions import extract_first_name_from_full_name, extract_last_name_from_full_name
from follow.controllers import voter_issue_follow_for_api
from geoip.controllers import voter_location_retrieve_from_ip_for_api
from image.controllers import TWITTER, FACEBOOK, cache_master_and_resized_image, create_resized_images
from import_export_ballotpedia.controllers import voter_ballot_items_retrieve_from_ballotpedia_for_api_v4
from import_export_facebook.controllers import voter_facebook_sign_in_retrieve_for_api, \
    voter_facebook_sign_in_save_for_api
from import_export_google_civic.controllers import voter_ballot_items_retrieve_from_google_civic_for_api
from import_export_twitter.controllers import voter_twitter_save_to_current_account_for_api
import json
from organization.models import OrganizationManager
from position.controllers import voter_all_positions_retrieve_for_api, \
    voter_position_retrieve_for_api, voter_position_comment_save_for_api, voter_position_visibility_save_for_api
from sms.controllers import voter_sms_phone_number_retrieve_for_api, voter_sms_phone_number_save_for_api
from sms.models import SMSManager
from support_oppose_deciding.controllers import voter_opposing_save, voter_stop_opposing_save, \
    voter_stop_supporting_save, voter_supporting_save_for_api
from voter.controllers import voter_address_retrieve_for_api, voter_create_for_api, voter_merge_two_accounts_for_api, \
    voter_merge_two_accounts_action, voter_photo_save_for_api, voter_retrieve_for_api, \
    voter_save_photo_from_file_reader, voter_sign_out_for_api, voter_split_into_two_accounts_for_api
from voter.models import BALLOT_ADDRESS, fetch_voter_we_vote_id_from_voter_device_link, \
    PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, PROFILE_IMAGE_TYPE_UPLOADED, \
    VoterAddress, VoterAddressManager, VoterDeviceLink, VoterDeviceLinkManager, VoterManager, Voter, \
    voter_has_authority

from voter_guide.controllers import voter_follow_all_organizations_followed_by_organization_for_api
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_maximum_number_to_retrieve_from_request, \
    get_voter_device_id, is_voter_device_id_valid, positive_value_exists
from apis_v1.views import views_voter_utils

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

                # DALE 2018-09-06 TURNED OFF
                # google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
                #     voter_device_id, text_for_map_search, use_test_election)
                # status += google_retrieve_results['status'] + ", "
                #
                # if positive_value_exists(google_retrieve_results['google_civic_election_id']):
                #     # Update voter_address with the google_civic_election_id retrieved from Google Civic
                #     # and clear out ballot_saved information
                #     google_civic_election_id = google_retrieve_results['google_civic_election_id']
                #
                #     voter_address.google_civic_election_id = google_civic_election_id
                #     voter_address_update_results = voter_address_manager.update_existing_voter_address_object(
                #         voter_address)
                #
                #     if voter_address_update_results['success']:
                #         # Replace the former google_civic_election_id from this voter_device_link
                #         voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(
                #             voter_device_id)
                #         if voter_device_link_results['voter_device_link_found']:
                #             voter_device_link = voter_device_link_results['voter_device_link']
                #             voter_device_link_manager.update_voter_device_link_with_election_id(
                #                 voter_device_link, google_retrieve_results['google_civic_election_id'])
                #
                # else:
                #     # This block of code helps us if the google_civic_election_id wasn't found when we reached out
                #     # to the Google Civic API, following finding the voter's location from IP address.
                #     google_civic_election_id = 0

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
    substituted_address_nearby = False
    voter_entered_address = True
    voter_specific_ballot_from_google_civic = False
    status = ""
    success = True

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
        status += device_id_results['status']
        json_data = {
            'status':               status,
            'success':              False,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not address_variable_exists:
        status += "MISSING_GET_VARIABLE-ADDRESS "
        json_data = {
            'status':               status,
            'success':              False,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # We retrieve voter_device_link
    voter_ballot_saved_manager = VoterBallotSavedManager()
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id,
                                                                                     read_only=True)
    if voter_device_link_results['voter_device_link_found']:
        voter_device_link = voter_device_link_results['voter_device_link']
        voter_id = voter_device_link.voter_id
    else:
        status += "VOTER_DEVICE_LINK_NOT_FOUND_FROM_DEVICE_ID "
        json_data = {
            'status':               status,
            'success':              False,
            'voter_device_id':      voter_device_id,
            'text_for_map_search':  text_for_map_search,
            'simple_save':          simple_save,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_ADDRESS_SAVE "
        json_data = {
            'status':               status,
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

    status += voter_address_save_results['status']
    # If simple_save is passed in only save address and then send response (you must pass in a google_civic_election_id)
    if positive_value_exists(simple_save) and positive_value_exists(google_civic_election_id):
        success = voter_address_save_results['success'] and voter_address_save_results['voter_address_found']
        status += "SIMPLE_ADDRESS_SAVE "
        json_data = {
            'status':               status,
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

        turn_off_direct_voter_ballot_retrieve = False  # Search for this variable elsewhere
        default_election_data_source_is_ballotpedia = True
        if positive_value_exists(simple_save):
            # Do not retrieve / return a ballot
            pass
        elif turn_off_direct_voter_ballot_retrieve:
            # We set this option when we want to force the retrieval of a nearby ballot
            pass
        elif default_election_data_source_is_ballotpedia:
            status += "VOTER_ADDRESS_SAVE-SHOULD_WE_USE_BALLOTPEDIA_API? "
            length_at_which_we_suspect_address_has_street = 25
            length_of_text_for_map_search = 0
            if isinstance(text_for_map_search, str):
                length_of_text_for_map_search = len(text_for_map_search)
            was_refreshed_from_ballotpedia_just_now = False

            # We don't want to call Ballotpedia when we just have "City, State ZIP". Since we don't always know
            #  whether we have a street address or not, then we use a simple string length cut-off.
            if length_of_text_for_map_search > length_at_which_we_suspect_address_has_street:
                status += "TEXT_FOR_MAP_SEARCH_LONG_ENOUGH "
                # 1a) Get ballot data from Ballotpedia for the actual VoterAddress
                ballotpedia_retrieve_results = voter_ballot_items_retrieve_from_ballotpedia_for_api_v4(
                    voter_device_id,
                    text_for_map_search=text_for_map_search,
                    google_civic_election_id=google_civic_election_id)
                status += ballotpedia_retrieve_results['status']
                if ballotpedia_retrieve_results['google_civic_election_id'] \
                        and ballotpedia_retrieve_results['ballot_returned_found']:
                    was_refreshed_from_ballotpedia_just_now = True
                    is_from_substituted_address = False
                    substituted_address_nearby = ''
                    is_from_test_address = False
                    polling_location_we_vote_id_source = ''  # Not used when retrieving directly for the voter

                    # These variables are needed below
                    ballot_location_display_name = ballotpedia_retrieve_results['ballot_location_display_name']
                    ballot_returned_we_vote_id = ballotpedia_retrieve_results['ballot_returned_we_vote_id']

                    # We update the voter_address with this google_civic_election_id outside of this function

                    # Save the meta information for this ballot data
                    save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                        voter_id=voter_id,
                        google_civic_election_id=ballotpedia_retrieve_results['google_civic_election_id'],
                        state_code=ballotpedia_retrieve_results['state_code'],
                        election_day_text=ballotpedia_retrieve_results['election_day_text'],
                        election_description_text=ballotpedia_retrieve_results['election_description_text'],
                        original_text_for_map_search=ballotpedia_retrieve_results['text_for_map_search'],
                        substituted_address_nearby=substituted_address_nearby,
                        is_from_substituted_address=is_from_substituted_address,
                        is_from_test_ballot=is_from_test_address,
                        polling_location_we_vote_id_source=polling_location_we_vote_id_source,
                        ballot_location_display_name=ballotpedia_retrieve_results['ballot_location_display_name'],
                        ballot_returned_we_vote_id=ballotpedia_retrieve_results['ballot_returned_we_vote_id'],
                        ballot_location_shortcut=ballotpedia_retrieve_results['ballot_location_shortcut'],
                        original_text_city=ballotpedia_retrieve_results['original_text_city'],
                        original_text_state=ballotpedia_retrieve_results['original_text_state'],
                        original_text_zip=ballotpedia_retrieve_results['original_text_zip'],
                    )
                    status += save_results['status']
                    google_civic_election_id = ballotpedia_retrieve_results['google_civic_election_id']
            else:
                status += "NOT_REACHING_OUT_TO_BALLOTPEDIA "

            if not was_refreshed_from_ballotpedia_just_now:
                # 2) Find ballot data previously stored from a nearby address
                ballot_returned_results = find_best_previously_stored_ballot_returned(voter_id, text_for_map_search)
                status += ballot_returned_results['status']
                if ballot_returned_results['ballot_returned_found']:
                    # If this ballot_returned entry is the result of searching based on an address, as opposed to
                    # a specific_ballot_requested, we want to update the VoterAddress
                    if positive_value_exists(voter_address.text_for_map_search):
                        try:
                            voter_address.ballot_location_display_name = \
                                ballot_returned_results['ballot_location_display_name']
                            voter_address.ballot_returned_we_vote_id = \
                                ballot_returned_results['ballot_returned_we_vote_id']
                            voter_address.save()
                        except Exception as e:
                            status += "COULD_NOT_SAVE_VOTER_ADDRESS: " + str(e) + " "

                    ballot_returned_we_vote_id = ballot_returned_results['ballot_returned_we_vote_id']
                    google_civic_election_id = ballot_returned_results['google_civic_election_id']
                    if positive_value_exists(google_civic_election_id) and positive_value_exists(voter_id):
                        # Delete voter-specific ballot_returned for this election
                        ballot_returned_manager = BallotReturnedManager()
                        results = ballot_returned_manager.delete_ballot_returned_by_identifier(
                            voter_id=voter_id,
                            google_civic_election_id=google_civic_election_id)

                        # Delete voter_ballot_saved for this election
                        voter_ballot_saved_manager = VoterBallotSavedManager()
                        voter_ballot_saved_manager.delete_voter_ballot_saved(
                            voter_id=voter_id, google_civic_election_id=google_civic_election_id)

                        # Delete all existing voter-specific ballot items for this election
                        ballot_item_list_manager = BallotItemListManager()
                        ballot_item_list_manager.delete_all_ballot_items_for_voter(voter_id, google_civic_election_id)

                    # And now store the details of this ballot for this voter
                    is_from_substituted_address = True
                    is_from_test_address = False
                    save_results = voter_ballot_saved_manager.update_or_create_voter_ballot_saved(
                        voter_id=voter_id,
                        google_civic_election_id=ballot_returned_results['google_civic_election_id'],
                        state_code=ballot_returned_results['state_code'],
                        election_day_text=ballot_returned_results['election_day_text'],
                        election_description_text=ballot_returned_results['election_description_text'],
                        original_text_for_map_search=text_for_map_search,
                        substituted_address_nearby=ballot_returned_results['substituted_address_nearby'],
                        is_from_substituted_address=is_from_substituted_address,
                        is_from_test_ballot=is_from_test_address,
                        polling_location_we_vote_id_source=ballot_returned_results[
                            'polling_location_we_vote_id_source'],
                        ballot_location_display_name=ballot_returned_results['ballot_location_display_name'],
                        ballot_returned_we_vote_id=ballot_returned_results['ballot_returned_we_vote_id'],
                        ballot_location_shortcut=ballot_returned_results['ballot_location_shortcut'],
                        substituted_address_city=ballot_returned_results['original_text_city'],
                        substituted_address_state=ballot_returned_results['original_text_state'],
                        substituted_address_zip=ballot_returned_results['original_text_zip'],
                    )
                    status += save_results['status']

        else:
            # Reach out to Google and populate ballot items in the database with fresh ballot data
            google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(  # DEBUG=1
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
            status += voter_address_update_results['status']
            if voter_address_update_results['success']:
                # Replace the former google_civic_election_id from this voter_device_link
                voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
                if voter_device_link_results['voter_device_link_found']:
                    voter_device_link = voter_device_link_results['voter_device_link']
                    voter_device_link_manager.update_voter_device_link_with_election_id(
                        voter_device_link, google_civic_election_id)
                if voter_address_update_results['voter_address_found']:
                    voter_address = voter_address_update_results['voter_address']
                    text_for_map_search_saved = voter_address.text_for_map_search

    if positive_value_exists(simple_save):
        # Do not retrieve / return a ballot
        json_data = {
            'status':                       status,
            'success':                      success,
            'google_civic_election_id':     google_civic_election_id,
            'text_for_map_search':          text_for_map_search,
            'simple_save':                  simple_save,
            'substituted_address_nearby':   substituted_address_nearby,
            'ballot_found':                 False,
            'ballot_caveat':                None,
            'is_from_substituted_address':  None,
            'is_from_test_ballot':          None,
            'ballot_item_list':             [],
        }
    else:
        # This does return the data twice, since the WebApp requests
        # voterBallotItemRetrieve when voterAddressSave completes
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

    original_text_city = ''
    original_text_state = ''
    original_text_zip = ''

    google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
        voter_device_id, text_for_map_search, use_test_election)

    if google_retrieve_results['google_civic_election_id'] and not use_test_election:
        # After the ballot is retrieved from google we want to save some info about it for the voter
        if positive_value_exists(voter_device_id):
            voter_device_link_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id,
                                                                                             read_only=True)
            if voter_device_link_results['voter_device_link_found']:
                voter_device_link = voter_device_link_results['voter_device_link']
                voter_id = voter_device_link.voter_id

        if positive_value_exists(google_retrieve_results['ballot_returned_we_vote_id']):
            ballot_returned = google_retrieve_results['ballot_returned']
            original_text_city = ballot_returned.normalized_city
            original_text_state = ballot_returned.normalized_state
            original_text_zip = ballot_returned.normalized_zip

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
                original_text_city=original_text_city,
                original_text_state=original_text_state,
                original_text_zip=original_text_zip,
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
        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id,
                                                                                         read_only=True)
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


def voter_count_view(request):  # voterCountView
    return voter_count()


def voter_create_view(request):  # voterCreate
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return voter_create_for_api(voter_device_id)


def voter_create_new_account_view(request):  # voterCreateNewAccount
    authority_required = {'admin'}
    status = ""
    if voter_has_authority(request, authority_required):
        # voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
        first_name = request.GET.get('firstname', '')
        last_name = request.GET.get('lastname', '')
        email = request.GET.get('email', '')
        password = request.GET.get('password', '')
        is_admin = request.GET.get('is_admin', False) == 'true'
        is_analytics_admin = request.GET.get('is_analytics_admin', False) == 'true'
        is_partner_organization = request.GET.get('is_partner_organization', False) == 'true'
        is_political_data_manager = request.GET.get('is_political_data_manager', False) == 'true'
        is_political_data_viewer = request.GET.get('is_political_data_viewer', False) == 'true'
        is_verified_volunteer = request.GET.get('is_verified_volunteer', False) == 'true'

        # Check to make sure email isn't attached to existing account in EmailAddress table
        email_address_queryset = EmailAddress.objects.all()
        email_address_queryset = email_address_queryset.filter(
            normalized_email_address__iexact=email,
            deleted=False
        )
        email_address_list = list(email_address_queryset)
        email_already_in_use = True if len(email_address_list) > 0 else False
        if email_already_in_use:
            status += "EMAIL_ADDRESS_ALREADY_IN_USE "
            json_data = {
                'status':           status,
                'success':          False,
                'duplicate_email':  True,
                'has_permission':   True,
            }
        else:
            results = Voter.objects.create_new_voter_account(
                first_name, last_name, email, password, is_admin, is_analytics_admin, is_partner_organization,
                is_political_data_manager, is_political_data_viewer, is_verified_volunteer)

            json_data = {
                'status':           results['status'],
                'success':          results['success'],
                'duplicate_email':  results['duplicate_email'],
                'has_permission':   True,
            }
    else:
        json_data = {
            'status':           "Insufficient rights to add user",
            'success':          True,
            'duplicate_email':  False,
            'has_permission':   False,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


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
    resend_verification_code_email = positive_value_exists(request.GET.get('resend_verification_code_email', False))
    send_link_to_sign_in = positive_value_exists(request.GET.get('send_link_to_sign_in', False))
    send_sign_in_code_email = positive_value_exists(request.GET.get('send_sign_in_code_email', False))
    make_primary_email = positive_value_exists(request.GET.get('make_primary_email', False))
    delete_email = positive_value_exists(request.GET.get('delete_email', ""))
    is_cordova = positive_value_exists(request.GET.get('is_cordova', False))
    hostname = request.GET.get('hostname', '')

    results = voter_email_address_save_for_api(
        voter_device_id=voter_device_id,
        text_for_email_address=text_for_email_address,
        incoming_email_we_vote_id=incoming_email_we_vote_id,
        send_link_to_sign_in=send_link_to_sign_in,
        send_sign_in_code_email=send_sign_in_code_email,
        resend_verification_email=resend_verification_email,
        resend_verification_code_email=resend_verification_code_email,
        make_primary_email=make_primary_email,
        delete_email=delete_email,
        is_cordova=is_cordova,
        web_app_root_url=hostname,
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
        'email_address_already_owned_by_this_voter':    results['email_address_already_owned_by_this_voter'],
        'email_address_created':            results['email_address_created'],
        'email_address_not_valid':          results['email_address_not_valid'],
        'email_address_deleted':            results['email_address_deleted'],
        'verification_email_sent':          results['verification_email_sent'],
        'link_to_sign_in_email_sent':       results['link_to_sign_in_email_sent'],
        'sign_in_code_email_sent':          results['sign_in_code_email_sent'],
        'email_address_found':              results['email_address_found'],
        'email_address_list_found':         results['email_address_list_found'],
        'email_address_list':               results['email_address_list'],
        'secret_code_system_locked_for_this_voter_device_id':
            results['secret_code_system_locked_for_this_voter_device_id'],
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


def voter_issue_follow_view(request):  # issueFollow
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    issue_we_vote_id = request.GET.get('issue_we_vote_id', False)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    follow_value = positive_value_exists(request.GET.get('follow', False))
    user_agent_string = request.META['HTTP_USER_AGENT']
    user_agent_object = get_user_agent(request)
    ignore_value = positive_value_exists(request.GET.get('ignore', False))

    result = voter_issue_follow_for_api(voter_device_id=voter_device_id,
                                        issue_we_vote_id=issue_we_vote_id,
                                        follow_value=follow_value,
                                        ignore_value=ignore_value, user_agent_string=user_agent_string,
                                        user_agent_object=user_agent_object)
    result['google_civic_election_id'] = google_civic_election_id
    return HttpResponse(json.dumps(result), content_type='application/json')


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
    hostname = request.GET.get('hostname', '')

    results = voter_merge_two_accounts_for_api(voter_device_id=voter_device_id,
                                               email_secret_key=email_secret_key,
                                               facebook_secret_key=facebook_secret_key,
                                               twitter_secret_key=twitter_secret_key,
                                               invitation_secret_key=invitation_secret_key,
                                               web_app_root_url=hostname)

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


def voter_plan_list_retrieve_view(request):  # voterPlanListRetrieve
    """
    Retrieve voter plans so we can show off examples from other voters
    :param request:
    :return:
    """
    status = ''
    voter_plan_list = []
    voter_manager = VoterManager()
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    results = voter_manager.retrieve_voter_plan_list(google_civic_election_id=google_civic_election_id)
    if not results['success']:
        status += results['status']
        status += "RETRIEVE_VOTER_PLAN_LIST_FAILED "
        json_data = {
            'status': status,
            'success': False,
            'voter_plan_list': voter_plan_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    modified_voter_plan_list = []
    voter_plan_list = results['voter_plan_list']
    for voter_plan in voter_plan_list:
        voter_plan_dict = {
            'date_entered':             voter_plan.date_entered.strftime('%Y-%m-%d %H:%M:%S'),
            'date_last_changed':        voter_plan.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'google_civic_election_id': voter_plan.google_civic_election_id,
            'show_to_public':           voter_plan.show_to_public,
            'state_code':               voter_plan.state_code,
            'voter_plan_data_serialized':     voter_plan.voter_plan_data_serialized,
            'voter_plan_text':          voter_plan.voter_plan_text,
            'voter_we_vote_id':         voter_plan.voter_we_vote_id,
        }
        modified_voter_plan_list.append(voter_plan_dict)
    json_data = {
        'status': status,
        'success': True,
        'voter_plan_list': modified_voter_plan_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_plans_for_voter_retrieve_view(request):  # voterPlansForVoterRetrieve
    """
    Retrieve all voter plans for signed in voter
    :param request:
    :return:
    """
    status = ''
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_we_vote_id = ''
    voter_plan_list = []
    voter_manager = VoterManager()

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)

    if not positive_value_exists(voter_we_vote_id):
        status += "VOTER_PLANS_RETRIEVE_MISSING_VOTER_WE_VOTE_ID "
        json_data = {
            'status': status,
            'success': False,
            'voter_plan_list': voter_plan_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = voter_manager.retrieve_voter_plan_list(voter_we_vote_id=voter_we_vote_id)
    if not results['success']:
        status += results['status']
        status += "RETRIEVE_VOTER_PLAN_LIST_FAILED "
        json_data = {
            'status': status,
            'success': False,
            'voter_plan_list': voter_plan_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    modified_voter_plan_list = []
    voter_plan_list = results['voter_plan_list']
    for voter_plan in voter_plan_list:
        voter_plan_dict = {
            'date_entered':             voter_plan.date_entered.strftime('%Y-%m-%d %H:%M:%S'),
            'date_last_changed':        voter_plan.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'google_civic_election_id': voter_plan.google_civic_election_id,
            'show_to_public':           voter_plan.show_to_public,
            'state_code':               voter_plan.state_code,
            'voter_plan_data_serialized':     voter_plan.voter_plan_data_serialized,
            'voter_plan_text':          voter_plan.voter_plan_text,
            'voter_we_vote_id':         voter_plan.voter_we_vote_id,
        }
        modified_voter_plan_list.append(voter_plan_dict)

    json_data = {
        'status': status,
        'success': True,
        'voter_plan_list': modified_voter_plan_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_plan_save_view(request):  # voterPlanSave
    """
    Save current voter plan for this voter
    :param request:
    :return:
    """
    status = ''
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    show_to_public = positive_value_exists(request.GET.get('show_to_public', False))
    state_code = request.GET.get('state_code', '')
    voter_plan_data_serialized = request.GET.get('voter_plan_data_serialized', '')
    # voter_plan_data_serialized = json.loads(voter_plan_data_serialized)  # Leave as a string
    voter_plan_text = request.GET.get('voter_plan_text', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_we_vote_id = ''
    voter_plan_list = []
    voter_manager = VoterManager()

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)

    if not positive_value_exists(voter_we_vote_id):
        status += "VOTER_PLAN_SAVE_MISSING_VOTER_WE_VOTE_ID "
        json_data = {
            'status': status,
            'success': False,
            'voter_plan_list': voter_plan_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not positive_value_exists(google_civic_election_id):
        status += "VOTER_PLAN_SAVE_MISSING_GOOGLE_CIVIC_ELECTION_ID "
        json_data = {
            'status': status,
            'success': False,
            'voter_plan_list': voter_plan_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = voter_manager.update_or_create_voter_plan(
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        show_to_public=show_to_public,
        state_code=state_code,
        voter_plan_data_serialized=voter_plan_data_serialized,
        voter_plan_text=voter_plan_text,
    )
    if not results['success']:
        status += results['status']
        status += "COULD_NOT_SAVE_VOTER_PLAN "

    results = voter_manager.retrieve_voter_plan_list(voter_we_vote_id=voter_we_vote_id)
    if not results['success']:
        status += results['status']
        status += "RETRIEVE_VOTER_PLAN_LIST_FAILED "
        json_data = {
            'status': status,
            'success': False,
            'voter_plan_list': voter_plan_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    modified_voter_plan_list = []
    voter_plan_list = results['voter_plan_list']
    for voter_plan in voter_plan_list:
        voter_plan_dict = {
            'date_entered':             voter_plan.date_entered.strftime('%Y-%m-%d %H:%M:%S'),
            'date_last_changed':        voter_plan.date_last_changed.strftime('%Y-%m-%d %H:%M:%S'),
            'google_civic_election_id': voter_plan.google_civic_election_id,
            'show_to_public':           voter_plan.show_to_public,
            'state_code':               voter_plan.state_code,
            'voter_plan_data_serialized':     voter_plan.voter_plan_data_serialized,
            'voter_plan_text':          voter_plan.voter_plan_text,
            'voter_we_vote_id':         voter_plan.voter_we_vote_id,
        }
        modified_voter_plan_list.append(voter_plan_dict)

    json_data = {
        'status': status,
        'success': True,
        'voter_plan_list': modified_voter_plan_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


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
    split_off_twitter = request.GET.get('split_off_twitter', True)  # We want to break off the Twitter from this account

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


def voter_sms_phone_number_retrieve_view(request):  # voterSMSPhoneNumberRetrieve
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = voter_sms_phone_number_retrieve_for_api(voter_device_id=voter_device_id)

    json_data = {
        'status':                   results['status'],
        'success':                  results['success'],
        'voter_device_id':          voter_device_id,
        'sms_phone_number_list_found': results['sms_phone_number_list_found'],
        'sms_phone_number_list':       results['sms_phone_number_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_sms_phone_number_save_view(request):  # voterSMSPhoneNumberSave
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    sms_phone_number = request.GET.get('sms_phone_number', '')
    incoming_sms_we_vote_id = request.GET.get('sms_we_vote_id', '')
    resend_verification_sms = positive_value_exists(request.GET.get('resend_verification_sms', False))
    send_sign_in_code_sms = positive_value_exists(request.GET.get('send_sign_in_code_sms', False))
    make_primary_sms_phone_number = positive_value_exists(request.GET.get('make_primary_sms_phone_number', False))
    delete_sms = positive_value_exists(request.GET.get('delete_sms', ""))
    hostname = request.GET.get('hostname', '')

    results = voter_sms_phone_number_save_for_api(
        voter_device_id=voter_device_id,
        sms_phone_number=sms_phone_number,
        incoming_sms_we_vote_id=incoming_sms_we_vote_id,
        send_sign_in_code_sms=send_sign_in_code_sms,
        resend_verification_sms=resend_verification_sms,
        make_primary_sms_phone_number=make_primary_sms_phone_number,
        delete_sms=delete_sms,
        web_app_root_url=hostname,
        )

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
        'sms_phone_number':                 sms_phone_number,
        'make_primary_sms_phone_number':    make_primary_sms_phone_number,
        'delete_sms':                       delete_sms,
        'sms_phone_number_we_vote_id':      results['sms_phone_number_we_vote_id'],
        'sms_phone_number_saved_we_vote_id':    results['sms_phone_number_saved_we_vote_id'],
        'sms_phone_number_already_owned_by_other_voter':    results['sms_phone_number_already_owned_by_other_voter'],
        'sms_phone_number_already_owned_by_this_voter':     results['sms_phone_number_already_owned_by_this_voter'],
        'sms_phone_number_created':         results['sms_phone_number_created'],
        'sms_phone_number_deleted':         results['sms_phone_number_deleted'],
        'verification_sms_sent':            results['verification_sms_sent'],
        'link_to_sign_in_sms_sent':         results['link_to_sign_in_sms_sent'],
        'sign_in_code_sms_sent':            results['sign_in_code_sms_sent'],
        'sms_phone_number_found':           results['sms_phone_number_found'],
        'sms_phone_number_list_found':      results['sms_phone_number_list_found'],
        'sms_phone_number_list':            results['sms_phone_number_list'],
        'secret_code_system_locked_for_this_voter_device_id':
            results['secret_code_system_locked_for_this_voter_device_id'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_stop_opposing_save_view(request):  # voterStopOpposingSave
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


def voter_stop_supporting_save_view(request):  # voterStopSupportingSave
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


def voter_supporting_save_view(request):  # voterSupportingSave
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


def return_flag_value(request, variable_name, is_post=False):
    try:
        if is_post:
            value = request.POST[variable_name]
        else:
            value = request.GET[variable_name]
        value = value.strip()
        value = convert_to_int(value)
    except KeyError:
        value = False
    return value


def return_string_value_and_changed_boolean_from_get(request, variable_name):
    value = request.GET.get(variable_name, False)
    value_changed = False
    if value is not False:
        value = value.strip()
        if value.lower() == 'false':
            value = False
            value_changed = False
        else:
            value_changed = True
    return value, value_changed


@csrf_exempt
def voter_update_view(request):  # voterUpdate
    """
    Update profile-related information for this voter
    :param request:
    :return:
    """
    from django.core.exceptions import RequestDataTooBig

    status = ""
    voter_updated = False
    voter_name_needs_to_be_updated_in_activity = False

    try:
        voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    except RequestDataTooBig:
        status += "RequestDataTooBig"
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': False,
            'facebook_email': False,
            'facebook_profile_image_url_https': False,
            'first_name': '',
            'middle_name': '',
            'last_name': '',
            'twitter_profile_image_url_https': '',
            'we_vote_hosted_profile_image_url_large': '',
            'we_vote_hosted_profile_image_url_medium': '',
            'we_vote_hosted_profile_image_url_tiny': '',
            'voter_updated': False,
            'interface_status_flags': 0,
            'flag_integer_to_set': 0,
            'flag_integer_to_unset': 0,
            'notification_settings_flags': 0,
            'notification_flag_integer_to_set': 0,
            'notification_flag_integer_to_unset': 0,
            'voter_photo_too_big': True,
        }

        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    is_post = True if request.method == 'POST' else False

    if is_post:
        facebook_email_changed = positive_value_exists(request.POST.get('facebook_email_changed', False))
        facebook_email = request.POST.get('facebook_email', '') if facebook_email_changed else False
        facebook_profile_image_url_https_changed = \
            positive_value_exists(request.POST.get('facebook_profile_image_url_https_changed', False))
        facebook_profile_image_url_https = request.POST.get('facebook_profile_image_url_https', '') \
            if facebook_profile_image_url_https_changed else False
        first_name_changed = positive_value_exists(request.POST.get('first_name_changed', False))
        first_name = request.POST.get('first_name', '') if first_name_changed else False
        middle_name_changed = positive_value_exists(request.POST.get('middle_name_changed', False))
        middle_name = request.POST.get('middle_name', '') if middle_name_changed else False
        last_name_changed = positive_value_exists(request.POST.get('last_name_changed', False))
        last_name = request.POST.get('last_name', '') if last_name_changed else False
        full_name_changed = positive_value_exists(request.POST.get('full_name_changed', False))
        full_name = request.POST.get('full_name', '') if full_name_changed else False
        name_save_only_if_no_existing_names = request.POST.get('name_save_only_if_no_existing_names', False)
        external_voter_id = request.POST.get('external_voter_id', False)
        membership_organization_we_vote_id = request.POST.get('membership_organization_we_vote_id', False)
        twitter_profile_image_url_https_changed = \
            positive_value_exists(request.POST.get('twitter_profile_image_url_https_changed', False))
        twitter_profile_image_url_https = request.POST.get('twitter_profile_image_url_https', '') \
            if twitter_profile_image_url_https_changed else False
        interface_status_flags = return_flag_value(request, 'interface_status_flags', is_post=True)
        flag_integer_to_set = return_flag_value(request, 'flag_integer_to_set', is_post=True)
        flag_integer_to_unset = return_flag_value(request, 'flag_integer_to_unset', is_post=True)
        notification_settings_flags = return_flag_value(request, 'notification_settings_flags', is_post=True)
        notification_flag_integer_to_set = return_flag_value(request, 'notification_flag_integer_to_set', is_post=True)
        notification_flag_integer_to_unset = \
            return_flag_value(request, 'notification_flag_integer_to_unset', is_post=True)
        try:
            send_journal_list = request.POST['send_journal_list']
        except KeyError:
            send_journal_list = False
        voter_photo_from_file_reader = request.POST.get('voter_photo_from_file_reader', '')
        voter_photo_changed = positive_value_exists(request.POST.get('voter_photo_changed', False))
        profile_image_type_currently_active = request.POST.get('profile_image_type_currently_active', False)
        profile_image_type_currently_active_changed = \
            positive_value_exists(request.POST.get('profile_image_type_currently_active_changed', False))
    else:
        facebook_email, facebook_email_changed = \
            return_string_value_and_changed_boolean_from_get(request, 'facebook_email')
        facebook_profile_image_url_https, facebook_profile_image_url_https_changed = \
            return_string_value_and_changed_boolean_from_get(request, 'facebook_profile_image_url_https')
        first_name, first_name_changed = return_string_value_and_changed_boolean_from_get(request, 'first_name')
        middle_name, middle_name_changed = return_string_value_and_changed_boolean_from_get(request, 'middle_name')
        last_name, last_name_changed = return_string_value_and_changed_boolean_from_get(request, 'last_name')
        full_name, full_name_changed = return_string_value_and_changed_boolean_from_get(request, 'full_name')
        name_save_only_if_no_existing_names = request.GET.get('name_save_only_if_no_existing_names', False)
        external_voter_id = request.GET.get('external_voter_id', False)
        membership_organization_we_vote_id = request.GET.get('membership_organization_we_vote_id', False)
        twitter_profile_image_url_https, twitter_profile_image_url_https_changed = \
            return_string_value_and_changed_boolean_from_get(request, 'twitter_profile_image_url_https')
        interface_status_flags = return_flag_value(request, 'interface_status_flags')
        flag_integer_to_set = return_flag_value(request, 'flag_integer_to_set')
        flag_integer_to_unset = return_flag_value(request, 'flag_integer_to_unset')
        notification_settings_flags = return_flag_value(request, 'notification_settings_flags')
        notification_flag_integer_to_set = return_flag_value(request, 'notification_flag_integer_to_set')
        notification_flag_integer_to_unset = return_flag_value(request, 'notification_flag_integer_to_unset')
        try:
            send_journal_list = request.GET['send_journal_list']
        except KeyError:
            send_journal_list = False
        voter_photo_from_file_reader = ''
        voter_photo_changed = False
        profile_image_type_currently_active = False
        profile_image_type_currently_active_changed = False

    # Voter has visited a private-labeled We Vote site, and we want to store that voter's id from another database
    if external_voter_id is not False:
        external_voter_id = external_voter_id.strip()
        if external_voter_id.lower() == 'false':
            external_voter_id = False
    # Voter has visited a private-labeled We Vote site, and we want to connect this voter to that organization
    if membership_organization_we_vote_id is not False:
        membership_organization_we_vote_id = membership_organization_we_vote_id.strip()
        if membership_organization_we_vote_id.lower() == 'false':
            membership_organization_we_vote_id = False

    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        status += "VOTER_DEVICE_ID_NOT_BALLOT " + device_id_results['status']
        json_data = {
                'status':                           status,
                'success':                          False,
                'voter_device_id':                  voter_device_id,
                'facebook_email':                   facebook_email,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
                'first_name':                       first_name,
                'middle_name':                      middle_name,
                'last_name':                        last_name,
                'twitter_profile_image_url_https':  twitter_profile_image_url_https,
                'we_vote_hosted_profile_image_url_large': "",
                'we_vote_hosted_profile_image_url_medium': "",
                'we_vote_hosted_profile_image_url_tiny': "",
                'voter_updated':                    voter_updated,
                'interface_status_flags':           interface_status_flags,
                'flag_integer_to_set':              flag_integer_to_set,
                'flag_integer_to_unset':            flag_integer_to_unset,
                'notification_settings_flags':      notification_settings_flags,
                'notification_flag_integer_to_set': notification_flag_integer_to_set,
                'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
            }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    at_least_one_variable_has_changed = True if \
        facebook_email \
        or facebook_profile_image_url_https \
        or first_name is not False \
        or middle_name is not False \
        or last_name is not False \
        or full_name \
        or interface_status_flags is not False \
        or flag_integer_to_unset is not False \
        or flag_integer_to_set is not False \
        or notification_settings_flags is not False \
        or notification_flag_integer_to_unset is not False \
        or notification_flag_integer_to_set is not False \
        or voter_photo_changed is not False \
        or profile_image_type_currently_active_changed is not False \
        or send_journal_list \
        else False
    external_voter_id_to_be_saved = True \
        if (membership_organization_we_vote_id is not False and external_voter_id is not False) \
        else False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_DEVICE_ID-VOTER_UPDATE "
        json_data = {
            'status':                           status,
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'facebook_email':                   facebook_email,
            'facebook_profile_image_url_https': facebook_profile_image_url_https,
            'first_name':                       first_name,
            'middle_name':                      middle_name,
            'last_name':                        last_name,
            'twitter_profile_image_url_https':  twitter_profile_image_url_https,
            'we_vote_hosted_profile_image_url_large':   "",
            'we_vote_hosted_profile_image_url_medium':  "",
            'we_vote_hosted_profile_image_url_tiny':    "",
            'voter_updated':                    voter_updated,
            'interface_status_flags':           interface_status_flags,
            'flag_integer_to_set':              flag_integer_to_set,
            'flag_integer_to_unset':            flag_integer_to_unset,
            'notification_settings_flags':      notification_settings_flags,
            'notification_flag_integer_to_set': notification_flag_integer_to_set,
            'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    # At this point, we have a valid voter
    voter = voter_results['voter']
    voter_we_vote_id = voter.we_vote_id
    voter_full_name_at_start = voter.get_full_name(real_name_only=True)

    if at_least_one_variable_has_changed or external_voter_id_to_be_saved:
        pass
    else:
        # If here, we want to return the latest data from the voter object
        status += "MISSING_VARIABLE-NO_VARIABLES_PASSED_IN_TO_CHANGE "
        json_data = {
                'status':                                   status,
                'success':                                  True,
                'voter_device_id':                          voter_device_id,
                'facebook_email':                           voter.facebook_email,
                'facebook_profile_image_url_https':         voter.facebook_profile_image_url_https,
                'first_name':                               voter.first_name,
                'middle_name':                              voter.middle_name,
                'last_name':                                voter.last_name,
                'twitter_profile_image_url_https':          voter.twitter_profile_image_url_https,
                'we_vote_hosted_profile_image_url_large':   voter.we_vote_hosted_profile_image_url_large,
                'we_vote_hosted_profile_image_url_medium':  voter.we_vote_hosted_profile_image_url_medium,
                'we_vote_hosted_profile_image_url_tiny':    voter.we_vote_hosted_profile_image_url_tiny,
                'voter_updated':                            voter_updated,
                'interface_status_flags':                   voter.interface_status_flags,
                'flag_integer_to_set':                      flag_integer_to_set,
                'flag_integer_to_unset':                    flag_integer_to_unset,
                'notification_settings_flags':              voter.notification_settings_flags,
                'notification_flag_integer_to_set':         notification_flag_integer_to_set,
                'notification_flag_integer_to_unset':       notification_flag_integer_to_unset,
            }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    # These variables will contain copy of default profile photo
    we_vote_hosted_profile_image_url_large = False
    we_vote_hosted_profile_image_url_medium = False
    we_vote_hosted_profile_image_url_tiny = False

    we_vote_hosted_profile_twitter_image_url_large = False
    we_vote_hosted_profile_twitter_image_url_medium = False
    we_vote_hosted_profile_twitter_image_url_tiny = False
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
        we_vote_hosted_profile_twitter_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_twitter_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_twitter_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']
        if positive_value_exists(cached_twitter_profile_image_url_https):
            twitter_profile_image_url_https = cached_twitter_profile_image_url_https

    we_vote_hosted_profile_facebook_image_url_large = False
    we_vote_hosted_profile_facebook_image_url_medium = False
    we_vote_hosted_profile_facebook_image_url_tiny = False
    if facebook_profile_image_url_https:
        # Cache original and resized images
        # TODO: Replace voter.facebook_id with value from facebook link to voter
        cache_results = cache_master_and_resized_image(
            voter_we_vote_id=voter.we_vote_id,
            facebook_user_id=voter.facebook_id,
            facebook_profile_image_url_https=facebook_profile_image_url_https,
            image_source=FACEBOOK)
        cached_facebook_profile_image_url_https = cache_results['cached_facebook_profile_image_url_https']
        we_vote_hosted_profile_facebook_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
        we_vote_hosted_profile_facebook_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
        we_vote_hosted_profile_facebook_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']
        if positive_value_exists(cached_facebook_profile_image_url_https):
            facebook_profile_image_url_https = cached_facebook_profile_image_url_https

    #
    # Save voter_photo_from_file_reader and get back we_vote_hosted_voter_photo_original_url
    we_vote_hosted_profile_uploaded_image_url_large = False
    we_vote_hosted_profile_uploaded_image_url_medium = False
    we_vote_hosted_profile_uploaded_image_url_tiny = False
    if voter_photo_changed and voter_photo_from_file_reader:
        photo_results = voter_save_photo_from_file_reader(
            voter_we_vote_id=voter_we_vote_id,
            voter_photo_from_file_reader=voter_photo_from_file_reader)
        if photo_results['we_vote_hosted_voter_photo_original_url']:
            we_vote_hosted_voter_photo_original_url = photo_results['we_vote_hosted_voter_photo_original_url']
            # Now we want to resize to a large version
            create_resized_image_results = create_resized_images(
                voter_we_vote_id=voter_we_vote_id,
                voter_uploaded_profile_image_url_https=we_vote_hosted_voter_photo_original_url)
            we_vote_hosted_profile_uploaded_image_url_large = \
                create_resized_image_results['cached_resized_image_url_large']
            we_vote_hosted_profile_uploaded_image_url_medium = \
                create_resized_image_results['cached_resized_image_url_medium']
            we_vote_hosted_profile_uploaded_image_url_tiny = \
                create_resized_image_results['cached_resized_image_url_tiny']
    elif voter_photo_changed:
        # If here we are deleting an existing photo
        we_vote_hosted_profile_uploaded_image_url_large = ''
        we_vote_hosted_profile_uploaded_image_url_medium = ''
        we_vote_hosted_profile_uploaded_image_url_tiny = ''
        we_vote_hosted_profile_image_url_large = ''
        we_vote_hosted_profile_image_url_medium = ''
        we_vote_hosted_profile_image_url_tiny = ''
        voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UNKNOWN

    # We need profile_image_type_currently_active setting
    if profile_image_type_currently_active_changed:
        # In this case it is coming in from API call and does not need to be calculated
        pass
    else:
        profile_image_type_currently_active = voter.profile_image_type_currently_active
        if profile_image_type_currently_active not in \
                [PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UPLOADED]:
            # Do we need to calculate a value to store?
            continue_analyzing_profile_image_type_currently_active = True
            if voter_photo_changed:
                if we_vote_hosted_profile_uploaded_image_url_large and \
                        we_vote_hosted_profile_uploaded_image_url_large != '':
                    profile_image_type_currently_active_changed = True
                    profile_image_type_currently_active = PROFILE_IMAGE_TYPE_UPLOADED
                    we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_uploaded_image_url_large
                    we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_uploaded_image_url_medium
                    we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_uploaded_image_url_tiny
                    continue_analyzing_profile_image_type_currently_active = False
            if continue_analyzing_profile_image_type_currently_active:
                if we_vote_hosted_profile_facebook_image_url_large:
                    profile_image_type_currently_active_changed = True
                    profile_image_type_currently_active = PROFILE_IMAGE_TYPE_FACEBOOK
                    we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_facebook_image_url_large
                    we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_facebook_image_url_medium
                    we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_facebook_image_url_tiny
                    continue_analyzing_profile_image_type_currently_active = False
            if continue_analyzing_profile_image_type_currently_active:
                if we_vote_hosted_profile_twitter_image_url_large:
                    profile_image_type_currently_active_changed = True
                    profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
                    we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_twitter_image_url_large
                    we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_twitter_image_url_medium
                    we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_twitter_image_url_tiny
                    continue_analyzing_profile_image_type_currently_active = False

    at_least_one_variable_has_changed = True if \
        at_least_one_variable_has_changed \
        or profile_image_type_currently_active_changed \
        else False

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

    success = True
    voter_manager = VoterManager()
    voter_updated = False
    linked_organization_we_vote_id = ''
    if at_least_one_variable_has_changed:
        results = voter_manager.update_voter_by_id(
            voter_id,
            facebook_email=facebook_email,
            facebook_profile_image_url_https=facebook_profile_image_url_https,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            interface_status_flags=interface_status_flags,
            flag_integer_to_set=flag_integer_to_set,
            flag_integer_to_unset=flag_integer_to_unset,
            notification_settings_flags=notification_settings_flags,
            notification_flag_integer_to_set=notification_flag_integer_to_set,
            notification_flag_integer_to_unset=notification_flag_integer_to_unset,
            profile_image_type_currently_active=profile_image_type_currently_active,
            twitter_profile_image_url_https=twitter_profile_image_url_https,
            we_vote_hosted_profile_facebook_image_url_large=we_vote_hosted_profile_facebook_image_url_large,
            we_vote_hosted_profile_facebook_image_url_medium=we_vote_hosted_profile_facebook_image_url_medium,
            we_vote_hosted_profile_facebook_image_url_tiny=we_vote_hosted_profile_facebook_image_url_tiny,
            we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
            we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
            we_vote_hosted_profile_twitter_image_url_large=we_vote_hosted_profile_twitter_image_url_large,
            we_vote_hosted_profile_twitter_image_url_medium=we_vote_hosted_profile_twitter_image_url_medium,
            we_vote_hosted_profile_twitter_image_url_tiny=we_vote_hosted_profile_twitter_image_url_tiny,
            we_vote_hosted_profile_uploaded_image_url_large=we_vote_hosted_profile_uploaded_image_url_large,
            we_vote_hosted_profile_uploaded_image_url_medium=we_vote_hosted_profile_uploaded_image_url_medium,
            we_vote_hosted_profile_uploaded_image_url_tiny=we_vote_hosted_profile_uploaded_image_url_tiny,
        )
        status += results['status']
        success = results['success']
        voter = results['voter']
        voter_updated = results['voter_updated']
        first_name = voter.first_name
        last_name = voter.last_name
        linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    organization_manager = OrganizationManager()
    if external_voter_id_to_be_saved:
        results = organization_manager.update_or_create_organization_membership_link_to_voter(
            membership_organization_we_vote_id, external_voter_id, voter_we_vote_id)
        status += results['status']
        success = results['success']

    # When the first or last name is changed, we want to update the organization name if the organization name
    #  starts with "Voter-" or organization.most_recent_name_update_from_first_and_last is True
    voter_full_name = voter.get_full_name(real_name_only=True)
    if positive_value_exists(voter_full_name):
        if voter_full_name != voter_full_name_at_start:
            voter_name_needs_to_be_updated_in_activity = True

    voter_name_changed = False
    if positive_value_exists(voter_full_name) \
            and (incoming_first_or_last_name or incoming_full_name_can_be_processed) \
            and positive_value_exists(linked_organization_we_vote_id):
        voter_name_changed = True
    if voter_name_changed or voter_photo_changed:
        results = organization_manager.retrieve_organization_from_we_vote_id(linked_organization_we_vote_id)
        if results['organization_found']:
            organization = results['organization']
            organization_changed = False
            organization_name_changed = False
            not_real_name = False
            if positive_value_exists(organization.organization_name):
                not_real_name = organization.organization_name.startswith('Voter-')
            if positive_value_exists(organization.most_recent_name_update_from_voter_first_and_last) or not_real_name:
                if not organization.most_recent_name_update_from_voter_first_and_last:
                    organization.most_recent_name_update_from_voter_first_and_last = True
                    organization_changed = True
                if positive_value_exists(voter_full_name):
                    organization.organization_name = voter_full_name
                    organization_changed = True
                    organization_name_changed = True
            if we_vote_hosted_profile_image_url_large is not False:
                organization.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                organization_changed = True
            if we_vote_hosted_profile_image_url_medium is not False:
                organization.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                organization_changed = True
            if we_vote_hosted_profile_image_url_tiny is not False:
                organization.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                organization_changed = True
            if organization_changed:
                try:
                    organization.save()
                    if positive_value_exists(organization_name_changed):
                        from voter_guide.models import VoterGuideManager
                        voter_guide_manager = VoterGuideManager()
                        results = \
                            voter_guide_manager.update_organization_voter_guides_with_organization_data(organization)
                        status += results['status']
                        from organization.controllers import update_position_entered_details_from_organization
                        # TODO This can be made much more efficient
                        position_results = update_position_entered_details_from_organization(organization)
                        status += position_results['status']
                    if positive_value_exists(organization_name_changed) and not not_real_name or \
                            organization.we_vote_hosted_profile_image_url_tiny is not False:
                        from campaign.models import CampaignXManager
                        campaignx_manager = CampaignXManager()
                        owner_results = campaignx_manager.update_campaignx_owners_with_organization_change(
                            organization_we_vote_id=organization.we_vote_id,
                            organization_name=organization.organization_name,
                            we_vote_hosted_profile_image_url_medium=
                            organization.we_vote_hosted_profile_image_url_medium,
                            we_vote_hosted_profile_image_url_tiny=organization.we_vote_hosted_profile_image_url_tiny,
                        )
                        status += owner_results['status']
                        supporter_results = campaignx_manager.update_campaignx_supporters_with_organization_change(
                            organization_we_vote_id=organization.we_vote_id,
                            supporter_name=organization.organization_name,
                            we_vote_hosted_profile_image_url_medium=
                            organization.we_vote_hosted_profile_image_url_medium,
                            we_vote_hosted_profile_image_url_tiny=organization.we_vote_hosted_profile_image_url_tiny,
                        )
                        status += supporter_results['status']
                except Exception as e:
                    status += "COULD_NOT_SAVE_ORGANIZATION: " + str(e) + " "
                    pass
    if voter_name_needs_to_be_updated_in_activity:
        from activity.models import ActivityManager
        activity_manager = ActivityManager()
        results = activity_manager.update_speaker_name_in_bulk(
            speaker_voter_we_vote_id=voter_we_vote_id,
            speaker_name=voter_full_name)
        status += results['status']

    json_data = {
        'status':                                   status,
        'success':                                  success,
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
        'voter_updated':                            voter_updated,
        'interface_status_flags':                   voter.interface_status_flags,
        'flag_integer_to_set':                      flag_integer_to_set,
        'flag_integer_to_unset':                    flag_integer_to_unset,
        'notification_settings_flags':              voter.notification_settings_flags,
        'notification_flag_integer_to_set':         notification_flag_integer_to_set,
        'notification_flag_integer_to_unset':       notification_flag_integer_to_unset,
    }

    response = HttpResponse(json.dumps(json_data), content_type='application/json')
    return response


def voter_notification_settings_update_view(request):  # voterNotificationSettingsUpdate
    """
    Update notification settings for voter based on secret key
    :param request:
    :return:
    """

    status = ""
    voter_found = False
    voter_updated = False
    normalized_email_address = ''
    normalized_sms_phone_number = ''

    # If we have an incoming GET value for a variable, use it. If we don't pass "False" into voter_update_for_api
    # as a signal to not change the variable. (To set variables to False, pass in the string "False".)
    try:
        email_subscription_secret_key = request.GET['email_subscription_secret_key']
        email_subscription_secret_key = email_subscription_secret_key.strip()
    except KeyError:
        email_subscription_secret_key = False

    try:
        sms_subscription_secret_key = request.GET['sms_subscription_secret_key']
        sms_subscription_secret_key = sms_subscription_secret_key.strip()
    except KeyError:
        sms_subscription_secret_key = False

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
        if not positive_value_exists(notification_flag_integer_to_set):
            notification_flag_integer_to_set = False
    except KeyError:
        notification_flag_integer_to_set = False

    try:
        notification_flag_integer_to_unset = request.GET['notification_flag_integer_to_unset']
        notification_flag_integer_to_unset = notification_flag_integer_to_unset.strip()
        notification_flag_integer_to_unset = convert_to_int(notification_flag_integer_to_unset)
        if not positive_value_exists(notification_flag_integer_to_unset):
            notification_flag_integer_to_unset = False

    except KeyError:
        notification_flag_integer_to_unset = False

    at_least_one_variable_has_changed = True if \
        interface_status_flags is not False \
        or flag_integer_to_unset is not False \
        or flag_integer_to_set is not False \
        or notification_settings_flags is not False \
        or notification_flag_integer_to_unset is not False \
        or notification_flag_integer_to_set is not False \
        else False

    email_manager = EmailManager()
    voter_manager = VoterManager()
    voter_id = 0
    voter_interface_status_flags = 0
    voter_notification_settings_flags = 0
    email_address_object_found = False
    if positive_value_exists(email_subscription_secret_key):
        email_results = email_manager.retrieve_email_address_object_from_secret_key(
            subscription_secret_key=email_subscription_secret_key)
        if email_results['email_address_object_found']:
            status += "VOTER_NOTIFICATION_SETTINGS_UPDATE-EMAIL_ADDRESS_FOUND "
            email_address_object = email_results['email_address_object']
            email_address_object_found = True
            normalized_email_address = email_address_object.normalized_email_address
            voter_results = voter_manager.retrieve_voter_by_we_vote_id(email_address_object.voter_we_vote_id)
            voter = voter_results['voter']
            voter_found = True
            voter_id = voter_results['voter_id']
            voter_interface_status_flags = voter.interface_status_flags
            voter_notification_settings_flags = voter.notification_settings_flags
        else:
            status += "EMAIL_ADDRESS_NOT_FOUND "
    elif positive_value_exists(sms_subscription_secret_key):
        # TODO Finish this
        pass
    else:
        status += "SECRET_KEY_NOT_PROVIDED-VOTER_NOTIFICATION_SETTINGS_UPDATE "
        json_data = {
            'status':                           status,
            'success':                          True,
            'email_found':                      email_address_object_found,
            'voter_found':                      voter_found,
            'voter_updated':                    voter_updated,
            'interface_status_flags':           interface_status_flags,
            'flag_integer_to_set':              flag_integer_to_set,
            'flag_integer_to_unset':            flag_integer_to_unset,
            'normalized_email_address':         normalized_email_address,
            'normalized_sms_phone_number':      normalized_sms_phone_number,
            'notification_settings_flags':      notification_settings_flags,
            'notification_flag_integer_to_set': notification_flag_integer_to_set,
            'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    if not positive_value_exists(voter_id):
        if email_address_object_found:
            status += "VOTER_NOT_FOUND_BUT_EMAIL_FOUND_FROM_SECRET_KEY "
        else:
            status += "VOTER_NOT_FOUND_FROM_SECRET_KEY "
        voter_found = False
        json_data = {
            'status':                           status,
            'success':                          True,
            'email_found':                      email_address_object_found,
            'voter_found':                      voter_found,
            'voter_updated':                    voter_updated,
            'interface_status_flags':           interface_status_flags,
            'flag_integer_to_set':              flag_integer_to_set,
            'flag_integer_to_unset':            flag_integer_to_unset,
            'normalized_email_address':         normalized_email_address,
            'normalized_sms_phone_number':      normalized_sms_phone_number,
            'notification_settings_flags':      notification_settings_flags,
            'notification_flag_integer_to_set': notification_flag_integer_to_set,
            'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    # At this point, we have a valid voter

    if at_least_one_variable_has_changed:
        pass
    else:
        # If here, there is nothing to change and we just want to return the latest data from the voter object
        status += "MISSING_VARIABLE-NO_VARIABLES_PASSED_IN_TO_CHANGE "
        json_data = {
                'status':                           status,
                'success':                          True,
                'email_found':                      email_address_object_found,
                'voter_found':                      voter_found,
                'voter_updated':                    voter_updated,
                'interface_status_flags':           voter_interface_status_flags,
                'flag_integer_to_set':              flag_integer_to_set,
                'flag_integer_to_unset':            flag_integer_to_unset,
                'normalized_email_address':         normalized_email_address,
                'normalized_sms_phone_number':      normalized_sms_phone_number,
                'notification_settings_flags':      voter_notification_settings_flags,
                'notification_flag_integer_to_set': notification_flag_integer_to_set,
                'notification_flag_integer_to_unset': notification_flag_integer_to_unset,
            }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    success = True
    voter_manager = VoterManager()
    voter_updated = False
    if at_least_one_variable_has_changed:
        results = voter_manager.update_voter_by_id(
            voter_id,
            interface_status_flags=interface_status_flags,
            flag_integer_to_set=flag_integer_to_set,
            flag_integer_to_unset=flag_integer_to_unset,
            notification_settings_flags=notification_settings_flags,
            notification_flag_integer_to_set=notification_flag_integer_to_set,
            notification_flag_integer_to_unset=notification_flag_integer_to_unset)
        status += results['status']
        success = results['success']
        voter = results['voter']
        voter_found = True
        voter_updated = results['voter_updated']
        voter_interface_status_flags = voter.interface_status_flags
        voter_notification_settings_flags = voter.notification_settings_flags
    json_data = {
        'status':                                   status,
        'success':                                  success,
        'email_found':                              email_address_object_found,
        'voter_found':                              voter_found,
        'voter_updated':                            voter_updated,
        'interface_status_flags':                   voter_interface_status_flags,
        'flag_integer_to_set':                      flag_integer_to_set,
        'flag_integer_to_unset':                    flag_integer_to_unset,
        'normalized_email_address':                 normalized_email_address,
        'normalized_sms_phone_number':              normalized_sms_phone_number,
        'notification_settings_flags':              voter_notification_settings_flags,
        'notification_flag_integer_to_set':         notification_flag_integer_to_set,
        'notification_flag_integer_to_unset':       notification_flag_integer_to_unset,
    }

    response = HttpResponse(json.dumps(json_data), content_type='application/json')
    return response


def voter_verify_secret_code_view(request):  # voterVerifySecretCode
    """
    Compare a time-limited 6 digit secret code against this specific voter_device_id. If correct, sign in the
    voter_device_id.
    :param request:
    :return:
    """
    status = ''
    success = True
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    secret_code = request.GET.get('secret_code', None)
    code_sent_to_sms_phone_number = request.GET.get('code_sent_to_sms_phone_number', None)

    voter_device_link_manager = VoterDeviceLinkManager()
    voter_manager = VoterManager()
    results = voter_device_link_manager.voter_verify_secret_code(
        voter_device_id=voter_device_id, secret_code=secret_code)
    incorrect_secret_code_entered = results['incorrect_secret_code_entered']
    secret_code_verified = results['secret_code_verified']
    number_of_tries_remaining_for_this_code = results['number_of_tries_remaining_for_this_code']
    secret_code_system_locked_for_this_voter_device_id = results['secret_code_system_locked_for_this_voter_device_id']
    voter_must_request_new_code = results['voter_must_request_new_code']

    if not positive_value_exists(secret_code_verified):
        status += results['status']

    voter_found = False
    voter = None
    voter_device_link = None
    if positive_value_exists(secret_code_verified):
        status, voter, voter_found, voter_device_link = views_voter_utils.get_voter_from_request(request, status)
        if not voter_found:
            secret_code_verified = False
            voter_must_request_new_code = True

        if voter_found:
            email_manager = EmailManager()
            sms_manager = SMSManager()
            if positive_value_exists(code_sent_to_sms_phone_number):
                existing_verified_sms_found = False
                new_owner_voter = None
                # Check to see if this sms is already owned by an existing account
                # We get the new sms being verified, so we can find the normalized_sms_phone_number and check to see
                # if that is in use by someone else.
                secret_key_results = sms_manager.retrieve_sms_phone_number_from_secret_key(
                    voter_device_link.sms_secret_key)
                if secret_key_results['sms_phone_number_found']:
                    sms_from_secret_key = secret_key_results['sms_phone_number']

                    matching_results = sms_manager.retrieve_sms_phone_number(
                        sms_from_secret_key.normalized_sms_phone_number)
                    if matching_results['sms_phone_number_found']:
                        sms_phone_number_from_normalized = matching_results['sms_phone_number']
                        if positive_value_exists(sms_phone_number_from_normalized.sms_ownership_is_verified):
                            if positive_value_exists(sms_phone_number_from_normalized.voter_we_vote_id):
                                voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                                    sms_phone_number_from_normalized.voter_we_vote_id)
                                if voter_results['voter_found']:
                                    voter_from_normalized = voter_results['voter']
                                    # If here we know the voter account still exists
                                    if voter_from_normalized.we_vote_id != voter.we_vote_id:
                                        existing_verified_sms_found = True
                                        new_owner_voter = voter_from_normalized
                    elif matching_results['sms_phone_number_list_found']:
                        sms_phone_number_list = matching_results['sms_phone_number_list']
                        for sms_phone_number_from_normalized in sms_phone_number_list:
                            if positive_value_exists(sms_phone_number_from_normalized.sms_ownership_is_verified):
                                if positive_value_exists(sms_phone_number_from_normalized.voter_we_vote_id):
                                    voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                                        sms_phone_number_from_normalized.voter_we_vote_id)
                                    if voter_results['voter_found']:
                                        voter_from_normalized = voter_results['voter']
                                        # If here we know the voter account still exists
                                        if voter_from_normalized.we_vote_id != voter.we_vote_id:
                                            existing_verified_sms_found = True
                                            new_owner_voter = voter_from_normalized
                                            break
                    else:
                        pass

                if existing_verified_sms_found:
                    # Merge existing account with new account
                    merge_results = voter_merge_two_accounts_action(
                        voter, new_owner_voter, voter_device_link, status=status)
                    status += merge_results['status']
                    success = merge_results['success']
                else:
                    # Find and verify the unverified email we are verifying
                    sms_results = sms_manager.verify_sms_phone_number_from_secret_key(
                        voter_device_link.sms_secret_key)
                    if sms_results['sms_phone_number_found']:
                        sms_phone_number = sms_results['sms_phone_number']
                        status += "SMS_FOUND_FROM_VERIFY "
                        try:
                            # Attach the sms_phone_number to the current voter
                            voter_manager.update_voter_sms_ownership_verified(
                                voter, sms_phone_number)
                        except Exception as e:
                            status += "UNABLE_TO_CONNECT_VERIFIED_SMS_WITH_THIS_ACCOUNT " + str(e) + " "
                    else:
                        status += sms_results['status']

                if positive_value_exists(voter_device_link.sms_secret_key):
                    # We remove secret_key's to avoid future collisions in the voter_device_link
                    clear_results = sms_manager.clear_secret_key_from_sms_phone_number(voter_device_link.sms_secret_key)
                    status += clear_results['status']
                    clear_results = voter_device_link_manager.clear_secret_key(
                        sms_secret_key=voter_device_link.sms_secret_key)
                    status += clear_results['status']
            else:
                # Default to code being sent to an email address
                existing_verified_email_address_found = False
                new_owner_voter = None
                email_manager = EmailManager()
                # Check to see if this email_address is already owned by an existing account
                # We get the new email being verified, so we can find the normalized_email_address and check to see
                # if that is in use by someone else.
                secret_key_results = email_manager.retrieve_email_address_object_from_secret_key(
                    voter_device_link.email_secret_key)
                if secret_key_results['email_address_object_found']:
                    email_object_from_secret_key = secret_key_results['email_address_object']

                    matching_results = email_manager.retrieve_email_address_object(
                        email_object_from_secret_key.normalized_email_address)
                    if matching_results['email_address_object_found']:
                        email_address_from_normalized = matching_results['email_address_object']
                        if positive_value_exists(email_address_from_normalized.email_ownership_is_verified):
                            if positive_value_exists(email_address_from_normalized.voter_we_vote_id):
                                voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                                    email_address_from_normalized.voter_we_vote_id)
                                if voter_results['voter_found']:
                                    voter_from_normalized = voter_results['voter']
                                    # If here we know the voter account still exists
                                    if voter_from_normalized.we_vote_id != voter.we_vote_id:
                                        existing_verified_email_address_found = True
                                        new_owner_voter = voter_from_normalized
                    elif matching_results['email_address_list_found']:
                        email_address_list = matching_results['email_address_list']
                        for email_address_from_normalized in email_address_list:
                            if positive_value_exists(email_address_from_normalized.email_ownership_is_verified):
                                if positive_value_exists(email_address_from_normalized.voter_we_vote_id):
                                    voter_results = voter_manager.retrieve_voter_by_we_vote_id(
                                        email_address_from_normalized.voter_we_vote_id)
                                    if voter_results['voter_found']:
                                        voter_from_normalized = voter_results['voter']
                                        # If here we know the voter account still exists
                                        if voter_from_normalized.we_vote_id != voter.we_vote_id:
                                            existing_verified_email_address_found = True
                                            new_owner_voter = voter_from_normalized
                                            break
                    else:
                        pass

                if existing_verified_email_address_found:
                    # Merge existing account with new account
                    merge_results = voter_merge_two_accounts_action(
                        voter, new_owner_voter, voter_device_link, status=status)
                    status += merge_results['status']
                    success = merge_results['success']
                else:
                    # Find and verify the unverified email we are verifying
                    email_results = email_manager.verify_email_address_object_from_secret_key(
                        voter_device_link.email_secret_key)
                    if email_results['email_address_object_found']:
                        email_address_object = email_results['email_address_object']
                        status += "EMAIL_ADDRESS_FOUND_FROM_VERIFY "
                        try:
                            # Attach the email_address_object to the current voter
                            voter_manager.update_voter_email_ownership_verified(
                                voter, email_address_object)
                        except Exception as e:
                            status += "UNABLE_TO_CONNECT_VERIFIED_EMAIL_WITH_THIS_ACCOUNT " + str(e) + " "
                    else:
                        status += email_results['status']

                if positive_value_exists(voter_device_link.email_secret_key):
                    # We remove secret_key's to avoid future collisions in the voter_device_link
                    clear_results = email_manager.clear_secret_key_from_email_address(
                        voter_device_link.email_secret_key)
                    status += clear_results['status']
                    clear_results = voter_device_link_manager.clear_secret_key(
                        email_secret_key=voter_device_link.email_secret_key)
                    status += clear_results['status']

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'incorrect_secret_code_entered':            incorrect_secret_code_entered,
        'number_of_tries_remaining_for_this_code':  number_of_tries_remaining_for_this_code,
        'secret_code_system_locked_for_this_voter_device_id': secret_code_system_locked_for_this_voter_device_id,
        'secret_code_verified':                     secret_code_verified,
        'voter_must_request_new_code':              voter_must_request_new_code,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')

@csrf_exempt
def voter_send_google_contacts_view(request):  # voterSendGoogleContacts
    """
    Receive the voter's google contacts that they allowed the download from the Campaign app
    :param request:
    :return:
    """
    success = True
    status = ''
    status, voter, voter_found, voter_device_link = views_voter_utils.get_voter_from_request(request, status)
    contacts_string = request.POST.get('contacts', None)
    contacts = json.loads(contacts_string)

    j = 0
    if contacts is not None:
        success = True
        for contact in contacts:
            j += 1
            print(str(j) + " " + json.dumps(contact))

    json_data = {
        'status':                                   status,
        'success':                                  success,
        'we_vote_id_for_google_contacts':           voter.we_vote_id,
        'contacts_stored':                          len(contacts),
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')

