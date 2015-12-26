# quick_info/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import QuickInfo, QuickInfoMaster
from rest_framework import serializers


class QuickInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickInfo
        fields = ('we_vote_id', 'language', 'info_text', 'info_html', 'ballot_item_display_name', 'more_info_credit',
                  'more_info_url', 'last_updated', 'last_editor_we_vote_id', 'contest_office_we_vote_id',
                  'candidate_campaign_we_vote_id', 'politician_we_vote_id', 'contest_measure_we_vote_id',
                  'quick_info_master_we_vote_id', 'google_civic_election_id')


class QuickInfoMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickInfoMaster
        fields = ('we_vote_id', 'kind_of_ballot_item',
                  'language', 'info_text', 'info_html', 'master_entry_name', 'more_info_credit', 'more_info_url',
                  'last_updated', 'last_editor_we_vote_id')
