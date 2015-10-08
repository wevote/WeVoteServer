# apis_v1/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from rest_framework import serializers
from voter.models import Voter


class VoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = ('id', 'first_name', 'last_name', 'email')

