# position_like/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^export/', views_admin.export_position_like_data_view(), name='position_like_export'),
]
