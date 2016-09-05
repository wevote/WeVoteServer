# politician/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Politician
from rest_framework import serializers


class PoliticianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Politician
        fields = ('we_vote_id', 'first_name', 'middle_name', 'last_name',
                  'politician_name', 'google_civic_candidate_name', 'full_name_assembled',
                  'gender', 'birth_date',
                  'bioguide_id', 'thomas_id', 'lis_id', 'govtrack_id', 'opensecrets_id', 'vote_smart_id', 'fec_id',
                  'cspan_id', 'wikipedia_id', 'ballotpedia_id', 'house_history_id',
                  'maplight_id', 'washington_post_id', 'icpsr_id',
                  'tag_link', 'political_party', 'state_code', 'politician_twitter_handle',
                  )
