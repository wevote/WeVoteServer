# office/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_we_vote_id_contest_office_integer, fetch_site_unique_id_prefix, \
    fetch_next_we_vote_id_elected_office_integer
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists, \
    OFFICE_NAME_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES, OFFICE_NAME_EQUIVALENT_PHRASE_PAIRS, \
    OFFICE_NAME_EQUIVALENT_DISTRICT_PHRASE_PAIRS, STATE_CODE_MAP


logger = wevote_functions.admin.get_logger(__name__)

CONTEST_OFFICE_UNIQUE_IDENTIFIERS = [
    'ballotpedia_district_id',
    'ballotpedia_election_id',
    'ballotpedia_id',
    'ballotpedia_office_id',
    'ballotpedia_office_name',
    'ballotpedia_office_url',
    'ballotpedia_race_id',
    'ballotpedia_race_office_level',
    'contest_level0',
    'contest_level1',
    'contest_level2',
    'cctl_uuid',
    'district_id',
    'district_name',
    'district_scope',
    'elected_office_name',
    'electorate_specifications',
    'google_ballot_placement',
    'google_civic_election_id',
    'google_civic_election_id_new',
    'google_civic_office_name',
    'maplight_id',
    'number_elected',
    'number_voting_for',
    'ocd_division_id',
    'office_name',
    'primary_party',
    'special',
    'state_code',
    'we_vote_id',
    'wikipedia_id',
]


class ContestOffice(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "off", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_office_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this contest office", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # The name of the office for this contest.
    office_name = models.CharField(verbose_name="name of the office", max_length=255, null=False, blank=False)
    # The offices' name as passed over by Google Civic. We save this so we can match to this office even
    # if we edit the office's name locally. Sometimes Google isn't consistent with office names.
    google_civic_office_name = models.CharField(verbose_name="office name exactly as received from google civic",
                                                max_length=255, null=True)
    google_civic_office_name2 = models.CharField(verbose_name="office name exactly as received from google civic",
                                                 max_length=255, null=True)
    google_civic_office_name3 = models.CharField(verbose_name="office name exactly as received from google civic",
                                                 max_length=255, null=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=False, blank=False)
    google_ballot_placement = models.BigIntegerField(
        verbose_name="the order this item should appear on the ballot", null=True, blank=True, unique=False)
    state_code = models.CharField(verbose_name="state this office serves", max_length=2, null=True, blank=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    maplight_id = models.CharField(
        verbose_name="maplight unique identifier", max_length=255, null=True, blank=True, unique=True)
    # 2018-02-16 It is unclear if we want to keep this field
    ballotpedia_id = models.CharField(
        verbose_name="ballotpedia unique identifier", max_length=255, null=True, blank=True)
    ballotpedia_election_id = models.PositiveIntegerField(verbose_name="ballotpedia election id", null=True, blank=True)
    # Equivalent to elected_office
    ballotpedia_office_id = models.PositiveIntegerField(verbose_name="ballotpedia integer id", null=True, blank=True)
    # The office's name as passed over by Ballotpedia. This helps us do exact matches when id is missing
    ballotpedia_office_name = models.CharField(verbose_name="office name exactly as received from ballotpedia",
                                               max_length=255, null=True, blank=True)
    ballotpedia_office_url = models.URLField(verbose_name='url of office on ballotpedia', blank=True, null=True)
    ballotpedia_district_id = models.PositiveIntegerField(verbose_name="ballotpedia district id", null=True, blank=True)
    # Equivalent to contest_office
    ballotpedia_race_id = models.PositiveIntegerField(verbose_name="ballotpedia integer id", null=True, blank=True)
    # Federal, State, Local,
    ballotpedia_race_office_level = models.CharField(verbose_name="race office level", max_length=255, null=True,
                                                     blank=True)
    wikipedia_id = models.CharField(verbose_name="wikipedia unique identifier", max_length=255, null=True, blank=True)
    # vote_type (ranked choice, majority)
    # The number of candidates that a voter may vote for in this contest.
    number_voting_for = models.CharField(verbose_name="google civic number of candidates to vote for",
                                         max_length=255, null=True, blank=True)
    # The number of candidates that will be elected to office in this contest.
    number_elected = models.CharField(verbose_name="google civic number of candidates who will be elected",
                                      max_length=255, null=True, blank=True)

    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="district name", max_length=255, null=True, blank=True)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=255, null=True, blank=True)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_id = models.CharField(verbose_name="google civic district id", max_length=255, null=True, blank=True)

    # The levels of government of the office for this contest. There may be more than one in cases where a
    # jurisdiction effectively acts at two different levels of government; for example, the mayor of the
    # District of Columbia acts at "locality" level, but also effectively at both
    # "administrative-area-2" and "administrative-area-1".
    contest_level0 = models.CharField(verbose_name="google civic level, option 0",
                                      max_length=255, null=True, blank=True)
    contest_level1 = models.CharField(verbose_name="google civic level, option 1",
                                      max_length=255, null=True, blank=True)
    contest_level2 = models.CharField(verbose_name="google civic level, option 2",
                                      max_length=255, null=True, blank=True)

    # ballot_placement: We store ballot_placement in the BallotItem table instead because it is different for each voter

    # A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = models.CharField(verbose_name="google civic primary party",
                                                 max_length=255, null=True, blank=True)
    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    elected_office_name = models.CharField(verbose_name="name of the elected office", max_length=255, null=True,
                                           blank=True, default=None)

    def get_office_state(self):
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
            next_local_integer = fetch_next_we_vote_id_contest_office_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "off" = tells us this is a unique id for a ContestOffice
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}off{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ContestOffice, self).save(*args, **kwargs)


class ContestOfficeManager(models.Model):

    def __unicode__(self):
        return "ContestOfficeManager"

    def retrieve_contest_office_from_id(self, contest_office_id):
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id)

    def retrieve_contest_office_from_we_vote_id(self, contest_office_we_vote_id):
        contest_office_id = 0
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, contest_office_we_vote_id)

    def retrieve_contest_office_from_ctcl_uuid(self, ctcl_uuid):
        contest_office_id = 0
        contest_office_we_vote_id = ''
        maplight_id = ''
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, contest_office_we_vote_id,
                                                              maplight_id, ctcl_uuid)

    def retrieve_contest_office_from_maplight_id(self, maplight_id):
        contest_office_id = 0
        contest_office_we_vote_id = ''
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, contest_office_we_vote_id, maplight_id)

    def retrieve_contest_office_from_ballotpedia_race_id(self, ballotpedia_race_id):
        contest_office_id = 0
        contest_office_we_vote_id = ''
        maplight_id = ''
        ctcl_uuid = ''
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, contest_office_we_vote_id,
                                                              maplight_id, ctcl_uuid, ballotpedia_race_id)

    def fetch_contest_office_id_from_maplight_id(self, maplight_id):
        contest_office_id = 0
        contest_office_we_vote_id = ''
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office(
            contest_office_id, contest_office_we_vote_id, maplight_id)
        if results['success']:
            return results['contest_office_id']
        return 0

    def fetch_contest_office_we_vote_id_from_id(self, contest_office_id):
        maplight_id = 0
        contest_office_we_vote_id = ''
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office(
            contest_office_id, contest_office_we_vote_id, maplight_id)
        if results['success']:
            return results['contest_office_we_vote_id']
        return 0

    def retrieve_offices_are_not_duplicates_list(self, contest_office_we_vote_id, for_editing=False):
        """
        Get a list of other office_we_vote_id's that are not duplicates
        :param contest_office_we_vote_id:
        :param for_editing:
        :return:
        """
        # Note that the direction of the linkage does not matter
        contest_offices_are_not_duplicates_list1 = []
        contest_offices_are_not_duplicates_list2 = []
        try:
            if positive_value_exists(for_editing):
                contest_offices_are_not_duplicates_list_query = ContestOfficesAreNotDuplicates.objects.filter(
                    contest_office1_we_vote_id__iexact=contest_office_we_vote_id,
                )
            else:
                contest_offices_are_not_duplicates_list_query = \
                    ContestOfficesAreNotDuplicates.objects.using('readonly').filter(
                        contest_office1_we_vote_id__iexact=contest_office_we_vote_id,
                    )
            contest_offices_are_not_duplicates_list1 = list(contest_offices_are_not_duplicates_list_query)
            success = True
            status = "CONTEST_OFFICES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except ContestOfficesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status = 'NO_CONTEST_OFFICES_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status = "CONTEST_OFFICES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1 "

        if success:
            try:
                if positive_value_exists(for_editing):
                    contest_offices_are_not_duplicates_list_query = ContestOfficesAreNotDuplicates.objects.filter(
                        contest_office2_we_vote_id__iexact=contest_office_we_vote_id,
                    )
                else:
                    contest_offices_are_not_duplicates_list_query = \
                        ContestOfficesAreNotDuplicates.objects.using('readonly').filter(
                            contest_office2_we_vote_id__iexact=contest_office_we_vote_id,
                        )
                contest_offices_are_not_duplicates_list2 = list(contest_offices_are_not_duplicates_list_query)
                success = True
                status = "CONTEST_OFFICES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except ContestOfficesAreNotDuplicates.DoesNotExist:
                success = True
                status = 'NO_CONTEST_OFFICES_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status = "CONTEST_OFFICES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2 "

        contest_offices_are_not_duplicates_list = \
            contest_offices_are_not_duplicates_list1 + contest_offices_are_not_duplicates_list2
        contest_offices_are_not_duplicates_list_found = positive_value_exists(len(
            contest_offices_are_not_duplicates_list))
        contest_offices_are_not_duplicates_list_we_vote_ids = []
        for one_entry in contest_offices_are_not_duplicates_list:
            if one_entry.contest_office1_we_vote_id != contest_office_we_vote_id:
                contest_offices_are_not_duplicates_list_we_vote_ids.append(one_entry.contest_office1_we_vote_id)
            elif one_entry.contest_office2_we_vote_id != contest_office_we_vote_id:
                contest_offices_are_not_duplicates_list_we_vote_ids.append(one_entry.contest_office2_we_vote_id)
        results = {
            'success':                                              success,
            'status':                                               status,
            'contest_offices_are_not_duplicates_list_found':        contest_offices_are_not_duplicates_list_found,
            'contest_offices_are_not_duplicates_list':              contest_offices_are_not_duplicates_list,
            'contest_offices_are_not_duplicates_list_we_vote_ids':  contest_offices_are_not_duplicates_list_we_vote_ids,
        }
        return results

    def fetch_offices_are_not_duplicates_list_we_vote_ids(self, office_we_vote_id):
        results = self.retrieve_offices_are_not_duplicates_list(office_we_vote_id)
        return results['contest_offices_are_not_duplicates_list_we_vote_ids']

    def update_or_create_contest_office(self, office_we_vote_id, maplight_id, google_civic_election_id,
                                        office_name, district_id, updated_contest_office_values):
        """
        Either update or create an office entry.
        """
        exception_multiple_object_returned = False
        new_office_created = False
        contest_office_on_stage = ContestOffice()
        success = False
        status = ""
        office_updated = False

        if not google_civic_election_id:
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID '
        # DALE 2016-05-10 Since we are allowing offices to be created prior to Google Civic data
        # being available, we need to remove our reliance on district_id or district_name
        # elif not (district_id or district_name):
        #     success = False
        #     status = 'MISSING_DISTRICT_ID'
        elif not office_name:
            success = False
            status += 'MISSING_OFFICE_NAME '
        elif positive_value_exists(office_we_vote_id):
            try:
                contest_office_on_stage, new_office_created = ContestOffice.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    we_vote_id__iexact=office_we_vote_id,
                    defaults=updated_contest_office_values)
                office_updated = not new_office_created
                success = True
                status += 'CONTEST_OFFICE_SAVED '
            except ContestOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND '
                exception_multiple_object_returned = True
            except ContestOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        elif positive_value_exists(maplight_id):
            try:
                contest_office_on_stage, new_office_created = ContestOffice.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    maplight_id__exact=maplight_id,
                    defaults=updated_contest_office_values)
                office_updated = not new_office_created
                success = True
                status += 'CONTEST_OFFICE_SAVED '
            except ContestOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND '
                exception_multiple_object_returned = True
            except ContestOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_MAPLIGHT_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        else:
            # Given we might have the office listed by google_civic_office_name
            # OR office_name, we need to check both before we try to create a new entry
            contest_office_found = False
            try:
                # TODO DALE Note that Vermont data in 2016 did not provide district_id. The unique value was in the
                # district_name. So all "VT State Senator" candidates were lumped into a single office. But I believe
                # Presidential races don't have either district_id or district_name, so we can't require one.
                # Perhaps have a special case for "district" -> "scope": "stateUpper"/"stateLower"
                # vs. "scope": "statewide"
                if positive_value_exists(district_id):
                    contest_office_on_stage = ContestOffice.objects.get(
                        Q(google_civic_office_name__iexact=office_name) |
                        Q(google_civic_office_name2__iexact=office_name) |
                        Q(google_civic_office_name3__iexact=office_name),
                        google_civic_election_id__exact=google_civic_election_id,
                        district_id__exact=district_id,
                        state_code__iexact=updated_contest_office_values['state_code'],
                    )
                else:
                    contest_office_on_stage = ContestOffice.objects.get(
                        Q(google_civic_office_name__iexact=office_name) |
                        Q(google_civic_office_name2__iexact=office_name) |
                        Q(google_civic_office_name3__iexact=office_name),
                        google_civic_election_id__exact=google_civic_election_id,
                        state_code__iexact=updated_contest_office_values['state_code'],
                    )
                contest_office_found = True
                success = True
                status += 'MATCHING_CONTEST_OFFICE_FOUND '
            except ContestOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_GOOGLE_CIVIC_OFFICE_NAME '
                exception_multiple_object_returned = True
            except ContestOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

            if not contest_office_found and not exception_multiple_object_returned:
                # Try to find record based on office_name (instead of google_civic_office_name)
                try:
                    if positive_value_exists(district_id):
                        contest_office_on_stage = ContestOffice.objects.get(
                            google_civic_election_id__exact=google_civic_election_id,
                            office_name__iexact=office_name,
                            district_id__exact=district_id,
                            state_code__iexact=updated_contest_office_values['state_code'],
                        )
                    else:
                        contest_office_on_stage = ContestOffice.objects.get(
                            google_civic_election_id__exact=google_civic_election_id,
                            office_name__iexact=office_name,
                            state_code__iexact=updated_contest_office_values['state_code'],
                        )
                    contest_office_found = True
                    success = True
                    status += 'CONTEST_OFFICE_SAVED '
                except ContestOffice.MultipleObjectsReturned as e:
                    success = False
                    status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_OFFICE_NAME '
                    exception_multiple_object_returned = True
                except ContestOffice.DoesNotExist:
                    exception_does_not_exist = True
                    status += "RETRIEVE_OFFICE_NOT_FOUND "
                except Exception as e:
                    status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

            if exception_multiple_object_returned:
                # We can't proceed because there is an error with the data
                success = False
            elif contest_office_found:
                # Update record
                try:
                    new_office_created = False
                    office_updated = False
                    office_has_changes = False
                    for key, value in updated_contest_office_values.items():
                        if hasattr(contest_office_on_stage, key):
                            # Note, the incoming google_civic_office_name may need to go in _name, _name2, or _name3
                            if key is "google_civic_office_name":
                                # We actually don't want to update existing values, but put the value in the first
                                # available "slot"
                                if not positive_value_exists(contest_office_on_stage.google_civic_office_name):
                                    contest_office_on_stage.google_civic_office_name = value
                                    office_has_changes = True
                                elif contest_office_on_stage.google_civic_office_name == value:
                                    pass
                                elif not positive_value_exists(contest_office_on_stage.google_civic_office_name2):
                                    contest_office_on_stage.google_civic_office_name2 = value
                                    office_has_changes = True
                                elif contest_office_on_stage.google_civic_office_name2 == value:
                                    pass
                                elif not positive_value_exists(contest_office_on_stage.google_civic_office_name3):
                                    contest_office_on_stage.google_civic_office_name3 = value
                                    office_has_changes = True
                                elif contest_office_on_stage.google_civic_office_name3 == value:
                                    pass
                            else:
                                setattr(contest_office_on_stage, key, value)
                                office_has_changes = True
                    if office_has_changes and positive_value_exists(contest_office_on_stage.we_vote_id):
                        contest_office_on_stage.save()
                        office_updated = True
                    if office_updated:
                        success = True
                        status += "CONTEST_OFFICE_UPDATED "
                    else:
                        success = True
                        status += "CONTEST_OFFICE_NOT_UPDATED "
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_CONTEST_OFFICE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    office_updated = False
                    new_office_created = False
                    contest_office_on_stage = ContestOffice.objects.create(
                        maplight_id=maplight_id,
                        google_civic_election_id=google_civic_election_id,
                        office_name=office_name,
                        district_id=district_id)
                    if positive_value_exists(contest_office_on_stage.id):
                        for key, value in updated_contest_office_values.items():
                            if hasattr(contest_office_on_stage, key):
                                setattr(contest_office_on_stage, key, value)
                        contest_office_on_stage.save()
                        new_office_created = True
                    if positive_value_exists(new_office_created):
                        success = True
                        status += "NEW_OFFICE_CREATED "
                    else:
                        success = False
                        status += "NEW_OFFICE_NOT_CREATED "
                except Exception as e:
                    status += 'FAILED_TO_CREATE_CONTEST_OFFICE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_office_created':       new_office_created,
            'contest_office':           contest_office_on_stage,
            'saved':                    new_office_created or office_updated,
            'updated':                  office_updated,
            'not_processed':            True if not success else False,
        }
        return results

    def update_or_create_contest_offices_are_not_duplicates(self, contest_office1_we_vote_id,
                                                            contest_office2_we_vote_id):
        """
        Either update or create a contest_office entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_contest_offices_are_not_duplicates_created = False
        contest_offices_are_not_duplicates = ContestOfficesAreNotDuplicates()
        status = ""

        if positive_value_exists(contest_office1_we_vote_id) and positive_value_exists(contest_office2_we_vote_id):
            try:
                updated_values = {
                    'contest_office1_we_vote_id':    contest_office1_we_vote_id,
                    'contest_office2_we_vote_id':    contest_office2_we_vote_id,
                }
                contest_offices_are_not_duplicates, new_contest_offices_are_not_duplicates_created = \
                    ContestOfficesAreNotDuplicates.objects.update_or_create(
                        contest_office1_we_vote_id__exact=contest_office1_we_vote_id,
                        contest_office2_we_vote_id__iexact=contest_office2_we_vote_id,
                        defaults=updated_values)
                success = True
                status += "CONTEST_OFFICES_ARE_NOT_DUPLICATES_UPDATED_OR_CREATED "
            except ContestOfficesAreNotDuplicates.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_ARE_NOT_DUPLICATES_FOUND_BY_CONTEST_OFFICE_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'EXCEPTION_UPDATE_OR_CREATE_CONTEST_OFFICES_ARE_NOT_DUPLICATES ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                                          success,
            'status':                                           status,
            'MultipleObjectsReturned':                          exception_multiple_object_returned,
            'new_contest_offices_are_not_duplicates_created':   new_contest_offices_are_not_duplicates_created,
            'contest_offices_are_not_duplicates':               contest_offices_are_not_duplicates,
        }
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_contest_office(self, contest_office_id, contest_office_we_vote_id='',
                                maplight_id=None, ctcl_uuid=None, ballotpedia_race_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        contest_office_on_stage = ContestOffice()

        try:
            if positive_value_exists(contest_office_id):
                contest_office_on_stage = ContestOffice.objects.get(id=contest_office_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_ID"
            elif positive_value_exists(contest_office_we_vote_id):
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id__iexact=contest_office_we_vote_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(ctcl_uuid):
                contest_office_on_stage = ContestOffice.objects.get(ctcl_uuid=ctcl_uuid)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_CTCL_UUID"
            elif positive_value_exists(maplight_id):
                contest_office_on_stage = ContestOffice.objects.get(maplight_id=maplight_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_MAPLIGHT_ID"
            elif positive_value_exists(ballotpedia_race_id):
                ballotpedia_race_id_integer = convert_to_int(ballotpedia_race_id)
                contest_office_on_stage = ContestOffice.objects.get(ballotpedia_race_id=ballotpedia_race_id_integer)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_BALLOTPEDIA_OFFICE_ID"
            else:
                status = "RETRIEVE_OFFICE_SEARCH_INDEX_MISSING"
        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_OFFICE_MULTIPLE_OBJECTS_RETURNED"
        except ContestOffice.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_OFFICE_NOT_FOUND"

        results = {
            'success':                      True if convert_to_int(contest_office_id) > 0 else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'contest_office_found':         True if convert_to_int(contest_office_id) > 0 else False,
            'contest_office_id':            convert_to_int(contest_office_id),
            'contest_office_we_vote_id':    contest_office_we_vote_id,
            'contest_office':               contest_office_on_stage,
        }
        return results

    def fetch_contest_office_id_from_we_vote_id(self, contest_office_we_vote_id):
        """
        Take in contest_office_we_vote_id and return internal/local-to-this-database contest_office_id
        :param contest_office_we_vote_id:
        :return:
        """
        contest_office_id = 0
        try:
            if positive_value_exists(contest_office_we_vote_id):
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id=contest_office_we_vote_id)
                contest_office_id = contest_office_on_stage.id

        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ContestOffice.DoesNotExist:
            contest_office_id = 0

        return contest_office_id

    def fetch_state_code_from_we_vote_id(self, contest_office_we_vote_id):
        """
        Take in contest_office_we_vote_id and return the state_code
        :param contest_office_we_vote_id:
        :return:
        """
        state_code = ""
        try:
            if positive_value_exists(contest_office_we_vote_id):
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id=contest_office_we_vote_id)
                state_code = contest_office_on_stage.state_code

        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ContestOffice.DoesNotExist:
            pass

        return state_code

    def create_contest_office_row_entry(self, contest_office_name, contest_office_votes_allowed, ctcl_uuid,
                                        contest_office_number_elected, google_civic_election_id, state_code,
                                        defaults):
        """
        Create ContestOffice table entry with ContestOffice details 
        :param contest_office_name: 
        :param contest_office_votes_allowed:
        :param ctcl_uuid: 
        :param contest_office_number_elected: 
        :param google_civic_election_id: 
        :param state_code:
        :param defaults:
        :return:
        """

        contest_office_updated = False
        new_contest_office_created = False
        new_contest_office = ''

        try:
            new_contest_office = ContestOffice.objects.create(
                office_name=contest_office_name,
                number_voting_for=contest_office_votes_allowed,
                ctcl_uuid=ctcl_uuid,
                number_elected=contest_office_number_elected,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code)
            if new_contest_office:
                success = True
                status = "CONTEST_OFFICE_CREATED"
                contest_office_updated = True
                new_contest_office_created = True
                new_contest_office.district_id = defaults['district_id']
                new_contest_office.district_name = defaults['district_name']
                new_contest_office.district_scope = defaults['district_scope']
                if 'ballotpedia_district_id' in defaults:
                    new_contest_office.ballotpedia_district_id = convert_to_int(defaults['ballotpedia_district_id'])
                if 'ballotpedia_election_id' in defaults:
                    new_contest_office.ballotpedia_election_id = convert_to_int(defaults['ballotpedia_election_id'])
                if 'ballotpedia_office_id' in defaults:
                    new_contest_office.ballotpedia_office_id = convert_to_int(defaults['ballotpedia_office_id'])
                if 'ballotpedia_office_name' in defaults:
                    new_contest_office.ballotpedia_office_name = defaults['ballotpedia_office_name']
                if 'ballotpedia_office_url' in defaults:
                    new_contest_office.ballotpedia_office_url = defaults['ballotpedia_office_url']
                if 'ballotpedia_race_id' in defaults:
                    new_contest_office.ballotpedia_race_id = convert_to_int(defaults['ballotpedia_race_id'])
                if 'ballotpedia_race_office_level' in defaults:
                    new_contest_office.ballotpedia_race_office_level = defaults['ballotpedia_race_office_level']
                new_contest_office.save()
            else:
                success = False
                status = "CONTEST_OFFICE_CREATE_FAILED"
        except Exception as e:
            success = False
            new_contest_office_created = False
            status = "CONTEST_OFFICE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                      success,
                'status':                       status,
                'new_contest_office_created':   new_contest_office_created,
                'contest_office_updated':       contest_office_updated,
                'contest_office':               new_contest_office,
            }
        return results

    def update_contest_office_row_entry(self, contest_office_name, contest_office_votes_allowed, ctcl_uuid,
                                        contest_office_number_elected, contest_office_we_vote_id,
                                        google_civic_election_id, state_code,
                                        defaults):
        """
        Update ContestOffice table entry with matching we_vote_id 
        :param contest_office_name: 
        :param contest_office_votes_allowed:
        :param ctcl_uuid: 
        :param contest_office_number_elected:
        :param contest_office_we_vote_id:
        :param google_civic_election_id:
        :param state_code:
        :param defaults:
        :return:
        """

        success = False
        status = ""
        contest_office_updated = False
        # new_contest_office_created = False
        # new_contest_office = ''
        existing_office_entry = ''
        contest_office_found = False

        try:
            if positive_value_exists(contest_office_we_vote_id):
                existing_office_entry = ContestOffice.objects.get(we_vote_id__iexact=contest_office_we_vote_id)
                contest_office_found = True
            elif positive_value_exists(ctcl_uuid):
                existing_office_entry = ContestOffice.objects.get(ctcl_uuid=ctcl_uuid)
                contest_office_found = True

            if contest_office_found:
                # found the existing entry, update the values
                existing_office_entry.office_name = contest_office_name
                existing_office_entry.number_voted_for = contest_office_votes_allowed
                existing_office_entry.ctcl_uuid = ctcl_uuid
                existing_office_entry.number_elected = contest_office_number_elected
                existing_office_entry.google_civic_election_id = google_civic_election_id
                existing_office_entry.state_code = state_code
                if 'district_id' in defaults:
                    existing_office_entry.district_id = defaults['district_id']
                if 'district_name' in defaults:
                    existing_office_entry.district_name = defaults['district_name']
                if 'district_scope' in defaults:
                    existing_office_entry.district_scope = defaults['district_scope']
                if 'ballotpedia_election_id' in defaults:
                    existing_office_entry.ballotpedia_election_id = convert_to_int(defaults['ballotpedia_election_id'])
                if 'ballotpedia_office_id' in defaults:
                    existing_office_entry.ballotpedia_office_id = convert_to_int(defaults['ballotpedia_office_id'])
                if 'ballotpedia_office_name' in defaults:
                    existing_office_entry.ballotpedia_office_name = defaults['ballotpedia_office_name']
                if 'ballotpedia_office_url' in defaults:
                    existing_office_entry.ballotpedia_office_url = defaults['ballotpedia_office_url']
                if 'ballotpedia_race_id' in defaults:
                    existing_office_entry.ballotpedia_race_id = convert_to_int(defaults['ballotpedia_race_id'])
                if 'ballotpedia_race_office_level' in defaults:
                    existing_office_entry.ballotpedia_race_office_level = defaults['ballotpedia_race_office_level']
                # now go ahead and save this entry (update)
                existing_office_entry.save()
                contest_office_updated = True
                success = True
                status = "CONTEST_OFFICE_UPDATED"
        except Exception as e:
            success = False
            contest_office_updated = False
            status = "CONTEST_OFFICE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                      success,
                'status':                       status,
                'contest_office_updated':       contest_office_updated,
                'contest_office':       existing_office_entry,
            }
        return results

    def count_contest_offices_for_election(self, google_civic_election_id):
        """
        Return count of contest offices found for a given election
        :param google_civic_election_id: 
        :return: 
        """
        contest_offices_count = 0
        success = False
        if positive_value_exists(google_civic_election_id):
            try:
                contest_office_item_queryset = ContestOffice.objects.all()
                contest_office_item_queryset = contest_office_item_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
                contest_offices_count = contest_office_item_queryset.count()

                status = 'CONTEST_OFFICE_ITEMS_FOUND '
                success = True
            except ContestOffice.DoesNotExist:
                # No contest office items found. Not a problem.
                status = 'NO_CONTEST_OFFICE_ITEMS_FOUND '
                success = True
            except Exception as e:
                handle_exception(e, logger=logger)
                status = 'FAILED retrieve_contest_office_items_for_election ' \
                         '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
        else:
            status = 'INVALID_GOOGLE_CIVIC_ELECTION_ID'
        results = {
            'success':                  success,
            'status':                   status,
            'contest_offices_count':    contest_offices_count,
        }
        return results


class ContestOfficeListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Offices
    """

    def __unicode__(self):
        return "ContestOfficeListManager"

    def retrieve_all_offices_for_upcoming_election(self, google_civic_election_id=0, state_code="",
                                                   return_list_of_objects=False):
        office_list = []
        return self.retrieve_offices(google_civic_election_id, state_code, office_list, return_list_of_objects)

    def retrieve_offices_by_list(self, office_list, return_list_of_objects=False):
        google_civic_election_id = 0
        state_code = ""
        return self.retrieve_offices(google_civic_election_id, state_code, office_list, return_list_of_objects)

    def fetch_office_count(self, google_civic_election_id=0, state_code=""):
        office_count = 0

        try:
            office_queryset = ContestOffice.objects.all()
            if positive_value_exists(google_civic_election_id):
                office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                office_queryset = office_queryset.filter(state_code__iexact=state_code)

            office_count = office_queryset.count()
        except ContestOffice.DoesNotExist:
            pass
        except Exception as e:
            pass

        return office_count

    def fetch_offices_from_non_unique_identifiers_count(
            self, google_civic_election_id, state_code, office_name, ignore_office_we_vote_id_list=[]):
        keep_looking_for_duplicates = True
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(office_name):
            # Search by Contest Office name exact match
            try:
                contest_office_query = ContestOffice.objects.all()
                contest_office_query = contest_office_query.filter(office_name__iexact=office_name,
                                                                   google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    contest_office_query = contest_office_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_office_we_vote_id_list):
                    contest_office_query = contest_office_query.exclude(we_vote_id__in=ignore_office_we_vote_id_list)

                contest_office_count = contest_office_query.count()
                if positive_value_exists(contest_office_count):
                    return contest_office_count
            except ContestOffice.DoesNotExist:
                status += "BATCH_ROW_ACTION_OFFICE_NOT_FOUND "
            except Exception as e:
                keep_looking_for_duplicates = False

        return 0

    def retrieve_offices(self, google_civic_election_id=0, state_code="", office_list=[],
                         return_list_of_objects=False, ballotpedia_district_id=0):
        office_list_objects = []
        office_list_light = []
        office_list_found = False

        try:
            office_queryset = ContestOffice.objects.all()
            if positive_value_exists(google_civic_election_id):
                office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(ballotpedia_district_id):
                office_queryset = office_queryset.filter(ballotpedia_district_id=ballotpedia_district_id)
            if positive_value_exists(state_code):
                office_queryset = office_queryset.filter(state_code__iexact=state_code)
            if len(office_list):
                office_queryset = office_queryset.filter(
                    we_vote_id__in=office_list)
            office_queryset = office_queryset.order_by("office_name")
            office_list_objects = office_queryset

            if len(office_list_objects):
                office_list_found = True
                status = 'OFFICES_RETRIEVED'
                success = True
            else:
                status = 'NO_OFFICES_RETRIEVED'
                success = True
        except ContestOffice.DoesNotExist:
            # No offices found. Not a problem.
            status = 'NO_OFFICES_FOUND_DoesNotExist'
            office_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_offices_for_upcoming_election ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if office_list_found:
            for office in office_list_objects:
                one_office = {
                    'ballot_item_display_name': office.office_name,
                    'measure_we_vote_id':       '',
                    'office_we_vote_id':        office.we_vote_id,
                    'candidate_we_vote_id':     '',
                }
                office_list_light.append(one_office.copy())

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'office_list_found':        office_list_found,
            'office_list_objects':      office_list_objects if return_list_of_objects else [],
            'office_list_light':        office_list_light,
        }
        return results

    def retrieve_possible_duplicate_offices(self, google_civic_election_id, state_code, office_name,
                                            we_vote_id_from_master=''):
        """
        Find offices that match another office in all critical fields other than we_vote_id_from_master
        :param google_civic_election_id:
        :param state_code:
        :param office_name:
        :param we_vote_id_from_master:
        :return:
        """
        office_list_objects = []
        office_list_found = False

        try:
            office_queryset = ContestOffice.objects.all()
            office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
            office_queryset = office_queryset.filter(office_name__iexact=office_name)  # Case doesn't matter
            if positive_value_exists(state_code):
                office_queryset = office_queryset.filter(state_code__iexact=state_code)  # Case doesn't matter
            # office_queryset = office_queryset.filter(district_id__exact=district_id)
            # office_queryset = office_queryset.filter(district_name__iexact=district_name)  # Case doesn't matter

            # Ignore we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                office_queryset = office_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            office_list_objects = office_queryset

            if len(office_list_objects):
                office_list_found = True
                status = 'OFFICES_RETRIEVED'
                success = True
            else:
                status = 'NO_OFFICES_RETRIEVED'
                success = True
        except ContestOffice.DoesNotExist:
            # No offices found. Not a problem.
            status = 'NO_OFFICES_FOUND_DoesNotExist'
            office_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_offices ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               state_code,
            'office_list_found':        office_list_found,
            'office_list':              office_list_objects,
        }
        return results

    def retrieve_contest_offices_from_non_unique_identifiers(
            self, contest_office_name, google_civic_election_id, incoming_state_code, district_id='', district_name='',
            ignore_office_we_vote_id_list=[]):
        keep_looking_for_duplicates = True
        success = False
        contest_office = ContestOffice()
        contest_office_found = False
        contest_office_list_filtered = []
        contest_office_list_found = False
        multiple_entries_found = False
        status = ""

        try:
            contest_office_query = ContestOffice.objects.all()
            # TODO Is there a way to filter with "dash" insensitivity? - vs --
            contest_office_query = contest_office_query.filter(office_name__iexact=contest_office_name,
                                                               state_code__iexact=incoming_state_code,
                                                               google_civic_election_id=google_civic_election_id)
            if positive_value_exists(district_id):
                contest_office_query = contest_office_query.filter(district_id=district_id)
            elif positive_value_exists(district_name):
                contest_office_query = contest_office_query.filter(district_name__iexact=district_name)

            if positive_value_exists(ignore_office_we_vote_id_list):
                contest_office_query = contest_office_query.exclude(we_vote_id__in=ignore_office_we_vote_id_list)

            contest_office_list_filtered = list(contest_office_query)
            if len(contest_office_list_filtered):
                keep_looking_for_duplicates = False
                # if a single entry matches, update that entry
                if len(contest_office_list_filtered) == 1:
                    status += 'RETRIEVE_CONTEST_OFFICES_FROM_NON_UNIQUE-SINGLE_ROW_RETRIEVED '
                    contest_office = contest_office_list_filtered[0]
                    contest_office_found = True
                    contest_office_list_found = True
                    success = True
                else:
                    # more than one entry found with a match in ContestOffice
                    contest_office_list_found = True
                    multiple_entries_found = True
                    status += 'RETRIEVE_CONTEST_OFFICES_FROM_NON_UNIQUE-MULTIPLE_ROWS_RETRIEVED '
                    success = True
            else:
                # Existing entry couldn't be found in the contest office table. We should keep looking for
                #  close matches
                success = True
        except ContestOffice.DoesNotExist:
            # Existing entry couldn't be found in the contest office table. We should keep looking for
            #  close matches
            success = True

        # Strip away common words and look for direct matches
        if keep_looking_for_duplicates:
            try:
                contest_office_query = ContestOffice.objects.all()
                contest_office_query = contest_office_query.filter(google_civic_election_id=google_civic_election_id)
                if positive_value_exists(incoming_state_code):
                    contest_office_query = contest_office_query.filter(state_code__iexact=incoming_state_code)

                if positive_value_exists(ignore_office_we_vote_id_list):
                    contest_office_query = contest_office_query.exclude(we_vote_id__in=ignore_office_we_vote_id_list)

                # Start with the contest_office_name and remove OFFICE_NAME_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES
                stripped_down_contest_office_name = contest_office_name.lower()
                for remove_this in OFFICE_NAME_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES:
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove "of State", ex/ "of California"
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " of " + state_name.lower()
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove leading state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = state_name.lower() + " "
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove trailing state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " " + state_name.lower()
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove leading and trailing spaces
                stripped_down_contest_office_name = stripped_down_contest_office_name.strip()

                contest_office_query = contest_office_query.filter(
                    office_name__icontains=stripped_down_contest_office_name)

                # icontains doesn't work when district ids are included
                contest_office_query = contest_office_query.exclude(office_name__icontains="district")

                contest_office_list = list(contest_office_query)

                contest_office_list_filtered = []
                if len(contest_office_list):
                    contest_office_list_filtered = remove_office_district_false_positives(
                        contest_office_name, contest_office_list)

                if len(contest_office_list_filtered):
                    keep_looking_for_duplicates = False
                    # if a single entry matches, update that entry
                    if len(contest_office_list_filtered) == 1:
                        status += 'RETRIEVE_CONTEST_OFFICES_FROM_NON_UNIQUE-SINGLE_ROW_RETRIEVED2 '
                        contest_office = contest_office_list_filtered[0]
                        contest_office_found = True
                        contest_office_list_found = True
                        success = True
                    else:
                        # more than one entry found with a match in ContestOffice
                        contest_office_list_found = True
                        multiple_entries_found = True
                        status += 'RETRIEVE_CONTEST_OFFICES_FROM_NON_UNIQUE-MULTIPLE_ROWS_RETRIEVED2 '
                        success = True
                else:
                    # Existing entry couldn't be found in the contest office table. We should keep looking for
                    #  close matches
                    success = True
            except ContestOffice.DoesNotExist:
                # Existing entry couldn't be found in the contest office table. We should keep looking for
                #  close matches
                success = True

        # Factor in OFFICE_NAME_EQUIVALENT_PHRASE_PAIRS
        if keep_looking_for_duplicates:
            try:
                contest_office_query = ContestOffice.objects.all()
                contest_office_query = contest_office_query.filter(
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(incoming_state_code):
                    contest_office_query = contest_office_query.filter(state_code__iexact=incoming_state_code)

                if positive_value_exists(ignore_office_we_vote_id_list):
                    contest_office_query = contest_office_query.exclude(we_vote_id__in=ignore_office_we_vote_id_list)

                # Start with the contest_office_name and remove OFFICE_NAME_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES
                stripped_down_contest_office_name = contest_office_name.lower()
                for remove_this in OFFICE_NAME_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES:
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove "of State", ex/ "of California"
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " of " + state_name.lower()
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove leading state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = state_name.lower() + " "
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove trailing state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " " + state_name.lower()
                    stripped_down_contest_office_name = stripped_down_contest_office_name.replace(remove_this, "")

                # Remove leading and trailing spaces
                stripped_down_contest_office_name = stripped_down_contest_office_name.strip()

                # Search through stripped_down_contest_office_name for OFFICE_NAME_EQUIVALENT_PHRASE_PAIRS
                filters = []
                district_found = False
                equivalent_phrase_found = False
                office_without_district_found = False
                for left_term, right_term in OFFICE_NAME_EQUIVALENT_DISTRICT_PHRASE_PAIRS.items():
                    if left_term in stripped_down_contest_office_name:
                        new_filter = Q(office_name__icontains=right_term) | Q(office_name__icontains=left_term)
                        filters.append(new_filter)
                        district_found = True
                        stripped_down_contest_office_name = stripped_down_contest_office_name.replace(left_term, "")
                        # Break out of the for loop since we only want to match to one district
                        break
                    if right_term in stripped_down_contest_office_name:
                        new_filter = Q(office_name__icontains=left_term) | Q(office_name__icontains=right_term)
                        filters.append(new_filter)
                        district_found = True
                        stripped_down_contest_office_name = stripped_down_contest_office_name.replace(right_term, "")
                        # Break out of the for loop since we only want to match to one district
                        break

                for left_term, right_term in OFFICE_NAME_EQUIVALENT_PHRASE_PAIRS.items():
                    if left_term in stripped_down_contest_office_name:
                        new_filter = Q(office_name__icontains=right_term) | Q(office_name__icontains=left_term)
                        filters.append(new_filter)
                        equivalent_phrase_found = True
                        continue
                    if right_term in stripped_down_contest_office_name:
                        new_filter = Q(office_name__icontains=left_term) | Q(office_name__icontains=right_term)
                        filters.append(new_filter)
                        equivalent_phrase_found = True
                        continue

                if district_found and not equivalent_phrase_found:
                    # Remove leading and trailing spaces
                    stripped_down_contest_office_name = stripped_down_contest_office_name.strip()
                    if positive_value_exists(stripped_down_contest_office_name):
                        new_filter = Q(office_name__icontains=stripped_down_contest_office_name)
                        filters.append(new_filter)
                        office_without_district_found = True

                if equivalent_phrase_found or office_without_district_found:
                    # Add the first query
                    final_filters = filters.pop()

                    # ...and "AND" the remaining items in the list
                    for item in filters:
                        final_filters &= item

                    contest_office_query = contest_office_query.filter(final_filters)

                    contest_office_list = list(contest_office_query)

                    contest_office_list_filtered = []
                    if len(contest_office_list):
                        contest_office_list_filtered = remove_office_district_false_positives(
                            contest_office_name, contest_office_list)

                    if len(contest_office_list_filtered):
                        keep_looking_for_duplicates = False
                        # if a single entry matches, update that entry
                        if len(contest_office_list_filtered) == 1:
                            status += 'RETRIEVE_CONTEST_OFFICES_FROM_NON_UNIQUE-SINGLE_ROW_RETRIEVED3 '
                            contest_office = contest_office_list_filtered[0]
                            contest_office_found = True
                            contest_office_list_found = True
                            success = True
                        else:
                            # more than one entry found with a match in ContestOffice
                            contest_office_list_found = True
                            multiple_entries_found = True
                            status += 'RETRIEVE_CONTEST_OFFICES_FROM_NON_UNIQUE-MULTIPLE_ROWS_RETRIEVED3 '
                            success = True
                    else:
                        # Existing entry couldn't be found in the contest office table. We should keep looking for
                        #  close matches
                        success = True
            except ContestOffice.DoesNotExist:
                # Existing entry couldn't be found in the contest office table. We should keep looking for
                #  close matches
                success = True

        # TODO To build
        # if keep_looking_for_duplicates:
        #     # Check to see if we have a BatchRowTranslationMap for the value in contest_office_name
        #     kind_of_batch = CONTEST_OFFICE
        #     batch_row_name = "contest_office_name"
        #     incoming_batch_row_value = contest_office_name
        #     mapped_value = batch_manager.fetch_batch_row_translation_map(kind_of_batch, batch_row_name,
        #                                                                  incoming_batch_row_value)
        #     if positive_value_exists(mapped_value):
        #         # Replace existing value with the
        #         contest_office_name = mapped_value
        #         contest_office_name_mapped = True
        #         kind_of_action = IMPORT_ADD_TO_EXISTING
        #         keep_looking_for_duplicates = False
        #
        # if keep_looking_for_duplicates:
        #     # Are there similar office names that we might want to map this value to?
        #     kind_of_batch = CONTEST_OFFICE
        #     batch_row_name = "contest_office_name"
        #     incoming_batch_row_value = contest_office_name
        #     office_results = batch_manager.find_possible_matches(kind_of_batch, batch_row_name,
        # incoming_batch_row_value,
        #                                                          google_civic_election_id, state_code)
        #     if office_results['possible_matches_found']:
        #         pass
        #
        #     kind_of_action = IMPORT_TO_BE_DETERMINED
        #     batch_row_action_contest_office_status += "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_CONTEST_OFFICE_CREATE "
        results = {
            'success':                      success,
            'status':                       status,
            'contest_office_found':         contest_office_found,
            'contest_office':               contest_office,
            'contest_office_list_found':    contest_office_list_found,
            'contest_office_list':          contest_office_list_filtered,
            'google_civic_election_id':     google_civic_election_id,
            'multiple_entries_found':       multiple_entries_found,
            'state_code':                   incoming_state_code,
        }
        return results


class ContestOfficesAreNotDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two contest offices as NOT duplicates
    """
    contest_office1_we_vote_id = models.CharField(
        verbose_name="first contest office we are tracking", max_length=255, null=True, unique=False)
    contest_office2_we_vote_id = models.CharField(
        verbose_name="second contest office we are tracking", max_length=255, null=True, unique=False)

    def fetch_other_office_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.contest_office1_we_vote_id:
            return self.contest_office2_we_vote_id
        elif one_we_vote_id == self.contest_office2_we_vote_id:
            return self.contest_office1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


def remove_office_district_false_positives(contest_office_name, contest_office_list):
    contest_office_list_filtered = []
    # We want to avoid matches like this:
    # U.S. House California District 1 == U.S. House California District 18
    contest_office_name_lower = contest_office_name.lower()
    if positive_value_exists(contest_office_name) and 'district' in contest_office_name_lower:
        contest_office_name_length = len(contest_office_name)
        for possible_match in contest_office_list:
            possible_match_name_length = len(possible_match.office_name)
            possible_match_office_name_lower = possible_match.office_name.lower()
            if contest_office_name_length < possible_match_name_length \
                    and 'district' in possible_match_office_name_lower:
                # If the incoming name is shorter than the final name, see if the beginning of
                # possible match is identical.
                possible_match_office_name_lower_cropped = \
                    possible_match_office_name_lower[:contest_office_name_length]
                if contest_office_name_lower == possible_match_office_name_lower_cropped:
                    # If the possible match contains the full contest_office_name, then we don't
                    # return it because it looks like we have District 1 == District 18
                    continue
            contest_office_list_filtered.append(possible_match)
    return contest_office_list_filtered
