# candidate/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import candidates_import_from_master_server, candidates_import_from_sample_file, \
    retrieve_candidate_photos
from .models import CandidateCampaign, CandidateCampaignListManager, CandidateCampaignManager
from .serializers import CandidateCampaignSerializer
from admin_tools.views import redirect_to_sign_in_page
from office.models import ContestOffice, ContestOfficeManager
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election, ElectionManager
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception, print_to_log
from import_export_vote_smart.models import VoteSmartRatingOneCandidate
from import_export_vote_smart.votesmart_local import VotesmartApiError
from position.models import PositionEntered, PositionListManager
from rest_framework.views import APIView
from rest_framework.response import Response
from voter.models import voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, \
    positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
class CandidatesSyncOutView(APIView):
    def get(self, request, format=None):
        google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

        candidate_list = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)

        serializer = CandidateCampaignSerializer(candidate_list, many=True)
        return Response(serializer.data)


@login_required
def candidates_import_from_master_server_view(request):
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    results = candidates_import_from_master_server(request, google_civic_election_id)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Candidates import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Master data not imported (local duplicates found): '
                                                     '{duplicates_removed}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               duplicates_removed=results['duplicates_removed'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:sync_dashboard', args=()) + "?google_civic_election_id=" +
                                str(google_civic_election_id) + "&state_code=" + str(state_code))


@login_required
def candidates_import_from_sample_file_view(request):
    """
    This gives us sample organizations, candidate campaigns, and positions for testing
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # We are importing candidate_campaigns data (and not politician data) because all we are doing is making sure we
    #  sync to the same We Vote ID. This is critical so we can link Positions to Organization & Candidate Campaign.
    # At this point (June 2015) we assume the politicians have been imported from Google Civic. We aren't assigning
    # the politicians a We Vote id, but instead use their full name as the identifier
    candidates_import_from_sample_file(request, False)

    messages.add_message(request, messages.INFO, 'Candidates imported.')

    return HttpResponseRedirect(reverse('import_export:import_export_index', args=()))


@login_required
def candidate_list_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    candidate_list = []

    try:
        candidate_list = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
        candidate_list = candidate_list.order_by('candidate_name')[:500]
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage': messages_on_stage,
        'candidate_list': candidate_list,
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
    }
    return render(request, 'candidate/candidate_list.html', template_values)


@login_required
def candidate_new_view(request):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    contest_office_id = request.GET.get('contest_office_id', 0)

    # These are the Offices already entered for this election
    try:
        contest_office_list = ContestOffice.objects.order_by('office_name')
        contest_office_list = contest_office_list.filter(google_civic_election_id=google_civic_election_id)
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)
        contest_office_list = []

    # Its helpful to see existing candidates when entering a new candidate
    candidate_list = []
    try:
        candidate_list = CandidateCampaign.objects.all()
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(contest_office_id):
            candidate_list = candidate_list.filter(contest_office_id=contest_office_id)
        candidate_list = candidate_list.order_by('candidate_name')[:500]
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    messages_on_stage = get_messages(request)
    template_values = {
        'messages_on_stage':        messages_on_stage,
        'office_list':              contest_office_list,
        'contest_office_id':        contest_office_id,
        'google_civic_election_id': google_civic_election_id,
        'candidate_list':           candidate_list,
    }
    return render(request, 'candidate/candidate_edit.html', template_values)


@login_required
def candidate_edit_view(request, candidate_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    candidate_id = convert_to_int(candidate_id)
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    contest_office_id = 0
    google_civic_election_id = 0

    try:
        candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
        candidate_on_stage_found = True
        contest_office_id = candidate_on_stage.contest_office_id
        google_civic_election_id = candidate_on_stage.google_civic_election_id
    except CandidateCampaign.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new below
        pass

    if candidate_on_stage_found:
        # Working with Vote Smart data
        try:
            vote_smart_candidate_id = candidate_on_stage.vote_smart_id
            rating_list_query = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')  # Desc order
            rating_list = rating_list_query.filter(candidateId=vote_smart_candidate_id)
        except VotesmartApiError as error_instance:
            # Catch the error message coming back from Vote Smart and pass it in the status
            error_message = error_instance.args
            status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
            print_to_log(logger=logger, exception_message_optional=status)
            rating_list = []

        # Working with We Vote Positions
        try:
            candidate_position_list = PositionEntered.objects.order_by('stance')
            candidate_position_list = candidate_position_list.filter(candidate_campaign_id=candidate_id)
            # if positive_value_exists(google_civic_election_id):
            #     organization_position_list = candidate_position_list.filter(
            #         google_civic_election_id=google_civic_election_id)
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            candidate_position_list = []

        # Working with Offices for this election
        try:
            contest_office_list = ContestOffice.objects.order_by('office_name')
            contest_office_list = contest_office_list.filter(
                google_civic_election_id=candidate_on_stage.google_civic_election_id)
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            contest_office_list = []

        template_values = {
            'messages_on_stage':        messages_on_stage,
            'candidate':                candidate_on_stage,
            'rating_list':              rating_list,
            'candidate_position_list':  candidate_position_list,
            'office_list':              contest_office_list,
            'contest_office_id':        contest_office_id,
            'google_civic_election_id': google_civic_election_id,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'candidate/candidate_edit.html', template_values)


@login_required
def candidate_edit_process_view(request):
    """
    Process the new or edit candidate forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(request.POST['candidate_id'])
    candidate_name = request.POST.get('candidate_name', False)
    candidate_twitter_handle = request.POST.get('candidate_twitter_handle', False)
    if positive_value_exists(candidate_twitter_handle):
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
    candidate_url = request.POST.get('candidate_url', False)
    contest_office_id = request.POST.get('contest_office_id', False)
    ballot_guide_official_statement = request.POST.get('ballot_guide_official_statement', False)
    party = request.POST.get('party', False)

    remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)

    # Check to see if this candidate is already being used anywhere
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    if positive_value_exists(candidate_id):
        try:
            candidate_query = CandidateCampaign.objects.filter(id=candidate_id)
            if len(candidate_query):
                candidate_on_stage = candidate_query[0]
                candidate_on_stage_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

    contest_office_we_vote_id = ''
    if positive_value_exists(contest_office_id):
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office_from_id(contest_office_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_we_vote_id = contest_office.we_vote_id

    try:
        if candidate_on_stage_found:
            # Update
            if candidate_twitter_handle is not False:
                candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
            if candidate_url is not False:
                candidate_on_stage.candidate_url = candidate_url
            if ballot_guide_official_statement is not False:
                candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
            if party is not False:
                candidate_on_stage.party = party

            # Check to see if this is a We Vote-created election
            # is_we_vote_google_civic_election_id = True \
            #     if convert_to_int(candidate_on_stage.google_civic_election_id) >= 1000000 \
            #     else False

            if contest_office_id is not False:
                # We only allow updating of candidates within the We Vote Admin in
                candidate_on_stage.contest_office_id = contest_office_id
                candidate_on_stage.contest_office_we_vote_id = contest_office_we_vote_id
            candidate_on_stage.save()
            messages.add_message(request, messages.INFO, 'Candidate Campaign updated.')
        else:
            # Create new
            # election must be found
            election_manager = ElectionManager()
            election_results = election_manager.retrieve_election(google_civic_election_id)
            if election_results['election_found']:
                election = election_results['election']
                state_code = election.get_election_state()
            else:
                messages.add_message(request, messages.ERROR, 'Could not find election -- required to save candidate.')
                return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

            required_candidate_variables = True \
                if positive_value_exists(candidate_name) and positive_value_exists(contest_office_id) \
                else False
            if required_candidate_variables:
                candidate_on_stage = CandidateCampaign(
                    candidate_name=candidate_name,
                    google_civic_election_id=google_civic_election_id,
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    state_code=state_code,
                )
                if candidate_twitter_handle is not False:
                    candidate_on_stage.candidate_twitter_handle = candidate_twitter_handle
                if candidate_url is not False:
                    candidate_on_stage.candidate_url = candidate_url
                if ballot_guide_official_statement is not False:
                    candidate_on_stage.ballot_guide_official_statement = ballot_guide_official_statement
                if party is not False:
                    candidate_on_stage.party = party
                candidate_on_stage.save()
                candidate_id = candidate_on_stage.id
                messages.add_message(request, messages.INFO, 'New candidate saved.')
            else:
                messages.add_message(request, messages.INFO, 'Could not save -- missing required variables.')
                if positive_value_exists(candidate_id):
                    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)) +
                                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                                "&contest_office_id=" + str(contest_office_id)
                                                )
                else:
                    return HttpResponseRedirect(reverse('candidate:candidate_new', args=()) +
                                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                                "&contest_office_id=" + str(contest_office_id)
                                                )

    except Exception as e:
        handle_record_not_saved_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'Could not save candidate.')
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    if remove_duplicate_process:
        return HttpResponseRedirect(reverse('candidate:find_and_remove_duplicate_candidates', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))
    else:
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))


@login_required
def candidate_retrieve_photos_view(request, candidate_id):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(candidate_id)
    force_retrieve = request.GET.get('force_retrieve', 0)

    candidate_campaign_manager = CandidateCampaignManager()

    results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_id)
    if not positive_value_exists(results['candidate_campaign_found']):
        messages.add_message(request, messages.ERROR,
                             "Candidate '{candidate_id}' not found.".format(candidate_id=candidate_id))
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    we_vote_candidate = results['candidate_campaign']

    display_messages = True
    retrieve_candidate_results = retrieve_candidate_photos(we_vote_candidate, force_retrieve)

    if retrieve_candidate_results['status'] and display_messages:
        messages.add_message(request, messages.INFO, retrieve_candidate_results['status'])
    return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))


@login_required
def find_and_remove_duplicate_candidates_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_list = []
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)

    number_of_duplicate_candidates_processed = 0
    number_of_duplicate_candidates_failed = 0
    number_of_duplicates_could_not_process = 0

    # TODO DALE Consider moving to candidate_campaign_list.find_and_remove_duplicate_candidates ?

    # We only want to process if a google_civic_election_id comes in
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()))

    try:
        # We sort by ID so that the entry which was saved first becomes the "master"
        candidate_list = CandidateCampaign.objects.order_by('id')
        candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
    except CandidateCampaign.DoesNotExist:
        pass

    # Loop through all of the candidates in this election
    candidate_campaign_list_manager = CandidateCampaignListManager()
    for we_vote_candidate in candidate_list:
        # Search for other candidates within this election that match name and election
        try:
            candidate_duplicates_query = CandidateCampaign.objects.order_by('candidate_name')
            candidate_duplicates_query = candidate_duplicates_query.filter(
                google_civic_election_id=google_civic_election_id)
            candidate_duplicates_query = candidate_duplicates_query.filter(
                candidate_name=we_vote_candidate.candidate_name)
            candidate_duplicates_query = candidate_duplicates_query.exclude(id=we_vote_candidate.id)
            number_of_duplicates = candidate_duplicates_query.count()
            if number_of_duplicates > 1:
                # Our system can't deal with this yet
                number_of_duplicates_could_not_process += 1
                pass
            elif number_of_duplicates == 1:
                candidate_duplicate_list = candidate_duplicates_query

                # If we can automatically merge, we should do it
                is_automatic_merge_ok_results = candidate_campaign_list_manager.is_automatic_merge_ok(
                    we_vote_candidate, candidate_duplicate_list[0])
                if is_automatic_merge_ok_results['automatic_merge_ok']:
                    automatic_merge_results = candidate_campaign_list_manager.do_automatic_merge(
                        we_vote_candidate, candidate_duplicate_list[0])
                    if automatic_merge_results['success']:
                        number_of_duplicate_candidates_processed += 1
                    else:
                        number_of_duplicate_candidates_failed += 1
                else:
                    # If we cannot automatically merge, direct to a page where we can look at the two side-by-side
                    message = "Google Civic Election ID: {election_id}, " \
                              "{num_of_duplicate_candidates_processed} duplicates processed, " \
                              "{number_of_duplicate_candidates_failed} duplicate merges failed, " \
                              "{number_of_duplicates_could_not_process} could not be processed because 3 exist " \
                              "".format(election_id=google_civic_election_id,
                                        num_of_duplicate_candidates_processed=number_of_duplicate_candidates_processed,
                                        number_of_duplicate_candidates_failed=number_of_duplicate_candidates_failed,
                                        number_of_duplicates_could_not_process=number_of_duplicates_could_not_process)

                    messages.add_message(request, messages.INFO, message)

                    message = "{is_automatic_merge_ok_results_status} " \
                              "".format(is_automatic_merge_ok_results_status=is_automatic_merge_ok_results['status'])
                    messages.add_message(request, messages.ERROR, message)

                    messages_on_stage = get_messages(request)
                    template_values = {
                        'messages_on_stage': messages_on_stage,
                        'candidate_option1': we_vote_candidate,
                        'candidate_option2': candidate_duplicate_list[0],
                    }
                    return render(request, 'candidate/candidate_merge.html', template_values)

        except CandidateCampaign.DoesNotExist:
            pass

    message = "Google Civic Election ID: {election_id}, " \
              "{number_of_duplicate_candidates_processed} duplicates processed, " \
              "{number_of_duplicate_candidates_failed} duplicate merges failed, " \
              "{number_of_duplicates_could_not_process} could not be processed because 3 exist " \
              "".format(election_id=google_civic_election_id,
                        number_of_duplicate_candidates_processed=number_of_duplicate_candidates_processed,
                        number_of_duplicate_candidates_failed=number_of_duplicate_candidates_failed,
                        number_of_duplicates_could_not_process=number_of_duplicates_could_not_process)

    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}".format(
        var=google_civic_election_id))


@login_required
def remove_duplicate_candidate_view(request):
    """
    We use this view to semi-automate the process of finding candidate duplicates. Exact
    copies can be deleted automatically, and similar entries can be manually reviewed and deleted.
    :param request:
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    candidate_id = request.GET.get('candidate_id', 0)

    remove_duplicate_process = request.GET.get('remove_duplicate_process', False)

    missing_variables = False

    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        missing_variables = True
    if not positive_value_exists(candidate_id):
        messages.add_message(request, messages.ERROR, "Candidate ID required.")
        missing_variables = True

    if missing_variables:
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}"
                                                                                   "".format(
            var=google_civic_election_id))

    candidate_campaign_list_manager = CandidateCampaignListManager()
    results = candidate_campaign_list_manager.remove_duplicate_candidate(candidate_id, google_civic_election_id)
    if results['success']:
        if remove_duplicate_process:
            # Continue this process
            return HttpResponseRedirect(reverse('candidate:find_and_remove_duplicate_candidates', args=()) +
                                        "?google_civic_election_id=" + google_civic_election_id)
        else:
            messages.add_message(request, messages.ERROR, results['status'])
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
    else:
        messages.add_message(request, messages.ERROR, "Could not remove candidate {candidate_id} '{candidate_name}'."
                                                      "".format(candidate_id=candidate_id,
                                                                candidate_name=candidate_id))  # TODO Add candidate_name
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}"
                                                                                   "".format(
            var=google_civic_election_id))


@login_required
def retrieve_candidate_photos_for_election_view(request, election_id):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_list = []
    google_civic_election_id = convert_to_int(election_id)

    # We only want to process if a google_civic_election_id comes in
    if not positive_value_exists(google_civic_election_id):
        messages.add_message(request, messages.ERROR, "Google Civic Election ID required.")
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()))

    try:
        candidate_list = CandidateCampaign.objects.order_by('candidate_name')
        if positive_value_exists(google_civic_election_id):
            candidate_list = candidate_list.filter(google_civic_election_id=google_civic_election_id)
    except CandidateCampaign.DoesNotExist:
        pass

    display_messages_per_candidate = False
    force_retrieve = False
    num_candidates_reviewed = 0
    num_with_vote_smart_ids = 0
    num_candidates_just_retrieved = 0

    num_with_vote_smart_photos = 0
    num_candidate_photos_just_retrieved = 0

    message = "About to loop through all of the candidates in this election and retrieve photos."
    print_to_log(logger, exception_message_optional=message)

    # Loop through all of the candidates in this election
    for we_vote_candidate in candidate_list:
        num_candidates_reviewed += 1
        retrieve_candidate_results = retrieve_candidate_photos(we_vote_candidate, force_retrieve)
        if retrieve_candidate_results['vote_smart_candidate_exists']:
            num_with_vote_smart_ids += 1
        if retrieve_candidate_results['vote_smart_candidate_just_retrieved']:
            num_candidates_just_retrieved += 1

        if retrieve_candidate_results['vote_smart_candidate_photo_exists']:
            num_with_vote_smart_photos += 1
        if retrieve_candidate_results['vote_smart_candidate_photo_just_retrieved']:
            num_candidate_photos_just_retrieved += 1

        if retrieve_candidate_results['status'] and display_messages_per_candidate:
            messages.add_message(request, messages.INFO, retrieve_candidate_results['status'])

    message = "Google Civic Election ID: {election_id}, " \
              "{num_candidates_reviewed} candidates reviewed, " \
              "{num_with_vote_smart_ids} with Vote Smart Ids, " \
              "{num_candidates_just_retrieved} candidates just retrieved, " \
              "{num_with_vote_smart_photos} with Vote Smart Photos, and " \
              "{num_candidate_photos_just_retrieved} photos just retrieved.".\
        format(election_id=google_civic_election_id,
               num_candidates_reviewed=num_candidates_reviewed,
               num_with_vote_smart_ids=num_with_vote_smart_ids,
               num_candidates_just_retrieved=num_candidates_just_retrieved,
               num_with_vote_smart_photos=num_with_vote_smart_photos,
               num_candidate_photos_just_retrieved=num_candidate_photos_just_retrieved)

    print_to_log(logger, exception_message_optional=message)
    messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) + "?google_civic_election_id={var}".format(
        var=google_civic_election_id))


@login_required
def candidate_summary_view(request, candidate_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    candidate_id = convert_to_int(candidate_id)
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    try:
        candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
        candidate_on_stage_found = True
    except CandidateCampaign.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except CandidateCampaign.DoesNotExist:
        # This is fine, create new
        pass

    if candidate_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'candidate': candidate_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'candidate/candidate_summary.html', template_values)


@login_required
def candidate_delete_process_view(request):
    """
    Delete this candidate
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    candidate_id = convert_to_int(request.GET.get('candidate_id', 0))
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    # Retrieve this candidate
    candidate_on_stage_found = False
    candidate_on_stage = CandidateCampaign()
    if positive_value_exists(candidate_id):
        try:
            candidate_query = CandidateCampaign.objects.filter(id=candidate_id)
            if len(candidate_query):
                candidate_on_stage = candidate_query[0]
                candidate_on_stage_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not find candidate -- exception.')

    if not candidate_on_stage_found:
        messages.add_message(request, messages.ERROR, 'Could not find candidate.')
        return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    # Are there any positions attached to this candidate that should be moved to another
    # instance of this candidate?
    position_list_manager = PositionListManager()
    position_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(candidate_id)
    if positive_value_exists(len(position_list)):
        positions_found_for_this_candidate = True
    else:
        positions_found_for_this_candidate = False

    try:
        if not positions_found_for_this_candidate:
            # Delete the candidate
            candidate_on_stage.delete()
            messages.add_message(request, messages.INFO, 'Candidate Campaign deleted.')
        else:
            messages.add_message(request, messages.ERROR, 'Could not delete -- '
                                                          'positions still attached to this candidate.')
            return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not delete candidate -- exception.')
        return HttpResponseRedirect(reverse('candidate:candidate_edit', args=(candidate_id,)))

    return HttpResponseRedirect(reverse('candidate:candidate_list', args=()) +
                                "?google_civic_election_id=" + str(google_civic_election_id))
