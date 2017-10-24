# google_custom_search/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^delete_possible_twitter_handles/(?P<candidate_campaign_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.delete_possible_google_search_users_view, name='delete_possible_google_search_users',),
    url(r'^retrieve_possible_google_search_data/(?P<candidate_campaign_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.retrieve_possible_google_search_users_view, name='retrieve_possible_google_search_users',),
]
