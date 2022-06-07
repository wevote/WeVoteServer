# friend/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^current_friends_data_healing/$',
        views_admin.current_friends_data_healing_view, name='current_friends_data_healing'),
    url(r'^refresh_voter_friend_count/$',
        views_admin.refresh_voter_friend_count_view, name='refresh_voter_friend_count'),
]
