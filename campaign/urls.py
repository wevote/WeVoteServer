# campaign/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.campaign_list_view, name='campaignx_list',),
    re_path(r'^compare_two_campaigns/$',
            views_admin.compare_two_campaigns_for_merge_view, name='compare_two_campaigns_for_merge'),
    re_path(r'^delete_process/$', views_admin.campaign_delete_process_view, name='campaignx_delete_process'),
    re_path(r'^(?P<campaignx_we_vote_id>wv[\w]{2}camp[\w]+)/edit$', views_admin.campaign_edit_view,
            name='campaignx_edit'),
    re_path(r'^edit_process/$', views_admin.campaign_edit_process_view, name='campaignx_edit_process'),
    re_path(r'^edit_owners_process/$', views_admin.campaign_edit_owners_process_view,
            name='campaignx_edit_owners_process'),
    re_path(r'^edit_politicians_process/$',
        views_admin.campaign_edit_politicians_process_view, name='campaignx_edit_politicians_process'),
    re_path(r'^(?P<campaignx_we_vote_id>wv[\w]{2}camp[\w]+)/edit_owners$',
        views_admin.campaign_edit_owners_view, name='campaignx_edit_owners'),
    re_path(r'^(?P<campaignx_we_vote_id>wv[\w]{2}camp[\w]+)/edit_politicians$',
        views_admin.campaign_edit_politicians_view, name='campaignx_edit_politicians'),
    re_path(r'^merge/$', views_admin.campaignx_merge_process_view, name='campaignx_merge_process'),
    re_path(r'^(?P<campaignx_we_vote_id>wv[\w]{2}camp[\w]+)/summary$',
        views_admin.campaign_summary_view, name='campaignx_summary'),
    re_path(r'^repair_ocd_id_mismatch/$',
            views_admin.repair_ocd_id_mismatch_damage_view, name='repair_ocd_id_mismatch'),
    re_path(r'^(?P<campaignx_we_vote_id>wv[\w]{2}camp[\w]+)/supporters$',
        views_admin.campaign_supporters_list_view, name='supporters_list'),
    re_path(r'^supporters_list_process/$', views_admin.campaign_supporters_list_process_view,
            name='supporters_list_process'),
]
