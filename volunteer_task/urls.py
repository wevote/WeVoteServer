# volunteer_task/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import re_path

from . import views_admin

urlpatterns = [
    re_path(r'^$', views_admin.performance_list_view, name='performance_list',),
    # re_path(r'^authenticate_manually/$', views_admin.voter_authenticate_manually_view, name='authenticate_manually'),
]
