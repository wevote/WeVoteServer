# polling_location/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    url(r'^$', views_admin.polling_location_list_view, name='polling_location_list',),
    # Interface for bringing in polling locations
    url(r'^import_polling_locations/$', views_admin.import_polling_locations_view, name='import_polling_locations'),
    # Processing incoming file with polling locations
    url(r'^import_polling_locations_process/$', views_admin.import_polling_locations_process_view,
        name='import_polling_locations_process'),
]
