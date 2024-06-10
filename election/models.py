# election/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime

from django.db import models
from django.db.models import Q

import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists
from wevote_functions.functions_date import convert_date_as_integer_to_date, convert_date_to_date_as_integer, \
    convert_date_to_we_vote_date_string

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
    objects = None
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=20, null=True, unique=True, db_index=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)  # Make unique=True after data is migrated
    ballotpedia_election_id = models.PositiveIntegerField(
        verbose_name="ballotpedia election id", null=True, unique=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=36, null=True, blank=True)
    ctcl_uuid2 = models.CharField(max_length=36, null=True, blank=True)
    ctcl_uuid3 = models.CharField(max_length=36, null=True, blank=True)
    # A displayable name for the election.
    election_name = models.CharField(verbose_name="election name", max_length=255, null=False, blank=False)
    # Day of the election in YYYY-MM-DD format.
    election_day_text = models.CharField(verbose_name="election day",
                                         max_length=255, null=True, blank=True, db_index=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)

    ballotpedia_kind_of_election = models.CharField(
        verbose_name="election filter", max_length=255, null=True, blank=True)
    # The state code for the election. This is not directly provided from Google Civic, but useful when we are
    # entering elections manually.
    state_code = models.CharField(verbose_name="state code for the election",
                                  max_length=2, null=True, blank=True, db_index=True)
    # We generate a string with all the state codes. Ex/ CA,CO,UT
    state_code_list_raw = models.CharField(max_length=255, null=True, blank=True)
    include_in_list_for_voters = models.BooleanField(default=False, db_index=True)

    # For internal notes regarding gathering data for this election
    internal_notes = models.TextField(null=True, blank=True, default=None)

    # Not an election we will be supporting
    ignore_this_election = models.BooleanField(default=False, db_index=True)
    # Have we finished all the election preparation related to Offices, Candidates, Measures and Ballot Locations?
    election_preparation_finished = models.BooleanField(default=False)
    # Have we finished all the election preparation related to Candidate photos?
    candidate_photos_finished = models.BooleanField(default=False)

    # This is a multi-state election
    is_national_election = models.BooleanField(default=False)

    use_ballotpedia_as_data_source = models.BooleanField(default=False)
    use_ctcl_as_data_source = models.BooleanField(default=False)
    # We can override another default data_source state-by-state by adding state_code
    use_ctcl_as_data_source_by_state_code = models.CharField(max_length=255, null=True, blank=True)
    use_google_civic_as_data_source = models.BooleanField(default=False)
    use_vote_usa_as_data_source = models.BooleanField(default=False)
    vote_usa_election_id = models.CharField(max_length=255, null=True)
    # Vote USA election ids like this -- we collapse into one election, and put PD, PR, SA into suffix_list:
    #  * GA20220524PD (Democratic Party Primary)
    #  * GA20220524PR (Republican Party Primary)
    #  * GA20220524SA (Special General)
    vote_usa_same_day_election_suffix_list = models.CharField(max_length=255, null=True)

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

    def state_code_list(self):
        if not positive_value_exists(self.state_code_list_raw):
            return []
        else:
            try:
                return self.state_code_list_raw.split(",")
            except Exception as e:
                return []


class ElectionManager(models.Manager):

    @staticmethod
    def fetch_next_local_google_civic_election_id_integer():
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

    @staticmethod
    def fetch_google_civic_election_id_from_list(google_civic_election_id_list):
        try:
            election_query = Election.objects.all()
            election_query = election_query.order_by('election_day_text')
            election_query = election_query.filter(google_civic_election_id__in=google_civic_election_id_list)
            election = election_query[:1]
            return election.google_civic_election_id
        except Exception as e:
            pass
        return 0

    def update_or_create_election(
            self,
            google_civic_election_id=None,
            election_name='',
            election_day_text='',
            ocd_division_id=None,
            ballotpedia_election_id=None,
            ballotpedia_kind_of_election=None,
            candidate_photos_finished=None,
            ctcl_uuid=None,
            election_name_do_not_override=False,
            election_preparation_finished=None,
            ignore_this_election=None,
            include_in_list_for_voters=None,
            internal_notes=None,
            is_national_election=None,
            state_code='',
            use_ballotpedia_as_data_source=None,
            use_ctcl_as_data_source=None,
            use_ctcl_as_data_source_by_state_code=None,
            use_google_civic_as_data_source=None,
            use_vote_usa_as_data_source=None,
            vote_usa_election_id=None,
            vote_usa_same_day_election_suffix_list=None):
        """
        Either update or create an election entry.
        """
        election_found = False
        election_on_same_day_found = False
        election_on_stage = None
        election_to_be_created = False  # Default to False
        exception_multiple_object_returned = False
        new_election_created = False
        status = ""
        success = True

        error_results = {
            'election':                 election_on_stage,
            'election_found':           election_found,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_election_created':     new_election_created,
            'status':                   status,
            'success':                  success,
        }

        if not positive_value_exists(election_day_text):
            success = False
            status += 'MISSING_ELECTION_DAY_TEXT '

        if not positive_value_exists(election_name):
            success = False
            status += 'MISSING_ELECTION_NAME '

        if not success:
            error_results['success'] = False
            error_results['status'] = status
            return error_results

        if not positive_value_exists(state_code) and positive_value_exists(ocd_division_id):
            state_code = extract_state_from_ocd_division_id(ocd_division_id)
        state_code_lower_case = state_code.lower() if state_code else ''

        try:
            # See if there is an election on this date already
            queryset = Election.objects.all()
            queryset = queryset.filter(election_day_text=election_day_text)
            election_possibility_list = list(queryset)
            if len(election_possibility_list) == 1:
                election_on_same_day_found = True
                status += "ELECTION_ON_SAME_DAY_FOUND, election_day_text: " + str(election_day_text) + " "
                one_election = election_possibility_list[0]
                one_election_state_code_lower_case = one_election.state_code.lower() \
                    if one_election.state_code else ''
                if positive_value_exists(state_code_lower_case):
                    # We are looking for state-specific election
                    if state_code_lower_case == one_election_state_code_lower_case:
                        election_found = True
                        election_on_stage = one_election
                    else:
                        status += "STATE_CODE_MISMATCH1: " + str(election_day_text) + " "
                else:
                    if not positive_value_exists(one_election.state_code) or one_election_state_code_lower_case == 'na':
                        # We know this existing election is a national election, and we are looking for a
                        #  national election, so we can update it
                        election_found = True
                        election_on_stage = one_election
                    else:
                        status += "STATE_CODE_MISMATCH2: " + str(election_day_text) + " "
            elif len(election_possibility_list) > 0:
                election_on_same_day_found = True
                # Start by going through the list of elections and see any match an incoming variable without any doubt
                for one_election in election_possibility_list:
                    if election_found:
                        # Skip the rest
                        pass
                    elif one_election.ballotpedia_election_id == ballotpedia_election_id:
                        election_found = True
                        election_on_stage = one_election
                    elif one_election.google_civic_election_id == google_civic_election_id:
                        election_found = True
                        election_on_stage = one_election
                    elif one_election.ctcl_uuid == ctcl_uuid:
                        election_found = True
                        election_on_stage = one_election
                # Then see if we can find a state-specific match
                if not election_found and positive_value_exists(state_code_lower_case):
                    for one_election in election_possibility_list:
                        one_election_state_code_lower_case = one_election.state_code.lower() \
                            if one_election.state_code else ''
                        if election_found:
                            # Skip the rest
                            pass
                        elif one_election_state_code_lower_case == state_code_lower_case:
                            election_found = True
                            election_on_stage = one_election
                    if not election_found:
                        existing_state_specific_election_not_found_for_this_state = True  # So we want to create new
                elif not election_found:
                    status += "ELECTION_NOT_FOUND_FROM_LIST: " + str(election_day_text) + " "

                # At this point there might be a national election, or elections on same day for other states
                # TODO: What to do here?
            else:
                election_to_be_created = True
                pass
        except Exception as e:
            status += "ELECTION_RETRIEVE_FAILURE: " + str(e) + " "
            success = False

        if success and not election_found:
            try:
                updated_values = {
                    # 'ctcl_uuid':          ctcl_uuid,  # Added below
                    'election_day_text':    election_day_text,
                }
                if positive_value_exists(state_code):
                    updated_values['state_code'] = state_code
                if positive_value_exists(ctcl_uuid):
                    election_on_stage, new_election_created = Election.objects.update_or_create(
                        ctcl_uuid=ctcl_uuid,
                        defaults=updated_values)
                    election_found = True
                    success = True
                    status += 'CTCL_ELECTION_SAVED '
                elif positive_value_exists(vote_usa_election_id):
                    election_on_stage, new_election_created = Election.objects.update_or_create(
                        vote_usa_election_id=vote_usa_election_id,
                        defaults=updated_values)
                    election_found = True
                    success = True
                    status += 'VOTE_USA_ELECTION_SAVED '
                elif positive_value_exists(google_civic_election_id):
                    election_on_stage, new_election_created = Election.objects.update_or_create(
                        google_civic_election_id=google_civic_election_id,
                        defaults=updated_values)
                    election_found = True
                    success = True
                    status += 'GOOGLE_ELECTION_SAVED '
                else:
                    success = False
                    status += 'ELECTION_NOT_SAVED '
            except Election.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_ELECTIONS_FOUND '
                exception_multiple_object_returned = True
            except Exception as e:
                success = False
                status += "ELECTION_SAVE_FAILURE: " + str(e) + " "

        if success and election_found:
            try:
                election_changed = False
                if ballotpedia_election_id is not None:
                    election_on_stage.ballotpedia_election_id = ballotpedia_election_id
                    election_changed = True
                if ballotpedia_kind_of_election is not None:
                    election_on_stage.ballotpedia_kind_of_election = ballotpedia_kind_of_election
                    election_changed = True
                if candidate_photos_finished is not None:
                    election_on_stage.candidate_photos_finished = candidate_photos_finished
                    election_changed = True
                if ctcl_uuid is not None:
                    if positive_value_exists(election_on_stage.ctcl_uuid):
                        # CTCL is now returning Runoffs, Primaries, General
                        # We Vote only wants one election per day. To deal with this discrepancy, we have multiple
                        #  ctcl_uuid fields
                        if ctcl_uuid == election_on_stage.ctcl_uuid:
                            pass
                        elif positive_value_exists(election_on_stage.ctcl_uuid2):
                            if ctcl_uuid == election_on_stage.ctcl_uuid2:
                                pass
                            elif positive_value_exists(election_on_stage.ctcl_uuid3):
                                if ctcl_uuid == election_on_stage.ctcl_uuid3:
                                    pass
                                else:
                                    status += "ALL_CTCL_UUIDS_FIELDS_FILLED "
                            else:
                                election_on_stage.ctcl_uuid3 = ctcl_uuid
                                election_changed = True
                        else:
                            election_on_stage.ctcl_uuid2 = ctcl_uuid
                            election_changed = True
                    else:
                        election_on_stage.ctcl_uuid = ctcl_uuid
                        election_changed = True
                if new_election_created:
                    election_on_stage.election_name = election_name
                    election_changed = True
                elif election_name_do_not_override:
                    # Do not replace existing election_name with new name
                    pass
                else:
                    election_on_stage.election_name = election_name
                    election_changed = True
                if election_preparation_finished is not None:
                    election_on_stage.election_preparation_finished = election_preparation_finished
                    election_changed = True
                if google_civic_election_id is not None:
                    election_on_stage.google_civic_election_id = google_civic_election_id
                    election_changed = True
                if not positive_value_exists(election_on_stage.google_civic_election_id):
                    google_civic_election_id = self.fetch_next_local_google_civic_election_id_integer()
                    google_civic_election_id = convert_to_int(google_civic_election_id)
                    if positive_value_exists(google_civic_election_id):
                        election_on_stage.google_civic_election_id = google_civic_election_id
                        election_changed = True
                if ignore_this_election is not None:
                    election_on_stage.ignore_this_election = ignore_this_election
                    election_changed = True
                if include_in_list_for_voters is not None:
                    election_on_stage.include_in_list_for_voters = include_in_list_for_voters
                    election_changed = True
                if internal_notes is not None:
                    election_on_stage.internal_notes = internal_notes
                    election_changed = True
                if is_national_election is not None:
                    election_on_stage.is_national_election = is_national_election
                    election_changed = True
                if ocd_division_id is not None:
                    election_on_stage.ocd_division_id = ocd_division_id
                    election_changed = True
                if use_ballotpedia_as_data_source is not None:
                    election_on_stage.use_ballotpedia_as_data_source = \
                        positive_value_exists(use_ballotpedia_as_data_source)
                    election_changed = True
                if use_ctcl_as_data_source is not None:
                    election_on_stage.use_ctcl_as_data_source = positive_value_exists(use_ctcl_as_data_source)
                    election_changed = True
                if use_ctcl_as_data_source_by_state_code is not None:
                    election_on_stage.use_ctcl_as_data_source_by_state_code = use_ctcl_as_data_source_by_state_code
                    election_changed = True
                if use_google_civic_as_data_source is not None:
                    election_on_stage.use_google_civic_as_data_source = \
                        positive_value_exists(use_google_civic_as_data_source)
                    election_changed = True
                if use_vote_usa_as_data_source is not None:
                    election_on_stage.use_vote_usa_as_data_source = positive_value_exists(use_vote_usa_as_data_source)
                    election_changed = True
                if vote_usa_election_id is not None:
                    election_on_stage.vote_usa_election_id = vote_usa_election_id
                    election_changed = True
                if vote_usa_same_day_election_suffix_list is not None:
                    election_on_stage.vote_usa_same_day_election_suffix_list = \
                        vote_usa_same_day_election_suffix_list
                    election_changed = True
                if election_changed:
                    election_on_stage.save()
            except Exception as e:
                success = False
                status += "ELECTION_SAVE_FAILURE: " + str(e) + " "

        results = {
            'election':                 election_on_stage,
            'election_found':           election_found,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_election_created':     new_election_created,
            'status':                   status,
            'success':                  success,
        }
        return results

    @staticmethod
    def retrieve_ballotpedia_election(ballotpedia_election_id=0):
        ballotpedia_election_id = convert_to_int(ballotpedia_election_id)

        ballotpedia_election = BallotpediaElection()
        try:
            if positive_value_exists(ballotpedia_election_id):
                ballotpedia_election = BallotpediaElection.objects.get(ballotpedia_election_id=ballotpedia_election_id)
                if ballotpedia_election.id:
                    ballotpedia_election_found = True
                    status = "BALLOTPEDIA_ELECTION_FOUND_WITH_GOOGLE_CIVIC_ELECTION_ID "
                else:
                    ballotpedia_election_found = False
                    status = "BALLOTPEDIA_ELECTION_NOT_FOUND_WITH_GOOGLE_CIVIC_ELECTION_ID "
                success = True
            else:
                ballotpedia_election_found = False
                status = "Insufficient variables included to retrieve one Ballotpedia election."
                success = False
        except BallotpediaElection.MultipleObjectsReturned as e:
            ballotpedia_election_found = False
            status = "ERROR_MORE_THAN_ONE_BALLOTPEDIA_ELECTION_FOUND"
            success = False
        except BallotpediaElection.DoesNotExist:
            ballotpedia_election_found = False
            status = "BALLOTPEDIA_ELECTION_NOT_FOUND"
            success = True

        results = {
            'success':                      success,
            'status':                       status,
            'ballotpedia_election_found':   ballotpedia_election_found,
            'ballotpedia_election_id':      ballotpedia_election_id,
            'ballotpedia_election':         ballotpedia_election,
        }
        return results

    @staticmethod
    def retrieve_elections_between_dates(
            starting_date_as_integer=0,
            ending_date_as_integer=0,
            restrict_to_elections_visible_to_voters=False):
        status = ""
        election_list_found = False

        starting_date = convert_date_as_integer_to_date(starting_date_as_integer)
        starting_date_as_we_vote_date = convert_date_to_we_vote_date_string(starting_date)
        ending_date = convert_date_as_integer_to_date(ending_date_as_integer)
        ending_date_as_we_vote_date = convert_date_to_we_vote_date_string(ending_date)
        try:
            election_list_query = Election.objects.using('readonly').all()
            if positive_value_exists(starting_date_as_integer):
                election_list_query = election_list_query.filter(election_day_text__gte=starting_date_as_we_vote_date)
            if positive_value_exists(ending_date_as_integer):
                election_list_query = election_list_query.filter(election_day_text__lte=ending_date_as_we_vote_date)
            if positive_value_exists(restrict_to_elections_visible_to_voters):
                election_list_query = election_list_query.filter(include_in_list_for_voters=True)
            election_list_query = election_list_query.exclude(ignore_this_election=True)
            election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list = list(election_list_query)
            if len(election_list) > 0:
                election_list_found = True
            status += 'ELECTIONS_FOUND '
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_ELECTIONS_FOUND '
            success = True
            election_list = []
        except Exception as e:
            status += 'ERROR_RETRIEVING_ELECTIONS_BETWEEN_DATES: ' + str(e) + ' '
            success = False
            election_list = []

        results = {
            'success':              success,
            'status':               status,
            'election_list':        election_list,
            'election_list_found':  election_list_found,
        }
        return results

    @staticmethod
    def retrieve_elections_by_date(newest_to_oldest=True, include_test_election=False):
        try:
            election_list_query = Election.objects.using('readonly').all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list_query = election_list_query.order_by('election_day_text', 'election_name')
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

    @staticmethod
    def retrieve_election(
            google_civic_election_id=0,
            election_id=0,
            read_only=True,
            ctcl_uuid='',
            vote_usa_election_id=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)

        election = None
        status = ""
        try:
            if positive_value_exists(ctcl_uuid):
                if positive_value_exists(read_only):
                    election = Election.objects.using('readonly').get(
                        Q(ctcl_uuid=ctcl_uuid) | Q(ctcl_uuid2=ctcl_uuid) | Q(ctcl_uuid3=ctcl_uuid))
                else:
                    election = Election.objects.get(
                        Q(ctcl_uuid=ctcl_uuid) | Q(ctcl_uuid2=ctcl_uuid) | Q(ctcl_uuid3=ctcl_uuid))
                if election.id:
                    ctcl_uuid = election.ctcl_uuid
                    election_found = True
                    status += "ELECTION_FOUND_WITH_CTCL_UUID "
                else:
                    election_found = False
                    status += "ELECTION_NOT_FOUND_WITH_CTCL_UUID "
                success = True
            elif positive_value_exists(google_civic_election_id):
                if positive_value_exists(read_only):
                    election = Election.objects.using('readonly').get(google_civic_election_id=google_civic_election_id)
                else:
                    election = Election.objects.get(google_civic_election_id=google_civic_election_id)
                if election.id:
                    ctcl_uuid = election.ctcl_uuid
                    election_found = True
                    status += "ELECTION_FOUND_WITH_GOOGLE_CIVIC_ELECTION_ID "
                else:
                    election_found = False
                    status += "ELECTION_NOT_FOUND_WITH_GOOGLE_CIVIC_ELECTION_ID "
                success = True
            elif positive_value_exists(election_id):
                if positive_value_exists(read_only):
                    election = Election.objects.using('readonly').get(id=election_id)
                else:
                    election = Election.objects.get(id=election_id)
                if election.id:
                    ctcl_uuid = election.ctcl_uuid
                    election_found = True
                    status += "ELECTION_FOUND_WITH_ELECTION_ID "
                else:
                    election_found = False
                    status += "ELECTION_NOT_FOUND_WITH_ID "
                success = True
            elif positive_value_exists(vote_usa_election_id):
                if positive_value_exists(read_only):
                    election = Election.objects.using('readonly').get(
                        vote_usa_election_id=vote_usa_election_id)
                else:
                    election = Election.objects.get(vote_usa_election_id=vote_usa_election_id)
                if election.id:
                    ctcl_uuid = election.ctcl_uuid
                    election_found = True
                    status += "ELECTION_FOUND_WITH_VOTE_USA_ELECTION_ID "
                else:
                    election_found = False
                    status += "ELECTION_NOT_FOUND_WITH_VOTE_USA_ELECTION_ID "
                success = True
            else:
                election_found = False
                status += "Insufficient variables included to retrieve one election."
                success = False
        except Election.MultipleObjectsReturned as e:
            election_found = False
            status += "ERROR_MORE_THAN_ONE_ELECTION_FOUND"
            success = False
        except Election.DoesNotExist:
            election_found = False
            status += "ELECTION_NOT_FOUND"
            success = True

        results = {
            'ctcl_uuid':                ctcl_uuid,
            'election':                 election,
            'election_found':           election_found,
            'google_civic_election_id': google_civic_election_id,
            'status':                   status,
            'success':                  success,
        }
        return results

    @staticmethod
    def retrieve_listed_elections():
        """
        These are all the elections marked as "listed" with "include_in_list_for_voters"
        :return:
        """
        election_list = []
        status = ''
        try:
            election_list_query = Election.objects.using('readonly').all()
            election_list_query = election_list_query.filter(include_in_list_for_voters=True)
            election_list_query = election_list_query.order_by('election_day_text').reverse()

            election_list = list(election_list_query)

            status += 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_ELECTIONS_FOUND'
            success = True

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    @staticmethod
    def retrieve_upcoming_elections(
            state_code="",
            without_state_code=False,
            require_include_in_list_for_voters=False,
            include_test_election=False,
            read_only=True):
        status = ''
        election_list_found = False
        upcoming_election_list = []
        today = datetime.now().date()
        we_vote_date_string = convert_date_to_we_vote_date_string(today)
        try:
            if positive_value_exists(read_only):
                election_list_query = Election.objects.using('readonly').all()
            else:
                election_list_query = Election.objects.all()
            election_list_query = election_list_query.filter(election_day_text__gte=we_vote_date_string)
            election_list_query = election_list_query.exclude(ignore_this_election=True)
            if positive_value_exists(require_include_in_list_for_voters):
                election_list_query = election_list_query.filter(include_in_list_for_voters=True)
            if positive_value_exists(without_state_code):
                election_list_query = election_list_query.filter(Q(state_code__isnull=True) | Q(state_code__exact=''))
            elif positive_value_exists(state_code):
                election_list_query = election_list_query.filter(state_code__iexact=state_code)
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list_query = election_list_query.order_by('election_day_text', 'election_name')

            upcoming_election_list = list(election_list_query)

            status += 'ELECTION_QUERY_COMPLETE '
            election_list_found = positive_value_exists(len(upcoming_election_list))
            success = True
        except Exception as e:
            status += "RETRIEVE_UPCOMING_ELECTIONS_QUERY_FAILURE " + str(e) + " "
            success = False

        results = {
            'success':          success,
            'status':           status,
            'election_list':    upcoming_election_list,
            'election_list_found': election_list_found,
        }
        return results

    def retrieve_upcoming_google_civic_election_id_list(
            self,
            limit_to_this_state_code='',
            require_include_in_list_for_voters=False):
        # There is a parallel function in controllers retrieve_upcoming_election_id_list(
        status = ""
        success = True
        upcoming_google_civic_election_id_list = []
        results = self.retrieve_upcoming_elections(
            state_code=limit_to_this_state_code,
            require_include_in_list_for_voters=require_include_in_list_for_voters,
            read_only=True)
        if results['election_list_found']:
            election_list = results['election_list']
            for one_election in election_list:
                if positive_value_exists(one_election.google_civic_election_id):
                    upcoming_google_civic_election_id_list.append(one_election.google_civic_election_id)
        else:
            status += results['status']
            success = results['success']

        # If a state code IS included, then the above retrieve_upcoming_elections will have missed the national election
        if positive_value_exists(limit_to_this_state_code):
            results = self.retrieve_upcoming_national_elections(
                require_include_in_list_for_voters=require_include_in_list_for_voters)
            if results['election_list_found']:
                election_list = results['election_list']
                for one_election in election_list:
                    if positive_value_exists(one_election.google_civic_election_id) \
                            and one_election.google_civic_election_id not in upcoming_google_civic_election_id_list:
                        upcoming_google_civic_election_id_list.append(one_election.google_civic_election_id)
            else:
                status += results['status']
                success = results['success']

        upcoming_google_civic_election_id_list_found = len(upcoming_google_civic_election_id_list)

        results = {
            'success':                                      success,
            'status':                                       status,
            'upcoming_google_civic_election_id_list':       upcoming_google_civic_election_id_list,
            'upcoming_google_civic_election_id_list_found': upcoming_google_civic_election_id_list_found,
        }
        return results

    @staticmethod
    def retrieve_prior_elections_this_year(
            state_code="",
            without_state_code=False,
            starting_year=0):
        status = ""
        success = True
        election_list_found = False
        prior_election_list = []
        year = 0
        today = datetime.now().date()
        we_vote_date_string = convert_date_to_we_vote_date_string(today)
        if positive_value_exists(starting_year):
            year = int(starting_year)
            if 2020 < year < 2050:
                first_day_this_year_string = str(year) + "-01-01"
        if not positive_value_exists(year):
            first_day_this_year_string = "{year}-01-01".format(year=today.year)

        try:
            election_list_query = Election.objects.using('readonly').all()
            election_list_query = election_list_query.filter(
                Q(election_day_text__lt=we_vote_date_string) & Q(election_day_text__gte=first_day_this_year_string))
            if positive_value_exists(without_state_code):
                election_list_query = election_list_query.filter(Q(state_code__isnull=True) | Q(state_code__exact=''))
            elif positive_value_exists(state_code):
                election_list_query = election_list_query.filter(state_code__iexact=state_code)
            election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list_query = election_list_query.order_by('election_day_text', 'election_name')

            prior_election_list = list(election_list_query)

            status += 'PRIOR_ELECTIONS_FOUND '
            election_list_found = positive_value_exists(len(prior_election_list))
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_PRIOR_ELECTIONS_FOUND '
            success = True
            election_list_found = False
        except Exception as e:
            status += "RETRIEVE_PRIOR_ELECTIONS_QUERY_FAILURE " + str(e) + " "
            success = False

        results = {
            'success':          success,
            'status':           status,
            'election_list':    prior_election_list,
            'election_list_found': election_list_found,
        }
        return results

    def retrieve_prior_google_civic_election_id_list_this_year(self, limit_to_this_state_code='', starting_year=0):
        status = ""
        success = True
        prior_google_civic_election_id_list = []
        results = self.retrieve_prior_elections_this_year(state_code=limit_to_this_state_code,
                                                          starting_year=starting_year)
        if results['election_list_found']:
            election_list = results['election_list']
            for one_election in election_list:
                if positive_value_exists(one_election.google_civic_election_id):
                    prior_google_civic_election_id_list.append(one_election.google_civic_election_id)
        else:
            status += results['status']
            # success = results['success']

        # If a state code IS included, then the above retrieve_upcoming_elections will have missed the national election
        if positive_value_exists(limit_to_this_state_code):
            results = self.retrieve_prior_national_elections_this_year()
            if results['election_list_found']:
                election_list = results['election_list_found']
                for one_election in election_list:
                    if positive_value_exists(one_election.google_civic_election_id) \
                            and one_election.google_civic_election_id not in prior_google_civic_election_id_list:
                        prior_google_civic_election_id_list.append(one_election.google_civic_election_id)
            else:
                status += results['status']

        prior_google_civic_election_id_list_found = len(prior_google_civic_election_id_list)

        results = {
            'success': success,
            'status': status,
            'prior_google_civic_election_id_list': prior_google_civic_election_id_list,
            'prior_google_civic_election_id_list_found': prior_google_civic_election_id_list_found,
        }
        return results

    def retrieve_next_election_for_state(self, state_code, require_include_in_list_for_voters=True):
        """
        We want either the next election in this state, or the next national election, whichever comes first
        :param state_code:
        :param require_include_in_list_for_voters:
        :return:
        """
        status = ""
        from ballot.models import BallotItemListManager
        ballot_item_list_manager = BallotItemListManager()
        # Find state-specific elections
        upcoming_state_elections_results = self.retrieve_upcoming_elections(
            state_code, require_include_in_list_for_voters=require_include_in_list_for_voters)
        state_election_list = upcoming_state_elections_results['election_list']
        status += upcoming_state_elections_results['status']

        # Find national elections with data from this state
        without_state_code = True
        upcoming_national_elections_results = self.retrieve_upcoming_elections(
            "", without_state_code=without_state_code,
            require_include_in_list_for_voters=require_include_in_list_for_voters)
        national_election_list = upcoming_national_elections_results['election_list']
        filtered_national_election_list = []
        for national_election in national_election_list:
            # Does this national election have any ballot items for state_code?
            results = ballot_item_list_manager.count_ballot_items(
                national_election.google_civic_election_id, state_code)
            ballot_item_count = results['ballot_item_list_count']
            if positive_value_exists(ballot_item_count):
                filtered_national_election_list.append(national_election)

        combined_election_list = state_election_list + filtered_national_election_list
        # Find earliest election (next election)
        election = None
        election_found = False
        earliest_election_day_text = None
        for one_election in combined_election_list:
            if not positive_value_exists(earliest_election_day_text):
                earliest_election_day_text = one_election.election_day_text
            if one_election.election_day_text <= earliest_election_day_text:
                earliest_election_day_text = one_election.election_day_text
                election = one_election
                election_found = True

        success = True
        status += "RETRIEVE_NEXT_ELECTION_FOR_STATE_COMPLETED "
        results = {
            'success':          success,
            'status':           status,
            'election_found':   election_found,
            'election':         election,
        }
        return results

    def retrieve_next_national_election(self, require_include_in_list_for_voters=False):
        """
        We want the next national election
        :return:
        """
        status = ""
        without_state_code = True
        upcoming_national_elections_results = self.retrieve_upcoming_elections(
            "", without_state_code, require_include_in_list_for_voters=require_include_in_list_for_voters)
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

    def retrieve_prior_election_for_state(self, state_code, require_include_in_list_for_voters=True,
                                          cached_national_election_list=False):
        """
        We want either the prior election in this state, or the prior national election, whichever was most recent
        :param state_code:
        :param require_include_in_list_for_voters:
        :param cached_national_election_list:
        :return:
        """
        status = ""
        from ballot.models import BallotItemListManager
        ballot_item_list_manager = BallotItemListManager()

        # Find state-specific elections
        prior_state_elections_results = self.retrieve_prior_elections_this_year(
            state_code=state_code)
        state_election_list = prior_state_elections_results['election_list']
        status += prior_state_elections_results['status']

        # Find national elections with data from this state
        if cached_national_election_list:
            national_election_list = cached_national_election_list
        else:
            without_state_code = True
            prior_national_elections_results = self.retrieve_prior_elections_this_year(
                state_code="", without_state_code=without_state_code)
            national_election_list = prior_national_elections_results['election_list']
        filtered_national_election_list = []
        for national_election in national_election_list:
            # Does this national election have any ballot items for state_code?
            results = ballot_item_list_manager.count_ballot_items(
                national_election.google_civic_election_id, state_code)
            ballot_item_count = results['ballot_item_list_count']
            if positive_value_exists(ballot_item_count):
                filtered_national_election_list.append(national_election)

        combined_election_list = state_election_list + filtered_national_election_list
        # Find latest election in the past
        election = None
        election_found = False
        latest_election_day_text = None
        for one_election in combined_election_list:
            if not positive_value_exists(latest_election_day_text):
                latest_election_day_text = one_election.election_day_text
            if one_election.election_day_text >= latest_election_day_text:
                latest_election_day_text = one_election.election_day_text
                election = one_election
                election_found = True

        success = True
        status += "RETRIEVE_PRIOR_ELECTION_FOR_STATE_COMPLETED "
        results = {
            'success':                  success,
            'status':                   status,
            'election_found':           election_found,
            'election':                 election,
            'national_election_list':   national_election_list,
        }
        return results

    def retrieve_upcoming_national_elections(
            self, require_include_in_list_for_voters=False):
        """
        We want all upcoming national elections
        :param require_include_in_list_for_voters:
        :return:
        """
        status = ""
        without_state_code = True
        upcoming_national_elections_results = self.retrieve_upcoming_elections(
            "", without_state_code, require_include_in_list_for_voters=require_include_in_list_for_voters)
        election_list = upcoming_national_elections_results['election_list']

        if not len(election_list):
            status += upcoming_national_elections_results['status']
            success = True
            status += "RETRIEVE_UPCOMING_ELECTIONS_FOR_STATE-NOT_FOUND: "
            results = {
                'success':          success,
                'status':           status,
                'election_list_found':   False,
                'election_list':         election_list,
            }
            return results

        success = True
        status += "RETRIEVE_UPCOMING_ELECTIONS_FOR_STATE-FOUND "
        results = {
            'success':          success,
            'status':           status,
            'election_list_found': False,
            'election_list': election_list,
        }
        return results

    def retrieve_next_election_with_state_optional(self, state_code="", require_include_in_list_for_voters=True):
        """
        We want either the next election in this state, or the next national election, whichever comes first
        :param state_code:
        :param require_include_in_list_for_voters:
        :return:
        """
        status = ""
        election_list = []
        if positive_value_exists(state_code):
            upcoming_state_elections_results = self.retrieve_upcoming_elections(
                state_code, require_include_in_list_for_voters=require_include_in_list_for_voters)
            election_list = upcoming_state_elections_results['election_list']
            status += upcoming_state_elections_results['status']
        if not len(election_list):
            without_state_code = True
            upcoming_national_elections_results = self.retrieve_upcoming_elections(
                "", without_state_code, require_include_in_list_for_voters=require_include_in_list_for_voters)
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

    def retrieve_prior_national_elections_this_year(self):
        """
        We want the prior national elections this year
        :return:
        """
        status = ""
        without_state_code = True
        prior_national_elections_results = self.retrieve_prior_elections_this_year("", without_state_code)
        election_list = prior_national_elections_results['election_list']

        if not len(election_list):
            status += prior_national_elections_results['status']
            success = True
            status += "RETRIEVE_PRIOR_ELECTION_FOR_STATE-NOT_FOUND: "
            results = {
                'success':          success,
                'status':           status,
                'election_list_found':   False,
                'election_list':         election_list,
            }
            return results

        success = True
        status += "RETRIEVE_PRIOR_ELECTION_FOR_STATE-FOUND "
        results = {
            'success':          success,
            'status':           status,
            'election_found':   True,
            'election_list': election_list,
        }
        return results

    @staticmethod
    def retrieve_year_list_by_election_list(google_civic_election_id_list=[]):
        success = True
        status = ""
        year_list = []
        year_list_found = False
        try:
            queryset = Election.objects.all()
            queryset = queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
            queryset = queryset.values_list('election_day_text', flat=True).distinct()
            election_day_text_list = list(queryset)
            year_list_found = len(election_day_text_list) > 0
            for election_day_text in election_day_text_list:
                year = election_day_text[:4]
                if year:
                    year_integer = convert_to_int(year)
                    if year_integer not in year_list:
                        year_list.append(year_integer)
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_YEAR_LIST: " + str(e) + ' '
        results = {
            'success':          success,
            'status':           status,
            'year_list':        year_list,
            'year_list_found':  year_list_found,
        }
        return results

    @staticmethod
    def retrieve_we_vote_elections():
        """
        Only retrieve the elections we have entered without a Google Civic Election Id
        :return:
        """
        status = ""
        try:
            election_list_query = Election.objects.all()
            # We can't do this as long as google_civic_election_id is stored as a char
            # election_list_query = election_list_query.filter(google_civic_election_id__gte=1000000)

            # Find only the rows where google_civic_election_id is a string longer than 6 digits ("999999")
            election_list_query = election_list_query.extra(where=["CHAR_LENGTH(google_civic_election_id) > 6"])
            election_list_query = election_list_query.order_by('election_day_text').reverse()
            election_list = election_list_query
            status += 'WE_VOTE_ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_WE_VOTE_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    @staticmethod
    def retrieve_google_civic_elections_in_state_list(state_code_list):
        status = ""
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
            status += 'WE_VOTE_ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_WE_VOTE_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    @staticmethod
    def retrieve_elections(include_test_election=False):
        """
        Retrieve all elections
        :param include_test_election:
        :return:
        """
        status = ""
        try:
            election_list_query = Election.objects.all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            election_list_query = election_list_query.order_by('-election_day_text')
            election_list = election_list_query
            status += 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    @staticmethod
    def retrieve_elections_by_election_date(
            election_day_text='',
            include_test_election=False,
            read_only=True):
        """
        Retrieve elections using election_day_text
        :param election_day_text: 
        :param include_test_election: 
        :param read_only:
        :return:
        """
        status = ""
        try:
            if positive_value_exists(read_only):
                election_list_query = Election.objects.using('readonly').all()
            else:
                election_list_query = Election.objects.all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)
            if election_day_text:
                election_list_query = election_list_query.filter(election_day_text=election_day_text)
            election_list_query = election_list_query.order_by('election_day_text', 'election_name')
            election_list = election_list_query
            status += 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_ELECTIONS_FOUND'
            success = True
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    @staticmethod
    def retrieve_elections_by_google_civic_election_id_list(
            google_civic_election_id_list=[],
            read_only=False):
        """
        Retrieve elections using google_civic_election_id
        :param google_civic_election_id_list:
        :param read_only:
        :return:
        """
        status = ""
        if not positive_value_exists(len(google_civic_election_id_list)):
            results = {
                'success':          False,
                'status':           "RETRIEVE_ELECTIONS_BY_GOOGLE_CIVIC_ELECTION_ID_LIST-MISSING ",
                'election_list':    [],
            }
            return results

        try:
            if positive_value_exists(read_only):
                election_list_query = Election.objects.using('readonly').all()
            else:
                election_list_query = Election.objects.all()
            election_list_query = election_list_query.filter(google_civic_election_id__in=google_civic_election_id_list)
            election_list_query = election_list_query.order_by('-election_day_text')
            election_list = list(election_list_query)
            status += 'ELECTIONS_FOUND '
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_ELECTIONS_FOUND '
            success = True
            election_list = []
        except Exception as e:
            status += 'NO_ELECTIONS_FOUND - ERROR: ' + str(e) + ' '
            success = False
            election_list = []

        results = {
            'success':          success,
            'status':           status,
            'election_list':    election_list,
        }
        return results

    @staticmethod
    def retrieve_elections_by_state_and_election_date(
            state_code='',
            election_day_text='',
            include_test_election=False,
            read_only=True):
        """
          Retrieve elections using state_code and election_day_text
        :param state_code:
        :param election_day_text: 
        :param include_test_election: 
        :param read_only:
        :return:
        """
        status = ""
        try:
            if positive_value_exists(read_only):
                election_list_query = Election.objects.using('readonly').all()
            else:
                election_list_query = Election.objects.all()
            if not positive_value_exists(include_test_election):
                election_list_query = election_list_query.exclude(google_civic_election_id=2000)

            if state_code and election_day_text:
                election_list_query = election_list_query.filter(state_code__iexact=state_code,
                                                                 election_day_text=election_day_text)
            election_list_query = election_list_query.order_by('election_day_text', 'election_name')
            election_list = election_list_query
            status += 'ELECTIONS_FOUND'
            success = True
        except Election.DoesNotExist as e:
            status += 'NO_ELECTIONS_FOUND'
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


def fetch_prior_election_for_state(state_code, require_include_in_list_for_voters=True):
    """
    :param state_code:
    :param require_include_in_list_for_voters:
    :return:
    """
    election_manager = ElectionManager()
    results = election_manager.retrieve_prior_election_for_state(
        state_code, require_include_in_list_for_voters=require_include_in_list_for_voters)
    if results['election_found']:
        election = results['election']
        return election
    else:
        return Election()


def fetch_next_election_for_state(state_code, require_include_in_list_for_voters=True):
    """
    Before using election returned, check for google_civic_election_id
    :param state_code:
    :param require_include_in_list_for_voters:
    :return:
    """
    election_manager = ElectionManager()
    results = election_manager.retrieve_next_election_for_state(
        state_code, require_include_in_list_for_voters=require_include_in_list_for_voters)
    if results['election_found']:
        election = results['election']
        return election
    else:
        return Election()
