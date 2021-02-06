# quick_info/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import QuickInfo, QuickInfoManager, QuickInfoMasterManager
from ballot.models import OFFICE, CANDIDATE, POLITICIAN, MEASURE
from candidate.models import CandidateManager
from config.base import get_environment_variable
from django.contrib import messages
from django.http import HttpResponse
from exception.models import handle_record_not_found_exception, handle_record_not_saved_exception
from organization.models import OrganizationManager
import json
from voter.models import fetch_voter_id_from_voter_device_link, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")
QUICK_INFO_URL = get_environment_variable("QUICK_INFO_URL")


def quick_info_save_for_api(  # TODO to be converted
        voter_device_id, quick_info_id, quick_info_we_vote_id,
        organization_we_vote_id,
        public_figure_we_vote_id,
        voter_we_vote_id,
        google_civic_election_id,
        ballot_item_display_name,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        stance,
        statement_text,
        statement_html,
        more_info_url
        ):
    quick_info_id = convert_to_int(quick_info_id)
    quick_info_we_vote_id = quick_info_we_vote_id.strip().lower()

    existing_unique_identifier_found = positive_value_exists(quick_info_id) \
        or positive_value_exists(quick_info_we_vote_id)
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
            'status':                   "QUICK_INFO_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'ballot_item_display_name':        ballot_item_display_name,
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
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
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                   "NEW_QUICK_INFO_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'ballot_item_display_name':        ballot_item_display_name,
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
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

    quick_info_manager = QuickInfoManager()
    save_results = quick_info_manager.update_or_create_quick_info(
        quick_info_id=quick_info_id,
        quick_info_we_vote_id=quick_info_we_vote_id,
        organization_we_vote_id=organization_we_vote_id,
        public_figure_we_vote_id=public_figure_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        ballot_item_display_name=ballot_item_display_name,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        stance=stance,
        statement_text=statement_text,
        statement_html=statement_html,
        more_info_url=more_info_url,
    )

    if save_results['success']:
        quick_info = save_results['quick_info']
        results = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info.id,
            'quick_info_we_vote_id':      quick_info.we_vote_id,
            'new_quick_info_created':     save_results['new_quick_info_created'],
            'ballot_item_display_name':        quick_info.ballot_item_display_name,
            'is_support':               quick_info.is_support(),
            'is_oppose':                quick_info.is_oppose(),
            'is_information_only':      quick_info.is_information_only(),
            'organization_we_vote_id':  quick_info.organization_we_vote_id,
            'google_civic_election_id': quick_info.google_civic_election_id,
            'voter_id':                 quick_info.voter_id,
            'office_we_vote_id':        '',  # quick_info.office_we_vote_id,
            'candidate_we_vote_id':     quick_info.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       quick_info.contest_measure_we_vote_id,
            'stance':                   quick_info.stance,
            'statement_text':           quick_info.statement_text,
            'statement_html':           quick_info.statement_html,
            'more_info_url':            quick_info.more_info_url,
            'last_updated':             '',
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'ballot_item_display_name':        '',
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
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


def quick_info_import_from_sample_file(request=None):  # , load_from_uri=False  # TODO to be converted
    """
    Get the json data, and either create new entries or update existing
    :return:
    """
    # if load_from_uri:
    #     # Request json file from We Vote servers
    #     messages.add_message(request, messages.INFO, "Loading quick_info from We Vote Master servers")
    #     request = requests.get(QUICK_INFO_URL, params={
    #         "key": WE_VOTE_API_KEY,  # This comes from an environment variable
    #     })
    #     structured_json = json.loads(request.text)
    # else:
    # Load saved json from local file
    with open("quick_info/import_data/quick_info_sample.json") as json_data:
        structured_json = json.load(json_data)

    quick_info_saved = 0
    quick_info_updated = 0
    quick_info_not_processed = 0
    for one_quick_info in structured_json:
        # Make sure we have the minimum required variables
        if not positive_value_exists(one_quick_info["we_vote_id"]) \
                or not positive_value_exists(one_quick_info["organization_we_vote_id"])\
                or not positive_value_exists(one_quick_info["candidate_campaign_we_vote_id"]):
            quick_info_not_processed += 1
            continue

        # Check to see if this quick_info is already being used anywhere
        quick_info_found = False
        try:
            if len(one_quick_info["we_vote_id"]) > 0:
                quick_info_query = QuickInfo.objects.filter(we_vote_id=one_quick_info["we_vote_id"])
                if len(quick_info_query):
                    quick_info = quick_info_query[0]
                    quick_info_found = True
        except QuickInfo.DoesNotExist as e:
            handle_record_not_found_exception(e, logger=logger)
            pass
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        # We need to look up the local organization_id based on the newly saved we_vote_id
        organization_manager = OrganizationManager()
        organization_id = organization_manager.fetch_organization_id(one_quick_info["organization_we_vote_id"])

        # We need to look up the local candidate_campaign_id
        candidate_manager = CandidateManager()
        candidate_campaign_id = candidate_manager.fetch_candidate_id_from_we_vote_id(
            one_quick_info["candidate_campaign_we_vote_id"])

        # Find the google_civic_candidate_name so we have a backup way to link quick_info if the we_vote_id is lost
        google_civic_candidate_name = one_quick_info["google_civic_candidate_name"] if \
            "google_civic_candidate_name" in one_quick_info else ''
        if not positive_value_exists(google_civic_candidate_name):
            google_civic_candidate_name = candidate_manager.fetch_google_civic_candidate_name_from_we_vote_id(
                one_quick_info["candidate_campaign_we_vote_id"])

        # TODO We need to look up contest_measure_id
        contest_measure_id = 0

        try:
            if quick_info_found:
                # Update
                quick_info.we_vote_id = one_quick_info["we_vote_id"]
                quick_info.organization_id = organization_id
                quick_info.organization_we_vote_id = one_quick_info["organization_we_vote_id"]
                quick_info.candidate_campaign_id = candidate_campaign_id
                quick_info.candidate_campaign_we_vote_id = one_quick_info["candidate_campaign_we_vote_id"]
                quick_info.google_civic_candidate_name = google_civic_candidate_name
                quick_info.contest_measure_id = contest_measure_id
                quick_info.date_entered = one_quick_info["date_entered"]
                quick_info.google_civic_election_id = one_quick_info["google_civic_election_id"]
                quick_info.stance = one_quick_info["stance"]
                quick_info.more_info_url = one_quick_info["more_info_url"]
                quick_info.statement_text = one_quick_info["statement_text"]
                quick_info.statement_html = one_quick_info["statement_html"]
                quick_info.save()
                quick_info_updated += 1
                # messages.add_message(request, messages.INFO, u"QuickInfo updated: {we_vote_id}".format(
                #     we_vote_id=one_quick_info["we_vote_id"]))
            else:
                # Create new
                quick_info = QuickInfo(
                    we_vote_id=one_quick_info["we_vote_id"],
                    organization_id=organization_id,
                    organization_we_vote_id=one_quick_info["organization_we_vote_id"],
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=one_quick_info["candidate_campaign_we_vote_id"],
                    google_civic_candidate_name=google_civic_candidate_name,
                    contest_measure_id=contest_measure_id,
                    date_entered=one_quick_info["date_entered"],
                    google_civic_election_id=one_quick_info["google_civic_election_id"],
                    stance=one_quick_info["stance"],
                    more_info_url=one_quick_info["more_info_url"],
                    statement_text=one_quick_info["statement_text"],
                    statement_html=one_quick_info["statement_html"],
                )
                quick_info.save()
                quick_info_saved += 1
                # messages.add_message(request, messages.INFO, u"New quick_info imported: {we_vote_id}".format(
                #     we_vote_id=one_quick_info["we_vote_id"]))
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            if request is not None:
                messages.add_message(request, messages.ERROR,
                                     u"Could not save/update quick_info, "
                                     u"quick_info_found: {quick_info_found}, "
                                     u"we_vote_id: {we_vote_id}, "
                                     u"organization_we_vote_id: {organization_we_vote_id}, "
                                     u"candidate_campaign_we_vote_id: {candidate_campaign_we_vote_id}".format(
                                         quick_info_found=quick_info_found,
                                         we_vote_id=one_quick_info["we_vote_id"],
                                         organization_we_vote_id=one_quick_info["organization_we_vote_id"],
                                         candidate_campaign_we_vote_id=one_quick_info["candidate_campaign_we_vote_id"],
                                     ))
            quick_info_not_processed += 1

    quick_info_results = {
        'saved': quick_info_saved,
        'updated': quick_info_updated,
        'not_processed': quick_info_not_processed,
    }
    return quick_info_results


# We retrieve the quick info for one ballot item. Could just be the stance, but for now we are
# retrieving all data
def quick_info_retrieve_for_api(kind_of_ballot_item, ballot_item_we_vote_id):
    ballot_item_we_vote_id = ballot_item_we_vote_id.strip().lower()

    if not positive_value_exists(kind_of_ballot_item) and \
            not kind_of_ballot_item in (OFFICE, CANDIDATE, POLITICIAN, MEASURE):
        json_data = {
            'status':                           "QUICK_INFO_RETRIEVE_KIND_OF_BALLOT_ITEM_NOT_SPECIFIED",
            'success':                          False,
            'quick_info_id':                    0,
            'quick_info_we_vote_id':            '',
            'kind_of_ballot_item':              kind_of_ballot_item,
            'ballot_item_we_vote_id':           ballot_item_we_vote_id,
            'quick_info_found':                 False,
            'language':                         '',
            'info_text':                        '',
            'info_html':                        '',
            'ballot_item_display_name':         '',
            'more_info_credit_text':            '',
            'more_info_url':                    '',
            'last_updated':                     '',
            'last_editor_we_vote_id':           '',
            'office_we_vote_id':                '',
            'candidate_we_vote_id':             '',
            'politician_we_vote_id':            '',
            'measure_we_vote_id':               '',
            'quick_info_master_we_vote_id':     '',
            'google_civic_election_id':         '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if kind_of_ballot_item == OFFICE:
        office_we_vote_id = ballot_item_we_vote_id
        candidate_we_vote_id = ""
        politician_we_vote_id = ""
        measure_we_vote_id = ""
    elif kind_of_ballot_item == CANDIDATE:
        office_we_vote_id = ""
        candidate_we_vote_id = ballot_item_we_vote_id
        politician_we_vote_id = ""
        measure_we_vote_id = ""
    elif kind_of_ballot_item == POLITICIAN:
        office_we_vote_id = ""
        candidate_we_vote_id = ""
        politician_we_vote_id = ballot_item_we_vote_id
        measure_we_vote_id = ""
    elif kind_of_ballot_item == MEASURE:
        office_we_vote_id = ""
        candidate_we_vote_id = ""
        politician_we_vote_id = ""
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_we_vote_id = ""
        candidate_we_vote_id = ""
        politician_we_vote_id = ""
        measure_we_vote_id = ""

    if not positive_value_exists(office_we_vote_id) and \
            not positive_value_exists(candidate_we_vote_id) and \
            not positive_value_exists(politician_we_vote_id) and \
            not positive_value_exists(measure_we_vote_id):
        json_data = {
            'status':                           "QUICK_INFO_RETRIEVE_MISSING_BALLOT_ITEM_ID",
            'success':                          False,
            'quick_info_id':                    0,
            'quick_info_we_vote_id':            '',
            'kind_of_ballot_item':              kind_of_ballot_item,
            'ballot_item_we_vote_id':           ballot_item_we_vote_id,
            'quick_info_found':                 False,
            'language':                         '',
            'info_text':                        '',
            'info_html':                        '',
            'ballot_item_display_name':         '',
            'more_info_credit_text':            '',
            'more_info_url':                    '',
            'last_updated':                     '',
            'last_editor_we_vote_id':           '',
            'office_we_vote_id':                office_we_vote_id,
            'candidate_we_vote_id':             candidate_we_vote_id,
            'politician_we_vote_id':            politician_we_vote_id,
            'measure_we_vote_id':               measure_we_vote_id,
            'quick_info_master_we_vote_id':     '',
            'google_civic_election_id':         '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    quick_info_manager = QuickInfoManager()

    if positive_value_exists(office_we_vote_id):
        results = quick_info_manager.retrieve_contest_office_quick_info(office_we_vote_id)

    elif positive_value_exists(candidate_we_vote_id):
        results = quick_info_manager.retrieve_candidate_quick_info(candidate_we_vote_id)

    elif positive_value_exists(measure_we_vote_id):
        results = quick_info_manager.retrieve_contest_measure_quick_info(measure_we_vote_id)

    # retrieve_quick_info results
    # results = {
    #     'success':                  success,
    #     'status':                   status,
    #     'error_result':             error_result,
    #     'DoesNotExist':             exception_does_not_exist,
    #     'MultipleObjectsReturned':  exception_multiple_object_returned,
    #     'quick_info_found':         True if quick_info_id > 0 else False,
    #     'quick_info_id':            quick_info_id,
    #     'quick_info_we_vote_id':    quick_info_on_stage.we_vote_id,
    #     'quick_info':               quick_info_on_stage,
    #     'is_chinese':               quick_info_on_stage.is_chinese(),
    #     'is_english':               quick_info_on_stage.is_english(),
    #     'is_spanish':               quick_info_on_stage.is_spanish(),
    #     'is_tagalog':               quick_info_on_stage.is_tagalog(),
    #     'is_vietnamese':            quick_info_on_stage.is_vietnamese(),
    # }

    if results['quick_info_found']:
        quick_info = results['quick_info']

        if positive_value_exists(quick_info.quick_info_master_we_vote_id):
            # If here, we are looking at a master entry
            quick_info_master_manager = QuickInfoMasterManager()
            quick_info_master_results = quick_info_master_manager.retrieve_quick_info_master_from_we_vote_id(
                quick_info.quick_info_master_we_vote_id)
            if quick_info_master_results['quick_info_master_found']:
                quick_info_master = quick_info_master_results['quick_info_master']
                info_text = quick_info_master.info_text
                info_html = quick_info_master.info_html
                more_info_url = quick_info_master.more_info_url
                more_info_credit_text = quick_info_master.more_info_credit_text()
            else:
                info_text = ""
                info_html = ""
                more_info_url = ""
                more_info_credit_text = ""
                results['status'] += ", " + quick_info_master_results['status']
        else:
            # If here, we are looking at a unique entry
            info_text = quick_info.info_text
            info_html = quick_info.info_html
            more_info_url = quick_info.more_info_url
            more_info_credit_text = quick_info.more_info_credit_text()

        json_data = {
            'success':                          True,
            'status':                           results['status'],
            'quick_info_found':                 True,
            'quick_info_id':                    quick_info.id,
            'quick_info_we_vote_id':            quick_info.we_vote_id,
            'kind_of_ballot_item':              kind_of_ballot_item,
            'ballot_item_we_vote_id':           ballot_item_we_vote_id,
            'ballot_item_display_name':         quick_info.ballot_item_display_name,
            'language':                         quick_info.language,
            'info_text':                        info_text,
            'info_html':                        info_html,
            'more_info_url':                    more_info_url,
            'more_info_credit_text':            more_info_credit_text,
            'last_updated':                     str(quick_info.last_updated),
            'last_editor_we_vote_id':           quick_info.last_editor_we_vote_id,
            'office_we_vote_id':                quick_info.contest_office_we_vote_id,
            'candidate_we_vote_id':             quick_info.candidate_campaign_we_vote_id,
            'politician_we_vote_id':            quick_info.politician_we_vote_id,
            'measure_we_vote_id':               quick_info.contest_measure_we_vote_id,
            'quick_info_master_we_vote_id':     quick_info.quick_info_master_we_vote_id,
            'google_civic_election_id':         quick_info.google_civic_election_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status':                           results['status'],
            'success':                          False,
            'quick_info_id':                    0,
            'quick_info_we_vote_id':            '',
            'kind_of_ballot_item':              kind_of_ballot_item,
            'ballot_item_we_vote_id':           ballot_item_we_vote_id,
            'quick_info_found':                 False,
            'language':                         '',
            'info_text':                        '',
            'info_html':                        '',
            'ballot_item_display_name':         '',
            'more_info_credit_text':            '',
            'more_info_url':                    '',
            'last_updated':                     '',
            'last_editor_we_vote_id':           '',
            'contest_office_we_vote_id':        office_we_vote_id,
            'candidate_campaign_we_vote_id':    candidate_we_vote_id,
            'politician_we_vote_id':            politician_we_vote_id,
            'contest_measure_we_vote_id':       measure_we_vote_id,
            'quick_info_master_we_vote_id':     '',
            'google_civic_election_id':         '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def quick_info_text_save_for_api(  # TODO to be converted
        voter_device_id, quick_info_id, quick_info_we_vote_id,
        google_civic_election_id,
        office_we_vote_id,
        candidate_we_vote_id,
        measure_we_vote_id,
        statement_text,
        statement_html
        ):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data_from_results = results['json_data']
        json_data = {
            'status':                   json_data_from_results['status'],
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        json_data = {
            'status':                   "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter = voter_results['voter']
    quick_info_id = convert_to_int(quick_info_id)
    quick_info_we_vote_id = quick_info_we_vote_id.strip().lower()

    existing_unique_identifier_found = positive_value_exists(quick_info_id) \
        or positive_value_exists(quick_info_we_vote_id)
    new_unique_identifier_found = positive_value_exists(voter_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have these variables in order to create a new entry
    required_variables_for_new_entry = positive_value_exists(voter_id) \
        and positive_value_exists(google_civic_election_id) and (
        positive_value_exists(office_we_vote_id) or
        positive_value_exists(candidate_we_vote_id) or
        positive_value_exists(measure_we_vote_id)
    )
    if not unique_identifier_found:
        results = {
            'status':                   "QUICK_INFO_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status':                   "NEW_QUICK_INFO_REQUIRED_VARIABLES_MISSING",
            'success':                  False,
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return results

    quick_info_manager = QuickInfoManager()
    save_results = quick_info_manager.update_or_create_quick_info(
        quick_info_id=quick_info_id,
        quick_info_we_vote_id=quick_info_we_vote_id,
        voter_we_vote_id=voter.we_vote_id,
        google_civic_election_id=google_civic_election_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        statement_text=statement_text,
        statement_html=statement_html,
    )

    if save_results['success']:
        quick_info = save_results['quick_info']
        results = {
            'success':                  save_results['success'],
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info.id,
            'quick_info_we_vote_id':      quick_info.we_vote_id,
            'new_quick_info_created':     save_results['new_quick_info_created'],
            'is_support':               quick_info.is_support(),
            'is_oppose':                quick_info.is_oppose(),
            'is_information_only':      quick_info.is_information_only(),
            'google_civic_election_id': quick_info.google_civic_election_id,
            'office_we_vote_id':        quick_info.contest_office_we_vote_id,
            'candidate_we_vote_id':     quick_info.candidate_campaign_we_vote_id,
            'measure_we_vote_id':       quick_info.contest_measure_we_vote_id,
            'statement_text':           quick_info.statement_text,
            'statement_html':           quick_info.statement_html,
            'last_updated':             '',
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'quick_info_id':              quick_info_id,
            'quick_info_we_vote_id':      quick_info_we_vote_id,
            'new_quick_info_created':     False,
            'is_support':               False,
            'is_oppose':                False,
            'is_information_only':      False,
            'google_civic_election_id': google_civic_election_id,
            'office_we_vote_id':        office_we_vote_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'measure_we_vote_id':       measure_we_vote_id,
            'statement_text':           statement_text,
            'statement_html':           statement_html,
            'last_updated':             '',
        }
        return results
