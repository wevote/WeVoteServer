# issue/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import url


urlpatterns = [
    # views_admin
    url(r'^$', views_admin.issue_list_view, name='issue_list',),
    url(r'^edit/(?P<issue_we_vote_id>wv[\w]{2}issue[\w]+)/$', views_admin.issue_edit_view, name='issue_edit'),
    url(r'^edit_process/$', views_admin.issue_edit_process_view, name='issue_edit_process'),
    url(r'^delete/', views_admin.issue_delete_process_view, name='issue_delete_process'),
    url(r'^delete_images/$', views_admin.issue_delete_images_view, name='issue_delete_images'),
    url(r'^import/$',
        views_admin.issues_import_from_master_server_view, name='issues_import_from_master_server'),
    url(r'^organization_link_import/$',
        views_admin.organization_link_to_issue_import_from_master_server_view,
        name='organization_link_to_issue_import_from_master_server'),
    url(r'^new/$', views_admin.issue_new_view, name='issue_new'),
    url(r'^partisan_analysis/$', views_admin.issue_partisan_analysis_view, name='issue_partisan_analysis'),
    url(r'^summary/(?P<issue_we_vote_id>wv[\w]{2}issue[\w]+)/$', views_admin.issue_summary_view,
        name='issue_summary'),
]
