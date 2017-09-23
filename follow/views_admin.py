# follow/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import FollowOrganization
from admin_tools.views import redirect_to_sign_in_page
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from voter.models import retrieve_voter_authority, voter_has_authority, VoterManager
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, positive_value_exists, \
    STATE_CODE_MAP
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def repair_follow_organization_view(request):
    """
    Process the new or edit organization forms
    :param request:
    :return:
    """
    authority_required = {'verified_volunteer'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    follow_organization_entries_updated = 0
    follow_organization_entries_not_updated = 0

    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")

    # find entries without a voter_linked_organization_we_vote_id
    follow_organization_list = []
    try:
        organization_query = FollowOrganization.objects.all()
        organization_query = organization_query.filter(
            (Q(voter_linked_organization_we_vote_id__isnull=True) | Q(voter_linked_organization_we_vote_id=''))
        )
        follow_organization_list = list(organization_query)
    except Exception as e:
        pass

    voter_manager = VoterManager()
    for follow_organization in follow_organization_list:
        voter_linked_organization_we_vote_id = \
            voter_manager.fetch_linked_organization_we_vote_id_from_local_id(follow_organization.voter_id)
        if positive_value_exists(voter_linked_organization_we_vote_id):
            try:
                follow_organization.voter_linked_organization_we_vote_id = voter_linked_organization_we_vote_id
                follow_organization.save()
                follow_organization_entries_updated += 1
            except Exception as e:
                follow_organization_entries_not_updated += 1

    return HttpResponseRedirect(reverse('organization:organization_list', args=()))
