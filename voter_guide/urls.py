# voter_guide/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.voter_guide_list_view, name='voter_guide_list',),
    re_path(r'^create/', views_admin.voter_guide_create_view, name='voter_guide_create'),
    re_path(r'^create_from_prior/',
        views_admin.create_possible_voter_guides_from_prior_elections_view,
        name='create_possible_voter_guides_from_prior_elections'),
    re_path(r'^create_process/', views_admin.voter_guide_create_process_view, name='voter_guide_create_process'),
    re_path(r'^(?P<voter_guide_we_vote_id>wv[\w]{2}vg[\w]+)/edit/$',
        views_admin.voter_guide_edit_view, name='voter_guide_edit'),
    re_path(r'^edit_process/$', views_admin.voter_guide_edit_process_view, name='voter_guide_edit_process'),
    re_path(r'^generate/', views_admin.generate_voter_guides_view, name='generate_voter_guides'),
    re_path(r'^generate_one_election/',
        views_admin.generate_voter_guides_for_one_election_view, name='generate_voter_guides_one_election'),
    re_path(r'^generate_voter_guide_possibility_batch/',
        views_admin.generate_voter_guide_possibility_batch_view,
        name='generate_voter_guide_possibility_batch',),
    re_path(r'^import/$',
        views_admin.voter_guides_import_from_master_server_view,
        name='voter_guides_import_from_master_server'),
    re_path(r'^label/', views_admin.label_vote_smart_voter_guides_view, name='label_vote_smart_voter_guides'),
    re_path(r'^possibility_list/', views_admin.voter_guide_possibility_list_view, name='voter_guide_possibility_list', ),
    re_path(r'^possibility_list_process/', views_admin.voter_guide_possibility_list_process_view, name='voter_guide_possibility_list_process', ),
    re_path(r'^possibility_list_migration/',
        views_admin.voter_guide_possibility_list_migration_view, name='voter_guide_possibility_list_migration', ),
    re_path(r'^refresh/', views_admin.refresh_existing_voter_guides_view, name='refresh_existing_voter_guides'),
    re_path(r'^search/', views_admin.voter_guide_search_view, name='voter_guide_search'),
    re_path(r'^search_process/', views_admin.voter_guide_search_process_view, name='voter_guide_search_process'),

    # views
]
