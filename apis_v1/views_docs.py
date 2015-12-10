# apis_v1/views_docs.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .documentation_source import ballot_item_options_retrieve_doc, candidate_retrieve_doc, candidates_retrieve_doc, \
    device_id_generate_doc, \
    elections_retrieve_doc, measure_retrieve_doc, office_retrieve_doc, \
    oppose_count_doc, organization_count_doc, \
    organization_follow_doc, organization_follow_ignore_doc, organization_stop_following_doc, \
    organization_retrieve_doc, organization_save_doc, organization_search_doc, \
    position_retrieve_doc, position_save_doc, \
    support_count_doc, voter_address_retrieve_doc, voter_address_save_doc, \
    voter_ballot_items_retrieve_doc, voter_ballot_items_retrieve_from_google_civic_doc, voter_count_doc, \
    voter_create_doc, voter_guide_possibility_retrieve_doc, voter_guide_possibility_save_doc, \
    voter_guides_to_follow_retrieve_doc, \
    voter_position_comment_save_doc, voter_position_retrieve_doc, \
    voter_opposing_save_doc, voter_retrieve_doc, voter_star_off_save_doc, voter_star_on_save_doc, \
    voter_star_status_retrieve_doc, voter_stop_opposing_save_doc, \
    voter_stop_supporting_save_doc, voter_supporting_save_doc
from django.shortcuts import render

LOCALHOST_URL_ROOT = 'http://localhost:8000'


def apis_index_doc_view(request):
    """
    Show a list of available APIs
    """
    template_values = {
        # 'key': value,
    }
    return render(request, 'apis_v1/apis_index.html', template_values)


def ballot_item_options_retrieve_doc_view(request):
    """
    Show documentation about ballotItemOptionsRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = ballot_item_options_retrieve_doc.ballot_item_options_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def candidate_retrieve_doc_view(request):
    """
    Show documentation about candidateRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = candidate_retrieve_doc.candidate_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def candidates_retrieve_doc_view(request):
    """
    Show documentation about candidatesRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = candidates_retrieve_doc.candidates_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def device_id_generate_doc_view(request):
    """
    Show documentation about deviceIdGenerate
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = device_id_generate_doc.device_id_generate_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def elections_retrieve_doc_view(request):
    """
    Show documentation about electionsRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = elections_retrieve_doc.elections_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def measure_retrieve_doc_view(request):
    """
    Show documentation about candidatesRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = measure_retrieve_doc.measure_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def office_retrieve_doc_view(request):
    """
    Show documentation about candidatesRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = office_retrieve_doc.office_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_count_doc_view(request):
    """
    Show documentation about organizationCount
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = organization_count_doc.organization_count_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_follow_doc_view(request):
    """
    Show documentation about organizationFollow
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = organization_follow_doc.organization_follow_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_follow_ignore_doc_view(request):
    """
    Show documentation about organizationFollowIgnore
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = organization_follow_ignore_doc.organization_follow_ignore_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_stop_following_doc_view(request):
    """
    Show documentation about organizationStopFollowing
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = organization_stop_following_doc.organization_stop_following_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_retrieve_doc_view(request):
    """
    Show documentation about organizationRetrieve
    """
    url_root = LOCALHOST_URL_ROOT

    template_values = organization_retrieve_doc.organization_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_save_doc_view(request):
    """
    Show documentation about organizationSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = organization_save_doc.organization_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_search_doc_view(request):
    """
    Show documentation about organizationSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = organization_search_doc.organization_search_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_retrieve_doc_view(request):
    """
    Show documentation about positionRetrieve
    """
    url_root = LOCALHOST_URL_ROOT

    template_values = position_retrieve_doc.position_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_save_doc_view(request):
    """
    Show documentation about positionSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = position_save_doc.position_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def oppose_count_doc_view(request):
    """
    Show documentation about opposeCount
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = oppose_count_doc.oppose_count_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def support_count_doc_view(request):
    """
    Show documentation about supportCount
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = support_count_doc.support_count_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_address_retrieve_doc_view(request):
    """
    Show documentation about voterAddressRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_address_retrieve_doc.voter_address_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_address_save_doc_view(request):
    """
    Show documentation about voterSaveRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_address_save_doc.voter_address_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_ballot_items_retrieve_doc_view(request):
    """
    Show documentation about voterBallotItemsRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_ballot_items_retrieve_doc.voter_ballot_items_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_ballot_items_retrieve_from_google_civic_doc_view(request):
    """
    Show documentation about voterBallotItemsRetrieveFromGoogleCivic
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_ballot_items_retrieve_from_google_civic_doc.\
        voter_ballot_items_retrieve_from_google_civic_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_count_doc_view(request):
    """
    Show documentation about voterCount
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_count_doc.voter_count_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_create_doc_view(request):
    """
    Show documentation about voterCreate
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_create_doc.voter_create_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guide_possibility_retrieve_doc_view(request):
    """
    Show documentation about voterGuidePossibilityRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = \
        voter_guide_possibility_retrieve_doc.voter_guide_possibility_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guide_possibility_save_doc_view(request):
    """
    Show documentation about voterGuidePossibilitySave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_guide_possibility_save_doc.voter_guide_possibility_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guides_to_follow_retrieve_doc_view(request):
    """
    Show documentation about voterGuidesToFollowRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_guides_to_follow_retrieve_doc.voter_guides_to_follow_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_retrieve_doc_view(request):
    """
    Show documentation about positionRetrieve
    """
    url_root = LOCALHOST_URL_ROOT

    template_values = voter_position_retrieve_doc.voter_position_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_comment_save_doc_view(request):
    """
    Show documentation about positionSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_position_comment_save_doc.voter_position_comment_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_opposing_save_doc_view(request):
    """
    Show documentation about voterSupportingSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_opposing_save_doc.voter_opposing_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_stop_opposing_save_doc_view(request):
    """
    Show documentation about voterStopSupportingSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_stop_opposing_save_doc.voter_stop_opposing_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_retrieve_doc_view(request):
    """
    Show documentation about voterRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_retrieve_doc.voter_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_stop_supporting_save_doc_view(request):
    """
    Show documentation about voterStopSupportingSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_stop_supporting_save_doc.voter_stop_supporting_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_supporting_save_doc_view(request):
    """
    Show documentation about voterSupportingSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_supporting_save_doc.voter_supporting_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_star_off_save_doc_view(request):
    """
    Show documentation about voterStarOffSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_star_off_save_doc.voter_star_off_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_star_on_save_doc_view(request):
    """
    Show documentation about voterStarOnSave
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_star_on_save_doc.voter_star_on_save_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_star_status_retrieve_doc_view(request):
    """
    Show documentation about voterStarStatusRetrieve
    """
    url_root = LOCALHOST_URL_ROOT
    template_values = voter_star_status_retrieve_doc.voter_star_status_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)
