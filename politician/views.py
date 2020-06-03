# politician/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from admin_tools.views import redirect_to_sign_in_page
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.urls import reverse
from django.views import generic
from .models import Politician, PoliticianTagLink
from tag.models import Tag
from voter.models import voter_has_authority


@login_required
def politician_tag_new_view(request, politician_id):
    """
    Form to add a new link tying a politician to twitter tags
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    # for message in messages_on_stage:
    #     if message.level is ERROR:

    politician_on_stage = get_object_or_404(Politician, id=politician_id)

    try:
        tag_link_list = politician_on_stage.tag_link.all()
    except PoliticianTagLink.DoesNotExist:
        tag_link_list = None
    template_values = {
        'politician_on_stage': politician_on_stage,
        'tag_link_list': tag_link_list,
        'messages_on_stage': messages_on_stage,
    }
    return render(request, 'politician/politician_tag_new.html', template_values)


@login_required
def politician_tag_new_process_view(request, politician_id):
    """
    Process the form to add a new link tying a politician to twitter tags
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    politician_on_stage = get_object_or_404(Politician, id=politician_id)
    new_tag = request.POST['new_tag']

    # If an invalid tag didn't come in, redirect back to tag_new
    if not is_tag_valid(new_tag):
        messages.add_message(request, messages.INFO, 'That is not a valid tag. Please enter a different tag.')
        return HttpResponseRedirect(reverse('politician:politician_tag_new', args=(politician_id,)))

    new_tag_temp, created = Tag.objects.get_or_create(hashtag_text=new_tag)
    new_tag_link = PoliticianTagLink(tag=new_tag_temp, politician=politician_on_stage)
    new_tag_link.save()

    return HttpResponseRedirect(reverse('politician:politician_detail', args=(politician_id,)))


def is_tag_valid(new_tag):
    if not bool(new_tag.strip()):  # If this doesn't evaluate true here, then it is empty and isn't valid
        return False
    return True
