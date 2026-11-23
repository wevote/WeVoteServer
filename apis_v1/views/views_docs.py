# apis_v1/views/views_docs.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import importlib

from django.contrib.messages import get_messages
from django.http import Http404
from django.shortcuts import render

from config.environment_variable_functions import get_environment_variable
from voter.models import voter_setup
from wevote_functions.functions import get_voter_api_device_id, set_voter_api_device_id, positive_value_exists
from wevote_functions.utils import get_git_params

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def get_api_doc_template_values(request, api_name='', template_values_function_name=None):
    """
    api_name='representatives_query' loads apis_v1/documentation_source/representatives_query_doc.py and calls
    representatives_query_doc_template_values(url_root), falling back to doc_template_values(url_root).
    Pass template_values_function_name for doc files that use a non-standard function name.
    """
    if not api_name or not api_name.replace('_', '').isalnum():
        raise Http404("Unknown API documentation")
    try:
        doc_module = importlib.import_module(
            'apis_v1.documentation_source.{api_name}_doc'.format(api_name=api_name))
    except ModuleNotFoundError:
        raise Http404("Unknown API documentation")
    if template_values_function_name:
        function_names = [template_values_function_name]
    else:
        function_names = ['{api_name}_doc_template_values'.format(api_name=api_name), 'doc_template_values']
    template_values_function = None
    for function_name in function_names:
        template_values_function = getattr(doc_module, function_name, None)
        if callable(template_values_function):
            break
    if not callable(template_values_function):
        raise Http404("Unknown API documentation")
    template_values = template_values_function(WE_VOTE_SERVER_ROOT_URL)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return template_values


def api_doc_view(request, api_name='', template_values_function_name=None):
    """
    Generic doc view, so we don't need custom code for every API. See get_api_doc_template_values.
    """
    template_values = get_api_doc_template_values(request, api_name, template_values_function_name)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def apis_index_doc_view(request):
    """
    Show a list of available APIs
    """
    # Create a voter_device_id and voter in the database if one doesn't exist yet
    results = voter_setup(request)
    voter_api_device_id = results['voter_api_device_id']
    store_new_voter_api_device_id_in_cookie = results['store_new_voter_api_device_id_in_cookie']

    messages_on_stage = get_messages(request)
    git_params = get_git_params()
    date = git_params['date']
    template_values = {
        'next': next,
        'messages_on_stage': messages_on_stage,
        'git_commit_date':  date,
    }
    response = render(request, 'apis_v1/apis_index.html', template_values)

    # We want to store the voter_device_id cookie if it is new
    if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


def voter_guide_possibility_highlights_retrieve_doc_view(request):
    """
    Show documentation about voterGuidePossibilityHighlightsRetrieve
    """
    template_values = get_api_doc_template_values(request, 'voter_guide_possibility_highlights_retrieve')
    is_post = True if request.method == 'POST' else False
    if is_post:
        get_or_post_selected = request.POST.get('get_or_post_selected', '')
    else:
        get_or_post_selected = request.GET.get('get_or_post_selected', '')
    if 'get_or_post' in template_values and template_values['get_or_post'] == 'GET or POST':
        if positive_value_exists(get_or_post_selected):
            template_values['get_or_post'] = get_or_post_selected
            template_values['get_or_post_selected'] = get_or_post_selected
    return render(request, 'apis_v1/api_doc_page.html', template_values)
