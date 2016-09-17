# candidate/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CandidateCampaign
from rest_framework import serializers


class CandidateCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateCampaign
        fields = ('we_vote_id', 'maplight_id', 'vote_smart_id', 'contest_office_we_vote_id', 'politician_we_vote_id',
                  'candidate_name', 'google_civic_candidate_name', 'party',
                  'photo_url', 'photo_url_from_maplight', 'photo_url_from_vote_smart',
                  'order_on_ballot', 'google_civic_election_id', 'ocd_division_id', 'state_code',
                  'candidate_url', 'facebook_url', 'twitter_url', 'twitter_user_id', 'candidate_twitter_handle',
                  'twitter_name', 'twitter_location',
                  'twitter_followers_count', 'twitter_profile_image_url_https', 'twitter_description',
                  'google_plus_url', 'youtube_url',
                  'candidate_email', 'candidate_phone',
                  'wikipedia_page_id', 'wikipedia_page_title', 'wikipedia_photo_url',
                  'ballotpedia_page_title', 'ballotpedia_photo_url',
                  'ballot_guide_official_statement',
                  )
