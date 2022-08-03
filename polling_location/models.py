# polling_location/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from django.db import models
from django.db.models import Q
from exception.models import handle_record_not_found_exception
from geopy.geocoders import get_geocoder_for_service
from geopy.exc import GeocoderQuotaExceeded
import wevote_functions.admin
from wevote_functions.functions import extract_zip_formatted_from_zip9, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_polling_location_integer, fetch_site_unique_id_prefix

GEOCODE_TIMEOUT = 10
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR = 'ADDRESS_PARSE_ERROR'
KIND_OF_LOG_ENTRY_API_END_POINT_CRASH = 'API_END_POINT_CRASH'
KIND_OF_LOG_ENTRY_BALLOT_RECEIVED = 'BALLOT_RECEIVED'
KIND_OF_LOG_ENTRY_NO_CONTESTS = 'NO_CONTESTS'
KIND_OF_LOG_ENTRY_NO_BALLOT_JSON = 'NO_BALLOT_JSON'
MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK = 125  # 125. Formerly 250 and 111
MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_LARGE_STATE = 95
MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_EXTRA_LARGE_STATE = 51
NUMBER_OF_MAP_POINTS_THRESHOLD_FOR_LARGE_STATE = 9000
NUMBER_OF_MAP_POINTS_THRESHOLD_FOR_EXTRA_LARGE_STATE = 14000

logger = wevote_functions.admin.get_logger(__name__)


class PollingLocation(models.Model):
    """
    This is for storing map point information from the Voting Information Project Feeds
    """
    # We rely on the default internal id field too
    # The ID of this map point from VIP. (It seems to only be unique within each state.)
    polling_location_id = models.CharField(max_length=255, verbose_name="vip polling_location id", null=False)
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this map point", max_length=255, default=None, null=True,
        blank=True, unique=True, db_index=True)
    location_name = models.CharField(max_length=255, verbose_name="location name", null=True, blank=True)
    polling_hours_text = models.CharField(max_length=255, verbose_name="polling hours", null=True, blank=True)
    directions_text = models.TextField(
        verbose_name="directions to get to map point", null=True, blank=True)
    line1 = models.CharField(max_length=255, blank=True, null=True, verbose_name='address line 1 returned from VIP',
                             db_index=True)
    line2 = models.CharField(max_length=255, blank=True, null=True, verbose_name='address line 2 returned from VIP')
    city = models.CharField(max_length=255, blank=True, null=True, verbose_name='city returned from VIP',
                            db_index=True)
    state = models.CharField(max_length=255, blank=True, null=True, verbose_name='state returned from VIP',
                             db_index=True)
    zip_long = models.CharField(max_length=255, blank=True, null=True,
                                verbose_name='raw text zip returned from VIP, 9 characters', db_index=True)
    county_name = models.CharField(default=None, max_length=255, null=True)
    precinct_name = models.CharField(default=None, max_length=255, null=True)
    # We write latitude/longitude back to the PollingLocation table when we get it for the BallotReturned table
    latitude = models.FloatField(default=None, null=True)
    longitude = models.FloatField(default=None, null=True)

    ctcl_error_count = models.PositiveIntegerField(default=None, null=True)
    google_response_address_not_found = models.PositiveIntegerField(
        verbose_name="how many times Google can't find address", default=None, null=True)
    vote_usa_error_count = models.PositiveIntegerField(default=None, null=True)

    no_contests_count = models.PositiveIntegerField(default=None, null=True)
    # Where did we get this map point from?
    source_code = models.CharField(default=None, max_length=50, null=True)
    successful_retrieve_count = models.PositiveIntegerField(default=None, null=True)

    use_for_bulk_retrieve = models.BooleanField(verbose_name="this provides geographical coverage", default=False)
    polling_location_deleted = models.BooleanField(verbose_name="removed from usage", default=False)

    def get_formatted_zip(self):
        return extract_zip_formatted_from_zip9(self.zip_long)

    def get_text_for_map_search_results(self):
        text_for_map_search = ""
        if self.line1:
            text_for_map_search += self.line1.strip()
        if self.city:
            if len(text_for_map_search):
                text_for_map_search += ", "
            text_for_map_search += self.city.strip()
        if self.state:
            if len(text_for_map_search):
                text_for_map_search += ", "
            text_for_map_search += self.state
        if positive_value_exists(self.zip_long):
            if len(text_for_map_search):
                text_for_map_search += " "
            text_for_map_search += self.get_formatted_zip()
        # We have to return this as results (instead of a straight string) because python interprets it as a tuple
        # if there are commas in the string
        results = {
            'text_for_map_search':  text_for_map_search,
        }
        return results

    def get_text_for_map_search(self):
        results = self.get_text_for_map_search_results()
        return results['text_for_map_search']

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_polling_location_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "ploc" = tells us this is a unique id for a PollingLocation
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}ploc{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(PollingLocation, self).save(*args, **kwargs)


class PollingLocationLogEntry(models.Model):
    batch_process_id = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    date_time = models.DateTimeField(null=False, auto_now_add=True)
    google_civic_election_id = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    is_from_ballotpedia = models.BooleanField(default=False, null=True, db_index=True)  # Error from Ballotpedia
    is_from_ctcl = models.BooleanField(default=False, null=True, db_index=True)  # Error from retrieving data from CTCL
    is_from_vote_usa = models.BooleanField(default=False, null=True, db_index=True)  # Error retrieving from Vote USA
    kind_of_log_entry = models.CharField(max_length=50, default=None, null=True, db_index=True)
    log_entry_deleted = models.BooleanField(default=False, db_index=True)
    log_entry_message = models.TextField(null=True)
    polling_location_we_vote_id = models.CharField(max_length=255, null=True, unique=False, db_index=True)
    state_code = models.CharField(max_length=2, null=True, db_index=True)
    text_for_map_search = models.CharField(max_length=255, null=True, unique=False)
    voter_we_vote_id = models.CharField(max_length=255, null=True, unique=False, db_index=True)


class PollingLocationManager(models.Manager):

    def create_polling_location_log_entry(
            self,
            batch_process_id=None,
            google_civic_election_id=None,
            is_from_ballotpedia=None,
            is_from_ctcl=None,
            is_from_vote_usa=None,
            kind_of_log_entry=None,
            log_entry_message=None,
            polling_location_we_vote_id=None,
            state_code=None,
            text_for_map_search=None,
    ):
        """
        Create PollingLocationLogEntry data
        """
        success = True
        status = " "
        polling_location_log_entry_saved = False
        polling_location_log_entry = None
        missing_required_variable = False

        if not is_from_ballotpedia and not is_from_ctcl and not is_from_vote_usa:
            missing_required_variable = True
            status += 'MISSING_IS_FROM_SOURCE '
        if not kind_of_log_entry:
            missing_required_variable = True
            status += 'MISSING_KIND_OF_LOG_ENTRY '
        if not polling_location_we_vote_id:
            missing_required_variable = True
            status += 'MISSING_POLLING_LOCATION_WE_VOTE_ID '
        if not state_code:
            missing_required_variable = True
            status += 'MISSING_STATE_CODE '

        if missing_required_variable:
            results = {
                'success':                          success,
                'status':                           status,
                'polling_location_log_entry_saved': polling_location_log_entry_saved,
                'polling_location_log_entry':       polling_location_log_entry,
            }
            return results

        try:
            polling_location_log_entry = PollingLocationLogEntry.objects.using('analytics').create(
                batch_process_id=batch_process_id,
                google_civic_election_id=google_civic_election_id,
                is_from_ballotpedia=is_from_ballotpedia,
                is_from_ctcl=is_from_ctcl,
                is_from_vote_usa=is_from_vote_usa,
                kind_of_log_entry=kind_of_log_entry,
                log_entry_message=log_entry_message,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                text_for_map_search=text_for_map_search,
            )
            success = True
            polling_location_log_entry_saved = True
            status += 'POLLING_LOCATION_LOG_ENTRY_SAVED '
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_POLLING_LOCATION_LOG_ENTRY: ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'polling_location_log_entry_saved': polling_location_log_entry_saved,
            'polling_location_log_entry':       polling_location_log_entry,
        }
        return results

    def calculate_number_of_map_points_to_retrieve_with_each_batch_chunk(self, state_code):
        # For both REFRESH and RETRIEVE, see if the number of map points for this state exceed the "large" threshold
        retrieved_each_batch_chunk = MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK  # 125. Formerly 250 and 111
        if positive_value_exists(state_code):
            try:
                polling_location_query = PollingLocation.objects.using('readonly').all()
                polling_location_query = polling_location_query.filter(state__iexact=state_code)
                polling_location_query = polling_location_query.filter(polling_location_deleted=False)
                number_of_polling_locations = polling_location_query.count()
            except Exception as e:
                number_of_polling_locations = 0

            if number_of_polling_locations > NUMBER_OF_MAP_POINTS_THRESHOLD_FOR_EXTRA_LARGE_STATE:  # 14000
                retrieved_each_batch_chunk = MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_EXTRA_LARGE_STATE  # 51
            elif number_of_polling_locations > NUMBER_OF_MAP_POINTS_THRESHOLD_FOR_LARGE_STATE:  # 9000
                retrieved_each_batch_chunk = MAP_POINTS_RETRIEVED_EACH_BATCH_CHUNK_FOR_LARGE_STATE  # 95

        return retrieved_each_batch_chunk

    def fetch_polling_location_count(
            self,
            state_code=''):
        status = ''
        try:
            polling_location_queryset = PollingLocation.objects.using('readonly').all()
            polling_location_queryset = polling_location_queryset.exclude(polling_location_deleted=True)
            if positive_value_exists(state_code):
                polling_location_queryset = polling_location_queryset.filter(state__iexact=state_code)
            polling_location_count = polling_location_queryset.count()
        except Exception as e:
            status += 'FAILED fetch_polling_location_count: ' + str(e) + ' '
            polling_location_count = 0

        return polling_location_count

    def update_or_create_polling_location(
            self,
            we_vote_id,
            polling_location_id,
            location_name,
            polling_hours_text,
            directions_text,
            line1,
            line2,
            city,
            state,
            zip_long,
            county_name='',
            precinct_name='',
            latitude=None,
            longitude=None,
            source_code='',
            use_for_bulk_retrieve=False,
            polling_location_deleted=False):
        """
        Either update or create an polling_location entry.
        """
        exception_multiple_object_returned = False
        polling_location_created = False
        polling_location = None
        proceed_to_update_or_save = True
        success = False
        status = ''
        status += 'ENTERING update_or_create_polling_location '

        if positive_value_exists(we_vote_id):
            # If here we are dealing with an existing polling_location
            pass
        else:
            if latitude and longitude:
                status += 'INCOMING_LAT_LONG '
                proceed_to_update_or_save = True
            elif not line1:
                success = False
                status += 'MISSING_POLLING_LOCATION_LINE1 '
                proceed_to_update_or_save = False
            elif not city:
                success = False
                status += 'MISSING_POLLING_LOCATION_CITY '
                proceed_to_update_or_save = False
            elif not state:
                success = False
                status += 'MISSING_POLLING_LOCATION_STATE '
                proceed_to_update_or_save = False
            # Note: It turns out that some states, like Alaska, do not provide ZIP codes
            # elif not zip_long:
            #     success = False
            #     status = 'MISSING_POLLING_LOCATION_ZIP'

        if proceed_to_update_or_save:
            try:
                if positive_value_exists(we_vote_id):
                    updated_values = {
                        'we_vote_id': we_vote_id,
                        'county_name': county_name.strip() if county_name else '',
                        'polling_location_id': polling_location_id,
                        'state': state,
                        'location_name': location_name.strip() if location_name else '',
                        'polling_hours_text': polling_hours_text.strip() if polling_hours_text else '',
                        'precinct_name': precinct_name.strip() if precinct_name else '',
                        'directions_text': directions_text.strip() if directions_text else '',
                        'line1': line1.strip() if line1 else '',
                        'line2': line2,
                        'city': city.strip() if city else '',
                        'polling_location_deleted': polling_location_deleted,
                        'source_code': source_code.strip() if source_code else '',
                        'zip_long': zip_long,
                    }
                    if latitude is not None:
                        updated_values['latitude'] = latitude
                    if longitude is not None:
                        updated_values['longitude'] = longitude
                    if positive_value_exists(use_for_bulk_retrieve):
                        updated_values['use_for_bulk_retrieve'] = use_for_bulk_retrieve
                    polling_location, polling_location_created = PollingLocation.objects.update_or_create(
                        we_vote_id__iexact=we_vote_id, defaults=updated_values)
                else:
                    polling_location = PollingLocation.objects.create(
                        polling_location_id=polling_location_id,
                        county_name=county_name.strip() if county_name else '',
                        state=state,
                        location_name=location_name.strip() if location_name else '',
                        polling_hours_text=polling_hours_text.strip() if polling_hours_text else '',
                        precinct_name=precinct_name.strip() if precinct_name else '',
                        directions_text=directions_text.strip() if directions_text else '',
                        latitude=latitude if latitude else None,
                        longitude=longitude if longitude else None,
                        line1=line1.strip() if line1 else '',
                        line2=line2,
                        city=city.strip() if city else '',
                        polling_location_deleted=polling_location_deleted,
                        source_code=source_code,
                        use_for_bulk_retrieve=use_for_bulk_retrieve,
                        zip_long=zip_long,
                    )
                polling_location_created = True
                success = True
                status += 'POLLING_LOCATION_CREATED '
            except Exception as e:
                success = False
                status += 'POLLING_LOCATION_CREATED_EXCEPTION: ' + str(e) + ' '
                exception_multiple_object_returned = True

        results = {
            'success':                      success,
            'status':                       status,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'polling_location':             polling_location,
            'polling_location_created':     polling_location_created,
        }
        return results

    def update_polling_location_with_log_counts(
            self,
            is_from_ctcl=False,
            is_from_vote_usa=False,
            is_no_contests=False,
            is_successful_retrieve=False,
            polling_location_we_vote_id='',
            update_data_counts=False,
            update_error_counts=False):
        status = ''
        update_ctcl_error_count = False
        update_no_contests_count = False
        update_successful_retrieve_count = False
        update_vote_usa_error_count = False
        update_values = {}

        # ##############
        # Count errors which shouldn't be happening, and can be fixed:
        # KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR = 'ADDRESS_PARSE_ERROR'
        # KIND_OF_LOG_ENTRY_API_END_POINT_CRASH = 'API_END_POINT_CRASH'
        # KIND_OF_LOG_ENTRY_NO_BALLOT_JSON = 'NO_BALLOT_JSON'
        try:
            if positive_value_exists(update_error_counts):
                if not positive_value_exists(is_from_ctcl) and not positive_value_exists(is_from_vote_usa):
                    update_ctcl_error_count = True
                    update_vote_usa_error_count = True
                else:
                    update_ctcl_error_count = positive_value_exists(is_from_ctcl)
                    update_vote_usa_error_count = positive_value_exists(is_from_vote_usa)

            if positive_value_exists(update_ctcl_error_count):
                count_query = PollingLocationLogEntry.objects.using('analytics').all()
                count_query = count_query.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
                count_query = count_query.filter(is_from_ctcl=True)
                count_query = count_query.filter(kind_of_log_entry__in=[
                    KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR,
                    KIND_OF_LOG_ENTRY_API_END_POINT_CRASH,
                    KIND_OF_LOG_ENTRY_NO_BALLOT_JSON,
                ])
                count_query = count_query.filter(log_entry_deleted=False)
                update_values['ctcl_error_count'] = count_query.count()

            if positive_value_exists(update_vote_usa_error_count):
                count_query = PollingLocationLogEntry.objects.using('analytics').all()
                count_query = count_query.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
                count_query = count_query.filter(is_from_vote_usa=True)
                count_query = count_query.filter(kind_of_log_entry__in=[
                    KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR,
                    KIND_OF_LOG_ENTRY_API_END_POINT_CRASH,
                    KIND_OF_LOG_ENTRY_NO_BALLOT_JSON,
                ])
                count_query = count_query.filter(log_entry_deleted=False)
                update_values['vote_usa_error_count'] = count_query.count()
        except Exception as e:
            status += "FAILED_RETRIEVING_ERROR_COUNTS: " + str(e) + ' '
            results = {
                'success': False,
                'status': status,
            }
            return results

        try:
            if positive_value_exists(update_data_counts):
                if not positive_value_exists(is_no_contests) and not positive_value_exists(is_successful_retrieve):
                    update_no_contests_count = True
                    update_successful_retrieve_count = True
                else:
                    update_no_contests_count = positive_value_exists(is_no_contests)
                    update_successful_retrieve_count = positive_value_exists(is_successful_retrieve)

            if positive_value_exists(update_no_contests_count):
                count_query = PollingLocationLogEntry.objects.using('analytics').all()
                count_query = count_query.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
                count_query = count_query.filter(kind_of_log_entry__in=[
                    KIND_OF_LOG_ENTRY_NO_CONTESTS,
                ])
                count_query = count_query.filter(log_entry_deleted=False)
                update_values['no_contests_count'] = count_query.count()

            if positive_value_exists(update_successful_retrieve_count):
                count_query = PollingLocationLogEntry.objects.using('analytics').all()
                count_query = count_query.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
                count_query = count_query.filter(kind_of_log_entry__in=[
                    KIND_OF_LOG_ENTRY_BALLOT_RECEIVED,
                ])
                count_query = count_query.filter(log_entry_deleted=False)
                update_values['successful_retrieve_count'] = count_query.count()
        except Exception as e:
            status += "FAILED_RETRIEVING_DATA_COUNTS: " + str(e) + ' '
            results = {
                'success': False,
                'status': status,
            }
            return results

        update_results = self.update_polling_location_row(
            polling_location_we_vote_id=polling_location_we_vote_id,
            update_values=update_values,
        )
        status = update_results['status']
        success = update_results['success']

        results = {
            'success':          success,
            'status':           status,
        }
        return results

    def update_polling_location_row(
            self,
            polling_location_we_vote_id='',
            update_values={}):
        polling_location = None
        polling_location_found = False
        success = True
        status = ''
        try:
            polling_location = PollingLocation.objects.get(we_vote_id__iexact=polling_location_we_vote_id)
            polling_location_found = True
        except Exception as e:
            status += "POLLING_LOCATION_GET: " + str(e) + ' '

        if polling_location_found:
            try:
                for key, value in update_values.items():
                    setattr(polling_location, key, value)
                polling_location.save()
            except Exception as e:
                status += "POLLING_LOCATION_SAVE: " + str(e) + ' '
        results = {
            'status':   status,
            'success':  success,
        }
        return results

    def soft_delete_polling_location_log_entry_list(
            self,
            kind_of_log_entry_list=[],
            polling_location_we_vote_id=''):
        status = ''
        success = True
        number_deleted = 0
        try:
            query = PollingLocationLogEntry.objects.using('analytics').all()
            query = query.exclude(log_entry_deleted=True)
            if positive_value_exists(len(kind_of_log_entry_list) > 0):
                query = query.filter(kind_of_log_entry__in=kind_of_log_entry_list)
            query = query.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
            number_deleted = query.update(
                log_entry_deleted=True,
            )
        except Exception as e:
            status += "PollingLocationLogEntry_SOFT_DELETE_FAILED: " + str(e) + ' '
            handle_record_not_found_exception(e, logger=logger)
            success = False

        results = {
            'status':           status,
            'success':          success,
            'number_deleted':   number_deleted,
        }
        return results

    def populate_address_from_latitude_and_longitude_for_polling_location(self, polling_location):
        """
        We use the google geocoder in partnership with geoip
        :param polling_location:
        :return:
        """
        status = ""
        latitude = None
        longitude = None
        # We try to use existing google_client
        if not hasattr(self, 'google_client') or not self.google_client:
            self.google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)

        if not hasattr(polling_location, "line1"):
            results = {
                'status':                   "POPULATE_ADDRESS_FROM_LAT_AND_LONG-NOT_A_POLLING_LOCATION_OBJECT ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
            }
            return results

        if not polling_location.latitude or not \
                polling_location.longitude:
            # We require lat/long to use this function
            results = {
                'status':                   "POPULATE_ADDRESS_FROM_LAT_AND_LONG-MISSING_REQUIRED_INFO ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
            }
            return results

        lat_long_string = '{}, {}'.format(
            polling_location.latitude,
            polling_location.longitude)
        try:
            location_list = self.google_client.reverse(lat_long_string, sensor=False, timeout=GEOCODE_TIMEOUT)
        except GeocoderQuotaExceeded:
            status += "GeocoderQuotaExceeded "
            results = {
                'status':                   status,
                'geocoder_quota_exceeded':  True,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
            }
            return results
        except Exception as e:
            status += "Geocoder-Exception: " + str(e) + " "
            results = {
                'status':                   status,
                'geocoder_quota_exceeded':  False,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
            }
            return results

        if location_list is None:
            results = {
                'status':                   "POPULATE_LATITUDE_AND_LONGITUDE-LOCATION_NOT_RETURNED_FROM_GEOCODER ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
            }
            return results

        try:
            state_code_found = False
            street_number = ''
            route = ''
            for location in location_list:
                # Repair the map point to include the ZIP code
                if hasattr(location, 'raw'):
                    if 'address_components' in location.raw:
                        for one_address_component in location.raw['address_components']:
                            if 'street_number' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                street_number = one_address_component['long_name']
                            if 'route' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                route = one_address_component['long_name']
                            if 'locality' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                polling_location.city = one_address_component['long_name']
                            if 'administrative_area_level_1' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['short_name']):
                                polling_location.state = one_address_component['short_name']
                                state_code_found = True
                            if 'postal_code' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                polling_location.zip_long = one_address_component['long_name']
                        if positive_value_exists(street_number) and positive_value_exists(route):
                            polling_location.line1 = street_number + ' ' + route
                if state_code_found:
                    break
            polling_location.save()
            status += "POLLING_LOCATION_SAVED_WITH_NEW_ADDRESS "
            success = True
        except Exception as e:
            status += "POLLING_LOCATION_NOT_SAVED_WITH_NEW_ADDRESS " + str(e) + " "
            success = False

        results = {
            'status':                   status,
            'geocoder_quota_exceeded':  False,
            'success':                  success,
            'latitude':                 latitude,
            'longitude':                longitude,
        }
        return results

    def populate_latitude_and_longitude_for_polling_location(self, polling_location):
        """
        We use the google geocoder in partnership with geoip
        :param polling_location:
        :return:
        """
        status = ""
        latitude = None
        longitude = None
        # We try to use existing google_client
        if not hasattr(self, 'google_client') or not self.google_client:
            self.google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)

        if not hasattr(polling_location, "line1"):
            results = {
                'status':                   "POPULATE_LATITUDE_AND_LONGITUDE-NOT_A_POLLING_LOCATION_OBJECT ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
                'polling_location':         polling_location,
            }
            return results

        #  or not positive_value_exists(polling_location.zip_long)
        if not positive_value_exists(polling_location.line1) or not \
                positive_value_exists(polling_location.city) or not \
                positive_value_exists(polling_location.state):
            if positive_value_exists(polling_location.line1) and \
                    positive_value_exists(polling_location.city) and \
                    positive_value_exists(polling_location.state) and \
                    'ak' == polling_location.state.lower() and not \
                    positive_value_exists(polling_location.zip_long):
                # We do not need a ZIP code in Alaska
                pass
            else:
                # We require all four values
                results = {
                    'status':                   "POPULATE_LATITUDE_AND_LONGITUDE-MISSING_REQUIRED_ADDRESS_INFO ",
                    'geocoder_quota_exceeded':  False,
                    'success':                  False,
                    'latitude':                 latitude,
                    'longitude':                longitude,
                    'polling_location':         polling_location,
                }
                return results

        full_ballot_address = '{}, {}, {} {}'.format(
            polling_location.line1,
            polling_location.city,
            polling_location.state,
            polling_location.zip_long)
        try:
            location = self.google_client.geocode(full_ballot_address, sensor=False, timeout=GEOCODE_TIMEOUT)
        except GeocoderQuotaExceeded:
            status += "GeocoderQuotaExceeded "
            results = {
                'status':                   status,
                'geocoder_quota_exceeded':  True,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
                'polling_location':         polling_location,
            }
            return results
        except Exception as e:
            status += "Geocoder-Exception: " + str(e) + " "
            results = {
                'status':                   status,
                'geocoder_quota_exceeded':  False,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
                'polling_location':         polling_location,
            }
            return results

        if location is None:
            results = {
                'status':                   "POPULATE_LATITUDE_AND_LONGITUDE-LOCATION_NOT_RETURNED_FROM_GEOCODER ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
                'latitude':                 latitude,
                'longitude':                longitude,
                'polling_location':         polling_location,
            }
            return results

        try:
            latitude = location.latitude
            longitude = location.longitude
            if not positive_value_exists(polling_location.zip_long):
                # Repair the map point to include the ZIP code
                if hasattr(location, 'raw'):
                    if 'address_components' in location.raw:
                        for one_address_component in location.raw['address_components']:
                            if 'postal_code' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                polling_location.zip_long = one_address_component['long_name']
            polling_location.latitude = location.latitude
            polling_location.longitude = location.longitude
            polling_location.save()
            status += "POLLING_LOCATION_SAVED_WITH_LATITUDE_AND_LONGITUDE "
            success = True
        except Exception as e:
            status += "POLLING_LOCATION_NOT_SAVED_WITH_LATITUDE_AND_LONGITUDE " + str(e) + " "
            success = False

        results = {
            'status':                   status,
            'geocoder_quota_exceeded':  False,
            'success':                  success,
            'latitude':                 latitude,
            'longitude':                longitude,
            'polling_location':         polling_location,
        }
        return results

    def retrieve_address_from_latitude_and_longitude(self, latitude, longitude):
        status = ""
        city = ''
        line1 = ''
        route = ''
        state_code = ''
        street_number = ''
        zip_long = ''

        # We try to use existing google_client
        if not hasattr(self, 'google_client') or not self.google_client:
            self.google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)

        if not latitude or not longitude:
            # We require lat/long to use this function
            results = {
                'status': "POPULATE_ADDRESS_FROM_LAT_AND_LONG-MISSING_REQUIRED_INFO ",
                'geocoder_quota_exceeded': False,
                'success': False,
                'city': city,
                'latitude': latitude,
                'longitude': longitude,
                'line1': line1,
                'state_code': state_code,
                'zip_long': zip_long,
            }
            return results

        lat_long_string = '{}, {}'.format(
            latitude,
            longitude)
        try:
            location_list = self.google_client.reverse(lat_long_string, sensor=False, timeout=GEOCODE_TIMEOUT)
        except GeocoderQuotaExceeded:
            status += "GeocoderQuotaExceeded "
            results = {
                'status': status,
                'geocoder_quota_exceeded': True,
                'success': False,
                'city': city,
                'latitude': latitude,
                'longitude': longitude,
                'line1': line1,
                'state_code': state_code,
                'zip_long': zip_long,
            }
            return results
        except Exception as e:
            status += "Geocoder-Exception: " + str(e) + " "
            results = {
                'status': status,
                'geocoder_quota_exceeded': False,
                'success': False,
                'city': city,
                'latitude': latitude,
                'longitude': longitude,
                'line1': line1,
                'state_code': state_code,
                'zip_long': zip_long,
            }
            return results

        if location_list is None:
            results = {
                'status': "POPULATE_LATITUDE_AND_LONGITUDE-LOCATION_NOT_RETURNED_FROM_GEOCODER ",
                'geocoder_quota_exceeded': False,
                'success': False,
                'city': city,
                'latitude': latitude,
                'longitude': longitude,
                'line1': line1,
                'state_code': state_code,
                'zip_long': zip_long,
            }
            return results

        try:
            state_code_found = False
            for location in location_list:
                # Repair the map point to include the ZIP code
                if hasattr(location, 'raw'):
                    if 'address_components' in location.raw:
                        for one_address_component in location.raw['address_components']:
                            if 'street_number' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                street_number = one_address_component['long_name']
                            if 'route' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                route = one_address_component['long_name']
                            if 'locality' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                city = one_address_component['long_name']
                            if 'administrative_area_level_1' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['short_name']):
                                state_code = one_address_component['short_name']
                                state_code_found = True
                            if 'postal_code' in one_address_component['types'] \
                                    and positive_value_exists(one_address_component['long_name']):
                                zip_long = one_address_component['long_name']
                        if positive_value_exists(street_number) and positive_value_exists(route):
                            line1 = street_number + ' ' + route
                if state_code_found:
                    break
            status += "POLLING_LOCATION_SAVED_WITH_NEW_ADDRESS "
            success = True
        except Exception as e:
            status += "NEW_ADDRESS_ERROR " + str(e) + " "
            success = False

        results = {
            'status': status,
            'geocoder_quota_exceeded': False,
            'success': success,
            'city': city,
            'latitude': latitude,
            'longitude': longitude,
            'line1': line1,
            'state_code': state_code,
            'zip_long': zip_long,
        }
        return results

    def retrieve_polling_location_by_we_vote_id(self, polling_location_we_vote_id=''):
        return self.retrieve_polling_location_by_id(polling_location_we_vote_id=polling_location_we_vote_id)

    def retrieve_polling_location_by_id(self, polling_location_id=0, polling_location_we_vote_id=''):
        # Retrieve a polling_location entry
        polling_location = None
        status = ""
        try:
            if positive_value_exists(polling_location_id):
                polling_location = PollingLocation.objects.get(id=polling_location_id)
                polling_location_found = True if polling_location.id else False
            elif positive_value_exists(polling_location_we_vote_id):
                polling_location = PollingLocation.objects.get(we_vote_id__iexact=polling_location_we_vote_id)
                polling_location_found = True if polling_location.id else False
            else:
                polling_location_found = False
            success = True
        except PollingLocation.MultipleObjectsReturned as e:
            status += "RETRIEVE_POLLING_LOCATION-MultipleObjectsReturned: " + str(e) + " "
            success = False
            polling_location_found = False
        except PollingLocation.DoesNotExist:
            success = True
            polling_location_found = False
        except Exception as e:
            polling_location_found = False
            status += "RETRIEVE_POLLING_LOCATION-COULD_NOT_RETRIEVE: " + str(e) + " "
            success = False

        if polling_location_found:
            status += "POLLING_LOCATION_FOUND "
            results = {
                'status':                   status,
                'success':                  success,
                'polling_location_found':   polling_location_found,
                'polling_location':         polling_location,
            }
            return results
        else:
            status += "POLLING_LOCATION_NOT_FOUND "
            polling_location = None
            results = {
                'status':                  status,
                'success':                 success,
                'polling_location_found':  False,
                'polling_location':        polling_location,
            }
            return results

    def retrieve_polling_location_log_entry_list(
            self,
            batch_process_id=0,
            exclude_deleted=True,
            is_from_ctcl=False,
            is_from_vote_usa=False,
            is_no_contests=False,
            google_civic_election_id=False,
            is_successful_retrieve=False,
            kind_of_log_entry_list=[],
            polling_location_we_vote_id='',
            read_only=True,
            show_errors=False,
            state_code=False):
        if positive_value_exists(show_errors):
            kind_of_log_entry_list.append(KIND_OF_LOG_ENTRY_ADDRESS_PARSE_ERROR)
            kind_of_log_entry_list.append(KIND_OF_LOG_ENTRY_API_END_POINT_CRASH)
            kind_of_log_entry_list.append(KIND_OF_LOG_ENTRY_NO_BALLOT_JSON)
        if positive_value_exists(is_no_contests):
            kind_of_log_entry_list.append(KIND_OF_LOG_ENTRY_NO_CONTESTS)
        if positive_value_exists(is_successful_retrieve):
            kind_of_log_entry_list.append(KIND_OF_LOG_ENTRY_BALLOT_RECEIVED)

        polling_location_log_entry_list_found = False
        polling_location_log_entry_list = []
        try:
            # if positive_value_exists(read_only):
            #     query = PollingLocationLogEntry.objects.using('readonly').all()
            # else:
            #     query = PollingLocationLogEntry.objects.using('analytics').all()
            query = PollingLocationLogEntry.objects.using('analytics').all()
            if positive_value_exists(batch_process_id):
                query = query.filter(batch_process_id=batch_process_id)
            if positive_value_exists(google_civic_election_id):
                query = query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(exclude_deleted):
                query = query.exclude(log_entry_deleted=True)
            if positive_value_exists(is_from_ctcl) or positive_value_exists(is_from_vote_usa):
                filters = []
                if positive_value_exists(is_from_ctcl):
                    new_filter = Q(is_from_ctcl=True)
                    filters.append(new_filter)
                if positive_value_exists(is_from_vote_usa):
                    new_filter = Q(is_from_vote_usa=True)
                    filters.append(new_filter)
                # We need these as options with Q filters so they aren't excluded
                if positive_value_exists(is_no_contests):
                    new_filter = Q(kind_of_log_entry__in=[KIND_OF_LOG_ENTRY_NO_CONTESTS])
                    filters.append(new_filter)
                if positive_value_exists(is_successful_retrieve):
                    new_filter = Q(kind_of_log_entry__in=[KIND_OF_LOG_ENTRY_BALLOT_RECEIVED])
                    filters.append(new_filter)
                if len(filters):
                    final_filters = filters.pop()
                    for item in filters:
                        final_filters |= item
                    query = query.filter(final_filters)
            if positive_value_exists(len(kind_of_log_entry_list) > 0):
                query = query.filter(kind_of_log_entry__in=kind_of_log_entry_list)
            if positive_value_exists(polling_location_we_vote_id):
                query = query.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
            if positive_value_exists(state_code):
                query = query.filter(state_code__iexact=state_code)
            query = query.order_by('-id')
            polling_location_log_entry_list = list(query)
            if len(polling_location_log_entry_list):
                polling_location_log_entry_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if polling_location_log_entry_list_found:
            return polling_location_log_entry_list
        else:
            polling_location_log_entry_list = []
            return polling_location_log_entry_list

    def retrieve_polling_locations_in_city_or_state(self, state='', city='', polling_location_zip=''):
        # Retrieve a list of polling_location entries
        polling_location_list_found = False
        polling_location_list = []

        if not positive_value_exists(state) and not positive_value_exists(city) \
                and not positive_value_exists(polling_location_zip):
            results = {
                'status': "NO_CRITERIA_FOR_FINDING_POLLING_LOCATIONS-NONE_RETURNED",
                'success': True,
                'polling_location_list_found': False,
                'polling_location_list': [],
            }
            return results

        try:
            polling_location_query = PollingLocation.objects.all()
            polling_location_query = polling_location_query.exclude(polling_location_deleted=True)
            if positive_value_exists(state):
                polling_location_query = polling_location_query.filter(state__iexact=state)
            if positive_value_exists(city):
                polling_location_query = polling_location_query.filter(city__iexact=city)
            if positive_value_exists(polling_location_zip):
                polling_location_query = polling_location_query.filter(zip_long__icontains=polling_location_zip)
            polling_location_list = polling_location_query.order_by("city")

            if len(polling_location_list):
                polling_location_list_found = True
        except Exception as e:
            pass

        if polling_location_list_found:
            results = {
                'status':                       "POLLING_LOCATIONS_FOUND",
                'success':                      True,
                'polling_location_list_found':  True,
                'polling_location_list':        polling_location_list,
            }
            return results
        else:
            results = {
                'status':                       "POLLING_LOCATIONS_NOT_FOUND",
                'success':                      True,
                'polling_location_list_found':  False,
                'polling_location_list':        [],
            }
            return results

    def retrieve_duplicate_polling_locations(
            self,
            polling_location_id='',
            state='',
            location_name='',
            line1='',
            zip_long='',
            latitude=None,
            longitude=None,
            we_vote_id_from_master=''):
        """
        :param polling_location_id:
        :param state:
        :param location_name:
        :param line1:
        :param zip_long:
        :param we_vote_id_from_master:
        :param latitude:
        :param longitude:
        :return:
        """
        polling_location_list_objects = []
        polling_location_list_found = False
        status = ''

        # If we don't have the right variables required for the filters below, exit
        if not positive_value_exists(polling_location_id) \
                and not positive_value_exists(state) \
                and not positive_value_exists(line1) \
                and latitude is None \
                and longitude is None \
                and not positive_value_exists(zip_long):

            results = {
                'success':                      False,
                'status':                       "MISSING_REQUIRED_VARIABLES_TO_LOOK_FOR_POLLING_LOCATIONS_DUPLICATES",
                'polling_location_list_found':  polling_location_list_found,
                'polling_location_list':        polling_location_list_objects,
            }
            return results

        try:
            polling_location_queryset = PollingLocation.objects.all()

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                polling_location_queryset = polling_location_queryset.exclude(we_vote_id__iexact=we_vote_id_from_master)

            if positive_value_exists(polling_location_id):
                # This is not the built in id, but an external ID
                polling_location_queryset = polling_location_queryset.filter(polling_location_id=polling_location_id)
            if positive_value_exists(location_name):
                polling_location_queryset = polling_location_queryset.filter(location_name__iexact=location_name)
            if positive_value_exists(state):
                polling_location_queryset = polling_location_queryset.filter(state__iexact=state)
            if latitude is not None:
                latitude_float = float(latitude)
                polling_location_queryset = polling_location_queryset.filter(latitude=latitude_float)
            if longitude is not None:
                longitude_float = float(longitude)
                polling_location_queryset = polling_location_queryset.filter(longitude=longitude_float)
            if positive_value_exists(line1):
                polling_location_queryset = polling_location_queryset.filter(line1__iexact=line1)
            if positive_value_exists(zip_long):
                polling_location_queryset = polling_location_queryset.filter(zip_long__iexact=zip_long)

            polling_location_list_objects = list(polling_location_queryset)

            if len(polling_location_list_objects):
                polling_location_list_found = True
                status += 'DUPLICATE_POLLING_LOCATIONS_RETRIEVED '
                success = True
            else:
                status += 'NO_DUPLICATE_POLLING_LOCATIONS_RETRIEVED '
                success = True
        except PollingLocation.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_DUPLICATE_POLLING_LOCATIONS_FOUND_DoesNotExist '
            polling_location_list_objects = []
            success = True
        except Exception as e:
            status += 'RETRIEVE_DUPLICATE_POLLING_LOCATIONS_FAILED: ' + str(e) + ' '
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'polling_location_list_found':  polling_location_list_found,
            'polling_location_list':        polling_location_list_objects,
        }
        return results

    def retrieve_possible_duplicate_polling_locations(
            self,
            polling_location_id,
            state,
            location_name,
            line1,
            zip_long,
            we_vote_id_from_master=''):
        """
        Note that we bring in multiple polling_locations with the same street address line1 and zip.
         This is because the source data seems to have multiple entries per physical address, perhaps due to assigning
         the same physical address a new state-specific unique identifier and name from election-to-election?
        :param polling_location_id:
        :param state:
        :param location_name:
        :param line1:
        :param zip_long:
        :param we_vote_id_from_master:
        :return:
        """
        polling_location_list_objects = []
        filters = []
        polling_location_list_found = False
        status = ''

        # If we don't have the right variables required for the filters below, exit
        if not (positive_value_exists(polling_location_id) or positive_value_exists(location_name)) \
                and not positive_value_exists(state) \
                and not positive_value_exists(line1) \
                and not positive_value_exists(zip_long):

            results = {
                'success':                      False,
                'status':                       "MISSING_REQUIRED_VARIABLES_TO_LOOK_FOR_POLLING_LOCATIONS_DUPLICATES",
                'polling_location_list_found':  polling_location_list_found,
                'polling_location_list':        polling_location_list_objects,
            }
            return results

        try:
            polling_location_queryset = PollingLocation.objects.all()
            location_id_and_state_used = False
            location_name_and_state_used = False

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                polling_location_queryset = polling_location_queryset.filter(~Q(we_vote_id__iexact=
                                                                                we_vote_id_from_master))

            # We want to find candidates with *any* of these values
            if positive_value_exists(polling_location_id) and positive_value_exists(state):
                location_id_and_state_used = True
                new_filter = Q(polling_location_id__iexact=polling_location_id) & Q(state__iexact=state)
                filters.append(new_filter)

            if positive_value_exists(location_name) and positive_value_exists(state):
                location_name_and_state_used = True
                new_filter = Q(location_name__iexact=location_name) & Q(state__iexact=state)
                filters.append(new_filter)

            # 2016-05-17 This portion of the query restricts us from retrieving all map points from master.
            #  That is why we only using this filter when neither of the above filters are used
            if not positive_value_exists(location_id_and_state_used) and \
                    not positive_value_exists(location_name_and_state_used):
                if positive_value_exists(line1) and positive_value_exists(zip_long):
                    new_filter = Q(line1__iexact=line1) & Q(zip_long__iexact=zip_long)
                    filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                polling_location_queryset = polling_location_queryset.filter(final_filters)

            polling_location_list_objects = polling_location_queryset

            if len(polling_location_list_objects):
                polling_location_list_found = True
                status += 'DUPLICATE_POLLING_LOCATIONS_RETRIEVED '
                success = True
            else:
                status += 'NO_DUPLICATE_POLLING_LOCATIONS_RETRIEVED '
                success = True
        except PollingLocation.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_DUPLICATE_POLLING_LOCATIONS_FOUND_DoesNotExist '
            polling_location_list_objects = []
            success = True
        except Exception as e:
            status += 'FAILED retrieve_possible_duplicate_polling_locations ' + str(e) + ' '
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'polling_location_list_found':  polling_location_list_found,
            'polling_location_list':        polling_location_list_objects,
        }
        return results
