# import_export_twitter/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import re_path

from . import views, views_admin


urlpatterns = [
    # views

    # views_admin
    re_path(r'^(?P<candidate_id>[0-9]+)/refresh_twitter_candidate_details/$',
        views_admin.refresh_twitter_candidate_details_view, name='refresh_twitter_candidate_details',),
    re_path(r'^delete_images_view/$',
        views_admin.delete_images_view, name='delete_images_view',),
    re_path(r'^(?P<election_id>[0-9]+)/refresh_twitter_candidate_details_for_election/$',
        views_admin.refresh_twitter_candidate_details_for_election_view,
        name='refresh_twitter_candidate_details_for_election',),
    re_path(r'^(?P<elected_official_id>[0-9]+)/refresh_twitter_elected_official_details/$',
        views_admin.refresh_twitter_elected_official_details_view, name='refresh_twitter_elected_official_details', ),
    re_path(r'^(?P<organization_id>[0-9]+)/refresh_twitter_organization_details/$',
        views_admin.refresh_twitter_organization_details_view, name='refresh_twitter_organization_details',),
    re_path(r'^(?P<politician_id>[0-9]+)/refresh_twitter_politician_details/$',
        views_admin.refresh_twitter_politician_details_view, name='refresh_twitter_politician_details',),
    re_path(r'^(?P<organization_id>[0-9]+)/scrape_website_for_social_media/$',
        views_admin.scrape_website_for_social_media_view, name='scrape_website_for_social_media',),
    re_path(r'^refresh_twitter_data_for_organizations/$',
        views_admin.refresh_twitter_data_for_organizations_view,
        name='refresh_twitter_data_for_organizations'),
    re_path(r'^scrape_social_media_for_candidates_in_one_election/$',
        views_admin.scrape_social_media_for_candidates_in_one_election_view,
        name='scrape_social_media_for_candidates_in_one_election'),
    re_path(r'^scrape_social_media_from_all_organizations/$',
        views_admin.scrape_social_media_from_all_organizations_view, name='scrape_social_media_from_all_organizations'),
    re_path(r'^transfer_candidate_twitter_handles_from_google_civic/$',
        views_admin.transfer_candidate_twitter_handles_from_google_civic_view,
        name='transfer_candidate_twitter_handles_from_google_civic'),
    re_path(r'^delete_possible_twitter_handles/(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.delete_possible_twitter_handles_view, name='delete_possible_twitter_handles', ),
    re_path(r'^retrieve_possible_twitter_handles/(?P<candidate_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.retrieve_possible_twitter_handles_view, name='retrieve_possible_twitter_handles', ),
    re_path(r'^bulk_retrieve_possible_twitter_handles/$',
        views_admin.bulk_retrieve_possible_twitter_handles_view, name='bulk_retrieve_possible_twitter_handles', ),
]
