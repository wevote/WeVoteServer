# import_export_ctcl/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^$', views_admin.import_export_ctcl_index_view, name='import_export_ctcl_index'),
]
