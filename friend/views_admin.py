# friend/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

from .controllers import generate_mutual_friends_for_all_voters, generate_mutual_friends_for_one_voter
from .models import CurrentFriend, FriendManager
import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from wevote_functions.functions import convert_to_int, positive_value_exists
from voter.models import Voter, voter_has_authority, VoterManager, voter_setup

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def current_friends_data_healing_view(request):
    status = ""
    number_of_linked_org_updates = 0
    number_of_voters_missing_linked_org = 0
    voter_we_vote_id_list = []

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}  # We may want to add a "voter_admin"
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    try:
        query = Voter.objects.all()
        query = query.filter(friend_count__gt=0)
        query = query.values_list('we_vote_id', flat=True).distinct()
        voter_we_vote_id_list = list(query)
    except Exception as e:
        messages.add_message(request, messages.ERROR,
                             'Could not retrieve any voters with current_friend > 0: ' + str(e))

    if len(voter_we_vote_id_list):
        voter_manager = VoterManager()
        for voter_we_vote_id in voter_we_vote_id_list:
            linked_organization_we_vote_id = voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(
                voter_we_vote_id=voter_we_vote_id)
            if positive_value_exists(linked_organization_we_vote_id):
                viewer_updated = CurrentFriend.objects \
                    .filter(viewer_voter_we_vote_id__iexact=voter_we_vote_id) \
                    .exclude(viewer_organization_we_vote_id__iexact=linked_organization_we_vote_id) \
                    .update(viewer_organization_we_vote_id=linked_organization_we_vote_id)
                if positive_value_exists(viewer_updated):
                    number_of_linked_org_updates += viewer_updated

                viewee_updated = CurrentFriend.objects \
                    .filter(viewee_voter_we_vote_id__iexact=voter_we_vote_id) \
                    .exclude(viewee_organization_we_vote_id__iexact=linked_organization_we_vote_id) \
                    .update(viewee_organization_we_vote_id=linked_organization_we_vote_id)
                if positive_value_exists(viewee_updated):
                    number_of_linked_org_updates += viewee_updated
            else:
                number_of_voters_missing_linked_org += 1

    if number_of_linked_org_updates:
        messages.add_message(request, messages.INFO,
                             'linked_organization_we_vote_id updates: ' + str(number_of_linked_org_updates))
    else:
        messages.add_message(request, messages.INFO,
                             'No linked_organization_we_vote_id updates. ')

    if number_of_voters_missing_linked_org:
        messages.add_message(request, messages.ERROR,
                             'number_of_voters_missing_linked_org: ' + str(number_of_voters_missing_linked_org))

    return HttpResponseRedirect(reverse('voter:voter_list', args=()))


@login_required
def generate_mutual_friends_for_all_voters_view(request):
    status = ""

    results = generate_mutual_friends_for_all_voters()
    status += results['status']
    messages.add_message(request, messages.INFO, 'status: ' + str(status))

    return HttpResponseRedirect(reverse('voter:voter_list', args=()))


@login_required
def generate_mutual_friends_for_one_voter_view(request):
    status = ""
    voter_id = request.GET.get('voter_id', 0)
    voter_id = convert_to_int(voter_id)
    voter_we_vote_id = request.GET.get('voter_we_vote_id', '')

    results = generate_mutual_friends_for_one_voter(voter_we_vote_id=voter_we_vote_id)
    status += results['status']
    messages.add_message(request, messages.INFO, 'status: ' + str(status))

    return HttpResponseRedirect(reverse('voter:voter_edit', args=(voter_id,)))


@login_required
def refresh_voter_friend_count_view(request):
    """

    :param request:
    :return:
    """
    status = ""

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}  # We may want to add a "voter_admin"
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    query = CurrentFriend.objects.using('readonly').all()
    query = query.values_list('viewer_voter_we_vote_id', flat=True).distinct()
    viewer_voter_we_vote_id_list = list(query)

    query = CurrentFriend.objects.using('readonly').all()
    query = query.values_list('viewee_voter_we_vote_id', flat=True).distinct()
    viewee_voter_we_vote_id_list = list(query)

    voter_we_vote_id_list = list(set(viewer_voter_we_vote_id_list + viewee_voter_we_vote_id_list))

    friend_manager = FriendManager()
    voter_manager = VoterManager()
    voters_with_friends = 0
    for one_voter_we_vote_id in voter_we_vote_id_list:
        friends_count = friend_manager.fetch_current_friends_count(voter_we_vote_id=one_voter_we_vote_id)
        if positive_value_exists(friends_count):
            voters_with_friends += 1
            results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id=one_voter_we_vote_id)
            if results['voter_found']:
                results['voter'].friend_count = friends_count
                results['voter'].save()

    if voters_with_friends:
        messages.add_message(request, messages.INFO, 'voters_with_friends: ' + str(voters_with_friends))

    return HttpResponseRedirect(reverse('voter:voter_list', args=()))
