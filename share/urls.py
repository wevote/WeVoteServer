# share/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from share import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.shared_item_list_view, name='shared_item_list',),
]
