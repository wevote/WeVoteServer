# reaction/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^export/', views_admin.export_reaction_like_data_view(), name='reaction_like_export'),
]
