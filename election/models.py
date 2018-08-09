# election/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import date, datetime, time
from django.db import models
from django.db.models import Max, Q
import wevote_functions.admin
from wevote_functions.functions import convert_date_to_date_as_integer, convert_date_to_we_vote_date_string, \
    convert_to_int, extract_state_from_ocd_division_id, positive_value_exists


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


class BallotpediaElection(models.Model):
    ballotpedia_election_id = models.PositiveIntegerField(
        verbose_name="ballotpedia election id", null=True, unique=True)
    # The ID of this election is linked to. (Provided by Google Civic or generated internally)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)
    # Called description by Ballotpedia
    election_description = models.CharField(verbose_name="election description", max_length=255, null=True)
    election_type = models.CharField(verbose_name="election type", max_length=255, null=True, blank=True)
    # Day of the election in YYYY-MM-DD format.
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    district_name = models.CharField(verbose_name="district name", max_length=255, null=True, blank=True)
    district_type = models.CharField(verbose_name="district type", max_length=255, null=True, blank=True)

    # The state code for the election
    state_code = models.CharField(verbose_name="state code for the election", max_length=2, null=True, blank=True)

    is_general_election = models.BooleanField(default=False)
    is_general_runoff_election = models.BooleanField(default=False)
    is_primary_election = models.BooleanField(default=False)
    is_primary_runoff_election = models.BooleanField(default=False)

    is_partisan = models.BooleanField(default=False)

    candidate_lists_complete = models.BooleanField(default=False)

    # For internal notes regarding gathering data for this election
    internal_notes = models.TextField(null=True, blank=True, default=None)

    def election_is_upcoming(self):
        if not positive_value_exists(self.election_day_text):
            return False
        today = datetime.now().date()
        today_date_as_integer = convert_date_to_date_as_integer(today)
        election_date_as_simple_string = self.election_day_text.replace("-", "")
        this_election_date_as_integer = convert_to_int(election_date_as_simple_string)
        if this_election_date_as_integer > today_date_as_integer:
            return True
        return False

    def get_election_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            # Pull this from ocdDivisionId
            if positive_value_exists(self.ocd_division_id):
                ocd_division_id = self.ocd_division_id
                return extract_state_from_ocd_division_id(ocd_division_id)
            else:
                return ''


class Election(models.Model):
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=20, null=True, unique=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)  # Make unique=True after data is migrated
    ballotpedia_election_id = models.PositiveIntegerField(
        verbose_name="ballotpedia election id", null=True, unique=True)
    # A displayable name for the election.
    election_name = models.CharField(verbose_name="election name", max_length=255, null=False, blank=False)
    # Day of the election in YYYY-MM-DD format.
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)

    ballotpedia_kind_of_election = models.CharField(
        verbose_name="election filter", max_length=255, null=True, blank=True)

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

    # The state code for the election. This is not directly provided from Google Civic, but useful when we are
    # entering elections manually.
    state_code = models.CharField(verbose_name="state code for the election", max_length=2, null=True, blank=True)
    include_in_list_for_voters = models.BooleanField(default=False)

    # For internal notes regarding gathering data for this election
    internal_notes = models.TextField(null=True, blank=True, default=None)

    # Not an election we will be supporting
    ignore_this_election = models.BooleanField(default=False)
    # Have we finished all of the election preparation related to Offices, Candidates, Measures and Ballot Locations?
    election_preparation_finished = models.BooleanField(default=False)
    # Have we finished all of the election preparation related to Candidate photos?
    candidate_photos_finished = models.BooleanField(default=False)

    # This is a multi-state election
    is_national_election = models.BooleanField(default=False)

    def election_is_upcoming(self):
        if not positive_value_exists(self.election_day_text):
            return False
        today = datetime.now().date()
        today_date_as_integer = convert_date_to_date_as_integer(today)
        election_date_as_simple_string = self.election_day_text.replace("-", "")
        this_election_date_as_integer = convert_to_int(election_date_as_simple_string)
        if this_election_date_as_integer > today_date_as_integer:
            return True
        return False

    def get_election_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            # Pull this from ocdDivisionId
            if positive_value_exists(self.ocd_division_id):
                ocd_division_id = self.ocd_division_id
                return extract_state_from_ocd_division_id(ocd_division_id)
            else:
                return ''


class ElectionManager(models.Model):

    def fetch_next_local_google_civic_election_id_integer(self):
        highest_id = 0
        election_query = Election.objects.all()
        election_query = election_query.order_by('-google_civic_election_id')
        election_list = list(election_query)
        for one_election in election_list:
            google_civic_election_id_integer = convert_to_int(one_election.google_civic_election_id)
            if google_civic_election_id_integer > highest_id:
                highest_id = google_civic_election_id_integer

        # Did not work with string
        # highest = Election.objects.all().aggregate(Max('google_civic_election_id'))['google_civic_election_id__max']

        last_integer = highest_id
        if last_integer >= 1000000:
            last_integer += 1
        else:
            last_integer = 1000000
        return last_integer

    def update_or_create_election(self, google_civic_election_id, election_name, election_day_text,
                                  ocd_division_id, state_code='', include_in_list_for_voters=None):
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
            if not positive_value_exists(state_code) and positive_value_exists(ocd_division_id):
                state_code = extract_state_from_ocd_division_id(ocd_division_id)

            try:
                updated_values = {
                    # Values we search against
                    'google_civic_election_id': google_civic_election_id,
                    # The rest of the values
                    'election_name':            election_name,
                    'election_day_text':        election_day_text,
                    'ocd_division_id':          ocd_division_id,
                    'state_code':               state_code,
                }
                election_on_stage, new_election_created = Election.objects.update_or_create(
                    google_civic_election_id=google_civic_election_id, defaults=updated_values)
                success = True
                status = 'ELECTION_SAVED'

                if include_in_list_for_voters is not None:
                    election_on_stage.include_in_list_for_voters = include_in_list_for_voters
                    election_on_stage.save()

            except Election.MultipleObjectsReturned as e:
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

    def retrieve_elections_by_date(self, newest_to_oldest=True, include_test_election=False):
        try:
            election_list_query = Election.objects.using('readonly').all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list_query = election_list_query.order_by('election_day_text')
            if newest_to_oldest:
                # Typically we want the newest election displayed first, with the older elections later in the list
                election_list_query = election_list_query.reverse()
            election_list = election_list_query
            status = 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    def retrieve_election(self, google_civic_election_id=0, election_id=0):
        google_civic_election_id = convert_to_int(google_civic_election_id)

        election = Election()
        try:
            if positive_value_exists(google_civic_election_id):
                election = Election.objects.get(google_civic_election_id=google_civic_election_id)
                if election.id:
                    election_found = True
                    status = "ELECTION_FOUND_WITH_GOOGLE_CIVIC_ELECTION_ID "
                else:
                    election_found = False
                    status = "ELECTION_NOT_FOUND_WITH_GOOGLE_CIVIC_ELECTION_ID "
                success = True
            elif positive_value_exists(election_id):
                election = Election.objects.get(id=election_id)
                if election.id:
                    election_found = True
                    status = "ELECTION_FOUND_WITH_ELECTION_ID "
                else:
                    election_found = False
                    status = "ELECTION_NOT_FOUND_WITH_ID "
                success = True
            else:
                election_found = False
                status = "Insufficient variables included to retrieve one election."
                success = False
        except Election.MultipleObjectsReturned as e:
            election_found = False
            status = "ERROR_MORE_THAN_ONE_ELECTION_FOUND"
            success = False
        except Election.DoesNotExist:
            election_found = False
            status = "ELECTION_NOT_FOUND"
            success = True

        results = {
            'success':                  success,
            'status':                   status,
            'election_found':           election_found,
            'google_civic_election_id': google_civic_election_id,
            'election':                 election,
        }
        return results

    def retrieve_listed_elections(self):
        """
        These are all of the elections marked as "listed" with "include_in_list_for_voters"
        :return:
        """
        election_list = []
        try:
            election_list_query = Election.objects.using('readonly').all()
            election_list_query = election_list_query.filter(include_in_list_for_voters=True)
            election_list_query = election_list_query.order_by('election_day_text').reverse()

            election_list = list(election_list_query)

            status = 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_ELECTIONS_FOUND'
            success = True

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    def retrieve_upcoming_elections(self, state_code="", without_state_code=False, include_test_election=False):
        election_list_found = False
        upcoming_election_list = []
        today = datetime.now().date()
        we_vote_date_string = convert_date_to_we_vote_date_string(today)
        try:
            election_list_query = Election.objects.using('readonly').all()
            election_list_query = election_list_query.filter(election_day_text__gte=we_vote_date_string)
            if positive_value_exists(without_state_code):
                election_list_query = election_list_query.filter(Q(state_code__isnull=True) | Q(state_code__exact=''))
            elif positive_value_exists(state_code):
                election_list_query = election_list_query.filter(state_code__iexact=state_code)
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list_query = election_list_query.order_by('election_day_text').reverse()

            upcoming_election_list = list(election_list_query)

            status = 'ELECTIONS_FOUND '
            election_list_found = True
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_ELECTIONS_FOUND '
            success = True
            election_list_found = False
        except Exception as e:
            status = "RETRIEVE_UPCOMING_ELECTIONS_QUERY_FAILURE "
            success = False

        results = {
            'success':          success,
            'status':           status,
            'election_list':    upcoming_election_list,
            'election_list_found': election_list_found,
        }
        return results

    def retrieve_next_election_for_state(self, state_code):
        """
        We want either the next election in this state, or the next national election, whichever comes first
        :param state_code:
        :return:
        """
        status = ""
        upcoming_state_elections_results = self.retrieve_upcoming_elections(state_code)
        election_list = upcoming_state_elections_results['election_list']
        if not len(election_list):
            status += upcoming_state_elections_results['status']
            without_state_code = True
            upcoming_national_elections_results = self.retrieve_upcoming_elections("", without_state_code)
            election_list = upcoming_national_elections_results['election_list']

            if not len(election_list):
                status += upcoming_national_elections_results['status']
                success = True
                status += "RETRIEVE_NEXT_ELECTION_FOR_STATE-NOT_FOUND: "
                results = {
                    'success':          success,
                    'status':           status,
                    'election_found':   False,
                    'election':         Election(),
                }
                return results

        success = True
        status += "RETRIEVE_NEXT_ELECTION_FOR_STATE-FOUND "
        election = election_list[0]
        results = {
            'success':          success,
            'status':           status,
            'election_found':   True,
            'election':         election,
        }
        return results

    def retrieve_next_national_election(self):
        """
        We want the next national election
        :return:
        """
        status = ""
        without_state_code = True
        upcoming_national_elections_results = self.retrieve_upcoming_elections("", without_state_code)
        election_list = upcoming_national_elections_results['election_list']

        if not len(election_list):
            status += upcoming_national_elections_results['status']
            success = True
            status += "RETRIEVE_NEXT_ELECTION_FOR_STATE-NOT_FOUND: "
            results = {
                'success':          success,
                'status':           status,
                'election_found':   False,
                'election':         Election(),
            }
            return results

        success = True
        status += "RETRIEVE_NEXT_ELECTION_FOR_STATE-FOUND "
        election = election_list[0]
        results = {
            'success':          success,
            'status':           status,
            'election_found':   True,
            'election':         election,
        }
        return results

    def retrieve_next_election_with_state_optional(self, state_code=""):
        """
        We want either the next election in this state, or the next national election, whichever comes first
        :param state_code:
        :return:
        """
        status = ""
        election_list = []
        if positive_value_exists(state_code):
            upcoming_state_elections_results = self.retrieve_upcoming_elections(state_code)
            election_list = upcoming_state_elections_results['election_list']
            status += upcoming_state_elections_results['status']
        if not len(election_list):
            without_state_code = True
            upcoming_national_elections_results = self.retrieve_upcoming_elections("", without_state_code)
            election_list = upcoming_national_elections_results['election_list']

            if not len(election_list):
                status += upcoming_national_elections_results['status']
                success = True
                status += "RETRIEVE_NEXT_ELECTION_WITH_STATE_OPTIONAL-NOT_FOUND: "
                results = {
                    'success':          success,
                    'status':           status,
                    'election_found':   False,
                    'election':         Election(),
                }
                return results

        success = True
        status += "RETRIEVE_NEXT_ELECTION_WITH_STATE_OPTIONAL-FOUND "
        election = election_list[0]
        results = {
            'success':          success,
            'status':           status,
            'election_found':   True,
            'election':         election,
        }
        return results

    def retrieve_we_vote_elections(self):
        """
        Only retrieve the elections we have entered without a Google Civic Election Id
        :return:
        """
        try:
            election_list_query = Election.objects.all()
            # We can't do this as long as google_civic_election_id is stored as a char
            # election_list_query = election_list_query.filter(google_civic_election_id__gte=1000000)

            # Find only the rows where google_civic_election_id is a string longer than 6 digits ("999999")
            election_list_query = election_list_query.extra(where=["CHAR_LENGTH(google_civic_election_id) > 6"])
            election_list_query = election_list_query.order_by('election_day_text').reverse()
            election_list = election_list_query
            status = 'WE_VOTE_ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_WE_VOTE_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    def retrieve_google_civic_elections_in_state_list(self, state_code_list):
        try:
            election_list_query = Election.objects.using('readonly').all()
            election_list_query = election_list_query.extra(where=["CHAR_LENGTH(google_civic_election_id) < 7"])
            election_list_query = election_list_query.exclude(google_civic_election_id=2000)

            q = Q()
            count = 0
            for state_code in state_code_list:
                q = q | Q(state_code__iexact=state_code)
                count += 1
            if positive_value_exists(count):
                election_list_query = election_list_query.filter(q)

            election_list_query = election_list_query.order_by('election_day_text').reverse()
            election_list = election_list_query
            status = 'WE_VOTE_ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_WE_VOTE_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    def retrieve_elections(self, include_test_election=False):
        """
        Retrieve all elections
        :param include_test_election:
        :return:
        """

        try:
            election_list_query = Election.objects.all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list_query = election_list_query.order_by('-election_day_text')
            election_list = election_list_query
            status = 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    def retrieve_elections_by_election_date(self, election_day_text='', include_test_election=False):
        """
        Retrieve elections using election_day_text
        :param election_day_text: 
        :param include_test_election: 
        :return: 
        """

        try:
            election_list_query = Election.objects.all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            if election_day_text:
                election_list_query = election_list_query.filter(election_day_text=election_day_text)
            election_list_query = election_list_query.order_by('election_day_text')
            election_list = election_list_query
            status = 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    def retrieve_elections_by_state_and_election_date(self, state_code='', election_day_text='',
                                                      include_test_election=False):
        """
          Retrieve elections using state_code and election_day_text
        :param state_code:
        :param election_day_text: 
        :param include_test_election: 
        :return: 
        """

        try:
            election_list_query = Election.objects.all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)

            if state_code and election_day_text:
                election_list_query = election_list_query.filter(state_code__iexact=state_code,
                                                                 election_day_text=election_day_text)
            election_list_query = election_list_query.order_by('election_day_text')
            election_list = election_list_query
            status = 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status = 'NO_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success': success,
            'status': status,
            'election_list': election_list,
        }
        return results


def fetch_election_state(google_civic_election_id):
    google_civic_election_id = convert_to_int(google_civic_election_id)

    election_manager = ElectionManager()
    results = election_manager.retrieve_election(google_civic_election_id)
    if results['election_found']:
        election = results['election']
        return election.get_election_state()
    else:
        return ''


def fetch_next_election_for_state(state_code):
    """
    Before using election returned, check for google_civic_election_id
    :param state_code:
    :return:
    """
    election_manager = ElectionManager()
    results = election_manager.retrieve_next_election_for_state(state_code)
    if results['election_found']:
        election = results['election']
        return election
    else:
        return Election()
