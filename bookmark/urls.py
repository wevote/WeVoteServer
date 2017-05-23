# bookmark/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

# See also organization/urls.py for follow_organization-related urls


urlpatterns = [
    # url(r'^export/', views_admin.ExportBookmarkItemDataView.as_view(), name='bookmark_item_export'),
    # url(r'^update_bookmarks/$',
    #     views_admin.find_and_update_bookmarks_view, name='find_and_update_bookmarks'),
]
