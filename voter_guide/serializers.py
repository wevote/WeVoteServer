# voter_guide/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoterGuide
from rest_framework import serializers


class VoterGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoterGuide
        fields = ('we_vote_id',
                  'display_name',
                  'google_civic_election_id',
                  'image_url',
                  'last_updated',
                  'organization_we_vote_id',
                  'owner_we_vote_id',
                  'public_figure_we_vote_id',
                  'twitter_description',
                  'twitter_followers_count',
                  'twitter_handle',
                  'vote_smart_time_span',
                  'voter_guide_owner_type',
                  )
