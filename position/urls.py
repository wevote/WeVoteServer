# position/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url
from position import views, views_admin

urlpatterns = [
    # admin_views.py
    url(r'^$', views_admin.position_list_view, name='position_list',),
    url(r'^edit_process/$', views_admin.position_edit_process_view, name='position_edit_process'),
    url(r'^export/', views_admin.ExportPositionDataView.as_view(), name='positions_export'),
    url(r'^new/$', views_admin.position_new_view, name='position_new',),
    url(r'^relink_candidates_measures/$', views_admin.relink_candidates_measures_view,
        name='relink_candidates_measures'),
    url(r'^(?P<position_id>[0-9]+)/edit/$', views_admin.position_edit_view, name='position_edit'),
    url(r'^(?P<position_id>[0-9]+)/summary/$', views_admin.position_summary_view, name='position_summary'),

    # views.py
    # These pages are called by the ballot HTML page, and they return a JSON with all of the orgs that oppose a
    # particular candidate or measure (Ex/ "Common Cause, Berkeley Democratic Club and 3 others oppose")
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/oppose/$',
        views.positions_related_to_candidate_campaign_oppose_view,
        name='positions_related_to_candidate_campaign_oppose_view'),
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/opposecount/$',
        views.positions_count_for_candidate_campaign_oppose_view,
        name='positions_count_for_candidate_campaign_oppose_view'),
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/support/$',
        views.positions_related_to_candidate_campaign_support_view,
        name='positions_related_to_candidate_campaign_support_view'),
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/supportcount/$',
        views.positions_count_for_candidate_campaign_support_view,
        name='positions_count_for_candidate_campaign_support_view'),
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/infoonly/$',
        views.positions_related_to_candidate_campaign_information_only_view,
        name='positions_related_to_candidate_campaign_information_only_view'),
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/deciding/$',
        views.positions_related_to_candidate_campaign_still_deciding_view,
        name='positions_related_to_candidate_campaign_still_deciding_view'),

    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/anypositionnfcount/$',
        views.positions_count_for_candidate_campaign_any_not_followed_view,
        name='positions_count_for_candidate_campaign_any_not_followed_view'),

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
    # url(r'^ms/(?P<measure_campaign_id>[0-9]+)/oppose/$',
    #     views.positions_related_to_measure_campaign_oppose_view,
    #     name='positions_related_to_measure_campaign_oppose_view'),
    # url(r'^ms/(?P<measure_campaign_id>[0-9]+)/support/$',
    #     views.positions_related_to_measure_campaign_support_view,
    #     name='positions_related_to_measure_campaign_support_view'),
]
