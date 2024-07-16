from django.db.models import Q

from candidate.models import CandidateCampaign, CandidateListManager
from candidate.controllers import fetch_ballotpedia_urls_to_retrieve_for_links_count, \
    fetch_ballotpedia_urls_to_retrieve_for_photos_count
from wevote_functions.functions import convert_to_int, is_valid_state_code, positive_value_exists
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, is_valid_state_code, positive_value_exists
from wevote_settings.models import RemoteRequestHistory, RemoteRequestHistoryManager
from .controllers import attach_ballotpedia_election_by_district_from_api, get_photo_url_from_ballotpedia, \
    retrieve_ballot_items_from_polling_location, \
    retrieve_ballotpedia_candidates_by_district_from_api, retrieve_ballotpedia_measures_by_district_from_api, \
    retrieve_ballotpedia_district_id_list_for_polling_location, retrieve_ballotpedia_offices_by_district_from_api, \
    get_candidate_links_from_ballotpedia

logger = wevote_functions.admin.get_logger(__name__)


def retrieve_ballotpedia_links_in_bulk(
    candidate_we_vote_id_list=[],
    limit=50,
    remote_request_history_manager=None,
    state_code='',
):
    already_retrieved = 0
    already_stored = 0
    candidate_list = []
    error_message_to_print = ''
    if remote_request_history_manager is None:
        remote_request_history_manager = RemoteRequestHistoryManager()
    status = ''
    success = True

    if not candidate_we_vote_id_list or len(candidate_we_vote_id_list) == 0:
        # #############################################################
        # Get candidates in the elections we care about - used below
        candidate_list_manager = CandidateListManager()
        # Only look at candidates for this year
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_year_list(
            year_list=[2024])
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    try:
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(we_vote_id__in=candidate_we_vote_id_list)  # Candidates for election or this year
        # Don't include candidates that do not have ballotpedia_candidate_url
        queryset = queryset.exclude(Q(ballotpedia_candidate_url__isnull=True) | Q(ballotpedia_candidate_url__exact=''))
        # Only include candidates that don't have a photo
        queryset = queryset.filter(
            Q(ballotpedia_photo_url__isnull=True) | Q(ballotpedia_photo_url__iexact=''))
        queryset = queryset.exclude(ballotpedia_candidate_links_retrieved=True)
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        if positive_value_exists(limit):
            candidate_list = queryset[:limit]
        else:
            candidate_list = list(queryset)
        # Run search in ballotpedia candidates
        for one_candidate in candidate_list:
            # Check to see if we have already tried to find all of their links from Ballotpedia. We don't want to
            #  search Ballotpedia more than once.
            get_results = get_candidate_links_from_ballotpedia(
                incoming_object=one_candidate,
                remote_request_history_manager=remote_request_history_manager,
                save_to_database=True)
            error_message_to_print += get_results['error_message_to_print']
            status += get_results['status']

    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    results = {
        'already_retrieved': already_retrieved,
        'already_stored': already_stored,
        'candidate_list': candidate_list,
        'error_message_to_print': error_message_to_print,
        'status': status,
        'success': success,
    }
    return results


def retrieve_ballotpedia_photos_in_bulk(
    candidate_we_vote_id_list=[],
    limit=50,
    remote_request_history_manager=None,
    state_code='',
):
    error_message_to_print = ''
    if remote_request_history_manager is None:
        remote_request_history_manager = RemoteRequestHistoryManager()
    status = ''
    success = True

    if not candidate_we_vote_id_list or len(candidate_we_vote_id_list) == 0:
        # #############################################################
        # Get candidates in the elections we care about - used below
        candidate_list_manager = CandidateListManager()
        # Only look at candidates for this year
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_year_list(
            year_list=[2024])
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    candidate_list = []
    already_retrieved = 0
    already_stored = 0
    photos_retrieved = 0
    photos_to_retrieve = 0
    try:
        queryset = CandidateCampaign.objects.all()
        queryset = queryset.filter(we_vote_id__in=candidate_we_vote_id_list)  # Candidates for election or this year
        queryset = queryset.exclude(ballotpedia_photo_url_is_placeholder=True)
        queryset = queryset.exclude(ballotpedia_photo_url_is_broken=True)
        # Don't include candidates that do not have ballotpedia_candidate_url
        queryset = queryset. \
            exclude(Q(ballotpedia_candidate_url__isnull=True) | Q(ballotpedia_candidate_url__exact=''))
        # Only include candidates that don't have a photo
        queryset = queryset.filter(
            Q(ballotpedia_photo_url__isnull=True) | Q(ballotpedia_photo_url__iexact=''))
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        photos_to_retrieve = queryset.count()

        if positive_value_exists(limit):
            candidate_list = queryset[:limit]
        else:
            candidate_list = list(queryset)
        # print(candidate_list)
        # Run search in ballotpedia candidates
        for one_candidate in candidate_list:
            # Check to see if we have already tried to find their photo link from Ballotpedia. We don't want to
            #  search Ballotpedia more than once.
            # request_history_query = RemoteRequestHistory.objects.using('readonly').filter(
            #     candidate_campaign_we_vote_id__iexact=one_candidate.we_vote_id,
            #     kind_of_action=RETRIEVE_POSSIBLE_BALLOTPEDIA_PHOTOS)
            # request_history_list = list(request_history_query)
            request_history_list = []
            if not positive_value_exists(len(request_history_list)):
                get_results = get_photo_url_from_ballotpedia(
                    incoming_object=one_candidate,
                    remote_request_history_manager=remote_request_history_manager,
                    save_to_database=True)
                if get_results['photo_url_found']:
                    photos_retrieved += 1
                error_message_to_print += get_results['error_message_to_print']
                status += get_results['status']
            else:
                logger.info("Skipped URL: " + one_candidate.ballotpedia_candidate_url)
                already_stored += 1
    except CandidateCampaign.DoesNotExist:
        # This is fine, do nothing
        pass

    results = {
        'already_retrieved': already_retrieved,
        'already_stored': already_stored,
        'candidate_list': candidate_list,
        'error_message_to_print': error_message_to_print,
        'photos_retrieved': photos_retrieved,
        'photos_to_retrieve': photos_to_retrieve,
        'status': status,
        'success': success,
    }
    return results


def retrieve_links_and_photos_from_ballotpedia_batch_process():
    status = ''
    success = True

    # #############################################################
    # Get candidates in the elections we care about - used below
    candidate_list_manager = CandidateListManager()
    # Only look at candidates for this year
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_year_list(
        year_list=[2024])
    candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    photo_results = retrieve_ballotpedia_photos_in_bulk(
        candidate_we_vote_id_list=candidate_we_vote_id_list,
        limit=10,
    )
    photos_retrieved = photo_results['photos_retrieved']
    photos_to_retrieve = fetch_ballotpedia_urls_to_retrieve_for_photos_count()

    links_results = retrieve_ballotpedia_links_in_bulk(
        candidate_we_vote_id_list=candidate_we_vote_id_list,
        limit=50,
    )
    profiles_retrieved = links_results['already_retrieved']
    profiles_to_retrieve = fetch_ballotpedia_urls_to_retrieve_for_links_count()

    results = {
        'photos_retrieved': photos_retrieved,
        'photos_to_retrieve': photos_to_retrieve,
        'profiles_retrieved': profiles_retrieved,
        'profiles_to_retrieve': profiles_to_retrieve,
        'status': status,
        'success': success,
    }
    return results
