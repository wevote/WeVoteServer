# voter_guide/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    # views_admin
    url(r'^$', views_admin.voter_guide_list_view, name='voter_guide_list',),
    url(r'^generate/', views_admin.generate_voter_guides_view, name='generate_voter_guides'),
    url(r'^refresh/', views_admin.refresh_existing_voter_guides_view, name='refresh_existing_voter_guides'),
    url(r'^generate_one_election/',
        views_admin.generate_voter_guides_for_one_election_view, name='generate_voter_guides_one_election'),

    # views
]
