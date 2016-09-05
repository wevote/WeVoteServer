# organization/serializers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Organization
from rest_framework import serializers


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('we_vote_id', 'organization_name', 'organization_type',
                  'organization_description', 'state_served_code',
                  'organization_website', 'organization_email', 'organization_image',
                  'organization_twitter_handle', 'twitter_user_id', 'twitter_followers_count', 'twitter_description',
                  'twitter_location', 'twitter_name',
                  'twitter_profile_image_url_https',
                  'twitter_profile_background_image_url_https', 'twitter_profile_banner_url_https',
                  'organization_facebook',
                  'vote_smart_id',
                  'organization_contact_name',
                  'organization_address', 'organization_city', 'organization_state', 'organization_zip',
                  'organization_phone1', 'organization_phone2', 'organization_fax',
                  'wikipedia_page_title', 'wikipedia_page_id', 'wikipedia_photo_url', 'wikipedia_thumbnail_url',
                  'wikipedia_thumbnail_width', 'wikipedia_thumbnail_height',
                  'ballotpedia_page_title', 'ballotpedia_photo_url',
                  )
