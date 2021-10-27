# polling_location/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.polling_location_list_view, name='polling_location_list', ),
    re_path(r'^import/$',
            views_admin.polling_locations_import_from_master_server_view,
            name='polling_locations_import_from_master_server'),
    re_path(r'^import_status/$',
            views_admin.polling_locations_import_from_master_server_status_view,
            name='polling_locations_import_from_master_server_status'),
    # Processing incoming file with map points
    re_path(r'^import_polling_locations_process/$', views_admin.import_polling_locations_process_view,
            name='import_polling_locations_process'),
    re_path(r'^(?P<polling_location_local_id>[0-9]+)/edit/$', views_admin.polling_location_edit_view,
            name='polling_location_edit'),
    re_path(r'^(?P<polling_location_local_id>[0-9]+)/visualize/$', views_admin.polling_location_visualize_view,
            name='polling_location_visualize'),
    re_path(r'^(?P<polling_location_we_vote_id>wv[\w]{2}ploc[\w]+)/edit_we_vote_id/$',
            views_admin.polling_location_edit_view, name='polling_location_we_vote_id_edit'),
    re_path(r'^polling_location_edit_process/$', views_admin.polling_location_edit_process_view,
            name='polling_location_edit_process'),
    re_path(r'^polling_location_list_process/$', views_admin.polling_location_list_process_view,
            name='polling_location_list_process'),
    re_path(r'^polling_locations_add_address_from_latitude_and_longitude/$',
            views_admin.polling_locations_add_address_from_latitude_and_longitude_view,
            name='polling_locations_add_address_from_latitude_and_longitude'),
    re_path(r'^polling_locations_add_latitude_and_longitude/$',
            views_admin.polling_locations_add_latitude_and_longitude_view,
            name='polling_locations_add_latitude_and_longitude'),
    re_path(r'^statistics/$', views_admin.polling_location_statistics_view, name='polling_location_statistics', ),
    re_path(r'^(?P<polling_location_local_id>[0-9]+)/summary/$', views_admin.polling_location_summary_view,
            name='polling_location_summary'),
    re_path(r'^(?P<polling_location_we_vote_id>wv[\w]{2}ploc[\w]+)/summary/$',
            views_admin.polling_location_summary_by_we_vote_id_view, name='polling_location_summary_by_we_vote_id'),
    re_path(r'^soft_delete_duplicates/$',
            views_admin.soft_delete_duplicates_view,
            name='soft_delete_duplicates'),
]
