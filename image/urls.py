# image/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin

urlpatterns = [
    url(r'^cache_images_locally_for_all_organizations/$', views_admin.cache_images_locally_for_all_organizations_view,
        name='cache_images_locally_for_all_organizations'),
    url(r'^cache_images_locally_for_all_voters/$', views_admin.cache_images_locally_for_all_voters_view,
        name='cache_images_locally_for_all_voters'),
    url(r'^create_resized_images_for_all_organizations/$', views_admin.create_resized_images_for_all_organizations_view,
        name='create_resized_images_for_all_organizations'),
    url(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/create_resized_images_for_organization/$',
        views_admin.create_resized_images_for_organization_view, name='create_resized_images_for_organization'),
    url(r'^(?P<voter_id>[0-9]+)/create_resized_images_for_voters/$',
        views_admin.create_resized_images_for_voters_view, name='create_resized_images_for_voters'),
    url(r'^(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/images_for_one_candidate/$',
        views_admin.images_for_one_candidate_view, name='images_for_one_candidate'),
    url(r'^(?P<organization_we_vote_id>wv[\w]{2}org[\w]+)/images_for_one_organization/$',
        views_admin.images_for_one_organization_view, name='images_for_one_organization'),
    url(r'^(?P<voter_id>[0-9]+)/images_for_one_voter/$',
        views_admin.images_for_one_voter_view, name='images_for_one_voter'),

]
