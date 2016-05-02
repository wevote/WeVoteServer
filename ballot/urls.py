# ballot/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^(?P<ballot_returned_id>[0-9]+)/list_edit/$', views_admin.ballot_item_list_edit_view,
        name='ballot_item_list_edit'),
    url(r'^list_edit_process/$', views_admin.ballot_item_list_edit_process_view, name='ballot_item_list_edit_process'),
]
