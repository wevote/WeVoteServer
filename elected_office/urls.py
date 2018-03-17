# office/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.elected_office_list_view, name='elected_office_list', ),
    url(r'^delete/$', views_admin.elected_office_delete_process_view, name='elected_office_delete_process'),
    url(r'^edit_process/$', views_admin.elected_office_edit_process_view, name='elected_office_edit_process'),
    url(r'^new/$', views_admin.elected_office_new_view, name='elected_office_new'),
    url(r'^(?P<elected_office_id>[0-9]+)/edit/$', views_admin.elected_office_edit_view, name='elected_office_edit'),
    url(r'^(?P<elected_office_id>[0-9]+)/summary/$', views_admin.elected_office_summary_view,
        name='elected_office_summary'),

]
