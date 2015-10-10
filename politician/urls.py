# politician/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^$', views.PoliticianIndexView.as_view(), name='politician_list'),
    url(r'^(?P<politician_id>[0-9]+)/$', views.politician_detail_view, name='politician_detail'),
    url(r'^(?P<politician_id>[0-9]+)/tag_new/$', views.politician_tag_new_view, name='politician_tag_new'),
    url(r'^(?P<politician_id>[0-9]+)/tag_new_process/$',
        views.politician_tag_new_process_view, name='politician_tag_new_process'),
    # url(r'^(?P<pk>[0-9]+)/add_tag/$', views.PoliticianAddTagView.as_view(), name='politician_add_tag'),
]