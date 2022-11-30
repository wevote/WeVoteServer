# share/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from share import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.voter_who_shares_summary_list_view, name='voter_who_shares_summary_list',),
    re_path(r'^shared_item_list/$', views_admin.shared_item_list_view, name='shared_item_list'),
]
