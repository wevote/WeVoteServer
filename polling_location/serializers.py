# polling_location/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import PollingLocation
from rest_framework import serializers


class PollingLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollingLocation
        fields = ('we_vote_id',
                  'city',
                  'directions_text',
                  'line1',
                  'line2',
                  'location_name',
                  'polling_hours_text',
                  'state',
                  'zip_long',
                  )
