# import_export_google_civic/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from import_export_google_civic.controllers import import_voterinfo_from_json


# We retrieve from Google Civic, electionQuery using election_remote_retrieve_view in
# election/views_admin.py


@login_required()
def import_voterinfo_from_json_view(request):
    """
    Take data from google civic information URL (JSON format) and store in the local database (???)
    Then display the data retrieved again from the local database
    """
    save_to_db = True
    json_from_google = import_voterinfo_from_json(save_to_db)

    template_values = {
        'json_from_google': json_from_google,
    }
    return render(request, 'import_export_google_civic/import_election_query.html', template_values)
