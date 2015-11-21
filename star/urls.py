# star/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

# See also organization/urls.py for follow_organization-related urls


urlpatterns = [
    url(r'^export/', views_admin.ExportStarItemDataView.as_view(), name='star_item_export'),
]
