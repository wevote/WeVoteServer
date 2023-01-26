# representative/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^$', views_admin.representative_list_view, name='representative_list',),
    re_path(r'^compare_two_representatives/$',
            views_admin.compare_two_representatives_for_merge_view, name='compare_two_representatives_for_merge'),
    re_path(r'^edit_process/$', views_admin.representative_edit_process_view, name='representative_edit_process'),
    re_path(r'^delete/', views_admin.representative_delete_process_view, name='representative_delete_process'),
    re_path(r'^duplicate_representatives/$',
            views_admin.find_and_merge_duplicate_representatives_view, name='find_and_merge_duplicate_representatives'),
    re_path(r'^(?P<representative_id>[0-9]+)/find_duplicate_representative/$',
            views_admin.find_duplicate_representative_view, name='find_duplicate_representative'),
    re_path(r'^politician_match/',
            views_admin.representative_politician_match_view, name='representative_politician_match'),
    re_path(r'^politician_match_this_year/', views_admin.representative_politician_match_this_year_view,
            name='representative_politician_match_this_year'),
    re_path(r'^update_representative_from_politician/', views_admin.update_representative_from_politician_view,
            name='update_representative_from_politician'),
    re_path(r'^update_from_politicians/', views_admin.update_representatives_from_politicians_view,
            name='update_representatives_from_politicians'),
    re_path(r'^merge/$', views_admin.representative_merge_process_view, name='representative_merge_process'),
    re_path(r'^new/$', views_admin.representative_new_view, name='representative_new'),
    re_path(r'^(?P<representative_id>[0-9]+)/edit/$', views_admin.representative_edit_view, name='representative_edit'),
    re_path(r'^(?P<representative_id>[0-9]+)/retrieve_photos/$',
            views_admin.representative_retrieve_photos_view, name='representative_retrieve_photos'),
]
