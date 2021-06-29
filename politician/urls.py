# politician/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import re_path


urlpatterns = [
    re_path(r'^$', views_admin.politician_list_view, name='politician_list',),
    re_path(r'^edit_process/$', views_admin.politician_edit_process_view, name='politician_edit_process'),
    re_path(r'^delete/', views_admin.politician_delete_process_view, name='politician_delete_process'),
    re_path(r'^import/$',
        views_admin.politicians_import_from_master_server_view, name='politicians_import_from_master_server'),
    re_path(r'^new/$', views_admin.politician_new_view, name='politician_new'),
    re_path(r'^(?P<politician_id>[0-9]+)/edit/$', views_admin.politician_edit_view, name='politician_edit'),
    re_path(r'^(?P<politician_we_vote_id>wv[\w]{2}pol[\w]+)/edit$',
        views_admin.politician_edit_view, name='politician_we_vote_id_edit'),
    re_path(r'^(?P<politician_id>[0-9]+)/retrieve_photos/$',
        views_admin.politician_retrieve_photos_view, name='politician_retrieve_photos'),
    # re_path(r'^(?P<politician_id>[0-9]+)/tag_new/$', views.politician_tag_new_view, name='politician_tag_new'),
    # re_path(r'^(?P<politician_id>[0-9]+)/tag_new_process/$',
    #     views.politician_tag_new_process_view, name='politician_tag_new_process'),
    # re_path(r'^(?P<pk>[0-9]+)/add_tag/$', views.PoliticianAddTagView.as_view(), name='politician_add_tag'),
]