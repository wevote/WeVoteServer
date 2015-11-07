# election/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Election
from rest_framework import serializers


class ElectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Election
        fields = ('google_civic_election_id', 'election_name', 'election_day_text', 'ocd_division_id',
                  'get_election_state')
