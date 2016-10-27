# position/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered, PositionForFriends, PositionManager, PositionListManager, ANY_STANCE, NO_STANCE, \
    FRIENDS_AND_PUBLIC, FRIENDS_ONLY, PUBLIC_ONLY, SHOW_PUBLIC, THIS_ELECTION_ONLY, ALL_OTHER_ELECTIONS, ALL_ELECTIONS
from ballot.models import OFFICE, CANDIDATE, MEASURE
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from election.models import fetch_election_state
from exception.models import handle_record_not_saved_exception
from follow.models import FollowOrganizationManager, FollowOrganizationList
from friend.models import FriendManager
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from organization.models import Organization, OrganizationManager
import json
import requests
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
from voter_guide.models import ORGANIZATION, PUBLIC_FIGURE, VOTER, UNKNOWN_VOTER_GUIDE
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
POSITIONS_SYNC_URL = get_environment_variable("POSITIONS_SYNC_URL")


def find_organizations_referenced_in_positions_for_this_voter(voter):
    related_organizations = []

    position_filters = []
    final_position_filters = []
    if positive_value_exists(voter.we_vote_id):
        new_position_filter = Q(voter_we_vote_id__iexact=voter.we_vote_id)
        position_filters.append(new_position_filter)
    if positive_value_exists(voter.id):
        new_position_filter = Q(voter_id=voter.id)
        position_filters.append(new_position_filter)
    if positive_value_exists(voter.linked_organization_we_vote_id):
        new_position_filter = Q(organization_we_vote_id=voter.linked_organization_we_vote_id)
        position_filters.append(new_position_filter)

    if len(position_filters):
        final_position_filters = position_filters.pop()

        # ...and "OR" the remaining items in the list
        for item in position_filters:
            final_position_filters |= item

    organization_filters = []
    organization_ids_found = []
    organization_we_vote_ids_found = []

    # PositionEntered
    position_list_query = PositionEntered.objects.all()
    position_list_query = position_list_query.filter(final_position_filters)

    for one_position in position_list_query:
        # Find organization(s) linked in one_position
        if positive_value_exists(one_position.organization_id) and \
                one_position.organization_id not in organization_ids_found:
            organization_ids_found.append(one_position.organization_id)
            new_organization_filter = Q(id=one_position.organization_id)
            organization_filters.append(new_organization_filter)
        if positive_value_exists(one_position.organization_we_vote_id) and \
                one_position.organization_we_vote_id not in organization_we_vote_ids_found:
            organization_we_vote_ids_found.append(one_position.organization_we_vote_id)
            new_organization_filter = Q(we_vote_id__iexact=one_position.organization_we_vote_id)
            organization_filters.append(new_organization_filter)

    # PositionForFriends
    position_list_query = PositionForFriends.objects.all()
    position_list_query = position_list_query.filter(final_position_filters)

    for one_position in position_list_query:
        # Find organization(s) linked in one_position
        if positive_value_exists(one_position.organization_id) and \
                one_position.organization_id not in organization_ids_found:
            organization_ids_found.append(one_position.organization_id)
            new_organization_filter = Q(id=one_position.organization_id)
            organization_filters.append(new_organization_filter)
        if positive_value_exists(one_position.organization_we_vote_id) and \
                one_position.organization_we_vote_id not in organization_we_vote_ids_found:
            organization_we_vote_ids_found.append(one_position.organization_we_vote_id)
            new_organization_filter = Q(we_vote_id__iexact=one_position.organization_we_vote_id)
            organization_filters.append(new_organization_filter)

    # Now that we have a list of all possible organization_id or organization_we_vote_id entries, retrieve all
    if len(organization_filters):
        final_organization_filters = organization_filters.pop()

        # ...and "OR" the remaining items in the list
        for item in organization_filters:
            final_organization_filters |= item

        # Finally, retrieve all of the organizations from any of these positions
        organization_list_query = Organization.objects.all()
        organization_list_query = organization_list_query.filter(final_organization_filters)

        for organization in organization_list_query:
            related_organizations.append(organization)

    return related_organizations


def move_positions_to_another_voter(from_voter_id, from_voter_we_vote_id,
                                    to_voter_id, to_voter_we_vote_id,
                                    to_voter_linked_organization_id, to_voter_linked_organization_we_vote_id):
    status = ''
    success = False
    position_entries_moved = 0
    position_entries_not_moved = 0
    position_manager = PositionManager()
    position_list_manager = PositionListManager()

    # Find private positions for the "from_voter" that we are moving away from
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = FRIENDS_ONLY
    from_position_private_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_private_list = from_position_private_results['position_list']

    for from_position_entry in from_position_private_list:
        # See if the "to_voter" already has the same entry
        position_we_vote_id = ""
        results = position_manager.retrieve_position_table_unknown(
            position_we_vote_id, from_position_entry.organization_id, from_position_entry.organization_we_vote_id,
            to_voter_id,
            from_position_entry.contest_office_id, from_position_entry.candidate_campaign_id,
            from_position_entry.contest_measure_id,
            from_position_entry.voter_we_vote_id, from_position_entry.contest_office_we_vote_id,
            from_position_entry.candidate_campaign_we_vote_id, from_position_entry.contest_measure_we_vote_id)

        if results['position_found']:
            # Look to see if there is a statement that can be preserved (i.e., moved from from_position to to_position
            save_to_position = False
            to_position_entry = results['position']
            if not positive_value_exists(to_position_entry.statement_html):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_html):
                    to_position_entry.statement_html = from_position_entry.statement_html
                    save_to_position = True
            if not positive_value_exists(to_position_entry.statement_text):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_text):
                    to_position_entry.statement_text = from_position_entry.statement_text
                    save_to_position = True
            # There might be a case where the to_voter didn't have a linked_organization_we_vote_id, but
            # the from_voter does, so we want to make sure to update that
            if not positive_value_exists(to_position_entry.organization_we_vote_id):
                to_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
                save_to_position = True
            if not positive_value_exists(to_position_entry.organization_id):
                to_position_entry.organization_id = to_voter_linked_organization_id
                save_to_position = True
            if save_to_position:
                try:
                    to_position_entry.save()
                except Exception as e:
                    pass
        else:
            # Change the position values to the new we_vote_id
            try:
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                from_position_entry.organization_id = to_voter_linked_organization_id
                from_position_entry.organization_we_vote_id = to_voter_linked_organization_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.save()
                position_entries_moved += 1
            except Exception as e:
                position_entries_not_moved += 1

    from_position_private_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_private_list_remaining = from_position_private_results['position_list']
    for from_position_entry in from_position_private_list_remaining:
        # Delete the remaining position values
        try:
            # Leave this turned off until testing is finished
            # from_position_entry.delete()
            pass
        except Exception as e:
            pass

    # Find public positions for the "from_voter" that we are moving away from
    stance_we_are_looking_for = ANY_STANCE
    friends_vs_public = PUBLIC_ONLY
    from_position_public_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_public_list = from_position_public_results['position_list']

    for from_position_entry in from_position_public_list:
        # See if the "to_voter" already has the same entry
        position_we_vote_id = ""
        results = position_manager.retrieve_position_table_unknown(
            position_we_vote_id, from_position_entry.organization_id, from_position_entry.organization_we_vote_id,
            to_voter_id,
            from_position_entry.contest_office_id, from_position_entry.candidate_campaign_id,
            from_position_entry.contest_measure_id,
            from_position_entry.voter_we_vote_id, from_position_entry.contest_office_we_vote_id,
            from_position_entry.candidate_campaign_we_vote_id, from_position_entry.contest_measure_we_vote_id)

        if results['position_found']:
            # Look to see if there is a statement that can be preserved
            save_to_position = False
            to_position_entry = results['position']
            if not positive_value_exists(to_position_entry.statement_html):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_html):
                    to_position_entry.statement_html = from_position_entry.statement_html
                    save_to_position = True
            if not positive_value_exists(to_position_entry.statement_text):
                # If the "to_position" does NOT have a statement_html, we look to see if the "from_position" has one
                # we can use
                if positive_value_exists(from_position_entry.statement_text):
                    to_position_entry.statement_text = from_position_entry.statement_text
                    save_to_position = True
            if save_to_position:
                try:
                    to_position_entry.save()
                except Exception as e:
                    pass
        else:
            # Change the position values to the new we_vote_id
            try:
                from_position_entry.voter_we_vote_id = to_voter_we_vote_id
                from_position_entry.voter_id = to_voter_id
                from_position_entry.save()
                position_entries_moved += 1
            except Exception as e:
                position_entries_not_moved += 1

    from_position_public_results = position_list_manager.retrieve_all_positions_for_voter(
        from_voter_id, from_voter_we_vote_id,
        stance_we_are_looking_for, friends_vs_public)
    from_position_public_list_remaining = from_position_public_results['position_list']
    for from_position_entry in from_position_public_list_remaining:
        # Delete the remaining position values
        try:
            # Leave this turned off until testing is finished
            # from_position_entry.delete()
            pass
        except Exception as e:
            pass

    results = {
        'status': status,
        'success': success,
        'from_voter_id': from_voter_id,
        'from_voter_we_vote_id': from_voter_we_vote_id,
        'to_voter_id': to_voter_id,
        'to_voter_we_vote_id': to_voter_we_vote_id,
        'position_entries_moved': position_entries_moved,
        'position_entries_not_moved': position_entries_not_moved,
    }
    return results


# We retrieve from only one of the two possible variables
def position_retrieve_for_api(position_we_vote_id, voter_device_id):  # positionRetrieve
    position_we_vote_id = position_we_vote_id.strip().lower()

    # TODO for certain positions (voter positions), we need to restrict the retrieve based on voter_device_id / voter_id
    if voter_device_id:
        pass

    we_vote_id = position_we_vote_id.strip().lower()
    if not positive_value_exists(position_we_vote_id):
        json_data = {
            'status':                   "POSITION_RETRIEVE_BOTH_IDS_MISSING",
            'success':                  False,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':              False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'vote_smart_rating':        '',
            'vote_smart_time_span':     '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()
    organization_id = 0
    organization_we_vote_id = ''
    contest_office_id = 0
    candidate_campaign_id = 0
    contest_measure_id = 0
    position_voter_id = 0
    results = position_manager.retrieve_position_table_unknown(
        position_we_vote_id, organization_id, organization_we_vote_id, position_voter_id,
        contest_office_id, candidate_campaign_id, contest_measure_id)

    if results['position_found']:
        position = results['position']
        json_data = {
            'success':                  True,
            'status':                   results['status'],
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'is_support':                       results['is_support'],
            'is_positive_rating':               results['is_positive_rating'],
            'is_support_or_positive_rating':    results['is_support_or_positive_rating'],
            'is_oppose':                        results['is_oppose'],
            'is_negative_rating':               results['is_negative_rating'],
            'is_oppose_or_negative_rating':     results['is_oppose_or_negative_rating'],
            'is_information_only':      results['is_information_only'],
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'vote_smart_rating':        position.vote_smart_rating,
            'vote_smart_time_span':     position.vote_smart_time_span,
            'last_updated':             position.last_updated(),
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   results['status'],
            'success':                  results['success'],
            'position_we_vote_id':      we_vote_id,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'organization_we_vote_id':  '',
            'google_civic_election_id': '',
            'voter_id':                 0,
            'office_we_vote_id':        '',
            'candidate_we_vote_id':     '',
            'measure_we_vote_id':       '',
            'stance':                   NO_STANCE,
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'vote_smart_rating':        '',
            'vote_smart_time_span':     '',
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_save_for_api(  # positionSave
        voter_device_id, position_we_vote_id,
        organization_we_vote_id,
        public_figure_we_vote_id,
        voter_we_vote_id,
        google_civic_election_id,
        ballot_item_display_name,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        stance,
        set_as_public_position,
        statement_text,
        statement_html,
        more_info_url
        ):
    position_we_vote_id = position_we_vote_id.strip().lower()

    existing_unique_identifier_found = positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(organization_we_vote_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    if not unique_identifier_found:
        results = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'is_public_position':       False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               '',
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': ballot_item_display_name,
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'is_public_position':       False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               '',
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results

    # Look up the state_code from the election
    state_code = fetch_election_state(google_civic_election_id)

    position_manager = PositionManager()
    save_results = position_manager.update_or_create_position(
        position_we_vote_id=position_we_vote_id,
        organization_we_vote_id=organization_we_vote_id,
        public_figure_we_vote_id=public_figure_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        state_code=state_code,
        ballot_item_display_name=ballot_item_display_name,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        stance=stance,
        set_as_public_position=set_as_public_position,
        statement_text=statement_text,
        statement_html=statement_html,
        more_info_url=more_info_url,
    )

    if save_results['success']:
        position = save_results['position']
        results = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position.we_vote_id,
            'new_position_created':     save_results['new_position_created'],
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'is_support':                       position.is_support(),
            'is_positive_rating':               position.is_positive_rating(),
            'is_support_or_positive_rating':    position.is_support_or_positive_rating(),
            'is_oppose':                        position.is_oppose(),
            'is_negative_rating':               position.is_negative_rating(),
            'is_oppose_or_negative_rating':     position.is_oppose_or_negative_rating(),
            'is_information_only':      position.is_information_only(),
            'is_public_position':       position.is_public_position,
            'organization_we_vote_id':  position.organization_we_vote_id,
            'google_civic_election_id': position.google_civic_election_id,
            'state_code':               position.state_code,
            'voter_id':                 position.voter_id,
            'office_we_vote_id':        '',  # position.office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'new_position_created':     False,
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':                       False,
            'is_positive_rating':               False,
            'is_support_or_positive_rating':    False,
            'is_oppose':                        False,
            'is_negative_rating':               False,
            'is_oppose_or_negative_rating':     False,
            'is_information_only':      False,
            'is_public_position':       False,
            'organization_we_vote_id':  organization_we_vote_id,
            'google_civic_election_id': google_civic_election_id,
            'voter_id':                 0,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'stance':                   stance,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'more_info_url':            more_info_url,
            'last_updated':             '',
        }
        return results


def position_list_for_ballot_item_for_api(voter_device_id, friends_vs_public,  # positionListForBallotItem
                                          office_id, office_we_vote_id,
                                          candidate_id, candidate_we_vote_id,
                                          measure_id, measure_we_vote_id,
                                          stance_we_are_looking_for=ANY_STANCE,
                                          show_positions_this_voter_follows=True):
    """
    We want to return a JSON file with the position identifiers from orgs, friends and public figures the voter follows
    This list of information is used to retrieve the detailed information
    """
    status = ""
    success = False

    position_manager = PositionManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':               'VALID_VOTER_DEVICE_ID_MISSING',
            'success':              False,
            'count':                0,
            'kind_of_ballot_item':  "UNKNOWN",
            'ballot_item_id':       0,
            'position_list':        position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        voter_id = voter.id
        voter_we_vote_id = voter.we_vote_id
    else:
        voter_id = 0
        voter_we_vote_id = ""
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':               "VALID_VOTER_ID_MISSING ",
            'success':              False,
            'count':                0,
            'kind_of_ballot_item':  "UNKNOWN",
            'ballot_item_id':       0,
            'position_list':        position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # If we are looking for positions that the voter is following, we can also show friend's opinions
    # If show_positions_this_voter_follows = False, then we are looking for positions we can follow
    retrieve_friends_positions = friends_vs_public in (FRIENDS_ONLY, FRIENDS_AND_PUBLIC) \
        and show_positions_this_voter_follows
    retrieve_public_positions = friends_vs_public in (PUBLIC_ONLY, FRIENDS_AND_PUBLIC)

    friends_we_vote_id_list = []
    if positive_value_exists(voter_we_vote_id):
        friend_manager = FriendManager()
        friend_results = friend_manager.retrieve_friends_we_vote_id_list(voter_we_vote_id)
        if friend_results['friends_we_vote_id_list_found']:
            friends_we_vote_id_list = friend_results['friends_we_vote_id_list']

    # Add yourself as a friend so your opinions show up
    friends_we_vote_id_list.append(voter_we_vote_id)

    position_list_manager = PositionListManager()
    ballot_item_found = False
    friends_positions_list = []
    if positive_value_exists(candidate_id) or positive_value_exists(candidate_we_vote_id):
        kind_of_ballot_item = CANDIDATE

        ############################
        # Retrieve public positions
        if retrieve_public_positions:
            retrieve_public_positions_now = True  # The alternate is positions for friends-only
            return_only_latest_position_per_speaker = True
            public_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                retrieve_public_positions_now, candidate_id, candidate_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker)
            is_public_position_setting = True
            public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
                                                                                 is_public_position_setting)
        else:
            public_positions_list = []

        ##################################
        # Now retrieve friend's positions
        if retrieve_friends_positions:
            retrieve_public_positions_now = False  # This being False means: "Positions from friends-only"
            return_only_latest_position_per_speaker = True
            friends_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                retrieve_public_positions_now, candidate_id, candidate_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker, friends_we_vote_id_list)
            # Now add is_public_position to each value
            is_public_position_setting = False
            friends_positions_list = position_list_manager.add_is_public_position(friends_positions_list,
                                                                                  is_public_position_setting)
        else:
            friends_positions_list = []

        # Since we want to return the id and we_vote_id for this ballot item, and we don't know for sure that
        # there are any positions for this ballot_item (which would include both the id and we_vote_id),
        # we retrieve the following so we can get the ballot item's id and we_vote_id (per the request of
        # the WebApp team)
        candidate_campaign_manager = CandidateCampaignManager()
        if positive_value_exists(candidate_id):
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
        else:
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)

        if results['candidate_campaign_found']:
            candidate_campaign = results['candidate_campaign']
            ballot_item_id = candidate_campaign.id
            ballot_item_we_vote_id = candidate_campaign.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = candidate_id
            ballot_item_we_vote_id = candidate_we_vote_id
    elif positive_value_exists(measure_id) or positive_value_exists(measure_we_vote_id):
        kind_of_ballot_item = MEASURE

        ############################
        # Retrieve public positions
        if retrieve_public_positions:
            retrieve_public_positions_now = True  # The alternate is positions for friends-only
            return_only_latest_position_per_speaker = True
            public_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
                retrieve_public_positions_now,
                measure_id, measure_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker)
            is_public_position_setting = True
            public_positions_list = position_list_manager.add_is_public_position(public_positions_list,
                                                                                 is_public_position_setting)
        else:
            public_positions_list = []

        ##################################
        # Now retrieve friend's positions
        if retrieve_friends_positions:
            retrieve_public_positions_now = False  # This being False means: "Positions from friends-only"
            return_only_latest_position_per_speaker = True
            friends_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
                retrieve_public_positions_now,
                measure_id, measure_we_vote_id, stance_we_are_looking_for,
                return_only_latest_position_per_speaker, friends_we_vote_id_list)
            is_public_position_setting = False
            friends_positions_list = position_list_manager.add_is_public_position(friends_positions_list,
                                                                                  is_public_position_setting)
        else:
            friends_positions_list = []

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this ballot_item, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        contest_measure_manager = ContestMeasureManager()
        if positive_value_exists(measure_id):
            results = contest_measure_manager.retrieve_contest_measure_from_id(measure_id)
        else:
            results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)

        if results['contest_measure_found']:
            contest_measure = results['contest_measure']
            ballot_item_id = contest_measure.id
            ballot_item_we_vote_id = contest_measure.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = measure_id
            ballot_item_we_vote_id = measure_we_vote_id
    elif positive_value_exists(office_id) or positive_value_exists(office_we_vote_id):
        public_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
                office_id, office_we_vote_id, stance_we_are_looking_for)
        kind_of_ballot_item = OFFICE

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this ballot_item, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        contest_office_manager = ContestOfficeManager()
        if positive_value_exists(office_id):
            results = contest_office_manager.retrieve_contest_office_from_id(office_id)
        else:
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)

        if results['contest_office_found']:
            contest_office = results['contest_office']
            ballot_item_id = contest_office.id
            ballot_item_we_vote_id = contest_office.we_vote_id
            ballot_item_found = True
        else:
            ballot_item_id = office_id
            ballot_item_we_vote_id = office_we_vote_id
    else:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not ballot_item_found:
        position_list = []
        json_data = {
            'status':                   'POSITION_LIST_RETRIEVE_BALLOT_ITEM_NOT_FOUND',
            'success':                  False,
            'count':                    0,
            'kind_of_ballot_item':      "UNKNOWN",
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if len(public_positions_list):
        follow_organization_list_manager = FollowOrganizationList()
        organizations_followed_by_voter = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

        if show_positions_this_voter_follows:
            position_objects = position_list_manager.calculate_positions_followed_by_voter(
                voter_id, public_positions_list, organizations_followed_by_voter)
            status = 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_FOLLOWED'
            success = True
        else:
            position_objects = position_list_manager.calculate_positions_not_followed_by_voter(
                public_positions_list, organizations_followed_by_voter)
            status = 'SUCCESSFUL_RETRIEVE_OF_POSITIONS_NOT_FOLLOWED'
            success = True
    else:
        position_objects = []

    if len(friends_positions_list):
        position_objects = friends_positions_list + position_objects

    positions_count = len(position_objects)

    # We need the linked_organization_we_vote_id so we can remove the viewer's positions from the list.
    linked_organization_we_vote_id = ""
    if positive_value_exists(positions_count):
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter = results['voter']
            linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    position_list = []
    for one_position in position_objects:
        # Is there sufficient information in the position to display it?
        some_data_exists = True if one_position.is_support() \
                           or one_position.is_oppose() \
                           or one_position.is_information_only() \
                           or positive_value_exists(one_position.vote_smart_rating) \
                           or positive_value_exists(one_position.statement_text) \
                           or positive_value_exists(one_position.more_info_url) else False
        if not some_data_exists:
            # Skip this position if there isn't any data to display
            continue

        # Whose position is it?
        if positive_value_exists(one_position.organization_we_vote_id):
            if linked_organization_we_vote_id == one_position.organization_we_vote_id:
                # Do not show your own position on the position list, since it will be in the edit spot already
                continue
            speaker_type = ORGANIZATION
            speaker_id = one_position.organization_id
            speaker_we_vote_id = one_position.organization_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or not positive_value_exists(one_position.speaker_twitter_handle):
                one_position = position_manager.refresh_cached_position_info(one_position)
            speaker_display_name = one_position.speaker_display_name
        elif positive_value_exists(one_position.voter_id):
            if voter_id == one_position.voter_id:
                # Do not show your own position on the position list, since it will be in the edit spot already
                continue
            speaker_type = VOTER
            speaker_id = one_position.voter_id
            speaker_we_vote_id = one_position.voter_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.voter_we_vote_id) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or not positive_value_exists(one_position.speaker_twitter_handle):
                one_position = position_manager.refresh_cached_position_info(one_position)
            if positive_value_exists(one_position.speaker_display_name):
                speaker_display_name = one_position.speaker_display_name
            else:
                speaker_display_name = "Your Friend (Missing Name)"
        elif positive_value_exists(one_position.public_figure_we_vote_id):
            speaker_type = PUBLIC_FIGURE
            speaker_id = one_position.public_figure_id
            speaker_we_vote_id = one_position.public_figure_we_vote_id
            one_position_success = True
            # Make sure we have this data to display
            if not positive_value_exists(one_position.speaker_display_name) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or not positive_value_exists(one_position.speaker_twitter_handle):
                one_position = position_manager.refresh_cached_position_info(one_position)
            speaker_display_name = one_position.speaker_display_name
        else:
            speaker_type = UNKNOWN_VOTER_GUIDE
            speaker_display_name = "Unknown"
            speaker_id = None
            speaker_we_vote_id = None
            one_position_success = False

        if one_position_success:
            one_position_dict_for_api = {
                'position_we_vote_id':              one_position.we_vote_id,
                'ballot_item_display_name':         one_position.ballot_item_display_name,
                'speaker_display_name':             speaker_display_name,
                'speaker_image_url_https':          one_position.speaker_image_url_https,
                'speaker_twitter_handle':           one_position.speaker_twitter_handle,
                'speaker_type':                     speaker_type,
                'speaker_id':                       speaker_id,
                'speaker_we_vote_id':               speaker_we_vote_id,
                'is_support':                       one_position.is_support(),
                'is_positive_rating':               one_position.is_positive_rating(),
                'is_support_or_positive_rating':    one_position.is_support_or_positive_rating(),
                'is_oppose':                        one_position.is_oppose(),
                'is_negative_rating':               one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':     one_position.is_oppose_or_negative_rating(),
                'is_information_only':              one_position.is_information_only(),
                'is_public_position':               one_position.is_public_position,
                'vote_smart_rating':                one_position.vote_smart_rating,
                'vote_smart_time_span':             one_position.vote_smart_time_span,
                'statement_text':                   one_position.statement_text,
                'more_info_url':                    one_position.more_info_url,
                'last_updated':                     one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    json_data = {
        'status':                   status,
        'success':                  success,
        'count':                    positions_count,
        'kind_of_ballot_item':      kind_of_ballot_item,
        'ballot_item_id':           ballot_item_id,
        'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        'position_list':            position_list,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_list_for_opinion_maker_for_api(voter_device_id,  # positionListForOpinionMaker
                                            organization_id, organization_we_vote_id,
                                            public_figure_id, public_figure_we_vote_id,
                                            friends_vs_public=FRIENDS_AND_PUBLIC,
                                            stance_we_are_looking_for=ANY_STANCE,
                                            filter_for_voter=False,
                                            filter_out_voter=False,
                                            google_civic_election_id=0,
                                            state_code=''):
    """
    We want to return a JSON file with a list of positions held by orgs, and friends public figures.
    We can limit the positions to friend's only if needed.
    """
    is_following = False
    is_ignoring = False
    opinion_maker_display_name = ''
    opinion_maker_image_url_https = ''
    status = ''
    position_list_raw = []

    # Convert incoming variables to "opinion_maker"
    if positive_value_exists(organization_id) or positive_value_exists(organization_we_vote_id):
        kind_of_opinion_maker = ORGANIZATION
        kind_of_opinion_maker_text = "ORGANIZATION"  # For returning a value via the API
        opinion_maker_id = organization_id
        opinion_maker_we_vote_id = organization_we_vote_id
    elif positive_value_exists(public_figure_id) or positive_value_exists(public_figure_we_vote_id):
        kind_of_opinion_maker = PUBLIC_FIGURE
        kind_of_opinion_maker_text = "PUBLIC_FIGURE"
        opinion_maker_id = public_figure_id
        opinion_maker_we_vote_id = public_figure_we_vote_id
    else:
        kind_of_opinion_maker = UNKNOWN_VOTER_GUIDE
        kind_of_opinion_maker_text = "UNKNOWN_VOTER_GUIDE"
        opinion_maker_id = 0
        opinion_maker_we_vote_id = ''

    position_manager = PositionManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':                           'VALID_VOTER_DEVICE_ID_MISSING_OPINION_MAKER_POSITION_LIST',
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
            'filter_for_voter':                 filter_for_voter,
            'filter_out_voter':                 filter_out_voter,
            'friends_vs_public':                friends_vs_public,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':                           "VALID_VOTER_ID_MISSING_OPINION_MAKER_POSITION_LIST ",
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
            'filter_for_voter':                 filter_for_voter,
            'filter_out_voter':                 filter_out_voter,
            'friends_vs_public':                friends_vs_public,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list_manager = PositionListManager()
    opinion_maker_found = False
    if kind_of_opinion_maker == ORGANIZATION:
        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this opinion_maker, we retrieve the following so we can get the id and we_vote_id (per the request of
        # the WebApp team)
        organization_manager = OrganizationManager()
        if positive_value_exists(organization_id):
            results = organization_manager.retrieve_organization_from_id(organization_id)
        else:
            results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)

        if results['organization_found']:
            organization = results['organization']
            opinion_maker_id = organization.id
            opinion_maker_we_vote_id = organization.we_vote_id
            opinion_maker_display_name = organization.organization_name
            opinion_maker_image_url_https = organization.organization_photo_url()
            opinion_maker_found = True

            follow_organization_manager = FollowOrganizationManager()
            voter_we_vote_id = ''
            following_results = follow_organization_manager.retrieve_voter_following_org_status(
                voter_id, voter_we_vote_id, opinion_maker_id, opinion_maker_we_vote_id)
            if following_results['is_following']:
                is_following = True
            elif following_results['is_ignoring']:
                is_ignoring = True

            position_list_raw = position_list_manager.retrieve_all_positions_for_organization(
                    organization_id, organization_we_vote_id, stance_we_are_looking_for, friends_vs_public,
                    filter_for_voter, filter_out_voter, voter_device_id, google_civic_election_id, state_code)
        else:
            opinion_maker_id = organization_id
            opinion_maker_we_vote_id = organization_we_vote_id
    elif kind_of_opinion_maker == PUBLIC_FIGURE:
        position_list_raw = position_list_manager.retrieve_all_positions_for_public_figure(
                public_figure_id, public_figure_we_vote_id, stance_we_are_looking_for,
                filter_for_voter, filter_out_voter, voter_device_id, google_civic_election_id, state_code)

        # Since we want to return the id and we_vote_id, and we don't know for sure that there are any positions
        # for this opinion_maker, we retrieve the following so we can have the id and we_vote_id (per the request of
        # the WebApp team)
        # TODO Do we want to give public figures an entry separate from their voter account? Needs to be implemented.
        # candidate_campaign_manager = CandidateCampaignManager()
        # if positive_value_exists(candidate_id):
        #     results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
        # else:
        #     results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
        #
        # if results['candidate_campaign_found']:
        #     candidate_campaign = results['candidate_campaign']
        #     ballot_item_id = candidate_campaign.id
        #     ballot_item_we_vote_id = candidate_campaign.we_vote_id
        #     opinion_maker_found = True
        # else:
        #     ballot_item_id = candidate_id
        #     ballot_item_we_vote_id = candidate_we_vote_id
    else:
        position_list = []
        json_data = {
            'status':                           'POSITION_LIST_RETRIEVE_MISSING_OPINION_MAKER_ID',
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
            'filter_for_voter':                 filter_for_voter,
            'filter_out_voter':                 filter_out_voter,
            'friends_vs_public':                friends_vs_public,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not opinion_maker_found:
        position_list = []
        json_data = {
            'status':                           'POSITION_LIST_RETRIEVE_OPINION_MAKER_NOT_FOUND',
            'success':                          False,
            'count':                            0,
            'kind_of_opinion_maker':            kind_of_opinion_maker_text,
            'opinion_maker_id':                 opinion_maker_id,
            'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
            'opinion_maker_display_name':       opinion_maker_display_name,
            'opinion_maker_image_url_https':    opinion_maker_image_url_https,
            'is_following':                     is_following,
            'is_ignoring':                      is_ignoring,
            'google_civic_election_id':         google_civic_election_id,
            'state_code':                       state_code,
            'position_list':                    position_list,
            'filter_for_voter':                 filter_for_voter,
            'filter_out_voter':                 filter_out_voter,
            'friends_vs_public':                friends_vs_public,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list = []
    for one_position in position_list_raw:
        # Whose position is it?
        missing_ballot_item_image = False
        missing_office_information = False
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = one_position.candidate_campaign_id
            ballot_item_we_vote_id = one_position.candidate_campaign_we_vote_id
            if not positive_value_exists(one_position.contest_office_we_vote_id) \
                    or not positive_value_exists(one_position.contest_office_name):
                missing_office_information = True
            if not positive_value_exists(one_position.ballot_item_image_url_https):
                missing_ballot_item_image = True
            one_position_success = True
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = one_position.contest_measure_id
            ballot_item_we_vote_id = one_position.contest_measure_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.contest_office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = one_position.contest_office_id
            ballot_item_we_vote_id = one_position.contest_office_we_vote_id
            one_position_success = True
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None
            one_position_success = False

        if one_position_success:
            # Make sure we have this data to display. If we don't, refresh PositionEntered table from other tables.
            if not positive_value_exists(one_position.ballot_item_display_name) \
                    or not positive_value_exists(one_position.state_code) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or missing_ballot_item_image \
                    or missing_office_information:
                one_position = position_manager.refresh_cached_position_info(one_position)
            one_position_dict_for_api = {
                'position_we_vote_id':          one_position.we_vote_id,
                'ballot_item_display_name':     one_position.ballot_item_display_name,  # Candidate name or Measure
                'ballot_item_image_url_https':  one_position.ballot_item_image_url_https,
                'ballot_item_twitter_handle':   one_position.ballot_item_twitter_handle,
                'ballot_item_political_party':  one_position.political_party,
                'kind_of_ballot_item':          kind_of_ballot_item,
                'ballot_item_id':               ballot_item_id,
                'ballot_item_we_vote_id':       ballot_item_we_vote_id,
                'ballot_item_state_code':       one_position.state_code,
                'contest_office_id':            one_position.contest_office_id,
                'contest_office_we_vote_id':    one_position.contest_office_we_vote_id,
                'contest_office_name':          one_position.contest_office_name,
                'is_support':                       one_position.is_support(),
                'is_positive_rating':               one_position.is_positive_rating(),
                'is_support_or_positive_rating':    one_position.is_support_or_positive_rating(),
                'is_oppose':                        one_position.is_oppose(),
                'is_negative_rating':               one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':     one_position.is_oppose_or_negative_rating(),
                'is_information_only':              one_position.is_information_only(),
                'is_public_position':           one_position.is_public_position,
                'speaker_display_name':         one_position.speaker_display_name,  # Organization name
                'vote_smart_rating':            one_position.vote_smart_rating,
                'vote_smart_time_span':         one_position.vote_smart_time_span,
                'google_civic_election_id':     one_position.google_civic_election_id,
                'more_info_url':                one_position.more_info_url,
                'statement_text':               one_position.statement_text,
                'last_updated':                 one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    # Now change the sort order

    status += ' POSITION_LIST_FOR_OPINION_MAKER_SUCCEEDED'
    success = True
    json_data = {
        'status':                           status,
        'success':                          success,
        'count':                            len(position_list),
        'kind_of_opinion_maker':            kind_of_opinion_maker_text,
        'opinion_maker_id':                 opinion_maker_id,
        'opinion_maker_we_vote_id':         opinion_maker_we_vote_id,
        'opinion_maker_display_name':       opinion_maker_display_name,
        'opinion_maker_image_url_https':    opinion_maker_image_url_https,
        'is_following':                     is_following,
        'is_ignoring':                      is_ignoring,
        'google_civic_election_id':         google_civic_election_id,
        'state_code':                       state_code,
        'position_list':                    position_list,
        'filter_for_voter':                 filter_for_voter,
        'filter_out_voter':                 filter_out_voter,
        'friends_vs_public':                friends_vs_public,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def position_list_for_voter_for_api(voter_device_id,
                                    friends_vs_public=FRIENDS_AND_PUBLIC,
                                    stance_we_are_looking_for=ANY_STANCE,
                                    show_only_this_election=False,
                                    show_all_other_elections=False,
                                    google_civic_election_id=0,
                                    state_code=''):  # positionListForVoter
    """
    We want to return a JSON file with a list of positions held by this voter.
    We can limit the positions to friend's only if needed.
    """
    voter_we_vote_id = ""
    voter_display_name = ''
    voter_image_url_https = ''
    status = ''
    position_list_raw = []

    position_manager = PositionManager()
    # Get voter_id from the voter_device_id so we can know who is supporting/opposing
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        position_list = []
        json_data = {
            'status':                           'VALID_VOTER_DEVICE_ID_MISSING_VOTER_POSITION_LIST',
            'success':                          False,
            'count':                            0,
            'friends_vs_public':                friends_vs_public,
            'google_civic_election_id':         google_civic_election_id,
            'position_list':                    position_list,
            'show_all_other_elections':         show_all_other_elections,
            'show_only_this_election':          show_only_this_election,
            'state_code':                       state_code,
            'voter_we_vote_id':                 voter_we_vote_id,
            'voter_display_name':               voter_display_name,
            'voter_image_url_https':            voter_image_url_https,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        position_list = []
        json_data = {
            'status':                           "VALID_VOTER_ID_MISSING_VOTER_POSITION_LIST ",
            'success':                          False,
            'count':                            0,
            'friends_vs_public':                friends_vs_public,
            'google_civic_election_id':         google_civic_election_id,
            'position_list':                    position_list,
            'show_all_other_elections':         show_all_other_elections,
            'show_only_this_election':          show_only_this_election,
            'state_code':                       state_code,
            'voter_we_vote_id':                 voter_we_vote_id,
            'voter_display_name':               voter_display_name,
            'voter_image_url_https':            voter_image_url_https,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter = voter_results['voter']
    position_list_manager = PositionListManager()
    if show_only_this_election:
        this_election_vs_others = THIS_ELECTION_ONLY
    elif show_all_other_elections:
        this_election_vs_others = ALL_OTHER_ELECTIONS
    else:
        this_election_vs_others = ALL_ELECTIONS

    position_list_results = position_list_manager.retrieve_all_positions_for_voter(
        voter.id, voter.we_vote_id, stance_we_are_looking_for, friends_vs_public, google_civic_election_id,
        this_election_vs_others, state_code)
    if position_list_results['position_list_found']:
        position_list_retrieved = position_list_results['position_list']
    else:
        position_list_retrieved = []

    position_list = []
    for one_position in position_list_retrieved:
        # Whose position is it?
        missing_ballot_item_image = False
        missing_office_information = False
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = one_position.candidate_campaign_id
            ballot_item_we_vote_id = one_position.candidate_campaign_we_vote_id
            if not positive_value_exists(one_position.contest_office_we_vote_id) \
                    or not positive_value_exists(one_position.contest_office_name):
                missing_office_information = True
            if not positive_value_exists(one_position.ballot_item_image_url_https):
                missing_ballot_item_image = True
            one_position_success = True
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = one_position.contest_measure_id
            ballot_item_we_vote_id = one_position.contest_measure_we_vote_id
            one_position_success = True
        elif positive_value_exists(one_position.contest_office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = one_position.contest_office_id
            ballot_item_we_vote_id = one_position.contest_office_we_vote_id
            one_position_success = True
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None
            one_position_success = False

        if one_position_success:
            # Make sure we have this data to display. If we don't, refresh PositionEntered table from other tables.
            if not positive_value_exists(one_position.ballot_item_display_name) \
                    or not positive_value_exists(one_position.state_code) \
                    or not positive_value_exists(one_position.speaker_image_url_https) \
                    or missing_ballot_item_image \
                    or missing_office_information:
                one_position = position_manager.refresh_cached_position_info(one_position)
            one_position_dict_for_api = {
                'position_we_vote_id':          one_position.we_vote_id,
                'ballot_item_display_name':     one_position.ballot_item_display_name,  # Candidate name or Measure
                'ballot_item_image_url_https':  one_position.ballot_item_image_url_https,
                'ballot_item_twitter_handle':   one_position.ballot_item_twitter_handle,
                'ballot_item_political_party':  one_position.political_party,
                'ballot_item_state_code':       one_position.state_code,
                'kind_of_ballot_item':          kind_of_ballot_item,
                'ballot_item_id':               ballot_item_id,
                'ballot_item_we_vote_id':       ballot_item_we_vote_id,
                'contest_office_id':            one_position.contest_office_id,
                'contest_office_we_vote_id':    one_position.contest_office_we_vote_id,
                'contest_office_name':          one_position.contest_office_name,
                'is_support':                       one_position.is_support(),
                'is_positive_rating':               one_position.is_positive_rating(),
                'is_support_or_positive_rating':    one_position.is_support_or_positive_rating(),
                'is_oppose':                        one_position.is_oppose(),
                'is_negative_rating':               one_position.is_negative_rating(),
                'is_oppose_or_negative_rating':     one_position.is_oppose_or_negative_rating(),
                'is_information_only':              one_position.is_information_only(),
                'is_public_position':           one_position.is_public_position,
                'speaker_display_name':         one_position.speaker_display_name,  # Voter name
                'google_civic_election_id':     one_position.google_civic_election_id,
                'more_info_url':                one_position.more_info_url,
                'statement_text':               one_position.statement_text,
                'last_updated':                 one_position.last_updated(),
            }
            position_list.append(one_position_dict_for_api)

    status += ' POSITION_LIST_FOR_VOTER_SUCCEEDED'
    success = True
    json_data = {
        'status':                           status,
        'success':                          success,
        'count':                            len(position_list),
        'friends_vs_public':                friends_vs_public,
        'google_civic_election_id':         google_civic_election_id,
        'position_list':                    position_list,
        'show_all_other_elections':         show_all_other_elections,
        'show_only_this_election':          show_only_this_election,
        'state_code':                       state_code,
        'voter_we_vote_id':                 voter_we_vote_id,
        'voter_display_name':               voter_display_name,
        'voter_image_url_https':            voter_image_url_https,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_import_from_sample_file(request=None):  # , load_from_uri=False
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # Load saved json from local file
    with open("position/import_data/positions_sample.json") as json_data:
        structured_json = json.load(json_data)

    request = None
    return positions_import_from_structured_json(request, structured_json)


def positions_import_from_master_server(request, google_civic_election_id=''):
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    messages.add_message(request, messages.INFO, "Loading Positions from We Vote Master servers")
    logger.info("Loading Positions from We Vote Master servers")
    # Request json file from We Vote servers
    request = requests.get(POSITIONS_SYNC_URL, params={
        "key":                      WE_VOTE_API_KEY,  # This comes from an environment variable
        "format":                   'json',
        "google_civic_election_id": google_civic_election_id,
    })
    structured_json = json.loads(request.text)

    results = filter_positions_structured_json_for_local_duplicates(structured_json)
    filtered_structured_json = results['structured_json']
    duplicates_removed = results['duplicates_removed']

    import_results = positions_import_from_structured_json(filtered_structured_json)
    import_results['duplicates_removed'] = duplicates_removed

    return import_results


def filter_positions_structured_json_for_local_duplicates(structured_json):
    """
    With this function, we remove positions that seem to be duplicates, but have different we_vote_id's.
    We do not check to see if we have a matching office this routine -- that is done elsewhere.
    :param structured_json:
    :return:
    """
    duplicates_removed = 0
    filtered_structured_json = []
    position_list_manager = PositionListManager()
    for one_position in structured_json:
        we_vote_id = one_position['we_vote_id'] if 'we_vote_id' in one_position else ''
        google_civic_election_id = \
            one_position['google_civic_election_id'] if 'google_civic_election_id' in one_position else ''
        organization_we_vote_id = \
            one_position['organization_we_vote_id'] if 'organization_we_vote_id' in one_position else ''
        candidate_campaign_we_vote_id = one_position['candidate_campaign_we_vote_id'] \
            if 'candidate_campaign_we_vote_id' in one_position else ''
        contest_measure_we_vote_id = one_position['contest_measure_we_vote_id'] \
            if 'contest_measure_we_vote_id' in one_position else ''

        # Check to see if there is an entry that matches in all critical ways, minus the we_vote_id
        we_vote_id_from_master = we_vote_id

        results = position_list_manager.retrieve_possible_duplicate_positions(
            google_civic_election_id, organization_we_vote_id,
            candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            we_vote_id_from_master)

        if results['position_list_found']:
            # There seems to be a duplicate already in this database using a different we_vote_id
            duplicates_removed += 1
        else:
            filtered_structured_json.append(one_position)

    positions_results = {
        'success':              True,
        'status':               "FILTER_POSITIONS_FOR_DUPLICATES_PROCESS_COMPLETE",
        'duplicates_removed':   duplicates_removed,
        'structured_json':      filtered_structured_json,
    }
    return positions_results


def positions_import_from_structured_json(structured_json):
    positions_saved = 0
    positions_updated = 0
    positions_not_processed = 0
    for one_position in structured_json:
        # Make sure we have the minimum required variables
        if positive_value_exists(one_position["we_vote_id"]) \
                and (positive_value_exists(one_position["organization_we_vote_id"]) or positive_value_exists(
                        one_position["public_figure_we_vote_id"])) \
                and positive_value_exists(one_position["candidate_campaign_we_vote_id"]):
            # organization position on candidate
            pass
        elif positive_value_exists(one_position["we_vote_id"]) \
                and (positive_value_exists(one_position["organization_we_vote_id"]) or positive_value_exists(
                    one_position["public_figure_we_vote_id"])) \
                and positive_value_exists(one_position["contest_measure_we_vote_id"]):
            # organization position on measure
            pass
        else:
            # Note that we do not import voter_we_vote_id positions at this point because they are considered private
            positions_not_processed += 1
            continue

        # Check to see if this position had been imported previously
        position_on_stage_found = False
        try:
            if len(one_position["we_vote_id"]) > 0:
                position_query = PositionEntered.objects.filter(we_vote_id=one_position["we_vote_id"])
                if len(position_query):
                    position_on_stage = position_query[0]
                    position_on_stage_found = True
        except PositionEntered.DoesNotExist as e:
            pass
        except Exception as e:
            pass

        # We need to look up the local organization_id and store for internal use
        organization_id = 0
        if positive_value_exists(one_position["organization_we_vote_id"]):
            organization_manager = OrganizationManager()
            organization_id = organization_manager.fetch_organization_id(one_position["organization_we_vote_id"])
            if not positive_value_exists(organization_id):
                # If an id does not exist, then we don't have this organization locally
                positions_not_processed += 1
                continue
        elif positive_value_exists(one_position["public_figure_we_vote_id"]):
            # TODO Build this for public_figure - skip for now
            continue

        candidate_campaign_manager = CandidateCampaignManager()
        candidate_campaign_id = 0
        contest_measure_id = 0
        if positive_value_exists(one_position["candidate_campaign_we_vote_id"]):
            # We need to look up the local candidate_campaign_id and store for internal use
            candidate_campaign_id = candidate_campaign_manager.fetch_candidate_campaign_id_from_we_vote_id(
                one_position["candidate_campaign_we_vote_id"])
            if not positive_value_exists(candidate_campaign_id):
                # If an id does not exist, then we don't have this candidate locally
                positions_not_processed += 1
                continue
        elif positive_value_exists(one_position["contest_measure_we_vote_id"]):
            contest_measure_manager = ContestMeasureManager()
            contest_measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(
                one_position["contest_measure_we_vote_id"])
            if not positive_value_exists(contest_measure_id):
                # If an id does not exist, then we don't have this measure locally
                positions_not_processed += 1
                continue

        contest_office_id = 0
        if positive_value_exists(one_position['contest_office_we_vote_id']):
            # TODO
            pass

        politician_id = 0
        if positive_value_exists(one_position['politician_we_vote_id']):
            # TODO
            pass

        voter_id = 0
        if positive_value_exists(one_position['voter_we_vote_id']):
            # TODO
            pass

        # Find the google_civic_candidate_name so we have a backup way to link position if the we_vote_id is lost
        google_civic_candidate_name = one_position["google_civic_candidate_name"] if \
            "google_civic_candidate_name" in one_position else ''
        if not positive_value_exists(google_civic_candidate_name):
            google_civic_candidate_name = candidate_campaign_manager.fetch_google_civic_candidate_name_from_we_vote_id(
                one_position["candidate_campaign_we_vote_id"])

        try:
            if position_on_stage_found:
                # Update
                position_on_stage.we_vote_id = one_position["we_vote_id"]
                position_on_stage.candidate_campaign_id = candidate_campaign_id
                position_on_stage.candidate_campaign_we_vote_id = one_position["candidate_campaign_we_vote_id"]
                position_on_stage.contest_measure_id = contest_measure_id
                position_on_stage.contest_measure_we_vote_id = one_position["contest_measure_we_vote_id"]
                position_on_stage.contest_office_id = contest_office_id
                position_on_stage.contest_office_we_vote_id = one_position["contest_office_we_vote_id"]
                position_on_stage.date_entered = one_position["date_entered"]
                position_on_stage.google_civic_candidate_name = google_civic_candidate_name
                position_on_stage.google_civic_election_id = one_position["google_civic_election_id"]
                position_on_stage.more_info_url = one_position["more_info_url"]
                position_on_stage.organization_id = organization_id
                position_on_stage.organization_we_vote_id = one_position["organization_we_vote_id"]
                position_on_stage.stance = one_position["stance"]
                position_on_stage.statement_text = one_position["statement_text"]
                position_on_stage.statement_html = one_position["statement_html"]
            else:
                # Create new
                position_on_stage = PositionEntered(
                    we_vote_id=one_position["we_vote_id"],
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=one_position["candidate_campaign_we_vote_id"],
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=one_position["contest_measure_we_vote_id"],
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=one_position["contest_office_we_vote_id"],
                    date_entered=one_position["date_entered"],
                    google_civic_candidate_name=google_civic_candidate_name,
                    google_civic_election_id=one_position["google_civic_election_id"],
                    more_info_url=one_position["more_info_url"],
                    organization_id=organization_id,
                    organization_we_vote_id=one_position["organization_we_vote_id"],
                    stance=one_position["stance"],
                    statement_html=one_position["statement_html"],
                    statement_text=one_position["statement_text"],
                )

            position_on_stage.ballot_item_display_name = one_position["ballot_item_display_name"]
            position_on_stage.ballot_item_image_url_https = one_position["ballot_item_image_url_https"]
            position_on_stage.ballot_item_twitter_handle = one_position["ballot_item_twitter_handle"]
            position_on_stage.from_scraper = one_position["from_scraper"]
            position_on_stage.date_last_changed = one_position["date_last_changed"]
            position_on_stage.organization_certified = one_position["organization_certified"]
            position_on_stage.politician_id = politician_id
            position_on_stage.politician_we_vote_id = one_position["politician_we_vote_id"]
            position_on_stage.public_figure_we_vote_id = one_position["public_figure_we_vote_id"]
            position_on_stage.speaker_display_name = one_position["speaker_display_name"]
            position_on_stage.speaker_image_url_https = one_position["speaker_image_url_https"]
            position_on_stage.speaker_twitter_handle = one_position["speaker_twitter_handle"]
            position_on_stage.tweet_source_id = one_position["tweet_source_id"]
            position_on_stage.twitter_user_entered_position = one_position["twitter_user_entered_position"]
            position_on_stage.volunteer_certified = one_position["volunteer_certified"]
            position_on_stage.vote_smart_rating = one_position["vote_smart_rating"]
            position_on_stage.vote_smart_rating_id = one_position["vote_smart_rating_id"]
            position_on_stage.vote_smart_rating_name = one_position["vote_smart_rating_name"]
            position_on_stage.vote_smart_time_span = one_position["vote_smart_time_span"]
            position_on_stage.voter_entering_position = one_position["voter_entering_position"]
            position_on_stage.voter_id = voter_id
            position_on_stage.voter_we_vote_id = one_position["voter_we_vote_id"]

            position_on_stage.save()
            if position_on_stage_found:
                # Update
                positions_updated += 1
            else:
                # New
                positions_saved += 1
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            positions_not_processed += 1

    positions_results = {
        'success': True,
        'status': "POSITIONS_IMPORT_PROCESS_COMPLETE",
        'saved': positions_saved,
        'updated': positions_updated,
        'not_processed': positions_not_processed,
    }
    return positions_results


# We retrieve the position for this voter for one ballot item. Could just be the stance, but for now we are
# retrieving the entire position
def voter_position_retrieve_for_api(voter_device_id, office_we_vote_id, candidate_we_vote_id, measure_we_vote_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if positive_value_exists(office_we_vote_id):
        kind_of_ballot_item = OFFICE
        ballot_item_we_vote_id = office_we_vote_id
    elif positive_value_exists(candidate_we_vote_id):
        kind_of_ballot_item = CANDIDATE
        ballot_item_we_vote_id = candidate_we_vote_id
    elif positive_value_exists(measure_we_vote_id):
        kind_of_ballot_item = MEASURE
        ballot_item_we_vote_id = candidate_we_vote_id
    else:
        kind_of_ballot_item = ''
        ballot_item_we_vote_id = ''

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                  False,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    office_we_vote_id = office_we_vote_id.strip().lower()
    candidate_we_vote_id = candidate_we_vote_id.strip().lower()
    measure_we_vote_id = measure_we_vote_id.strip().lower()

    if not positive_value_exists(office_we_vote_id) and \
            not positive_value_exists(candidate_we_vote_id) and \
            not positive_value_exists(measure_we_vote_id):
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "POSITION_RETRIEVE_MISSING_AT_LEAST_ONE_BALLOT_ITEM_ID",
            'success':                  False,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_manager = PositionManager()

    if positive_value_exists(office_we_vote_id):
        results = position_manager.retrieve_voter_contest_office_position_with_we_vote_id(
            voter_id, office_we_vote_id)

    elif positive_value_exists(candidate_we_vote_id):
        results = position_manager.retrieve_voter_candidate_campaign_position_with_we_vote_id(
            voter_id, candidate_we_vote_id)

    elif positive_value_exists(measure_we_vote_id):
        results = position_manager.retrieve_voter_contest_measure_position_with_we_vote_id(
            voter_id, measure_we_vote_id)

    if results['position_found']:
        position = results['position']
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'success':                  True,
            'status':                   results['status'],
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_display_name': position.ballot_item_display_name,
            'speaker_display_name':     position.speaker_display_name,
            'speaker_image_url_https':  position.speaker_image_url_https,
            'speaker_twitter_handle':   position.speaker_twitter_handle,
            'is_support':               results['is_support'],
            'is_oppose':                results['is_oppose'],
            'is_information_only':      results['is_information_only'],
            'google_civic_election_id': position.google_civic_election_id,
            'office_we_vote_id':        position.contest_office_we_vote_id,
            'candidate_we_vote_id':     position.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       position.contest_measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   position.stance,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'more_info_url':            position.more_info_url,
            'last_updated':             position.last_updated(),
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   results['status'],
            'success':                  True,
            'position_we_vote_id':      '',
            'ballot_item_display_name': '',
            'speaker_display_name':     '',
            'speaker_image_url_https':  '',
            'speaker_twitter_handle':   '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': '',
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'stance':                   '',
            'statement_text':           '',
            'statement_html':           '',
            'more_info_url':            '',
            'last_updated':             '',
            'voter_device_id':          voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


# We retrieve the position for this voter for all ballot items. Could just be the stance, but for now we are
# retrieving the entire position
def voter_all_positions_retrieve_for_api(voter_device_id, google_civic_election_id):  # voterAllPositionsRetrieve
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status':                   "VOTER_DEVICE_ID_NOT_VALID-VOTER_ALL_POSITIONS",
            'success':                  False,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_ALL_POSITIONS",
            'success':                  False,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    position_list_manager = PositionListManager()
    voter_we_vote_id = ''

    results = position_list_manager.retrieve_all_positions_for_voter_simple(voter_id, voter_we_vote_id,
                                                                            google_civic_election_id)

    if results['position_list_found']:
        position_list = results['position_list']
        json_data = {
            'status':                   results['status'],
            'success':                  True,
            'position_list_found':      True,
            'position_list':            position_list,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                   "VOTER_POSITIONS_NOT_FOUND-NONE_EXIST",
            'success':                  True,
            'position_list_found':      False,
            'position_list':            [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_position_comment_save_for_api(  # voterPositionCommentSave
        voter_device_id, position_we_vote_id,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        statement_text,
        statement_html,
        ):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data_from_results = results['json_data']
        json_data = {
            'status':                   json_data_from_results['status'],
            'success':                  False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_POSITION_COMMENT",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data

    voter = voter_results['voter']
    position_we_vote_id = position_we_vote_id.strip().lower()

    existing_unique_identifier_found = positive_value_exists(position_we_vote_id)
    new_unique_identifier_found = positive_value_exists(voter_id) \
        and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
        )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(voter_id) \
        and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
        )
    if not unique_identifier_found:
        json_data = {
            'status':                   "POSITION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        # Don't need is_positive_rating, is_support_or_positive_rating, is_negative_rating,
        # or is_oppose_or_negative_rating
        json_data = {
            'status':                   "NEW_POSITION_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position_we_vote_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'statement_text':           statement_text,
            'is_public_position':       False
        }
        return json_data

    position_manager = PositionManager()
    save_results = position_manager.update_or_create_position_comment(
        position_we_vote_id=position_we_vote_id,
        voter_id=voter_id,
        voter_we_vote_id=voter.we_vote_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        statement_text=statement_text,
        statement_html=statement_html
    )

    if save_results['success']:
        position = save_results['position']

        is_public_position = save_results['is_public_position']

        if positive_value_exists(position.candidate_campaign_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = position.candidate_campaign_id
            ballot_item_we_vote_id = position.candidate_campaign_we_vote_id
        elif positive_value_exists(position.contest_measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = position.contest_measure_id
            ballot_item_we_vote_id = position.contest_measure_we_vote_id
        elif positive_value_exists(position.contest_office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = position.contest_office_id
            ballot_item_we_vote_id = position.contest_office_we_vote_id
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None

        json_data = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'statement_text':           position.statement_text,
            'statement_html':           position.statement_html,
            'is_public_position':       is_public_position
        }
        return json_data
    else:
        json_data = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      '',
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   "",
            'kind_of_ballot_item':      "",
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'is_public_position':       False
        }
        return json_data


def voter_position_visibility_save_for_api(  # voterPositionVisibilitySave
        voter_device_id,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        visibility_setting
        ):
    status = "ENTERING_VOTER_POSITION_VISIBILITY"
    is_public_position = None

    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data_from_results = results['json_data']
        json_data = {
            'status':                   json_data_from_results['status'],
            'success':                  False,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
        }
        return json_data

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID-VOTER_POSITION_COMMENT",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data

    voter = voter_results['voter']
    unique_identifier_found = positive_value_exists(voter_id) \
        and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
        )
    if not unique_identifier_found:
        json_data = {
            'status':                   "VOTER_POSITION_VISIBILITY-REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data

    switch_to_show_position_to_public = visibility_setting == SHOW_PUBLIC
    switch_to_show_position_to_friends = visibility_setting == FRIENDS_ONLY

    if not switch_to_show_position_to_public and not switch_to_show_position_to_friends:
        json_data = {
            'status':                   "VOTER_POSITION_VISIBILITY-NO_VISIBILITY_SETTING_PROVIDED",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'ballot_item_id':           0,
            'ballot_item_we_vote_id':   '',
            'kind_of_ballot_item':      '',
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data

    # Make sure we can lay our hands on the existing position entry
    success = False
    position_manager = PositionManager()
    if positive_value_exists(candidate_we_vote_id):
        results = position_manager.retrieve_voter_candidate_campaign_position_with_we_vote_id(
            voter_id, candidate_we_vote_id)
    elif positive_value_exists(measure_we_vote_id):
        results = position_manager.retrieve_voter_contest_measure_position_with_we_vote_id(
            voter_id, measure_we_vote_id)
    elif positive_value_exists(office_we_vote_id):
        results = position_manager.retrieve_voter_contest_office_position_with_we_vote_id(
            voter_id, office_we_vote_id)

    if not results['position_found']:
        # If here, an existing position does not exist and a new position needs to be created
        results = position_manager.create_position_for_visibility_change(
            voter_id, office_we_vote_id, candidate_we_vote_id, measure_we_vote_id, visibility_setting)
        if results['position_found']:
            is_public_position = results['is_public_position']
            position = results['position']
            status = results['status']
            success = results['success']
        else:
            status = "VOTER_POSITION_VISIBILITY-POSITION_NOT_FOUND_AND_NOT_CREATED"
            success = False

    elif results['position_found']:
        is_public_position = results['is_public_position']
        position = results['position']

        if positive_value_exists(switch_to_show_position_to_public):
            if positive_value_exists(is_public_position):
                status = "VOTER_POSITION_VISIBILITY-ALREADY_PUBLIC_POSITION"
                merge_results = position_manager.merge_into_public_position(position)
                success = merge_results['success']
                status += " " + merge_results['status']
            else:
                # If here, copy the position from the PositionForFriends table to the PositionEntered table
                status = "VOTER_POSITION_VISIBILITY-SWITCHING_TO_PUBLIC_POSITION"
                change_results = position_manager.transfer_to_public_position(position)
                success = change_results['success']
                status += " " + change_results['status']
                if success:
                    is_public_position = True
        elif positive_value_exists(switch_to_show_position_to_friends):
            if positive_value_exists(is_public_position):
                # If here, copy the position from the PositionEntered to the PositionForFriends table
                status = "VOTER_POSITION_VISIBILITY-SWITCHING_TO_FRIENDS_ONLY_POSITION"
                change_results = position_manager.transfer_to_friends_only_position(position)
                success = change_results['success']
                status += " " + change_results['status']
                if success:
                    is_public_position = False
            else:
                status = "VOTER_POSITION_VISIBILITY-ALREADY_FRIENDS_ONLY_POSITION"
                merge_results = position_manager.merge_into_friends_only_position(position)
                success = merge_results['success']
                status += " " + merge_results['status']
    else:
        status = "VOTER_POSITION_VISIBILITY-POSITION_NOT_FOUND-COULD_NOT_BE_CREATED"
        # If here, an existing position could not be created
        position_manager.create_position_for_visibility_change()

    if success:
        # Prepare return values
        if positive_value_exists(candidate_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = position.candidate_campaign_id
            ballot_item_we_vote_id = position.candidate_campaign_we_vote_id
        elif positive_value_exists(measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = position.contest_measure_id
            ballot_item_we_vote_id = measure_we_vote_id
        elif positive_value_exists(office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = position.contest_office_id
            ballot_item_we_vote_id = position.contest_office_we_vote_id
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None

        json_data = {
            'success':                  success,
            'status':                   status,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      position.we_vote_id,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data
    else:
        if positive_value_exists(candidate_we_vote_id):
            kind_of_ballot_item = CANDIDATE
            ballot_item_id = 0
            ballot_item_we_vote_id = candidate_we_vote_id
        elif positive_value_exists(measure_we_vote_id):
            kind_of_ballot_item = MEASURE
            ballot_item_id = 0
            ballot_item_we_vote_id = measure_we_vote_id
        elif positive_value_exists(office_we_vote_id):
            kind_of_ballot_item = OFFICE
            ballot_item_id = 0
            ballot_item_we_vote_id = office_we_vote_id
        else:
            kind_of_ballot_item = "UNKNOWN_BALLOT_ITEM"
            ballot_item_id = None
            ballot_item_we_vote_id = None

        json_data = {
            'success':                  success,
            'status':                   status,
            'voter_device_id':          voter_device_id,
            'position_we_vote_id':      '',
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'visibility_setting':       visibility_setting,
            'is_public_position':       is_public_position,
        }
        return json_data
