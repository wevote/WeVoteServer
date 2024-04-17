# friend/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import path

from . import views_admin


urlpatterns = [
    path('current_friends_data_healing/',
        views_admin.current_friends_data_healing_view, name='current_friends_data_healing'),
    path('generate_mutual_friends_for_all_voters/',
        views_admin.generate_mutual_friends_for_all_voters_view, name='generate_mutual_friends_for_all_voters'),
    path('generate_mutual_friends_for_one_voter/',
        views_admin.generate_mutual_friends_for_one_voter_view, name='generate_mutual_friends_for_one_voter'),
    path('refresh_voter_friend_count/',
        views_admin.refresh_voter_friend_count_view, name='refresh_voter_friend_count'),
]
