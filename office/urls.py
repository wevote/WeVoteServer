# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.office_list_view, name='office_list',),
    url(r'^compare_two_offices/$',
        views_admin.compare_two_offices_for_merge_view, name='compare_two_offices_for_merge'),
    url(r'^delete/$', views_admin.office_delete_process_view, name='office_delete_process'),
    url(r'^(?P<office_id>[0-9]+)/find_duplicate_office/$',
        views_admin.find_duplicate_office_view, name='find_duplicate_office'),
    url(r'^duplicate_offices/$',
        views_admin.find_and_merge_duplicate_offices_view, name='find_and_merge_duplicate_offices'),
    url(r'^edit_process/$', views_admin.office_edit_process_view, name='office_edit_process'),
    # url(r'^export/', views_admin.OfficesSyncOutView.as_view(), name='offices_export'),
    url(r'^import/$',
        views_admin.offices_import_from_master_server_view, name='offices_import_from_master_server'),
    url(r'^merge/$', views_admin.office_merge_process_view, name='office_merge_process'),
    url(r'^new/$', views_admin.office_new_view, name='office_new'),
    url(r'^(?P<office_id>[0-9]+)/edit/$', views_admin.office_edit_view, name='office_edit'),
    url(r'^(?P<contest_office_we_vote_id>wv[\w]{2}off[\w]+)/edit/$',
        views_admin.office_edit_view, name='office_edit_we_vote_id'),
    url(r'^(?P<office_id>[0-9]+)/summary/$', views_admin.office_summary_view, name='office_summary'),
]
