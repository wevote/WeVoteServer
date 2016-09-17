# import_export_endorsements/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin


urlpatterns = [
    url(r'^(?P<organization_id>[0-9]+)/import_organization_endorsements/$', views_admin.import_organization_endorsements,
        name='import_organization_endorsements',),
]
