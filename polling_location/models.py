# polling_location/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class PollingLocation(models.Model):
    """
    This is for storing polling location information from the Voting Information Project Feeds
    """
    # We rely on the default internal id field too
    # The unique ID of this election from VIP. (It may not in fact be unique -- TBD.)
    polling_location_id = models.CharField(max_length=254, verbose_name="vip polling_location id", null=False,
                                           unique=True)
    location_name = models.CharField(max_length=254, verbose_name="location name", null=True, blank=True)
    polling_hours_text = models.CharField(max_length=254, verbose_name="polling hours", null=True, blank=True)
    line1 = models.CharField(max_length=254, blank=True, null=True, verbose_name='address line 1 returned from VIP')
    line2 = models.CharField(max_length=254, blank=True, null=True, verbose_name='address line 2 returned from VIP')
    city = models.CharField(max_length=254, blank=True, null=True, verbose_name='city returned from VIP')
    state = models.CharField(max_length=254, blank=True, null=True, verbose_name='state returned from VIP')
    zip_long = models.CharField(max_length=254, blank=True, null=True,
                                verbose_name='raw text zip returned from VIP, 9 characters')


class PollingLocationManager(models.Model):

    def update_or_create_polling_location(self,
                                          polling_location_id, location_name, polling_hours_text, line1, line2, city,
                                          state, zip_long):
        """
        Either update or create an polling_location entry.
        """
        exception_multiple_object_returned = False
        new_polling_location_created = False

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
        elif not zip_long:
            success = False
            status = 'MISSING_POLLING_LOCATION_ZIP'
        else:
            try:
                updated_values = {
                    'location_name': location_name,
                    'polling_hours_text': polling_hours_text,
                    'line1': line1,
                    'line2': line2,
                    'city': city,
                    'state': state,
                    'zip_long': zip_long,
                }
                # We use polling_location_id + state to find prior entries since I am not sure polling_location_id's
                #  are unique from state-to-state
                new_polling_location, new_polling_location_created = PollingLocation.objects.update_or_create(
                    polling_location_id=polling_location_id, state=state, defaults=updated_values)
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
