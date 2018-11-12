# voter/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    url(r'^$', views_admin.voter_list_view, name='voter_list',),
    url(r'^authenticate_manually/$', views_admin.voter_authenticate_manually_view, name='authenticate_manually'),
    url(r'^authenticate_manually_process/$',
        views_admin.voter_authenticate_manually_process_view, name='authenticate_manually_process'),
    url(r'^voter_change_authority/$',
        views_admin.voter_change_authority_process_view, name='voter_change_authority_process'),
    url(r'^voter_remove_facebook_auth_process/$',
        views_admin.voter_remove_facebook_auth_process_view, name='voter_remove_facebook_auth_process'),
    url(r'^edit_process/$', views_admin.voter_edit_process_view, name='voter_edit_process'),
    url(r'^login_complete/$', views_admin.login_complete_view, name='login_complete_view'),
    url(r'^(?P<voter_id>[0-9]+)/edit/$', views_admin.voter_edit_view, name='voter_edit'),
    url(r'^edit/(?P<voter_we_vote_id>wv[\w]{2}voter[\w]+)$', views_admin.voter_edit_view, name='voter_edit_we_vote_id'),
    url(r'^(?P<voter_id>[0-9]+)/summary/$', views_admin.voter_summary_view, name='voter_summary'),
]
