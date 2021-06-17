# import_export_google_civic/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from . import views_admin
from django.conf.urls import re_path


urlpatterns = [
    # views_admin
    re_path(r'^retrieve_representatives_for_many_addresses/$',
        views_admin.retrieve_representatives_for_many_addresses_view, name='retrieve_representatives_for_many_addresses'),
    re_path(r'^retrieve_representatives_for_one_address/$',
        views_admin.retrieve_representatives_for_one_address_view, name='retrieve_representatives_for_one_address'),
]
