# position/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import JsonResponse
from candidate.models import CandidateCampaignManager
from follow.models import FollowOrganizationList
from organization.models import OrganizationManager
from .models import ANY, SUPPORT, NO_STANCE, INFORMATION_ONLY, STILL_DECIDING, OPPOSE, \
    PositionListForCandidateCampaign
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.models import convert_to_int, get_voter_device_id


logger = wevote_functions.admin.get_logger(__name__)


def positions_related_to_candidate_campaign_view(request, candidate_campaign_id, stance_we_are_looking_for):
    """
    We want to return a JSON file with the support positions for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    if stance_we_are_looking_for not in(SUPPORT, NO_STANCE, INFORMATION_ONLY, STILL_DECIDING, OPPOSE):
        logger.debug(stance_we_are_looking_for)
        return JsonResponse({0: "stance not recognized"})

    # This implementation is built to make only two database calls. All other calculations are done here in the
    #  application layer

    position_list_manager = PositionListForCandidateCampaign()
    all_positions_list_for_candidate_campaign = \
        position_list_manager.retrieve_all_positions_for_candidate_campaign(
            candidate_campaign_id, stance_we_are_looking_for)

    voter_device_id = get_voter_device_id(request)
    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)

    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_info_for_voter_simple_array(voter_id)

    positions_followed = position_list_manager.calculate_positions_followed_by_voter(
        voter_id, all_positions_list_for_candidate_campaign, organizations_followed_by_voter)

    positions_not_followed = position_list_manager.calculate_positions_not_followed_by_voter(
        all_positions_list_for_candidate_campaign, organizations_followed_by_voter)

    # TODO: Below we return a snippet of HTML, but this should be converted to returning just the org's name
    #       and id, so the "x, y, and z support" can be assembled and rendered by the client
    # VERSION 1
    # position_html = assemble_candidate_campaign_position_stance_html(
    #     all_positions_list_for_candidate_campaign, stance_we_are_looking_for, candidate_campaign_id)
    # VERSION 2
    position_html = assemble_candidate_campaign_stance_html(
        candidate_campaign_id, stance_we_are_looking_for, positions_followed, positions_not_followed)

    return JsonResponse({0: position_html})


def assemble_candidate_campaign_stance_html(
        candidate_campaign_id, stance_we_are_looking_for, positions_followed, positions_not_followed):
    """

    :param candidate_campaign_id:
    :param stance_we_are_looking_for:
    :param positions_followed:
    :param positions_not_followed:
    :return:
    """
    #################################
    # Start with positions_followed

    # Assemble some information that is independent of each position
    number_of_positions_followed_total = len(positions_followed)
    popup_box_title_verb = display_stance_we_are_looking_for_title(
        stance_we_are_looking_for, number_of_positions_followed_total)

    candidate_campaign_manager = CandidateCampaignManager()
    results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(candidate_campaign_id)
    if results['candidate_campaign_found']:
        candidate_campaign = results['candidate_campaign']
        popup_box_title_candidate_name = candidate_campaign.candidate_name
    else:
        popup_box_title_candidate_name = ""

    popup_box_title = popup_box_title_verb+" "+popup_box_title_candidate_name
    if stance_we_are_looking_for == SUPPORT:
        # This is the class we reference with jquery for opening a div popup to display the supporters
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_supporters"
        # This is the URL that returns the supporters for this candidate
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/supporters?f=1"  # Only show orgs followed
    elif stance_we_are_looking_for == OPPOSE:
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_opposers"
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/opposers?f=1"
    elif stance_we_are_looking_for == INFORMATION_ONLY:
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_infoonly"
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/infoonlylist?f=1"
    elif stance_we_are_looking_for == STILL_DECIDING:
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_deciders"
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/deciders?f=1"
    else:
        class_used_to_open_popup = ''
        retrieve_positions_url = ''

    # Cycle through these positions and put together a line about who is supporting, opposing, have information
    #  or are still deciding
    positions_followed_stance_html = ""
    is_first = True
    number_of_positions_followed_counter = 0
    only_you = False
    for position in positions_followed:
        if is_first:
            positions_followed_stance_html += ""
        else:
            is_next_to_last = number_of_positions_followed_counter == number_of_positions_followed_total - 1
            positions_followed_stance_html += " and " if is_next_to_last else ", "
        is_first = False

        if position.organization_id > 0:
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization(position.organization_id)
            if results['organization_found']:
                organization_on_stage = results['organization']
                link_open = "<a class='{link_class}' href='{link_href}' id='{popup_box_title}'>".format(
                    link_class=class_used_to_open_popup,
                    link_href=retrieve_positions_url,
                    popup_box_title=popup_box_title,
                )
                positions_followed_stance_html += "{link_open}{organization_name}</a>".format(
                    link_open=link_open,
                    organization_name=organization_on_stage.name,
                )
                number_of_positions_followed_counter += 1
        elif position.voter_id > 0:
            positions_followed_stance_html += "You"
            number_of_positions_followed_counter += 1
            if number_of_positions_followed_total == 1:
                only_you = True
    if number_of_positions_followed_total:
        verb_text = display_stance_we_are_looking_for(
            stance_we_are_looking_for, number_of_positions_followed_total, only_you)
        if verb_text:
            positions_followed_stance_html = "<span class='positions_followed_text'>" + positions_followed_stance_html
            positions_followed_stance_html += " <span class='position_stance_verb'>{verb_text}</span>".format(
                verb_text=verb_text)
            positions_followed_stance_html += "</span>"

    #################################
    # NOT Followed
    #################################
    # Now create string with html for positions_not_followed
    positions_not_followed_stance_html = ""
    number_of_positions_not_followed_total = len(positions_not_followed)
    # If there aren't any "not followed" positions, just return the positions_followed_stance_html
    if number_of_positions_not_followed_total == 0:
        return positions_followed_stance_html

    # If here we know there is at least one position available that isnt' being followed by voter
    popup_box_title = popup_box_title_verb+" "+popup_box_title_candidate_name
    if stance_we_are_looking_for == SUPPORT:
        # This is the class we reference with jquery for opening a div popup to display the supporters
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_supporters"
        # This is the URL that returns the supporters for this candidate
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/supporters?nf=1"  # Only show orgs not followed
    elif stance_we_are_looking_for == OPPOSE:
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_opposers"
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/opposers?nf=1"
    elif stance_we_are_looking_for == INFORMATION_ONLY:
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_infoonly"
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/infoonlylist?nf=1"
    elif stance_we_are_looking_for == STILL_DECIDING:
        class_used_to_open_popup = "candidate_campaign_"+candidate_campaign_id+"_deciders"
        retrieve_positions_url = "/pos/cand/"+candidate_campaign_id+"/deciders?nf=1"
    else:
        class_used_to_open_popup = ''
        retrieve_positions_url = ''

    link_open = "<a class='{link_class}' href='{link_href}' id='{popup_box_title}'>".format(
        link_class=class_used_to_open_popup,
        link_href=retrieve_positions_url,
        popup_box_title=popup_box_title,
    )

    # How we display the link to the positions NOT followed varies based on the number of *followed* positions
    if number_of_positions_followed_total == 0:
        if number_of_positions_not_followed_total == 1:
            not_followed_stance_verb = display_stance_verb_we_are_looking_for_singular(stance_we_are_looking_for)
        else:
            not_followed_stance_verb = display_stance_verb_we_are_looking_for_plural(stance_we_are_looking_for)
        positions_not_followed_stance_html += \
            "{link_open}{number} {not_followed_stance_verb}</a> ({link_open}learn more</a>)".format(
                link_open=link_open,
                number=number_of_positions_not_followed_total,
                not_followed_stance_verb=not_followed_stance_verb,
            )
    elif number_of_positions_followed_total < 5:
        if number_of_positions_not_followed_total == 1:
            not_followed_stance_verb = "other " \
                + display_stance_verb_we_are_looking_for_plural(stance_we_are_looking_for)
        else:
            not_followed_stance_verb = "others "\
                + display_stance_verb_we_are_looking_for_singular(stance_we_are_looking_for)
        positions_not_followed_stance_html += \
            "({link_open}{number_of_positions_not_followed_total} {not_followed_stance_verb}</a>)".format(
                link_open=link_open,
                number_of_positions_not_followed_total=number_of_positions_not_followed_total,
                not_followed_stance_verb=not_followed_stance_verb,
            )
    else:  # When there are more than 5 positions from followed organizations
        positions_not_followed_stance_html += "({link_open}show more supporters</a>)".format(
            link_open=link_open,
        )

    stance_html = positions_followed_stance_html + " " + "<span class='positions_not_followed'>" \
        + positions_not_followed_stance_html + "</span>"

    return stance_html


def display_stance_we_are_looking_for_title(stance_we_are_looking_for, number_of_stances_found):
    text_for_stance_we_are_looking_for = ""
    if stance_we_are_looking_for == OPPOSE:
        text_for_stance_we_are_looking_for += "Opposition to" \
            if number_of_stances_found > 1 else "Opposition to"  # Text for one org
    elif stance_we_are_looking_for == INFORMATION_ONLY:
        text_for_stance_we_are_looking_for += "Comments about" \
            if number_of_stances_found > 1 else "Comments about"  # Text for one org
    elif stance_we_are_looking_for == STILL_DECIDING:
        text_for_stance_we_are_looking_for += "Questions about" \
            if number_of_stances_found > 1 else "Questions about"  # Text for one org
    elif stance_we_are_looking_for == SUPPORT:
        text_for_stance_we_are_looking_for += "Support for" \
            if number_of_stances_found > 1 else "Support for"  # Text for one org
    return text_for_stance_we_are_looking_for


def display_stance_we_are_looking_for(stance_we_are_looking_for, number_of_stances_found, only_you):
    # If only_you is True, we want singular like "You oppose" as opposed to "You opposes"
    text_for_stance_we_are_looking_for = ""
    if stance_we_are_looking_for == OPPOSE:
        text_for_stance_we_are_looking_for += "oppose" \
            if number_of_stances_found > 1 or only_you else "opposes"  # Text for one org
    elif stance_we_are_looking_for == INFORMATION_ONLY:
        text_for_stance_we_are_looking_for += "have comments" \
            if number_of_stances_found > 1 or only_you else "has comments"  # Text for one org
    elif stance_we_are_looking_for == STILL_DECIDING:
        text_for_stance_we_are_looking_for += "are still deciding" \
            if number_of_stances_found > 1 or only_you else "is still deciding"  # Text for one org
    elif stance_we_are_looking_for == SUPPORT:
        text_for_stance_we_are_looking_for += "support" \
            if number_of_stances_found > 1 or only_you else "supports"  # Text for one org
    return text_for_stance_we_are_looking_for


def display_stance_verb_we_are_looking_for_singular(stance_we_are_looking_for):
    text_for_stance_we_are_looking_for = ""
    if stance_we_are_looking_for == OPPOSE:
        text_for_stance_we_are_looking_for += "oppose"
    elif stance_we_are_looking_for == INFORMATION_ONLY:
        text_for_stance_we_are_looking_for += "has comment"
    elif stance_we_are_looking_for == STILL_DECIDING:
        text_for_stance_we_are_looking_for += "is still deciding"
    elif stance_we_are_looking_for == SUPPORT:
        text_for_stance_we_are_looking_for += "support"
    return text_for_stance_we_are_looking_for


def display_stance_verb_we_are_looking_for_plural(stance_we_are_looking_for):
    text_for_stance_we_are_looking_for = ""
    if stance_we_are_looking_for == OPPOSE:
        text_for_stance_we_are_looking_for += "opposes"
    elif stance_we_are_looking_for == INFORMATION_ONLY:
        text_for_stance_we_are_looking_for += "have comments"
    elif stance_we_are_looking_for == STILL_DECIDING:
        text_for_stance_we_are_looking_for += "are still deciding"
    elif stance_we_are_looking_for == SUPPORT:
        text_for_stance_we_are_looking_for += "supporters"
    return text_for_stance_we_are_looking_for


def positions_count_for_candidate_campaign_any_not_followed_view(request, candidate_campaign_id):
    show_followed_positions = False
    return positions_count_for_candidate_campaign_any_view(
        request, candidate_campaign_id, show_followed_positions)


def positions_count_for_candidate_campaign_any_view(request, candidate_campaign_id, show_followed_positions=True):
    """
    We want to return a simple count of available positions (not already followed) for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    stance_we_are_looking_for = ANY
    # TODO Isn't working -- needs some code from wevotebase
    # return positions_count_for_candidate_campaign_view(
    #     request, candidate_campaign_id, stance_we_are_looking_for, show_followed_positions)
    return


def positions_related_to_candidate_campaign_oppose_view(request, candidate_campaign_id):
    """
    We want to return a JSON file with the oppose positions for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    stance_we_are_looking_for = OPPOSE
    return positions_related_to_candidate_campaign_view(request, candidate_campaign_id, stance_we_are_looking_for)


def positions_count_for_candidate_campaign_oppose_view(request, candidate_campaign_id):
    """
    We want to return a simple count of the oppose positions (of followed orgs) for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    stance_we_are_looking_for = OPPOSE
    # TODO Isn't working -- needs some code from wevotebase
    #return positions_count_for_candidate_campaign_view(request, candidate_campaign_id, stance_we_are_looking_for)
    return


def positions_related_to_candidate_campaign_information_only_view(request, candidate_campaign_id):
    """
    We want to return a JSON file with the oppose positions for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    stance_we_are_looking_for = INFORMATION_ONLY
    return positions_related_to_candidate_campaign_view(request, candidate_campaign_id, stance_we_are_looking_for)


def positions_related_to_candidate_campaign_still_deciding_view(request, candidate_campaign_id):
    """
    We want to return a JSON file with the oppose positions for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    stance_we_are_looking_for = STILL_DECIDING
    return positions_related_to_candidate_campaign_view(request, candidate_campaign_id, stance_we_are_looking_for)


def positions_related_to_candidate_campaign_support_view(request, candidate_campaign_id):
    """
    We want to return a JSON file with the support positions (of followed orgs) for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    stance_we_are_looking_for = SUPPORT
    return positions_related_to_candidate_campaign_view(request, candidate_campaign_id, stance_we_are_looking_for)


def positions_count_for_candidate_campaign_support_view(request, candidate_campaign_id):
    """
    We want to return a simple count of the support positions (of followed orgs) for a particular candidate's campaign
    :param request:
    :param candidate_campaign_id:
    :return:
    """
    stance_we_are_looking_for = SUPPORT
    # TODO This isn't working -- needs some code from wevotebase
    #return positions_count_for_candidate_campaign_view(request, candidate_campaign_id, stance_we_are_looking_for)
    return


def positions_related_to_contest_measure_oppose_view(request, contest_measure_id):
    """
    We want to return a JSON file with the oppose positions for a particular measure's campaign
    :param request:
    :param contest_measure_id:
    :return:
    """
    print "TO BE IMPLEMENTED, positions_related_to_contest_measure_oppose_view, contest_measure_id: {}".format(
        contest_measure_id)
    return JsonResponse({0: "Sierra Club opposes"})


def positions_related_to_contest_measure_support_view(request, contest_measure_id):
    """
    We want to return a JSON file with the support positions for a particular measure's campaign
    :param request:
    :param contest_measure_id:
    :return:
    """
    print "TO BE IMPLEMENTED, positions_related_to_contest_measure_support_view, contest_measure_id: {}".format(
        contest_measure_id)
    return JsonResponse({0: "Irvine Republican Club supports"})

