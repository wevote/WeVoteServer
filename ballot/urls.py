# ballot/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^import_ballot_items/$',
        views_admin.ballot_items_import_from_master_server_view,
        name='ballot_items_import_from_master_server'),
    url(r'^import_ballot_returned/$',
        views_admin.ballot_returned_import_from_master_server_view,
        name='ballot_returned_import_from_master_server'),
    url(r'^(?P<ballot_returned_id>[0-9]+)/delete/$', views_admin.ballot_returned_delete_process_view,
        name='ballot_returned_delete_process'),
    url(r'^(?P<ballot_returned_id>[0-9]+)/list_edit/$', views_admin.ballot_item_list_edit_view,
        name='ballot_item_list_edit'),
    url(r'^(?P<polling_location_we_vote_id>wv[\w]{2}ploc[\w]+)/list_edit_by_polling_location/$',
        views_admin.ballot_item_list_by_polling_location_edit_view,
        name='ballot_item_list_by_polling_location_edit'),
    url(r'^list_edit_process/$', views_admin.ballot_item_list_edit_process_view, name='ballot_item_list_edit_process'),
    url(r'^ballot_items_repair/$', views_admin.ballot_items_repair_view, name='ballot_items_repair'),
    url(r'^update_ballot_returned_latitude_and_longitude/$',
        views_admin.update_ballot_returned_with_latitude_and_longitude_view,
        name='update_ballot_returned_latitude_and_longitude'),
]
