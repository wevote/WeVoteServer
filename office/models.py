# office/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_we_vote_id_last_contest_office_integer, fetch_site_unique_id_prefix, \
    fetch_next_we_vote_id_last_elected_office_integer
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


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
    # if we edit the office's name locally.
    google_civic_office_name = models.CharField(verbose_name="office name exactly as received from google civic",
                                                max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=False, blank=False)
    state_code = models.CharField(verbose_name="state this office serves", max_length=2, null=True, blank=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    maplight_id = models.CharField(
        verbose_name="maplight unique identifier", max_length=255, null=True, blank=True, unique=True)
    ballotpedia_id = models.CharField(
        verbose_name="ballotpedia unique identifier", max_length=255, null=True, blank=True)
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
            next_local_integer = fetch_next_we_vote_id_last_contest_office_integer()
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

    def retrieve_contest_office_from_maplight_id(self, maplight_id):
        contest_office_id = 0
        contest_office_we_vote_id = ''
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, contest_office_we_vote_id, maplight_id)

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
                        google_civic_election_id__exact=google_civic_election_id,
                        google_civic_office_name__iexact=office_name,
                        district_id__exact=district_id,
                        state_code__iexact=updated_contest_office_values['state_code'],
                    )
                else:
                    contest_office_on_stage = ContestOffice.objects.get(
                        google_civic_election_id__exact=google_civic_election_id,
                        google_civic_office_name__iexact=office_name,
                        state_code__iexact=updated_contest_office_values['state_code'],
                    )
                contest_office_found = True
                success = True
                status += 'CONTEST_OFFICE_SAVED '
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
                    for key, value in updated_contest_office_values.items():
                        if hasattr(contest_office_on_stage, key):
                            setattr(contest_office_on_stage, key, value)
                    contest_office_on_stage.save()
                    office_updated = True
                    new_office_created = False
                    success = True
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_CONTEST_OFFICE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    contest_office_on_stage = ContestOffice.objects.create()
                    for key, value in updated_contest_office_values.items():
                        if hasattr(contest_office_on_stage, key):
                            setattr(contest_office_on_stage, key, value)
                    contest_office_on_stage.save()
                    office_updated = False
                    new_office_created = True
                    success = True
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

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_contest_office(self, contest_office_id, contest_office_we_vote_id='', maplight_id=None):
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
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id=contest_office_we_vote_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(maplight_id):
                contest_office_on_stage = ContestOffice.objects.get(maplight_id=maplight_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_MAPLIGHT_ID"
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
                                        contest_office_number_elected, google_civic_election_id, state_code):
        """
        Create ContestOffice table entry with ContestOffice details 
        :param contest_office_name: 
        :param contest_office_votes_allowed:
        :param ctcl_uuid: 
        :param contest_office_number_elected: 
        :param google_civic_election_id: 
        :param state_code:
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
                new_contest_office_created = True
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
                'new_contest_office':           new_contest_office,
            }
        return results

    def update_contest_office_row_entry(self, contest_office_name, contest_office_votes_allowed, ctcl_uuid,
                                        contest_office_number_elected, contest_office_we_vote_id,
                                        google_civic_election_id, state_code):
        """
        Update ContestOffice table entry with matching we_vote_id 
        :param contest_office_name: 
        :param contest_office_votes_allowed:
        :param ctcl_uuid: 
        :param contest_office_number_elected:
        :param contest_office_we_vote_id:
        :param google_civic_election_id:
        :param state_code:
        :return: 
        """

        success = False
        status = ""
        contest_office_updated = False
        # new_contest_office_created = False
        # new_contest_office = ''
        existing_contest_office_entry = ''

        try:
            existing_contest_office_entry = ContestOffice.objects.get(we_vote_id__iexact=contest_office_we_vote_id)
            if existing_contest_office_entry:
                # found the existing entry, update the values
                existing_contest_office_entry.office_name = contest_office_name
                existing_contest_office_entry.number_voted_for = contest_office_votes_allowed
                existing_contest_office_entry.ctcl_uuid = ctcl_uuid
                existing_contest_office_entry.number_elected = contest_office_number_elected
                existing_contest_office_entry.google_civic_election_id = google_civic_election_id
                existing_contest_office_entry.state_code = state_code
                # now go ahead and save this entry (update)
                existing_contest_office_entry.save()
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
                'updated_contest_office':       existing_contest_office_entry,
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

    def retrieve_offices(self, google_civic_election_id=0, state_code="", office_list=[],
                         return_list_of_objects=False):
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
            self, contest_office_name, google_civic_election_id, state_code):
        keep_looking_for_duplicates = True
        success = False
        contest_office = ContestOffice()
        contest_office_found = False
        contest_office_list = []
        contest_office_list_found = False
        multiple_entries_found = False
        status = ""

        try:
            contest_office_query = ContestOffice.objects.all()
            # TODO Is there a way to filter with "dash" insensitivity? - vs --
            contest_office_query = contest_office_query.filter(office_name__iexact=contest_office_name,
                                                               state_code__iexact=state_code,
                                                               google_civic_election_id=google_civic_election_id)

            contest_office_list = list(contest_office_query)
            if len(contest_office_list):
                keep_looking_for_duplicates = False
                # if a single entry matches, update that entry
                if len(contest_office_list) == 1:
                    status += 'CREATE_BATCH_ROW_ACTION_CONTEST_OFFICE-SINGLE_ROW_RETRIEVED '
                    contest_office = contest_office_list[0]
                    contest_office_found = True
                    contest_office_list_found = True
                    success = True
                else:
                    # more than one entry found with a match in ContestOffice
                    contest_office_list_found = True
                    multiple_entries_found = True
                    status += 'CREATE_BATCH_ROW_ACTION_CONTEST_OFFICE-MULTIPLE_ROWS_RETRIEVED '
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
            'contest_office_list':          contest_office_list,
            'multiple_entries_found':       multiple_entries_found,
        }
        return results


class ElectedOffice(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "electedoff", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_office_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this elected office", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # The name of the elected office.
    elected_office_name = models.CharField(verbose_name="name of the elected office", max_length=255, null=False,
                                           blank=False)
    elected_office_name_es = models.CharField(verbose_name="name of the elected office in Spanish", max_length=255,
                                              null=True, blank=True, default=None)
    # The offices' name as passed over by Google Civic. We save this so we can match to this office even
    # if we edit the office's name locally.
    google_civic_elected_office_name = models.CharField(
        verbose_name="elected_office name exactly as received from google civic", max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=False, blank=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    state_code = models.CharField(verbose_name="state this office serves", max_length=2, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    maplight_id = models.CharField(
        verbose_name="maplight unique identifier", max_length=255, null=True, blank=True, unique=True)
    ballotpedia_id = models.CharField(
        verbose_name="ballotpedia unique identifier", max_length=255, null=True, blank=True)
    wikipedia_id = models.CharField(verbose_name="wikipedia unique identifier", max_length=255, null=True, blank=True)
    # vote_type (ranked choice, majority)
    # The number of candidates that a voter may vote for in this contest.
    # TODO check if number_voting_for is needed
    # number_voting_for = models.CharField(verbose_name="google civic number of candidates to vote for",
    #                                      max_length=255, null=True, blank=True)
    # The number of candidates that will be elected to office in this contest.
    number_elected = models.CharField(verbose_name="google civic number of candidates who will be elected",
                                      max_length=255, null=True, blank=True)

    # State code
    state_code = models.CharField(verbose_name="state this elected_office serves", max_length=2, null=True, blank=True)
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
    elected_office_description = models.CharField(verbose_name="elected_office description", max_length=255, null=True,
                                                  blank=True)
    elected_office_description_es = models.CharField(verbose_name="elected_office description in Spanish",
                                                     max_length=255, null=True, blank=True)
    elected_office_is_partisan = models.BooleanField(verbose_name="elected_office is_partisan", default=False)

    def get_elected_office_state(self):
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
            next_local_integer = fetch_next_we_vote_id_last_elected_office_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "off" = tells us this is a unique id for a ContestOffice
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}electedoffice{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ElectedOffice, self).save(*args, **kwargs)


class ElectedOfficeManager(models.Model):

    def __unicode__(self):
        return "ElectedOfficeManager"

    def retrieve_elected_office_from_id(self, elected_office_id):
        elected_office_manager = ElectedOfficeManager()
        return elected_office_manager.retrieve_elected_office(elected_office_id)

    def retrieve_elected_office_from_we_vote_id(self, elected_office_we_vote_id):
        elected_office_id = 0
        elected_office_manager = ElectedOfficeManager()
        return elected_office_manager.retrieve_elected_office(elected_office_id, elected_office_we_vote_id)

    def retrieve_elected_office_from_maplight_id(self, maplight_id):
        elected_office_id = 0
        elected_office_we_vote_id = ''
        elected_office_manager = ElectedOfficeManager()
        return elected_office_manager.retrieve_elected_office(elected_office_id, elected_office_we_vote_id, maplight_id)

    def fetch_elected_office_id_from_maplight_id(self, maplight_id):
        elected_office_id = 0
        elected_office_we_vote_id = ''
        elected_office_manager = ElectedOfficeManager()
        results = elected_office_manager.retrieve_elected_office(
            elected_office_id, elected_office_we_vote_id, maplight_id)
        if results['success']:
            return results['elected_office_id']
        return 0

    def fetch_elected_office_we_vote_id_from_id(self, elected_office_id):
        maplight_id = 0
        elected_office_we_vote_id = ''
        elected_office_manager = ElectedOfficeManager()
        results = elected_office_manager.retrieve_elected_office(
            elected_office_id, elected_office_we_vote_id, maplight_id)
        if results['success']:
            return results['elected_office_we_vote_id']
        return 0

    def update_or_create_elected_office(self, elected_office_we_vote_id, maplight_id, google_civic_election_id,
                                         elected_office_name, state_code, district_id, updated_elected_office_values):
        """
        Either update or create an elected_office entry.
        """
        exception_multiple_object_returned = False
        new_elected_office_created = False
        elected_office_on_stage = ElectedOffice()
        success = False
        status = ""
        elected_office_updated = False

        if not google_civic_election_id:
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID '
        # DALE 2016-05-10 Since we are allowing offices to be created prior to Google Civic data
        # being available, we need to remove our reliance on district_id or district_name
        # elif not (district_id or district_name):
        #     success = False
        #     status = 'MISSING_DISTRICT_ID'
        elif not elected_office_name:
            success = False
            status += 'MISSING_ELECTED_OFFICE_NAME '
        elif positive_value_exists(elected_office_we_vote_id):
            try:
                elected_office_on_stage, new_elected_office_created = ElectedOffice.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    we_vote_id__iexact=elected_office_we_vote_id,
                    defaults=updated_elected_office_values)
                elected_office_updated = not new_elected_office_created
                success = True
                status += 'ELECTED_OFFICE_SAVED '
            except ElectedOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_ELECTED_OFFICES_FOUND '
                exception_multiple_object_returned = True
            except ElectedOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_ELECTED_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_ELECTED_OFFICE_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        elif positive_value_exists(maplight_id):
            try:
                elected_office_on_stage, new_elected_office_created = ElectedOffice.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    maplight_id__exact=maplight_id,
                    defaults=updated_elected_office_values)
                elected_office_updated = not new_elected_office_created
                success = True
                status += 'ELECTED_OFFICE_SAVED '
            except ElectedOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_ELECTED_OFFICES_FOUND '
                exception_multiple_object_returned = True
            except ElectedOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_ELECTED_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_ELECTED_OFFICE_BY_MAPLIGHT_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        else:
            # Given we might have the elected_office listed by google_civic_office_name
            # OR elected_office_name, we need to check both before we try to create a new entry
            elected_office_found = False
            try:
                # TODO DALE Note that Vermont data in 2016 did not provide district_id. The unique value was in the
                # district_name. So all "VT State Senator" candidates were lumped into a single office. But I believe
                # Presidential races don't have either district_id or district_name, so we can't require one.
                # Perhaps have a special case for "district" -> "scope": "stateUpper"/"stateLower"
                # vs. "scope": "statewide"
                if positive_value_exists(district_id):
                    elected_office_on_stage = ElectedOffice.objects.get(
                        google_civic_election_id__exact=google_civic_election_id,
                        google_civic_office_name__iexact=elected_office_name,
                        district_id__exact=district_id,
                        state_code__iexact=state_code
                    )
                else:
                    elected_office_on_stage = ElectedOffice.objects.get(
                        google_civic_election_id__exact=google_civic_election_id,
                        google_civic_office_name__iexact=elected_office_name,
                        state_code__iexact=state_code
                    )
                elected_office_found = True
                success = True
                status += 'ELECTED_OFFICE_SAVED '
            except ElectedOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_ELECTED_OFFICES_FOUND_BY_GOOGLE_CIVIC_OFFICE_NAME '
                exception_multiple_object_returned = True
            except ElectedOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_ELECTED_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_ELECTED_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

            if not elected_office_found and not exception_multiple_object_returned:
                # Try to find record based on elected_office_name (instead of google_civic_office_name)
                try:
                    if positive_value_exists(district_id):
                        elected_office_on_stage = ElectedOffice.objects.get(
                            google_civic_election_id__exact=google_civic_election_id,
                            office_name__iexact=elected_office_name,
                            district_id__exact=district_id,
                            state_code__iexact=state_code
                        )
                    else:
                        elected_office_on_stage = ElectedOffice.objects.get(
                            google_civic_election_id__exact=google_civic_election_id,
                            office_name__iexact=elected_office_name,
                            state_code__iexact=state_code
                        )
                    elected_contest_office_found = True
                    success = True
                    status += 'ELECTED_OFFICE_SAVED '
                except ElectedOffice.MultipleObjectsReturned as e:
                    success = False
                    status += 'MULTIPLE_MATCHING_ELECTED_OFFICES_FOUND_BY_OFFICE_NAME '
                    exception_multiple_object_returned = True
                except ElectedOffice.DoesNotExist:
                    exception_does_not_exist = True
                    status += "RETRIEVE_ELECTED_OFFICE_NOT_FOUND "
                except Exception as e:
                    status += 'FAILED retrieve_all_elected_offices ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

            if exception_multiple_object_returned:
                # We can't proceed because there is an error with the data
                success = False
            elif elected_office_found:
                # Update record
                try:
                    for key, value in updated_elected_office_values.items():
                        if hasattr(elected_office_on_stage, key):
                            setattr(elected_office_on_stage, key, value)
                    elected_office_on_stage.save()
                    elected_office_updated = True
                    new_elected_office_created = False
                    success = True
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_ELECTED_OFFICE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    elected_office_on_stage = ElectedOffice.objects.create()
                    for key, value in updated_elected_office_values.items():
                        if hasattr(elected_office_on_stage, key):
                            setattr(elected_office_on_stage, key, value)
                    elected_office_on_stage.save()
                    elected_office_updated = False
                    new_elected_office_created = True
                    success = True
                except Exception as e:
                    status += 'FAILED_TO_CREATE_ELECTED_OFFICE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_office_created':       new_elected_office_created,
            'contest_office':           elected_office_on_stage,
            'saved':                    new_elected_office_created or elected_office_updated,
            'updated':                  elected_office_updated,
            'not_processed':            True if not success else False,
        }
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_elected_office(self, elected_office_id, elected_office_we_vote_id='', maplight_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        elected_office_on_stage = ElectedOffice()

        try:
            if positive_value_exists(elected_office_id):
                elected_office_on_stage = ElectedOffice.objects.get(id=elected_office_id)
                elected_office_id = elected_office_on_stage.id
                elected_office_we_vote_id = elected_office_on_stage.we_vote_id
                status = "RETRIEVE_ELECTED_OFFICE_FOUND_BY_ID"
            elif positive_value_exists(elected_office_we_vote_id):
                elected_office_on_stage = ElectedOffice.objects.get(we_vote_id=elected_office_we_vote_id)
                elected_office_id = elected_office_on_stage.id
                elected_office_we_vote_id = elected_office_on_stage.we_vote_id
                status = "RETRIEVE_ELECTED_OFFICE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(maplight_id):
                elected_office_on_stage = ElectedOffice.objects.get(maplight_id=maplight_id)
                elected_office_id = elected_office_on_stage.id
                elected_office_we_vote_id = elected_office_on_stage.we_vote_id
                status = "RETRIEVE_ELECTED_OFFICE_FOUND_BY_MAPLIGHT_ID"
            else:
                status = "RETRIEVE_ELECTED_OFFICE_SEARCH_INDEX_MISSING"
        except ElectedOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_ELECTED_OFFICE_MULTIPLE_OBJECTS_RETURNED"
        except ElectedOffice.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_ELECTED_OFFICE_NOT_FOUND"

        results = {
            'success':                      True if convert_to_int(elected_office_id) > 0 else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'elected_office_found':         True if convert_to_int(elected_office_id) > 0 else False,
            'elected_office_id':            convert_to_int(elected_office_id),
            'elected_office_we_vote_id':    elected_office_we_vote_id,
            'elected_office':               elected_office_on_stage,
        }
        return results

    def fetch_elected_office_id_from_we_vote_id(self, elected_office_we_vote_id):
        """
        Take in elected_office_we_vote_id and return internal/local-to-this-database elected_office_id
        :param elected_office_we_vote_id:
        :return:
        """
        elected_office_id = 0
        try:
            if positive_value_exists(elected_office_we_vote_id):
                elected_office_on_stage = ElectedOffice.objects.get(we_vote_id=elected_office_we_vote_id)
                elected_office_id = elected_office_on_stage.id

        except ElectedOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ElectedOffice.DoesNotExist:
            elected_office_id = 0

        return elected_office_id

    def create_elected_office_row_entry(self, elected_office_name, state_code, elected_office_description, ctcl_uuid,
                                        elected_office_is_partisan, google_civic_election_id, elected_office_name_es='',
                                        elected_office_description_es=''):
        """
        Create ElectedOffice table entry with ElectedOffice details 
        :param elected_office_name: 
        :param state_code: 
        :param elected_office_description: 
        :param ctcl_uuid: 
        :param elected_office_is_partisan: 
        :param google_civic_election_id: 
        :param elected_office_name_es: elected office name in Spanish
        :param elected_office_description_es: elected office description in Spanish
        :return: 
        """
        success = False
        status = ""
        elected_office_updated = False
        new_elected_office_created = False
        new_elected_office = ''

        try:
            new_elected_office = ElectedOffice.objects.create(
                elected_office_name=elected_office_name, state_code=state_code,
                elected_office_description=elected_office_description, ctcl_uuid=ctcl_uuid,
                elected_office_is_partisan=elected_office_is_partisan,
                google_civic_election_id=google_civic_election_id,
                elected_office_name_es=elected_office_name_es,
                elected_office_description_es=elected_office_description_es)
            if new_elected_office:
                success = True
                status = "ELECTED_OFFICE_CREATED"
                new_elected_office_created = True
            else:
                success = False
                status = "ELECTED_OFFICE_CREATE_FAILED"
        except Exception as e:
            success = False
            new_elected_office_created = False
            status = "ELECTED_OFFICE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                      success,
                'status':                       status,
                'new_elected_office_created':   new_elected_office_created,
                'elected_office_updated':       elected_office_updated,
                'new_elected_office':           new_elected_office,
            }
        return results

    def update_elected_office_row_entry(self, elected_office_name, state_code, elected_office_description, ctcl_uuid,
                                        elected_office_is_partisan, google_civic_election_id,
                                        elected_office_we_vote_id, elected_office_name_es,
                                        elected_office_description_es):
        """
            Update ElectedOffice table entry with matching we_vote_id 
        :param elected_office_name: 
        :param state_code: 
        :param elected_office_description: 
        :param ctcl_uuid: 
        :param elected_office_is_partisan: 
        :param google_civic_election_id: 
        :param elected_office_we_vote_id:  
        :param elected_office_name_es: elected office name in Spanish
        :param elected_office_description_es: elected office description in Spanish
        :return: 
        """
        success = False
        status = ""
        elected_office_updated = False
        # new_elected_office_created = False
        # new_elected_office = ''
        existing_elected_office_entry = ''

        try:
            existing_elected_office_entry = ElectedOffice.objects.get(we_vote_id__iexact=elected_office_we_vote_id)
            if existing_elected_office_entry:
                # found the existing entry, update the values
                existing_elected_office_entry.elected_office_name = elected_office_name
                existing_elected_office_entry.state_code = state_code
                existing_elected_office_entry.google_civic_election_id = google_civic_election_id
                existing_elected_office_entry.elected_office_description = elected_office_description
                existing_elected_office_entry.ctcl_uuid = ctcl_uuid
                existing_elected_office_entry.elected_office_is_partisan = elected_office_is_partisan
                existing_elected_office_entry.elected_office_name_es = elected_office_name_es
                existing_elected_office_entry.elected_office_description_es = elected_office_description_es
                # now go ahead and save this entry (update)
                existing_elected_office_entry.save()
                elected_office_updated = True
                success = True
                status = "ELECTED_OFFICE_UPDATED"
        except Exception as e:
            success = False
            elected_office_updated = False
            status = "ELECTED_OFFICE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                      success,
                'status':                       status,
                'elected_office_updated':       elected_office_updated,
                'updated_elected_office':       existing_elected_office_entry,
            }
        return results


class ElectedOfficeListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Offices
    """

    def __unicode__(self):
        return "ElectedOfficeListManager"

    # def retrieve_all_elected_offices_for_upcoming_election(self, google_civic_election_id=0, state_code="",
    #                                                return_list_of_objects=False):
    #     elected_office_list = []
    #     return self.retrieve_elected_offices(google_civic_election_id, state_code, elected_office_list,
    # return_list_of_objects)

    def retrieve_elected_offices_by_list(self, office_list, return_list_of_objects=False):
        google_civic_election_id = 0
        state_code = ""
        return self.retrieve_elected_offices(google_civic_election_id, state_code, office_list, return_list_of_objects)

    def retrieve_elected_offices(self, google_civic_election_id=0, state_code="", elected_office_list=[],
                                 return_list_of_objects=False):
        elected_office_list_objects = []
        elected_office_list_light = []
        elected_office_list_found = False

        try:
            elected_office_queryset = ElectedOffice.objects.all()
            if positive_value_exists(google_civic_election_id):
                elected_office_queryset = elected_office_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(state_code):
                elected_office_queryset = elected_office_queryset.filter(state_code__iexact=state_code)
            if len(elected_office_list):
                elected_office_queryset = elected_office_queryset.filter(
                    we_vote_id__in=elected_office_list)
            elected_office_queryset = elected_office_queryset.order_by("elected_office_name")
            elected_office_list_objects = elected_office_queryset

            if len(elected_office_list_objects):
                elected_office_list_found = True
                status = 'ELECTED_OFFICES_RETRIEVED'
                success = True
            else:
                status = 'NO_ELECTED_OFFICES_RETRIEVED'
                success = True
        except ElectedOffice.DoesNotExist:
            # No elected offices found. Not a problem.
            status = 'NO_ELECTED_OFFICES_FOUND_DoesNotExist'
            elected_office_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_elected_offices ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if elected_office_list_found:
            for elected_office in elected_office_list_objects:
                one_elected_office = {
                    'ballot_item_display_name': elected_office.office_name,
                    'measure_we_vote_id':       '',
                    'elected_office_we_vote_id':        elected_office.we_vote_id,
                    'candidate_we_vote_id':     '',
                }
                elected_office_list_light.append(one_elected_office.copy())

        results = {
            'success':                      success,
            'status':                       status,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   state_code,
            'elected_office_list_found':    elected_office_list_found,
            'elected_office_list_objects':  elected_office_list_objects if return_list_of_objects else [],
            'elected_office_list_light':    elected_office_list_light,
        }
        return results

    def retrieve_possible_duplicate_elected_offices(self, google_civic_election_id, elected_office_name, state_code,
                                                    we_vote_id_from_master=''):
        """
        Find elected offices that match another elected office in all critical fields other than we_vote_id_from_master
        :param google_civic_election_id:
        :return:
        """
        elected_office_list_objects = []
        elected_office_list_found = False

        try:
            elected_office_queryset = ElectedOffice.objects.all()
            elected_office_queryset = elected_office_queryset.filter(google_civic_election_id=google_civic_election_id)
            elected_office_queryset = elected_office_queryset.filter(elected_office_name__iexact=elected_office_name)
            # Case doesn't matter
            if positive_value_exists(state_code):
                elected_office_queryset = elected_office_queryset.filter(state_code__iexact=state_code)
            # Case doesn't matter
            # elected_office_queryset = elected_office_queryset.filter(district_id__exact=district_id)
            # elected_office_queryset = elected_office_queryset.filter(district_name__iexact=district_name)
            #  Case doesn't matter

            # Ignore we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                elected_office_queryset = elected_office_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            elected_office_list_objects = elected_office_queryset

            if len(elected_office_list_objects):
                elected_office_list_found = True
                status = 'ELECTED_OFFICES_RETRIEVED'
                success = True
            else:
                status = 'NO_ELECTED_OFFICES_RETRIEVED'
                success = True
        except ElectedOffice.DoesNotExist:
            # No offices found. Not a problem.
            status = 'NO_ELECTED_OFFICES_FOUND_DoesNotExist'
            elected_office_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_elected_duplicate_offices ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'office_list_found':        elected_office_list_found,
            'office_list':              elected_office_list_objects,
        }
        return results
