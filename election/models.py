# election/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class Election(models.Model):
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=20, null=True, unique=True)
    # A displayable name for the election.
    election_name = models.CharField(verbose_name="election name", max_length=254, null=False, blank=False)
    # Day of the election in YYYY-MM-DD format.
    election_date_text = models.CharField(verbose_name="election day", max_length=254, null=True, blank=True)
    raw_ocd_division_id = models.CharField(verbose_name="raw ocd division id", max_length=254, null=True, blank=True)


class ElectionManager(models.Model):

    def update_or_create_election(self, google_civic_election_id, election_name, election_date_text,
                                  raw_ocd_division_id):
        """
        Either update or create an election entry.
        """
        exception_multiple_object_returned = False
        new_election_created = False

        if not google_civic_election_id:
            success = False
            status = 'MISSING_ELECTION_ID'
        elif not election_name:
            success = False
            status = 'MISSING_ELECTION_NAME'
        else:
            try:
                updated_values = {
                    'election_name': election_name,
                    'election_date_text': election_date_text,
                    'raw_ocd_division_id': raw_ocd_division_id,
                }
                new_election_created = Election.objects.update_or_create(
                    google_civic_election_id=google_civic_election_id, defaults=updated_values)
                success = True
                status = 'ELECTION_SAVED'
            except Election.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_ADDRESSES_FOUND'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_election_created':     new_election_created,
        }
        return results
