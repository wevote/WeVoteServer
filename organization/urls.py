# organization/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views, views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.organization_list_view, name='organization_list',),
    re_path(r'^compare_two_organizations/$',
        views_admin.compare_two_organizations_for_merge_view, name='compare_two_organizations_for_merge'),
    re_path(r'^delete_process/$', views_admin.organization_delete_process_view, name='organization_delete_process'),
    re_path(r'^edit/(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)$',
        views_admin.organization_edit_view, name='organization_edit_we_vote_id'),
    re_path(r'^(?P<organization_id>[0-9]+)/edit/$', views_admin.organization_edit_view, name='organization_edit'),
    re_path(r'^(?P<organization_id>[0-9]+)/edit_account/$',
        views_admin.organization_edit_account_view, name='organization_edit_account'),
    re_path(r'^edit_account_process/$',
        views_admin.organization_edit_account_process_view, name='organization_edit_account_process'),
    re_path(r'^edit_process/$', views_admin.organization_edit_process_view, name='organization_edit_process'),
    re_path(r'^(?P<organization_id>[0-9]+)/edit_listed_campaigns/$',
        views_admin.organization_edit_listed_campaigns_view, name='organization_edit_listed_campaigns'),
    re_path(r'^edit_listed_campaigns_process/$',
        views_admin.organization_edit_listed_campaigns_process_view, name='organization_edit_listed_campaigns_process'),
    re_path(r'^import/$',
        views_admin.organizations_import_from_master_server_view, name='organizations_import_from_master_server'),
    re_path(r'^merge/$', views_admin.organization_merge_process_view, name='organization_merge_process'),
    re_path(r'^new/$', views_admin.organization_new_view, name='organization_new'),
    re_path(r'^(?P<organization_id>[0-9]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_position_list',),
    re_path(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/retrieve_tweets/$',
        views_admin.organization_retrieve_tweets_view, name='organization_retrieve_tweets',),
    re_path(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/organization_analyze_tweets/$',
        views_admin.organization_analyze_tweets_view, name='organization_analyze_tweets',),
    re_path(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_we_vote_id_position_list',),
    re_path(r'^(?P<incorrect_integer>[0-9]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_we_vote_id_position_list',),
    re_path(r'^(?P<organization_id>[0-9]+)/pos/new/$',
        views_admin.organization_position_new_view, name='organization_position_new',),
    re_path(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/delete/$',
        views_admin.organization_delete_existing_position_process_form_view, name='organization_position_delete',),
    re_path(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/$',
        views_admin.organization_position_edit_view, name='organization_position_edit', ),
    re_path(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/$',
        views_admin.organization_position_edit_view, name='organization_we_vote_id_position_edit', ),
    re_path(r'^pos/edit_process/$',
        views_admin.organization_position_edit_process_view, name='organization_position_edit_process'),
    re_path(r'^reserved_domain_list/$',
        views_admin.reserved_domain_list_view, name='reserved_domain_list'),
    re_path(r'^reserved_domain_edit/$',
        views_admin.reserved_domain_edit_view, name='reserved_domain_edit'),
    re_path(r'^reserved_domain_edit_process/$',
        views_admin.reserved_domain_edit_process_view, name='reserved_domain_edit_process'),

    # views
    # This is used for a voter to follow an organization
    re_path(r'^(?P<organization_id>[0-9]+)/follow/$',
        views.organization_follow_view, name='organization_follow_view',),
    # This is used for a voter to unfollow an organization
    re_path(r'^(?P<organization_id>[0-9]+)/stop_following/$',
        views.organization_stop_following_view, name='organization_stop_following_view',),
    # # This is used for a voter to ignore an organization
    # re_path(r'^(?P<organization_id>[0-9]+)/follow_ignore/$',
    #   views.organization_follow_ignore_view, name='organization_follow_ignore_view',),
]
