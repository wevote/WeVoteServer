# election/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import re_path


urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.election_list_view, name='election_list',),
    re_path(r'^(?P<election_local_id>[0-9]+)/edit/$', views_admin.election_edit_view, name='election_edit'),
    re_path(r'^(?P<election_local_id>[0-9]+)/summary/$', views_admin.election_summary_view, name='election_summary'),
    re_path(r'^(?P<google_civic_election_id>[0-9]+)/summary_by_google_id/$',
        views_admin.election_summary_view, name='election_summary_by_google_id'),
    re_path(r'^ballotpedia_election_delete_process/$',
        views_admin.ballotpedia_election_delete_process_view, name='ballotpedia_election_delete_process'),
    re_path(r'^election_ballot_location_visualize/$', views_admin.election_ballot_location_visualize_view,
            name='election_ballot_location_visualize'),
    re_path(r'^election_delete_process/$', views_admin.election_delete_process_view, name='election_delete_process'),
    re_path(r'^edit_process/$', views_admin.election_edit_process_view, name='election_edit_process'),
    re_path(r'^(?P<election_local_id>[0-9]+)/election_all_ballots_retrieve/$',
        views_admin.election_all_ballots_retrieve_view, name='election_all_ballots_retrieve'),
    re_path(r'^(?P<election_local_id>[0-9]+)/election_one_ballot_retrieve/$',
        views_admin.election_one_ballot_retrieve_view, name='election_one_ballot_retrieve'),
    re_path(r'^election_migration/$', views_admin.election_migration_view, name='election_migration'),
    re_path(r'^election_remote_retrieve/$', views_admin.election_remote_retrieve_view, name='election_remote_retrieve'),
    re_path(r'^import/$',
        views_admin.elections_import_from_master_server_view, name='elections_import_from_master_server'),
    re_path(r'^nationwide_election_list/$', views_admin.nationwide_election_list_view, name='nationwide_election_list'),
    re_path(r'^test/$',
        views_admin.test_view, name='test'),
]
