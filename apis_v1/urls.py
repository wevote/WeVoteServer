# apis_v1/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url
from . import views
from . import views_docs

urlpatterns = [
    url(r'^deviceIdGenerate/$', views.device_id_generate, name='deviceIdGenerate'),

    url(r'^docs/$', views_docs.apis_index, name='apisIndex'),
    url(r'^docs/deviceIdGenerate/$', views_docs.device_id_generate, name='deviceIdGenerateDocs'),
]
