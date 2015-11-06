# organization/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Organization
from rest_framework import serializers


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('we_vote_id', 'organization_name', 'organization_website', 'organization_twitter_handle', 'organization_type')
