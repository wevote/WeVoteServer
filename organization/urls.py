# organization/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.organization_list_view, name='organization_list',),
    url(r'^compare_two_organizations/$',
        views_admin.compare_two_organizations_for_merge_view, name='compare_two_organizations_for_merge'),
    url(r'^delete_process/$', views_admin.organization_delete_process_view, name='organization_delete_process'),
    url(r'^edit/(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)$',
        views_admin.organization_edit_view, name='organization_edit_we_vote_id'),
    url(r'^(?P<organization_id>[0-9]+)/edit/$', views_admin.organization_edit_view, name='organization_edit'),
    url(r'^(?P<organization_id>[0-9]+)/edit_account/$',
        views_admin.organization_edit_account_view, name='organization_edit_account'),
    url(r'^edit_account_process/$',
        views_admin.organization_edit_account_process_view, name='organization_edit_account_process'),
    url(r'^edit_process/$', views_admin.organization_edit_process_view, name='organization_edit_process'),
    url(r'^(?P<organization_id>[0-9]+)/edit_listed_campaigns/$',
        views_admin.organization_edit_listed_campaigns_view, name='organization_edit_listed_campaigns'),
    url(r'^edit_listed_campaigns_process/$',
        views_admin.organization_edit_listed_campaigns_process_view, name='organization_edit_listed_campaigns_process'),
    url(r'^import/$',
        views_admin.organizations_import_from_master_server_view, name='organizations_import_from_master_server'),
    url(r'^merge/$', views_admin.organization_merge_process_view, name='organization_merge_process'),
    url(r'^new/$', views_admin.organization_new_view, name='organization_new'),
    url(r'^(?P<organization_id>[0-9]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_position_list',),
    url(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/retrieve_tweets/$',
        views_admin.organization_retrieve_tweets_view, name='organization_retrieve_tweets',),
    url(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/organization_analyze_tweets/$',
        views_admin.organization_analyze_tweets_view, name='organization_analyze_tweets',),
    url(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_we_vote_id_position_list',),
    url(r'^(?P<incorrect_integer>[0-9]+)/pos/$',
        views_admin.organization_position_list_view, name='organization_we_vote_id_position_list',),
    url(r'^(?P<organization_id>[0-9]+)/pos/new/$',
        views_admin.organization_position_new_view, name='organization_position_new',),
    url(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/delete/$',
        views_admin.organization_delete_existing_position_process_form_view, name='organization_position_delete',),
    url(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/$',
        views_admin.organization_position_edit_view, name='organization_position_edit', ),
    url(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/pos/(?P<position_we_vote_id>wv[\w]{2}pos[\w]+)/$',
        views_admin.organization_position_edit_view, name='organization_we_vote_id_position_edit', ),
    url(r'^pos/edit_process/$',
        views_admin.organization_position_edit_process_view, name='organization_position_edit_process'),
    url(r'^reserved_domain_list/$',
        views_admin.reserved_domain_list_view, name='reserved_domain_list'),
    url(r'^reserved_domain_edit/$',
        views_admin.reserved_domain_edit_view, name='reserved_domain_edit'),
    url(r'^reserved_domain_edit_process/$',
        views_admin.reserved_domain_edit_process_view, name='reserved_domain_edit_process'),

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
