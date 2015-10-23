# candidate/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CandidateCampaign
from rest_framework import serializers


class CandidateCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateCampaign
        fields = ('we_vote_id', 'maplight_id', 'contest_office_we_vote_id', 'politician_we_vote_id',
                  'candidate_name', 'google_civic_candidate_name', 'party', 'photo_url', 'photo_url_from_maplight',
                  'order_on_ballot', 'google_civic_election_id', 'ocd_division_id', 'state_code',
                  'candidate_url', 'facebook_url', 'twitter_url', 'google_plus_url', 'youtube_url',
                  'candidate_email', 'candidate_phone'
                  )
