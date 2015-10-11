# election/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.election_list_view, name='election_list',),
    url(r'^(?P<election_id>[0-9]+)/edit/$', views_admin.election_edit_view, name='election_edit'),
    url(r'^(?P<election_id>[0-9]+)/summary/$', views_admin.election_summary_view, name='election_summary'),
    url(r'^edit_process/$', views_admin.election_edit_process_view, name='election_edit_process'),
    url(r'^(?P<election_id>[0-9]+)/election_all_ballots_retrieve/$', views_admin.election_all_ballots_retrieve_view,
        name='election_all_ballots_retrieve'),
    url(r'^election_remote_retrieve/$', views_admin.election_remote_retrieve_view, name='election_remote_retrieve'),
]
