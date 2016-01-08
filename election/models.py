# election/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.models import extract_state_from_ocd_division_id


TIME_SPAN_LIST = [
    '2016',
    '2015',
    '2014-2015',
    '2014',
    '2013-2014',
    '2013',
    '2012',
]

logger = wevote_functions.admin.get_logger(__name__)


class Election(models.Model):
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=20, null=True, unique=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)  # Make unique=True after data is migrated
    # A displayable name for the election.
    election_name = models.CharField(verbose_name="election name", max_length=255, null=False, blank=False)
    # Day of the election in YYYY-MM-DD format.
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    # DALE 2015-05-01 The election type is currently in the contests, and not in the election
    # is_general_election = False  # Reset to false
    # is_primary_election = False  # Reset to false
    # is_runoff_election = False  # Reset to false
    # for case in switch(election_structured_data['type']):
    #     if case('Primary'):
    #         is_primary_election = True
    #         break
    #     if case('Run-off'):
    #         is_runoff_election = True
    #         break
    #     if case('General'): pass
    #     if case():  # default
    #         is_general_election = True

    def get_election_state(self):
        # Pull this from ocdDivisionId
        ocd_division_id = self.ocd_division_id
        return extract_state_from_ocd_division_id(ocd_division_id)


class ElectionManager(models.Model):

    def update_or_create_election(self, google_civic_election_id, election_name, election_day_text,
                                  ocd_division_id):
        """
        Either update or create an election entry.
        """
        exception_multiple_object_returned = False
        new_election_created = False

        if not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID'
        elif not election_name:
            success = False
            status = 'MISSING_ELECTION_NAME'
        else:
            try:
                updated_values = {
                    # Values we search against
                    'google_civic_election_id': google_civic_election_id,
                    # The rest of the values
                    'election_name': election_name,
                    'election_day_text': election_day_text,
                    'ocd_division_id': ocd_division_id,
                }
                election_on_stage, new_election_created = Election.objects.update_or_create(
                    google_civic_election_id=google_civic_election_id, defaults=updated_values)
                success = True
                status = 'ELECTION_SAVED'
            except Election.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_ELECTIONS_FOUND'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_election_created':     new_election_created,
        }
        return results
