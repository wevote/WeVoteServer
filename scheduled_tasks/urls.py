# scheduled_tasks/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin


urlpatterns = [
    re_path(r'^task_list/$', views_admin.scheduled_tasks_list_view, name='task_list'),
]
