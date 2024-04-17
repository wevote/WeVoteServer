# googlebot_site_map/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^googlebot_site_map_list_view/$', views_admin.googlebot_site_map_list_view,
            name='googlebot_site_map_list_view',),
]
