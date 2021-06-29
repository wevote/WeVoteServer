# ballot/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    # views_admin
    re_path(r'^import_ballot_items/$',
        views_admin.ballot_items_import_from_master_server_view,
        name='ballot_items_import_from_master_server'),
    re_path(r'^import_ballot_returned/$',
        views_admin.ballot_returned_import_from_master_server_view,
        name='ballot_returned_import_from_master_server'),
    re_path(r'^(?P<ballot_item_id>[0-9]+)/delete_ballot_item/$', views_admin.ballot_item_delete_process_view,
        name='ballot_item_delete_process'),
    re_path(r'^(?P<ballot_returned_id>[0-9]+)/delete_ballot_returned/$', views_admin.ballot_returned_delete_process_view,
        name='ballot_returned_delete_process'),
    re_path(r'^(?P<ballot_returned_id>[0-9]+)/list_edit/$', views_admin.ballot_item_list_edit_view,
        name='ballot_item_list_edit'),
    re_path(r'^(?P<ballot_returned_we_vote_id>wv[\w]{2}ballot[\w]+)/list_edit_by_we_vote_id/$',
        views_admin.ballot_item_list_edit_view,
        name='ballot_item_list_edit_by_we_vote_id'),
    re_path(r'^(?P<polling_location_we_vote_id>wv[\w]{2}ploc[\w]+)/list_edit_by_polling_location/$',
        views_admin.ballot_item_list_by_polling_location_edit_view,
        name='ballot_item_list_by_polling_location_edit'),
    re_path(r'^list_edit_process/$', views_admin.ballot_item_list_edit_process_view, name='ballot_item_list_edit_process'),
    re_path(r'^ballot_items_repair/$', views_admin.ballot_items_repair_view, name='ballot_items_repair'),
    re_path(r'^update_ballot_returned_latitude_and_longitude/$',
        views_admin.update_ballot_returned_with_latitude_and_longitude_view,
        name='update_ballot_returned_latitude_and_longitude'),
]
