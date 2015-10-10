# tag/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render

from .models import Tag


def tag_list_view(request):  # , politician_id
    # politician_on_stage = get_object_or_404(Politician, id=politician_id)
    # TODO Find the tags attached to this politician
    tag_list = Tag.objects.order_by('twitter_handle')
    # post_list = Post.objects.filter
    template_values = {
        # 'politician_on_stage': politician_on_stage,
        # 'post_list': tag_list,  # This is for prototyping only -- we want to move very quickly to posts being pulled onto the page via javascript
        'tag_list': tag_list,
    }
    return render(request, 'tag/tag_list.html', template_values)


def tag_new_view(request):
    template_values = {

    }
    return render(request, 'tag/tag_new.html', template_values)


def tag_new_process_view(request):
    new_tag = request.POST['new_tag']

    # Check to see if this tag is already being used anywhere

    new_tag_temp, created = Tag.objects.get_or_create(hashtag_text=new_tag)

    return HttpResponseRedirect(reverse('tag:tag_list', args=()))
