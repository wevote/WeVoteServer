# ballot/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BallotItem, BallotReturned
from rest_framework import serializers


class BallotItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BallotItem
        fields = ('ballot_item_display_name',
                  'contest_office_we_vote_id',
                  'contest_measure_we_vote_id',
                  'google_ballot_placement',
                  'google_civic_election_id',
                  'local_ballot_order',
                  'measure_subtitle',
                  'polling_location_we_vote_id',
                  )


class BallotReturnedSerializer(serializers.ModelSerializer):
    class Meta:
        model = BallotReturned
        fields = ('election_date',
                  'election_description_text',
                  'google_civic_election_id',
                  'latitude',
                  'longitude',
                  'normalized_line1',
                  'normalized_line2',
                  'normalized_city',
                  'normalized_state',
                  'normalized_zip',
                  'polling_location_we_vote_id',
                  'text_for_map_search',
                  )
