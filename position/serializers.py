# position/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PositionEntered
from rest_framework import serializers


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionEntered
        fields = ('we_vote_id', 'ballot_item_display_name', 'ballot_item_image_url_https',
                  'speaker_display_name', 'speaker_image_url_https', 'date_entered', 'date_last_changed',
                  'organization_we_vote_id', 'voter_we_vote_id', 'public_figure_we_vote_id',
                  'google_civic_election_id', 'state_code',
                  'vote_smart_rating_id', 'vote_smart_time_span', 'vote_smart_rating', 'vote_smart_rating_name',
                  'contest_office_we_vote_id', 'candidate_campaign_we_vote_id',
                  'google_civic_candidate_name',
                  'politician_we_vote_id', 'contest_measure_we_vote_id',
                  'stance', 'statement_text', 'statement_html', 'more_info_url',
                  'from_scraper', 'organization_certified', 'volunteer_certified')
