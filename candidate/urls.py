# candidate/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import url


urlpatterns = [
    # views_admin
    url(r'^$', views_admin.candidate_list_view, name='candidate_list',),
    url(r'^politician_match_this_election/', views_admin.candidate_politician_match_for_this_election_view,
        name='candidate_politician_match_for_this_election'),
    url(r'^edit_process/$', views_admin.candidate_edit_process_view, name='candidate_edit_process'),
    url(r'^merge/$', views_admin.candidate_merge_process_view, name='candidate_merge_process'),
    # url(r'^export/', views_admin.CandidatesSyncOutView.as_view(), name='candidates_export'),
    url(r'^delete/', views_admin.candidate_delete_process_view, name='candidate_delete_process'),
    url(r'^politician_match/', views_admin.candidate_politician_match_view, name='candidate_politician_match'),
    url(r'^import/$',
        views_admin.candidates_import_from_master_server_view, name='candidates_import_from_master_server'),
    url(r'^new/$', views_admin.candidate_new_view, name='candidate_new'),
    url(r'^(?P<candidate_id>[0-9]+)/edit/$', views_admin.candidate_edit_view, name='candidate_edit'),
    url(r'^(?P<candidate_campaign_we_vote_id>wv[\w]{2}cand[\w]+)/edit/$',
        views_admin.candidate_edit_view, name='candidate_edit_we_vote_id'),
    url(r'^(?P<candidate_id>[0-9]+)/find_duplicate_candidate/$',
        views_admin.find_duplicate_candidate_view, name='find_duplicate_candidate'),
    url(r'^(?P<candidate_id>[0-9]+)/retrieve_photos/$',
        views_admin.candidate_retrieve_photos_view, name='candidate_retrieve_photos'),
    url(r'^duplicate_candidates/$',
        views_admin.find_and_remove_duplicate_candidates_view, name='find_and_remove_duplicate_candidates'),
    url(r'^remove_duplicate_candidate/$',
        views_admin.remove_duplicate_candidate_view, name='remove_duplicate_candidate'),
    url(r'^(?P<election_id>[0-9]+)/photos_for_election/$',
        views_admin.retrieve_candidate_photos_for_election_view, name='photos_for_election'),
    url(r'^(?P<candidate_id>[0-9]+)/summary/$', views_admin.candidate_summary_view,
        name='candidate_summary'),
]
