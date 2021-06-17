# import_export_vote_smart/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views, views_admin


urlpatterns = [
    re_path(r'^candidate_list/$', views_admin.vote_smart_candidate_list_view, name='vote_smart_candidate_list'),
    re_path(r'^$', views_admin.vote_smart_index_view, name='vote_smart_index',),
    re_path(r'^(?P<vote_smart_candidate_id>[0-9]+)/import_one_candidate_ratings/$',
        views_admin.import_one_candidate_ratings_view, name='import_one_candidate_ratings',),
    re_path(r'^(?P<vote_smart_candidate_id>[0-9]+)/import_one_politician_ratings/$',
        views_admin.import_one_politician_ratings_view, name='import_one_politician_ratings',),
    re_path(r'^(?P<candidate_id>[0-9]+)/transfer_vote_smart_ratings_to_positions_for_candidate/$',
        views_admin.transfer_vote_smart_ratings_to_positions_for_candidate_view,
        name='transfer_vote_smart_ratings_to_positions_for_candidate',),
    re_path(r'^(?P<politician_id>[0-9]+)/transfer_vote_smart_ratings_to_positions_for_politician/$',
        views_admin.transfer_vote_smart_ratings_to_positions_for_politician_view,
        name='transfer_vote_smart_ratings_to_positions_for_politician',),
    re_path(r'^import_group_ratings/$', views_admin.import_group_ratings_view, name='import_group_ratings'),
    re_path(r'^(?P<special_interest_group_id>[0-9]+)/import_one_group_ratings/$', views_admin.import_one_group_ratings_view,
        name='import_one_group_ratings',),
    re_path(r'^import_photo/$', views_admin.import_photo_view, name='import_photo'),
    re_path(r'^import_vote_smart_position_categories/$',
        views_admin.import_vote_smart_position_categories_view, name='import_vote_smart_position_categories'),
    re_path(r'^import_special_interest_groups/$',
        views_admin.import_special_interest_groups_view, name='import_special_interest_groups'),
    re_path(r'^import_states/$', views_admin.import_states_view, name='import_states'),
    re_path(r'^retrieve_positions_from_vote_smart_for_election/$',
        views_admin.retrieve_positions_from_vote_smart_for_election_view,
        name='retrieve_positions_from_vote_smart_for_election'),
    re_path(r'^states/(?P<pk>[A-Z]+)/$', views_admin.state_detail_view, name='state_detail'),
    re_path(r'^position_category_list/$',
        views_admin.vote_smart_position_category_list_view, name='vote_smart_position_category_list'),
    re_path(r'^rating_list/$', views_admin.vote_smart_rating_list_view, name='vote_smart_rating_list'),
    re_path(r'^special_interest_group_list/$',
        views_admin.vote_smart_special_interest_group_list_view, name='vote_smart_special_interest_group_list'),
    re_path(r'^(?P<special_interest_group_id>[0-9]+)/ratings/$', views_admin.special_interest_group_rating_list_view,
        name='special_interest_group_rating_list',),
    re_path(r'^transfer_vote_smart_sigs_to_we_vote_orgs/$',
        views_admin.transfer_vote_smart_sigs_to_we_vote_orgs_view, name='transfer_vote_smart_sigs_to_we_vote_orgs'),
]
