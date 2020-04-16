# share/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ShareManager
from organization.models import OrganizationManager
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def shared_item_retrieve_for_api(  # sharedItemRetrieve
        voter_device_id='',
        destination_full_url='',
        shared_item_code='',
        shared_item_clicked=False):
    status = ''
    success = True
    candidate_we_vote_id = ''
    date_first_shared = None
    is_ballot_share = False
    is_candidate_share = False
    is_measure_share = False
    is_office_share = False
    google_civic_election_id = ''
    measure_we_vote_id = ''
    office_we_vote_id = ''
    api_call_coming_from_voter_who_shared = False
    shared_by_voter_we_vote_id = ''
    shared_by_organization_we_vote_id = ''
    shared_item_code_no_opinions = ''
    shared_item_code_with_opinions = ''
    shared_item_id = 0
    site_owner_organization_we_vote_id = ''
    url_with_shared_item_code_no_opinions = ''
    url_with_shared_item_code_with_opinions = ''
    viewed_by_voter_we_vote_id = ''
    viewed_by_organization_we_vote_id = ''
    share_manager = ShareManager()

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        viewed_by_voter_we_vote_id = voter.we_vote_id
        viewed_by_organization_we_vote_id = voter.linked_organization_we_vote_id

    results = share_manager.retrieve_shared_item(
        destination_full_url=destination_full_url,
        shared_by_voter_we_vote_id=viewed_by_voter_we_vote_id,
        shared_item_code=shared_item_code)
    status += results['status']
    if not results['shared_item_found']:
        status += "SHARED_ITEM_NOT_FOUND "
        results = {
            'status':                       status,
            'success':                      False,
            'destination_full_url':         destination_full_url,
            'shared_item_code_no_opinions':             shared_item_code_no_opinions,
            'shared_item_code_with_opinions':           shared_item_code_with_opinions,
            'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
            'url_with_shared_item_code_with_opinions':  url_with_shared_item_code_with_opinions,
            'is_ballot_share':              is_ballot_share,
            'is_candidate_share':           is_candidate_share,
            'is_measure_share':             is_measure_share,
            'is_office_share':              is_office_share,
            'google_civic_election_id':     google_civic_election_id,
            'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
            'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
            'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
            'candidate_we_vote_id':         candidate_we_vote_id,
            'measure_we_vote_id':           measure_we_vote_id,
            'office_we_vote_id':            office_we_vote_id,
            'date_first_shared':            date_first_shared,
        }
        return results

    shared_item = results['shared_item']
    shared_item_id = shared_item.id
    if positive_value_exists(shared_item.destination_full_url):
        try:
            hostname = shared_item.destination_full_url.strip().lower()
            hostname = hostname.replace('http://', '')
            hostname = hostname.replace('https://', '')
            if '/' in hostname:
                hostname_array = hostname.split('/')
                hostname = hostname_array[0]
        except Exception as e:
            status += "COULD_NOT_MODIFY_HOSTNAME " + str(e) + " "
        url_with_shared_item_code_no_opinions = "https://" + hostname + "/-" + shared_item.shared_item_code_no_opinions
        url_with_shared_item_code_with_opinions = \
            "https://" + hostname + "/-" + shared_item.shared_item_code_with_opinions

    if viewed_by_voter_we_vote_id == shared_item.shared_by_voter_we_vote_id:
        api_call_coming_from_voter_who_shared = True

    # Store that the link was clicked
    if positive_value_exists(shared_item_clicked):
        opinions_included = shared_item.shared_item_code_with_opinions == shared_item_code
        clicked_results = share_manager.create_shared_link_clicked(
            shared_item_code=shared_item_code,
            shared_item_id=shared_item_id,
            shared_by_voter_we_vote_id=shared_item.shared_by_voter_we_vote_id,
            shared_by_organization_we_vote_id=shared_item.shared_by_organization_we_vote_id,
            viewed_by_voter_we_vote_id=viewed_by_voter_we_vote_id,
            viewed_by_organization_we_vote_id=viewed_by_organization_we_vote_id,
            opinions_included=opinions_included)
        status += clicked_results['status']

    results = {
        'status':                       status,
        'success':                      success,
        'destination_full_url':         shared_item.destination_full_url,
        'is_ballot_share':              shared_item.is_ballot_share,
        'is_candidate_share':           shared_item.is_candidate_share,
        'is_measure_share':             shared_item.is_measure_share,
        'is_office_share':              shared_item.is_office_share,
        'google_civic_election_id':     shared_item.google_civic_election_id,
        'site_owner_organization_we_vote_id':   shared_item.site_owner_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_item.shared_by_voter_we_vote_id,
        'shared_by_organization_we_vote_id':    shared_item.shared_by_organization_we_vote_id,
        'candidate_we_vote_id':         shared_item.candidate_we_vote_id,
        'measure_we_vote_id':           shared_item.measure_we_vote_id,
        'office_we_vote_id':            shared_item.office_we_vote_id,
        'date_first_shared':            str(shared_item.date_first_shared),
    }
    if api_call_coming_from_voter_who_shared:
        results['shared_item_code_no_opinions'] = shared_item.shared_item_code_no_opinions
        results['shared_item_code_with_opinions'] = shared_item.shared_item_code_with_opinions
        results['url_with_shared_item_code_no_opinions'] = url_with_shared_item_code_no_opinions
        results['url_with_shared_item_code_with_opinions'] = url_with_shared_item_code_with_opinions
    else:
        # If here we don't want to reveal the other shared_item code
        if shared_item.shared_item_code_no_opinions == shared_item_code:
            results['shared_item_code_no_opinions'] = shared_item.shared_item_code_no_opinions
            results['url_with_shared_item_code_no_opinions'] = url_with_shared_item_code_no_opinions
        else:
            results['shared_item_code_no_opinions'] = ''
            results['url_with_shared_item_code_no_opinions'] = ''
        if shared_item.shared_item_code_with_opinions == shared_item_code:
            results['shared_item_code_with_opinions'] = shared_item.shared_item_code_with_opinions
            results['url_with_shared_item_code_with_opinions'] = url_with_shared_item_code_with_opinions
        else:
            results['shared_item_code_with_opinions'] = ''
            results['url_with_shared_item_code_with_opinions'] = ''
    return results


def shared_item_save_for_api(  # sharedItemSave
        voter_device_id='',
        destination_full_url='',
        ballot_item_we_vote_id='',
        google_civic_election_id='',
        is_ballot_share=False,
        is_candidate_share=False,
        is_measure_share=False,
        is_office_share=False):
    status = ''
    success = True
    candidate_we_vote_id = ''
    date_first_shared = None
    measure_we_vote_id = ''
    office_we_vote_id = ''
    shared_by_voter_we_vote_id = ''
    shared_by_organization_we_vote_id = ''
    shared_item_code_no_opinions = ''
    shared_item_code_with_opinions = ''
    site_owner_organization_we_vote_id = ''
    url_with_shared_item_code_no_opinions = destination_full_url  # Default to this
    url_with_shared_item_code_with_opinions = destination_full_url  # Default to this

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if voter_results['voter_found']:
        voter = voter_results['voter']
        shared_by_voter_we_vote_id = voter.we_vote_id
        shared_by_organization_we_vote_id = voter.linked_organization_we_vote_id

    organization_manager = OrganizationManager()
    try:
        hostname = destination_full_url.strip().lower()
        hostname = hostname.replace('http://', '')
        hostname = hostname.replace('https://', '')
        if '/' in hostname:
            hostname_array = hostname.split('/')
            hostname = hostname_array[0]

        results = organization_manager.retrieve_organization_from_incoming_hostname(hostname, read_only=True)
        status += results['status']
        organization_found = results['organization_found']
        if organization_found:
            organization = results['organization']
            site_owner_organization_we_vote_id = organization.we_vote_id
    except Exception as e:
        status += "COULD_NOT_MODIFY_HOSTNAME " + str(e) + " "
        success = False

    if positive_value_exists(ballot_item_we_vote_id):
        if "cand" in ballot_item_we_vote_id:
            candidate_we_vote_id = ballot_item_we_vote_id
        elif "meas" in ballot_item_we_vote_id:
            measure_we_vote_id = ballot_item_we_vote_id
        elif "off" in ballot_item_we_vote_id:
            office_we_vote_id = ballot_item_we_vote_id

    required_variables_for_new_entry = positive_value_exists(destination_full_url) \
        and positive_value_exists(shared_by_voter_we_vote_id)
    if not required_variables_for_new_entry or not success:
        status += "NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING "
        results = {
            'status':                       status,
            'success':                      False,
            'destination_full_url':         destination_full_url,
            'shared_item_code_no_opinions':             shared_item_code_no_opinions,
            'shared_item_code_with_opinions':           shared_item_code_with_opinions,
            'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
            'url_with_shared_item_code_with_opinions':  url_with_shared_item_code_with_opinions,
            'is_ballot_share':              is_ballot_share,
            'is_candidate_share':           is_candidate_share,
            'is_measure_share':             is_measure_share,
            'is_office_share':              is_office_share,
            'google_civic_election_id':     google_civic_election_id,
            'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
            'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
            'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
            'candidate_we_vote_id':         candidate_we_vote_id,
            'measure_we_vote_id':           measure_we_vote_id,
            'office_we_vote_id':            office_we_vote_id,
            'date_first_shared':            date_first_shared,
        }
        return results

    share_manager = ShareManager()
    defaults = {
        'candidate_we_vote_id': candidate_we_vote_id,
        'google_civic_election_id': google_civic_election_id,
        'is_ballot_share': is_ballot_share,
        'is_candidate_share': is_candidate_share,
        'is_measure_share': is_measure_share,
        'is_office_share': is_office_share,
        'measure_we_vote_id': measure_we_vote_id,
        'office_we_vote_id': office_we_vote_id,
        'site_owner_organization_we_vote_id': site_owner_organization_we_vote_id,
        'shared_by_voter_we_vote_id': shared_by_voter_we_vote_id,
        'shared_by_organization_we_vote_id': shared_by_organization_we_vote_id,
    }
    create_results = share_manager.create_or_update_shared_item(
        destination_full_url=destination_full_url,
        shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        defaults=defaults,
    )
    status += create_results['status']
    if create_results['shared_item_found']:
        shared_item = create_results['shared_item']
        shared_item_code_no_opinions = shared_item.shared_item_code_no_opinions
        shared_item_code_with_opinions = shared_item.shared_item_code_with_opinions
        url_with_shared_item_code_no_opinions = "https://" + hostname + "/-" + shared_item_code_no_opinions
        url_with_shared_item_code_with_opinions = "https://" + hostname + "/-" + shared_item_code_with_opinions

    results = {
        'status':                       status,
        'success':                      success,
        'destination_full_url':         destination_full_url,
        'shared_item_code_no_opinions':             shared_item_code_no_opinions,
        'shared_item_code_with_opinions':           shared_item_code_with_opinions,
        'url_with_shared_item_code_no_opinions':    url_with_shared_item_code_no_opinions,
        'url_with_shared_item_code_with_opinions':  url_with_shared_item_code_with_opinions,
        'is_ballot_share':              is_ballot_share,
        'is_candidate_share':           is_candidate_share,
        'is_measure_share':             is_measure_share,
        'is_office_share':              is_office_share,
        'google_civic_election_id':     google_civic_election_id,
        'site_owner_organization_we_vote_id':   site_owner_organization_we_vote_id,
        'shared_by_voter_we_vote_id':           shared_by_voter_we_vote_id,
        'shared_by_organization_we_vote_id':    shared_by_organization_we_vote_id,
        'candidate_we_vote_id':         candidate_we_vote_id,
        'measure_we_vote_id':           measure_we_vote_id,
        'office_we_vote_id':            office_we_vote_id,
        'date_first_shared':            date_first_shared,
    }
    return results
