# import_export_facebook/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin


urlpatterns = [
    url(r'^bulk_retrieve_facebook_photos/$',
        views_admin.bulk_retrieve_facebook_photos_view, name='bulk_retrieve_facebook_photos', ),
    url(r'^scrape_and_save_facebook_photo/$',
        views_admin.scrape_and_save_facebook_photo_view, name='scrape_and_save_facebook_photo', ),
]
