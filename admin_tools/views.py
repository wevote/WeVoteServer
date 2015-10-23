# admin_tools/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.controllers import candidates_import_from_sample_file
# from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.shortcuts import render
from election.controllers import elections_import_from_sample_file
from office.controllers import offices_import_from_sample_file
from organization.controllers import organizations_import_from_sample_file
from polling_location.controllers import import_and_save_all_polling_locations_data
from position.controllers import positions_import_from_sample_file


def admin_home_view(request):

    template_values = {
    }
    return render(request, 'admin_home/index.html', template_values)


# @login_required()  # Commented out while we are developing login process
def import_test_data_view(request):
    # This routine works without requiring a Google Civic API key

    polling_locations_results = import_and_save_all_polling_locations_data()

    # NOTE: The approach of having each developer pull directly from Google Civic won't work because if we are going
    # to import positions, we need to have stable we_vote_ids for all ballot items
    # =========================
    # # We redirect to the view that calls out to Google Civic and brings in ballot data
    # # This isn't ideal (I'd rather call a controller instead of redirecting to a view), but this is a unique case
    # # and we have a lot of error-display-to-screen code
    # election_local_id = 0
    # google_civic_election_id = 4162  # Virginia
    # return HttpResponseRedirect(reverse('election:election_all_ballots_retrieve',
    #                                     args=(election_local_id,)) +
    #                             "?google_civic_election_id=" + str(google_civic_election_id))

    # Import election data from We Vote export file
    elections_results = elections_import_from_sample_file()

    # Import ContestOffices
    load_from_uri = False
    offices_results = offices_import_from_sample_file(request, load_from_uri)

    # Import candidate data from We Vote export file
    load_from_uri = False
    candidates_results = candidates_import_from_sample_file(request, load_from_uri)

    # Import ContestMeasures

    # Import organization data from We Vote export file
    load_from_uri = False
    organizations_results = organizations_import_from_sample_file(request, load_from_uri)

    # Import positions data from We Vote export file
    load_from_uri = False
    positions_results = positions_import_from_sample_file(request, load_from_uri)

    messages.add_message(request, messages.INFO,
                         'The following data has been imported: <br />'
                         'Polling locations saved: {polling_locations_saved}, updated: {polling_locations_updated},'
                         ' not_processed: {polling_locations_not_processed} <br />'
                         'Elections saved: {elections_saved}, updated: {elections_updated},'
                         ' not_processed: {elections_not_processed} <br />'
                         'Offices saved: {offices_saved}, updated: {offices_updated},'
                         ' not_processed: {offices_not_processed} <br />'
                         'Candidates saved: {candidates_saved}, updated: {candidates_updated},'
                         ' not_processed: {candidates_not_processed} <br />'
                         'Organizations saved: {organizations_saved}, updated: {organizations_updated},'
                         ' not_processed: {organizations_not_processed} <br />'
                         'Positions saved: {positions_saved}, updated: {positions_updated},'
                         ' not_processed: {positions_not_processed} <br />'
                         ''.format(
                             polling_locations_saved=polling_locations_results['saved'],
                             polling_locations_updated=polling_locations_results['updated'],
                             polling_locations_not_processed=polling_locations_results['not_processed'],
                             elections_saved=elections_results['saved'],
                             elections_updated=elections_results['updated'],
                             elections_not_processed=elections_results['not_processed'],
                             offices_saved=offices_results['saved'],
                             offices_updated=offices_results['updated'],
                             offices_not_processed=offices_results['not_processed'],
                             candidates_saved=candidates_results['saved'],
                             candidates_updated=candidates_results['updated'],
                             candidates_not_processed=candidates_results['not_processed'],
                             organizations_saved=organizations_results['saved'],
                             organizations_updated=organizations_results['updated'],
                             organizations_not_processed=organizations_results['not_processed'],
                             positions_saved=positions_results['saved'],
                             positions_updated=positions_results['updated'],
                             positions_not_processed=positions_results['not_processed'],
                         ))
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))


# @login_required()  # Commented out while we are developing login process
def delete_test_data_view(request):
    # We leave in place the polling locations data and the election data from Google civic

    # Delete candidate data from exported file

    # Delete organization data from exported file

    # Delete positions data from exported file
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))
