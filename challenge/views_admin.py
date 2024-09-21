# challenge/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import localtime, now

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from datetime import datetime, timedelta
from election.models import ElectionManager
from follow.models import FOLLOW_DISLIKE, FOLLOWING, FollowOrganization, FollowOrganizationManager
from follow.controllers import create_followers_from_positions
from organization.models import Organization, OrganizationManager
from politician.models import Politician, PoliticianManager
from stripe_donations.models import StripeManager
from volunteer_task.models import VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS, \
    VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION, VolunteerTaskManager
from voter.models import fetch_voter_from_voter_device_link, voter_has_authority, VoterManager
from wevote_functions.functions import convert_state_code_to_state_text, convert_to_int, \
    get_voter_api_device_id, positive_value_exists, STATE_CODE_MAP
from wevote_functions.functions_date import generate_date_as_integer
from .controllers import fetch_duplicate_challenge_count, \
    figure_out_challenge_conflict_values, find_duplicate_challenge, merge_if_duplicate_challenges, \
    merge_these_two_challenges
from .models import Challenge, ChallengesAreNotDuplicates, ChallengesArePossibleDuplicates, \
    ChallengeManager, ChallengeOwner, ChallengePolitician, ChallengeSEOFriendlyPath, ChallengeParticipant, \
    CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED, \
    CHALLENGE_UNIQUE_IDENTIFIERS, FINAL_ELECTION_DATE_COOL_DOWN, PARTICIPANTS_COUNT_MINIMUM_FOR_LISTING

logger = wevote_functions.admin.get_logger(__name__)
CHALLENGES_ROOT_URL = get_environment_variable("CHALLENGES_ROOT_URL", no_exception=True)
if not positive_value_exists(CHALLENGES_ROOT_URL):
    CHALLENGES_ROOT_URL = "https://quality.wevote.us"
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")


@login_required
def challenge_delete_process_view(request):
    """
    Delete a challenge
    :param request:
    :return:
    """
    status = ""
    challenge_we_vote_id = request.POST.get('challenge_we_vote_id', 0)
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))

    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    state_code = request.POST.get('state_code', '')

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager', 'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this Campaign. '
                             'Please check the checkbox to confirm you want to delete this organization.')
        return HttpResponseRedirect(reverse('challenge:challenge_edit', args=(challenge_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    challenge_manager = ChallengeManager()
    results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge_we_vote_id)
    if results['challenge_found']:
        challenge = results['challenge']

        challenge.delete()
        messages.add_message(request, messages.INFO, 'Challenge deleted.')
    else:
        messages.add_message(request, messages.ERROR, 'Challenge not found.')

    return HttpResponseRedirect(reverse('challenge:challenge_list', args=()))


@login_required
def challenge_duplicates_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    state_code = request.GET.get('state_code', '')
    challenge_search = request.GET.get('challenge_search', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    show_all = positive_value_exists(request.GET.get('show_all', False))
    show_related_candidates = positive_value_exists(request.GET.get('show_related_candidates', False))
    show_challenges_with_email = request.GET.get('show_challenges_with_email', False)

    duplicates_list = []
    duplicates_list_count = 0
    possible_duplicates_count = 0
    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    try:
        queryset = ChallengesArePossibleDuplicates.objects.using('readonly').all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        duplicates_list_count = queryset.count()
        queryset = queryset.exclude(
            Q(challenge2_we_vote_id__isnull=True) | Q(challenge2_we_vote_id=''))
        possible_duplicates_count = queryset.count()
        if not positive_value_exists(show_all):
            duplicates_list = list(queryset[:200])
        else:
            duplicates_list = list(queryset[:1000])
    except ObjectDoesNotExist:
        # This is fine
        pass

    # Collect the challenge_we_vote_id of all possible duplicates so we can retrieve the objects in a single db call
    challenges_to_display_we_vote_id_list = []
    for one_duplicate in duplicates_list:
        if positive_value_exists(one_duplicate.challenge1_we_vote_id):
            challenges_to_display_we_vote_id_list.append(one_duplicate.challenge1_we_vote_id)
        if positive_value_exists(one_duplicate.challenge2_we_vote_id):
            challenges_to_display_we_vote_id_list.append(one_duplicate.challenge2_we_vote_id)

    challenges_dict = {}
    try:
        queryset = Challenge.objects.using('readonly').all()
        queryset = queryset.filter(we_vote_id__in=challenges_to_display_we_vote_id_list)
        challenge_data_list = list(queryset)
        for one_challenge in challenge_data_list:
            challenges_dict[one_challenge.we_vote_id] = one_challenge
    except Exception as e:
        pass

    # Now retrieve all seo_friendly_path entries associated with each Campaign, so we can attach below
    challenge_seo_friendly_path_dict = {}
    try:
        queryset = ChallengeSEOFriendlyPath.objects.using('readonly').all()
        queryset = queryset.filter(challenge_we_vote_id__in=challenges_to_display_we_vote_id_list)
        challenge_seo_friendly_path_list = list(queryset)
        for one_seo_friendly_path in challenge_seo_friendly_path_list:
            challenge_entry = challenges_dict[one_seo_friendly_path.challenge_we_vote_id]
            if challenge_entry.seo_friendly_path == one_seo_friendly_path.final_pathname_string:
                # Do not add to the list if already attached directly to challenge
                continue
            if one_seo_friendly_path.challenge_we_vote_id not in challenge_seo_friendly_path_dict:
                challenge_seo_friendly_path_dict[one_seo_friendly_path.challenge_we_vote_id] = []
            challenge_seo_friendly_path_dict[one_seo_friendly_path.challenge_we_vote_id]\
                .append(one_seo_friendly_path.final_pathname_string)
    except Exception as e:
        pass

    # Retrieve linked politician, so we can include the Twitter handles for the Politician

    # Attached seo_friendly_path_list
    for one_challenge in challenge_data_list:
        if one_challenge.we_vote_id in challenge_seo_friendly_path_dict:
            one_challenge.seo_friendly_path_list = challenge_seo_friendly_path_dict[one_challenge.we_vote_id]

    duplicates_list_modified = []
    for one_duplicate in duplicates_list:
        if positive_value_exists(one_duplicate.challenge1_we_vote_id) \
                and one_duplicate.challenge1_we_vote_id in challenges_dict \
                and positive_value_exists(one_duplicate.challenge2_we_vote_id) \
                and one_duplicate.challenge2_we_vote_id in challenges_dict:
            one_duplicate.challenge1 = challenges_dict[one_duplicate.challenge1_we_vote_id]
            one_duplicate.challenge2 = challenges_dict[one_duplicate.challenge2_we_vote_id]
            duplicates_list_modified.append(one_duplicate)
        else:
            possible_duplicates_count -= 1

    messages.add_message(request, messages.INFO,
                         "Challenges analyzed: {duplicates_list_count:,}. "
                         "Possible duplicate challenges found: {possible_duplicates_count:,}. "
                         "State: {state_code}"
                         "".format(
                             duplicates_list_count=duplicates_list_count,
                             possible_duplicates_count=possible_duplicates_count,
                             state_code=state_code))

    template_values = {
        'messages_on_stage':            messages_on_stage,
        'google_civic_election_id':     google_civic_election_id,
        'duplicates_list':              duplicates_list_modified,
        'challenge_search':            challenge_search,
        'show_all':                     show_all,
        'show_challenges_with_email':  show_challenges_with_email,
        'show_related_candidates':      show_related_candidates,
        'state_code':                   state_code,
        'state_list':                   sorted_state_list,
    }
    return render(request, 'challenge/challenge_duplicates_list.html', template_values)


@login_required
def challenge_edit_owners_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_we_vote_id = request.POST.get('challenge_we_vote_id', None)
    challenge_owner_visible_to_public = \
        positive_value_exists(request.POST.get('challenge_owner_visible_to_public', False))
    challenge_owner_feature_this_profile_image = \
        positive_value_exists(request.POST.get('challenge_owner_feature_this_profile_image', False))
    challenge_owner_organization_we_vote_id_filter = request.POST.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.POST.get('challenge_search', '')
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    incoming_challenge_owner_we_vote_id = request.POST.get('incoming_challenge_owner_we_vote_id', None)
    if positive_value_exists(incoming_challenge_owner_we_vote_id):
        incoming_challenge_owner_we_vote_id = incoming_challenge_owner_we_vote_id.strip()
    state_code = request.POST.get('state_code', '')

    organization_manager = OrganizationManager()
    voter_manager = VoterManager()
    challenge_owner_organization_we_vote_id = ''
    challenge_owner_voter_we_vote_id = ''

    if positive_value_exists(incoming_challenge_owner_we_vote_id):
        # We allow either organization_we_vote_id or voter_we_vote_id
        if 'org' in incoming_challenge_owner_we_vote_id:
            challenge_owner_organization_we_vote_id = incoming_challenge_owner_we_vote_id
            challenge_owner_voter_we_vote_id = \
                voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                    challenge_owner_organization_we_vote_id)
        elif 'voter' in incoming_challenge_owner_we_vote_id:
            challenge_owner_voter_we_vote_id = incoming_challenge_owner_we_vote_id
            challenge_owner_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(challenge_owner_voter_we_vote_id)

    # Create new ChallengeOwner
    if positive_value_exists(challenge_owner_organization_we_vote_id) or \
            positive_value_exists(challenge_owner_voter_we_vote_id):
        do_not_create = False
        link_already_exists = False
        status = ""
        # Does it already exist?
        try:
            if positive_value_exists(challenge_owner_organization_we_vote_id):
                ChallengeOwner.objects.get(
                    challenge_we_vote_id=challenge_we_vote_id,
                    organization_we_vote_id=challenge_owner_organization_we_vote_id)
                link_already_exists = True
            elif positive_value_exists(challenge_owner_voter_we_vote_id):
                ChallengeOwner.objects.get(
                    challenge_we_vote_id=challenge_we_vote_id,
                    voter_we_vote_id=challenge_owner_voter_we_vote_id)
                link_already_exists = True
        except ChallengeOwner.DoesNotExist:
            link_already_exists = False
        except Exception as e:
            do_not_create = True
            messages.add_message(request, messages.ERROR, 'ChallengeOwner already exists.')
            status += "ADD_CHALLENGE_OWNER_ALREADY_EXISTS " + str(e) + " "

        if not do_not_create and not link_already_exists:
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(challenge_owner_organization_we_vote_id)
            if organization_results['organization_found']:
                organization_name = organization_results['organization'].organization_name
                we_vote_hosted_profile_image_url_medium = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_medium
                we_vote_hosted_profile_image_url_tiny = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_tiny
            else:
                organization_name = ''
                we_vote_hosted_profile_image_url_medium = ''
                we_vote_hosted_profile_image_url_tiny = ''
            # Now create new link
            try:
                # Create the ChallengeOwner
                ChallengeOwner.objects.create(
                    challenge_we_vote_id=challenge_we_vote_id,
                    organization_name=organization_name,
                    organization_we_vote_id=challenge_owner_organization_we_vote_id,
                    feature_this_profile_image=challenge_owner_feature_this_profile_image,
                    voter_we_vote_id=challenge_owner_voter_we_vote_id,
                    we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                    visible_to_public=challenge_owner_visible_to_public)

                messages.add_message(request, messages.INFO, 'New ChallengeOwner created.')
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     'Could not create ChallengeOwner.'
                                     ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or editing a ChallengeOwner
    challenge_manager = ChallengeManager()
    challenge_owner_list = challenge_manager.retrieve_challenge_owner_list(
        challenge_we_vote_id_list=[challenge_we_vote_id],
        viewer_is_owner=True
    )
    for challenge_owner in challenge_owner_list:
        if positive_value_exists(challenge_owner.challenge_we_vote_id):
            delete_variable_name = "delete_challenge_owner_" + str(challenge_owner.id)
            delete_challenge_owner = positive_value_exists(request.POST.get(delete_variable_name, False))
            if positive_value_exists(delete_challenge_owner):
                challenge_owner.delete()
                messages.add_message(request, messages.INFO, 'Deleted ChallengeOwner.')
            else:
                owner_changed = False
                visible_to_public_exists_variable_name = \
                    "challenge_owner_visible_to_public_" + str(challenge_owner.id) + "_exists"
                challenge_owner_visible_to_public_exists = \
                    request.POST.get(visible_to_public_exists_variable_name, None)
                visible_to_public_variable_name = "challenge_owner_visible_to_public_" + str(challenge_owner.id)
                challenge_owner_visible_to_public = \
                    positive_value_exists(request.POST.get(visible_to_public_variable_name, False))
                feature_this_profile_image_variable_name = \
                    "challenge_owner_feature_this_profile_image_" + str(challenge_owner.id)
                challenge_owner_feature_this_profile_image = \
                    positive_value_exists(request.POST.get(feature_this_profile_image_variable_name, False))
                if challenge_owner_visible_to_public_exists is not None:
                    challenge_owner.feature_this_profile_image = challenge_owner_feature_this_profile_image
                    challenge_owner.visible_to_public = challenge_owner_visible_to_public
                    owner_changed = True

                # Now refresh organization cached data
                organization_results = \
                    organization_manager.retrieve_organization_from_we_vote_id(challenge_owner.organization_we_vote_id)
                if organization_results['organization_found']:
                    organization_name = organization_results['organization'].organization_name
                    if positive_value_exists(organization_name) and \
                            challenge_owner.organization_name != organization_name:
                        challenge_owner.organization_name = organization_name
                        owner_changed = True
                    we_vote_hosted_profile_image_url_medium = \
                        organization_results['organization'].we_vote_hosted_profile_image_url_medium
                    if positive_value_exists(we_vote_hosted_profile_image_url_medium) and \
                            challenge_owner.we_vote_hosted_profile_image_url_medium != \
                            we_vote_hosted_profile_image_url_medium:
                        challenge_owner.we_vote_hosted_profile_image_url_medium = \
                            we_vote_hosted_profile_image_url_medium
                        owner_changed = True
                    we_vote_hosted_profile_image_url_tiny = \
                        organization_results['organization'].we_vote_hosted_profile_image_url_tiny
                    if positive_value_exists(we_vote_hosted_profile_image_url_tiny) and \
                            challenge_owner.we_vote_hosted_profile_image_url_tiny != \
                            we_vote_hosted_profile_image_url_tiny:
                        challenge_owner.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                        owner_changed = True
                if not positive_value_exists(challenge_owner.voter_we_vote_id):
                    voter_we_vote_id = voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                        challenge_owner.organization_we_vote_id)
                    if positive_value_exists(voter_we_vote_id):
                        challenge_owner.voter_we_vote_id = voter_we_vote_id
                        owner_changed = True
                if owner_changed:
                    challenge_owner.save()

    return HttpResponseRedirect(reverse('challenge:challenge_edit_owners', args=(challenge_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&challenge_owner_organization_we_vote_id=" +
                                str(challenge_owner_organization_we_vote_id_filter) +
                                "&challenge_search=" + str(challenge_search) +
                                "&state_code=" + str(state_code))


@login_required
def challenge_edit_owners_view(request, challenge_id=0, challenge_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.GET.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.GET.get('challenge_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    challenge_id = convert_to_int(challenge_id)
    challenge_manager = ChallengeManager()
    challenge = None
    results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge_we_vote_id)

    if results['challenge_found']:
        challenge = results['challenge']

    challenge_owner_list_modified = []
    challenge_owner_list = challenge_manager.retrieve_challenge_owner_list(
        challenge_we_vote_id_list=[challenge_we_vote_id],
        viewer_is_owner=True
    )

    # voter_manager = VoterManager()
    for challenge_owner in challenge_owner_list:
        challenge_owner_list_modified.append(challenge_owner)

    template_values = {
        'challenge':                                challenge,
        'challenge_owner_list':                     challenge_owner_list_modified,
        'challenge_owner_organization_we_vote_id':  challenge_owner_organization_we_vote_id,
        'challenge_search':                         challenge_search,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'state_code':                               state_code,
    }
    return render(request, 'challenge/challenge_edit_owners.html', template_values)


@login_required
def challenge_edit_politicians_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.POST.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.POST.get('challenge_search', '')
    challenge_we_vote_id = request.POST.get('challenge_we_vote_id', None)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', None)
    if positive_value_exists(politician_we_vote_id):
        politician_we_vote_id = politician_we_vote_id.strip()
    google_civic_election_id = convert_to_int(request.POST.get('google_civic_election_id', 0))
    state_code = request.POST.get('state_code', '')

    # Create new ChallengePolitician
    if positive_value_exists(politician_we_vote_id):
        if 'pol' not in politician_we_vote_id:
            messages.add_message(request, messages.ERROR, 'Valid PoliticianWeVoteId missing.')
        else:
            do_not_create = False
            link_already_exists = False
            status = ""
            # Does it already exist?
            try:
                ChallengePolitician.objects.get(
                    challenge_we_vote_id=challenge_we_vote_id,
                    politician_we_vote_id=politician_we_vote_id)
                link_already_exists = True
            except ChallengePolitician.DoesNotExist:
                link_already_exists = False
            except Exception as e:
                do_not_create = True
                messages.add_message(request, messages.ERROR, 'Link already exists.')
                status += "ADD_CHALLENGE_POLITICIAN_ALREADY_EXISTS " + str(e) + " "

            if not do_not_create and not link_already_exists:
                politician_manager = PoliticianManager()
                politician_results = \
                    politician_manager.retrieve_politician_from_we_vote_id(politician_we_vote_id)
                if politician_results['politician_found']:
                    politician_name = politician_results['politician'].politician_name
                    state_code = politician_results['politician'].state_code
                    we_vote_hosted_profile_image_url_large = \
                        politician_results['politician'].we_vote_hosted_profile_image_url_large
                    we_vote_hosted_profile_image_url_medium = \
                        politician_results['politician'].we_vote_hosted_profile_image_url_medium
                    we_vote_hosted_profile_image_url_tiny = \
                        politician_results['politician'].we_vote_hosted_profile_image_url_tiny
                else:
                    politician_name = ''
                    we_vote_hosted_profile_image_url_large = ''
                    we_vote_hosted_profile_image_url_medium = ''
                    we_vote_hosted_profile_image_url_tiny = ''
                voter_we_vote_id = ''
                try:
                    # Create the ChallengePolitician
                    ChallengePolitician.objects.create(
                        challenge_we_vote_id=challenge_we_vote_id,
                        politician_name=politician_name,
                        politician_we_vote_id=politician_we_vote_id,
                        state_code=state_code,
                        we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                        we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                    )

                    messages.add_message(request, messages.INFO, 'New ChallengePolitician created.')
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         'Could not create ChallengePolitician.'
                                         ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or editing a ChallengePolitician
    challenge_manager = ChallengeManager()
    challenge_politician_list = challenge_manager.retrieve_challenge_politician_list(
        challenge_we_vote_id=challenge_we_vote_id,
        read_only=False,
    )
    for challenge_politician in challenge_politician_list:
        if positive_value_exists(challenge_politician.challenge_we_vote_id):
            delete_variable_name = "delete_challenge_politician_" + str(challenge_politician.id)
            delete_challenge_politician = positive_value_exists(request.POST.get(delete_variable_name, False))
            if positive_value_exists(delete_challenge_politician):
                challenge_politician.delete()
                messages.add_message(request, messages.INFO, 'Deleted ChallengePolitician.')
            else:
                pass

    return HttpResponseRedirect(reverse('challenge:challenge_edit_politicians', args=(challenge_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&challenge_owner_organization_we_vote_id=" +
                                str(challenge_owner_organization_we_vote_id) +
                                "&challenge_search=" + str(challenge_search) +
                                "&state_code=" + str(state_code))


@login_required
def challenge_edit_politicians_view(request, challenge_id=0, challenge_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.GET.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.GET.get('challenge_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')

    messages_on_stage = get_messages(request)
    challenge_id = convert_to_int(challenge_id)
    challenge_manager = ChallengeManager()
    challenge = None
    results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge_we_vote_id)

    if results['challenge_found']:
        challenge = results['challenge']

    challenge_politician_list = challenge_manager.retrieve_challenge_politician_list(
        challenge_we_vote_id=challenge_we_vote_id,
    )

    template_values = {
        'challenge':                                challenge,
        'challenge_owner_organization_we_vote_id':  challenge_owner_organization_we_vote_id,
        'challenge_search':                         challenge_search,
        'challenge_politician_list':                challenge_politician_list,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'state_code':                               state_code,
    }
    return render(request, 'challenge/challenge_edit_politicians.html', template_values)


@login_required
def challenge_edit_process_view(request):
    """

    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_device_id = get_voter_api_device_id(request)
    voter = fetch_voter_from_voter_device_link(voter_device_id)
    change_description = ''
    if hasattr(voter, 'last_name'):
        changed_by_name = voter.get_full_name()
        changed_by_voter_we_vote_id = voter.we_vote_id
    else:
        changed_by_name = ""
        changed_by_voter_we_vote_id = ''

    challenge_id = convert_to_int(request.POST.get('challenge_id', 0))
    challenge_owner_organization_we_vote_id = request.POST.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.POST.get('challenge_search', '')
    challenge_we_vote_id = request.POST.get('challenge_we_vote_id', None)
    challenge_title = request.POST.get('challenge_title', None)
    challenge_description = request.POST.get('challenge_description', None)
    final_election_date_as_integer = convert_to_int(request.POST.get('final_election_date_as_integer', 0))
    final_election_date_as_integer = None if final_election_date_as_integer == 0 else final_election_date_as_integer
    google_civic_election_id = request.POST.get('google_civic_election_id', 0)
    take_out_of_draft_mode = request.POST.get('take_out_of_draft_mode', None)
    is_blocked_by_we_vote = request.POST.get('is_blocked_by_we_vote', False)
    is_blocked_by_we_vote_reason = request.POST.get('is_blocked_by_we_vote_reason', None)
    is_in_team_review_mode = request.POST.get('is_in_team_review_mode', False)
    is_not_promoted_by_we_vote = request.POST.get('is_not_promoted_by_we_vote', False)
    is_not_promoted_by_we_vote_reason = request.POST.get('is_not_promoted_by_we_vote_reason', None)
    is_ok_to_promote_on_we_vote = request.POST.get('is_ok_to_promote_on_we_vote', False)
    politician_we_vote_id = request.POST.get('politician_we_vote_id', None)
    politician_starter_list_serialized = request.POST.get('politician_starter_list_serialized', None)
    seo_friendly_path = request.POST.get('seo_friendly_path', None)
    state_code = request.POST.get('state_code', None)
    participants_count_minimum_ignored = request.POST.get('participants_count_minimum_ignored', False)

    # Check to see if this challenge is already being used anywhere
    challenge = None
    challenge_found = False
    challenge_manager = ChallengeManager()
    politician_manager = PoliticianManager()
    status = ""
    if positive_value_exists(challenge_id) or positive_value_exists(challenge_we_vote_id):
        try:
            if positive_value_exists(challenge_id):
                challenge = Challenge.objects.get(id=challenge_id)
                challenge_we_vote_id = challenge.we_vote_id
            else:
                challenge = Challenge.objects.get(we_vote_id=challenge_we_vote_id)
            challenge_found = True
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Challenge can only be edited for existing organization.')
            status += "EDIT_CHALLENGE_PROCESS_NOT_FOUND " + str(e) + " "
    elif positive_value_exists(challenge_title):
        try:
            challenge = Challenge.objects.create(
                challenge_title=challenge_title,
                started_by_voter_we_vote_id=changed_by_voter_we_vote_id,
            )
            challenge_found = True
            challenge_we_vote_id = challenge.we_vote_id
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Challenge could not be created.')
            status += "CREATE_CHALLENGE_PROCESS_FAILED: " + str(e) + " "

    push_seo_friendly_path_changes = False
    try:
        if challenge_found:
            # Update
            if challenge_title is not None:
                challenge.challenge_title = challenge_title
            if challenge_description is not None:
                challenge.challenge_description = challenge_description.strip()
            if take_out_of_draft_mode is not None and positive_value_exists(take_out_of_draft_mode):
                # Take a challenge out of draft mode. Do not support taking it back to draft mode.
                challenge.in_draft_mode = False
            challenge.is_blocked_by_we_vote = positive_value_exists(is_blocked_by_we_vote)
            challenge.final_election_date_as_integer = final_election_date_as_integer
            if is_blocked_by_we_vote_reason is not None:
                challenge.is_blocked_by_we_vote_reason = is_blocked_by_we_vote_reason.strip()
            challenge.is_in_team_review_mode = positive_value_exists(is_in_team_review_mode)
            challenge.is_not_promoted_by_we_vote = positive_value_exists(is_not_promoted_by_we_vote)
            if is_not_promoted_by_we_vote_reason is not None:
                challenge.is_not_promoted_by_we_vote_reason = is_not_promoted_by_we_vote_reason.strip()
            challenge.is_ok_to_promote_on_we_vote = positive_value_exists(is_ok_to_promote_on_we_vote)
            if politician_starter_list_serialized is not None:
                challenge.politician_starter_list_serialized = politician_starter_list_serialized.strip()
            if politician_we_vote_id is not None:
                challenge.politician_we_vote_id = politician_we_vote_id
            if positive_value_exists(challenge.politician_we_vote_id):
                politician_results = politician_manager.retrieve_politician(
                    politician_we_vote_id=challenge.politician_we_vote_id)
                if politician_results['politician_found']:
                    politician = politician_results['politician']
                    from challenge.controllers import update_challenge_from_politician
                    results = update_challenge_from_politician(challenge=challenge, politician=politician)
                    if results['success']:
                        challenge = results['challenge']
                        challenge.date_last_updated_from_politician = localtime(now()).date()
                elif politician_results['success']:
                    # It was a successful query, but politician wasn't found. Remove the politician_we_vote_id
                    challenge.politician_we_vote_id = None
            # If new seo_friendly_path is provided, check to make sure it is not already in use
            # If seo_friendly_path is not provided, only create a new one if challenge.seo_friendly_path
            #  doesn't already exist.
            update_to_new_seo_friendly_path = False
            if seo_friendly_path is not False:
                if positive_value_exists(seo_friendly_path):
                    if seo_friendly_path != challenge.seo_friendly_path:
                        update_to_new_seo_friendly_path = True
            elif not positive_value_exists(challenge.seo_friendly_path):
                update_to_new_seo_friendly_path = True
            if update_to_new_seo_friendly_path:
                seo_results = challenge_manager.generate_seo_friendly_path(
                    base_pathname_string=seo_friendly_path,
                    challenge_title=challenge.challenge_title,
                    challenge_we_vote_id=challenge.we_vote_id)
                if seo_results['success']:
                    seo_friendly_path = seo_results['seo_friendly_path']
                if not positive_value_exists(seo_friendly_path):
                    seo_friendly_path = None
                challenge.seo_friendly_path = seo_friendly_path

            # Now generate_seo_friendly_path if there isn't one
            #  This code is not redundant because of a few rare cases where we can fall-through the logic above.
            if not positive_value_exists(challenge.seo_friendly_path):
                seo_results = challenge_manager.generate_seo_friendly_path(
                    base_pathname_string=challenge.seo_friendly_path,
                    challenge_title=challenge.challenge_title,
                    challenge_we_vote_id=challenge.we_vote_id)
                if seo_results['success']:
                    seo_friendly_path = seo_results['seo_friendly_path']
                    if positive_value_exists(seo_friendly_path):
                        challenge.seo_friendly_path = seo_friendly_path
                        messages.add_message(request, messages.INFO,
                                             'Challenge saved with new SEO friendly path.')
                    else:
                        status += seo_results['status'] + ' '
                else:
                    status += seo_results['status'] + ' '

            if participants_count_minimum_ignored is not None:
                challenge.participants_count_minimum_ignored = positive_value_exists(participants_count_minimum_ignored)
            challenge.save()

            messages.add_message(request, messages.INFO, 'Challenge updated.')
        else:
            messages.add_message(request, messages.ERROR, 'Please provide Challenge Title.')
            return HttpResponseRedirect(reverse('challenge:challenge_new', args=()) +
                                        "?google_civic_election_id=" + str(google_civic_election_id) +
                                        "&challenge_owner_organization_we_vote_id=" +
                                        str(challenge_owner_organization_we_vote_id) +
                                        "&challenge_search=" + str(challenge_search) +
                                        "&state_code=" + str(state_code))
    except Exception as e:
        messages.add_message(request, messages.ERROR, 'Could not save Challenge.'
                                                      ' {error} [type: {error_type}]'.format(error=e,
                                                                                             error_type=type(e)))
        return HttpResponseRedirect(reverse('challenge:challenge_edit', args=(challenge_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&challenge_owner_organization_we_vote_id=" +
                                    str(challenge_owner_organization_we_vote_id) +
                                    "&challenge_search=" + str(challenge_search) +
                                    "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('challenge:challenge_summary', args=(challenge_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&challenge_owner_organization_we_vote_id=" +
                                str(challenge_owner_organization_we_vote_id) +
                                "&challenge_search=" + str(challenge_search) +
                                "&state_code=" + str(state_code))


@login_required
def challenge_edit_view(request, challenge_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.GET.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.GET.get('challenge_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    messages_on_stage = get_messages(request)
    challenge_manager = ChallengeManager()
    challenge_on_stage = None
    status = ""
    results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge_we_vote_id)

    if results['challenge_found']:
        challenge_on_stage = results['challenge']

    election_manager = ElectionManager()
    upcoming_election_list = []
    results = election_manager.retrieve_upcoming_elections()
    if results['success']:
        upcoming_election_list = results['election_list']

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    politician_state_code = ''
    related_challenge_list = []
    if challenge_on_stage and positive_value_exists(challenge_on_stage.politician_we_vote_id):
        try:
            politician_queryset = Politician.objects.using('readonly').all()
            politician = politician_queryset.get(we_vote_id=challenge_on_stage.politician_we_vote_id)
            if positive_value_exists(politician.last_name):
                from challenge.models import Challenge
                queryset = Challenge.objects.using('readonly').all()
                queryset = queryset.exclude(we_vote_id=challenge_we_vote_id)
                queryset = queryset.filter(challenge_title__icontains=politician.first_name)
                queryset = queryset.filter(challenge_title__icontains=politician.last_name)
                related_challenge_list = list(queryset)
            if positive_value_exists(politician.state_code):
                politician_state_code = politician.state_code
        except Exception as e:
            related_challenge_list = []

    # ##################################
    # Show the seo friendly paths for this politician
    path_count = 0
    path_list = []
    if positive_value_exists(challenge_we_vote_id):
        from challenge.models import ChallengeSEOFriendlyPath
        try:
            path_query = ChallengeSEOFriendlyPath.objects.using('readonly').all()
            path_query = path_query.filter(challenge_we_vote_id=challenge_we_vote_id)
            path_count = path_query.count()
            path_list = list(path_query[:4])
        except Exception as e:
            status += 'ERROR_RETRIEVING_FROM_ChallengeSEOFriendlyPath: ' + str(e) + ' '

        if positive_value_exists(challenge_on_stage.seo_friendly_path):
            path_list_modified = []
            for one_path in path_list:
                if challenge_on_stage.seo_friendly_path != one_path.final_pathname_string:
                    path_list_modified.append(one_path)
            path_list = path_list_modified
        path_list = path_list[:3]

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'challenge':                                challenge_on_stage,
        'challenge_owner_organization_we_vote_id':  challenge_owner_organization_we_vote_id,
        'challenge_search':                         challenge_search,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'path_list':                                path_list,
        'politician_state_code':                    politician_state_code,
        'related_challenge_list':                   related_challenge_list,
        'state_list':                               sorted_state_list,
        'upcoming_election_list':                   upcoming_election_list,
        'web_app_root_url':                         web_app_root_url,
    }
    return render(request, 'challenge/challenge_edit.html', template_values)


@login_required
def challenge_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.GET.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.GET.get('challenge_search', '')
    challenge_type_filter = request.GET.get('challenge_type_filter', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    limit_to_opinions_in_state_code = request.GET.get('limit_to_opinions_in_state_code', '')
    limit_to_opinions_in_this_year = convert_to_int(request.GET.get('limit_to_opinions_in_this_year', 0))
    hide_challenges_not_visible_yet = \
        positive_value_exists(request.GET.get('hide_challenges_not_visible_yet', False))
    include_challenges_from_prior_elections = \
        positive_value_exists(request.GET.get('include_challenges_from_prior_elections', False))
    save_changes = request.GET.get('save_changes', False)
    save_changes = positive_value_exists(save_changes)
    show_all = request.GET.get('show_all', False)
    show_blocked_challenges = \
        positive_value_exists(request.GET.get('show_blocked_challenges', False))
    show_challenges_in_draft = \
        positive_value_exists(request.GET.get('show_challenges_in_draft', False))
    show_challenges_linked_to_politicians = \
        positive_value_exists(request.GET.get('show_challenges_linked_to_politicians', False))
    show_more = request.GET.get('show_more', False)  # Show up to 1,000 organizations
    show_issues = request.GET.get('show_issues', '')
    show_organizations_without_email = positive_value_exists(request.GET.get('show_organizations_without_email', False))
    sort_by = request.GET.get('sort_by', '')
    state_code = request.GET.get('state_code', '')
    status = ''
    success = True
    update_challenges_from_politicians = \
        positive_value_exists(request.GET.get('update_challenges_from_politicians', False))
    update_challenges_that_need_organization = \
        positive_value_exists(request.GET.get('update_challenges_that_need_organization', False))

    messages_on_stage = get_messages(request)
    challenge_manager = ChallengeManager()
    challenge_list_to_update = []

    # ################################################
    # Maintenance script section START
    # ################################################

    clean_challenges_with_dead_politician_we_vote_id = True
    # If a Challenge entry has a politician_we_vote_id which no longer exists, remove the seo_friendly_path
    #  so that entry doesn't block the use of that seo_friendly_path
    if clean_challenges_with_dead_politician_we_vote_id:
        number_to_update = 5000  # Set to 5,000 at a time
        politician_we_vote_id_list = []
        total_to_update_after = 0
        try:
            queryset = Challenge.objects.using('readonly').all()
            queryset = queryset.exclude(
                Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=''))
            queryset = queryset.exclude(politician_we_vote_id_verified=True)
            total_to_update = queryset.count()
            total_to_update_after = total_to_update - number_to_update if total_to_update > number_to_update else 0
            challenge_list_to_update = list(queryset[:number_to_update])
            for one_challenge in challenge_list_to_update:
                if positive_value_exists(one_challenge.politician_we_vote_id):
                    if one_challenge.politician_we_vote_id not in politician_we_vote_id_list:
                        politician_we_vote_id_list.append(one_challenge.politician_we_vote_id)
        except Exception as e:
            status += "CHALLENGE_CLEAN_QUERY_FAILED: " + str(e) + " "

        politician_we_vote_ids_not_found_list = []
        if len(politician_we_vote_id_list) > 0:
            queryset = Politician.objects.using('readonly').all()
            queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
            queryset = queryset.values_list('we_vote_id', flat=True).distinct()
            politician_we_vote_ids_found_list = list(queryset)
            politician_we_vote_ids_not_found_list = politician_we_vote_id_list.copy()
            for one_politician_we_vote_id in politician_we_vote_ids_found_list:
                politician_we_vote_ids_not_found_list.remove(one_politician_we_vote_id)
        update_list = []
        for one_challenge in challenge_list_to_update:
            one_challenge.politician_we_vote_id_verified = True
            if one_challenge.politician_we_vote_id in politician_we_vote_ids_not_found_list:
                one_challenge.date_last_updated_from_politician = localtime(now()).date()
                one_challenge.politician_we_vote_id = None
                one_challenge.seo_friendly_path = None
            update_list.append(one_challenge)

        if len(update_list) > 0:
            try:
                Challenge.objects.bulk_update(
                    update_list,
                    ['date_last_updated_from_politician',
                     'politician_we_vote_id',
                     'politician_we_vote_id_verified',
                     'seo_friendly_path'])
                messages.add_message(request, messages.INFO,
                                     "{updates_made:,} challenge entries cleaned from missing politicians. "
                                     "{total_to_update_after:,} remaining."
                                     "".format(total_to_update_after=total_to_update_after,
                                               updates_made=len(challenge_list_to_update)))
            except Exception as e:
                messages.add_message(
                    request, messages.ERROR,
                    "ERROR with clean_challenges_with_dead_politician_we_vote_id: {e} "
                    "politician_we_vote_ids_not_found_list: {politician_we_vote_ids_not_found_list}"
                    "".format(e=e,
                              politician_we_vote_ids_not_found_list=politician_we_vote_ids_not_found_list))

    # If a Challenge entry has a politician_we_vote_id, but no organization_we_vote_id,
    #  then add organization_we_vote_id to the entry
    if update_challenges_that_need_organization:
        number_to_update = 5000
        politician_we_vote_id_list = []
        total_to_update_after = 0
        update_count = 0
        try:
            queryset = Challenge.objects.all()  # Cannot be 'readonly' because we need to update below.
            if positive_value_exists(state_code):
                queryset = queryset.filter(state_code__iexact=state_code)
            queryset = queryset.exclude(
                Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=''))
            # NOTE: IF instead of checking for existing organization_we_vote_id, we use an analysis boolean,
            #  we could use this script to verify we have stored the correct organization_we_vote_id
            queryset = queryset.filter(
                Q(organization_we_vote_id__isnull=True) | Q(organization_we_vote_id=''))
            total_to_update = queryset.count()
            total_to_update_after = total_to_update - number_to_update if total_to_update > number_to_update else 0
            challenge_list_to_update = list(queryset[:number_to_update])
            for one_challenge in challenge_list_to_update:
                if positive_value_exists(one_challenge.politician_we_vote_id):
                    if one_challenge.politician_we_vote_id not in politician_we_vote_id_list:
                        politician_we_vote_id_list.append(one_challenge.politician_we_vote_id)
        except Exception as e:
            status += "CHALLENGE_ORG_LINKS_QUERY_FAILED: " + str(e) + " "

        # Organization table has the master link to politician_we_vote_id, which is why we use that table
        organization_dict_by_politician_we_vote_id = {}
        organization_list = []
        politician_we_vote_ids_not_found_list = []
        if len(politician_we_vote_id_list) > 0:
            queryset = Organization.objects.using('readonly').all()
            queryset = queryset.filter(politician_we_vote_id__in=politician_we_vote_id_list)
            organization_list = list(queryset)
        for one_organization in organization_list:
            organization_dict_by_politician_we_vote_id[one_organization.politician_we_vote_id] = one_organization

        if len(organization_list) == 0:
            messages.add_message(
                request, messages.ERROR,
                "No organizations found by politician_we_vote_id from the Campaigns reviewed. "
                "politician_we_vote_id_list: {politician_we_vote_id_list}"
                "".format(politician_we_vote_id_list=politician_we_vote_id_list))

        update_list = []
        for one_challenge in challenge_list_to_update:
            if one_challenge.politician_we_vote_id in organization_dict_by_politician_we_vote_id:
                organization = organization_dict_by_politician_we_vote_id[one_challenge.politician_we_vote_id]
                one_challenge.organization_we_vote_id = organization.we_vote_id
                update_list.append(one_challenge)
                update_count += 1
            else:
                politician_we_vote_ids_not_found_list.append(one_challenge.politician_we_vote_id)

        if len(update_list) > 0:
            try:
                Challenge.objects.bulk_update(update_list, ['organization_we_vote_id'])
                messages.add_message(
                    request, messages.INFO,
                    "{updates_made:,} challenge entries updated with organization_we_vote_id "
                    "out of {updates_planned}. "
                    "{total_to_update_after:,} remaining. "
                    "politician_we_vote_ids_not_found_list: {politician_we_vote_ids_not_found_list}"
                    "".format(
                        politician_we_vote_ids_not_found_list=politician_we_vote_ids_not_found_list,
                        total_to_update_after=total_to_update_after,
                        updates_planned=len(challenge_list_to_update),
                        updates_made=update_count))
            except Exception as e:
                messages.add_message(
                    request, messages.ERROR,
                    "ERROR with update_challenges_that_need_organization: {e} "
                    "politician_we_vote_ids_not_found_list: {politician_we_vote_ids_not_found_list}"
                    "".format(e=e,
                              politician_we_vote_ids_not_found_list=politician_we_vote_ids_not_found_list))
        # else:
        #     messages.add_message(
        #         request, messages.ERROR,
        #         "No updates to be made. "
        #         "politician_we_vote_id_list: {politician_we_vote_id_list}"
        #         "".format(politician_we_vote_id_list=politician_we_vote_id_list))

    # Bring over updated politician profile photos to the challenge entries with politician_we_vote_id
    if update_challenges_from_politicians:
        challenge_list = []
        number_to_update = 5000  # Set to 5,000 at a time
        total_to_update_after = 0
        try:
            queryset = Challenge.objects.all()
            queryset = queryset.exclude(
                Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=''))
            # if positive_value_exists(state_code):
            #     queryset = queryset.filter(state_code__iexact=state_code)
            # Ignore Campaigns which have been updated in the last 6 months: date_last_updated_from_politician
            today = datetime.now().date()
            six_months_ago = today - timedelta(weeks=26)
            queryset = queryset.exclude(date_last_updated_from_politician__gt=six_months_ago)
            total_to_update = queryset.count()
            total_to_update_after = total_to_update - number_to_update if total_to_update > number_to_update else 0
            challenge_list = list(queryset[:number_to_update])
        except Exception as e:
            status += "CHALLENGE_QUERY_FAILED: " + str(e) + " "

        # Retrieve all related politicians with one query
        politician_we_vote_id_list = []
        for challenge in challenge_list:
            if positive_value_exists(challenge.politician_we_vote_id):
                if challenge.politician_we_vote_id not in politician_we_vote_id_list:
                    politician_we_vote_id_list.append(challenge.politician_we_vote_id)

        politician_list_by_challenge_we_vote_id = {}
        if len(politician_we_vote_id_list) > 0:
            queryset = Politician.objects.using('readonly').all()
            queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
            politician_list = list(queryset)
            for one_politician in politician_list:
                if positive_value_exists(one_politician.linked_challenge_we_vote_id) and \
                        one_politician.linked_challenge_we_vote_id not in politician_list_by_challenge_we_vote_id:
                    politician_list_by_challenge_we_vote_id[one_politician.linked_challenge_we_vote_id] = one_politician

        # Loop through all the challenges, and update them with some politician data
        politician_we_vote_id_remaining_list = politician_we_vote_id_list.copy()
        if len(challenge_list) > 0:
            challenge_update_errors = 0
            challenges_updated = 0
            challenges_without_changes = 0
            update_list = []
            from challenge.controllers import update_challenge_from_politician
            for challenge in challenge_list:
                if challenge.we_vote_id in politician_list_by_challenge_we_vote_id:
                    politician = politician_list_by_challenge_we_vote_id[challenge.we_vote_id]
                    politician_we_vote_id_remaining_list.remove(politician.we_vote_id)
                else:
                    politician = None
                    challenge.date_last_updated_from_politician = localtime(now()).date()
                    challenge.politician_we_vote_id = None
                    challenge.seo_friendly_path = None
                    challenge.save()
                if not politician or not hasattr(politician, 'we_vote_id'):
                    continue
                results = update_challenge_from_politician(challenge=challenge, politician=politician)
                if results['success']:
                    save_changes = results['save_changes']
                    challenge = results['challenge']
                    challenge.date_last_updated_from_politician = localtime(now()).date()
                    update_list.append(challenge)
                    # challenge.save()
                    if save_changes:
                        challenges_updated += 1
                    else:
                        challenges_without_changes += 1
                else:
                    challenge_update_errors += 1
                    status += results['status']
            if challenges_updated > 0:
                try:
                    Challenge.objects.bulk_update(
                        update_list,
                        ['we_vote_hosted_challenge_photo_large_url',
                         'we_vote_hosted_challenge_photo_medium_url',
                         'we_vote_hosted_challenge_photo_small_url',
                         'date_last_updated_from_politician',
                         'seo_friendly_path',
                         'we_vote_hosted_profile_image_url_large',
                         'we_vote_hosted_profile_image_url_medium',
                         'we_vote_hosted_profile_image_url_tiny'])
                    messages.add_message(request, messages.INFO,
                                         "{updates_made:,} challenge entries updated from politicians. "
                                         "{total_to_update_after:,} remaining."
                                         "".format(total_to_update_after=total_to_update_after,
                                                   updates_made=challenges_updated))
                except Exception as e:
                    messages.add_message(
                        request, messages.ERROR,
                        "ERROR with update_challenge_list_from_politicians_script: {e} "
                        "politician_we_vote_id_remaining_list: {politician_we_vote_id_remaining_list} "
                        "{total_to_update_after:,} remaining."
                        "".format(e=e,
                                  total_to_update_after=total_to_update_after,
                                  politician_we_vote_id_remaining_list=politician_we_vote_id_remaining_list))
                    second_save_failed = False
                    for challenge in update_list:
                        try:
                            challenge.save()
                        except Exception as e:
                            status += "CHALLENGE_SAVE_FAILED: " + str(e) + " "
                            second_save_failed = True
                    if second_save_failed:
                        messages.add_message(
                            request, messages.ERROR,
                            "Second save failed, status: {status} remaining."
                            "".format(status=status))

    # ################################################
    # Maintenance script section END
    # ################################################

    challenge_we_vote_ids_in_order = []
    if challenge_owner_organization_we_vote_id:
        # Find existing order
        challenge_owner_list_with_order = challenge_manager.retrieve_challenge_owner_list(
            organization_we_vote_id=challenge_owner_organization_we_vote_id,
            has_order_in_list=True,
            read_only=False)
        for challenge_owner in challenge_owner_list_with_order:
            challenge_we_vote_ids_in_order.append(challenge_owner.challenge_we_vote_id)

        if save_changes:
            challenge_we_vote_id_list_from_owner_organization_we_vote_id = \
                challenge_manager.fetch_challenge_we_vote_id_list_from_owner_organization_we_vote_id(
                    challenge_owner_organization_we_vote_id)
            for one_challenge_we_vote_id in challenge_we_vote_id_list_from_owner_organization_we_vote_id:
                one_challenge_order_changed_name = str(one_challenge_we_vote_id) + '_order_changed'
                order_changed = positive_value_exists(request.GET.get(one_challenge_order_changed_name, 0))
                if positive_value_exists(order_changed):
                    # Remove existing
                    try:
                        challenge_we_vote_ids_in_order.remove(one_challenge_we_vote_id)
                    except Exception as e:
                        pass
                    # Find out the new placement for this item
                    one_challenge_order_in_list_name = str(one_challenge_we_vote_id) + '_order_in_list'
                    order_in_list = request.GET.get(one_challenge_order_in_list_name, '')
                    if positive_value_exists(order_in_list):
                        order_in_list = convert_to_int(order_in_list)
                        index_from_order = order_in_list - 1
                        challenge_we_vote_ids_in_order.insert(index_from_order, one_challenge_we_vote_id)
                    else:
                        # Reset existing value
                        for challenge_owner in challenge_owner_list_with_order:
                            if challenge_owner.challenge_we_vote_id == one_challenge_we_vote_id:
                                challenge_owner.order_in_list = None
                                challenge_owner.save()

        if len(challenge_we_vote_ids_in_order) > 0:
            # Re-save the order of all challenges
            challenge_owner_list = challenge_manager.retrieve_challenge_owner_list(
                challenge_we_vote_id_list=challenge_we_vote_ids_in_order,
                organization_we_vote_id=challenge_owner_organization_we_vote_id,
                read_only=False)
            new_order = 0
            for challenge_we_vote_id in challenge_we_vote_ids_in_order:
                for challenge_owner in challenge_owner_list:
                    if challenge_we_vote_id == challenge_owner.challenge_we_vote_id:
                        new_order += 1
                        challenge_owner.order_in_list = new_order
                        challenge_owner.save()

    challenge_list_query = Challenge.objects.using('readonly').all()
    if positive_value_exists(hide_challenges_not_visible_yet):
        challenge_list_query = challenge_list_query.filter(
            Q(participants_count__gte=PARTICIPANTS_COUNT_MINIMUM_FOR_LISTING) |
            Q(participants_count_minimum_ignored=True))

    final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
    if positive_value_exists(include_challenges_from_prior_elections):
        pass
    else:
        challenge_list_query = challenge_list_query.filter(
            Q(final_election_date_as_integer__isnull=True) |
            Q(final_election_date_as_integer__gt=final_election_date_plus_cool_down))

    if positive_value_exists(show_blocked_challenges):
        challenge_list_query = challenge_list_query.filter(is_blocked_by_we_vote=True)
    else:
        challenge_list_query = challenge_list_query.filter(is_blocked_by_we_vote=False)

    if positive_value_exists(show_challenges_in_draft):
        challenge_list_query = challenge_list_query.filter(in_draft_mode=True)
    else:
        challenge_list_query = challenge_list_query.filter(in_draft_mode=False)

    if positive_value_exists(show_challenges_linked_to_politicians):
        challenge_list_query = challenge_list_query.filter(politician_we_vote_id__isnull=False)
    else:
        challenge_list_query = challenge_list_query.filter(
            Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id__exact=''))

    if positive_value_exists(challenge_owner_organization_we_vote_id):
        challenge_we_vote_id_list_from_owner_organization_we_vote_id = \
            challenge_manager.fetch_challenge_we_vote_id_list_from_owner_organization_we_vote_id(
                challenge_owner_organization_we_vote_id)
        challenge_list_query = challenge_list_query.filter(
            we_vote_id__in=challenge_we_vote_id_list_from_owner_organization_we_vote_id)

    client_list_query = Organization.objects.using('readonly').all()
    client_list_query = client_list_query.filter(chosen_feature_package__isnull=False)
    client_organization_list = list(client_list_query)

    challenge_to_repair_count = 0
    if positive_value_exists(sort_by):
        # if sort_by == "twitter":
        #     challenge_list_query = \
        #         challenge_list_query.order_by('organization_name').order_by('-twitter_followers_count')
        # else:
        challenge_list_query = challenge_list_query.order_by('-participants_count')
    else:
        challenge_list_query = challenge_list_query.order_by('-participants_count')

    if positive_value_exists(challenge_search):
        search_words = challenge_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(challenge_title__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(challenge_description__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(politician_we_vote_id=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_we_vote_id=one_word)
            filters.append(new_filter)

            new_filter = Q(seo_friendly_path__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(started_by_voter_we_vote_id=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                challenge_list_query = challenge_list_query.filter(final_filters)

    challenge_count = challenge_list_query.count()
    messages.add_message(request, messages.INFO,
                         '{challenge_count:,} challenges found.'.format(challenge_count=challenge_count))
    if positive_value_exists(challenge_to_repair_count):
        messages.add_message(request, messages.INFO,
                             '{challenge_to_repair_count:,} challenges to repair.'
                             ''.format(challenge_to_repair_count=challenge_to_repair_count))

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        challenge_list = challenge_list_query[:1000]
    elif positive_value_exists(show_all):
        challenge_list = challenge_list_query
    else:
        challenge_list = challenge_list_query[:50]

    if len(challenge_we_vote_ids_in_order) > 0:
        modified_challenge_list = []
        challenge_we_vote_id_already_placed = []
        for challenge_we_vote_id in challenge_we_vote_ids_in_order:
            for challenge in challenge_list:
                if challenge_we_vote_id == challenge.we_vote_id:
                    modified_challenge_list.append(challenge)
                    challenge_we_vote_id_already_placed.append(challenge.we_vote_id)
        # Now add the rest
        for challenge in challenge_list:
            if challenge.we_vote_id not in challenge_we_vote_id_already_placed:
                modified_challenge_list.append(challenge)
                challenge_we_vote_id_already_placed.append(challenge.we_vote_id)
        challenge_list = modified_challenge_list

    # Now loop through these organizations and add owners
    modified_challenge_list = []
    politician_we_vote_id_list = []
    for challenge in challenge_list:
        challenge.challenge_owner_list = challenge_manager.retrieve_challenge_owner_list(
            challenge_we_vote_id_list=[challenge.we_vote_id],
            viewer_is_owner=True,
            read_only=True)
        challenge.chip_in_total = StripeManager.retrieve_chip_in_total('', challenge.we_vote_id)
        modified_challenge_list.append(challenge)
        if positive_value_exists(challenge.politician_we_vote_id):
            politician_we_vote_id_list.append(challenge.politician_we_vote_id)

    if len(politician_we_vote_id_list) > 0:
        modified_challenge_list2 = []
        queryset = Politician.objects.using('readonly').all()
        queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(queryset)
        for challenge in modified_challenge_list:
            for one_politician in politician_list:
                if one_politician.we_vote_id == challenge.politician_we_vote_id:
                    challenge.linked_politician_state_code = one_politician.state_code
            modified_challenge_list2.append(challenge)
        modified_challenge_list = modified_challenge_list2

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    # Calculate the number of Challenge entries with politician_we_vote_id
    #  that do NOT have organization_we_vote_id
    queryset = Challenge.objects.using('readonly').all()
    # DALE 2024-07-23 I don't think Challenge data has state_code in it yet
    if positive_value_exists(state_code):
        queryset = queryset.filter(state_code__iexact=state_code)
    queryset = queryset.exclude(Q(politician_we_vote_id__isnull=True) |
                                Q(politician_we_vote_id__exact=''))
    queryset = queryset.filter(Q(organization_we_vote_id__isnull=True) |
                               Q(organization_we_vote_id__exact=''))
    challenges_that_need_organization = queryset.count()

    if 'localhost' in WEB_APP_ROOT_URL:
        web_app_root_url = 'https://localhost:3000'
    else:
        web_app_root_url = 'https://quality.WeVote.US'
    template_values = {
        'challenges_that_need_organization':         challenges_that_need_organization,
        'challenge_list':                           modified_challenge_list,
        'challenge_owner_organization_we_vote_id':  challenge_owner_organization_we_vote_id,
        'challenge_search':                         challenge_search,
        'challenge_type_filter':                    challenge_type_filter,
        'challenge_types':                          [],
        'client_organization_list':                 client_organization_list,
        'final_election_date_plus_cool_down':       final_election_date_plus_cool_down,
        'google_civic_election_id':                 google_civic_election_id,
        'hide_challenges_not_visible_yet':           hide_challenges_not_visible_yet,
        'include_challenges_from_prior_elections':   include_challenges_from_prior_elections,
        'limit_to_opinions_in_state_code':          limit_to_opinions_in_state_code,
        'limit_to_opinions_in_this_year':           limit_to_opinions_in_this_year,
        'messages_on_stage':                        messages_on_stage,
        'show_all':                                 show_all,
        'show_blocked_challenges':                   show_blocked_challenges,
        'show_challenges_in_draft':                  show_challenges_in_draft,
        'show_challenges_linked_to_politicians':     show_challenges_linked_to_politicians,
        'show_issues':                              show_issues,
        'show_more':                                show_more,
        'show_organizations_without_email':         show_organizations_without_email,
        'sort_by':                                  sort_by,
        'state_code':                               state_code,
        'state_list':                               sorted_state_list,
        'web_app_root_url':                         web_app_root_url,
    }
    return render(request, 'challenge/challenge_list.html', template_values)


@login_required
def challenge_summary_view(request, challenge_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.GET.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.GET.get('challenge_search', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', '')
    status = ''

    messages_on_stage = get_messages(request)
    challenge_manager = ChallengeManager()
    challenge = None

    results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge_we_vote_id)

    if results['challenge_found']:
        challenge = results['challenge']
    else:
        status += results['status']
        messages.add_message(request, messages.ERROR,
                             'Challenge \'{challenge_we_vote_id}\' not found: {status}.'
                             ''.format(
                                 challenge_we_vote_id=challenge_we_vote_id,
                                 status=status))
        return HttpResponseRedirect(reverse('challenge:challenge_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    # ##################################
    # Show the seo friendly paths for this challenge
    path_count = 0
    path_list = []
    if positive_value_exists(challenge_we_vote_id):
        from challenge.models import ChallengeSEOFriendlyPath
        try:
            path_query = ChallengeSEOFriendlyPath.objects.all()
            path_query = path_query.filter(challenge_we_vote_id=challenge_we_vote_id)
            path_count = path_query.count()
            path_list = list(path_query[:4])
        except Exception as e:
            status += 'ERROR_RETRIEVING_FROM_ChallengeSEOFriendlyPath: ' + str(e) + ' '

        if positive_value_exists(challenge.seo_friendly_path):
            path_list_modified = []
            for one_path in path_list:
                if challenge.seo_friendly_path != one_path.final_pathname_string:
                    path_list_modified.append(one_path)
            path_list = path_list_modified
        path_list = path_list[:3]

    challenge_owner_list_modified = []
    challenge_owner_list = challenge_manager.retrieve_challenge_owner_list(
        challenge_we_vote_id_list=[challenge_we_vote_id],
        viewer_is_owner=True
    )

    for challenge_owner in challenge_owner_list:
        challenge_owner_list_modified.append(challenge_owner)

    challenge_politician_list_modified = []
    challenge_politician_list = challenge_manager.retrieve_challenge_politician_list(
        challenge_we_vote_id=challenge_we_vote_id,
        read_only=True,
    )

    for challenge_politician in challenge_politician_list:
        challenge_politician_list_modified.append(challenge_politician)

    position_list = []
    participants_query = ChallengeParticipant.objects.using('readonly').all()
    participants_query = participants_query.filter(challenge_we_vote_id=challenge_we_vote_id)
    participants_query = participants_query.filter(visible_to_public=True)
    challenge_participants_count = participants_query.count()
    challenge_participant_list = list(participants_query[:4])

    if 'localhost' in CHALLENGES_ROOT_URL:
        challenges_site_root_url = 'https://localhost:3000'
    else:
        challenges_site_root_url = 'https://WeVote.US'
    template_values = {
        'challenges_site_root_url':                 challenges_site_root_url,
        'challenge':                                challenge,
        'challenge_owner_list':                     challenge_owner_list_modified,
        'challenge_owner_organization_we_vote_id':  challenge_owner_organization_we_vote_id,
        'challenge_politician_list':                challenge_politician_list_modified,
        'challenge_search':                         challenge_search,
        'challenge_participants_count':             challenge_participants_count,
        'challenge_participant_list':               challenge_participant_list,
        'google_civic_election_id':                 google_civic_election_id,
        'messages_on_stage':                        messages_on_stage,
        'path_count':                               path_count,
        'path_list':                                path_list,
        'position_list':                            position_list,
        'state_code':                               state_code,
    }
    return render(request, 'challenge/challenge_summary.html', template_values)


@login_required
def challenge_participant_list_view(request, challenge_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.GET.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.GET.get('challenge_search', '')
    challenge_type_filter = request.GET.get('challenge_type_filter', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    limit_to_opinions_in_state_code = request.GET.get('limit_to_opinions_in_state_code', '')
    limit_to_opinions_in_this_year = convert_to_int(request.GET.get('limit_to_opinions_in_this_year', 0))
    sort_by = request.GET.get('sort_by', '')
    state_code = request.GET.get('state_code', '')
    show_all = request.GET.get('show_all', False)
    show_more = request.GET.get('show_more', False)  # Show up to 1,000 organizations
    show_issues = request.GET.get('show_issues', '')
    only_show_participants_with_endorsements = \
        positive_value_exists(request.GET.get('only_show_participants_with_endorsements', False))
    show_participants_not_visible_to_public = \
        positive_value_exists(request.GET.get('show_participants_not_visible_to_public', False))

    messages_on_stage = get_messages(request)

    challenge = Challenge.objects.get(we_vote_id=challenge_we_vote_id)
    challenge_title = challenge.challenge_title

    participants_query = ChallengeParticipant.objects.all()
    participants_query = participants_query.filter(challenge_we_vote_id=challenge_we_vote_id)

    if positive_value_exists(only_show_participants_with_endorsements):
        participants_query = participants_query.exclude(
            Q(custom_message_for_friends__isnull=True) |
            Q(custom_message_for_friends__exact='')
        )

    participants_query = participants_query.order_by('-date_joined')

    if positive_value_exists(show_participants_not_visible_to_public):
        pass
    else:
        # Default to only show visible_to_public
        participants_query = participants_query.filter(visible_to_public=True)

    # if positive_value_exists(state_code):
    #     participants_query = participants_query.filter(state_served_code__iexact=state_code)
    #
    # if positive_value_exists(challenge_type_filter):
    #     if challenge_type_filter == UNKNOWN:
    #         # Make sure to also show organizations that are not specified
    #         participants_query = participants_query.filter(
    #             Q(organization_type__iexact=challenge_type_filter) |
    #             Q(organization_type__isnull=True) |
    #             Q(organization_type__exact='')
    #         )
    #     else:
    #         participants_query = participants_query.filter(organization_type__iexact=challenge_type_filter)
    # else:
    #     # By default, don't show individuals
    #     participants_query = participants_query.exclude(organization_type__iexact=INDIVIDUAL)

    if positive_value_exists(challenge_search):
        search_words = challenge_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(participant_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(custom_message_for_friends__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_we_vote_id=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                participants_query = participants_query.filter(final_filters)

    participants_count = participants_query.count()
    messages.add_message(request, messages.INFO,
                         'Showing {participants_count:,} challenge participants.'.format(participants_count=participants_count))

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        participant_list = participants_query[:1000]
    elif positive_value_exists(show_all):
        participant_list = participants_query
    else:
        participant_list = participants_query[:200]

    for participant in participant_list:
        participant.chip_in_total = StripeManager.retrieve_chip_in_total(participant.voter_we_vote_id,
                                                                       participant.challenge_we_vote_id)


    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'challenge_owner_organization_we_vote_id':  challenge_owner_organization_we_vote_id,
        'challenge_search':                         challenge_search,
        'challenge_we_vote_id':                     challenge_we_vote_id,
        'challenge_title':                          challenge_title,
        'google_civic_election_id':                 google_civic_election_id,
        'limit_to_opinions_in_state_code':          limit_to_opinions_in_state_code,
        'limit_to_opinions_in_this_year':           limit_to_opinions_in_this_year,
        'messages_on_stage':                        messages_on_stage,
        'challenge_type_filter':                    challenge_type_filter,
        'challenge_types':                          [],
        'participant_list':                         participant_list,
        'show_all':                                 show_all,
        'show_issues':                              show_issues,
        'show_more':                                show_more,
        'show_participants_not_visible_to_public':  show_participants_not_visible_to_public,
        'only_show_participants_with_endorsements': only_show_participants_with_endorsements,
        'sort_by':                                  sort_by,
        'state_code':                               state_code,
        'state_list':                               sorted_state_list,
    }
    return render(request, 'challenge/challenge_participant_list.html', template_values)


@login_required
def challenge_participant_list_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_owner_organization_we_vote_id = request.POST.get('challenge_owner_organization_we_vote_id', '')
    challenge_search = request.POST.get('challenge_search', '')
    challenge_we_vote_id = request.POST.get('challenge_we_vote_id', '')
    google_civic_election_id = request.POST.get('google_civic_election_id', '')
    incoming_challenge_participant_we_vote_id = request.POST.get('incoming_challenge_participant_we_vote_id', '')
    incoming_challenge_custom_message_for_friends = request.POST.get('incoming_challenge_custom_message_for_friends', '')
    incoming_challenge_participant_wants_visibility = request.POST.get('incoming_challenge_participant_wants_visibility', '')
    incoming_visibility_blocked_by_we_vote = request.POST.get('incoming_visibility_blocked_by_we_vote', '')
    state_code = request.POST.get('state_code', '')
    show_all = request.POST.get('show_all', False)
    show_more = request.POST.get('show_more', False)  # Show up to 1,000 organizations
    only_show_participants_with_endorsements = \
        positive_value_exists(request.POST.get('only_show_participants_with_endorsements', False))
    show_participants_not_visible_to_public = \
        positive_value_exists(request.POST.get('show_participants_not_visible_to_public', False))

    update_message = ''
    voter_manager = VoterManager()
    organization_manager = OrganizationManager()

    challenge_participant_organization_we_vote_id = ''
    challenge_participant_voter_we_vote_id = ''
    if positive_value_exists(incoming_challenge_participant_we_vote_id):
        # We allow either organization_we_vote_id or voter_we_vote_id
        if 'org' in incoming_challenge_participant_we_vote_id:
            challenge_participant_organization_we_vote_id = incoming_challenge_participant_we_vote_id
            challenge_participant_voter_we_vote_id = \
                voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                    challenge_participant_organization_we_vote_id)
        elif 'voter' in incoming_challenge_participant_we_vote_id:
            challenge_participant_voter_we_vote_id = incoming_challenge_participant_we_vote_id
            challenge_participant_organization_we_vote_id = \
                voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(
                    incoming_challenge_participant_we_vote_id)

    politician_we_vote_id = ''
    if positive_value_exists(challenge_we_vote_id):
        try:
            challenge_on_stage = Challenge.objects.get(we_vote_id=challenge_we_vote_id)
            politician_we_vote_id = challenge_on_stage.politician_we_vote_id
        except Exception as e:
            politician_we_vote_id = ''
    politician_we_vote_id_list = []
    if positive_value_exists(politician_we_vote_id):
        politician_we_vote_id_list.append(politician_we_vote_id)

    # 2024-07-23
    if positive_value_exists(politician_we_vote_id):
        # If this Challenge is linked to a politician, don't work with classic ChallengeParticipants
        challenge_we_vote_id_list_to_refresh = [challenge_we_vote_id]
        error_message_to_print = ''
        info_message_to_print = ''
        # #############################
        # Create FollowOrganization entries
        #  From PUBLIC positions
        results = create_followers_from_positions(
            friends_only_positions=False,
            politicians_to_follow_we_vote_id_list=politician_we_vote_id_list)
        if positive_value_exists(results['error_message_to_print']):
            error_message_to_print += results['error_message_to_print']
        if positive_value_exists(results['info_message_to_print']):
            info_message_to_print += results['info_message_to_print']
        challenge_we_vote_id_list_changed = results['challenge_we_vote_id_list_to_refresh']
        if len(challenge_we_vote_id_list_changed) > 0:
            challenge_we_vote_id_list_to_refresh = \
                list(set(challenge_we_vote_id_list_changed + challenge_we_vote_id_list_to_refresh))
        # From FRIENDS_ONLY positions
        results = create_followers_from_positions(
            friends_only_positions=True,
            politicians_to_follow_we_vote_id_list=politician_we_vote_id_list)
        challenge_we_vote_id_list_changed = results['challenge_we_vote_id_list_to_refresh']
        if len(challenge_we_vote_id_list_changed) > 0:
            challenge_we_vote_id_list_to_refresh = \
                list(set(challenge_we_vote_id_list_changed + challenge_we_vote_id_list_to_refresh))

        follow_organization_manager = FollowOrganizationManager()
        participants_count = follow_organization_manager.fetch_follow_organization_count(
            following_status=FOLLOWING,
            organization_we_vote_id_being_followed=challenge_on_stage.organization_we_vote_id)
        opposers_count = follow_organization_manager.fetch_follow_organization_count(
            following_status=FOLLOW_DISLIKE,
            organization_we_vote_id_being_followed=challenge_on_stage.organization_we_vote_id)
        challenge_on_stage.opposers_count = opposers_count
        challenge_on_stage.participants_count = participants_count
        challenge_on_stage.save()

        if positive_value_exists(results['error_message_to_print']):
            error_message_to_print += results['error_message_to_print']
        if positive_value_exists(results['info_message_to_print']):
            info_message_to_print += results['info_message_to_print']
        messages.add_message(request, messages.INFO, 'ChallengeParticipant linked to Politician -- cannot process.')
        return HttpResponseRedirect(reverse('challenge:participant_list', args=(challenge_we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    "&challenge_owner_organization_we_vote_id=" +
                                    str(challenge_owner_organization_we_vote_id) +
                                    "&challenge_search=" + str(challenge_search) +
                                    "&state_code=" + str(state_code) +
                                    "&only_show_participants_with_endorsements=" +
                                    str(only_show_participants_with_endorsements) +
                                    "&show_participants_not_visible_to_public=" + str(
            show_participants_not_visible_to_public)
                                    )

    participants_query = ChallengeParticipant.objects.all()
    participants_query = participants_query.filter(challenge_we_vote_id=challenge_we_vote_id)

    if positive_value_exists(only_show_participants_with_endorsements):
        participants_query = participants_query.exclude(
            Q(custom_message_for_friends__isnull=True) |
            Q(custom_message_for_friends__exact='')
        )

    participants_query = participants_query.order_by('-date_joined')

    if positive_value_exists(show_participants_not_visible_to_public):
        pass
    else:
        # Default to only show visible_to_public
        participants_query = participants_query.filter(visible_to_public=True)

    if positive_value_exists(challenge_search):
        search_words = challenge_search.split()
        for one_word in search_words:
            filters = []
            new_filter = Q(participant_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(custom_message_for_friends__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id=one_word)
            filters.append(new_filter)

            new_filter = Q(organization_we_vote_id=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                participants_query = participants_query.filter(final_filters)

    # Limit to only showing 200 on screen
    if positive_value_exists(show_more):
        participant_list = participants_query[:1000]
    elif positive_value_exists(show_all):
        participant_list = participants_query
    else:
        participant_list = participants_query[:200]

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    # Create new ChallengeParticipant
    if positive_value_exists(challenge_participant_organization_we_vote_id) or \
            positive_value_exists(challenge_participant_voter_we_vote_id):
        do_not_create = False
        participant_already_exists = False
        status = ""
        # Does it already exist?
        try:
            if positive_value_exists(challenge_participant_organization_we_vote_id):
                ChallengeParticipant.objects.get(
                    challenge_we_vote_id=challenge_we_vote_id,
                    organization_we_vote_id=challenge_participant_organization_we_vote_id)
                participant_already_exists = True
            elif positive_value_exists(challenge_participant_voter_we_vote_id):
                ChallengeParticipant.objects.get(
                    challenge_we_vote_id=challenge_we_vote_id,
                    voter_we_vote_id=challenge_participant_voter_we_vote_id)
                participant_already_exists = True
        except ChallengeParticipant.DoesNotExist:
            participant_already_exists = False
        except Exception as e:
            do_not_create = True
            messages.add_message(request, messages.ERROR, 'ChallengeParticipant already exists.')
            status += "ADD_CHALLENGE_PARTICIPANT_ALREADY_EXISTS " + str(e) + " "

        if not do_not_create and not participant_already_exists:
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(challenge_participant_organization_we_vote_id)
            if organization_results['organization_found']:
                participant_name = organization_results['organization'].participant_name
                we_vote_hosted_profile_image_url_medium = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_medium
                we_vote_hosted_profile_image_url_tiny = \
                    organization_results['organization'].we_vote_hosted_profile_image_url_tiny
            else:
                participant_name = ''
                we_vote_hosted_profile_image_url_medium = ''
                we_vote_hosted_profile_image_url_tiny = ''
            try:
                # Create the ChallengeParticipant
                ChallengeParticipant.objects.create(
                    challenge_we_vote_id=challenge_we_vote_id,
                    participant_name=participant_name,
                    organization_we_vote_id=challenge_participant_organization_we_vote_id,
                    custom_message_for_friends=incoming_challenge_custom_message_for_friends,
                    voter_we_vote_id=challenge_participant_voter_we_vote_id,
                    we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                    visibility_blocked_by_we_vote=incoming_visibility_blocked_by_we_vote,
                    visible_to_public=incoming_challenge_participant_wants_visibility)

                messages.add_message(request, messages.INFO, 'New ChallengeParticipant created.')
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     'Could not create ChallengeParticipant.'
                                     ' {error} [type: {error_type}]'.format(error=e, error_type=type(e)))

    # ##################################
    # Deleting or editing a ChallengeParticipant
    update_challenge_participant_count = False
    results = deleting_or_editing_challenge_participant_list(
        request=request,
        participant_list=participant_list,
    )
    update_challenge_participant_count = update_challenge_participant_count or results['update_challenge_participant_count']
    update_message = results['update_message']
    if positive_value_exists(update_message):
        messages.add_message(request, messages.INFO, update_message)

    challenge_we_vote_id_list_to_refresh = [challenge_we_vote_id]
    error_message_to_print = ''
    info_message_to_print = ''

    # We update here only if we didn't save above
    if update_challenge_participant_count and positive_value_exists(challenge_we_vote_id):
        challenge_manager = ChallengeManager()
        participant_count = challenge_manager.fetch_challenge_participant_count(challenge_we_vote_id)
        results = challenge_manager.retrieve_challenge(
            challenge_we_vote_id=challenge_we_vote_id,
            read_only=False)
        if results['challenge_found']:
            challenge = results['challenge']
            challenge.participants_count = participant_count
            challenge.save()

    if positive_value_exists(error_message_to_print):
        messages.add_message(request, messages.ERROR, error_message_to_print)
    if positive_value_exists(info_message_to_print):
        messages.add_message(request, messages.INFO, info_message_to_print)

    return HttpResponseRedirect(reverse('challenge:participant_list', args=(challenge_we_vote_id,)) +
                                "?google_civic_election_id=" + str(google_civic_election_id) +
                                "&challenge_owner_organization_we_vote_id=" +
                                str(challenge_owner_organization_we_vote_id) +
                                "&challenge_search=" + str(challenge_search) +
                                "&state_code=" + str(state_code) +
                                "&only_show_participants_with_endorsements=" +
                                str(only_show_participants_with_endorsements) +
                                "&show_participants_not_visible_to_public=" + str(show_participants_not_visible_to_public)
                                )


@login_required
def compare_two_challenges_for_merge_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # challenge_year = request.GET.get('challenge_year', 0)
    challenge1_we_vote_id = request.GET.get('challenge1_we_vote_id', 0)
    challenge2_we_vote_id = request.GET.get('challenge2_we_vote_id', 0)
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    google_civic_election_id = convert_to_int(google_civic_election_id)
    status = ''

    if challenge1_we_vote_id == challenge2_we_vote_id:
        messages.add_message(request, messages.ERROR,
                             "Challenge1 and Challenge2 are the same -- can't compare.")
        return HttpResponseRedirect(reverse('challenge:challenge_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    challenge_manager = ChallengeManager()
    challenge_results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge1_we_vote_id, read_only=True)
    if not challenge_results['challenge_found']:
        messages.add_message(request, messages.ERROR, "Challenge1 not found.")
        return HttpResponseRedirect(reverse('challenge:challenge_list', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    challenge_option1_for_template = challenge_results['challenge']

    challenge_results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge2_we_vote_id, read_only=True)
    if not challenge_results['challenge_found']:
        messages.add_message(request, messages.ERROR, "Challenge2 not found.")
        return HttpResponseRedirect(reverse('challenge:challenge_summary',
                                            args=(challenge_option1_for_template.we_vote_id,)) +
                                    "?google_civic_election_id=" + str(google_civic_election_id))

    challenge_option2_for_template = challenge_results['challenge']

    conflict_results = figure_out_challenge_conflict_values(
        challenge_option1_for_template, challenge_option2_for_template)
    challenge_merge_conflict_values = conflict_results['conflict_values']
    if not conflict_results['success']:
        status += conflict_results['status']
        success = conflict_results['success']
    else:
        status += "COMPARE_TWO_CHALLENGES_DUPLICATE_FOUND "

    # This view function takes us to displaying a template
    remove_duplicate_process = False  # Do not try to find another office to merge after finishing
    return render_challenge_merge_form(
        request,
        challenge_option1_for_template,
        challenge_option2_for_template,
        challenge_merge_conflict_values,
        # challenge_year=challenge_year,
        remove_duplicate_process=remove_duplicate_process)


@login_required
def find_and_merge_duplicate_challenges_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    find_number_of_duplicates = request.GET.get('find_number_of_duplicates', 0)
    state_code = request.GET.get('state_code', "")
    status = ""
    challenge_manager = ChallengeManager()
    ignore_challenge_we_vote_id_list = []

    queryset = ChallengesAreNotDuplicates.objects.using('readonly').all()
    # if positive_value_exists(state_code):
    #     queryset = queryset.filter(state_code__iexact=state_code)
    queryset = queryset.exclude(challenge1_we_vote_id=None)
    queryset = queryset.exclude(challenge2_we_vote_id=None)
    queryset_challenge1 = queryset.values_list('challenge1_we_vote_id', flat=True).distinct()
    exclude_challenge1_we_vote_id_list = list(queryset_challenge1)
    # We also want to exclude the second challenges, so we aren't creating
    #   duplicate ChallengesArePossibleDuplicates entries
    queryset_challenge2 = queryset.values_list('challenge2_we_vote_id', flat=True).distinct()
    exclude_challenge2_we_vote_id_list = list(queryset_challenge2)
    exclude_challenge_we_vote_id_list = \
        list(set(exclude_challenge1_we_vote_id_list + exclude_challenge2_we_vote_id_list))

    queryset = ChallengesArePossibleDuplicates.objects.using('readonly').all()
    # if positive_value_exists(state_code):
    #     queryset = queryset.filter(state_code__iexact=state_code)
    queryset = queryset.exclude(challenge1_we_vote_id=None)
    queryset = queryset.exclude(challenge2_we_vote_id=None)
    queryset_challenge1 = queryset.values_list('challenge1_we_vote_id', flat=True).distinct()
    exclude_challenge1_we_vote_id_list = list(queryset_challenge1)
    # We also want to exclude the second challenges, so we aren't creating
    #   duplicate ChallengesArePossibleDuplicates entries
    queryset_challenge2 = queryset.values_list('challenge2_we_vote_id', flat=True).distinct()
    exclude_challenge2_we_vote_id_list = list(queryset_challenge2)
    exclude_challenge_we_vote_id_list2 = \
        list(set(exclude_challenge1_we_vote_id_list + exclude_challenge2_we_vote_id_list))

    # Now combine the ChallengesAreNotDuplicates and ChallengesArePossibleDuplicates lists
    exclude_challenge_we_vote_id_list = \
        list(set(exclude_challenge_we_vote_id_list + exclude_challenge_we_vote_id_list2))

    challenge_query = Challenge.objects.using('readonly').all()
    # We only want to check challenges hard linked to politicians for duplicates
    challenge_query = challenge_query.exclude(
        Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id=''))
    challenge_query = challenge_query.exclude(we_vote_id__in=exclude_challenge_we_vote_id_list)
    if positive_value_exists(state_code):
        challenge_query = challenge_query.filter(state_code__iexact=state_code)
    challenge_list = list(challenge_query[:1000])

    # Loop through all the challenges to see how many have possible duplicates
    if positive_value_exists(find_number_of_duplicates):
        duplicate_challenge_count = 0
        for one_challenge in challenge_list:
            # Note that we don't reset the ignore_challenge_list, so we don't search for a duplicate both directions
            ignore_challenge_we_vote_id_list.append(one_challenge.we_vote_id)
            duplicate_challenge_count_temp = fetch_duplicate_challenge_count(
                challenge=one_challenge,
                ignore_challenge_we_vote_id_list=ignore_challenge_we_vote_id_list)
            duplicate_challenge_count += duplicate_challenge_count_temp

        if positive_value_exists(duplicate_challenge_count):
            messages.add_message(request, messages.INFO,
                                 "There are approximately {duplicate_challenge_count} "
                                 "possible duplicates."
                                 "".format(duplicate_challenge_count=duplicate_challenge_count))
    try:
        # Give the volunteer who entered this credit
        volunteer_task_manager = VolunteerTaskManager()
        task_results = volunteer_task_manager.create_volunteer_task_completed(
            action_constant=VOLUNTEER_ACTION_DUPLICATE_POLITICIAN_ANALYSIS,
            request=request,
        )
    except Exception as e:
        status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
    # Loop through all the challenges to find politician_we_vote_id
    politician_we_vote_id_list = []
    for one_challenge in challenge_list:
        if one_challenge.we_vote_id in exclude_challenge_we_vote_id_list:
            continue
        if positive_value_exists(one_challenge.politician_we_vote_id):
            politician_we_vote_id_list.append(one_challenge.politician_we_vote_id)

    # Fill a dict with politician names, which we need so we can search for possible duplicates by name
    politician_name_dict_by_we_vote_id = {}
    if positive_value_exists(len(politician_we_vote_id_list)):
        queryset = Politician.objects.using('readonly').filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(queryset)
        for one_politician in politician_list:
            politician_name_dict_by_we_vote_id[one_politician.we_vote_id] = one_politician.politician_name

    # Loop through all the challenges
    for one_challenge in challenge_list:
        if one_challenge.we_vote_id in exclude_challenge_we_vote_id_list:
            continue
        # Add current challenge entry to ignore list
        ignore_challenge_we_vote_id_list.append(one_challenge.we_vote_id)
        # Now check to for other challenges we have labeled as "not a duplicate"
        not_a_duplicate_list = challenge_manager.fetch_challenges_are_not_duplicates_list_we_vote_ids(
            one_challenge.we_vote_id)

        ignore_challenge_we_vote_id_list += not_a_duplicate_list
        politician_name = None
        state_code = ''
        try:
            if one_challenge.politician_we_vote_id in politician_name_dict_by_we_vote_id:
                politician_name = politician_name_dict_by_we_vote_id[one_challenge.politician_we_vote_id]
            # We might also want to get state_code from politicians
        except Exception as e:
            pass
        results = find_duplicate_challenge(
            challenge=one_challenge,
            ignore_challenge_we_vote_id_list=ignore_challenge_we_vote_id_list,
            politician_name=politician_name,
            state_code=state_code,
        )

        # If we find challenges to merge, stop and ask for confirmation
        if results['challenge_merge_possibility_found']:
            challenge_option1_for_template = one_challenge
            challenge_option2_for_template = results['challenge_merge_possibility']

            # Can we automatically merge these challenges?
            merge_results = merge_if_duplicate_challenges(
                challenge_option1_for_template,
                challenge_option2_for_template,
                results['challenge_merge_conflict_values'])

            if merge_results['challenges_merged']:
                challenge = merge_results['challenge']
                if challenge.we_vote_id not in exclude_challenge_we_vote_id_list:
                    exclude_challenge_we_vote_id_list.append(challenge.we_vote_id)
                if one_challenge.we_vote_id not in exclude_challenge_we_vote_id_list:
                    exclude_challenge_we_vote_id_list.append(one_challenge.we_vote_id)
                ChallengesAreNotDuplicates.objects.create(
                    challenge1_we_vote_id=challenge.we_vote_id,
                    challenge2_we_vote_id=None,
                    # state_code=state_code,
                )
                ChallengesAreNotDuplicates.objects.create(
                    challenge1_we_vote_id=one_challenge.we_vote_id,
                    challenge2_we_vote_id=None,
                    # state_code=state_code,
                )
                messages.add_message(request, messages.INFO, "Challenge {challenge_title} automatically merged."
                                                             "".format(challenge_title=challenge.challenge_title))
                # No need to start over
                # return HttpResponseRedirect(reverse('challenge:find_and_merge_duplicate_challenges', args=()) +
                #                             "?state_code=" + str(state_code))
            else:
                # Add an entry showing that this is a possible match
                ChallengesArePossibleDuplicates.objects.create(
                    challenge1_we_vote_id=one_challenge.we_vote_id,
                    challenge2_we_vote_id=challenge_option2_for_template.we_vote_id,
                    state_code=state_code,
                )
                if challenge_option2_for_template.we_vote_id not in exclude_challenge_we_vote_id_list:
                    exclude_challenge_we_vote_id_list.append(challenge_option2_for_template.we_vote_id)
        else:
            # No matches found
            ChallengesAreNotDuplicates.objects.create(
                challenge1_we_vote_id=one_challenge.we_vote_id,
                challenge2_we_vote_id=None,
                # state_code=state_code,
            )

    return HttpResponseRedirect(reverse('challenge:duplicates_list', args=()) +
                                "?state_code={state_code}"
                                "".format(state_code=state_code))


def render_challenge_merge_form(
        request,
        challenge_option1_for_template,
        challenge_option2_for_template,
        challenge_merge_conflict_values,
        challenge_year=0,
        remove_duplicate_process=True):
    politician1_full_name = ''
    politician1_state_code = ''
    if challenge_option1_for_template and \
            positive_value_exists(challenge_option1_for_template.politician_we_vote_id):
        try:
            politician_queryset = Politician.objects.using('readonly').all()
            politician = politician_queryset.get(we_vote_id=challenge_option1_for_template.politician_we_vote_id)
            if politician and positive_value_exists(politician.first_name):
                politician1_full_name = politician.display_full_name()
            if politician and positive_value_exists(politician.state_code):
                politician1_state_code = politician.state_code
        except Exception as e:
            pass

    politician2_full_name = ''
    politician2_state_code = ''
    if challenge_option1_for_template and \
            positive_value_exists(challenge_option2_for_template.politician_we_vote_id):
        try:
            politician_queryset = Politician.objects.using('readonly').all()
            politician = politician_queryset.get(we_vote_id=challenge_option2_for_template.politician_we_vote_id)
            if politician and positive_value_exists(politician.first_name):
                politician2_full_name = politician.display_full_name()
            if politician and positive_value_exists(politician.state_code):
                politician2_state_code = politician.state_code
        except Exception as e:
            pass

    messages_on_stage = get_messages(request)
    template_values = {
        'challenge_option1':        challenge_option1_for_template,
        'challenge_option2':        challenge_option2_for_template,
        'challenge_year':           challenge_year,
        'conflict_values':          challenge_merge_conflict_values,
        'messages_on_stage':        messages_on_stage,
        'remove_duplicate_process': remove_duplicate_process,
        'politician1_full_name':    politician1_full_name,
        'politician1_state_code':   politician1_state_code,
        'politician2_full_name':    politician2_full_name,
        'politician2_state_code':   politician2_state_code,
    }
    return render(request, 'challenge/challenge_merge.html', template_values)


@login_required
def challenge_merge_process_view(request):
    """
    Process the merging of two challenge entries
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'political_data_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge_manager = ChallengeManager()

    is_post = True if request.method == 'POST' else False

    if is_post:
        merge = request.POST.get('merge', False)
        skip = request.POST.get('skip', False)

        # Challenge 1 is the one we keep, and Challenge 2 is the one we will merge into Challenge 1
        challenge_year = request.POST.get('challenge_year', 0)
        challenge1_we_vote_id = request.POST.get('challenge1_we_vote_id', 0)
        challenge2_we_vote_id = request.POST.get('challenge2_we_vote_id', 0)
        google_civic_election_id = request.POST.get('google_civic_election_id', 0)
        redirect_to_challenge_list = request.POST.get('redirect_to_challenge_list', False)
        regenerate_challenge_title = positive_value_exists(request.POST.get('regenerate_challenge_title', False))
        remove_duplicate_process = request.POST.get('remove_duplicate_process', False)
        state_code = request.POST.get('state_code', '')
    else:
        merge = request.GET.get('merge', False)
        skip = request.GET.get('skip', False)

        # Challenge 1 is the one we keep, and Challenge 2 is the one we will merge into Challenge 1
        challenge_year = request.GET.get('challenge_year', 0)
        challenge1_we_vote_id = request.GET.get('challenge1_we_vote_id', 0)
        challenge2_we_vote_id = request.GET.get('challenge2_we_vote_id', 0)
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
        redirect_to_challenge_list = request.GET.get('redirect_to_challenge_list', False)
        regenerate_challenge_title = positive_value_exists(request.GET.get('regenerate_challenge_title', False))
        remove_duplicate_process = request.GET.get('remove_duplicate_process', False)
        state_code = request.GET.get('state_code', '')

    if positive_value_exists(skip):
        results = challenge_manager.update_or_create_challenges_are_not_duplicates(
            challenge1_we_vote_id, challenge2_we_vote_id)
        if not results['new_challenges_are_not_duplicates_created']:
            messages.add_message(
                request, messages.ERROR, 'Merge: Could not save challenges_are_not_duplicates entry: '
                                         '' + results['status'])
        messages.add_message(request, messages.INFO, 'Prior challenge entries skipped, and not merged.')
        # When implemented, consider directing here: find_and_merge_duplicate_challenges
        return HttpResponseRedirect(reverse('challenge:challenge_list', args=()) +
                                    "?challenge_year=" + str(challenge_year) +
                                    "&google_civic_election_id=" + str(google_civic_election_id) +
                                    "&state_code=" + str(state_code))

    challenge1_results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge1_we_vote_id, read_only=True)
    if challenge1_results['challenge_found']:
        challenge1_on_stage = challenge1_results['challenge']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve challenge 1.')
        return HttpResponseRedirect(reverse('challenge:challenge_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_challenges=' + str(challenge_year) +
                                    '&state_code=' + str(state_code))

    challenge2_results = challenge_manager.retrieve_challenge(challenge_we_vote_id=challenge2_we_vote_id, read_only=True)
    if challenge2_results['challenge_found']:
        challenge2_on_stage = challenge2_results['challenge']
    else:
        messages.add_message(request, messages.ERROR, 'Could not retrieve challenge 2.')
        return HttpResponseRedirect(reverse('challenge:challenge_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_challenges=' + str(challenge_year) +
                                    '&state_code=' + str(state_code))

    # Gather choices made from merge form
    conflict_values = figure_out_challenge_conflict_values(challenge1_on_stage, challenge2_on_stage)
    admin_merge_choices = {}
    clear_these_attributes_from_challenge2 = []
    for attribute in CHALLENGE_UNIQUE_IDENTIFIERS:
        conflict_value = conflict_values.get(attribute, None)
        if conflict_value == "CONFLICT":
            if is_post:
                choice = request.POST.get(attribute + '_choice', '')
            else:
                choice = request.GET.get(attribute + '_choice', '')
            if challenge2_we_vote_id == choice:
                admin_merge_choices[attribute] = getattr(challenge2_on_stage, attribute)
                if attribute in CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                    clear_these_attributes_from_challenge2.append(attribute)
        elif conflict_value == "CHALLENGE2":
            admin_merge_choices[attribute] = getattr(challenge2_on_stage, attribute)
            if attribute in CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED:
                clear_these_attributes_from_challenge2.append(attribute)

    merge_results = merge_these_two_challenges(
        challenge1_we_vote_id,
        challenge2_we_vote_id,
        admin_merge_choices=admin_merge_choices,
        clear_these_attributes_from_challenge2=clear_these_attributes_from_challenge2,
        regenerate_challenge_title=regenerate_challenge_title)

    if positive_value_exists(merge_results['challenges_merged']):
        challenge = merge_results['challenge']
        messages.add_message(request, messages.INFO, "Challenge '{challenge_title}' merged."
                                                     "".format(challenge_title=challenge.challenge_title))
    else:
        # NOTE: We could also redirect to a page to look specifically at these two challenge entries, but this should
        # also get you back to looking at the two challenge entries
        messages.add_message(request, messages.ERROR, merge_results['status'])
        return HttpResponseRedirect(reverse('challenge:find_and_merge_duplicate_challenges', args=()) +
                                    "?google_civic_election_id=" + str(google_civic_election_id) +
                                    '&challenge_year=' + str(challenge_year) +
                                    "&auto_merge_off=1" +
                                    "&state_code=" + str(state_code))

    if redirect_to_challenge_list:
        return HttpResponseRedirect(reverse('challenge:challenge_list', args=()) +
                                    '?google_civic_election_id=' + str(google_civic_election_id) +
                                    '&show_this_year_of_challenges=' + str(challenge_year) +
                                    '&state_code=' + str(state_code))

    # To be implemented
    # if remove_duplicate_process:
    #     return HttpResponseRedirect(reverse('challenge:find_and_merge_duplicate_challenges', args=()) +
    #                                 "?google_civic_election_id=" + str(google_civic_election_id) +
    #                                 '&challenge_year=' + str(challenge_year) +
    #                                 "&state_code=" + str(state_code))

    return HttpResponseRedirect(reverse('challenge:challenge_edit', args=(challenge.we_vote_id,)))


@login_required
def challenge_not_duplicates_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    challenge1_we_vote_id = request.GET.get('challenge1_we_vote_id', '')
    challenge2_we_vote_id = request.GET.get('challenge2_we_vote_id', '')
    state_code = request.GET.get('state_code', '')
    status = ""
    volunteer_task_manager = VolunteerTaskManager()
    voter_id = 0
    voter_we_vote_id = ""
    voter_device_id = get_voter_api_device_id(request)
    if positive_value_exists(voter_device_id):
        voter = fetch_voter_from_voter_device_link(voter_device_id)
        if hasattr(voter, 'we_vote_id'):
            voter_id = voter.id
            voter_we_vote_id = voter.we_vote_id

    challenge_manager = ChallengeManager()
    results = challenge_manager.update_or_create_challenges_are_not_duplicates(
        challenge1_we_vote_id, challenge2_we_vote_id)
    if results['success']:
        queryset = ChallengesArePossibleDuplicates.objects.filter(
            challenge1_we_vote_id=challenge1_we_vote_id,
            challenge2_we_vote_id=challenge2_we_vote_id,
        )
        queryset.delete()
        if positive_value_exists(voter_we_vote_id):
            try:
                # Give the volunteer who entered this credit
                task_results = volunteer_task_manager.create_volunteer_task_completed(
                    action_constant=VOLUNTEER_ACTION_POLITICIAN_DEDUPLICATION,
                    voter_id=voter_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED-DEDUPLICATION: ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

    if not results['new_challenges_are_not_duplicates_created']:
        messages.add_message(request, messages.ERROR, 'Could not save challenges_are_not_duplicates entry: ' +
                             results['status'])
    messages.add_message(request, messages.INFO, 'Two challenges marked as not duplicates.')
    return HttpResponseRedirect(reverse('challenge:duplicates_list', args=()) +
                                "?state_code=" + str(state_code))


def deleting_or_editing_challenge_participant_list(
        request=None,
        participant_list=[]):
    organization_dict_by_we_vote_id = {}
    organization_manager = OrganizationManager()
    update_challenge_participant_count = False
    update_message = ''
    voter_manager = VoterManager()
    for challenge_participant in participant_list:
        if positive_value_exists(challenge_participant.challenge_we_vote_id):
            delete_variable_name = "delete_challenge_participant_" + str(challenge_participant.id)
            delete_challenge_participant = positive_value_exists(request.POST.get(delete_variable_name, False))
            if positive_value_exists(delete_challenge_participant):
                challenge_participant.delete()
                update_challenge_participant_count = True
                update_message += 'Deleted ChallengeParticipant. '
            else:
                participant_changed = False
                data_exists_variable_name = \
                    "challenge_participant_" + str(challenge_participant.id) + "_exists"
                challenge_participant_exists = request.POST.get(data_exists_variable_name, None)
                # Supporter Wants Visibility
                visible_to_public_variable_name = "challenge_participant_visible_to_public_" + str(challenge_participant.id)
                challenge_participant_visible_to_public = \
                    positive_value_exists(request.POST.get(visible_to_public_variable_name, False))
                # Visibility Blocked by We Vote
                blocked_by_we_vote_variable_name = \
                    "challenge_participant_visibility_blocked_by_we_vote_" + str(challenge_participant.id)
                challenge_participant_visibility_blocked_by_we_vote = \
                    positive_value_exists(request.POST.get(blocked_by_we_vote_variable_name, False))
                if challenge_participant_exists is not None:
                    challenge_participant.visibility_blocked_by_we_vote = \
                        challenge_participant_visibility_blocked_by_we_vote
                    challenge_participant.visible_to_public = challenge_participant_visible_to_public
                    participant_changed = True

                # Now refresh organization cached data
                organization = None
                organization_found = False
                if challenge_participant.organization_we_vote_id in organization_dict_by_we_vote_id:
                    organization = organization_dict_by_we_vote_id[challenge_participant.organization_we_vote_id]
                    if hasattr(organization, 'we_vote_hosted_profile_image_url_medium'):
                        organization_found = True
                else:
                    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                        challenge_participant.organization_we_vote_id,
                        read_only=True)
                    if organization_results['organization_found']:
                        organization = organization_results['organization']
                        organization_dict_by_we_vote_id[challenge_participant.organization_we_vote_id] = organization
                        organization_found = True
                if organization_found:
                    participant_name = organization.organization_name
                    if positive_value_exists(participant_name) and \
                            challenge_participant.participant_name != participant_name:
                        challenge_participant.participant_name = participant_name
                        participant_changed = True
                    we_vote_hosted_profile_image_url_medium = \
                        organization.we_vote_hosted_profile_image_url_medium
                    if positive_value_exists(we_vote_hosted_profile_image_url_medium) and \
                            challenge_participant.we_vote_hosted_profile_image_url_medium != \
                            we_vote_hosted_profile_image_url_medium:
                        challenge_participant.we_vote_hosted_profile_image_url_medium = \
                            we_vote_hosted_profile_image_url_medium
                        participant_changed = True
                    we_vote_hosted_profile_image_url_tiny = organization.we_vote_hosted_profile_image_url_tiny
                    if positive_value_exists(we_vote_hosted_profile_image_url_tiny) and \
                            challenge_participant.we_vote_hosted_profile_image_url_tiny != \
                            we_vote_hosted_profile_image_url_tiny:
                        challenge_participant.we_vote_hosted_profile_image_url_tiny = \
                            we_vote_hosted_profile_image_url_tiny
                        participant_changed = True
                if not positive_value_exists(challenge_participant.voter_we_vote_id):
                    voter_we_vote_id = voter_manager.fetch_voter_we_vote_id_by_linked_organization_we_vote_id(
                        challenge_participant.organization_we_vote_id)
                    if positive_value_exists(voter_we_vote_id):
                        challenge_participant.voter_we_vote_id = voter_we_vote_id
                        participant_changed = True
                if participant_changed:
                    challenge_participant.save()
                    update_message += 'Updated ChallengeParticipant. '
    results = {
        'update_challenge_participant_count': update_challenge_participant_count,
        'update_message': update_message,
    }
    return results
