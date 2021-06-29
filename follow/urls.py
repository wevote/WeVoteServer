# follow/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views_admin

# See also organization/urls.py for follow_organization-related urls


urlpatterns = [
    re_path(r'^repair_follow_organization/$',
        views_admin.repair_follow_organization_view, name='repair_follow_organization'),
]
