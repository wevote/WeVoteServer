# candidate/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.urls import re_path


urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.candidate_list_view, name='candidate_list',),
    re_path(r'^create/$', views_admin.candidate_create_process_view, name='candidate_create_process'),
    re_path(r'^create_us_house_candidates/$',
            views_admin.create_us_house_candidates_view, name='create_us_house_candidates'),
    re_path(r'^politician_match_this_election/', views_admin.candidate_politician_match_this_election_view,
            name='candidate_politician_match_for_this_election'),
    re_path(r'^politician_match_this_year/', views_admin.candidate_politician_match_this_year_view,
            name='candidate_politician_match_this_year'),
    re_path(r'^edit_process/$', views_admin.candidate_edit_process_view, name='candidate_edit_process'),
    re_path(r'^merge/$', views_admin.candidate_merge_process_view, name='candidate_merge_process'),
    re_path(r'^delete/', views_admin.candidate_delete_process_view, name='candidate_delete_process'),
    re_path(r'^delete_all_duplicates/$',
            views_admin.candidate_delete_all_duplicates_view, name='delete_all_duplicates'),
    re_path(r'^politician_match/', views_admin.candidate_politician_match_view, name='candidate_politician_match'),
    re_path(r'^import/$',
            views_admin.candidates_import_from_master_server_view, name='candidates_import_from_master_server'),
    re_path(r'^new/$', views_admin.candidate_new_view, name='candidate_new'),
    re_path(r'^new_search/$', views_admin.candidate_new_search_view, name='candidate_new_search'),
    re_path(r'^new_search_process/$',
            views_admin.candidate_new_search_process_view, name='candidate_new_search_process'),
    re_path(r'^(?P<candidate_id>[0-9]+)/edit/$', views_admin.candidate_edit_view, name='candidate_edit'),
    re_path(r'^(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/edit/$',
            views_admin.candidate_edit_view, name='candidate_edit_we_vote_id'),
    re_path(r'^(?P<candidate_id>[0-9]+)/find_duplicate_candidate/$',
            views_admin.find_duplicate_candidate_view, name='find_duplicate_candidate'),
    re_path(r'^(?P<candidate_id>[0-9]+)/retrieve_photos/$',
            views_admin.candidate_retrieve_photos_view, name='candidate_retrieve_photos'),
    re_path(r'^compare_two_candidates/$',
            views_admin.compare_two_candidates_for_merge_view, name='compare_two_candidates_for_merge'),
    re_path(r'^find_duplicate_candidates/$',
            views_admin.find_and_merge_duplicate_candidates_view, name='find_and_merge_duplicate_candidates'),
    re_path(r'^duplicates_list/$', views_admin.candidate_duplicates_list_view, name='duplicates_list'),
    re_path(r'^not_duplicates/$', views_admin.candidates_not_duplicates_view, name='not_duplicates'),
    re_path(r'^remove_duplicate_candidates/$',
            views_admin.remove_duplicate_candidates_view, name='remove_duplicate_candidates'),
    re_path(r'^(?P<election_id>[0-9]+)/photos_for_election/$',
            views_admin.retrieve_candidate_photos_for_election_view, name='photos_for_election'),
    re_path(r'^repair_imported_names/$', views_admin.repair_imported_names_view, name='repair_imported_names'),
    re_path(r'^(?P<candidate_id>[0-9]+)/summary/$', views_admin.candidate_summary_view,
            name='candidate_summary'),
    re_path(r'^update_ocd_id_state_mismatch/', views_admin.update_ocd_id_state_mismatch_view,
            name='update_ocd_id_state_mismatch'),
    re_path(r'^update_candidate_from_politician/', views_admin.update_candidate_from_politician_view,
            name='update_candidate_from_politician'),
    re_path(r'^update_candidates_from_politicians/', views_admin.update_candidates_from_politicians_view,
            name='update_candidates_from_politicians'),
    re_path(r'^update_profile_image_background_color/',
            views_admin.update_profile_image_background_color_view_for_candidates,
            name='update_profile_image_background_color')
]
