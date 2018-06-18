# import_export_ballotpedia/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    # url(r'^$', views_admin.retrieve_ballotpedia_candidates_by_election_from_api_view, name='ballotpedia_home',),
    url(r'^(?P<election_local_id>[0-9]+)/attach_ballotpedia_election/$',
        views_admin.attach_ballotpedia_election_view,
        name='attach_ballotpedia_election'),
    url(r'^import_ballot_items_for_location/$', views_admin.import_ballot_items_for_location_view,
        name='import_ballot_items_for_location'),
    url(r'^retrieve_candidates/$', views_admin.retrieve_ballotpedia_candidates_by_election_from_api_view,
        name='retrieve_candidates'),
    url(r'^(?P<election_local_id>[0-9]+)/retrieve_ballotpedia_data_for_polling_locations/$',
        views_admin.retrieve_ballotpedia_data_for_polling_locations_view,
        name='retrieve_ballotpedia_data_for_polling_locations'),
    url(r'^retrieve_offices/$', views_admin.retrieve_ballotpedia_offices_by_election_from_api_view,
        name='retrieve_offices'),
]
