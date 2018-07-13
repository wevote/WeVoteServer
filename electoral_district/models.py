# electoral_district/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_electoral_district_integer, fetch_site_unique_id_prefix

logger = wevote_functions.admin.get_logger(__name__)

ELECTORAL_DISTRICT_TYPE_BOROUGH = 'borough'
ELECTORAL_DISTRICT_TYPE_CITY = 'city'
ELECTORAL_DISTRICT_TYPE_CITY_COUNCIL = 'city_council'
ELECTORAL_DISTRICT_TYPE_CONGRESSIONAL = 'congressional'
ELECTORAL_DISTRICT_TYPE_COUNTY = 'county'
ELECTORAL_DISTRICT_TYPE_COUNTY_COUNCIL = 'county-council'
ELECTORAL_DISTRICT_TYPE_JUDICIAL = 'judicial'
ELECTORAL_DISTRICT_TYPE_MUNICIPALITY = 'municipality'
ELECTORAL_DISTRICT_TYPE_NATIONAL = 'national'
ELECTORAL_DISTRICT_TYPE_SCHOOL = 'school'
ELECTORAL_DISTRICT_TYPE_SPECIAL = 'special'
ELECTORAL_DISTRICT_TYPE_STATE = 'state'
ELECTORAL_DISTRICT_TYPE_STATE_HOUSE = 'state-house'
ELECTORAL_DISTRICT_TYPE_STATE_SENATE = 'state-senate'
ELECTORAL_DISTRICT_TYPE_TOWN = 'town'
ELECTORAL_DISTRICT_TYPE_TOWNSHIP = 'township'
ELECTORAL_DISTRICT_TYPE_UTILITY = 'utility'
ELECTORAL_DISTRICT_TYPE_VILLAGE = 'village'
ELECTORAL_DISTRICT_TYPE_WARD = 'ward'
ELECTORAL_DISTRICT_TYPE_WATER = 'water'
ELECTORAL_DISTRICT_TYPE_OTHER = 'other'

ELECTORAL_DISTRICT_TYPE_CHOICES = (
    (ELECTORAL_DISTRICT_TYPE_BOROUGH, 'borough'),
    (ELECTORAL_DISTRICT_TYPE_CITY, 'city'),
    (ELECTORAL_DISTRICT_TYPE_CITY_COUNCIL, 'city-council'),
    (ELECTORAL_DISTRICT_TYPE_CONGRESSIONAL, 'congressional'),
    (ELECTORAL_DISTRICT_TYPE_COUNTY, 'county'),
    (ELECTORAL_DISTRICT_TYPE_COUNTY_COUNCIL, 'county-council'),
    (ELECTORAL_DISTRICT_TYPE_JUDICIAL, 'judicial'),
    (ELECTORAL_DISTRICT_TYPE_MUNICIPALITY, 'municipality'),
    (ELECTORAL_DISTRICT_TYPE_NATIONAL, 'national'),
    (ELECTORAL_DISTRICT_TYPE_SCHOOL, 'school'),
    (ELECTORAL_DISTRICT_TYPE_SPECIAL, 'special'),
    (ELECTORAL_DISTRICT_TYPE_STATE, 'state'),
    (ELECTORAL_DISTRICT_TYPE_STATE_HOUSE, 'state-house'),
    (ELECTORAL_DISTRICT_TYPE_STATE_SENATE, 'state-senate'),
    (ELECTORAL_DISTRICT_TYPE_TOWN, 'town'),
    (ELECTORAL_DISTRICT_TYPE_TOWNSHIP, 'township'),
    (ELECTORAL_DISTRICT_TYPE_UTILITY, 'utility'),
    (ELECTORAL_DISTRICT_TYPE_VILLAGE, 'village'),
    (ELECTORAL_DISTRICT_TYPE_WARD, 'ward'),
    (ELECTORAL_DISTRICT_TYPE_WATER, 'water'),
    (ELECTORAL_DISTRICT_TYPE_OTHER, 'other'),
)


class ElectoralDistrict(models.Model):
    # The unique ID of this electoral_district. (Provided by CTCL).
    # TODO ctcl_id_temp is unique for each data file, however it may not be unique across different data feeds
    ctcl_id_temp = models.CharField(verbose_name="temporary ctcl id", max_length=255, null=True, unique=True)

    # Needs to allow we_vote_id to be null so we can use the get_or_create... function
    we_vote_id = models.CharField(verbose_name="permanent we vote id", max_length=255, null=True, unique=True)

    # required fields as per VIP specification for ElectoralDistrict are name and type, rest of the fields are optional
    electoral_district_name = models.CharField(verbose_name="electoral district name", max_length=255, null=True,
                                               unique=False)
    electoral_district_type = models.CharField(verbose_name="electoral district type",
                                               choices=ELECTORAL_DISTRICT_TYPE_CHOICES, max_length=16,
                                               default=ELECTORAL_DISTRICT_TYPE_STATE, blank=False, null=False)

    electoral_district_number = models.PositiveIntegerField(verbose_name="electoral district number", blank=True,
                                                            null=True)
    electoral_district_other_type = models.CharField(verbose_name="Allows for cataloging a new DistrictType option "
                                                                  "when Type is specified as other", null=True,
                                                     blank=True, max_length=255)

    ocd_id_external_id = models.CharField(verbose_name="ocd id external identifier", max_length=255, blank=True,
                                          null=True)
    ballotpedia_district_id = models.PositiveIntegerField(blank=True, null=True)
    ballotpedia_district_kml = models.URLField(verbose_name='url of kml file on ballotpedia', blank=True, null=True)
    ballotpedia_district_latitude = models.FloatField(null=True, verbose_name='latitude')
    ballotpedia_district_longitude = models.FloatField(null=True, verbose_name='longitude')
    ballotpedia_district_type = models.CharField(null=True, blank=True, max_length=255)
    ballotpedia_district_url = models.URLField(verbose_name='url of district on ballotpedia', blank=True, null=True)
    ballotpedia_district_ocd_id = models.CharField(verbose_name="ocd id identifier", max_length=255, blank=True,
                                                   null=True)

    state_code = models.CharField(verbose_name="state code", max_length=3, blank=True, null=True)

    # for now we are only handling ocd_id from the various ExternalIdentifier nodes. Refer to this link for details
    # http://vip-specification.readthedocs.io/en/release/built_rst/xml/enumerations/identifier_type.html
    # #multi-xml-identifier-type
    # fips_external_id = models.CharField(verbose_name="fips external id", max_length=255, blank=True, null=True)
    # local_level_external_id = models.CharField(verbose_name="local level external identifier", max_length=255,
    #                                            blank=True, null=True)
    # national_level_external_id = models.CharField(verbose_name="national level external identifier", max_length=255,
    #                                               blank=True, null=True)

    # state_level_external_id = models.CharField(verbose_name="state level external identifier", max_length=255,
    #                                            blank=True, null=True)
    # other_external_id = models.CharField(verbose_name="other external identifier", max_length=255, blank=True,
    #                                      null=True)
    # external_identifiers_link = models.ManyToManyField(External_Identifiers,
    #                                                    through='ElectoralDistrictExternalIdentifiersLink',
    #                                                    verbose_name="external identifier to connect VIP data to "
    #                                                                 "external datasets", )

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_electoral_district_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "dist" = tells us this is a unique id for an Electoral District
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}dist{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ElectoralDistrict, self).save(*args, **kwargs)

# EXTERNAL_IDENTIFIER_TYPE_FIPS = 'fips'
# EXTERNAL_IDENTIFIER_TYPE_LOCAL_LEVEL = 'local-level'
# EXTERNAL_IDENTIFIER_TYPE_NATIONAL_LEVEL = 'national-level'
# EXTERNAL_IDENTIFIER_TYPE_OCD_ID = 'ocd-id'
# EXTERNAL_IDENTIFIER_TYPE_STATE_LEVEL = 'state-level'
# EXTERNAL_IDENTIFIER_TYPE_OTHER = 'other'
#
# EXTERNAL_IDENTIFIER_TYPE_CHOICES = (
#     (EXTERNAL_IDENTIFIER_TYPE_FIPS, 'fips'),
#     (EXTERNAL_IDENTIFIER_TYPE_LOCAL_LEVEL, 'local-level'),
#     (EXTERNAL_IDENTIFIER_TYPE_NATIONAL_LEVEL, 'national-level'),
#     (EXTERNAL_IDENTIFIER_TYPE_OCD_ID, 'oci-id'),
#     (EXTERNAL_IDENTIFIER_TYPE_STATE_LEVEL, 'state-level'),
#     (EXTERNAL_IDENTIFIER_TYPE_OTHER, 'other'),
# )
#
# class ExternalIdentifier(models.Model):
#
#     # id = models.CharField(verbose_name="unique id for external identifier", null=False, blank=False, unique=True)
#     type = models.CharField(verbose_name='external identifier type', choices=EXTERNAL_IDENTIFIER_TYPE_CHOICES,
#                             default=EXTERNAL_IDENTIFIER_TYPE_OTHER, max_length=16, null=False, blank=False)
#     other_type = models.CharField(verbose_name='cataloging of external identifier outside of type choices',
#                                   max_length=255, null=True, blank=True)
#     value = models.CharField(verbose_name='value of the external identifier', null=False, blank=False, max_length=255)
#


class ElectoralDistrictLinkToPollingLocation(models.Model):
    """
    This class shows which districts a Polling location is in
    """
    # We are relying on built-in Python id field

    # The polling location's we_vote_id linked to the electoral district
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # The polling location's we_vote_id linked to the electoral district
    electoral_district_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # The district being linked
    ballotpedia_district_id = models.PositiveIntegerField(null=True, blank=True)

    # The date the the issue link was modified
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def __unicode__(self):
        return self.id


class ElectoralDistrictManager(models.Model):

    def retrieve_ballotpedia_district_ids_for_polling_location(self, polling_location_we_vote_id):
        ballotpedia_district_id_list = []
        ballotpedia_district_id_list_found = False
        success = True
        status = ""

        results = self.retrieve_electoral_district_link_list(polling_location_we_vote_id)
        if results['electoral_district_link_list_found']:
            electoral_district_link_list = results['electoral_district_link_list']
            for one_electoral_district_link in electoral_district_link_list:
                ballotpedia_district_id_list.append(one_electoral_district_link.ballotpedia_district_id)
            status += "ELECTORAL_DISTRICT_LIST_FOUND "
        else:
            status += results['status'] + "ELECTORAL_DISTRICT_LIST_NOT_FOUND "

        if len(ballotpedia_district_id_list):
            ballotpedia_district_id_list_found = True

        results = {
            'status': status,
            'success': success,
            'ballotpedia_district_id_list': ballotpedia_district_id_list,
            'ballotpedia_district_id_list_found': ballotpedia_district_id_list_found,
        }
        return results

    def retrieve_electoral_district_link_list(self, polling_location_we_vote_id="",
                                              electoral_district_we_vote_id="",
                                              ballotpedia_district_id=0,
                                              read_only=True):
        # Retrieve a list of electoral_district_link entries
        electoral_district_link_list_found = False
        electoral_district_link_list = []
        try:
            if positive_value_exists(read_only):
                electoral_district_query = ElectoralDistrictLinkToPollingLocation.objects.using('readonly').all()
            else:
                electoral_district_query = ElectoralDistrictLinkToPollingLocation.objects.all()

            if positive_value_exists(polling_location_we_vote_id):
                electoral_district_query = \
                    electoral_district_query.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
            if positive_value_exists(electoral_district_we_vote_id):
                electoral_district_query = \
                    electoral_district_query.filter(electoral_district_we_vote_id__iexact=electoral_district_we_vote_id)
            if positive_value_exists(ballotpedia_district_id):
                electoral_district_query = \
                    electoral_district_query.filter(ballotpedia_district_id=ballotpedia_district_id)

            electoral_district_link_list = list(electoral_district_query)
            if len(electoral_district_link_list):
                electoral_district_link_list_found = True
        except Exception as e:
            pass

        if electoral_district_link_list_found:
            results = {
                'status': "ELECTORAL_DISTRICT_LINK_LIST_FOUND",
                'success': True,
                'electoral_district_link_list': electoral_district_link_list,
                'electoral_district_link_list_found': electoral_district_link_list_found,
            }
            return results
        else:
            results = {
                'status': "ELECTORAL_DISTRICT_LINK_LIST_NOT_FOUND",
                'success': True,
                'electoral_district_link_list': [],
                'electoral_district_link_list_found': electoral_district_link_list_found,
            }
            return results

    def update_or_create_electoral_district(self, ctcl_id_temp, electoral_district_name,
                                            updated_values):
        """
        Either update or create an electoral district entry.
        """
        exception_multiple_object_returned = False
        created = False

        # ctcl_id_temp, electoral_district_name and electoral_district_type are required fields for
        # electoral_district. electoral_district_type is set to ELECTORAL_DISTRICT_TYPE_STATE as default value
        # TODO check if this default value is correct

        if not ctcl_id_temp:
            success = False
            status = 'MISSING_CTCL_TEMP_ID'
        elif not electoral_district_name:
            success = False
            status = 'MISSING_ELECTORAL_DISTRICT_NAME'
        else:
            new_electoral_district, created = ElectoralDistrict.objects.update_or_create(
                ctcl_id_temp=ctcl_id_temp, electoral_district_name=electoral_district_name, defaults=updated_values)
            if new_electoral_district or len(new_electoral_district):
                success = True
                status = 'ELECTORAL_DISTRICT_SAVED'
            else:
                success = False
                status = 'MULTIPLE_MATCHING_ELECTORAL_DISTRICTS_FOUND'

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_electoral_district_created':     created,
        }
        return results

    def update_or_create_electoral_district_link_to_polling_location(
            self, polling_location_we_vote_id, electoral_district_we_vote_id, ballotpedia_district_id):
        if not positive_value_exists(polling_location_we_vote_id):
            success = False
            status = "MISSING_POLLING_LOCATION_WE_VOTE_ID "
            results = {
                'success': success,
                'status': status,
            }
            return results
        if not positive_value_exists(electoral_district_we_vote_id) \
                and not positive_value_exists(ballotpedia_district_id):
            success = False
            status = "MISSING_BOTH_ELECTORAL_DISTRICT_WE_VOTE_ID_AND_BALLOTPEDIA_DISTRICT_ID "
            results = {
                'success': success,
                'status': status,
            }
            return results

        try:
            defaults = {
                'polling_location_we_vote_id': polling_location_we_vote_id,
            }
            if positive_value_exists(electoral_district_we_vote_id):
                defaults['electoral_district_we_vote_id'] = electoral_district_we_vote_id
            if positive_value_exists(ballotpedia_district_id):
                defaults['ballotpedia_district_id'] = ballotpedia_district_id

            if positive_value_exists(ballotpedia_district_id):
                ElectoralDistrictLinkToPollingLocation.objects.update_or_create(
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    ballotpedia_district_id=ballotpedia_district_id,
                    defaults=defaults,
                    )
            elif positive_value_exists(electoral_district_we_vote_id):
                ElectoralDistrictLinkToPollingLocation.objects.update_or_create(
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    electoral_district_we_vote_id=electoral_district_we_vote_id,
                    defaults=defaults,
                    )
            status = "POLLING_LOCATION_LINK_TO_ELECTORAL_DISTRICT_CREATED_OR_UPDATED "
            success = True

        except Exception as e:
            status = "POLLING_LOCATION_LINK_TO_ELECTORAL_DISTRICT_NOT_CREATED "
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

    def fetch_state_code(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            return ''
