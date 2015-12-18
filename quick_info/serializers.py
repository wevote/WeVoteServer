# quick_info/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import QuickInfo
from rest_framework import serializers


class QuickInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickInfo
        fields = ('we_vote_id', 'organization_we_vote_id',
                  'candidate_campaign_we_vote_id', 'google_civic_candidate_name',
                  'measure_campaign_we_vote_id', 'date_entered', 'google_civic_election_id', 'stance', 'more_info_url',
                  'statement_text', 'statement_html')
