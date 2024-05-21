# office_held/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from django.db import models
from django.db.models import F, Q, Count, FloatField, ExpressionWrapper, Func
from geopy.geocoders import get_geocoder_for_service
from geopy.exc import GeocoderQuotaExceeded
from exception.models import handle_exception, handle_record_found_more_than_one_exception
import sys
from wevote_settings.constants import OFFICE_HELD_YEARS_AVAILABLE
from wevote_settings.models import fetch_site_unique_id_prefix, fetch_next_we_vote_id_office_held_integer
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists

DEG_TO_RADS = 0.0174533
DISTANCE_LIMIT_IN_MILES = 25
GEOCODE_TIMEOUT = 10
GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
RADIUS_OF_EARTH_IN_MILES = 3958.756
WE_VOTE_API_KEY = get_environment_variable("WE_VOTE_API_KEY")

logger = wevote_functions.admin.get_logger(__name__)


class Sin(Func):
    function = 'SIN'


class Cos(Func):
    function = 'COS'


class ACos(Func):
    function = 'ACOS'


def attach_defaults_values_to_office_held_object(office_held, defaults):
    if 'ballotpedia_id' in defaults:
        office_held.ballotpedia_id = defaults['ballotpedia_id']
    if 'ctcl_uuid' in defaults:
        office_held.ctcl_uuid = defaults['ctcl_uuid']
    if 'district_id' in defaults:
        office_held.district_id = defaults['district_id']
    if 'district_name' in defaults:
        office_held.district_name = defaults['district_name']
    if 'district_scope' in defaults:
        office_held.district_scope = defaults['district_scope']
    if 'google_civic_office_held_name' in defaults:
        office_held.google_civic_office_held_name = defaults['google_civic_office_held_name']
    if 'google_civic_office_held_name2' in defaults:
        office_held.google_civic_office_held_name2 = defaults['google_civic_office_held_name2']
    if 'google_civic_office_held_name3' in defaults:
        office_held.google_civic_office_held_name3 = defaults['google_civic_office_held_name3']
    if 'maplight_id' in defaults:
        office_held.maplight_id = defaults['maplight_id']
    if 'number_elected' in defaults:
        office_held.number_elected = defaults['number_elected']
    if 'ocd_division_id' in defaults:
        office_held.ocd_division_id = defaults['ocd_division_id']
    if 'office_held_description' in defaults:
        office_held.office_held_description = defaults['office_held_description']
    if 'office_held_description_es' in defaults:
        office_held.office_held_description_es = defaults['office_held_description_es']
    if 'office_held_is_partisan' in defaults:
        office_held.office_held_is_partisan = defaults['office_held_is_partisan']
    if 'office_held_level0' in defaults:
        office_held.office_held_level0 = defaults['office_held_level0']
    if 'office_held_level1' in defaults:
        office_held.office_held_level1 = defaults['office_held_level1']
    if 'office_held_level2' in defaults:
        office_held.office_held_level2 = defaults['office_held_level2']
    if 'office_held_name_es' in defaults:
        office_held.office_held_name_es = defaults['office_held_name_es']
    if 'office_held_role0' in defaults:
        office_held.office_held_role0 = defaults['office_held_role0']
    if 'office_held_role1' in defaults:
        office_held.office_held_role1 = defaults['office_held_role1']
    if 'office_held_role2' in defaults:
        office_held.office_held_role2 = defaults['office_held_role2']
    if 'primary_party' in defaults:
        office_held.primary_party = defaults['primary_party']
    if 'race_office_level' in defaults:
        office_held.race_office_level = defaults['race_office_level']
    if 'state_code' in defaults:
        office_held.state_code = defaults['state_code']
    if 'wikipedia_id' in defaults:
        office_held.wikipedia_id = defaults['wikipedia_id']
    year_with_data_list = OFFICE_HELD_YEARS_AVAILABLE
    for year in year_with_data_list:
        year_with_data_key = 'year_with_data_' + str(year)
        if year_with_data_key in defaults:
            setattr(office_held, year_with_data_key, defaults[year_with_data_key])
    return office_held


def attach_defaults_values_to_offices_held_object(offices_held_for_location, defaults):
    if 'date_last_retrieved' in defaults:
        offices_held_for_location.date_last_retrieved = defaults['date_last_retrieved']
    if 'polling_location_we_vote_id' in defaults:
        offices_held_for_location.polling_location_we_vote_id = defaults['polling_location_we_vote_id']
    if 'state_code' in defaults:
        offices_held_for_location.state_code = defaults['state_code']
    if 'voter_we_vote_id' in defaults:
        offices_held_for_location.voter_we_vote_id = defaults['voter_we_vote_id']
    year_with_data_list = OFFICE_HELD_YEARS_AVAILABLE
    for year in year_with_data_list:
        year_with_data_key = 'year_with_data_' + str(year)
        if year_with_data_key in defaults:
            setattr(offices_held_for_location, year_with_data_key, defaults[year_with_data_key])
    index_number = 1
    while index_number < 31:
        office_held_name_field_name = "office_held_name_{:02d}".format(index_number)
        if office_held_name_field_name in defaults:
            setattr(offices_held_for_location, office_held_name_field_name, defaults[office_held_name_field_name])
        office_held_we_vote_id_field_name = "office_held_we_vote_id_{:02d}".format(index_number)
        if office_held_we_vote_id_field_name in defaults:
            setattr(offices_held_for_location, office_held_we_vote_id_field_name,
                    defaults[office_held_we_vote_id_field_name])
        index_number += 1
    return offices_held_for_location


class ContestOfficeToOfficeHeldLink(models.Model):
    """
    With this table, we can store the ContestOffices leading to a Candidate becoming a Representative for OfficeHeld
    """
    contest_office_we_vote_id = models.CharField(db_index=True, max_length=255, null=False, unique=False)
    office_held_we_vote_id = models.CharField(db_index=True, max_length=255, null=False, unique=False)
    state_code = models.CharField(db_index=True, max_length=2, null=True)
    # The year this contest happened
    contest_office_year = models.PositiveIntegerField(default=0)

    def office_held(self):
        try:
            office = OfficeHeld.objects.get(we_vote_id=self.office_held_we_vote_id)
        except OfficeHeld.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("RepresentativeToOfficeHeldLink.office_held Found multiple")
            return
        except OfficeHeld.DoesNotExist:
            logger.error("RepresentativeToOfficeHeldLink.office_held not attached to object, id: "
                         "" + str(self.office_held_we_vote_id))
            return
        return office


class OfficeHeld(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "officeheld", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_office_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this office held", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_id = models.CharField(verbose_name="google civic district id", max_length=255, null=True, blank=True)
    district_name = models.CharField(verbose_name="district name", max_length=255, null=True, blank=True)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=255, null=True, blank=True)
    # The offices' name as passed over by Google Civic. We save this, so we can match to this office even
    # if we edit the office's name locally.
    google_civic_office_held_name = models.CharField(max_length=255, null=True, blank=True)
    google_civic_office_held_name2 = models.CharField(max_length=255, null=True, blank=True)
    google_civic_office_held_name3 = models.CharField(max_length=255, null=True, blank=True)
    # As we add more years here, update /wevote_settings/constants.py IS_BATTLEGROUND_YEARS_AVAILABLE
    is_battleground_race_2019 = models.BooleanField(default=False, null=False)
    is_battleground_race_2020 = models.BooleanField(default=False, null=False)
    is_battleground_race_2021 = models.BooleanField(default=False, null=False)
    is_battleground_race_2022 = models.BooleanField(default=False, null=False)
    is_battleground_race_2023 = models.BooleanField(default=False, null=False)
    is_battleground_race_2024 = models.BooleanField(default=False, null=False)
    is_battleground_race_2025 = models.BooleanField(default=False, null=False)
    is_battleground_race_2026 = models.BooleanField(default=False, null=False)
    is_us_national_house = models.BooleanField(null=True)
    is_us_national_senate = models.BooleanField(null=True)
    # The number of candidates elected to office
    number_elected = models.CharField(max_length=255, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    ocd_id_state_mismatch_checked = models.BooleanField(default=False, null=False)
    ocd_id_state_mismatch_found = models.BooleanField(default=False, null=False)
    office_held_description = models.TextField(verbose_name="office_held description", null=True, blank=True)
    office_held_description_es = models.TextField(
        verbose_name="office_held description in Spanish", null=True, blank=True)
    office_held_facebook_url = models.TextField(blank=True, null=True)
    facebook_url_is_broken = models.BooleanField(default=False)
    # The levels of government of the office for this contest. There may be more than one in cases where a
    # jurisdiction effectively acts at two different levels of government; for example, the mayor of the
    # District of Columbia acts at "locality" level, but also effectively at both
    # "administrative-area-2" and "administrative-area-1".
    office_held_level0 = models.CharField(max_length=255, null=True, blank=True)
    office_held_level1 = models.CharField(max_length=255, null=True, blank=True)
    office_held_level2 = models.CharField(max_length=255, null=True, blank=True)
    # The name of the office held by a representative.
    office_held_name = models.CharField(
        verbose_name="name of the office held", max_length=255, null=False, blank=False)
    office_held_name_es = models.CharField(
        verbose_name="name of the office held in Spanish", max_length=255, null=True, blank=True, default=None)
    office_held_is_partisan = models.BooleanField(verbose_name="office_held is_partisan", default=False)
    office_held_role0 = models.CharField(max_length=255, null=True, blank=True)
    office_held_role1 = models.CharField(max_length=255, null=True, blank=True)
    office_held_role2 = models.CharField(max_length=255, null=True, blank=True)
    office_held_twitter_handle = models.CharField(max_length=255, null=True, unique=False)
    office_held_url = models.TextField(blank=True, null=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    race_office_level = models.CharField(max_length=255, null=True, blank=True)
    state_code = models.CharField(verbose_name="state this office_held serves", max_length=2, null=True, blank=True)

    # Which years do we have representative data? This is cached data built up from master
    #  data in the Representative.years_in_office_flags field
    # As we add more years here, update /wevote_settings/constants.py OFFICE_HELD_YEARS_AVAILABLE
    # As we add more years here, update attach_defaults_values_to_office_held_object
    year_with_data_2023 = models.BooleanField(default=None, null=True)
    year_with_data_2024 = models.BooleanField(default=None, null=True)
    year_with_data_2025 = models.BooleanField(default=None, null=True)
    year_with_data_2026 = models.BooleanField(default=None, null=True)

    def get_office_held_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            # Pull this from ocdDivisionId
            if positive_value_exists(self.ocd_division_id):
                ocd_division_id = self.ocd_division_id
                return extract_state_from_ocd_division_id(ocd_division_id)
            else:
                return ''

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_office_held_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "officeheld" = tells us this is a unique id for a OfficeHeld
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}officeheld{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(OfficeHeld, self).save(*args, **kwargs)


class OfficeHeldManager(models.Manager):

    @staticmethod
    def __unicode__():
        return "OfficeHeldManager"

    @staticmethod
    def retrieve_office_held_from_id(office_held_id):
        office_held_manager = OfficeHeldManager()
        return office_held_manager.retrieve_office_held(office_held_id)

    @staticmethod
    def retrieve_office_held_from_we_vote_id(office_held_we_vote_id):
        office_held_id = 0
        office_held_manager = OfficeHeldManager()
        return office_held_manager.retrieve_office_held(office_held_id, office_held_we_vote_id)

    @staticmethod
    def retrieve_office_held_from_maplight_id(maplight_id):
        office_held_id = 0
        office_held_we_vote_id = ''
        office_held_manager = OfficeHeldManager()
        return office_held_manager.retrieve_office_held(office_held_id, office_held_we_vote_id, maplight_id)

    @staticmethod
    def fetch_office_held_id_from_maplight_id(maplight_id):
        office_held_id = 0
        office_held_we_vote_id = ''
        office_held_manager = OfficeHeldManager()
        results = office_held_manager.retrieve_office_held(
            office_held_id, office_held_we_vote_id, maplight_id)
        if results['success']:
            return results['office_held_id']
        return 0

    @staticmethod
    def fetch_office_held_we_vote_id_from_id(office_held_id):
        maplight_id = 0
        office_held_we_vote_id = ''
        office_held_manager = OfficeHeldManager()
        results = office_held_manager.retrieve_office_held(
            office_held_id, office_held_we_vote_id, maplight_id)
        if results['success']:
            return results['office_held_we_vote_id']
        return 0

    def find_closest_offices_held_for_location(
            self,
            text_for_map_search='',
            google_civic_election_id=0,
            read_only=True):
        """
        We search for the closest address for this election in the OfficesHeldForLocation table.
        :param text_for_map_search:
        :param google_civic_election_id:
        :param read_only:
        :return:
        """
        offices_held_for_location_found = False
        offices_held_for_location = None
        location = None
        # try_without_maps_key = False
        status = ""
        state_code = ""

        if not positive_value_exists(text_for_map_search):
            status += "FIND_CLOSEST_OFFICES_HELD_FOR_LOCATION-NO_TEXT_FOR_MAP_SEARCH "
            return {
                'status': status,
                'geocoder_quota_exceeded': False,
                'offices_held_for_location_found': offices_held_for_location_found,
                'offices_held_for_location': offices_held_for_location,
            }

        if not hasattr(self, 'google_client') or not self.google_client:
            self.google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
        # Note April 2022:  If you get vague error messages from GeoPy that you can't figure out, it is easy to install
        # Google's google-maps-services-python and then do the same query and get better messages.  I guess we want to
        # keep using the GeoPy as a wrapper, in case some day we want to swap out google for geolocation, with a better
        # competitor.  (GeoPy doesn't have much value in our use case.)
        try:
            location = self.google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
        except GeocoderQuotaExceeded:
            # try_without_maps_key = True
            status += "GEOCODER_QUOTA_EXCEEDED "
        except Exception as e:
            try_without_maps_key = True
            status += 'GEOCODER_ERROR {error} [type: {error_type}] '.format(error=e, error_type=type(e))
            # logger.info(status + " @ " + text_for_map_search + "  google_civic_election_id=" +
            #             str(google_civic_election_id))

        # Since July 2018 Google requires each request to have an API key.
        # Pass a valid `api_key` to GoogleV3 geocoder to fix this error.
        # See https://developers.google.com/maps/documentation/geocoding/usage-and-billing
        # if try_without_maps_key:
        #     # If we have exceeded our account, try without a maps key
        #     try:
        #         temp_google_client = get_geocoder_for_service('google')()
        #         location = temp_google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
        #     except GeocoderQuotaExceeded:
        #         status += "GEOCODER_QUOTA_EXCEEDED "
        #         results = {
        #             'status':                   status,
        #             'geocoder_quota_exceeded':  True,
        #             'offices_held_for_location_found':    offices_held_for_location_found,
        #             'offices_held_for_location':          offices_held_for_location,
        #         }
        #         return results
        #     except Exception as e:
        #         status += "GEOCODER_ERROR: " + str(e) + ' '
        #         location = None

        offices_held_for_location = None
        if location is None:
            status += 'Geocoder could not find location matching "{}". Trying City, State. '.format(text_for_map_search)
            # If Geocoder is not able to give us a location, look to see if their voter entered their address as
            # "city_name, state_code" eg: "Sunnyvale, CA". If so, try to parse the entry and get ballot data
            # for that location
            if 'test' in sys.argv:
                queryset = OfficesHeldForLocation.objects.all()
            elif positive_value_exists(read_only):
                queryset = OfficesHeldForLocation.objects.using('readonly').all()
            else:
                queryset = OfficesHeldForLocation.objects.all()
            # Limit this query to entries stored for map points
            queryset = queryset.exclude(
                Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))

            if "," in text_for_map_search:
                address = text_for_map_search
                state_code = address.split(', ')[-1]
                state_code = state_code.upper()
                city = address.split(', ')[-2]
                city = city.lower()
                if positive_value_exists(state_code):
                    if positive_value_exists(state_code) and len(state_code) == 2:
                        queryset = queryset.filter(state_code__iexact=state_code)

            # if positive_value_exists(google_civic_election_id):
            #     queryset = queryset.filter(google_civic_election_id=google_civic_election_id)
            # else:
            #     # If we have an active election coming up, including today
            #     # fetch_next_upcoming_election_in_this_state returns next election with ballot items
            #     upcoming_google_civic_election_id = self.fetch_next_upcoming_election_in_this_state(state_code)
            #     if positive_value_exists(upcoming_google_civic_election_id):
            #         queryset = queryset.filter(
            #             google_civic_election_id=upcoming_google_civic_election_id)
            #     else:
            #         past_google_civic_election_id = self.fetch_last_election_in_this_state(state_code)
            #         if positive_value_exists(past_google_civic_election_id):
            #             # Limit the search to the most recent election with ballot items
            #             queryset = queryset.filter(
            #                 google_civic_election_id=past_google_civic_election_id)

            try:
                offices_held_for_location = queryset.first()
            except Exception as e:
                offices_held_for_location = None
                status += "OFFICES_HELD_FOR_LOCATION_QUERY_FIRST_FAILED_LOCATION_NONE: " + str(e) + ' '
            # offices_held_for_location_list = list(queryset)
            # if len(offices_held_for_location_list):
            #     offices_held_for_location = offices_held_for_location_list[0]
        else:
            # If here, then the geocoder successfully found the address
            status += 'GEOCODER_FOUND_LOCATION '
            address = location.address
            # address has format "line_1, state zip, USA"

            if 'test' in sys.argv:
                queryset = OfficesHeldForLocation.objects.all()
            elif positive_value_exists(read_only):
                queryset = OfficesHeldForLocation.objects.using('readonly').all()
            else:
                queryset = OfficesHeldForLocation.objects.all()
            # Limit this query to entries stored for map points
            queryset = queryset.exclude(
                Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
            if positive_value_exists(address) and "," in address:
                raw_state_code = address.split(', ')
                if positive_value_exists(raw_state_code):
                    state_code = raw_state_code[-2][:2]
            if positive_value_exists(state_code):
                # This search for normalized_state is NOT redundant because some elections are in many states
                queryset = queryset.filter(state_code__iexact=state_code)

            try:
                lat_rads_ploc = location.latitude * DEG_TO_RADS
                lon_rads_ploc = location.longitude * DEG_TO_RADS
                queryset = queryset.annotate(
                    # Calculate the approximate great circle distance between two coordinates
                    # https://medium.com/@petehouston/calculate-distance-of-two-locations-on-earth-using-python-1501b1944d97
                    distance=ExpressionWrapper(
                         (RADIUS_OF_EARTH_IN_MILES * (
                             ACos(
                                 (Sin(F('latitude') * DEG_TO_RADS) *
                                  Sin(lat_rads_ploc)) +
                                 (Cos(F('latitude') * DEG_TO_RADS) *
                                  Cos(lat_rads_ploc) *
                                  Cos((F('longitude') * DEG_TO_RADS) - lon_rads_ploc))
                             )
                           )),
                         output_field=FloatField()))
            except Exception as e:
                status += "EXCEPTION_IN_ANNOTATE_CALCULATION1-" + str(e) + ' '

            # Do not return ballots more than 25 miles away
            queryset = queryset.filter(distance__lte=DISTANCE_LIMIT_IN_MILES)

            queryset = queryset.order_by('distance')
            try:
                offices_held_for_location = queryset.first()
                if offices_held_for_location is None:
                    status += "OFFICES_HELD_FOR_LOCATION_QUERY_FIRST_FAILED-" \
                              "HAS_LOCATION_AND_POSITIVE_GOOGLE_CIVIC_ID__BALLOT_NONE "
                else:
                    status += "SUBSTITUTED_BALLOT_DISTANCE1: " + str(offices_held_for_location.distance) + " "
            except Exception as e:
                offices_held_for_location = None
                status += "OFFICES_HELD_FOR_LOCATION_QUERY_FIRST_FAILED_HAS_LOCATION_AND_POSITIVE_GOOGLE_CIVIC_ID: " + str(e) + ' '

        if offices_held_for_location is not None:
            offices_held_for_location_found = True
            status += 'OFFICES_HELD_FOR_LOCATION_FOUND '
        else:
            status += 'NO_STORED_BALLOT_MATCHES_STATE: {}. '.format(state_code)
            # Now Try the search again without the limitation of the state_code
            if location is not None:
                # If here, then the geocoder successfully found the address
                status += 'GEOCODER_FOUND_LOCATION-ATTEMPT2 '
                address = location.address
                # address has format "line_1, state zip, USA"

                if 'test' in sys.argv:
                    queryset = OfficesHeldForLocation.objects.all()
                elif positive_value_exists(read_only):
                    queryset = OfficesHeldForLocation.objects.using('readonly').all()
                else:
                    queryset = OfficesHeldForLocation.objects.all()
                # Limit this query to entries stored for map points
                queryset = queryset.exclude(
                    Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))

                # Calculate the approximate great circle distance between two coordinates
                # https://medium.com/@petehouston/calculate-distance-of-two-locations-on-earth-using-python-1501b1944d97
                try:
                    lat_rads_ploc = location.latitude * DEG_TO_RADS
                    lon_rads_ploc = location.longitude * DEG_TO_RADS
                    queryset = queryset.annotate(
                        distance=ExpressionWrapper(
                            (RADIUS_OF_EARTH_IN_MILES * (
                                ACos(
                                    (Sin(F('latitude') * DEG_TO_RADS) *
                                     Sin(lat_rads_ploc)) +
                                    (Cos(F('latitude') * DEG_TO_RADS) *
                                     Cos(lat_rads_ploc) *
                                     Cos((F('longitude') * DEG_TO_RADS) - lon_rads_ploc))
                                )
                            )),
                            output_field=FloatField()))
                except Exception as e:
                    status += "EXCEPTION_IN_ANNOTATE_CALCULATION2-" + str(e) + ' '

                # Do not return offices_held_for_locations more than 25 miles away
                queryset = queryset.filter(distance__lte=DISTANCE_LIMIT_IN_MILES)

                queryset = queryset.order_by('distance')

                # status += "SEARCHING_BY_GOOGLE_CIVIC_ID-ATTEMPT2 "
                # queryset = queryset.filter(
                #     google_civic_election_id=google_civic_election_id)
                try:
                    offices_held_for_location = queryset.first()
                    status += "SUBSTITUTED_BALLOT_DISTANCE4: " + str(offices_held_for_location.distance) + " "
                except Exception as e:
                    offices_held_for_location = None
                    status += "OFFICES_HELD_FOR_LOCATION_QUERY_FIRST_FAILED-" \
                              "HAS_BALLOT_LOCATION_AND_POSITIVE_GOOGLE_CIVIC_ID: " + str(e) + ' '
                # offices_held_for_location_list = list(queryset)
                # if len(offices_held_for_location_list):
                #     offices_held_for_location = offices_held_for_location_list[0]
                if offices_held_for_location is not None:
                    offices_held_for_location_found = True
                    status += 'OFFICES_HELD_FOR_LOCATION_FOUND-ATTEMPT2 '

        status += 'END_OF_FIND_CLOSEST_OFFICES_HELD_FOR_LOCATION '

        return {
            'status':                           status,
            'geocoder_quota_exceeded':          False,
            'offices_held_for_location_found':  offices_held_for_location_found,
            'offices_held_for_location':        offices_held_for_location,
        }

    @staticmethod
    def retrieve_office_held(
            google_civic_office_held_name='',
            maplight_id=None,
            ocd_division_id='',
            office_held_id=0,
            office_held_name='',
            office_held_we_vote_id='',
            read_only=False,
    ):
        office_held = None
        office_held_found = False
        office_held_list = []
        office_held_list_found = False
        status = ''
        success = True

        try:
            if positive_value_exists(office_held_id):
                if read_only:
                    office_held = OfficeHeld.objects.using('readonly').get(id=office_held_id)
                else:
                    office_held = OfficeHeld.objects.get(id=office_held_id)
                office_held_id = office_held.id
                office_held_found = True
                office_held_we_vote_id = office_held.we_vote_id
                status += "RETRIEVE_OFFICE_HELD_FOUND_BY_ID "
            elif positive_value_exists(office_held_we_vote_id):
                if read_only:
                    office_held = OfficeHeld.objects.using('readonly').get(we_vote_id=office_held_we_vote_id)
                else:
                    office_held = OfficeHeld.objects.get(we_vote_id=office_held_we_vote_id)
                office_held_id = office_held.id
                office_held_found = True
                office_held_we_vote_id = office_held.we_vote_id
                status += "RETRIEVE_OFFICE_HELD_FOUND_BY_WE_VOTE_ID "
            elif positive_value_exists(maplight_id):
                if read_only:
                    office_held = OfficeHeld.objects.using('readonly').get(maplight_id=maplight_id)
                else:
                    office_held = OfficeHeld.objects.get(maplight_id=maplight_id)
                office_held_id = office_held.id
                office_held_found = True
                office_held_we_vote_id = office_held.we_vote_id
                status += "RETRIEVE_OFFICE_HELD_FOUND_BY_MAPLIGHT_ID "
            elif positive_value_exists(ocd_division_id) and (
                    positive_value_exists(google_civic_office_held_name) or positive_value_exists(office_held_name)):
                if read_only:
                    queryset = OfficeHeld.objects.using('readonly').all()
                else:
                    queryset = OfficeHeld.objects.all()
                queryset = queryset.filter(ocd_division_id=ocd_division_id)
                if positive_value_exists(office_held_name):
                    queryset = queryset.filter(
                        Q(office_held_name=office_held_name) |
                        Q(google_civic_office_held_name=office_held_name) |
                        Q(google_civic_office_held_name2=office_held_name) |
                        Q(google_civic_office_held_name3=office_held_name)
                    )
                if positive_value_exists(google_civic_office_held_name):
                    queryset = queryset.filter(
                        Q(google_civic_office_held_name=google_civic_office_held_name) |
                        Q(google_civic_office_held_name2=google_civic_office_held_name) |
                        Q(google_civic_office_held_name3=google_civic_office_held_name)
                    )
                office_held_list = list(queryset)
                if len(office_held_list) > 0:
                    # At least one entry exists
                    if len(office_held_list) == 1:
                        office_held = office_held_list[0]
                        office_held_id = office_held.id
                        office_held_found = True
                        office_held_list_found = False
                        office_held_we_vote_id = office_held.we_vote_id
                        status += "OFFICE_HELD_FOUND "
                    else:
                        # more than one entry found
                        office_held_found = False
                        office_held_list_found = True
                        status += "MULTIPLE_OFFICE_HELD_MATCHES "
                else:
                    office_held_found = False
                    office_held_list_found = False
                    status += "OFFICE_HELD_NOT_FOUND "
            else:
                status += "RETRIEVE_OFFICE_HELD_SEARCH_INDEX_MISSING "
                success = False
        except OfficeHeld.DoesNotExist as e:
            status += "OFFICE_HELD_ROW_NOT_FOUND: " + str(e) + " "
            success = True
        except Exception as e:
            status += "FAILED_OFFICE_HELD_RETRIEVE: " + str(e) + " "
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'office_held':              office_held,
            'office_held_found':        office_held_found,
            'office_held_id':           convert_to_int(office_held_id),
            'office_held_list':         office_held_list,
            'office_held_list_found':   office_held_list_found,
            'office_held_we_vote_id':   office_held_we_vote_id,
        }
        return results

    @staticmethod
    def fetch_office_held_id_from_we_vote_id(office_held_we_vote_id):
        """
        Take in office_held_we_vote_id and return internal/local-to-this-database office_held_id
        :param office_held_we_vote_id:
        :return:
        """
        office_held_id = 0
        try:
            if positive_value_exists(office_held_we_vote_id):
                office_held = OfficeHeld.objects.get(we_vote_id=office_held_we_vote_id)
                office_held_id = office_held.id

        except OfficeHeld.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except OfficeHeld.DoesNotExist:
            office_held_id = 0

        return office_held_id

    @staticmethod
    def create_office_held_row_entry(
            office_held_name,
            defaults={}):
        """
        Create OfficeHeld table entry with OfficeHeld details 
        :param office_held_name: 
        :param defaults:
        :return:
        """
        success = False
        status = ""
        office_held_created = False
        office_held_found = False
        office_held_updated = False
        office_held = None

        try:
            office_held = OfficeHeld.objects.create(
                office_held_name=office_held_name)
            if office_held:
                status += "OFFICE_HELD_CREATED "
                office_held_created = True
                office_held_found = True
                office_held = attach_defaults_values_to_office_held_object(office_held, defaults)
                office_held.save()
                office_held_updated = True
                success = True
            else:
                success = False
                status += "OFFICE_HELD_CREATE_FAILED "
        except Exception as e:
            success = False
            office_held_created = False
            status += "OFFICE_HELD_CREATE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'office_held_created':      office_held_created,
                'office_held_found':        office_held_found,
                'office_held_updated':      office_held_updated,
                'office_held':              office_held,
            }
        return results

    @staticmethod
    def create_offices_held_for_location_row_entry(
            polling_location_we_vote_id=None,
            state_code=None,
            voter_we_vote_id=None,
            defaults={}):
        """
        Create OfficesHeldForLocation table entry with information about the OfficeHeld entries associated
        with one location.
        :param polling_location_we_vote_id:
        :param state_code:
        :param voter_we_vote_id:
        :param defaults:
        :return:
        """
        success = False
        status = ""
        offices_held_for_location_created = False
        offices_held_for_location_found = False
        offices_held_for_location_updated = False
        offices_held_for_location = None

        try:
            offices_held_for_location = OfficesHeldForLocation.objects.create(
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                voter_we_vote_id=voter_we_vote_id)
            if offices_held_for_location:
                status += "OFFICES_HELD_FOR_LOCATION_CREATED "
                offices_held_for_location_created = True
                offices_held_for_location_found = True
                offices_held_for_location = \
                    attach_defaults_values_to_offices_held_object(offices_held_for_location, defaults)
                offices_held_for_location.save()
                offices_held_for_location_updated = True
                success = True
            else:
                success = False
                status += "OFFICES_HELD_FOR_LOCATION_CREATE_FAILED "
        except Exception as e:
            success = False
            offices_held_for_location_created = False
            status += "OFFICES_HELD_FOR_LOCATION_CREATE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'offices_held_for_location_created':      offices_held_for_location_created,
                'offices_held_for_location_found':        offices_held_for_location_found,
                'offices_held_for_location_updated':      offices_held_for_location_updated,
                'offices_held_for_location':              offices_held_for_location,
            }
        return results

    @staticmethod
    def update_office_held_row_entry(
            office_held_we_vote_id='',
            defaults={}):
        """
            Update OfficeHeld table entry with matching we_vote_id 
        :param office_held_we_vote_id:
        :param defaults:
        :return: 
        """
        success = False
        status = ""
        office_held_found = False
        office_held_updated = False
        office_held = None

        try:
            office_held = OfficeHeld.objects.get(we_vote_id__iexact=office_held_we_vote_id)
            if office_held:
                office_held_found = True
                # found the existing entry, update the values
                office_held = attach_defaults_values_to_office_held_object(office_held, defaults)
                office_held.save()
                office_held_updated = True
                success = True
                status += "OFFICE_HELD_UPDATED "
        except Exception as e:
            success = False
            office_held_updated = False
            status += "OFFICE_HELD_RETRIEVE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':              success,
                'status':               status,
                'office_held':          office_held,
                'office_held_found':    office_held_found,
                'office_held_updated':  office_held_updated,
        }
        return results

    @staticmethod
    def update_offices_held_for_location_row_entry(
            offices_held_for_location=None,
            defaults={}):
        success = False
        status = ""
        offices_held_for_location_found = False
        offices_held_for_location_updated = False

        try:
            if offices_held_for_location and hasattr(offices_held_for_location, 'office_held_name_01'):
                offices_held_for_location_found = True
                # found the existing entry, update the values
                offices_held_for_location = \
                    attach_defaults_values_to_offices_held_object(offices_held_for_location, defaults)
                offices_held_for_location.save()
                offices_held_for_location_updated = True
                success = True
                status += "OFFICES_HELD_FOR_LOCATION_UPDATED "
        except Exception as e:
            success = False
            offices_held_for_location_updated = False
            status += "OFFICES_HELD_FOR_LOCATION_RETRIEVE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                              success,
                'status':                               status,
                'offices_held_for_location':            offices_held_for_location,
                'offices_held_for_location_found':      offices_held_for_location_found,
                'offices_held_for_location_updated':    offices_held_for_location_updated,
        }
        return results

    @staticmethod
    def retrieve_office_held_list(
            state_code="",
            office_held_we_vote_id_list=[],
            read_only=False):
        office_held_list = []
        office_held_list_found = False
        status = ""

        try:
            if positive_value_exists(read_only):
                queryset = OfficeHeld.objects.using('readonly').all()
            else:
                queryset = OfficeHeld.objects.all()
            if positive_value_exists(state_code):
                queryset = queryset.filter(state_code__iexact=state_code)
            if len(office_held_we_vote_id_list):
                queryset = queryset.filter(we_vote_id__in=office_held_we_vote_id_list)
            queryset = queryset.order_by("office_held_name")
            office_held_list = list(queryset)

            if len(office_held_list):
                office_held_list_found = True
                status += 'OFFICES_HELD_RETRIEVED '
                success = True
            else:
                status += 'NO_OFFICES_HELD_RETRIEVED '
                success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_office_held_list ' \
                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'office_held_list_found':   office_held_list_found,
            'office_held_list':         office_held_list,
            'state_code':               state_code,
            'status':                   status,
            'success':                  success,
        }
        return results

    @staticmethod
    def retrieve_offices_held_for_location(
            offices_held_for_location_id=0,
            polling_location_we_vote_id='',
            voter_we_vote_id='',
            read_only=False,
    ):
        offices_held_for_location = None
        offices_held_for_location_found = False
        status = ''
        success = True

        try:
            if positive_value_exists(offices_held_for_location_id):
                if read_only:
                    queryset = OfficesHeldForLocation.objects.using('readonly').all()
                else:
                    queryset = OfficesHeldForLocation.objects.all()
                queryset = queryset.filter(id=offices_held_for_location_id)
                queryset = queryset.order_by('-date_last_retrieved')
                offices_held_list = list(queryset[:1])
                if len(offices_held_list) == 1:
                    offices_held_for_location = offices_held_list[0]
                    offices_held_for_location_found = True
                status += "RETRIEVE_OFFICES_HELD_FOR_LOCATION_FOUND_BY_ID "
            elif positive_value_exists(polling_location_we_vote_id):
                if read_only:
                    queryset = OfficesHeldForLocation.objects.using('readonly').all()
                else:
                    queryset = OfficesHeldForLocation.objects.all()
                queryset = queryset.filter(polling_location_we_vote_id=polling_location_we_vote_id)
                queryset = queryset.order_by('-date_last_retrieved')
                offices_held_list = queryset[:1]
                if len(offices_held_list) == 1:
                    offices_held_for_location = offices_held_list[0]
                    offices_held_for_location_found = True
                status += "RETRIEVE_OFFICES_HELD_FOR_LOCATION_FOUND_BY_POLLING_LOCATION_WE_VOTE_ID "
            elif positive_value_exists(voter_we_vote_id):
                if read_only:
                    queryset = OfficesHeldForLocation.objects.using('readonly').all()
                else:
                    queryset = OfficesHeldForLocation.objects.all()
                queryset = queryset.filter(voter_we_vote_id=voter_we_vote_id)
                queryset = queryset.order_by('-date_last_retrieved')
                offices_held_list = queryset[:1]
                if len(offices_held_list) == 1:
                    offices_held_for_location = offices_held_list[0]
                    offices_held_for_location_found = True
                status += "RETRIEVE_OFFICES_HELD_FOR_LOCATION_FOUND_BY_VOTER_WE_VOTE_ID "
            else:
                status += "RETRIEVE_OFFICES_HELD_FOR_LOCATION_SEARCH_INDEX_MISSING "
                success = False
        except Exception as e:
            status += "FAILED_OFFICES_HELD_FOR_LOCATION_RETRIEVE: " + str(e) + " "
            success = False

        results = {
            'success':                          success,
            'status':                           status,
            'offices_held_for_location':        offices_held_for_location,
            'offices_held_for_location_found':  offices_held_for_location_found,
        }
        return results

    def retrieve_office_held_list_by_location(
            self,
            polling_location_we_vote_id='',
            voter_we_vote_id='',
            read_only=False,
    ):
        return self.retrieve_offices_held_for_location(
            polling_location_we_vote_id=polling_location_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=read_only,
        )

    @staticmethod
    def retrieve_possible_duplicate_offices_held(
            google_civic_election_id,
            office_held_name,
            state_code,
            we_vote_id_from_master=''):
        """
        Find entry that matches another entry in all critical fields other than we_vote_id_from_master
        :param google_civic_election_id:
        :param office_held_name:
        :param state_code:
        :param we_vote_id_from_master
        :return:
        """
        office_held_list_objects = []
        office_held_list_found = False
        status = ""

        try:
            queryset = OfficeHeld.objects.all()
            queryset = queryset.filter(google_civic_election_id=google_civic_election_id)
            queryset = queryset.filter(office_held_name__iexact=office_held_name)
            # Case doesn't matter
            if positive_value_exists(state_code):
                queryset = queryset.filter(state_code__iexact=state_code)
            # Case doesn't matter
            # queryset = queryset.filter(district_id__exact=district_id)
            # queryset = queryset.filter(district_name__iexact=district_name)
            #  Case doesn't matter

            # Ignore we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                queryset = queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            office_held_list_objects = queryset

            if len(office_held_list_objects):
                office_held_list_found = True
                status += 'OFFICES_HELD_RETRIEVED '
                success = True
            else:
                status += 'NO_OFFICES_HELD_RETRIEVED '
                success = True
        except OfficeHeld.DoesNotExist:
            # No offices found. Not a problem.
            status += 'NO_OFFICES_HELD_FOUND_DoesNotExist '
            office_held_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_possible_elected_duplicate_offices ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'office_list_found':        office_held_list_found,
            'office_list':              office_held_list_objects,
        }
        return results

    @staticmethod
    def update_or_create_office_held(
            office_held_we_vote_id,
            updated_values={}):
        """
        Either update or create an office_held entry.
        """
        exception_multiple_object_returned = False
        new_office_held_created = False
        office_held = None
        status = ""
        office_held_updated = False

        if not office_held_we_vote_id:
            success = False
            status += 'MISSING_OFFICE_HELD_WE_VOTE_ID '
        else:
            try:
                office_held, new_office_held_created = OfficeHeld.objects.update_or_create(
                    we_vote_id=office_held_we_vote_id,
                    defaults=updated_values)
                office_held_updated = not new_office_held_created
                success = True
                status += 'OFFICE_HELD_SAVED '
            except OfficeHeld.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_OFFICES_HELD_FOUND: ' + str(e) + ' '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_HELD_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'created':                  new_office_held_created,
            'office_held':              office_held,
            'saved':                    new_office_held_created or office_held_updated,
            'updated':                  office_held_updated,
            'not_processed':            True if not success else False,
        }
        return results

    @staticmethod
    def update_or_create_offices_held_for_location(
            polling_location_we_vote_id='',
            updated_values={}):
        """
        Either update or create an OfficesHeldForLocation entry.
        """
        exception_multiple_object_returned = False
        new_offices_held_for_location_created = False
        offices_held_for_location = None
        status = ""
        offices_held_for_location_updated = False

        if not polling_location_we_vote_id:
            success = False
            status += 'MISSING_POLLING_LOCATION_WE_VOTE_ID '
        else:
            try:
                offices_held_for_location, new_offices_held_for_location_created = \
                    OfficesHeldForLocation.objects.update_or_create(
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        defaults=updated_values)
                offices_held_for_location_updated = not new_offices_held_for_location_created
                success = True
                status += 'OFFICES_HELD_FOR_LOCATION_SAVED '
            except OfficesHeldForLocation.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_OFFICES_HELD_FOUND: ' + str(e) + ' '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'FAILED_TO_CREATE_OFFICES_HELD_FOR_LOCATION_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'created':                  new_offices_held_for_location_created,
            'offices_held_for_location':    offices_held_for_location,
            'saved':                    new_offices_held_for_location_created or offices_held_for_location_updated,
            'updated':                  offices_held_for_location_updated,
            'not_processed':            True if not success else False,
        }
        return results


class OfficesHeldForLocation(models.Model):
    date_last_retrieved = models.DateField(null=True, auto_now=False)
    date_last_updated = models.DateField(null=True, auto_now=True)
    latitude = models.FloatField(null=True, verbose_name='latitude returned from Google')
    longitude = models.FloatField(null=True, verbose_name='longitude returned from Google')
    office_held_name_01 = models.CharField(max_length=255, null=True)
    office_held_name_02 = models.CharField(max_length=255, null=True)
    office_held_name_03 = models.CharField(max_length=255, null=True)
    office_held_name_04 = models.CharField(max_length=255, null=True)
    office_held_name_05 = models.CharField(max_length=255, null=True)
    office_held_name_06 = models.CharField(max_length=255, null=True)
    office_held_name_07 = models.CharField(max_length=255, null=True)
    office_held_name_08 = models.CharField(max_length=255, null=True)
    office_held_name_09 = models.CharField(max_length=255, null=True)
    office_held_name_10 = models.CharField(max_length=255, null=True)
    office_held_name_11 = models.CharField(max_length=255, null=True)
    office_held_name_12 = models.CharField(max_length=255, null=True)
    office_held_name_13 = models.CharField(max_length=255, null=True)
    office_held_name_14 = models.CharField(max_length=255, null=True)
    office_held_name_15 = models.CharField(max_length=255, null=True)
    office_held_name_16 = models.CharField(max_length=255, null=True)
    office_held_name_17 = models.CharField(max_length=255, null=True)
    office_held_name_18 = models.CharField(max_length=255, null=True)
    office_held_name_19 = models.CharField(max_length=255, null=True)
    office_held_name_20 = models.CharField(max_length=255, null=True)
    office_held_name_21 = models.CharField(max_length=255, null=True)
    office_held_name_22 = models.CharField(max_length=255, null=True)
    office_held_name_23 = models.CharField(max_length=255, null=True)
    office_held_name_24 = models.CharField(max_length=255, null=True)
    office_held_name_25 = models.CharField(max_length=255, null=True)
    office_held_name_26 = models.CharField(max_length=255, null=True)
    office_held_name_27 = models.CharField(max_length=255, null=True)
    office_held_name_28 = models.CharField(max_length=255, null=True)
    office_held_name_29 = models.CharField(max_length=255, null=True)
    office_held_name_30 = models.CharField(max_length=255, null=True)
    office_held_we_vote_id_01 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_02 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_03 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_04 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_05 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_06 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_07 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_08 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_09 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_10 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_11 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_12 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_13 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_14 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_15 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_16 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_17 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_18 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_19 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_20 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_21 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_22 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_23 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_24 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_25 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_26 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_27 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_28 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_29 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    office_held_we_vote_id_30 = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)

    polling_location_we_vote_id = models.CharField(default=None, max_length=255, null=True, unique=False, db_index=True)
    state_code = models.CharField(max_length=2, null=True, db_index=True)
    voter_we_vote_id = models.CharField(default=None, max_length=255, null=True)
    # Which years do we have OfficesHeldForLocation data?
    # As we add more years here, update /wevote_settings/constants.py OFFICE_HELD_YEARS_AVAILABLE
    # As we add more years here, update attach_defaults_values_to_offices_held_object
    year_with_data_2023 = models.BooleanField(default=None, null=True)
    year_with_data_2024 = models.BooleanField(default=None, null=True)
    year_with_data_2025 = models.BooleanField(default=None, null=True)
    year_with_data_2026 = models.BooleanField(default=None, null=True)
