# import_export_vote_smart/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import retrieve_and_save_vote_smart_states
from .models import State
from django.shortcuts import redirect, render
from django.views import generic


def import_states_view(request):
    """
    """
    # # If person isn't signed in, we don't want to let them visit this page yet
    # if not request.user.is_authenticated():
    #     return redirect('/admin')

    retrieve_and_save_vote_smart_states()

    template_values = {
        'state_list': State.objects.order_by('name'),
    }
    return render(request, 'import_export_vote_smart/vote_smart_import.html', template_values)


def state_detail_view(request, pk):
    """
    """
    # # If person isn't signed in, we don't want to let them visit this page yet
    # if not request.user.is_authenticated():
    #     return redirect('/admin')
    state_id = pk

    template_values = {
        'state': State.objects.get(stateId=state_id),
    }
    return render(request, 'import_export_vote_smart/state_detail.html', template_values)
