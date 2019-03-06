# import_export_maplight/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import import_maplight_from_json
from .models import MapLightCandidate
from candidate.models import CandidateCampaignManager
from django.contrib import messages
from django.contrib.messages import get_messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from exception.models import handle_record_not_saved_exception
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def import_export_maplight_index_view(request):
    """
    Provide an index of import/export actions (for We Vote data maintenance)
    """
    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':    messages_on_stage,
    }
    return render(request, 'import_export_maplight/index.html', template_values)


def import_maplight_from_json_view(request):
    """
    Take data from Test XML file and store in the local Voting Info Project database
    """
    # If person isn't signed in, we don't want to let them visit this page yet
    if not request.user.is_authenticated:
        return redirect('/admin')

    import_maplight_from_json(request)

    messages.add_message(request, messages.INFO, 'Maplight sample data imported.')

    return HttpResponseRedirect(reverse('import_export:import_export_index', args=()))


def transfer_maplight_data_to_we_vote_tables(request):
    # TODO We need to perhaps set up a table for these mappings that volunteers can add to?
    #  We need a plan for how volunteers can help us add to these mappings
    # One possibility -- ask volunteers to update this Google Sheet, then write a csv importer:
    #  https://docs.google.com/spreadsheets/d/1havD7GCxmBhi-zLLMdOpSJlU_DtBjvb5IJNiXgno9Bk/edit#gid=0
    politician_name_mapping_list = []
    one_mapping = {
        "google_civic_name": "Betty T. Yee",
        "maplight_display_name": "Betty Yee",
        "maplight_original_name": "Betty T Yee",
    }
    politician_name_mapping_list.append(one_mapping)
    one_mapping = {
        "google_civic_name": "Edmund G. \"Jerry\" Brown",
        "maplight_display_name": "Jerry Brown",
        "maplight_original_name": "",
    }
    politician_name_mapping_list.append(one_mapping)

    candidate_campaign_manager = CandidateCampaignManager()

    maplight_candidates_current_query = MapLightCandidate.objects.all()

    for one_candidate_from_maplight_table in maplight_candidates_current_query:
        found_by_id = False
        # Try to find a matching candidate
        results = candidate_campaign_manager.retrieve_candidate_campaign_from_id_maplight(
            one_candidate_from_maplight_table.candidate_id)

        if not results['success']:
            logger.warning(u"Candidate NOT found by MapLight id: {name}".format(
                name=one_candidate_from_maplight_table.candidate_id
            ))
            results = candidate_campaign_manager.retrieve_candidate_campaign_from_candidate_name(
                one_candidate_from_maplight_table.display_name)

            if not results['success']:
                logger.warning(u"Candidate NOT found by display_name: {name}".format(
                    name=one_candidate_from_maplight_table.display_name
                ))
                results = candidate_campaign_manager.retrieve_candidate_campaign_from_candidate_name(
                    one_candidate_from_maplight_table.original_name)

                if not results['success']:
                    logger.warning(u"Candidate NOT found by original_name: {name}".format(
                        name=one_candidate_from_maplight_table.original_name
                    ))

                    one_mapping_google_civic_name = ''
                    for one_mapping_found in politician_name_mapping_list:
                        if positive_value_exists(one_mapping_found['maplight_display_name']) \
                                and one_mapping_found['maplight_display_name'] == \
                                one_candidate_from_maplight_table.display_name:
                            one_mapping_google_civic_name = one_mapping_found['google_civic_name']
                            break
                    if positive_value_exists(one_mapping_google_civic_name):
                        results = candidate_campaign_manager.retrieve_candidate_campaign_from_candidate_name(
                            one_mapping_google_civic_name)
                    if not results['success'] or not positive_value_exists(one_mapping_google_civic_name):
                        logger.warning(u"Candidate NOT found by mapping to google_civic name: {name}".format(
                            name=one_mapping_google_civic_name
                        ))

                        continue  # Go to the next candidate

        candidate_campaign_on_stage = results['candidate_campaign']

        # Just in case the logic above let us through to here accidentally without a candidate_name value, don't proceed
        if not positive_value_exists(candidate_campaign_on_stage.candidate_name):
            continue

        logger.debug(u"Candidate {name} found".format(
            name=candidate_campaign_on_stage.candidate_name
        ))

        try:
            # Tie the maplight id to our record
            if not found_by_id:
                candidate_campaign_on_stage.id_maplight = one_candidate_from_maplight_table.candidate_id

            # Bring over the photo
            candidate_campaign_on_stage.photo_url_from_maplight = one_candidate_from_maplight_table.photo

            # We can bring over other data as needed, like gender for example
            candidate_campaign_on_stage.save()
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)

    messages.add_message(request, messages.INFO, 'MapLight data woven into We Vote tables.')

    return HttpResponseRedirect(reverse('import_export:import_export_index', args=()))
