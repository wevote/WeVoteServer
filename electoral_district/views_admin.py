# electoral_district/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import electoral_districts_import_from_sample_file
from .models import ElectoralDistrict, ElectoralDistrictManager, ElectoralDistrictLinkToPollingLocation
from admin_tools.views import redirect_to_sign_in_page
from ballot.models import BallotReturnedListManager
from config.base import get_environment_variable
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception
from import_export_ctcl.controllers import CTCL_SAMPLE_XML_FILE
from voter.models import voter_has_authority
from wevote_functions.functions import convert_state_code_to_state_text, convert_to_float, convert_to_int, \
    positive_value_exists
import wevote_functions.admin
from django.http import HttpResponse
import json

logger = wevote_functions.admin.get_logger(__name__)

# These are states for which we have electoral_district data
STATE_LIST_IMPORT = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        # 'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        # 'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        # 'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        # 'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        # 'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        # 'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming'
}


@login_required
def electoral_district_import_from_xml_view(request):

    results = electoral_districts_import_from_sample_file(CTCL_SAMPLE_XML_FILE)

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Electoral Districts import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))


@login_required
def electoral_district_list_view(request):
    # admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    polling_location_we_vote_id = request.GET.get('polling_location_we_vote_id', "")
    state_code = request.GET.get('state_code', '')
    electoral_district_search = request.GET.get('electoral_district_search', '')

    if positive_value_exists(polling_location_we_vote_id):
        # Find the electoral_districts this polling location is in
        electoral_district_link_query = ElectoralDistrictLinkToPollingLocation.objects.all()
        electoral_district_link_query = electoral_district_link_query.filter(
            polling_location_we_vote_id__iexact=polling_location_we_vote_id)

        electoral_district_link_list = list(electoral_district_link_query)

        electoral_district_query = ElectoralDistrict.objects.all()

        electoral_district_list = []
        electoral_district_count = 0
        filters = []
        for one_link in electoral_district_link_list:
            new_filter = Q(we_vote_id__icontains=one_link.electoral_district_we_vote_id)
            filters.append(new_filter)

        # Add the first query
        if len(filters):
            final_filters = filters.pop()

            # ...and "OR" the remaining items in the list
            for item in filters:
                final_filters |= item

            electoral_district_query = electoral_district_query.filter(final_filters)

            electoral_district_list = list(electoral_district_query)
            electoral_district_count = len(electoral_district_list)
    else:

        electoral_district_count_query = ElectoralDistrict.objects.all()
        electoral_district_query = ElectoralDistrict.objects.all()

        if positive_value_exists(state_code):
            electoral_district_count_query = electoral_district_count_query.filter(state_code__iexact=state_code)
            electoral_district_query = electoral_district_query.filter(state_code__iexact=state_code)

        if positive_value_exists(electoral_district_search):
            search_words = electoral_district_search.split()
            for one_word in search_words:
                filters = []

                new_filter = Q(we_vote_id__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(electoral_district_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(ctcl_id_temp__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    electoral_district_count_query = electoral_district_count_query.filter(final_filters)
                    electoral_district_query = electoral_district_query.filter(final_filters)

        electoral_district_count = electoral_district_count_query.count()

        info_message = '{electoral_district_count} electoral districts found.'.format(
            electoral_district_count=electoral_district_count)

        electoral_district_list = electoral_district_query.order_by('electoral_district_name')[:100]

        messages.add_message(request, messages.INFO, info_message)

    state_list = STATE_LIST_IMPORT
    sorted_state_list = sorted(state_list.items())

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':        messages_on_stage,
        'google_civic_election_id': google_civic_election_id,
        'electoral_district_list':    electoral_district_list,
        'electoral_district_count':   electoral_district_count,
        'electoral_district_search':  electoral_district_search,
        'polling_location_we_vote_id':       polling_location_we_vote_id,
        'state_code':               state_code,
        'state_name':               convert_state_code_to_state_text(state_code),
        'state_list':               sorted_state_list,
    }
    return render(request, 'electoral_district/electoral_district_list.html', template_values)


@login_required
def electoral_district_summary_view(request, electoral_district_we_vote_id):
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    messages_on_stage = get_messages(request)
    electoral_district_on_stage_found = False
    electoral_district_on_stage = ElectoralDistrict()
    try:
        electoral_district_on_stage = ElectoralDistrict.objects.get(we_vote_id=electoral_district_we_vote_id)
        electoral_district_on_stage_found = True
    except ElectoralDistrict.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except ElectoralDistrict.DoesNotExist:
        # This is fine, create new
        pass

    template_values = {
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage':        messages_on_stage,
        'electoral_district':         electoral_district_on_stage,
    }
    return render(request, 'electoral_district/electoral_district_summary.html', template_values)
