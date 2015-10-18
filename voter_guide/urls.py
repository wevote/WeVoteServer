# voter_guide/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.voter_guide_list_view, name='voter_guide_list',),
    url(r'^generate/', views_admin.generate_voter_guides_view, name='generate_voter_guides'),

    # views
]
