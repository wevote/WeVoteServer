# candidate/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.candidate_list_view, name='candidate_list',),
    url(r'^edit_process/$', views_admin.candidate_edit_process_view, name='candidate_edit_process'),
    url(r'^export/', views_admin.ExportCandidateCampaignDataView.as_view(), name='candidates_export'),
    url(r'^new/$', views_admin.candidate_new_view, name='candidate_new'),
    url(r'^(?P<candidate_id>[0-9]+)/edit/$', views_admin.candidate_edit_view, name='candidate_edit'),
    url(r'^(?P<candidate_id>[0-9]+)/summary/$', views_admin.candidate_summary_view,
        name='candidate_summary'),
]
