# import_export_twitter/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin


urlpatterns = [
    # views
    url(r'^process_sign_in_response/$', views.process_sign_in_response_view, name='process_sign_in_response'),

    # views_admin
    url(r'^(?P<candidate_id>[0-9]+)/refresh_twitter_candidate_details/$',
        views_admin.refresh_twitter_candidate_details_view, name='refresh_twitter_candidate_details',),
    url(r'^(?P<election_id>[0-9]+)/refresh_twitter_candidate_details_for_election/$',
        views_admin.refresh_twitter_candidate_details_for_election_view,
        name='refresh_twitter_candidate_details_for_election',),
    url(r'^(?P<organization_id>[0-9]+)/refresh_twitter_organization_details/$',
        views_admin.refresh_twitter_organization_details_view, name='refresh_twitter_organization_details',),
    url(r'^(?P<organization_id>[0-9]+)/scrape_website_for_social_media/$',
        views_admin.scrape_website_for_social_media_view, name='scrape_website_for_social_media',),
    url(r'^scrape_social_media_for_candidates_in_one_election/$',
        views_admin.scrape_social_media_for_candidates_in_one_election_view,
        name='scrape_social_media_for_candidates_in_one_election'),
    url(r'^scrape_social_media_from_all_organizations/$',
        views_admin.scrape_social_media_from_all_organizations_view, name='scrape_social_media_from_all_organizations'),
    url(r'^transfer_candidate_twitter_handles_from_google_civic/$',
        views_admin.transfer_candidate_twitter_handles_from_google_civic_view,
        name='transfer_candidate_twitter_handles_from_google_civic'),
]
