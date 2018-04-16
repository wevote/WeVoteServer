# import_export_ballotpedia/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^$', views_admin.retrieve_candidates_from_api_view, name='ballotpedia_home',),
    url(r'^retrieve_candidates/$', views_admin.retrieve_candidates_from_api_view, name='retrieve_candidates'),
    url(r'^import_ballot_items_for_location/$', views_admin.import_ballot_items_for_location_view,
        name='import_ballot_items_for_location'),
    url(r'^(?P<election_local_id>[0-9]+)/retrieve_distributed_ballotpedia_ballots/$',
        views_admin.retrieve_distributed_ballotpedia_ballots_view, name='retrieve_distributed_ballotpedia_ballots'),
]
