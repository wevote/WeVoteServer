# elected_office/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_site_unique_id_prefix, fetch_next_we_vote_id_elected_office_integer
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


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
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
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
            next_local_integer = fetch_next_we_vote_id_elected_office_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "electedoffice" = tells us this is a unique id for a ElectedOffice
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

    def update_or_create_elected_office( self, google_civic_elected_office_name, ocd_division_id, elected_office_name,
                                         number_elected, state_code, district_name, contest_level0,
                                         elected_office_description):
        """
        Either update or create an elected_office entry.
        """
        exception_multiple_object_returned = False
        new_elected_office_created = False
        elected_office_on_stage = ElectedOffice()
        success = False
        status = ""
        elected_office_updated = False

        if not google_civic_elected_office_name:
            success = False
            status += 'MISSING_OFFICE_NAME '
        elif not ocd_division_id:
            success = False
            status += 'MISSING_OCD_DIVISION_ID '
        else:
            try:
                elected_office_on_stage, new_elected_office_created = ElectedOffice.objects.update_or_create(
                    google_civic_elected_office_name=google_civic_elected_office_name,
                    ocd_division_id=ocd_division_id,
                    elected_office_name=elected_office_name,
                    number_elected=number_elected,
                    state_code=state_code,
                    district_name=district_name,
                    contest_level0=contest_level0,
                    elected_office_description=elected_office_description)
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

    def retrieve_all_elected_offices_for_upcoming_election(self, google_civic_election_id=0, state_code="",
                                                           return_list_of_objects=False):
        elected_office_list = []
        return self.retrieve_elected_offices(google_civic_election_id, state_code, elected_office_list,
                                             return_list_of_objects)

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
                    'ballot_item_display_name':     elected_office.elected_office_name,
                    'measure_we_vote_id':           '',
                    'elected_office_we_vote_id':    elected_office.we_vote_id,
                    'candidate_we_vote_id':         '',
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
        :param elected_office_name:
        :param state_code:
        :param we_vote_id_from_master
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
