# elected_official/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.elected_official_list_view, name='elected_official_list',),
    url(r'^edit_process/$', views_admin.elected_official_edit_process_view, name='elected_official_edit_process'),
    url(r'^delete/', views_admin.elected_official_delete_process_view, name='elected_official_delete_process'),
    # url(r'^import/$',
    #     views_admin.elected_officials_import_from_master_server_view,
    # name='elected_officials_import_from_master_server'),
    url(r'^new/$', views_admin.elected_official_new_view, name='elected_official_new'),
    url(r'^(?P<elected_official_id>[0-9]+)/edit/$', views_admin.elected_official_edit_view,
        name='elected_official_edit'),
    url(r'^(?P<elected_official_id>[0-9]+)/retrieve_photos/$',
        views_admin.elected_official_retrieve_photos_view, name='elected_official_retrieve_photos'),
]
