# import_export_facebook/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin


urlpatterns = [
    # views

    # views_admin
    url(r'^bulk_retrieve_facebook_photos_view/$',
        views_admin.bulk_retrieve_facebook_photos_view, name='bulk_retrieve_facebook_photos_view', ),
]
