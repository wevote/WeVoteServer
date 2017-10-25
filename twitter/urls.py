# twitter/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also import_export_twitter/urls.py
from django.conf.urls import url

from . import views, views_admin

urlpatterns = [
    # views

    # views_admin
    url(r'^delete_possible_twitter_handles/(?P<candidate_campaign_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.delete_possible_twitter_handles_view, name='delete_possible_twitter_handles',),
    url(r'^retrieve_possible_twitter_handles/(?P<candidate_campaign_we_vote_id>wv[\w]{2}cand[\w]+)/$',
        views_admin.retrieve_possible_twitter_handles_view, name='retrieve_possible_twitter_handles',),
    url(r'^bulk_retrieve_possible_twitter_handles/$',
        views_admin.bulk_retrieve_possible_twitter_handles_view, name='bulk_retrieve_possible_twitter_handles',),
]
