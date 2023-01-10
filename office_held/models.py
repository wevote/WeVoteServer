# office_held/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_site_unique_id_prefix, fetch_next_we_vote_id_office_held_integer
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


class OfficeHeld(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "officeheld", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_office_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this office held", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # The name of the office held by a representative.
    office_held_name = models.CharField(
        verbose_name="name of the office held", max_length=255, null=False, blank=False)
    office_held_name_es = models.CharField(
        verbose_name="name of the office held in Spanish", max_length=255, null=True, blank=True, default=None)
    # The offices' name as passed over by Google Civic. We save this so we can match to this office even
    # if we edit the office's name locally.
    google_civic_office_held_name = models.CharField(
        verbose_name="office_held name exactly as received from google civic", max_length=255, null=True, blank=True)
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
    state_code = models.CharField(verbose_name="state this office_held serves", max_length=2, null=True, blank=True)
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
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=36, null=True, blank=True)
    office_held_description = models.CharField(verbose_name="office_held description", max_length=255, null=True,
                                                  blank=True)
    office_held_description_es = models.CharField(verbose_name="office_held description in Spanish",
                                                     max_length=255, null=True, blank=True)
    office_held_is_partisan = models.BooleanField(verbose_name="office_held is_partisan", default=False)

    def get_office_held_state(self):
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
            next_local_integer = fetch_next_we_vote_id_office_held_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "officeheld" = tells us this is a unique id for a OfficeHeld
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}officeheld{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(OfficeHeld, self).save(*args, **kwargs)


class OfficeHeldManager(models.Manager):

    def __unicode__(self):
        return "OfficeHeldManager"

    def retrieve_office_held_from_id(self, office_held_id):
        office_held_manager = OfficeHeldManager()
        return office_held_manager.retrieve_office_held(office_held_id)

    def retrieve_office_held_from_we_vote_id(self, office_held_we_vote_id):
        office_held_id = 0
        office_held_manager = OfficeHeldManager()
        return office_held_manager.retrieve_office_held(office_held_id, office_held_we_vote_id)

    def retrieve_office_held_from_maplight_id(self, maplight_id):
        office_held_id = 0
        office_held_we_vote_id = ''
        office_held_manager = OfficeHeldManager()
        return office_held_manager.retrieve_office_held(office_held_id, office_held_we_vote_id, maplight_id)

    def fetch_office_held_id_from_maplight_id(self, maplight_id):
        office_held_id = 0
        office_held_we_vote_id = ''
        office_held_manager = OfficeHeldManager()
        results = office_held_manager.retrieve_office_held(
            office_held_id, office_held_we_vote_id, maplight_id)
        if results['success']:
            return results['office_held_id']
        return 0

    def fetch_office_held_we_vote_id_from_id(self, office_held_id):
        maplight_id = 0
        office_held_we_vote_id = ''
        office_held_manager = OfficeHeldManager()
        results = office_held_manager.retrieve_office_held(
            office_held_id, office_held_we_vote_id, maplight_id)
        if results['success']:
            return results['office_held_we_vote_id']
        return 0

    def update_or_create_office_held( self, google_civic_office_held_name, ocd_division_id, office_held_name,
                                         number_elected, state_code, district_name, contest_level0,
                                         office_held_description):
        """
        Either update or create an office_held entry.
        """
        exception_multiple_object_returned = False
        new_office_held_created = False
        office_held_on_stage = OfficeHeld()
        success = False
        status = ""
        office_held_updated = False

        if not google_civic_office_held_name:
            success = False
            status += 'MISSING_OFFICE_NAME '
        elif not ocd_division_id:
            success = False
            status += 'MISSING_OCD_DIVISION_ID '
        else:
            try:
                office_held_on_stage, new_office_held_created = OfficeHeld.objects.update_or_create(
                    google_civic_office_held_name=google_civic_office_held_name,
                    ocd_division_id=ocd_division_id,
                    office_held_name=office_held_name,
                    number_elected=number_elected,
                    state_code=state_code,
                    district_name=district_name,
                    contest_level0=contest_level0,
                    office_held_description=office_held_description)
                office_held_updated = not new_office_held_created
                success = True
                status += 'OFFICE_HELD_SAVED '
            except OfficeHeld.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_OFFICES_HELD_FOUND '
                exception_multiple_object_returned = True
            except OfficeHeld.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_HELD_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_HELD_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_office_created':       new_office_held_created,
            'contest_office':           office_held_on_stage,
            'saved':                    new_office_held_created or office_held_updated,
            'updated':                  office_held_updated,
            'not_processed':            True if not success else False,
        }
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_office_held(self, office_held_id, office_held_we_vote_id='', maplight_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        office_held_on_stage = OfficeHeld()

        try:
            if positive_value_exists(office_held_id):
                office_held_on_stage = OfficeHeld.objects.get(id=office_held_id)
                office_held_id = office_held_on_stage.id
                office_held_we_vote_id = office_held_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_HELD_FOUND_BY_ID"
            elif positive_value_exists(office_held_we_vote_id):
                office_held_on_stage = OfficeHeld.objects.get(we_vote_id=office_held_we_vote_id)
                office_held_id = office_held_on_stage.id
                office_held_we_vote_id = office_held_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_HELD_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(maplight_id):
                office_held_on_stage = OfficeHeld.objects.get(maplight_id=maplight_id)
                office_held_id = office_held_on_stage.id
                office_held_we_vote_id = office_held_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_HELD_FOUND_BY_MAPLIGHT_ID"
            else:
                status = "RETRIEVE_OFFICE_HELD_SEARCH_INDEX_MISSING"
        except OfficeHeld.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_OFFICE_HELD_MULTIPLE_OBJECTS_RETURNED"
        except OfficeHeld.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_OFFICE_HELD_NOT_FOUND"

        results = {
            'success':                      True if convert_to_int(office_held_id) > 0 else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'office_held_found':         True if convert_to_int(office_held_id) > 0 else False,
            'office_held_id':            convert_to_int(office_held_id),
            'office_held_we_vote_id':    office_held_we_vote_id,
            'office_held':               office_held_on_stage,
        }
        return results

    def fetch_office_held_id_from_we_vote_id(self, office_held_we_vote_id):
        """
        Take in office_held_we_vote_id and return internal/local-to-this-database office_held_id
        :param office_held_we_vote_id:
        :return:
        """
        office_held_id = 0
        try:
            if positive_value_exists(office_held_we_vote_id):
                office_held_on_stage = OfficeHeld.objects.get(we_vote_id=office_held_we_vote_id)
                office_held_id = office_held_on_stage.id

        except OfficeHeld.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except OfficeHeld.DoesNotExist:
            office_held_id = 0

        return office_held_id

    def create_office_held_row_entry(self, office_held_name, state_code, office_held_description, ctcl_uuid,
                                        office_held_is_partisan, google_civic_election_id, office_held_name_es='',
                                        office_held_description_es=''):
        """
        Create OfficeHeld table entry with OfficeHeld details 
        :param office_held_name: 
        :param state_code: 
        :param office_held_description: 
        :param ctcl_uuid: 
        :param office_held_is_partisan: 
        :param google_civic_election_id: 
        :param office_held_name_es: office held name in Spanish
        :param office_held_description_es: office held description in Spanish
        :return: 
        """
        success = False
        status = ""
        office_held_updated = False
        new_office_held_created = False
        new_office_held = ''

        try:
            new_office_held = OfficeHeld.objects.create(
                office_held_name=office_held_name, state_code=state_code,
                office_held_description=office_held_description, ctcl_uuid=ctcl_uuid,
                office_held_is_partisan=office_held_is_partisan,
                google_civic_election_id=google_civic_election_id,
                office_held_name_es=office_held_name_es,
                office_held_description_es=office_held_description_es)
            if new_office_held:
                success = True
                status = "OFFICE_HELD_CREATED"
                new_office_held_created = True
            else:
                success = False
                status = "OFFICE_HELD_CREATE_FAILED"
        except Exception as e:
            success = False
            new_office_held_created = False
            status = "OFFICE_HELD_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                      success,
                'status':                       status,
                'new_office_held_created':   new_office_held_created,
                'office_held_updated':       office_held_updated,
                'new_office_held':           new_office_held,
            }
        return results

    def update_office_held_row_entry(self, office_held_name, state_code, office_held_description, ctcl_uuid,
                                        office_held_is_partisan, google_civic_election_id,
                                        office_held_we_vote_id, office_held_name_es,
                                        office_held_description_es):
        """
            Update OfficeHeld table entry with matching we_vote_id 
        :param office_held_name: 
        :param state_code: 
        :param office_held_description: 
        :param ctcl_uuid: 
        :param office_held_is_partisan: 
        :param google_civic_election_id: 
        :param office_held_we_vote_id:  
        :param office_held_name_es: office held name in Spanish
        :param office_held_description_es: office held description in Spanish
        :return: 
        """
        success = False
        status = ""
        office_held_updated = False
        # new_office_held_created = False
        # new_office_held = ''
        existing_office_held_entry = ''

        try:
            existing_office_held_entry = OfficeHeld.objects.get(we_vote_id__iexact=office_held_we_vote_id)
            if existing_office_held_entry:
                # found the existing entry, update the values
                existing_office_held_entry.office_held_name = office_held_name
                existing_office_held_entry.state_code = state_code
                existing_office_held_entry.google_civic_election_id = google_civic_election_id
                existing_office_held_entry.office_held_description = office_held_description
                existing_office_held_entry.ctcl_uuid = ctcl_uuid
                existing_office_held_entry.office_held_is_partisan = office_held_is_partisan
                existing_office_held_entry.office_held_name_es = office_held_name_es
                existing_office_held_entry.office_held_description_es = office_held_description_es
                # now go ahead and save this entry (update)
                existing_office_held_entry.save()
                office_held_updated = True
                success = True
                status = "OFFICE_HELD_UPDATED"
        except Exception as e:
            success = False
            office_held_updated = False
            status = "OFFICE_HELD_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                      success,
                'status':                       status,
                'office_held_updated':       office_held_updated,
                'updated_office_held':       existing_office_held_entry,
            }
        return results


class OfficeHeldListManager(models.Manager):
    """
    This is a class to make it easy to retrieve lists of Offices
    """

    def __unicode__(self):
        return "OfficeHeldListManager"

    def retrieve_all_offices_held_for_upcoming_election(self, google_civic_election_id=0, state_code="",
                                                           return_list_of_objects=False):
        office_held_list = []
        return self.retrieve_offices_held(google_civic_election_id, state_code, office_held_list,
                                             return_list_of_objects)

    def retrieve_offices_held_by_list(self, office_list, return_list_of_objects=False):
        google_civic_election_id = 0
        state_code = ""
        return self.retrieve_offices_held(google_civic_election_id, state_code, office_list, return_list_of_objects)

    def retrieve_offices_held(self, google_civic_election_id=0, state_code="", office_held_list=[],
                                 return_list_of_objects=False):
        office_held_list_objects = []
        office_held_list_light = []
        office_held_list_found = False

        try:
            office_held_queryset = OfficeHeld.objects.all()
            if positive_value_exists(google_civic_election_id):
                office_held_queryset = office_held_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(state_code):
                office_held_queryset = office_held_queryset.filter(state_code__iexact=state_code)
            if len(office_held_list):
                office_held_queryset = office_held_queryset.filter(
                    we_vote_id__in=office_held_list)
            office_held_queryset = office_held_queryset.order_by("office_held_name")
            office_held_list_objects = office_held_queryset

            if len(office_held_list_objects):
                office_held_list_found = True
                status = 'OFFICES_HELD_RETRIEVED'
                success = True
            else:
                status = 'NO_OFFICES_HELD_RETRIEVED'
                success = True
        except OfficeHeld.DoesNotExist:
            # No entries found. Not a problem.
            status = 'NO_OFFICES_HELD_FOUND_DoesNotExist'
            office_held_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_offices_held ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if office_held_list_found:
            for office_held in office_held_list_objects:
                one_office_held = {
                    'ballot_item_display_name':     office_held.office_held_name,
                    'measure_we_vote_id':           '',
                    'office_held_we_vote_id':    office_held.we_vote_id,
                    'candidate_we_vote_id':         '',
                }
                office_held_list_light.append(one_office_held.copy())

        results = {
            'success':                      success,
            'status':                       status,
            'google_civic_election_id':     google_civic_election_id,
            'state_code':                   state_code,
            'office_held_list_found':    office_held_list_found,
            'office_held_list_objects':  office_held_list_objects if return_list_of_objects else [],
            'office_held_list_light':    office_held_list_light,
        }
        return results

    def retrieve_possible_duplicate_offices_held(self, google_civic_election_id, office_held_name, state_code,
                                                    we_vote_id_from_master=''):
        """
        Find entry that matches another entry in all critical fields other than we_vote_id_from_master
        :param google_civic_election_id:
        :param office_held_name:
        :param state_code:
        :param we_vote_id_from_master
        :return:
        """
        office_held_list_objects = []
        office_held_list_found = False

        try:
            office_held_queryset = OfficeHeld.objects.all()
            office_held_queryset = office_held_queryset.filter(google_civic_election_id=google_civic_election_id)
            office_held_queryset = office_held_queryset.filter(office_held_name__iexact=office_held_name)
            # Case doesn't matter
            if positive_value_exists(state_code):
                office_held_queryset = office_held_queryset.filter(state_code__iexact=state_code)
            # Case doesn't matter
            # office_held_queryset = office_held_queryset.filter(district_id__exact=district_id)
            # office_held_queryset = office_held_queryset.filter(district_name__iexact=district_name)
            #  Case doesn't matter

            # Ignore we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                office_held_queryset = office_held_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            office_held_list_objects = office_held_queryset

            if len(office_held_list_objects):
                office_held_list_found = True
                status = 'OFFICES_HELD_RETRIEVED'
                success = True
            else:
                status = 'NO_OFFICES_HELD_RETRIEVED'
                success = True
        except OfficeHeld.DoesNotExist:
            # No offices found. Not a problem.
            status = 'NO_OFFICES_HELD_FOUND_DoesNotExist'
            office_held_list_objects = []
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
            'office_list_found':        office_held_list_found,
            'office_list':              office_held_list_objects,
        }
        return results
