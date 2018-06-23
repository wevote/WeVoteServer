# voter_guide/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.voter_guide_list_view, name='voter_guide_list',),
    url(r'^create/', views_admin.voter_guide_create_view, name='voter_guide_create'),
    url(r'^create_process/', views_admin.voter_guide_create_process_view, name='voter_guide_create_process'),
    url(r'^(?P<voter_guide_we_vote_id>wv[\w]{2}vg[\w]+)/edit/$',
        views_admin.voter_guide_edit_view, name='voter_guide_edit'),
    url(r'^edit_process/$', views_admin.voter_guide_edit_process_view, name='voter_guide_edit_process'),
    url(r'^generate/', views_admin.generate_voter_guides_view, name='generate_voter_guides'),
    url(r'^generate_one_election/',
        views_admin.generate_voter_guides_for_one_election_view, name='generate_voter_guides_one_election'),
    url(r'^generate_voter_guide_possibility_batch/',
        views_admin.generate_voter_guide_possibility_batch_view,
        name='generate_voter_guide_possibility_batch',),
    url(r'^import/$',
        views_admin.voter_guides_import_from_master_server_view,
        name='voter_guides_import_from_master_server'),
    url(r'^possibility_list/', views_admin.voter_guide_possibility_list_view, name='voter_guide_possibility_list', ),
    url(r'^refresh/', views_admin.refresh_existing_voter_guides_view, name='refresh_existing_voter_guides'),
    url(r'^search/', views_admin.voter_guide_search_view, name='voter_guide_search'),
    url(r'^search_process/', views_admin.voter_guide_search_process_view, name='voter_guide_search_process'),

    # views
]
