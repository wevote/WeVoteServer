# polling_location/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.functions import extract_zip_formatted_from_zip9, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_polling_location_integer, fetch_site_unique_id_prefix


logger = wevote_functions.admin.get_logger(__name__)


class PollingLocation(models.Model):
    """
    This is for storing polling location information from the Voting Information Project Feeds
    """
    # We rely on the default internal id field too
    # The ID of this polling location from VIP. (It seems to only be unique within each state.)
    polling_location_id = models.CharField(max_length=255, verbose_name="vip polling_location id", null=False)
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this polling location", max_length=255, default=None, null=True,
        blank=True, unique=True)
    location_name = models.CharField(max_length=255, verbose_name="location name", null=True, blank=True)
    polling_hours_text = models.CharField(max_length=255, verbose_name="polling hours", null=True, blank=True)
    directions_text = models.TextField(
        verbose_name="directions to get to polling location", null=True, blank=True)
    line1 = models.CharField(max_length=255, blank=True, null=True, verbose_name='address line 1 returned from VIP')
    line2 = models.CharField(max_length=255, blank=True, null=True, verbose_name='address line 2 returned from VIP')
    city = models.CharField(max_length=255, blank=True, null=True, verbose_name='city returned from VIP')
    state = models.CharField(max_length=255, blank=True, null=True, verbose_name='state returned from VIP')
    zip_long = models.CharField(max_length=255, blank=True, null=True,
                                verbose_name='raw text zip returned from VIP, 9 characters')
    # We write latitude/longitude back to the PollingLocation table when we get it for the BallotReturned table
    latitude = models.FloatField(null=True, verbose_name='latitude returned from Google')
    longitude = models.FloatField(null=True, verbose_name='longitude returned from Google')

    def get_formatted_zip(self):
        return extract_zip_formatted_from_zip9(self.zip_long)

    def get_text_for_map_search(self):
        text_for_map_search = ''
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
        if self.zip_long:
            if len(text_for_map_search):
                text_for_map_search += " "
            text_for_map_search += self.get_formatted_zip()
        return text_for_map_search

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_polling_location_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "ploc" = tells us this is a unique id for a PollingLocation
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}ploc{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(PollingLocation, self).save(*args, **kwargs)


class PollingLocationManager(models.Model):

    def update_or_create_polling_location(self, we_vote_id,
                                          polling_location_id, location_name, polling_hours_text, directions_text,
                                          line1, line2, city, state, zip_long, latitude='', longitude=''):
        """
        Either update or create an polling_location entry.
        """
        exception_multiple_object_returned = False
        new_polling_location_created = False
        new_polling_location = PollingLocation()
        proceed_to_update_or_save = True
        success = False
        status = 'ENTERING update_or_create_polling_location'

        if positive_value_exists(we_vote_id):
            # If here we are dealing with an existing polling_location
            pass
        else:
            if not polling_location_id:
                success = False
                status = 'MISSING_POLLING_LOCATION_ID'
                proceed_to_update_or_save = False
            elif not line1:
                success = False
                status = 'MISSING_POLLING_LOCATION_LINE1'
                proceed_to_update_or_save = False
            elif not city:
                success = False
                status = 'MISSING_POLLING_LOCATION_CITY'
                proceed_to_update_or_save = False
            elif not state:
                success = False
                status = 'MISSING_POLLING_LOCATION_STATE'
                proceed_to_update_or_save = False
            # Note: It turns out that some states, like Alaska, do not provide ZIP codes
            # elif not zip_long:
            #     success = False
            #     status = 'MISSING_POLLING_LOCATION_ZIP'

        if proceed_to_update_or_save:
            try:
                if positive_value_exists(we_vote_id):
                    updated_values = {
                        # Values we search against
                        # No need to include we_vote_id here
                        # The rest of the values
                        'polling_location_id': polling_location_id,
                        'state': state,
                        'location_name': location_name.strip() if location_name else '',
                        'polling_hours_text': polling_hours_text.strip() if polling_hours_text else '',
                        'directions_text': directions_text.strip() if directions_text else '',
                        'line1': line1.strip() if line1 else '',
                        'line2': line2,
                        'city': city.strip() if city else '',
                        'zip_long': zip_long,
                    }
                    if positive_value_exists(latitude):
                        updated_values['latitude'] = latitude
                    if positive_value_exists(longitude):
                        updated_values['longitude'] = longitude
                    new_polling_location, new_polling_location_created = PollingLocation.objects.update_or_create(
                        we_vote_id__iexact=we_vote_id, defaults=updated_values)
                else:
                    updated_values = {
                        # Values we search against
                        'polling_location_id': polling_location_id,
                        'state': state,
                        # The rest of the values
                        'location_name': location_name.strip() if location_name else '',
                        'polling_hours_text': polling_hours_text.strip() if polling_hours_text else '',
                        'directions_text': directions_text.strip() if directions_text else '',
                        'line1': line1.strip() if line1 else '',
                        'line2': line2,
                        'city': city.strip() if city else '',
                        'zip_long': zip_long,
                    }
                    # We use polling_location_id + state to find prior entries since I am not sure polling_location_id's
                    #  are unique from state-to-state
                    if positive_value_exists(latitude):
                        updated_values['latitude'] = latitude
                    if positive_value_exists(longitude):
                        updated_values['longitude'] = longitude
                    new_polling_location, new_polling_location_created = PollingLocation.objects.update_or_create(
                        polling_location_id__exact=polling_location_id, state=state, defaults=updated_values)
                success = True
                status = 'POLLING_LOCATION_SAVED'
            except PollingLocation.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_ADDRESSES_FOUND'
                exception_multiple_object_returned = True

        results = {
            'success':                      success,
            'status':                       status,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'new_polling_location':         new_polling_location,
            'new_polling_location_created': new_polling_location_created,
        }
        return results

    def retrieve_polling_location_by_id(self, polling_location_id=0, polling_location_we_vote_id=''):
        # Retrieve a polling_location entry
        try:
            if positive_value_exists(polling_location_id):
                polling_location = PollingLocation.objects.get(id=polling_location_id)
                polling_location_found = True if polling_location.id else False
            elif positive_value_exists(polling_location_we_vote_id):
                polling_location = PollingLocation.objects.get(we_vote_id=polling_location_we_vote_id)
                polling_location_found = True if polling_location.id else False
            else:
                polling_location_found = False
        except PollingLocation.MultipleObjectsReturned as e:
            success = False
            polling_location_found = False
        except PollingLocation.DoesNotExist:
            success = True
            polling_location_found = False
        except Exception as e:
            polling_location_found = False
            pass

        if polling_location_found:
            results = {
                'status':                   "POLLING_LOCATION_FOUND",
                'success':                  True,
                'polling_location_found':   polling_location_found,
                'polling_location':         polling_location,
            }
            return results
        else:
            polling_location = PollingLocation()
            results = {
                'status':                  "POLLING_LOCATION_NOT_FOUND",
                'success':                 True,
                'polling_location_found':  False,
                'polling_location':        polling_location,
            }
            return results

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
            polling_location_list = PollingLocation.objects.all()
            if positive_value_exists(state):
                polling_location_list = polling_location_list.filter(state__iexact=state)
            if positive_value_exists(city):
                polling_location_list = polling_location_list.filter(city__iexact=city)
            if positive_value_exists(polling_location_zip):
                polling_location_list = polling_location_list.filter(zip_long__icontains=polling_location_zip)
            polling_location_list = polling_location_list.order_by("city")

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


class PollingLocationListManager(models.Model):

    def retrieve_possible_duplicate_polling_locations(self, polling_location_id, state, location_name, line1, zip_long,
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

            # 2016-05-17 This portion of the query restricts us from retrieving all polling locations from master.
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
                status = 'DUPLICATE_POLLING_LOCATIONS_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_POLLING_LOCATIONS_RETRIEVED'
                success = True
        except PollingLocation.DoesNotExist:
            # No candidates found. Not a problem.
            status = 'NO_DUPLICATE_POLLING_LOCATIONS_FOUND_DoesNotExist'
            polling_location_list_objects = []
            success = True
        except Exception as e:
            status = 'FAILED retrieve_possible_duplicate_polling_locations ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'polling_location_list_found':  polling_location_list_found,
            'polling_location_list':        polling_location_list_objects,
        }
        return results

