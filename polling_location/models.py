# polling_location/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.functions import extract_zip_formatted_from_zip9


logger = wevote_functions.admin.get_logger(__name__)


class PollingLocation(models.Model):
    """
    This is for storing polling location information from the Voting Information Project Feeds
    """
    # We rely on the default internal id field too
    # The ID of this polling location from VIP. (It seems to only be unique within each state.)
    polling_location_id = models.CharField(max_length=255, verbose_name="vip polling_location id", null=False)
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


class PollingLocationManager(models.Model):

    def update_or_create_polling_location(self,
                                          polling_location_id, location_name, polling_hours_text, directions_text,
                                          line1, line2, city, state, zip_long):
        """
        Either update or create an polling_location entry.
        """
        exception_multiple_object_returned = False
        new_polling_location_created = False
        new_polling_location = PollingLocation()

        if not polling_location_id:
            success = False
            status = 'MISSING_POLLING_LOCATION_ID'
        elif not line1:
            success = False
            status = 'MISSING_POLLING_LOCATION_LINE1'
        elif not city:
            success = False
            status = 'MISSING_POLLING_LOCATION_CITY'
        elif not state:
            success = False
            status = 'MISSING_POLLING_LOCATION_STATE'
        # Note: It turns out that some states, like Alaska, do not provide ZIP codes
        # elif not zip_long:
        #     success = False
        #     status = 'MISSING_POLLING_LOCATION_ZIP'
        else:
            try:
                updated_values = {
                    # Values we search against
                    'polling_location_id': polling_location_id,
                    'state': state,
                    # The rest of the values
                    'location_name': location_name.strip(),
                    'polling_hours_text': polling_hours_text.strip(),
                    'directions_text': directions_text.strip(),
                    'line1': line1.strip(),
                    'line2': line2,
                    'city': city.strip(),
                    'zip_long': zip_long,
                }
                # We use polling_location_id + state to find prior entries since I am not sure polling_location_id's
                #  are unique from state-to-state
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
