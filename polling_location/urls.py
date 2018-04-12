# polling_location/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    url(r'^$', views_admin.polling_location_list_view, name='polling_location_list',),
    url(r'^import/$',
        views_admin.polling_locations_import_from_master_server_view,
        name='polling_locations_import_from_master_server'),
    # Processing incoming file with polling locations
    url(r'^import_polling_locations_process/$', views_admin.import_polling_locations_process_view,
        name='import_polling_locations_process'),
    url(r'^(?P<polling_location_local_id>[0-9]+)/edit/$', views_admin.polling_location_edit_view,
        name='polling_location_edit'),
    url(r'^(?P<polling_location_we_vote_id>wv[\w]{2}ploc[\w]+)/edit_we_vote_id/$',
        views_admin.polling_location_edit_view, name='polling_location_we_vote_id_edit'),
    url(r'^polling_location_edit_process/$', views_admin.polling_location_edit_process_view,
        name='polling_location_edit_process'),
    url(r'^(?P<polling_location_local_id>[0-9]+)/summary/$', views_admin.polling_location_summary_view,
        name='polling_location_summary'),
    url(r'^(?P<polling_location_we_vote_id>wv[\w]{2}ploc[\w]+)/summary/$',
        views_admin.polling_location_summary_by_we_vote_id_view, name='polling_location_summary_by_we_vote_id'),
]
