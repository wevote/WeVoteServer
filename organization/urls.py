# organization/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin

urlpatterns = [
    # views_admin
    url(r'^(?P<organization_id>[0-9]+)/edit/$', views_admin.organization_edit_view, name='organization_edit'),
    url(r'^edit/(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)$',
        views_admin.organization_edit_view, name='organization_edit_we_vote_id'),
    url(r'^edit_process/$', views_admin.organization_edit_process_view, name='organization_edit_process'),
    url(r'^$', views_admin.organization_list_view, name='organization_list',),
    url(r'^import/$',
        views_admin.organizations_import_from_master_server_view, name='organizations_import_from_master_server'),
    url(r'^new/$', views_admin.organization_new_view, name='organization_new'),
    url(r'^(?P<organization_id>[0-9]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_position_list',),
    url(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_we_vote_id_position_list',),
    url(r'^(?P<organization_id>[0-9]+)/pos/new/$',
        views_admin.organization_position_new_view, name='organization_position_new',),
    url(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/delete/$',
        views_admin.organization_delete_existing_position_process_form_view, name='organization_position_delete',),
    url(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/$',
        views_admin.organization_position_edit_view, name='organization_position_edit', ),
    url(r'^pos/edit_process/$',
        views_admin.organization_position_edit_process_view, name='organization_position_edit_process'),

    # views
    # This is used for a voter to follow an organization
    url(r'^(?P<organization_id>[0-9]+)/follow/$',
        views.organization_follow_view, name='organization_follow_view',),
    # This is used for a voter to unfollow an organization
    url(r'^(?P<organization_id>[0-9]+)/stop_following/$',
        views.organization_stop_following_view, name='organization_stop_following_view',),
    # # This is used for a voter to ignore an organization
    # url(r'^(?P<organization_id>[0-9]+)/follow_ignore/$',
    #   views.organization_follow_ignore_view, name='organization_follow_ignore_view',),
]
