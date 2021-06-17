# donate/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin


urlpatterns = [
    re_path(r'^plan_list/$', views_admin.organization_subscription_list_view, name='plan_list'),
]
