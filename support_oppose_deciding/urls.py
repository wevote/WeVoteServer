# support_oppose_deciding/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url
from support_oppose_deciding import views

urlpatterns = [

    # What is the signed in voter's position on this candidate_campaign?
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/voterstance/$',
        views.voter_stance_for_candidate_campaign_view,
        name='voter_stance_for_candidate_campaign_view'),

    # Toggle ON the voter's support of this candidate
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/support/$',
        views.voter_supporting_candidate_campaign_view,
        name='voter_supporting_candidate_campaign_view'),
    # Toggle OFF the voter's support of this candidate
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/stopsupport/$',
        views.voter_stop_supporting_candidate_campaign_view,
        name='voter_stop_supporting_candidate_campaign_view'),

    # Toggle ON the voter's opposition of this candidate
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/oppose/$',
        views.voter_opposing_candidate_campaign_view,
        name='voter_opposing_candidate_campaign_view'),
    # Toggle OFF the voter's opposition of this candidate
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/stopoppose/$',
        views.voter_stop_opposing_candidate_campaign_view,
        name='voter_stop_opposing_candidate_campaign_view'),

    # Toggle ON the voter's asking friends about this candidate
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/ask/$',
        views.voter_asking_candidate_campaign_view,
        name='voter_asking_candidate_campaign_view'),
    # Toggle OFF the voter's asking friends about this candidate
    url(r'^cand/(?P<candidate_campaign_id>[0-9]+)/stopasking/$',
        views.voter_stop_asking_candidate_campaign_view,
        name='voter_stop_asking_candidate_campaign_view'),
]
