# position/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url
from . import views, views_admin

urlpatterns = [
    # views_admin.py
    url(r'^$', views_admin.position_list_view, name='position_list',),
    url(r'^delete/$', views_admin.position_delete_process_view, name='position_delete_process',),
    url(r'^edit_process/$', views_admin.position_edit_process_view, name='position_edit_process'),
    # url(r'^export/', views_admin.PositionsSyncOutView.as_view(), name='positions_export'),
    url(r'^import/$',
        views_admin.positions_import_from_master_server_view, name='positions_import_from_master_server'),
    url(r'^new/$', views_admin.position_new_view, name='position_new',),
    url(r'^relink_candidates_measures/$', views_admin.relink_candidates_measures_view,
        name='relink_candidates_measures'),
    url(r'^(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/edit/$', views_admin.position_edit_view, name='position_edit'),
    url(r'^(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/summary/$',
        views_admin.position_summary_view, name='position_summary'),
    url(r'^refresh_positions_with_candidate_details/',
        views_admin.refresh_positions_with_candidate_details_for_election_view,
        name='refresh_positions_with_candidate_details_for_election'),
    url(r'^refresh_positions_with_office_details/',
        views_admin.refresh_positions_with_contest_office_details_for_election_view,
        name='refresh_positions_with_contest_office_details_for_election'),
    url(r'^refresh_positions_with_measure_details/',
        views_admin.refresh_positions_with_contest_measure_details_for_election_view,
        name='refresh_positions_with_contest_measure_details_for_election')
    # # These pages are used to return the div popup page with details about all supporters, opposers, etc.
    # # Any position that this voter isn't already following
    # url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/anyposition/$',
    #     views_admin.positions_display_list_related_to_candidate_campaign_any_position_view,
    #     name='positions_display_list_related_to_candidate_campaign_any_position_view'),
    # # Candidate Supporters
    # url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/supporters/$',
    #     views_admin.positions_display_list_related_to_candidate_campaign_supporters_view,
    #     name='positions_display_list_related_to_candidate_campaign_supporters_view'),
    # # Candidate Opposers
    # url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/opposers/$',
    #     views_admin.positions_display_list_related_to_candidate_campaign_opposers_view,
    #     name='positions_display_list_related_to_candidate_campaign_opposers_view'),
    # # Candidate No Stance, Comments, Information only
    # url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/infoonlylist/$',
    #     views_admin.positions_display_list_related_to_candidate_campaign_information_only_view,
    #     name='positions_display_list_related_to_candidate_campaign_information_only_view'),
    # # Candidate - Still Deciding
    # url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/deciders/$',
    #     views_admin.positions_display_list_related_to_candidate_campaign_deciders_view,
    #     name='positions_display_list_related_to_candidate_campaign_deciders_view'),
    #
    # # Measures
    # url(r'^ms/(?P<contest_measure_id>[0-9]+)/oppose/$',
    #     views.positions_related_to_contest_measure_oppose_view,
    #     name='positions_related_to_contest_measure_oppose_view'),
    # url(r'^ms/(?P<contest_measure_id>[0-9]+)/support/$',
    #     views.positions_related_to_contest_measure_support_view,
    #     name='positions_related_to_contest_measure_support_view'),
]
