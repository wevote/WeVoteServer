# quick_info/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import LANGUAGE_CHOICES, QuickInfo, QuickInfoManager, \
    QuickInfoMaster, QuickInfoMasterManager, \
    SPANISH, ENGLISH, TAGALOG, VIETNAMESE, CHINESE, \
    NOT_SPECIFIED
from ballot.models import OFFICE, CANDIDATE, POLITICIAN, MEASURE, KIND_OF_BALLOT_ITEM_CHOICES
from .serializers import QuickInfoSerializer, QuickInfoMasterSerializer
from candidate.models import CandidateCampaign, CandidateCampaignManager
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
# from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from election.models import Election
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from measure.models import ContestMeasure, ContestMeasureManager
from office.models import ContestOffice, ContestOfficeManager
from rest_framework.views import APIView
from rest_framework.response import Response
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: login_required() throws an error. Needs to be figured out if we ever want to secure this page.
class ExportQuickInfoDataView(APIView):
    def get(self, request, format=None):
        quick_info_list = QuickInfo.objects.all()
        serializer = QuickInfoSerializer(quick_info_list, many=True)
        return Response(serializer.data)


class ExportQuickInfoMasterDataView(APIView):
    def get(self, request, format=None):
        quick_info_master_list = QuickInfoMaster.objects.all()
        serializer = QuickInfoMasterSerializer(quick_info_master_list, many=True)
        return Response(serializer.data)


# @login_required()  # Commented out while we are developing login process()
def quick_info_list_view(request):
    messages_on_stage = get_messages(request)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', '')
    language = request.GET.get('language', '')

    quick_info_list = QuickInfo.objects.order_by('id')  # This order_by is temp
    if positive_value_exists(google_civic_election_id):
        quick_info_list = QuickInfo.objects.filter(google_civic_election_id=google_civic_election_id)
    if positive_value_exists(kind_of_ballot_item):
        # Only return entries where the corresponding field has a We Vote id value in it.
        if kind_of_ballot_item == OFFICE:
            quick_info_list = QuickInfo.objects.filter(contest_office_we_vote_id__startswith='wv')
        elif kind_of_ballot_item == CANDIDATE:
            quick_info_list = QuickInfo.objects.filter(candidate_campaign_we_vote_id__startswith='wv')
        elif kind_of_ballot_item == POLITICIAN:
            quick_info_list = QuickInfo.objects.filter(politician_we_vote_id__startswith='wv')
        elif kind_of_ballot_item == MEASURE:
            quick_info_list = QuickInfo.objects.filter(contest_measure_we_vote_id__startswith='wv')
    if positive_value_exists(language):
        quick_info_list = QuickInfo.objects.filter(language=language)

    election_list = Election.objects.order_by('-election_day_text')

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'quick_info_list':          quick_info_list,
        'election_list':            election_list,
        'google_civic_election_id': google_civic_election_id,
        'language_choices':         LANGUAGE_CHOICES,
        'language':                 language,
        'ballot_item_choices':      KIND_OF_BALLOT_ITEM_CHOICES,
        'kind_of_ballot_item':      kind_of_ballot_item,
    }
    return render(request, 'quick_info/quick_info_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_new_view(request):
    # If the voter tried to submit an entry, and it didn't save, capture the changed values for display
    language = request.POST.get('language', ENGLISH)
    info_text = request.POST.get('info_text', "")
    info_html = request.POST.get('info_html', "")
    ballot_item_display_name = request.POST.get('ballot_item_display_name', "")
    more_info_credit = request.POST.get('more_info_credit', "")
    more_info_url = request.POST.get('more_info_url', "")

    contest_office_we_vote_id = request.POST.get('contest_office_we_vote_id', "")
    candidate_campaign_we_vote_id = request.POST.get('candidate_campaign_we_vote_id', "")
    politician_we_vote_id = request.POST.get('politician_we_vote_id', "")
    contest_measure_we_vote_id = request.POST.get('contest_measure_we_vote_id', "")

    quick_info_master_we_vote_id = request.POST.get('quick_info_master_we_vote_id', "")
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    if positive_value_exists(google_civic_election_id):
        election_found = True
    else:
        election_found = False

    # Do we want to use master text (used across multiple ballot items), or text unique to one ballot item
    use_master_entry = request.POST.get('use_master_entry', True)  # Default is "use master entry"
    use_master_entry = positive_value_exists(use_master_entry)

    # ##################################
    # Above we have dealt with data provided by prior submit
    election_list = Election.objects.order_by('-election_day_text')

    quick_info = QuickInfo()
    quick_info.language = language
    # See below: quick_info.info_text = info_text
    # See below: quick_info.info_html = info_html
    quick_info.ballot_item_display_name = ballot_item_display_name
    quick_info.contest_office_we_vote_id = contest_office_we_vote_id
    quick_info.candidate_campaign_we_vote_id = candidate_campaign_we_vote_id
    quick_info.politician_we_vote_id = politician_we_vote_id
    quick_info.contest_measure_we_vote_id = contest_measure_we_vote_id
    # See below: quick_info.quick_info_master_we_vote_id = quick_info_master_we_vote_id
    quick_info.google_civic_election_id = google_civic_election_id

    if use_master_entry:
        quick_info.quick_info_master_we_vote_id = quick_info_master_we_vote_id
        # Retrieve the quick_info_master being used by this quick_info entry
        quick_info_master_manager = QuickInfoMasterManager()
        results = quick_info_master_manager.retrieve_quick_info_master_from_we_vote_id(
            quick_info.quick_info_master_we_vote_id)
        if positive_value_exists(results['success']):
            quick_info_master = results['quick_info_master']
        else:
            quick_info_master = QuickInfoMaster()
        # When in the other state (unique entry for this ballot item), we cache the info_text value in a hidden field
    else:
        quick_info.info_text = info_text
        quick_info.info_html = info_html
        quick_info.more_info_credit = more_info_credit
        quick_info.more_info_url = more_info_url
        quick_info_master = QuickInfoMaster()
        # When in the other state (unique entry for this ballot item), we cache the quick_info_master_we_vote_id value
        # in a hidden field

    contest_office_options = ContestOffice.objects.order_by('office_name')
    if positive_value_exists(google_civic_election_id):
        contest_office_options = contest_office_options.filter(google_civic_election_id=google_civic_election_id)

    candidate_campaign_options = CandidateCampaign.objects.order_by('candidate_name')
    if positive_value_exists(google_civic_election_id):
        candidate_campaign_options = candidate_campaign_options.filter(google_civic_election_id=google_civic_election_id)

    contest_measure_options = ContestMeasure.objects.order_by('measure_title')
    if positive_value_exists(google_civic_election_id):
        contest_measure_options = contest_measure_options.filter(google_civic_election_id=google_civic_election_id)

    quick_info_master_list = QuickInfoMaster.objects.order_by('id')  # This order_by is temp
    kind_of_ballot_item = quick_info.get_kind_of_ballot_item()
    if positive_value_exists(kind_of_ballot_item):
        quick_info_master_list = quick_info_master_list.filter(kind_of_ballot_item=kind_of_ballot_item)
    if positive_value_exists(language):
        quick_info_master_list = quick_info_master_list.filter(language=language)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'contest_office_options':       contest_office_options,
        'candidate_campaign_options':   candidate_campaign_options,
        'contest_measure_options':      contest_measure_options,
        'election_list':                election_list,
        'election_found':               election_found,
        'language_choices':             LANGUAGE_CHOICES,
        'use_master_entry':             use_master_entry,  # Use "master", or enter text unique to this ballot item
        'quick_info':                   quick_info,
        'quick_info_master':            quick_info_master,
        'quick_info_master_list':       quick_info_master_list,
        'quick_info_master_we_vote_id': quick_info_master_we_vote_id,  # Cache this value on the page
        'info_text':                    info_text,  # Cache this value on the page
    }
    return render(request, 'quick_info/quick_info_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_edit_view(request, quick_info_id):
    form_submitted = request.POST.get('form_submitted', False)
    quick_info_id = convert_to_int(quick_info_id)

    try:
        quick_info = QuickInfo.objects.get(id=quick_info_id)
    except QuickInfo.MultipleObjectsReturned as e:
        # Pretty unlikely that multiple objects have the same id
        messages.add_message(request, messages.ERROR, "This quick_info_id has multiple records.")
        return HttpResponseRedirect(reverse('quick_info:quick_info_list', args=()))
    except QuickInfo.DoesNotExist:
        # This is fine, create new entry
        return quick_info_new_view(request)

    change_election = request.POST.get('change_election', '0')  # *Just* switch the election we are looking at
    change_language = request.POST.get('change_language', '0')  # *Just* switch to different language
    change_text_vs_master = request.POST.get('change_text_vs_master', '0')  # *Just* switch between text entry & master
    change_quick_info_master = request.POST.get('change_quick_info_master', '0')  # *Just* update master display

    if positive_value_exists(form_submitted) or positive_value_exists(change_election) or \
            positive_value_exists(change_language) or positive_value_exists(change_text_vs_master) or \
            positive_value_exists(change_quick_info_master):
        # If the voter tried to submit an entry, and it didn't save, capture the changed values for display
        language = request.POST.get('language', False)
        info_text = request.POST.get('info_text', False)
        info_html = request.POST.get('info_html', False)
        ballot_item_display_name = request.POST.get('ballot_item_display_name', False)
        more_info_credit = request.POST.get('more_info_credit', False)
        more_info_url = request.POST.get('more_info_url', False)

        contest_office_we_vote_id = request.POST.get('contest_office_we_vote_id', False)
        candidate_campaign_we_vote_id = request.POST.get('candidate_campaign_we_vote_id', False)
        politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
        contest_measure_we_vote_id = request.POST.get('contest_measure_we_vote_id', False)

        quick_info_master_we_vote_id = request.POST.get('quick_info_master_we_vote_id', False)
        google_civic_election_id = request.POST.get('google_civic_election_id', False)

        # Do we want to use master text (used across multiple ballot items), or text unique to one ballot item
        use_master_entry = request.POST.get('use_master_entry', True)  # Default is "use master entry"
        use_master_entry = positive_value_exists(use_master_entry)

        # Write over the fields where a change has been made on the form
        if language is not False:
            quick_info.language = language
        # See below: quick_info.info_text = info_text
        # See below: quick_info.info_html = info_html
        if ballot_item_display_name is not False:
            quick_info.ballot_item_display_name = ballot_item_display_name
        if more_info_credit is not False:
            quick_info.more_info_credit = more_info_credit
        if more_info_url is not False:
            quick_info.more_info_url = more_info_url
        if contest_office_we_vote_id is not False:
            quick_info.contest_office_we_vote_id = contest_office_we_vote_id
        if candidate_campaign_we_vote_id is not False:
            quick_info.candidate_campaign_we_vote_id = candidate_campaign_we_vote_id
        if politician_we_vote_id is not False:
            quick_info.politician_we_vote_id = politician_we_vote_id
        if contest_measure_we_vote_id is not False:
            quick_info.contest_measure_we_vote_id = contest_measure_we_vote_id
        # See below: quick_info.quick_info_master_we_vote_id = quick_info_master_we_vote_id
        if google_civic_election_id is not False:
            quick_info.google_civic_election_id = google_civic_election_id

        if use_master_entry:
            if quick_info_master_we_vote_id is not False:
                quick_info.quick_info_master_we_vote_id = quick_info_master_we_vote_id
            # Retrieve the quick_info_master being used by this quick_info entry
            quick_info_master_manager = QuickInfoMasterManager()
            results = quick_info_master_manager.retrieve_quick_info_master_from_we_vote_id(
                quick_info.quick_info_master_we_vote_id)
            if positive_value_exists(results['success']):
                quick_info_master = results['quick_info_master']
            else:
                quick_info_master = QuickInfoMaster()
            # When in the other state (unique entry for this ballot item), we cache the info_text
            # value in a hidden field
        else:
            if info_text is not False:
                quick_info.info_text = info_text
            if info_html is not False:
                quick_info.info_html = info_html
            quick_info_master = QuickInfoMaster()
            # When in the other state (unique entry for this ballot item), we cache the
            # quick_info_master_we_vote_id value in a hidden field
    else:
        use_master_entry = positive_value_exists(quick_info.quick_info_master_we_vote_id) or not \
            (positive_value_exists(quick_info.info_text) or positive_value_exists(quick_info.info_html))
        quick_info_master_we_vote_id = quick_info.quick_info_master_we_vote_id
        # Retrieve the quick_info_master being used by this quick_info entry
        quick_info_master_manager = QuickInfoMasterManager()
        results = quick_info_master_manager.retrieve_quick_info_master_from_we_vote_id(
            quick_info.quick_info_master_we_vote_id)
        if positive_value_exists(results['success']):
            quick_info_master = results['quick_info_master']
        else:
            quick_info_master = QuickInfoMaster()
        info_text = quick_info.info_text
        language = quick_info.language

    # ##################################
    # Above we have dealt with data provided by prior submit
    election_list = Election.objects.order_by('-election_day_text')

    if positive_value_exists(quick_info.google_civic_election_id):
        election_found = True
    else:
        election_found = False

    contest_office_options = ContestOffice.objects.order_by('office_name')
    if positive_value_exists(quick_info.google_civic_election_id):
        contest_office_options = contest_office_options.filter(
            google_civic_election_id=quick_info.google_civic_election_id)

    candidate_campaign_options = CandidateCampaign.objects.order_by('candidate_name')
    if positive_value_exists(quick_info.google_civic_election_id):
        candidate_campaign_options = candidate_campaign_options.filter(
            google_civic_election_id=quick_info.google_civic_election_id)

    contest_measure_options = ContestMeasure.objects.order_by('measure_title')
    if positive_value_exists(quick_info.google_civic_election_id):
        contest_measure_options = contest_measure_options.filter(
            google_civic_election_id=quick_info.google_civic_election_id)

    quick_info_master_list = QuickInfoMaster.objects.order_by('id')  # This order_by is temp
    kind_of_ballot_item = quick_info.get_kind_of_ballot_item()
    if positive_value_exists(kind_of_ballot_item):
        quick_info_master_list = quick_info_master_list.filter(kind_of_ballot_item=kind_of_ballot_item)
    if positive_value_exists(language):
        quick_info_master_list = quick_info_master_list.filter(language=language)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'contest_office_options':       contest_office_options,
        'candidate_campaign_options':   candidate_campaign_options,
        'contest_measure_options':      contest_measure_options,
        'election_list':                election_list,
        'election_found':               election_found,
        'language_choices':             LANGUAGE_CHOICES,
        'use_master_entry':             use_master_entry,  # Use "master", or enter text unique to this ballot item
        'quick_info':                   quick_info,
        'quick_info_master':            quick_info_master,
        'quick_info_master_list':       quick_info_master_list,
        'quick_info_master_we_vote_id': quick_info_master_we_vote_id,  # Cache this value on the page
        'info_text':                    info_text,  # Cache this value on the page
    }
    return render(request, 'quick_info/quick_info_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_edit_process_view(request):
    """
    Process the new or edit quick_info forms
    :param request:
    :return:
    """
    quick_info_id = convert_to_int(request.POST.get('quick_info_id', False))
    quick_info_we_vote_id = convert_to_int(request.POST.get('quick_info_we_vote_id', False))

    language = request.POST.get('language', False)
    info_text = request.POST.get('info_text', False)
    info_html = request.POST.get('info_html', False)
    ballot_item_display_name = request.POST.get('ballot_item_display_name', False)
    more_info_credit = request.POST.get('more_info_credit', False)
    more_info_url = request.POST.get('more_info_url', False)

    contest_office_we_vote_id = request.POST.get('contest_office_we_vote_id', False)
    candidate_campaign_we_vote_id = request.POST.get('candidate_campaign_we_vote_id', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', False)
    contest_measure_we_vote_id = request.POST.get('contest_measure_we_vote_id', False)

    quick_info_master_we_vote_id = request.POST.get('quick_info_master_we_vote_id', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', False)

    change_election = request.POST.get('change_election', '0')  # *Just* switch the election we are looking at
    change_language = request.POST.get('change_language', '0')  # *Just* switch to different language
    use_unique_text = request.POST.get('use_unique_text', '0')
    use_master_entry = request.POST.get('use_master_entry', '0')
    change_text_vs_master = request.POST.get('change_text_vs_master', '0')  # *Just* switch between text entry & master
    change_quick_info_master = request.POST.get('change_quick_info_master', '0')  # *Just* update master display

    number_of_ballot_items = 0
    if positive_value_exists(contest_office_we_vote_id):
        number_of_ballot_items += 1
    if positive_value_exists(candidate_campaign_we_vote_id):
        number_of_ballot_items += 1
    if positive_value_exists(politician_we_vote_id):
        number_of_ballot_items += 1
    if positive_value_exists(contest_measure_we_vote_id):
        number_of_ballot_items += 1

    if positive_value_exists(change_election) or \
            positive_value_exists(change_language) or \
            positive_value_exists(change_text_vs_master) or \
            positive_value_exists(change_quick_info_master):
        # We are just changing an option, and not trying to save
        ready_to_save = False
    elif number_of_ballot_items is 0:
        messages.add_message(request, messages.ERROR, "You must choose at least one ballot item.")
        ready_to_save = False
    elif number_of_ballot_items > 1:
        messages.add_message(request, messages.ERROR, "Please choose only one ballot item.")
        ready_to_save = False
    # Do we have all of the required variables, unique to each mode?
    else:
        # If using a master entry
        if positive_value_exists(use_master_entry):
            if not positive_value_exists(quick_info_master_we_vote_id):
                messages.add_message(request, messages.ERROR, "Please choose a master entry for this ballot item.")
                ready_to_save = False
            else:
                ready_to_save = True
        # If entering text specific to this ballot item
        elif not positive_value_exists(use_master_entry) or positive_value_exists(use_unique_text):
            if not positive_value_exists(language):
                messages.add_message(request, messages.ERROR, "Please choose a language for your new entry.")
                ready_to_save = False
            elif not (positive_value_exists(info_text) or positive_value_exists(info_html)):
                messages.add_message(request, messages.ERROR,
                                     "Please enter the text/html information about this ballot item.")
                ready_to_save = False
            elif not positive_value_exists(more_info_url):
                messages.add_message(request, messages.ERROR, "Please enter the source URL for this description.")
                ready_to_save = False
            else:
                ready_to_save = True
        else:
            messages.add_message(request, messages.ERROR, "More information needed to save this entry.")
            ready_to_save = False

    if not ready_to_save:
        # Could we also just call the view directly with the request, instead of redirecting the browser?
        if positive_value_exists(quick_info_id):
            return quick_info_edit_view(request, quick_info_id)
            # return HttpResponseRedirect(reverse('quick_info:quick_info_edit', args=()) + url_variables)
        else:
            return quick_info_new_view(request)
            # return HttpResponseRedirect(reverse('quick_info:quick_info_new', args=()) + url_variables)

    # Now that we know we are ready to save, we want to wipe out the values we don't want to save
    if positive_value_exists(use_master_entry):
        info_html = ""
        info_text = ""
        more_info_url = ""
        more_info_credit = NOT_SPECIFIED
    else:
        quick_info_master_we_vote_id = ""

    # Figure out what text to use for the Ballot Item Label
    if not positive_value_exists(ballot_item_display_name):
        if positive_value_exists(contest_office_we_vote_id):
            contest_office_manager = ContestOfficeManager()
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office_we_vote_id)
            if results['success']:
                contest_office = results['contest_office']
                ballot_item_display_name = contest_office.office_name
            else:
                ballot_item_display_name = ''
        elif positive_value_exists(candidate_campaign_we_vote_id):
            candidate_campaign_manager = CandidateCampaignManager()
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                candidate_campaign_we_vote_id)
            if results['success']:
                candidate_campaign = results['candidate_campaign']
                ballot_item_display_name = candidate_campaign.candidate_name
            else:
                ballot_item_display_name = ''
        # if positive_value_exists(politician_we_vote_id):
        #     ballot_item_display_name = ''
        elif positive_value_exists(contest_measure_we_vote_id):
            contest_measure_manager = ContestMeasureManager()
            results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(contest_measure_we_vote_id)
            if results['success']:
                contest_measure = results['contest_measure']
                ballot_item_display_name = contest_measure.measure_title
            else:
                ballot_item_display_name = ""

    last_editor_we_vote_id = ""  # TODO We need to calculate this

    quick_info_manager = QuickInfoManager()
    results = quick_info_manager.update_or_create_quick_info(
        quick_info_id=quick_info_id,
        quick_info_we_vote_id=quick_info_we_vote_id,
        ballot_item_display_name=ballot_item_display_name,
        contest_office_we_vote_id=contest_office_we_vote_id,
        candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
        politician_we_vote_id=politician_we_vote_id,
        contest_measure_we_vote_id=contest_measure_we_vote_id,
        info_html=info_html,
        info_text=info_text,
        language=language,
        last_editor_we_vote_id=last_editor_we_vote_id,
        quick_info_master_we_vote_id=quick_info_master_we_vote_id,
        more_info_url=more_info_url,
        more_info_credit=more_info_credit,
        google_civic_election_id=google_civic_election_id
        )
    if results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        messages.add_message(request, messages.ERROR,
                             results['status'] + "language: {language}".format(
                                     language=language,
                             ))
        if positive_value_exists(quick_info_id):
            return quick_info_edit_view(request, quick_info_id)
        else:
            return quick_info_new_view(request)

    return HttpResponseRedirect(reverse('quick_info:quick_info_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def quick_info_summary_view(request, quick_info_id):  # TODO to be updated
    messages_on_stage = get_messages(request)
    quick_info_id = convert_to_int(quick_info_id)
    quick_info_on_stage_found = False
    quick_info_on_stage = QuickInfo()
    try:
        quick_info_on_stage = QuickInfo.objects.get(id=quick_info_id)
        quick_info_on_stage_found = True
    except QuickInfo.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except QuickInfo.DoesNotExist:
        # This is fine, create new
        pass

    if quick_info_on_stage_found:
        template_values = {
            'messages_on_stage': messages_on_stage,
            'quick_info': quick_info_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'quick_info/quick_info_summary.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_master_list_view(request):
    messages_on_stage = get_messages(request)
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    language = request.GET.get('language', ENGLISH)

    quick_info_master_list = QuickInfoMaster.objects.order_by('id')  # This order_by is temp
    if positive_value_exists(kind_of_ballot_item):
        quick_info_master_list = quick_info_master_list.filter(kind_of_ballot_item=kind_of_ballot_item)
    if positive_value_exists(language):
        quick_info_master_list = quick_info_master_list.filter(language=language)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'quick_info_master_list':   quick_info_master_list,
        'language_choices':         LANGUAGE_CHOICES,
        'ballot_item_choices':      KIND_OF_BALLOT_ITEM_CHOICES,
        'kind_of_ballot_item':      kind_of_ballot_item,
        'language':                 language,
    }
    return render(request, 'quick_info/quick_info_master_list.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_master_new_view(request):
    # If the voter tried to submit an entry, and it didn't save, capture the changed values for display
    kind_of_ballot_item = request.POST.get('kind_of_ballot_item', "")
    language = request.POST.get('language', ENGLISH)
    info_text = request.POST.get('info_text', "")
    info_html = request.POST.get('info_html', "")
    master_entry_name = request.POST.get('master_entry_name', "")
    more_info_credit = request.POST.get('more_info_credit', "")
    more_info_url = request.POST.get('more_info_url', "")

    quick_info_master = QuickInfoMaster()
    quick_info_master.kind_of_ballot_item = kind_of_ballot_item
    quick_info_master.language = language
    quick_info_master.master_entry_name = master_entry_name
    quick_info_master.more_info_credit = more_info_credit
    quick_info_master.more_info_url = more_info_url
    quick_info_master.info_text = info_text
    quick_info_master.info_html = info_html

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'language_choices':             LANGUAGE_CHOICES,
        'ballot_item_choices':          KIND_OF_BALLOT_ITEM_CHOICES,
        'quick_info_master':            quick_info_master,
    }
    return render(request, 'quick_info/quick_info_master_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_master_edit_view(request, quick_info_master_id):
    form_submitted = request.POST.get('form_submitted', False)
    quick_info_master_id = convert_to_int(quick_info_master_id)

    try:
        quick_info_master = QuickInfoMaster.objects.get(id=quick_info_master_id)
    except QuickInfoMaster.MultipleObjectsReturned as e:
        # Pretty unlikely that multiple objects have the same id
        messages.add_message(request, messages.ERROR, "This quick_info_master_id has multiple records.")
        return HttpResponseRedirect(reverse('quick_info:quick_info_master_list', args=()))
    except QuickInfoMaster.DoesNotExist:
        # This is fine, create new entry
        return quick_info_master_new_view(request)

    if positive_value_exists(form_submitted):
        # If the voter tried to submit an entry, and it didn't save, capture the changed values for display
        kind_of_ballot_item = request.POST.get('kind_of_ballot_item', False)
        language = request.POST.get('language', False)
        info_text = request.POST.get('info_text', False)
        info_html = request.POST.get('info_html', False)
        master_entry_name = request.POST.get('master_entry_name', False)
        more_info_credit = request.POST.get('more_info_credit', False)
        more_info_url = request.POST.get('more_info_url', False)

        # Write over the fields where a change has been made on the form
        if kind_of_ballot_item is not False:
            quick_info_master.kind_of_ballot_item = kind_of_ballot_item
        if language is not False:
            quick_info_master.language = language
        if master_entry_name is not False:
            quick_info_master.master_entry_name = master_entry_name
        if more_info_credit is not False:
            quick_info_master.more_info_credit = more_info_credit
        if more_info_url is not False:
            quick_info_master.more_info_url = more_info_url
        if info_text is not False:
            quick_info_master.info_text = info_text
        if info_html is not False:
            quick_info_master.info_html = info_html

    # ##################################
    # Above we have dealt with data provided by prior submit
    quick_info_list = QuickInfo.objects.order_by('id')  # This order_by is temp
    quick_info_list = QuickInfo.objects.filter(quick_info_master_we_vote_id=quick_info_master.we_vote_id)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'ballot_item_choices':          KIND_OF_BALLOT_ITEM_CHOICES,
        'language_choices':             LANGUAGE_CHOICES,
        'quick_info_master':            quick_info_master,
        'quick_info_list':              quick_info_list,
    }
    return render(request, 'quick_info/quick_info_master_edit.html', template_values)


# @login_required()  # Commented out while we are developing login process()
def quick_info_master_edit_process_view(request):
    """
    Process the new or edit quick_info_master forms
    :param request:
    :return:
    """
    quick_info_master_id = convert_to_int(request.POST.get('quick_info_master_id', False))
    quick_info_master_we_vote_id = convert_to_int(request.POST.get('quick_info_master_we_vote_id', False))

    kind_of_ballot_item = request.POST.get('kind_of_ballot_item', False)
    language = request.POST.get('language', False)
    info_text = request.POST.get('info_text', False)
    info_html = request.POST.get('info_html', False)
    master_entry_name = request.POST.get('master_entry_name', False)
    more_info_credit = request.POST.get('more_info_credit', False)
    more_info_url = request.POST.get('more_info_url', False)

    if not positive_value_exists(language):
        messages.add_message(request, messages.ERROR, "Please choose a language for your new entry.")
        ready_to_save = False
    elif not (positive_value_exists(info_text) or positive_value_exists(info_html)):
        messages.add_message(request, messages.ERROR,
                             "Please enter the text/html information about this ballot item.")
        ready_to_save = False
    elif not positive_value_exists(more_info_url):
        messages.add_message(request, messages.ERROR, "Please enter the source URL for this description.")
        ready_to_save = False
    else:
        ready_to_save = True

    if not ready_to_save:
        # Could we also just call the view directly with the request, instead of redirecting the browser?
        if positive_value_exists(quick_info_master_id):
            return quick_info_master_edit_view(request, quick_info_master_id)
        else:
            return quick_info_master_new_view(request)

    last_editor_we_vote_id = ""  # TODO We need to calculate this

    quick_info_master_manager = QuickInfoMasterManager()
    results = quick_info_master_manager.update_or_create_quick_info_master(
        quick_info_master_id=quick_info_master_id,
        quick_info_master_we_vote_id=quick_info_master_we_vote_id,
        master_entry_name=master_entry_name,
        kind_of_ballot_item=kind_of_ballot_item,
        info_html=info_html,
        info_text=info_text,
        language=language,
        last_editor_we_vote_id=last_editor_we_vote_id,
        more_info_url=more_info_url,
        more_info_credit=more_info_credit)
    if results['success']:
        messages.add_message(request, messages.INFO, results['status'])
    else:
        messages.add_message(request, messages.ERROR,
                             results['status'] + "language: {language}".format(
                                     language=language,
                             ))
        if positive_value_exists(quick_info_master_id):
            return quick_info_master_edit_view(request, quick_info_master_id)
        else:
            return quick_info_master_new_view(request)

    return HttpResponseRedirect(reverse('quick_info:quick_info_master_list', args=()))
