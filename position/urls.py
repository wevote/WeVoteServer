# position/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url
from position import views

urlpatterns = [
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

    # These pages are used to return the div popup page with details about all supporters, opposers, etc.
    # Any position that this voter isn't already following
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/anyposition/$',
        views.positions_display_list_related_to_candidate_campaign_any_position_view,
        name='positions_display_list_related_to_candidate_campaign_any_position_view'),
    # Candidate Supporters
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/supporters/$',
        views.positions_display_list_related_to_candidate_campaign_supporters_view,
        name='positions_display_list_related_to_candidate_campaign_supporters_view'),
    # Candidate Opposers
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/opposers/$',
        views.positions_display_list_related_to_candidate_campaign_opposers_view,
        name='positions_display_list_related_to_candidate_campaign_opposers_view'),
    # Candidate No Stance, Comments, Information only
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/infoonlylist/$',
        views.positions_display_list_related_to_candidate_campaign_information_only_view,
        name='positions_display_list_related_to_candidate_campaign_information_only_view'),
    # Candidate - Still Deciding
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/deciders/$',
        views.positions_display_list_related_to_candidate_campaign_deciders_view,
        name='positions_display_list_related_to_candidate_campaign_deciders_view'),

    # Measures
    url(r'^ms/(?P<measure_campaign_id>[0-9]+)/oppose/$',
        views.positions_related_to_measure_campaign_oppose_view,
        name='positions_related_to_measure_campaign_oppose_view'),
    url(r'^ms/(?P<measure_campaign_id>[0-9]+)/support/$',
        views.positions_related_to_measure_campaign_support_view,
        name='positions_related_to_measure_campaign_support_view'),
]
