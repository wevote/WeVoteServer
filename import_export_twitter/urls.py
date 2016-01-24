# import_export_twitter/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views, views_admin


urlpatterns = [
    url(r'^(?P<organization_id>[0-9]+)/refresh_twitter_details/$',
        views_admin.refresh_twitter_details_view, name='refresh_twitter_details',),
    url(r'^(?P<organization_id>[0-9]+)/scrape_website_for_social_media/$',
        views_admin.scrape_website_for_social_media_view, name='scrape_website_for_social_media',),
    url(r'^scrape_social_media_from_all_organizations/$',
        views_admin.scrape_social_media_from_all_organizations_view, name='scrape_social_media_from_all_organizations'),
]
