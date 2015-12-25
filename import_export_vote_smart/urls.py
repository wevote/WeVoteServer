# import_export_vote_smart/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin


urlpatterns = [
    url(r'^import_states/$', views_admin.import_states_view, name='import_states'),
    url(r'^states/(?P<pk>[A-Z]+)/$', views_admin.state_detail_view, name='state_detail'),
]
