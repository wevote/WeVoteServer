# voter_guide/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoterGuideList
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from election.models import Election


# @login_required()  # Commented out while we are developing login process()
def generate_voter_guides_view(request):

    messages.add_message(request, messages.INFO, 'Voter guides generated.')
    return HttpResponseRedirect(reverse('voter_guide:voter_guide_list', args=()))


# @login_required()  # Commented out while we are developing login process()
def voter_guide_list_view(request):
    try:
        google_civic_election_id = request.GET['google_civic_election_id']
    except KeyError:
        google_civic_election_id = 0

    voter_guide_list = []
    voter_guide_list_object = VoterGuideList()
    results = voter_guide_list_object.retrieve_voter_guides_for_election(
        google_civic_election_id=google_civic_election_id)

    if results['success']:
        voter_guide_list = results['voter_guide_list']
    # else:
    #     messages.add_message(request, messages.INFO, 'No voter guides found.')

    election_list = Election.objects.order_by('election_name')

    messages_on_stage = get_messages(request)
    template_values = {
        'election_list': election_list,
        'google_civic_election_id': google_civic_election_id,
        'messages_on_stage': messages_on_stage,
        'voter_guide_list': voter_guide_list,
    }
    return render(request, 'voter_guide/voter_guide_list.html', template_values)
