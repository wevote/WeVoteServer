# google_custom_search/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^delete_possible_twitter_handles/(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.delete_possible_google_search_users_view, name='delete_possible_google_search_users',),
    url(r'^retrieve_possible_google_search_data/(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.retrieve_possible_google_search_users_view, name='retrieve_possible_google_search_users',),
    url (r'^possible_google_search_user_do_not_match/$',
         views_admin.possible_google_search_user_do_not_match_view, name='possible_google_search_user_do_not_match',),
    url (r'^bulk_retrieve_possible_google_search_users/$',
         views_admin.bulk_retrieve_possible_google_search_users_view,
         name='bulk_retrieve_possible_google_search_users',),
    url (r'^bulk_possible_google_search_users_do_not_match/(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/$',
         views_admin.bulk_possible_google_search_users_do_not_match_view,
         name='bulk_possible_google_search_users_do_not_match',),
]
