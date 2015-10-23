# admin_tools/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.admin_home_view, name='admin_home',),
    url(r'^import_test_data/$', views.import_test_data_view, name='import_test_data'),
]
