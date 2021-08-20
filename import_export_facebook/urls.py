# import_export_facebook/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views, views_admin


urlpatterns = [
    re_path(r'^bulk_retrieve_facebook_photos/$',
            views_admin.bulk_retrieve_facebook_photos_view, name='bulk_retrieve_facebook_photos', ),
    re_path(r'^get_and_save_facebook_photo/$',
            views_admin.get_and_save_facebook_photo_view, name='get_and_save_facebook_photo', ),
]
