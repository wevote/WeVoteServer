# politician/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.politician_list_view, name='politician_list',),
    re_path(r'^compare_two_politicians/$',
            views_admin.compare_two_politicians_for_merge_view, name='compare_two_politicians_for_merge'),
    re_path(r'^find_duplicate_politicians/$',
            views_admin.find_and_merge_duplicate_politicians_view, name='find_and_merge_duplicate_politicians'),
    re_path(r'^edit_process/$', views_admin.politician_edit_process_view, name='politician_edit_process'),
    re_path(r'^delete/', views_admin.politician_delete_process_view, name='politician_delete_process'),
    re_path(r'^delete_all_duplicates/$',
            views_admin.politician_delete_all_duplicates_view, name='delete_all_duplicates'),
    re_path(r'^duplicates_list/$', views_admin.politician_duplicates_list_view, name='duplicates_list'),
    re_path(r'^not_duplicates/$', views_admin.politician_not_duplicates_view, name='not_duplicates'),
    re_path(r'^import/$',
            views_admin.politicians_import_from_master_server_view, name='politicians_import_from_master_server'),
    re_path(r'^merge/$', views_admin.politician_merge_process_view, name='politician_merge_process'),
    re_path(r'^new/$', views_admin.politician_new_view, name='politician_new'),
    re_path(r'^(?P<politician_id>[0-9]+)/edit/$', views_admin.politician_edit_view, name='politician_edit'),
    re_path(r'^(?P<politician_we_vote_id>wv[\w]{2}pol[\w]+)/edit$',
            views_admin.politician_edit_view, name='politician_we_vote_id_edit'),
    re_path(r'^(?P<politician_id>[0-9]+)/retrieve_photos/$',
            views_admin.politician_retrieve_photos_view, name='politician_retrieve_photos'),
    re_path(r'^repair_ocd_id_mismatch/$',
            views_admin.repair_ocd_id_mismatch_damage_view, name='repair_ocd_id_mismatch'),
    re_path(r'^set_missing_gender_ids/$', views_admin.set_missing_gender_ids_view, name='set_missing_gender_ids'),
    re_path(r'^update_politician_from_candidate/', views_admin.update_politician_from_candidate_view,
            name='update_politician_from_candidate'),
    re_path(r'^update_from_candidates/', views_admin.update_politicians_from_candidates_view,
            name='update_politicians_from_candidates'),
    re_path(r'^update_profile_image_background_color/',
            views_admin.update_profile_image_background_color_view_for_politicians,
            name='update_profile_image_background_color'),
    # 2024-05-15: Causing problems on live servers
    # re_path(r'^update_recommended_politicians/', views_admin.update_recommended_politicians_view,
    #         name='update_recommended_politicians')
]