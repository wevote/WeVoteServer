# import_export_vote_smart/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_vote_smart_candidates_into_local_db, \
    retrieve_vote_smart_candidate_bio_into_local_db, \
    retrieve_vote_smart_position_categories_into_local_db, \
    retrieve_vote_smart_officials_into_local_db, retrieve_and_save_vote_smart_states, \
    retrieve_vote_smart_ratings_by_candidate_into_local_db, retrieve_vote_smart_ratings_by_group_into_local_db, \
    retrieve_vote_smart_special_interest_group_into_local_db, \
    retrieve_vote_smart_special_interest_groups_into_local_db, \
    transfer_vote_smart_ratings_to_positions_for_candidate
from .models import VoteSmartCategory, VoteSmartRating, VoteSmartRatingOneCandidate, VoteSmartSpecialInterestGroup,\
    VoteSmartState
from .votesmart_local import VotesmartApiError
from candidate.models import CandidateCampaign, CandidateCampaignManager
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_deleted_exception, handle_record_not_found_exception, handle_record_not_saved_exception, \
    print_to_log
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists, STATE_CODE_MAP

logger = wevote_functions.admin.get_logger(__name__)


def import_one_candidate_ratings_view(request, vote_smart_candidate_id):
    one_group_results = retrieve_vote_smart_ratings_by_candidate_into_local_db(vote_smart_candidate_id)

    if one_group_results['success']:
        messages.add_message(request, messages.INFO, "Ratings for one candidate retrieved. ")
    else:
        messages.add_message(request, messages.ERROR, "Ratings for one candidate NOT retrieved. "
                                                      "(error: {error_message})"
                                                      "".format(error_message=one_group_results['status']))

    candidate_manager = CandidateCampaignManager()
    results = candidate_manager.retrieve_candidate_campaign_from_vote_smart_id(vote_smart_candidate_id)
    if results['candidate_campaign_found']:
        candidate = results['candidate_campaign']
        candidate_campaign_id = candidate.id
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_campaign_id,)))
    else:
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()))


def transfer_vote_smart_ratings_to_positions_for_candidate_view(request, candidate_campaign_id):

    results = transfer_vote_smart_ratings_to_positions_for_candidate(candidate_campaign_id)

    if results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        messages.add_message(request, messages.ERROR, results['status'])

    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_campaign_id,)))


def import_group_ratings_view(request):
    # state_code = request.GET.get('state_code', 'NA')  # Default to national
    # category_id = request.GET.get('category_id', 0)

    # Retrieve each group so we can request the ratings for each group
    get_sig_group_count = 0
    get_sig_error_message_count = 0
    special_interest_group_list = VoteSmartSpecialInterestGroup.objects.order_by('name')
    for one_group in special_interest_group_list:
        special_interest_group_id = one_group.sigId
        one_group_results = retrieve_vote_smart_ratings_by_group_into_local_db(special_interest_group_id)

        if not one_group_results['success']:
            print_to_log(logger=logger, exception_message_optional=one_group_results['status'])
            get_sig_error_message_count += 1
        else:
            get_sig_group_count += 1

    messages.add_message(request, messages.INFO, "Ratings from {get_sig_group_count} "
                                                 "Special Interest Groups retrieved. "
                                                 "(errors: {get_sig_error_message_count})"
                                                 "".format(get_sig_group_count=get_sig_group_count,
                                                           get_sig_error_message_count=get_sig_error_message_count))

    return HttpResponseRedirect(reverse('import_export_vote_smart:vote_smart_rating_list', args=()))


def import_one_group_ratings_view(request, special_interest_group_id):
    one_group_results = retrieve_vote_smart_ratings_by_group_into_local_db(special_interest_group_id)

    if one_group_results['success']:
        messages.add_message(request, messages.INFO, "Ratings from Special Interest Group retrieved. ")
    else:
        messages.add_message(request, messages.ERROR, "Ratings from Special Interest Group NOT retrieved. "
                                                      "(error: {error_message})"
                                                      "".format(error_message=one_group_results['status']))

    return HttpResponseRedirect(reverse('import_export_vote_smart:special_interest_group_rating_list',
                                        args=(special_interest_group_id,)))


# @login_required()  # Commented out while we are developing login process()
def import_states_view(request):
    """
    """
    retrieve_and_save_vote_smart_states()

    template_values = {
        'state_list': VoteSmartState.objects.order_by('name'),
    }
    return render(request, 'import_export_vote_smart/vote_smart_import.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def import_photo_view(request):
    # NOTE: This view is for testing purposes. For the operational "Import Vote Smart Images" view, see:
    #  "candidate_retrieve_photos_view" in candidate/views_admin.py
    last_name = "Trump"
    results = retrieve_vote_smart_candidates_into_local_db(last_name)
    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        messages.add_message(request, messages.INFO, "Photo retrieved.")

        # Now we can go on to make sure we have the right VoteSmartCandidate
        vote_smart_candidate_id = 15723
        # ...and then retrieve the photo
        results = retrieve_vote_smart_candidate_bio_into_local_db(vote_smart_candidate_id)

    last_name = "Pelosi"
    results = retrieve_vote_smart_officials_into_local_db(last_name)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'import_export_vote_smart/vote_smart_import.html', template_values)


def import_special_interest_groups_view(request):
    # state_code = request.GET.get('state_code', 'NA')  # Default to national
    # category_id = request.GET.get('category_id', 0)

    # First retrieve an index of all groups for each state and category
    group_count = 0
    error_message_count = 0
    position_category_list = VoteSmartCategory.objects.order_by('name')
    for position_category in position_category_list:
        category_id = position_category.categoryId

        for state_code, state_name in STATE_CODE_MAP.items():
            results = retrieve_vote_smart_special_interest_groups_into_local_db(category_id, state_code)

            if not results['success']:
                # messages.add_message(request, messages.INFO, results['status'])
                print_to_log(logger=logger, exception_message_optional=results['status'])
                error_message_count += 1
            else:
                group_count += 1

    messages.add_message(request, messages.INFO, "{group_count} Special Interest Groups retrieved. "
                                                 "(errors: {error_message_count})"
                                                 "".format(group_count=group_count,
                                                           error_message_count=error_message_count))

    # Then retrieve the details about each group
    get_sig_group_count = 0
    get_sig_error_message_count = 0
    special_interest_group_list = VoteSmartSpecialInterestGroup.objects.order_by('name')
    for one_group in special_interest_group_list:
        special_interest_group_id = one_group.sigId
        one_group_results = retrieve_vote_smart_special_interest_group_into_local_db(special_interest_group_id)

        if not one_group_results['success']:
            print_to_log(logger=logger, exception_message_optional=one_group_results['status'])
            get_sig_error_message_count += 1
        else:
            get_sig_group_count += 1

    messages.add_message(request, messages.INFO, "{get_sig_group_count} Special Interest Groups augmented. "
                                                 "(errors: {get_sig_error_message_count})"
                                                 "".format(get_sig_group_count=get_sig_group_count,
                                                           get_sig_error_message_count=get_sig_error_message_count))

    return HttpResponseRedirect(reverse('import_export_vote_smart:vote_smart_special_interest_group_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def vote_smart_rating_list_view(request):
    messages_on_stage = get_messages(request)
    rating_list_found = False
    try:
        rating_list = VoteSmartRating.objects.order_by('-timeSpan')[:1000]  # Descending order, and limited to 1000
        if len(rating_list):
            rating_list_found = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        print_to_log(logger=logger, exception_message_optional=status)

    # election_list = Election.objects.order_by('-election_day_text')

    if rating_list_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'rating_list': rating_list,
            # 'election_list': election_list,
            # 'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
            # 'election_list': election_list,
            # 'google_civic_election_id': google_civic_election_id,
        }
    return render(request, 'import_export_vote_smart/rating_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def special_interest_group_rating_list_view(request, special_interest_group_id):
    messages_on_stage = get_messages(request)
    special_interest_group_id = convert_to_int(special_interest_group_id)
    # google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    special_interest_group_found = False
    try:
        special_interest_group_query = VoteSmartSpecialInterestGroup.objects.filter(sigId=special_interest_group_id)
        if special_interest_group_query.count():
            special_interest_group = special_interest_group_query[0]
            special_interest_group_found = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        print_to_log(logger=logger, exception_message_optional=status)
        special_interest_group_found = False

    if not special_interest_group_found:
        messages.add_message(request, messages.ERROR,
                             'Could not find special_interest_group when trying to retrieve ratings.')
        return HttpResponseRedirect(reverse('import_export_vote_smart:vote_smart_special_interest_group_list', args=()))
    else:
        rating_list_found = False
        try:
            rating_list = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')
            rating_list = rating_list.filter(sigId=special_interest_group_id)
            if len(rating_list):
                rating_list_found = True
        except VotesmartApiError as error_instance:
            # Catch the error message coming back from Vote Smart and pass it in the status
            error_message = error_instance.args
            status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
            print_to_log(logger=logger, exception_message_optional=status)

        # election_list = Election.objects.order_by('-election_day_text')

        if rating_list_found:
            template_values = {
                'messages_on_stage': messages_on_stage,
                'special_interest_group': special_interest_group,
                'rating_list': rating_list,
                # 'election_list': election_list,
                # 'google_civic_election_id': google_civic_election_id,
            }
        else:
            template_values = {
                'messages_on_stage': messages_on_stage,
                'special_interest_group': special_interest_group,
                # 'election_list': election_list,
                # 'google_civic_election_id': google_civic_election_id,
            }
    return render(request, 'import_export_vote_smart/group_rating_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def vote_smart_special_interest_group_list_view(request):
    messages_on_stage = get_messages(request)

    special_interest_group_list = VoteSmartSpecialInterestGroup.objects.order_by('name')

    template_values = {
        'messages_on_stage': messages_on_stage,

        'special_interest_group_list': special_interest_group_list,
    }
    return render(request, 'import_export_vote_smart/special_interest_group_list.html', template_values)


def import_vote_smart_position_categories_view(request):
    results = retrieve_vote_smart_position_categories_into_local_db()
    if not results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        messages.add_message(request, messages.INFO, "Categories retrieved.")

    return HttpResponseRedirect(reverse('import_export_vote_smart:vote_smart_position_category_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def vote_smart_position_category_list_view(request):
    messages_on_stage = get_messages(request)

    position_category_list = VoteSmartCategory.objects.order_by('name')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'position_category_list': position_category_list,
    }
    return render(request, 'import_export_vote_smart/position_category_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def state_detail_view(request, pk):
    """
    """
    state_id = pk

    template_values = {
        'state': VoteSmartState.objects.get(stateId=state_id),
    }
    return render(request, 'import_export_vote_smart/state_detail.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def vote_smart_index_view(request):
    """
    """

    template_values = {
    }
    return render(request, 'import_export_vote_smart/index.html', template_values)
