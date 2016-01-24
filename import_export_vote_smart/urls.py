# import_export_vote_smart/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin


urlpatterns = [
    url(r'^$', views_admin.vote_smart_index_view, name='vote_smart_index',),
    url(r'^(?P<vote_smart_candidate_id>[0-9]+)/import_one_candidate_ratings/$',
        views_admin.import_one_candidate_ratings_view, name='import_one_candidate_ratings',),
    url(r'^(?P<candidate_campaign_id>[0-9]+)/transfer_vote_smart_ratings_to_positions_for_candidate/$',
        views_admin.transfer_vote_smart_ratings_to_positions_for_candidate_view,
        name='transfer_vote_smart_ratings_to_positions_for_candidate',),
    url(r'^import_group_ratings/$', views_admin.import_group_ratings_view, name='import_group_ratings'),
    url(r'^(?P<special_interest_group_id>[0-9]+)/import_one_group_ratings/$', views_admin.import_one_group_ratings_view,
        name='import_one_group_ratings',),
    url(r'^import_photo/$', views_admin.import_photo_view, name='import_photo'),
    url(r'^import_vote_smart_position_categories/$',
        views_admin.import_vote_smart_position_categories_view, name='import_vote_smart_position_categories'),
    url(r'^import_special_interest_groups/$',
        views_admin.import_special_interest_groups_view, name='import_special_interest_groups'),
    url(r'^import_states/$', views_admin.import_states_view, name='import_states'),
    url(r'^states/(?P<pk>[A-Z]+)/$', views_admin.state_detail_view, name='state_detail'),
    url(r'^position_category_list/$',
        views_admin.vote_smart_position_category_list_view, name='vote_smart_position_category_list'),
    url(r'^rating_list/$', views_admin.vote_smart_rating_list_view, name='vote_smart_rating_list'),
    url(r'^special_interest_group_list/$',
        views_admin.vote_smart_special_interest_group_list_view, name='vote_smart_special_interest_group_list'),
    url(r'^(?P<special_interest_group_id>[0-9]+)/ratings/$', views_admin.special_interest_group_rating_list_view,
        name='special_interest_group_rating_list',),
    url(r'^transfer_vote_smart_sigs_to_we_vote_orgs/$',
        views_admin.transfer_vote_smart_sigs_to_we_vote_orgs_view, name='transfer_vote_smart_sigs_to_we_vote_orgs'),
]
