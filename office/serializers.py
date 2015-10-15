# candidate/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ContestOffice
from rest_framework import serializers


class ContestOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContestOffice
        fields = ('we_vote_id', 'office_name')
