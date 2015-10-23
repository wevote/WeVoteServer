# candidate/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestOffice
from rest_framework import serializers


class ContestOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContestOffice
        fields = ('we_vote_id', 'office_name', 'google_civic_election_id', 'ocd_division_id', 'maplight_id',
                  'ballotpedia_id', 'wikipedia_id', 'number_voting_for', 'number_elected', 'state_code',
                  'primary_party', 'district_name', 'district_scope', 'district_id', 'contest_level0',
                  'contest_level1', 'contest_level2', 'electorate_specifications', 'special')
