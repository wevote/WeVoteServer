# measure/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestMeasure
from rest_framework import serializers


class ContestMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContestMeasure
        fields = ('we_vote_id', 'measure_title', 'measure_subtitle', 'measure_text', 'measure_url',
                  'google_civic_election_id', 'ocd_division_id', 'maplight_id',
                  'primary_party', 'district_name', 'district_scope', 'district_id', 'state_code')
