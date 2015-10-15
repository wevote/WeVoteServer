# candidate/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import CandidateCampaign
from rest_framework import serializers


class CandidateCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateCampaign
        fields = ('we_vote_id', 'candidate_name', 'candidate_url', 'candidate_email', 'facebook_url', 'google_civic_election_id',
                  'google_plus_url', 'order_on_ballot', 'party', 'candidate_phone', 'photo_url', 'twitter_url', 'youtube_url')
