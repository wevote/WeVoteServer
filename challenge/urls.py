# challenge/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.challenge_list_view, name='challenge_list',),
    re_path(r'^compare_two_challenges/$',
            views_admin.compare_two_challenges_for_merge_view, name='compare_two_challenges_for_merge'),
    re_path(r'^find_duplicate_challenges/$',
            views_admin.find_and_merge_duplicate_challenges_view,
            name='find_and_merge_duplicate_challenges'),
    re_path(r'^(?P<challenge_we_vote_id>wv[\w]{2}chal[\w]+)/edit$', views_admin.challenge_edit_view,
            name='challenge_edit'),
    re_path(r'^new/$', views_admin.challenge_edit_view, name='challenge_new'),
    re_path(r'^delete_process/$', views_admin.challenge_delete_process_view, name='challenge_delete_process'),
    re_path(r'^duplicates_list/$', views_admin.challenge_duplicates_list_view, name='duplicates_list'),
    re_path(r'^not_duplicates/$', views_admin.challenge_not_duplicates_view, name='not_duplicates'),
    re_path(r'^edit_process/$', views_admin.challenge_edit_process_view, name='challenge_edit_process'),
    re_path(r'^edit_owners_process/$', views_admin.challenge_edit_owners_process_view,
            name='challenge_edit_owners_process'),
    re_path(r'^edit_politicians_process/$',
        views_admin.challenge_edit_politicians_process_view, name='challenge_edit_politicians_process'),
    re_path(r'^(?P<challenge_we_vote_id>wv[\w]{2}chal[\w]+)/edit_owners$',
        views_admin.challenge_edit_owners_view, name='challenge_edit_owners'),
    re_path(r'^(?P<challenge_we_vote_id>wv[\w]{2}chal[\w]+)/edit_politicians$',
        views_admin.challenge_edit_politicians_view, name='challenge_edit_politicians'),
    re_path(r'^merge/$', views_admin.challenge_merge_process_view, name='challenge_merge_process'),
    re_path(r'^(?P<challenge_we_vote_id>wv[\w]{2}chal[\w]+)/summary$',
        views_admin.challenge_summary_view, name='challenge_summary'),
    re_path(r'^(?P<challenge_we_vote_id>wv[\w]{2}chal[\w]+)/participants$',
        views_admin.challenge_participant_list_view, name='participant_list'),
    re_path(r'^participant_list_process/$', views_admin.challenge_participant_list_process_view,
            name='participant_list_process'),
    re_path(r'^refresh_participant_info/$', views_admin.refresh_participant_info_view,
            name='refresh_participant_info'),
]
