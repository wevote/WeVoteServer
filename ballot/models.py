# ballot/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import sys
from datetime import date, datetime

from django.db import models
from django.db.models import F, Q, Count, FloatField, ExpressionWrapper, Func
from geopy.exc import GeocoderQuotaExceeded
from geopy.geocoders import get_geocoder_for_service

import wevote_functions.admin
from candidate.models import CandidateCampaign
from config.base import get_environment_variable
from election.models import ElectionManager
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from polling_location.models import PollingLocationManager
from wevote_functions.functions import convert_to_int, extract_state_code_from_address_string, \
    positive_value_exists, STATE_CODE_MAP
from wevote_functions.functions_date import convert_date_to_date_as_integer
from wevote_settings.models import fetch_next_we_vote_id_ballot_returned_integer, fetch_site_unique_id_prefix

OFFICE = 'OFFICE'
CANDIDATE = 'CANDIDATE'
POLITICIAN = 'POLITICIAN'
MEASURE = 'MEASURE'
KIND_OF_BALLOT_ITEM_CHOICES = (
    (OFFICE,        'Office'),
    (CANDIDATE,     'Candidate'),
    (POLITICIAN,    'Politician'),
    (MEASURE,       'Measure'),
)

GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
GEOCODE_TIMEOUT = 10
RADIUS_OF_EARTH_IN_MILES = 3958.756
DEG_TO_RADS = 0.0174533
DISTANCE_LIMIT_IN_MILES = 25

logger = wevote_functions.admin.get_logger(__name__)


class Sin(Func):
    function = 'SIN'


class Cos(Func):
    function = 'COS'


class ACos(Func):
    function = 'ACOS'


class BallotItem(models.Model):
    """
    This is a generated table with ballot item data from a variety of sources, including Google Civic
    One ballot item is either 1) a measure/referendum or 2) an office that is being competed for
    """
    # The unique id of the voter for which this ballot was retrieved
    voter_id = models.IntegerField(verbose_name="the voter unique id",
                                   default=0, null=False, blank=False, db_index=True)
    # The map point for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the map point", max_length=255, default=None, null=True,
        blank=True, unique=False, db_index=True)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=20, null=False, db_index=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False)
    state_code = models.CharField(
        verbose_name="state the ballot item is related to", max_length=2, null=True, db_index=True)

    google_ballot_placement = models.BigIntegerField(
        verbose_name="the order this item should appear on the ballot", null=True, blank=True, unique=False)
    local_ballot_order = models.IntegerField(
        verbose_name="locally calculated order this item should appear on the ballot", null=True, blank=True)

    # The id for this contest office specific to this server.
    # TODO contest_office_id should be positive integer as opposed to CharField
    contest_office_id = models.CharField(verbose_name="local id for this contest office", max_length=255, null=True,
                                         blank=True)
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this office", max_length=255, default=None, null=True,
        blank=True, unique=False, db_index=True)
    # The local database id for this measure, specific to this server.
    # TODO contest_measure_id should be positive integer as opposed to CharField
    contest_measure_id = models.CharField(
        verbose_name="contest_measure unique id", max_length=255, null=True, blank=True)
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this measure", max_length=255, default=None, null=True,
        blank=True, unique=False, db_index=True)
    # This is a sortable name, either the candidate name or the measure name
    ballot_item_display_name = models.CharField(verbose_name="a label we can sort by", max_length=255, null=True,
                                                blank=True)

    measure_subtitle = models.TextField(verbose_name="google civic referendum subtitle",
                                        null=True, blank=True, default="")
    measure_text = models.TextField(verbose_name="measure text", null=True, blank=True, default="")
    measure_url = models.TextField(verbose_name='url of measure', null=True)
    yes_vote_description = models.TextField(verbose_name="what a yes vote means", null=True, blank=True, default=None)
    no_vote_description = models.TextField(verbose_name="what a no vote means", null=True, blank=True, default=None)

    def is_contest_office(self):
        if positive_value_exists(self.contest_office_id) or positive_value_exists(self.contest_office_we_vote_id):
            return True
        return False

    def is_contest_measure(self):
        if positive_value_exists(self.contest_measure_id) or positive_value_exists(self.contest_measure_we_vote_id):
            return True
        return False

    def display_ballot_item(self):
        return self.ballot_item_display_name

    @staticmethod
    def fetch_ballot_order():
        return 3

    def candidates_list(self):
        candidates_list_temp = CandidateCampaign.objects.all()
        candidates_list_temp = candidates_list_temp.filter(google_civic_election_id=self.google_civic_election_id)
        candidates_list_temp = candidates_list_temp.filter(contest_office_id=self.contest_office_id)
        return candidates_list_temp


class BallotItemManager(models.Manager):

    @staticmethod
    def remove_duplicate_ballot_item_entries(
            google_civic_election_id,
            contest_measure_id,
            contest_office_id,
            voter_id=0,
            polling_location_we_vote_id=""):
        status = ""
        success = ""
        ballot_item_found = False
        ballot_item = None

        ballot_item_list_manager = BallotItemListManager()
        # retrieve_possible_duplicate_ballot_items
        retrieve_results = ballot_item_list_manager.retrieve_ballot_item_duplicate_list(
            google_civic_election_id, contest_measure_id, contest_office_id,
            voter_id=voter_id, polling_location_we_vote_id=polling_location_we_vote_id)
        if retrieve_results['ballot_item_list_count'] == 1:
            # Only one found
            ballot_item_list = retrieve_results['ballot_item_list']
            ballot_item = ballot_item_list[0]
            ballot_item_found = True
        elif retrieve_results['ballot_item_list_count'] > 1:
            # If here, we found a duplicate
            first_one_kept = False
            ballot_item_list = retrieve_results['ballot_item_list']
            for one_ballot_item in ballot_item_list:
                if first_one_kept:
                    one_ballot_item.delete()
                else:
                    ballot_item = one_ballot_item
                    ballot_item_found = True
                    first_one_kept = True

        results = {
            "status":               status,
            "success":              success,
            "ballot_item_found":    ballot_item_found,
            "ballot_item":          ballot_item,
        }
        return results

    @staticmethod
    def refresh_cached_ballot_item_measure_info(ballot_item, contest_measure=None):
        """
        The BallotItem tables cache information from other tables. This function reaches out to the source tables
        and copies over the latest information to the BallotItem table.
        :param ballot_item:
        :param contest_measure: No need to retrieve again if passed in
        :return:
        """
        values_changed = False
        measure_found = False
        contest_measure_manager = ContestMeasureManager()
        results = {}
        if contest_measure and hasattr(contest_measure, 'measure_title'):
            measure_found = True
        elif positive_value_exists(ballot_item.contest_measure_id):
            results = contest_measure_manager.retrieve_contest_measure_from_id(ballot_item.contest_measure_id)
            measure_found = results['contest_measure_found']
            contest_measure = results['contest_measure']
        elif positive_value_exists(ballot_item.contest_measure_we_vote_id):
            results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                ballot_item.contest_measure_we_vote_id)
            measure_found = results['contest_measure_found']
            contest_measure = results['contest_measure']

        if measure_found:
            ballot_item.contest_measure_id = contest_measure.id
            ballot_item.contest_measure_we_vote_id = contest_measure.we_vote_id
            ballot_item.ballot_item_display_name = contest_measure.measure_title
            ballot_item.google_ballot_placement = contest_measure.google_ballot_placement
            ballot_item.measure_subtitle = contest_measure.measure_subtitle
            ballot_item.measure_text = contest_measure.measure_text
            ballot_item.measure_url = contest_measure.measure_url
            ballot_item.no_vote_description = contest_measure.ballotpedia_no_vote_description
            ballot_item.yes_vote_description = contest_measure.ballotpedia_yes_vote_description
            values_changed = True

        if values_changed:
            ballot_item.save()

        return ballot_item

    @staticmethod
    def refresh_cached_ballot_item_office_info(ballot_item, contest_office=None):
        """
        The BallotItem tables cache information from other tables. This function reaches out to the source tables
        and copies over the latest information to the BallotItem table.
        :param ballot_item:
        :param contest_office: No need to retrieve again if passed in
        :return:
        """
        values_changed = False
        office_found = False
        contest_office_manager = ContestOfficeManager()
        if contest_office and hasattr(contest_office, 'office_name'):
            office_found = True
        elif positive_value_exists(ballot_item.contest_office_id):
            results = contest_office_manager.retrieve_contest_office_from_id(ballot_item.contest_office_id)
            office_found = results['contest_office_found']
            contest_office = results['contest_office']
        elif positive_value_exists(ballot_item.contest_office_we_vote_id):
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
                ballot_item.contest_office_we_vote_id)
            office_found = results['contest_office_found']
            contest_office = results['contest_office']

        if office_found:
            ballot_item.contest_office_id = contest_office.id
            ballot_item.contest_office_we_vote_id = contest_office.we_vote_id
            ballot_item.ballot_item_display_name = contest_office.office_name
            ballot_item.google_ballot_placement = contest_office.google_ballot_placement
            values_changed = True

        if values_changed:
            ballot_item.save()

        return ballot_item

    @staticmethod
    def retrieve_ballot_item(ballot_item_id=0):
        status = ""
        ballot_item = BallotItem()
        try:
            if positive_value_exists(ballot_item_id):
                ballot_item = BallotItem.objects.get(id=ballot_item_id)
                if ballot_item.id:
                    ballot_item_found = True
                    status = "BALLOT_ITEM_FOUND_WITH_BALLOT_ITEM_ID "
                else:
                    ballot_item_found = False
                    status = "ELECTION_NOT_FOUND_WITH_BALLOT_ITEM_ID "
                success = True
            else:
                ballot_item_found = False
                status = "Insufficient variables included to retrieve one ballot_item."
                success = False
        except BallotItem.MultipleObjectsReturned as e:
            status += "ERROR_MORE_THAN_ONE_BALLOT_ITEM_FOUND-BY_BALLOT_ITEM "
            handle_record_found_more_than_one_exception(e, logger, exception_message_optional=status)
            ballot_item_found = False
            success = False
        except BallotItem.DoesNotExist:
            ballot_item_found = False
            status += "BALLOT_ITEM_NOT_FOUND "
            success = True

        results = {
            'success':              success,
            'status':               status,
            'ballot_item_found':    ballot_item_found,
            'ballot_item':          ballot_item,
        }
        return results

    @staticmethod
    def update_or_create_ballot_item_for_voter(
            voter_id=0,
            google_civic_election_id='',
            google_ballot_placement=None,
            ballot_item_display_name='',
            measure_subtitle='',
            measure_text='',
            local_ballot_order=0,
            contest_office_id=0,
            contest_office_we_vote_id='',
            contest_measure_id=0,
            contest_measure_we_vote_id='',
            state_code='',
            defaults={}):
        ballot_item_found = False  # At the end, does a ballot_item exist?
        ballot_item_on_stage = None
        delete_extra_ballot_item_entries = False
        exception_multiple_object_returned = False
        new_ballot_item_created = False
        status = ""
        success = True
        if contest_measure_id is not None:
            contest_measure_id = convert_to_int(contest_measure_id)
        if contest_office_id is not None:
            contest_office_id = convert_to_int(contest_office_id)
        if google_ballot_placement is not None:
            google_ballot_placement = convert_to_int(google_ballot_placement)

        # We require both contest_office_id and contest_office_we_vote_id
        #  OR both contest_measure_id and contest_measure_we_vote_id
        required_office_ids_found = positive_value_exists(contest_office_id) \
            and positive_value_exists(contest_office_we_vote_id)
        required_measure_ids_found = positive_value_exists(contest_measure_id) \
            and positive_value_exists(contest_measure_we_vote_id)
        contest_or_measure_identifier_found = required_office_ids_found or required_measure_ids_found
        if not contest_or_measure_identifier_found:
            success = False
            status += 'MISSING_SUFFICIENT_OFFICE_OR_MEASURE_IDS '
        # If here, then we know that there are sufficient office or measure ids
        elif not google_civic_election_id:
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID '
        elif not voter_id:
            success = False
            status += 'MISSING_VOTER_ID '
        else:
            try:
                # Retrieve list of ballot_items that match

                # Use get_or_create to see if a ballot item exists
                create_values = {
                    # Values we search against
                    'google_civic_election_id':     google_civic_election_id,
                    'voter_id':                     voter_id,
                    # The rest of the values
                    'contest_office_id':            contest_office_id,
                    'contest_office_we_vote_id':    contest_office_we_vote_id,
                    'contest_measure_id':           contest_measure_id,
                    'contest_measure_we_vote_id':   contest_measure_we_vote_id,
                    'google_ballot_placement':      google_ballot_placement,
                    'local_ballot_order':           local_ballot_order,
                    'ballot_item_display_name':     ballot_item_display_name,
                    'measure_subtitle':             measure_subtitle,
                    'measure_text':                 measure_text,
                    'state_code':                   state_code,
                }
                if 'measure_url' in defaults:
                    create_values['measure_url'] = defaults['measure_url']
                if 'yes_vote_description' in defaults:
                    create_values['yes_vote_description'] = defaults['yes_vote_description']
                if 'no_vote_description' in defaults:
                    create_values['no_vote_description'] = defaults['no_vote_description']

                # We search with contest_measure_id and contest_office_id because they are (will be) integers,
                #  which will be a faster search
                ballot_item_on_stage, new_ballot_item_created = BallotItem.objects.get_or_create(
                    contest_measure_id__exact=contest_measure_id,
                    contest_office_id__exact=contest_office_id,
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_id__exact=voter_id,
                    defaults=create_values)
                ballot_item_found = True
            except BallotItem.MultipleObjectsReturned as e:
                status += "UPDATE_OR_CREATE_BALLOT_ITEM-MORE_THAN_ONE_FOUND-ABOUT_TO_DELETE_DUPLICATE "
                handle_record_found_more_than_one_exception(e, logger, exception_message_optional=status)
                success = False
                delete_extra_ballot_item_entries = True
                exception_multiple_object_returned = True
            except Exception as e:
                status += "UPDATE_OR_CREATE_BALLOT_ITEM-EXCEPTION: " + str(e) + " "
                success = False

            if positive_value_exists(delete_extra_ballot_item_entries):
                success = False
                ballot_item_manager = BallotItemManager()
                results = ballot_item_manager.remove_duplicate_ballot_item_entries(
                    google_civic_election_id, contest_measure_id, contest_office_id, voter_id=voter_id)
                if results['ballot_item_found']:
                    ballot_item_found = True
                    ballot_item_on_stage = results['ballot_item']
                    success = True

            if positive_value_exists(ballot_item_found):
                try:
                    # if a ballot_item is found (instead of just created), *then* update it
                    # Note, we never update google_civic_election_id or voter_id
                    if new_ballot_item_created:
                        success = True
                        status += 'BALLOT_ITEM_CREATED '
                    else:
                        ballot_item_on_stage.contest_office_id = contest_office_id
                        ballot_item_on_stage.contest_office_we_vote_id = contest_office_we_vote_id
                        ballot_item_on_stage.contest_measure_id = contest_measure_id
                        ballot_item_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                        ballot_item_on_stage.google_ballot_placement = google_ballot_placement
                        ballot_item_on_stage.local_ballot_order = local_ballot_order
                        ballot_item_on_stage.ballot_item_display_name = ballot_item_display_name
                        ballot_item_on_stage.measure_subtitle = measure_subtitle
                        ballot_item_on_stage.measure_text = measure_text
                        if 'measure_url' in defaults:
                            measure_url = defaults['measure_url']
                            ballot_item_on_stage.measure_url = measure_url
                        if 'yes_vote_description' in defaults:
                            yes_vote_description = defaults['yes_vote_description']
                            ballot_item_on_stage.yes_vote_description = yes_vote_description
                        if 'no_vote_description' in defaults:
                            no_vote_description = defaults['no_vote_description']
                            ballot_item_on_stage.no_vote_description = no_vote_description
                        ballot_item_on_stage.save()

                        success = True
                        status += 'BALLOT_ITEM_UPDATED '

                except Exception as e:
                    status += "UPDATE_OR_CREATE_BALLOT_ITEM-BALLOT_ITEM_FOUND_UPDATE_EXCEPTION " + str(e) + " "
                    handle_record_found_more_than_one_exception(e, logger, exception_message_optional=status)
                    success = False
                    exception_multiple_object_returned = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'ballot_item_found':        ballot_item_found,
            'new_ballot_item_created':  new_ballot_item_created,
        }
        return results

    @staticmethod
    def update_or_create_ballot_item_for_polling_location(
            polling_location_we_vote_id,
            google_civic_election_id,
            google_ballot_placement,
            ballot_item_display_name,
            measure_subtitle,
            measure_text,
            local_ballot_order,
            contest_office_id=0,
            contest_office_we_vote_id='',
            contest_measure_id=0,
            contest_measure_we_vote_id='',
            state_code='',
            defaults={}):
        ballot_item_found = False  # At the end, does a ballot_item exist?
        ballot_item_on_stage = None
        delete_extra_ballot_item_entries = False
        exception_multiple_object_returned = False
        new_ballot_item_created = False
        status = ""

        # Make sure we have this polling_location
        polling_location_manager = PollingLocationManager()
        results = polling_location_manager.retrieve_polling_location_by_id(0, polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location_found = True
        else:
            polling_location_found = False

        if positive_value_exists(contest_office_we_vote_id) and not positive_value_exists(contest_office_id):
            # Look up contest_office_id
            contest_office_manager = ContestOfficeManager()
            contest_office_id = contest_office_manager.fetch_contest_office_id_from_we_vote_id(
                contest_office_we_vote_id)
        elif positive_value_exists(contest_office_id) and not positive_value_exists(contest_office_we_vote_id):
            # Look up contest_office_we_vote_id
            contest_office_manager = ContestOfficeManager()
            contest_office_we_vote_id = contest_office_manager.fetch_contest_office_we_vote_id_from_id(
                contest_office_id)

        if positive_value_exists(contest_measure_we_vote_id) and not positive_value_exists(contest_measure_id):
            # Look up contest_measure_id
            contest_measure_manager = ContestMeasureManager()
            contest_measure_id = contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(
                contest_measure_we_vote_id)
        elif positive_value_exists(contest_measure_id) and not positive_value_exists(contest_measure_we_vote_id):
            # Look up contest_measure_id
            contest_measure_manager = ContestMeasureManager()
            contest_measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(
                contest_measure_id)

        # We require both contest_office_id and contest_office_we_vote_id
        #  OR both contest_measure_id and contest_measure_we_vote_id
        required_office_ids_found = positive_value_exists(contest_office_id) \
            and positive_value_exists(contest_office_we_vote_id)
        required_measure_ids_found = positive_value_exists(contest_measure_id) \
            and positive_value_exists(contest_measure_we_vote_id)
        contest_or_measure_identifier_found = required_office_ids_found or required_measure_ids_found
        if not contest_or_measure_identifier_found:
            success = False
            status += 'MISSING_SUFFICIENT_OFFICE_OR_MEASURE_IDS-POLLING_LOCATION '
        # If here, then we know that there are sufficient office or measure ids
        elif not google_civic_election_id:
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID-POLLING_LOCATION '
        elif not polling_location_we_vote_id:
            success = False
            status += 'MISSING_POLLING_LOCATION_WE_VOTE_ID '
        #  We Vote Server doesn't have a matching map point yet.
        # elif not polling_location_found:
        #     success = False
        #     status = 'MISSING_POLLING_LOCATION_LOCALLY'
        else:
            try:
                # Use get_or_create to see if a ballot item exists
                create_values = {
                    # Values we search against
                    'google_civic_election_id':     google_civic_election_id,
                    'polling_location_we_vote_id':  polling_location_we_vote_id,
                    # The rest of the values
                    'contest_office_id':            contest_office_id,
                    'contest_office_we_vote_id':    contest_office_we_vote_id,
                    'contest_measure_id':           contest_measure_id,
                    'contest_measure_we_vote_id':   contest_measure_we_vote_id,
                    'google_ballot_placement':      google_ballot_placement,
                    'local_ballot_order':           local_ballot_order,
                    'ballot_item_display_name':     ballot_item_display_name,
                    'measure_subtitle':             measure_subtitle,
                    'measure_text':                 measure_text,
                    'state_code':                   state_code,
                }

                if 'measure_url' in defaults:
                    create_values['measure_url'] = defaults['measure_url']
                if 'yes_vote_description' in defaults:
                    create_values['yes_vote_description'] = defaults['yes_vote_description']
                if 'no_vote_description' in defaults:
                    create_values['no_vote_description'] = defaults['no_vote_description']

                # We search with contest_measure_id and contest_office_id because they are (will be) integers,
                #  which will be a faster search
                ballot_item_on_stage, new_ballot_item_created = BallotItem.objects.get_or_create(
                    contest_measure_id__exact=contest_measure_id,
                    contest_office_id__exact=contest_office_id,
                    google_civic_election_id__exact=google_civic_election_id,
                    polling_location_we_vote_id__iexact=polling_location_we_vote_id,
                    defaults=create_values)
                ballot_item_found = True
            except BallotItem.MultipleObjectsReturned as e:
                status += 'MULTIPLE_MATCHING_BALLOT_ITEMS_FOUND-POLLING_LOCATION '
                handle_record_found_more_than_one_exception(e, logger=logger, exception_message_optional=status)
                delete_extra_ballot_item_entries = True
                exception_multiple_object_returned = True

            if positive_value_exists(delete_extra_ballot_item_entries):
                ballot_item_manager = BallotItemManager()
                results = ballot_item_manager.remove_duplicate_ballot_item_entries(
                    google_civic_election_id, contest_measure_id, contest_office_id,
                    polling_location_we_vote_id=polling_location_we_vote_id)
                if results['ballot_item_found']:
                    ballot_item_found = True
                    ballot_item_on_stage = results['ballot_item']

            # if a ballot_item is found (instead of just created), *then* update it
            # Note, we never update google_civic_election_id or voter_id
            if ballot_item_found:
                try:
                    ballot_item_on_stage.contest_office_id = contest_office_id
                    ballot_item_on_stage.contest_office_we_vote_id = contest_office_we_vote_id
                    ballot_item_on_stage.contest_measure_id = contest_measure_id
                    ballot_item_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                    ballot_item_on_stage.google_ballot_placement = google_ballot_placement
                    ballot_item_on_stage.local_ballot_order = local_ballot_order
                    ballot_item_on_stage.ballot_item_display_name = ballot_item_display_name
                    ballot_item_on_stage.measure_subtitle = measure_subtitle
                    ballot_item_on_stage.measure_text = measure_text
                    ballot_item_on_stage.state_code = state_code
                    if 'measure_url' in defaults:
                        measure_url = defaults['measure_url']
                        ballot_item_on_stage.measure_url = measure_url
                    if 'yes_vote_description' in defaults:
                        yes_vote_description = defaults['yes_vote_description']
                        ballot_item_on_stage.yes_vote_description = yes_vote_description
                    if 'no_vote_description' in defaults:
                        no_vote_description = defaults['no_vote_description']
                        ballot_item_on_stage.no_vote_description = no_vote_description
                    ballot_item_on_stage.save()

                    success = True
                    status = 'BALLOT_ITEM_UPDATED-POLLING_LOCATION'

                except BallotItemManager.MultipleObjectsReturned as e:
                    handle_record_found_more_than_one_exception(e, logger=logger)
                    success = False
                    status = 'MULTIPLE_MATCHING_BALLOT_ITEMS_FOUND-POLLING_LOCATION '
                    exception_multiple_object_returned = True
            else:
                success = True
                status = 'BALLOT_ITEM_CREATED-POLLING_LOCATION'

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'ballot_item':              ballot_item_on_stage,
            'ballot_item_found':        ballot_item_found,
            'new_ballot_item_created':  new_ballot_item_created,
        }
        return results

    @staticmethod
    def create_ballot_item_row_entry(
            ballot_item_display_name,
            local_ballot_order,
            state_code,
            google_civic_election_id,
            defaults):
        """
        Create BallotItem table entry with BallotItem details
        :param ballot_item_display_name:
        :param local_ballot_order:
        :param state_code:
        :param google_civic_election_id:
        :param defaults:
        :return:
        """

        new_ballot_item_created = False
        new_ballot_item = ''
        status = ''

        try:
            if positive_value_exists(state_code):
                state_code = state_code.lower()
            new_ballot_item = BallotItem.objects.create(
                ballot_item_display_name=ballot_item_display_name,
                local_ballot_order=local_ballot_order,
                state_code=state_code,
                google_civic_election_id=google_civic_election_id)
            if new_ballot_item:
                success = True
                status += "CONTEST_OFFICE_BALLOT_ITEM_BEING_CREATED "
                new_ballot_item_created = True
                new_ballot_item.contest_office_id = defaults['contest_office_id']
                new_ballot_item.contest_office_we_vote_id = defaults['contest_office_we_vote_id']
                new_ballot_item.contest_measure_id = defaults['contest_measure_id']
                new_ballot_item.contest_measure_we_vote_id = defaults['contest_measure_we_vote_id']
                new_ballot_item.measure_subtitle = defaults['measure_subtitle']
                new_ballot_item.polling_location_we_vote_id = defaults['polling_location_we_vote_id']
                if 'measure_url' in defaults:
                    measure_url = defaults['measure_url']
                    new_ballot_item.measure_url = measure_url
                if 'yes_vote_description' in defaults:
                    yes_vote_description = defaults['yes_vote_description']
                    new_ballot_item.yes_vote_description = yes_vote_description
                if 'no_vote_description' in defaults:
                    no_vote_description = defaults['no_vote_description']
                    new_ballot_item.no_vote_description = no_vote_description
                if 'state_code' in defaults and positive_value_exists(defaults['state_code']):
                    state_code_from_defaults = defaults['state_code']
                    state_code_from_defaults = state_code_from_defaults.lower()
                    new_ballot_item.state_code = state_code_from_defaults
                new_ballot_item.save()
                status += "NEW_BALLOT_ITEM_CREATED "
            else:
                success = False
                status += "BALLOT_ITEM_CREATE_FAILED "
        except Exception as e:
            success = False
            new_ballot_item_created = False
            status += "BALLOT_ITEM_RETRIEVE_ERROR " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                      success,
                'status':                       status,
                'new_ballot_item_created':      new_ballot_item_created,
                'ballot_item':                  new_ballot_item,
            }
        return results

    @staticmethod
    def delete_ballot_item(ballot_item_id=0):
        status = ""
        ballot_item_found = False
        ballot_item_deleted = False
        try:
            if positive_value_exists(ballot_item_id):
                ballot_item = BallotItem.objects.get(id=ballot_item_id)
                if ballot_item.id:
                    ballot_item_found = True
                    ballot_item.delete()
                    ballot_item_deleted = True
                    status = "BALLOT_ITEM_FOUND_AND_DELETED_WITH_BALLOT_ITEM_ID "
                else:
                    status = "BALLOT_ITEM_NOT_FOUND_WITH_BALLOT_ITEM_ID "
                success = True
            else:
                status = "DELETE: Insufficient variables included to retrieve one ballot_item."
                success = False
        except BallotItem.MultipleObjectsReturned as e:
            status += "ERROR_MORE_THAN_ONE_BALLOT_ITEM_FOUND-BY_BALLOT_ITEM-DELETE "
            handle_record_found_more_than_one_exception(e, logger, exception_message_optional=status)
            success = False
        except BallotItem.DoesNotExist:
            status += "BALLOT_ITEM_NOT_FOUND-DELETE "
            success = True

        results = {
            'success':              success,
            'status':               status,
            'ballot_item_found':    ballot_item_found,
            'ballot_item_deleted':  ballot_item_deleted,
        }
        return results

    @staticmethod
    def refresh_all_ballot_item_measure_entries(contest_measure):
        """
        Bulk update all ballot_item entries for this measure
        """
        success = False
        status = ""
        try:
            number_of_ballot_items_updated = BallotItem.objects.filter(
                contest_measure_we_vote_id=contest_measure.we_vote_id,
            ).update(
                ballot_item_display_name=contest_measure.measure_title,
                contest_measure_id=contest_measure.id,
                measure_subtitle=contest_measure.measure_subtitle,
                measure_text=contest_measure.measure_text,
                measure_url=contest_measure.measure_url,
                no_vote_description=contest_measure.ballotpedia_no_vote_description,
                # state_code=contest_measure.state_code,
                yes_vote_description=contest_measure.ballotpedia_yes_vote_description,
            )
        except Exception as e:
            success = False
            number_of_ballot_items_updated = 0
            status += "REFRESH_ALL_BALLOT_ITEM_MEASURE_ENTRIES_ERROR " + str(e) + " "

        results = {
                'success':                          success,
                'status':                           status,
                'number_of_ballot_items_updated':   number_of_ballot_items_updated,
            }
        return results

    @staticmethod
    def refresh_all_ballot_item_office_entries(contest_office):
        """
        Bulk update all ballot_item entries for this office
        """
        success = True
        status = ""
        try:
            number_of_ballot_items_updated = BallotItem.objects.filter(
                contest_office_we_vote_id=contest_office.we_vote_id,
            ).update(
                ballot_item_display_name=contest_office.office_name,
                contest_office_id=contest_office.id,
                # state_code=contest_office.state_code,
            )
        except Exception as e:
            success = False
            number_of_ballot_items_updated = 0
            status += "REFRESH_ALL_BALLOT_ITEM_OFFICE_ENTRIES_ERROR " + str(e) + " "

        results = {
                'success':                          success,
                'status':                           status,
                'number_of_ballot_items_updated':   number_of_ballot_items_updated,
            }
        return results

    def update_ballot_item_row_entry(
            self,
            ballot_item_display_name,
            local_ballot_order,
            google_civic_election_id,
            defaults):
        """
        Update BallotItem table entry with matching we_vote_id
        :param ballot_item_display_name:
        :param local_ballot_order:
        :param google_civic_election_id:
        :param defaults:
        :return:
        """

        success = False
        status = ""
        ballot_item_found = False
        ballot_item_updated = False
        change_to_save = False
        existing_ballot_item_entry = ''
        existing_ballot_item_entry_id = 0

        try:
            # Removed the "__iexact" to gain db query speed
            if positive_value_exists(defaults['polling_location_we_vote_id']) and \
                    positive_value_exists(google_civic_election_id):
                if positive_value_exists(defaults['contest_office_we_vote_id']):
                    existing_ballot_item_entry = BallotItem.objects.using('readonly').get(
                        contest_office_we_vote_id=defaults['contest_office_we_vote_id'],
                        polling_location_we_vote_id=defaults['polling_location_we_vote_id'],
                        google_civic_election_id=google_civic_election_id)
                    ballot_item_found = True
                    existing_ballot_item_entry_id = existing_ballot_item_entry.id
                elif positive_value_exists(defaults['contest_measure_we_vote_id']):
                    existing_ballot_item_entry = BallotItem.objects.using('readonly').get(
                        contest_measure_we_vote_id=defaults['contest_measure_we_vote_id'],
                        polling_location_we_vote_id=defaults['polling_location_we_vote_id'],
                        google_civic_election_id=google_civic_election_id)
                    ballot_item_found = True
                    existing_ballot_item_entry_id = existing_ballot_item_entry.id

            if ballot_item_found and positive_value_exists(existing_ballot_item_entry_id):
                # Found an existing entry, now check for differences
                if existing_ballot_item_entry.ballot_item_display_name != ballot_item_display_name:
                    change_to_save = True
                if existing_ballot_item_entry.local_ballot_order != local_ballot_order:
                    change_to_save = True
                if existing_ballot_item_entry.contest_office_id != str(defaults['contest_office_id']):
                    change_to_save = True
                if existing_ballot_item_entry.contest_office_we_vote_id != defaults['contest_office_we_vote_id']:
                    change_to_save = True
                if existing_ballot_item_entry.contest_measure_id != str(defaults['contest_measure_id']):
                    change_to_save = True
                if existing_ballot_item_entry.contest_measure_we_vote_id != defaults['contest_measure_we_vote_id']:
                    change_to_save = True
                if existing_ballot_item_entry.measure_subtitle != defaults['measure_subtitle']:
                    change_to_save = True
                if 'measure_url' in defaults:
                    if existing_ballot_item_entry.measure_url != defaults['measure_url']:
                        change_to_save = True
                if 'yes_vote_description' in defaults:
                    if existing_ballot_item_entry.yes_vote_description != defaults['yes_vote_description']:
                        change_to_save = True
                if 'no_vote_description' in defaults:
                    if existing_ballot_item_entry.no_vote_description != defaults['no_vote_description']:
                        change_to_save = True
                if 'state_code' in defaults and positive_value_exists(defaults['state_code']):
                    state_code = defaults['state_code']
                    state_code = state_code.lower()
                    if existing_ballot_item_entry.state_code != state_code:
                        change_to_save = True
                success = True
                if change_to_save:
                    status += "BALLOT_ITEM_CHANGES_TO_SAVE "
                else:
                    status += "BALLOT_ITEM_HAS_NO_CHANGES_TO_SAVE "
        except Exception as e:
            success = False
            ballot_item_list = []
            ballot_item_list_found = False
            ballot_item_updated = False
            status += "BALLOT_ITEM_COMPARISON_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
            # Delete duplicates after the first entry
            if positive_value_exists(defaults['polling_location_we_vote_id']) and \
                    positive_value_exists(google_civic_election_id):
                if positive_value_exists(defaults['contest_office_we_vote_id']):
                    existing_ballot_item_query = BallotItem.objects.filter(
                        contest_office_we_vote_id=defaults['contest_office_we_vote_id'],
                        polling_location_we_vote_id=defaults['polling_location_we_vote_id'],
                        google_civic_election_id=google_civic_election_id)
                    ballot_item_list = list(existing_ballot_item_query)
                    ballot_item_list_found = len(ballot_item_list) > 1
                elif positive_value_exists(defaults['contest_measure_we_vote_id']):
                    existing_ballot_item_query = BallotItem.objects.filter(
                        contest_measure_we_vote_id=defaults['contest_measure_we_vote_id'],
                        polling_location_we_vote_id=defaults['polling_location_we_vote_id'],
                        google_civic_election_id=google_civic_election_id)
                    ballot_item_list = list(existing_ballot_item_query)
                    ballot_item_list_found = len(ballot_item_list) > 1
                if ballot_item_list_found:
                    ballot_item_list.pop(0)  # Remove first item, so we don't delete it
                    # Now delete all remaining duplicate entries
                    item_deleted = False
                    for ballot_item in ballot_item_list:
                        ballot_item.delete()
                        item_deleted = True
                    if item_deleted:
                        return self.update_ballot_item_row_entry(
                            ballot_item_display_name,
                            local_ballot_order,
                            google_civic_election_id,
                            defaults)

        try:
            if change_to_save and positive_value_exists(existing_ballot_item_entry_id):
                # Now retrieve an editable version from the main database
                existing_ballot_item_entry = BallotItem.objects.get(id=existing_ballot_item_entry_id)
                # Found an existing entry, now check for differences
                existing_ballot_item_entry.ballot_item_display_name = ballot_item_display_name
                existing_ballot_item_entry.local_ballot_order = local_ballot_order
                contest_office_id = defaults['contest_office_id']
                if positive_value_exists(contest_office_id):
                    existing_ballot_item_entry.contest_office_id = str(contest_office_id)
                else:
                    existing_ballot_item_entry.contest_office_id = None
                existing_ballot_item_entry.contest_office_we_vote_id = defaults['contest_office_we_vote_id']
                contest_measure_id = defaults['contest_measure_id']
                if positive_value_exists(contest_measure_id):
                    existing_ballot_item_entry.contest_measure_id = str(contest_measure_id)
                else:
                    existing_ballot_item_entry.contest_measure_id = None
                existing_ballot_item_entry.contest_measure_we_vote_id = defaults['contest_measure_we_vote_id']
                existing_ballot_item_entry.measure_subtitle = defaults['measure_subtitle']
                if 'measure_url' in defaults:
                    measure_url = defaults['measure_url']
                    existing_ballot_item_entry.measure_url = measure_url
                if 'yes_vote_description' in defaults:
                    yes_vote_description = defaults['yes_vote_description']
                    existing_ballot_item_entry.yes_vote_description = yes_vote_description
                if 'no_vote_description' in defaults:
                    no_vote_description = defaults['no_vote_description']
                    existing_ballot_item_entry.no_vote_description = no_vote_description
                if 'state_code' in defaults and positive_value_exists(defaults['state_code']):
                    state_code = defaults['state_code']
                    existing_ballot_item_entry.state_code = state_code.lower()

                # now go ahead and save this entry (update)
                existing_ballot_item_entry.save()
                ballot_item_updated = True
                success = True
                status += "BALLOT_ITEM_UPDATED "
        except Exception as e:
            success = False
            ballot_item_updated = False
            status += "BALLOT_ITEM_RETRIEVE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                   success,
                'status':                    status,
                'ballot_item_updated':       ballot_item_updated,
                'ballot_item':               existing_ballot_item_entry,
            }
        return results


class BallotItemListManager(models.Manager):
    """
    A way to work with a list of ballot_items
    """
    @staticmethod
    def delete_all_ballot_items_for_voter(voter_id, google_civic_election_id):
        ballot_item_list_deleted = False
        status = ''
        success = True
        try:
            ballot_item_queryset = BallotItem.objects.filter(voter_id=voter_id)
            if positive_value_exists(google_civic_election_id):
                ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_items_deleted_count = ballot_item_queryset.count()
            ballot_item_queryset.delete()

            ballot_item_list_deleted = True
            status += 'BALLOT_ITEMS_DELETED '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_DELETED_DoesNotExist '
            ballot_items_deleted_count = 0
        except Exception as e:
            handle_exception(e, logger=logger)
            ballot_items_deleted_count = 0
            status += 'FAILED delete_all_ballot_items_for_voter ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'voter_id':                 voter_id,
            'ballot_item_list_deleted': ballot_item_list_deleted,
            'ballot_items_deleted_count':   ballot_items_deleted_count,
        }
        return results

    @staticmethod
    def retrieve_ballot_items_for_election(google_civic_election_id, state_code=''):
        ballot_item_list = []
        ballot_item_list_found = False
        status = ''
        try:
            # We cannot use 'readonly' because the result set sometimes gets modified with .save()
            ballot_item_queryset = BallotItem.objects.all()
            ballot_item_queryset = ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                ballot_item_queryset = ballot_item_queryset.filter(state_code__iexact=state_code)
            ballot_item_list = list(ballot_item_queryset)
            success = True
            if positive_value_exists(ballot_item_list):
                ballot_item_list_found = True
                status += 'BALLOT_ITEMS_FOUND '
            else:
                status += 'NO_BALLOT_ITEMS_FOUND, not positive_value_exists '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            success = True
            status += 'NO_BALLOT_ITEMS_FOUND '
            ballot_item_list = []
        except Exception as e:
            success = False
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_items_for_election ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        results = {
            'success':                  success,
            'status':                   status,
            'ballot_item_list_found':   ballot_item_list_found,
            'ballot_item_list':         ballot_item_list,
        }
        return results

    @staticmethod
    def retrieve_ballot_items_for_election_lacking_state(google_civic_election_id, number_to_retrieve=5000):
        """

        :param google_civic_election_id:
        :param number_to_retrieve: Repairing 1000 ballot items takes about 9 seconds.
        :return:
        """
        ballot_item_list = []
        ballot_item_list_found = False
        status = ''
        try:
            ballot_item_queryset = BallotItem.objects.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_queryset = ballot_item_queryset.filter(Q(state_code=None) | Q(state_code=""))
            ballot_item_list = list(ballot_item_queryset[:number_to_retrieve])

            if positive_value_exists(ballot_item_list):
                ballot_item_list_found = True
                status += 'BALLOT_ITEMS_FOUND_WITHOUT_STATE '
            else:
                status += 'NO_BALLOT_ITEMS_WITHOUT_STATE_FOUND, not positive_value_exists '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_WITHOUT_STATE_FOUND '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_items_for_election_lacking_state ' \
                      '{error} [type: {error_type}] '.format(error=e.message, error_type=type(e))

        results = {
            'success':                  True if ballot_item_list_found else False,
            'status':                   status,
            'ballot_item_list_found':   ballot_item_list_found,
            'ballot_item_list':         ballot_item_list,
        }
        return results
    
    @staticmethod
    def count_ballot_items(google_civic_election_id, state_code=""):
        ballot_item_list_count = 0
        success = False
        status = ''
        try:
            ballot_item_queryset = BallotItem.objects.using('readonly').all()
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                ballot_item_queryset = ballot_item_queryset.filter(state_code__iexact=state_code)
            else:
                ballot_item_queryset = ballot_item_queryset.filter(Q(state_code=None) | Q(state_code=""))
            ballot_item_list_count = ballot_item_queryset.count()

            status += 'COUNT_BALLOT_ITEMS_COMPLETE '
            success = True
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_COUNT_FOUND '
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED count_ballot_items ' + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'ballot_item_list_count':   ballot_item_list_count,
        }
        return results

    @staticmethod
    def count_ballot_items_for_election_lacking_state(google_civic_election_id):
        ballot_item_list_count = 0
        success = False
        status = ''
        try:
            ballot_item_queryset = BallotItem.objects.using('readonly').all()
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_queryset = ballot_item_queryset.filter(Q(state_code=None) | Q(state_code=""))
            ballot_item_list_count = ballot_item_queryset.count()

            status += 'BALLOT_ITEMS_WITHOUT_STATE_FOUND '
            success = True
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_WITHOUT_STATE_FOUND '
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_items_for_election_lacking_state ' \
                      '{error} [type: {error_type}] '.format(error=e.message, error_type=type(e))

        results = {
            'success':                  success,
            'status':                   status,
            'ballot_item_list_count':   ballot_item_list_count,
        }
        return results

    @staticmethod
    def retrieve_all_ballot_items_for_contest_measure(measure_id, measure_we_vote_id):
        ballot_item_list = []
        ballot_item_list_found = False
        status = ''

        if not positive_value_exists(measure_id) and not positive_value_exists(measure_we_vote_id):
            status += 'VALID_MEASURE_ID_AND_MEASURE_WE_VOTE_ID_MISSING'
            results = {
                'success':                  True if ballot_item_list_found else False,
                'status':                   status,
                'measure_id':               measure_id,
                'measure_we_vote_id':       measure_we_vote_id,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list,
            }
            return results

        try:
            ballot_item_queryset = BallotItem.objects.all()
            if positive_value_exists(measure_id):
                ballot_item_queryset = ballot_item_queryset.filter(contest_measure_id=measure_id)
            elif positive_value_exists(measure_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(contest_measure_we_vote_id=measure_we_vote_id)

            ballot_item_queryset = ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_list = ballot_item_queryset

            if len(ballot_item_list):
                ballot_item_list_found = True
                status += 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_contest_measure '
            else:
                status += 'NO_BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_contest_measure '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_FOUND_DoesNotExist, retrieve_all_ballot_items_for_contest_measure '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_ballot_items_for_contest_measure ' \
                      '{error} [type: {error_type}] '.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if ballot_item_list_found else False,
            'status':                       status,
            'measure_id':                   measure_id,
            'measure_we_vote_id':           measure_we_vote_id,
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results

    @staticmethod
    def retrieve_all_ballot_items_for_contest_office(office_id, office_we_vote_id):
        ballot_item_list = []
        ballot_item_list_found = False
        status = ''

        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status += 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING '
            results = {
                'success':                  True if ballot_item_list_found else False,
                'status':                   status,
                'office_id':                office_id,
                'office_we_vote_id':        office_we_vote_id,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list,
            }
            return results

        try:
            ballot_item_queryset = BallotItem.objects.all()
            if positive_value_exists(office_id):
                ballot_item_queryset = ballot_item_queryset.filter(contest_office_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(contest_office_we_vote_id=office_we_vote_id)

            ballot_item_queryset = ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_list = ballot_item_queryset

            if len(ballot_item_list):
                ballot_item_list_found = True
                status += 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_contest_office '
            else:
                status += 'NO_BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_contest_office '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_FOUND_DoesNotExist, retrieve_all_ballot_items_for_contest_office '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_ballot_items_for_contest_office ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        results = {
            'success':                      True if ballot_item_list_found else False,
            'status':                       status,
            'office_id':                    office_id,
            'office_we_vote_id':            office_we_vote_id,
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results

    @staticmethod
    def retrieve_ballot_item_duplicate_list(
            google_civic_election_id,
            contest_measure_id,
            contest_office_id,
            voter_id=0,
            polling_location_we_vote_id=""):
        ballot_item_list = []
        ballot_item_list_count = 0
        ballot_item_list_found = False
        status = ""

        if not positive_value_exists(voter_id) and not positive_value_exists(polling_location_we_vote_id):
            status += "RETRIEVE_BALLOT_ITEM_DUPLICATE_LIST-MISSING_REQUIRED_VARIABLE "
            success = False
            results = {
                'success':                  success,
                'status':                   status,
                'ballot_item_list':         ballot_item_list,
                'ballot_item_list_count':   ballot_item_list_count,
                'ballot_item_list_found':   ballot_item_list_found,
            }
            return results

        try:
            # We cannot use 'readonly' because the result set sometimes gets modified with .save()
            ballot_item_queryset = BallotItem.objects.all()
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_queryset = ballot_item_queryset.filter(contest_measure_id=contest_measure_id)
            ballot_item_queryset = ballot_item_queryset.filter(contest_office_id=contest_office_id)
            if positive_value_exists(voter_id):
                ballot_item_queryset = ballot_item_queryset.filter(voter_id=voter_id)
            if positive_value_exists(polling_location_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(
                    polling_location_we_vote_id__iexact=polling_location_we_vote_id)

            ballot_item_list = list(ballot_item_queryset)
            ballot_item_list_count = len(ballot_item_list)
            success = True
            if positive_value_exists(ballot_item_list):
                ballot_item_list_found = True
                status += 'BALLOT_ITEM_DUPLICATE_LIST_FOUND '
            else:
                status += 'NO_BALLOT_ITEM_DUPLICATE_LIST_FOUND-EMPTY_LIST '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            success = True
            status += 'NO_BALLOT_ITEM_DUPLICATE_LIST_FOUND '
            ballot_item_list = []
        except Exception as e:
            success = False
            status += 'FAILED retrieve_ballot_item_duplicate_list ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'status':                   status,
            'ballot_item_list':         ballot_item_list,
            'ballot_item_list_count':   ballot_item_list_count,
            'ballot_item_list_found':   ballot_item_list_found,
        }
        return results

    @staticmethod
    def delete_all_ballot_items_for_contest_office(office_id, office_we_vote_id):
        ballot_items_deleted_count = 0
        status = ''

        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status += 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING '
            success = False
            results = {
                'success':                  success,
                'status':                   status,
                'office_id':                office_id,
                'office_we_vote_id':        office_we_vote_id,
                'ballot_items_deleted_count':   ballot_items_deleted_count,
            }
            return results

        try:
            ballot_item_queryset = BallotItem.objects.all()
            if positive_value_exists(office_id):
                ballot_item_queryset = ballot_item_queryset.filter(contest_office_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(contest_office_we_vote_id=office_we_vote_id)
            ballot_items_deleted_count = ballot_item_queryset.count()
            ballot_item_queryset.delete()

            status += 'BALLOT_ITEMS_DELETE, delete_all_ballot_items_for_contest_office '
            success = True
        except Exception as e:
            success = False
            ballot_items_deleted_count = 0
            handle_exception(e, logger=logger)
            status += 'FAILED delete_all_ballot_items_for_contest_office ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        results = {
            'success':                      success,
            'status':                       status,
            'office_id':                    office_id,
            'office_we_vote_id':            office_we_vote_id,
            'ballot_items_deleted_count':   ballot_items_deleted_count,
        }
        return results

    @staticmethod
    def retrieve_all_ballot_items_for_voter(
            voter_id=0,
            google_civic_election_id_list=[],
            ignore_ballot_item_order=False,
            read_only=False):
        polling_location_we_vote_id = ''
        ballot_item_list = []
        ballot_item_list_found = False
        status = ''
        success = True
        # Since the BallotItem table stores the election_id as a string, convert
        google_civic_election_id_string_list = []
        for one_id in google_civic_election_id_list:
            google_civic_election_id_string_list.append(str(one_id))
        try:
            if positive_value_exists(voter_id):
                # Intentionally not using 'readonly' here as the default
                if read_only:
                    ballot_item_queryset = BallotItem.objects.using('readonly').all()
                else:
                    ballot_item_queryset = BallotItem.objects.all()
                ballot_item_queryset = ballot_item_queryset.filter(voter_id=voter_id)
                ballot_item_queryset = ballot_item_queryset.filter(
                    google_civic_election_id__in=google_civic_election_id_string_list)
                if not positive_value_exists(ignore_ballot_item_order):
                    ballot_item_queryset = \
                        ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
                ballot_item_list = list(ballot_item_queryset)

            if len(ballot_item_list):
                ballot_item_list_found = True
                status += 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_voter '
            else:
                status += 'NO_BALLOT_ITEMS_FOUND_0 '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_FOUND_DoesNotExist '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_ballot_items_for_voter ' \
                      '{error} [type: {error_type}] '.format(error=e.message, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'google_civic_election_id_list': google_civic_election_id_list,
            'voter_id':                     voter_id,
            'polling_location_we_vote_id':  polling_location_we_vote_id,
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results

    @staticmethod
    def retrieve_all_ballot_items_for_polling_location(
            polling_location_we_vote_id='',
            google_civic_election_id_list=[],
            ignore_ballot_item_order=False,
            read_only=True):
        voter_id = 0
        ballot_item_list = []
        ballot_item_list_found = False
        status = ''
        try:
            if positive_value_exists(read_only):
                ballot_item_queryset = BallotItem.objects.using('readonly').all()
            else:
                ballot_item_queryset = BallotItem.objects.all()
            if not positive_value_exists(ignore_ballot_item_order):
                ballot_item_queryset = ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(polling_location_we_vote_id=polling_location_we_vote_id)
            if positive_value_exists(len(google_civic_election_id_list) > 0):
                ballot_item_queryset = ballot_item_queryset.filter(
                    google_civic_election_id__in=google_civic_election_id_list)
            ballot_item_list = list(ballot_item_queryset)

            if len(ballot_item_list):
                ballot_item_list_found = True
                status += 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_polling_location '
            else:
                status += 'NO_BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_polling_location '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_ITEMS_FOUND_DoesNotExist, retrieve_all_ballot_items_for_polling_location '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_ballot_items_for_polling_location ' \
                      '{error} '.format(error=str(e))

        results = {
            'success':                      True if ballot_item_list_found else False,
            'status':                       status,
            'google_civic_election_id_list': google_civic_election_id_list,
            'voter_id':                     voter_id,
            'polling_location_we_vote_id':  polling_location_we_vote_id,
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results

    @staticmethod
    def fetch_most_recent_google_civic_election_id():
        election_manager = ElectionManager()
        results = election_manager.retrieve_elections_by_date()
        if results['success']:
            election_list = results['election_list']
            for one_election in election_list:
                ballot_item_queryset = BallotItem.objects.using('readonly').all()
                ballot_item_queryset = ballot_item_queryset.filter(
                    google_civic_election_id=one_election.google_civic_election_id)
                number_found = ballot_item_queryset.count()
                if positive_value_exists(number_found):
                    # Since we are starting with the most recent election, as soon as we find
                    # any election with ballot items, we can exit.
                    return one_election.google_civic_election_id
        return 0

    @staticmethod
    def fetch_ballot_item_list_count_for_ballot_returned(
        voter_id,
        polling_location_we_vote_id,
        google_civic_election_id):
        voter_id = convert_to_int(voter_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        try:
            ballot_item_queryset = BallotItem.objects.using('readonly').all()
            if positive_value_exists(voter_id):
                ballot_item_queryset = ballot_item_queryset.filter(
                    voter_id=voter_id)
            elif positive_value_exists(polling_location_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(
                    polling_location_we_vote_id__iexact=polling_location_we_vote_id)
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            return ballot_item_queryset.count()
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            pass
        except Exception as e:
            pass

        return 0

    # def copy_ballot_items(self, ballot_returned, to_voter_id):
    #     status = ""
    #     ballot_item_list = []
    #     ballot_item_list_found = False
    #     # Get all ballot items from the reference ballot_returned
    #     if positive_value_exists(ballot_returned.polling_location_we_vote_id):
    #         retrieve_results = self.retrieve_all_ballot_items_for_polling_location(
    #             ballot_returned.polling_location_we_vote_id,
    #             ballot_returned.google_civic_election_id)
    #         status += retrieve_results['status']
    #         ballot_item_list_found = retrieve_results['ballot_item_list_found']
    #         ballot_item_list = retrieve_results['ballot_item_list']
    #     elif positive_value_exists(ballot_returned.voter_id):
    #         retrieve_results = self.retrieve_all_ballot_items_for_voter(
    #             ballot_returned.voter_id,
    #             ballot_returned.google_civic_election_id)
    #         status += retrieve_results['status']
    #         ballot_item_list_found = retrieve_results['ballot_item_list_found']
    #         ballot_item_list = retrieve_results['ballot_item_list']
    #
    #     if not ballot_item_list_found:
    #         error_results = {
    #             'ballot_returned_copied':   False,
    #             'success':                  False,
    #             'status':                   status,
    #         }
    #         return error_results
    #
    #     ballot_item_manager = BallotItemManager()
    #
    #     # This is a list of ballot items, usually from a map point, that we are copying over to a voter
    #     for one_ballot_item in ballot_item_list:
    #         defaults = {}
    #         defaults['measure_url'] = one_ballot_item.measure_url
    #         defaults['yes_vote_description'] = one_ballot_item.yes_vote_description
    #         defaults['no_vote_description'] = one_ballot_item.no_vote_description
    #
    #         create_results = ballot_item_manager.update_or_create_ballot_item_for_voter(
    #             to_voter_id,
    #             ballot_returned.google_civic_election_id,
    #             one_ballot_item.google_ballot_placement,
    #             one_ballot_item.ballot_item_display_name,
    #             one_ballot_item.measure_subtitle,
    #             one_ballot_item.measure_text,
    #             one_ballot_item.local_ballot_order,
    #             one_ballot_item.contest_office_id,
    #             one_ballot_item.contest_office_we_vote_id,
    #             one_ballot_item.contest_measure_id,
    #             one_ballot_item.contest_measure_we_vote_id,
    #             one_ballot_item.state_code,
    #             defaults)
    #         if not create_results['success']:
    #             status += create_results['status']
    #
    #     results = {
    #         'ballot_returned_copied':   True,
    #         'success':                  True,
    #         'status':                   status,
    #     }
    #     return results

    def refresh_ballot_items_from_master_tables(self, voter_id, google_civic_election_id,
                                                offices_dict={}, measures_dict={}):
        """

        :param voter_id:
        :param google_civic_election_id:
        :param offices_dict: # key is office_we_vote_id, value is the office object
        :param measures_dict: # key is measure_we_vote_id, value is the measure object
        :return:
        """
        status = ""
        if not positive_value_exists(voter_id) or not positive_value_exists(google_civic_election_id):
            status += "REFRESH_BALLOT_ITEMS_FROM_MASTER_TABLES-MISSING_VOTER_OR_ELECTION "
            error_results = {
                'success':                  False,
                'status':                   status,
                'offices_dict':             offices_dict,
                'measures_dict':            measures_dict,
            }
            return error_results

        # Get all ballot items for this voter
        google_civic_election_id_list = [google_civic_election_id]
        retrieve_results = self.retrieve_all_ballot_items_for_voter(
            voter_id=voter_id,
            google_civic_election_id_list=google_civic_election_id_list)
        status += retrieve_results['status']
        ballot_item_list_found = retrieve_results['ballot_item_list_found']
        ballot_item_list = retrieve_results['ballot_item_list']

        if not ballot_item_list_found:
            error_results = {
                'success':                  False,
                'status':                   status,
                'offices_dict':             offices_dict,
                'measures_dict':            measures_dict,
            }
            return error_results

        ballot_item_manager = BallotItemManager()
        measure_manager = ContestMeasureManager()
        office_manager = ContestOfficeManager()
        measures_not_found = []
        offices_not_found = []
        for one_ballot_item in ballot_item_list:
            defaults = {}
            google_ballot_placement = one_ballot_item.google_ballot_placement
            ballot_item_display_name = one_ballot_item.ballot_item_display_name
            measure_subtitle = one_ballot_item.measure_subtitle
            measure_text = one_ballot_item.measure_text
            if positive_value_exists(one_ballot_item.contest_measure_we_vote_id):
                measure_found = False
                if one_ballot_item.contest_measure_we_vote_id in measures_dict:
                    measure = measures_dict[one_ballot_item.contest_measure_we_vote_id]
                    measure_found = True
                else:
                    if one_ballot_item.contest_measure_we_vote_id not in measures_not_found:
                        results = measure_manager.retrieve_contest_measure_from_we_vote_id(
                            one_ballot_item.contest_measure_we_vote_id)
                        if results['contest_measure_found']:
                            measure = results['contest_measure']
                            measures_dict[measure.we_vote_id] = measure
                            measure_found = True
                        else:
                            measures_not_found.append(one_ballot_item.contest_measure_we_vote_id)

                if measure_found:
                    defaults['measure_url'] = measure.get_measure_url()
                    defaults['yes_vote_description'] = measure.ballotpedia_yes_vote_description
                    defaults['no_vote_description'] = measure.ballotpedia_no_vote_description
                    google_ballot_placement = measure.google_ballot_placement
                    ballot_item_display_name = measure.measure_title
                    measure_subtitle = measure.measure_subtitle
                    measure_text = measure.measure_text
            elif positive_value_exists(one_ballot_item.contest_office_we_vote_id):
                office_found = False
                if one_ballot_item.contest_office_we_vote_id in offices_dict:
                    office = offices_dict[one_ballot_item.contest_office_we_vote_id]
                    office_found = True
                else:
                    if one_ballot_item.contest_office_we_vote_id not in offices_not_found:
                        results = office_manager.retrieve_contest_office_from_we_vote_id(
                            one_ballot_item.contest_office_we_vote_id)
                        if results['contest_office_found']:
                            office = results['contest_office']
                            offices_dict[office.we_vote_id] = office
                            office_found = True
                        else:
                            offices_not_found.append(one_ballot_item.contest_office_we_vote_id)

                if office_found:
                    google_ballot_placement = office.google_ballot_placement
                    ballot_item_display_name = office.office_name

            create_results = ballot_item_manager.update_or_create_ballot_item_for_voter(
                voter_id, google_civic_election_id, google_ballot_placement,
                ballot_item_display_name, measure_subtitle,
                measure_text,
                one_ballot_item.local_ballot_order,
                one_ballot_item.contest_office_id, one_ballot_item.contest_office_we_vote_id,
                one_ballot_item.contest_measure_id, one_ballot_item.contest_measure_we_vote_id,
                one_ballot_item.state_code, defaults)
            if not create_results['success']:
                status += create_results['status']

        results = {
            'success':                  True,
            'status':                   status,
            'offices_dict':             offices_dict,
            'measures_dict':            measures_dict,
        }
        return results

    @staticmethod
    def retrieve_possible_duplicate_ballot_items(
            ballot_item_display_name,
            google_civic_election_id,
            polling_location_we_vote_id,
            voter_id,
            contest_office_we_vote_id,
            contest_measure_we_vote_id,
            state_code):
        ballot_item_list_objects = []
        ballot_item_list_found = False
        ballot_item_list_count = 0
        status = ''

        if not positive_value_exists(google_civic_election_id):
            # We must have a google_civic_election_id
            results = {
                'success':                  False,
                'status':                   "MISSING_GOOGLE_CIVIC_ELECTION_ID ",
                'google_civic_election_id': google_civic_election_id,
                'ballot_item_list_count':   ballot_item_list_count,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list_objects,
            }
            return results
        elif not positive_value_exists(polling_location_we_vote_id) \
                and not positive_value_exists(voter_id):
            # We must have a polling_location_we_vote_id to look up
            results = {
                'success':                  False,
                'status':                   "MISSING_POLLING_LOCATION_WE_VOTE_ID_AND_VOTER_ID ",
                'google_civic_election_id': google_civic_election_id,
                'ballot_item_list_count':   ballot_item_list_count,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list_objects,
            }
            return results
        elif not positive_value_exists(ballot_item_display_name) \
                and not positive_value_exists(contest_office_we_vote_id) \
                and not positive_value_exists(contest_measure_we_vote_id):
            # We must have at least one of these
            results = {
                'success':                  False,
                'status':                   "MISSING_MEASURE_AND_OFFICE_WE_VOTE_ID",
                'google_civic_election_id': google_civic_election_id,
                'ballot_item_list_count':   ballot_item_list_count,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list_objects,
            }
            return results

        try:
            ballot_item_queryset = BallotItem.objects.all()
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(polling_location_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(
                    polling_location_we_vote_id__iexact=polling_location_we_vote_id)
            else:
                ballot_item_queryset = ballot_item_queryset.filter(
                    voter_id=voter_id)
            if positive_value_exists(state_code):
                ballot_item_queryset = ballot_item_queryset.filter(state_code__iexact=state_code)

            # We want to find candidates with *any* of these values
            if positive_value_exists(ballot_item_display_name):
                ballot_item_queryset = ballot_item_queryset.filter(
                    ballot_item_display_name__iexact=ballot_item_display_name)
                if positive_value_exists(contest_office_we_vote_id):
                    # Ignore entries with contest_office_we_vote_id coming in from master server
                    ballot_item_queryset = ballot_item_queryset.filter(~Q(
                        contest_office_we_vote_id__iexact=contest_office_we_vote_id))
                elif positive_value_exists(contest_measure_we_vote_id):
                    # Ignore entries with contest_measure_we_vote_id coming in from master server
                    ballot_item_queryset = ballot_item_queryset.filter(~Q(
                        contest_measure_we_vote_id__iexact=contest_measure_we_vote_id))
            elif positive_value_exists(contest_office_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(
                    contest_office_we_vote_id__iexact=contest_office_we_vote_id)
            elif positive_value_exists(contest_measure_we_vote_id):
                ballot_item_queryset = ballot_item_queryset.filter(
                    contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)

            ballot_item_list_objects = list(ballot_item_queryset)
            ballot_item_list_count = len(ballot_item_list_objects)

            if ballot_item_list_count:
                ballot_item_list_found = True
                status += 'DUPLICATE_BALLOT_ITEMS_RETRIEVED '
                success = True
            else:
                status += 'NO_DUPLICATE_BALLOT_ITEMS_RETRIEVED '
                success = True
        except BallotItem.DoesNotExist:
            # No ballot_items found. Not a problem.
            status += 'NO_DUPLICATE_BALLOT_ITEMS_FOUND_DoesNotExist '
            ballot_item_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_possible_duplicate_ballot_items ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'ballot_item_list_count':   ballot_item_list_count,
            'ballot_item_list_found':   ballot_item_list_found,
            'ballot_item_list':         ballot_item_list_objects,
        }
        return results


class BallotReturned(models.Model):
    """
    This is a generated table with a summary of address + election combinations returned ballot data
    """
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True,
        blank=True, unique=True)

    # Either voter_id or polling_location_we_vote_id will be set, but not both.
    # The unique id of the voter for which this ballot was retrieved.
    voter_id = models.IntegerField(verbose_name="the voter unique id", null=True, blank=True)
    # The map point for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the map point", max_length=255, default=None, null=True,
        blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, db_index=True)
    # state_code = models.CharField(verbose_name="state the ballot item is related to", max_length=2, null=True)

    election_description_text = models.CharField(max_length=255, blank=False, null=False,
                                                 verbose_name='text label for this election')
    election_date = models.DateField(verbose_name='election start date', null=True, auto_now=False)

    # Should we show this ballot as an option for this election?
    ballot_location_display_option_on = models.BooleanField(default=False, db_index=True)
    ballot_location_display_name = models.CharField(verbose_name='name that shows in button',
                                                    max_length=255, blank=True, null=True, db_index=True)
    ballot_location_shortcut = models.CharField(verbose_name='the url string to find this location',
                                                max_length=255, blank=True, null=True)
    ballot_location_order = models.PositiveIntegerField(
        verbose_name="order of these ballot locations in display", default=0, null=False)

    text_for_map_search = models.CharField(max_length=255, blank=False, null=False, verbose_name='address as entered')

    latitude = models.FloatField(null=True, verbose_name='latitude returned from Google')
    longitude = models.FloatField(null=True, verbose_name='longitude returned from Google')
    state_code = models.CharField(
        verbose_name="state code returned or calculated", max_length=2, null=True, db_index=True)

    normalized_line1 = models.CharField(max_length=255, blank=True, null=True,
                                        verbose_name='normalized address line 1 returned from Google')
    normalized_line2 = models.CharField(max_length=255, blank=True, null=True,
                                        verbose_name='normalized address line 2 returned from Google')
    normalized_city = models.CharField(max_length=255, blank=True, null=True,
                                       verbose_name='normalized city returned from Google')
    normalized_state = models.CharField(max_length=255, blank=True, null=True,
                                        verbose_name='normalized state returned from Google')
    normalized_zip = models.CharField(max_length=255, blank=True, null=True,
                                      verbose_name='normalized zip returned from Google')

    date_last_updated = models.DateTimeField(
        verbose_name='date ballot items last retrieved', auto_now=True, db_index=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this voter_guide came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            self.generate_new_we_vote_id()
        super(BallotReturned, self).save(*args, **kwargs)

    def generate_new_we_vote_id(self):
        # ...generate a new id
        site_unique_id_prefix = fetch_site_unique_id_prefix()
        next_local_integer = fetch_next_we_vote_id_ballot_returned_integer()
        # "wv" = We Vote
        # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
        # "ballot" = tells us this is a unique id for a ballot_returned entry
        # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
        self.we_vote_id = "wv{site_unique_id_prefix}ballot{next_integer}".format(
            site_unique_id_prefix=site_unique_id_prefix,
            next_integer=next_local_integer,
        )
        # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        return

    def election_day_text(self):
        if isinstance(self.election_date, date):
            # Consider using:  and isinstance(self.election_date, str)
            return self.election_date.strftime('%Y-%m-%d')
        else:
            return ""


class BallotReturnedEmpty(models.Model):
    """
    This keeps track of polling locations we asked for a ballot for, but it came back empty
    """
    # The map point for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the map point", max_length=255, default=None, null=True,
        blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, db_index=True)
    is_from_ctcl = models.BooleanField(default=False)  # The ballot was returned empty from CTCL
    is_from_vote_usa = models.BooleanField(default=False)  # The ballot was returned empty from Vote USA

    # latitude = models.FloatField(null=True, verbose_name='latitude returned from Google')
    # longitude = models.FloatField(null=True, verbose_name='longitude returned from Google')
    state_code = models.CharField(
        verbose_name="state code returned or calculated", max_length=2, null=True, db_index=True)

    date_last_updated = models.DateTimeField(
        verbose_name='date ballot items last retrieved', auto_now=True, db_index=True)


class BallotReturnedManager(models.Manager):
    """
    Scenario where we get an incomplete address and Google Civic can't find it:
    1. A voter enters an address into text_for_map_search.
    2. Try to get ballot from Google Civic, if no response found...
    3. We search for the closest address for this election in the ballot_returned table.
    4. We find the closest address.
    5. We then assemble the ballot from the ballot items table so we can offer that to the new voter.
    6. Copy these ballot items over to this new voter

    New ballot comes in and we want to cache it:
    1. Search by voter_id (or polling_location_we_vote_id) + google_civic_election_id to see if have an entry
    2. If so, update it. If not...
    3. Save a new entry and attach it to either voter_id or polling_location_we_vote_id.
    NOTE: I think it will be faster to just always save an entry at an address on the chance there are some
      duplicates, instead of burning the db cycles to search for an existing entry
    """

    def __unicode__(self):
        return "BallotReturnedManager"

    @staticmethod
    def remove_duplicate_ballot_returned_entries(
            google_civic_election_id,
            polling_location_we_vote_id,
            voter_id):
        status = ""
        success = ""
        ballot_returned_found = False
        ballot_returned = None

        ballot_returned_list_manager = BallotReturnedListManager()
        retrieve_results = ballot_returned_list_manager.retrieve_ballot_returned_duplicate_list(
            google_civic_election_id, polling_location_we_vote_id, voter_id)
        if retrieve_results['ballot_returned_list_count'] == 1:
            # Only one found
            ballot_returned_list = retrieve_results['ballot_returned_list']
            ballot_returned = ballot_returned_list[0]
            ballot_returned_found = True
        elif retrieve_results['ballot_returned_list_count'] > 1:
            # If here, we found a duplicate
            first_one_kept = False
            ballot_returned_list = retrieve_results['ballot_returned_list']
            for one_ballot_returned in ballot_returned_list:
                if first_one_kept:
                    one_ballot_returned.delete()
                else:
                    ballot_returned = one_ballot_returned
                    ballot_returned_found = True
                    first_one_kept = True

        results = {
            "status":                   status,
            "success":                  success,
            "ballot_returned_found":    ballot_returned_found,
            "ballot_returned":          ballot_returned,
        }
        return results

    @staticmethod
    def retrieve_ballot_returned_from_google_civic_election_id(google_civic_election_id):
        ballot_returned_id = 0
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id, google_civic_election_id)
    
    @staticmethod
    def retrieve_ballot_returned_from_voter_id(voter_id, google_civic_election_id):
        ballot_returned_id = 0
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(
            ballot_returned_id,
            google_civic_election_id,
            voter_id)

    @staticmethod
    def retrieve_ballot_returned_from_polling_location_we_vote_id(
        polling_location_we_vote_id,
        google_civic_election_id):
        ballot_returned_id = 0
        voter_id = 0
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id, google_civic_election_id, voter_id, polling_location_we_vote_id)
    
    @staticmethod
    def retrieve_ballot_returned_from_ballot_returned_we_vote_id(ballot_returned_we_vote_id):
        ballot_returned_id = 0
        google_civic_election_id = 0
        voter_id = 0
        polling_location_we_vote_id = ''
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(
            ballot_returned_id, google_civic_election_id, voter_id, polling_location_we_vote_id,
            ballot_returned_we_vote_id)

    @staticmethod
    def retrieve_ballot_returned_from_ballot_location_shortcut(ballot_location_shortcut):
        ballot_returned_id = 0
        google_civic_election_id = 0
        voter_id = 0
        polling_location_we_vote_id = ''
        ballot_returned_we_vote_id = ''
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(
            ballot_returned_id, google_civic_election_id, voter_id, polling_location_we_vote_id,
            ballot_returned_we_vote_id, ballot_location_shortcut)

    @staticmethod
    def retrieve_existing_ballot_returned_by_identifier(
            ballot_returned_id=0,
            google_civic_election_id=0,
            voter_id=0,
            polling_location_we_vote_id='',
            ballot_returned_we_vote_id='',
            ballot_location_shortcut=''):
        """
        Search by voter_id (or polling_location_we_vote_id) + google_civic_election_id to see if have an entry
        :param ballot_returned_id:
        :param google_civic_election_id:
        :param voter_id:
        :param polling_location_we_vote_id:
        :param ballot_returned_we_vote_id:
        :param ballot_location_shortcut:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        ballot_returned_found = False
        ballot_returned = BallotReturned()
        status = ''

        try:
            if positive_value_exists(ballot_returned_id):
                ballot_returned = BallotReturned.objects.get(id=ballot_returned_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status += "BALLOT_RETURNED_FOUND_FROM_VOTER_ID "
            elif positive_value_exists(ballot_returned_we_vote_id):
                ballot_returned = BallotReturned.objects.get(we_vote_id__iexact=ballot_returned_we_vote_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status += "BALLOT_RETURNED_FOUND_FROM_BALLOT_RETURNED_WE_VOTE_ID "
            elif positive_value_exists(ballot_location_shortcut):
                ballot_returned = BallotReturned.objects.get(
                    ballot_location_shortcut=ballot_location_shortcut)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status += "BALLOT_RETURNED_FOUND_FROM_BALLOT_RETURNED_LOCATION_SHORTCUT "
            elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.get(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status += "BALLOT_RETURNED_FOUND_FROM_VOTER_ID "
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.get(
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status += "BALLOT_RETURNED_FOUND_FROM_POLLING_LOCATION_WE_VOTE_ID "
            elif positive_value_exists(google_civic_election_id):
                ballot_returned_query = BallotReturned.objects.filter(google_civic_election_id=google_civic_election_id)
                ballot_returned_query = ballot_returned_query.filter(Q(voter_id__isnull=True) | Q(voter_id=0))
                ballot_returned_query = ballot_returned_query.order_by("-ballot_location_shortcut")
                ballot_returned = ballot_returned_query.first()
                if ballot_returned and hasattr(ballot_returned, "id"):
                    # If still here, we found an existing ballot_returned
                    ballot_returned_id = ballot_returned.id
                    ballot_returned_we_vote_id = ballot_returned.we_vote_id
                    ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                    success = True
                    status += "BALLOT_RETURNED_FOUND_FROM_GOOGLE_CIVIC_ELECTION_ID " \
                              "" + str(ballot_returned_we_vote_id) + ' '
                else:
                    ballot_returned_found = False
                    success = True
                    status += "BALLOT_RETURNED_NOT_FOUND_FROM_GOOGLE_CIVIC_ELECTION_ID "
            else:
                ballot_returned_found = False
                success = False
                status += "COULD_NOT_RETRIEVE_BALLOT_RETURNED-MISSING_VARIABLES "

        except BallotReturned.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            success = False
            status += "MULTIPLE_BALLOT_RETURNED-MUST_DELETE_ALL "
        except BallotReturned.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "BALLOT_RETURNED_NOT_FOUND "
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_BALLOT_RETURNED-EXCEPTION: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'ballot_returned_found':    ballot_returned_found,
            'ballot_returned':          ballot_returned,
        }
        return results

    @staticmethod
    def delete_ballot_returned_by_identifier(
            ballot_returned_id=0,
            google_civic_election_id=0,
            voter_id=0,
            polling_location_we_vote_id='',
            ballot_returned_we_vote_id='',
            ballot_location_shortcut=''):
        """
        :param ballot_returned_id:
        :param google_civic_election_id:
        :param voter_id:
        :param polling_location_we_vote_id:
        :param ballot_returned_we_vote_id:
        :param ballot_location_shortcut:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        ballot_deleted = False
        ballot_deleted_count = 0
        status = ''
        success = True

        try:
            if positive_value_exists(ballot_returned_id):
                ballot_deleted_count, details = BallotReturned.objects.get(id=ballot_returned_id).delete()
                ballot_deleted = positive_value_exists(ballot_deleted_count)
                status += "BALLOT_RETURNED_FOUND_FROM_VOTER_ID "
            elif positive_value_exists(ballot_returned_we_vote_id):
                ballot_deleted_count, details = BallotReturned.objects.get(
                    we_vote_id__iexact=ballot_returned_we_vote_id).delete()
                ballot_deleted = positive_value_exists(ballot_deleted_count)
                status += "BALLOT_RETURNED_FOUND_FROM_BALLOT_RETURNED_WE_VOTE_ID "
            elif positive_value_exists(ballot_location_shortcut):
                ballot_deleted_count, details = BallotReturned.objects.get(
                    ballot_location_shortcut=ballot_location_shortcut).delete()
                ballot_deleted = positive_value_exists(ballot_deleted_count)
                status += "BALLOT_RETURNED_FOUND_FROM_BALLOT_RETURNED_LOCATION_SHORTCUT "
            elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                ballot_deleted_count, details = BallotReturned.objects.get(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id).delete()
                ballot_deleted = positive_value_exists(ballot_deleted_count)
                status += "BALLOT_RETURNED_FOUND_FROM_VOTER_ID "
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                ballot_deleted_count, details = BallotReturned.objects.get(
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    google_civic_election_id=google_civic_election_id).delete()
                ballot_deleted = positive_value_exists(ballot_deleted_count)
                status += "BALLOT_RETURNED_FOUND_FROM_POLLING_LOCATION_WE_VOTE_ID "
            elif positive_value_exists(google_civic_election_id):
                ballot_deleted_count, details = \
                    BallotReturned.objects.filter(google_civic_election_id=google_civic_election_id).delete()
                ballot_deleted = positive_value_exists(ballot_deleted_count)
            else:
                ballot_deleted = False
                success = False
                status += "COULD_NOT_RETRIEVE_BALLOT_RETURNED-MISSING_VARIABLES "

        except BallotReturned.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            success = False
            status += "MULTIPLE_BALLOT_RETURNED-MUST_DELETE_ALL " + str(e) + " "
        except BallotReturned.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "BALLOT_RETURNED_NOT_FOUND "
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_BALLOT_RETURNED-EXCEPTION " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'ballot_deleted':           ballot_deleted,
            'ballot_deleted_count':     ballot_deleted_count,
        }
        return results

    @staticmethod
    def create_ballot_returned_with_normalized_values(
            google_civic_address_dict,
            election_day_text,
            election_description_text,
            google_civic_election_id,
            voter_id=0,
            polling_location_we_vote_id='',
            latitude='',
            longitude=''):
        status = ''
        # Protect against ever saving test elections in the BallotReturned table
        if positive_value_exists(google_civic_election_id) and convert_to_int(google_civic_election_id) == 2000:
            results = {
                'status':                   "CHOSE_TO_NOT_SAVE_BALLOT_RETURNED_FOR_TEST_ELECTION",
                'success':                  True,
                'ballot_returned':          None,
                'ballot_returned_found':    False,
            }
            return results

        # We assume that we tried to find an entry for this voter or polling_location
        try:
            ballot_returned_id = 0
            if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.create(google_civic_election_id=google_civic_election_id,
                                                                voter_id=voter_id,
                                                                election_date=election_day_text,
                                                                election_description_text=election_description_text)
                ballot_returned_id = ballot_returned.id
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.create(google_civic_election_id=google_civic_election_id,
                                                                polling_location_we_vote_id=polling_location_we_vote_id,
                                                                election_date=election_day_text,
                                                                election_description_text=election_description_text)
                ballot_returned_id = ballot_returned.id
            else:
                ballot_returned = None
            if positive_value_exists(ballot_returned_id):
                text_for_map_search = ''
                if 'line1' in google_civic_address_dict:
                    ballot_returned.normalized_line1 = google_civic_address_dict['line1']
                    text_for_map_search += ballot_returned.normalized_line1 + ", "
                if 'line2' in google_civic_address_dict:
                    ballot_returned.normalized_line2 = google_civic_address_dict['line2']
                    text_for_map_search += ballot_returned.normalized_line2 + ", "
                ballot_returned.normalized_city = google_civic_address_dict['city']
                text_for_map_search += ballot_returned.normalized_city + ", "
                ballot_returned.normalized_state = google_civic_address_dict['state']
                text_for_map_search += ballot_returned.normalized_state + " "
                if 'zip' in google_civic_address_dict:
                    ballot_returned.normalized_zip = google_civic_address_dict['zip']
                    text_for_map_search += ballot_returned.normalized_zip
                if latitude or longitude:
                    ballot_returned.latitude = latitude
                    ballot_returned.longitude = longitude

                ballot_returned.text_for_map_search = text_for_map_search

                ballot_returned.save()
                status += "SAVED_BALLOT_RETURNED_WITH_NORMALIZED_VALUES"
                success = True
                ballot_returned_found = True
            else:
                status += "UNABLE_TO_CREATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES"
                success = False
                ballot_returned_found = False

        except Exception as e:
            status += "UNABLE_TO_CREATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES_EXCEPTION: " + str(e) + " "
            success = False
            ballot_returned = None
            ballot_returned_found = False

        results = {
            'status':                   status,
            'success':                  success,
            'ballot_returned':          ballot_returned,
            'ballot_returned_found':    ballot_returned_found,
        }
        return results

    @staticmethod
    def create_ballot_returned(
            voter_id=0,
            google_civic_election_id=0,
            polling_location_we_vote_id='',
            election_day_text='',
            election_description_text='',
            updates={}):
        status = ''
        # Protect against ever saving test elections in the BallotReturned table
        if positive_value_exists(google_civic_election_id) and convert_to_int(google_civic_election_id) == 2000:
            results = {
                'status':                   "CHOSE_TO_NOT_SAVE_BALLOT_RETURNED_FOR_TEST_ELECTION",
                'success':                  True,
                'ballot_returned':          None,
                'ballot_returned_found':    False,
            }
            return results

        google_civic_election_id = convert_to_int(google_civic_election_id)
        # We assume that we tried to find an entry for this voter or polling_location
        try:
            ballot_returned_id = 0
            if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.create(
                    google_civic_election_id=google_civic_election_id,
                    voter_id=voter_id,
                    election_date=election_day_text,
                    election_description_text=election_description_text)
                ballot_returned_id = ballot_returned.id
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.create(
                    google_civic_election_id=google_civic_election_id,
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    election_date=election_day_text,
                    election_description_text=election_description_text)
                ballot_returned_id = ballot_returned.id
            else:
                ballot_returned = None
            if positive_value_exists(ballot_returned_id):
                text_for_map_search = ''
                if 'normalized_line1' in updates:
                    ballot_returned.normalized_line1 = updates['normalized_line1']
                    text_for_map_search += ballot_returned.normalized_line1 + ", "
                if 'normalized_line2' in updates:
                    ballot_returned.normalized_line2 = updates['normalized_line2']
                    text_for_map_search += ballot_returned.normalized_line2 + ", "
                if 'normalized_city' in updates:
                    ballot_returned.normalized_city = updates['normalized_city']
                    text_for_map_search += ballot_returned.normalized_city + ", "
                if 'normalized_state' in updates:
                    ballot_returned.normalized_state = updates['normalized_state']
                    text_for_map_search += ballot_returned.normalized_state + " "
                if 'zip' in updates:
                    ballot_returned.normalized_zip = updates['normalized_zip']
                    text_for_map_search += ballot_returned.normalized_zip
                if 'normalized_latitude' in updates and updates['normalized_latitude']:
                    ballot_returned.latitude = updates['normalized_latitude']
                if 'normalized_longitude' in updates and updates['normalized_longitude']:
                    ballot_returned.longitude = updates['normalized_longitude']

                ballot_returned.text_for_map_search = text_for_map_search

                ballot_returned.save()
                status += "SAVED_BALLOT_RETURNED_WITH_NORMALIZED_VALUES "
                success = True
                ballot_returned_found = True
            else:
                status += "UNABLE_TO_CREATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES "
                success = False
                ballot_returned_found = False

        except Exception as e:
            status += "UNABLE_TO_CREATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES_EXCEPTION: " + str(e) + ' '
            success = False
            ballot_returned = None
            ballot_returned_found = False

        results = {
            'status':                   status,
            'success':                  success,
            'ballot_returned':          ballot_returned,
            'ballot_returned_found':    ballot_returned_found,
        }
        return results

    @staticmethod
    def create_ballot_returned_empty(
            google_civic_election_id=0,
            is_from_ctcl=False,
            is_from_vote_usa=False,
            polling_location_we_vote_id='',
            state_code=None):
        ballot_returned_empty = None
        ballot_returned_empty_found = False
        if positive_value_exists(google_civic_election_id):
            google_civic_election_id = convert_to_int(google_civic_election_id)
        status = ''
        success = True

        try:
            ballot_returned_empty = BallotReturnedEmpty.objects.create(
                google_civic_election_id=google_civic_election_id,
                is_from_ctcl=is_from_ctcl,
                is_from_vote_usa=is_from_vote_usa,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code)
            ballot_returned_empty_found = True
            status += "BALLOT_RETURNED_EMPTY_CREATED "
        except Exception as e:
            status += "BALLOT_RETURNED_EMPTY_NOT_CREATED: " + str(e) + " "
            success = False

        results = {
            'status':                       status,
            'success':                      success,
            'ballot_returned_empty':        ballot_returned_empty,
            'ballot_returned_empty_found':  ballot_returned_empty_found,
        }
        return results

    @staticmethod
    def is_ballot_returned_different(google_civic_address_dict, ballot_returned):
        if 'line1' in google_civic_address_dict:
            if not ballot_returned.normalized_line1 == google_civic_address_dict['line1']:
                return True
        elif positive_value_exists(ballot_returned.normalized_line1):
            return True
        if 'line2' in google_civic_address_dict:
            if not ballot_returned.normalized_line2 == google_civic_address_dict['line2']:
                return True
        elif positive_value_exists(ballot_returned.normalized_line2):
            return True
        if not ballot_returned.normalized_city == google_civic_address_dict['city']:
            return True
        if not ballot_returned.normalized_state == google_civic_address_dict['state']:
            return True
        if 'zip' in google_civic_address_dict:
            if not ballot_returned.normalized_zip == google_civic_address_dict['zip']:
                return True
        elif positive_value_exists(ballot_returned.normalized_zip):
            return True
        if not positive_value_exists(ballot_returned.text_for_map_search):
            return True
        return False

    def update_ballot_returned_with_normalized_values(self, google_civic_address_dict, ballot_returned,
                                                      latitude='', longitude=''):
        status = ''
        try:
            text_for_map_search = ''
            if self.is_ballot_returned_different(google_civic_address_dict, ballot_returned):
                if 'line1' in google_civic_address_dict:
                    ballot_returned.normalized_line1 = google_civic_address_dict['line1']
                    text_for_map_search += ballot_returned.normalized_line1 + ", "
                if 'line2' in google_civic_address_dict:
                    ballot_returned.normalized_line2 = google_civic_address_dict['line2']
                    text_for_map_search += ballot_returned.normalized_line2 + ", "
                ballot_returned.normalized_city = google_civic_address_dict['city']
                text_for_map_search += ballot_returned.normalized_city + ", "
                ballot_returned.normalized_state = google_civic_address_dict['state']
                text_for_map_search += ballot_returned.normalized_state + " "
                if 'zip' in google_civic_address_dict:
                    ballot_returned.normalized_zip = google_civic_address_dict['zip']
                    text_for_map_search += ballot_returned.normalized_zip
                if latitude or longitude:
                    ballot_returned.latitude = latitude
                    ballot_returned.longitude = longitude

                ballot_returned.text_for_map_search = text_for_map_search

                ballot_returned.save()
                status += "UPDATED_BALLOT_RETURNED_WITH_NORMALIZED_VALUES "
                success = True
            else:
                status += "BALLOT_RETURNED_ALREADY_MATCHES_NORMALIZED_VALUES "
                success = False

        except Exception as e:
            status += "UNABLE_TO_UPDATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES_EXCEPTION: " + str(e) + " "
            success = False

        results = {
            'status':           status,
            'success':          success,
            'ballot_returned':  ballot_returned,
        }
        return results

    @staticmethod
    def fetch_last_election_in_this_state(state_code):
        """
        Find the last election (in the past) that has at least one ballot at a map point
        :param state_code:
        :return:
        """

        if not positive_value_exists(state_code):
            return 0

        election_manager = ElectionManager()
        election_results = election_manager.retrieve_elections_by_date()
        filtered_election_list = []
        today = datetime.now().date()
        today_date_as_integer = convert_date_to_date_as_integer(today)
        if election_results['success']:
            # These elections are sorted by most recent to least recent
            election_list = election_results['election_list']
            for election in election_list:
                # Filter out elections later than today
                if not positive_value_exists(election.election_day_text):
                    continue

                election_date_as_simple_string = election.election_day_text.replace("-", "")
                this_election_date_as_integer = convert_to_int(election_date_as_simple_string)
                if this_election_date_as_integer > today_date_as_integer:
                    continue

                # Leave national elections which have a blank state_code, and then add elections in this state
                if not positive_value_exists(election.state_code):
                    filtered_election_list.append(election)
                elif election.state_code.lower() == state_code.lower():
                    filtered_election_list.append(election)
                else:
                    # Neither national nor in this state
                    pass

        if not len(filtered_election_list):
            return 0

        # Start with list of elections (before today) in this state,
        #  including national but without elections in other states
        for election in filtered_election_list:
            try:
                # Loop backwards in time until we find an election with at least one ballot_returned entry
                ballot_returned_query = BallotReturned.objects.filter(
                    google_civic_election_id=election.google_civic_election_id)
                # Only return entries saved for polling_locations
                ballot_returned_query = ballot_returned_query.exclude(polling_location_we_vote_id=None)
                at_least_one_ballot_returned_for_election = ballot_returned_query.count()

                if positive_value_exists(at_least_one_ballot_returned_for_election):
                    # Break out and return this election_id
                    return election.google_civic_election_id
            except Exception as e:
                return 0

        # If we got through the elections without finding any ballot_returned entries, there is no prior elections
        return 0

    @staticmethod
    def fetch_next_upcoming_election_in_this_state(state_code, skip_these_elections=[]):
        """
        Find the soonest upcoming election in the future with at least one ballot at a map point
        :param state_code:
        :return:
        """
        if not positive_value_exists(state_code):
            return 0

        election_manager = ElectionManager()
        newest_to_oldest = False  # We want oldest to newest since we are looking for the next election
        election_results = election_manager.retrieve_elections_by_date(newest_to_oldest)
        filtered_election_list = []
        today = datetime.now().date()
        today_date_as_integer = convert_date_to_date_as_integer(today)
        if election_results['success']:
            # These elections are sorted by today, then tomorrow, etc
            election_list = election_results['election_list']
            for election in election_list:
                # Filter out elections we want to skip
                if len(skip_these_elections):
                    if election.google_civic_election_id in skip_these_elections:
                        continue
                # Filter out elections earlier than today
                if not positive_value_exists(election.election_day_text):
                    continue
                election_date_as_simple_string = election.election_day_text.replace("-", "")
                this_election_date_as_integer = convert_to_int(election_date_as_simple_string)
                if this_election_date_as_integer < today_date_as_integer:
                    continue

                # Leave national elections which have a blank state_code, and then add elections in this state
                if not positive_value_exists(election.state_code):
                    filtered_election_list.append(election)
                elif election.state_code.lower() == state_code.lower():
                    filtered_election_list.append(election)
                else:
                    # Neither national nor in this state
                    pass

        if not len(filtered_election_list):
            return 0

        # Start with list of elections (before today) in this state,
        #  including national but without elections in other states
        for election in filtered_election_list:
            if len(skip_these_elections):
                if election.google_civic_election_id in skip_these_elections:
                    continue
            try:
                # Loop backwards in time until we find an election with at least one ballot_returned entry
                ballot_returned_query = BallotReturned.objects.filter(
                    google_civic_election_id=election.google_civic_election_id)
                # Only return entries saved for polling_locations
                ballot_returned_query = ballot_returned_query.exclude(polling_location_we_vote_id=None)
                at_least_one_ballot_returned_for_election = ballot_returned_query.count()

                if positive_value_exists(at_least_one_ballot_returned_for_election):
                    # Break out and return this election_id
                    return election.google_civic_election_id
            except Exception as e:
                return 0

        # If we got through the elections without finding any ballot_returned entries, there is no prior election
        return 0

    def find_closest_ballot_returned(self, text_for_map_search, google_civic_election_id=0, read_only=True):
        """
        We search for the closest address for this election in the ballot_returned table. We never have to worry
        about test elections being returned with this routine, because we don't store ballot_returned entries for
        test elections.
        :param text_for_map_search:
        :param google_civic_election_id:
        :param read_only:
        :return:
        """
        ballot_returned_found = False
        ballot_returned = None
        location = None
        try_without_maps_key = False
        status = ""
        state_code = ""

        if not positive_value_exists(text_for_map_search):
            status += "FIND_CLOSEST_BALLOT_RETURNED-NO_TEXT_FOR_MAP_SEARCH "
            return {
                'status': status,
                'geocoder_quota_exceeded': False,
                'ballot_returned_found': ballot_returned_found,
                'ballot_returned': ballot_returned,
            }

        if not hasattr(self, 'google_client') or not self.google_client:
            self.google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
        # Note April 2022:  If you get vague error messages from GeoPy that you can't figure out, it is easy to install
        # Google's google-maps-services-python and then do the same query and get better messages.  I guess we want to
        # keep using the GeoPy as a wrapper, in case some day we want to swap out google for geolocation, with a better
        # competitor.  (GeoPy doesn't have much value in our use case.)
        try:
            location = self.google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
        except GeocoderQuotaExceeded:
            try_without_maps_key = True
            status += "GEOCODER_QUOTA_EXCEEDED "
        except Exception as e:
            try_without_maps_key = True
            status += 'GEOCODER_ERROR {error} [type: {error_type}] '.format(error=e, error_type=type(e))
            # logger.info(status + " @ " + text_for_map_search + "  google_civic_election_id=" +
            #             str(google_civic_election_id))

        if try_without_maps_key:
            # If we have exceeded our account, try without a maps key
            try:
                temp_google_client = get_geocoder_for_service('google')()
                location = temp_google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
            except GeocoderQuotaExceeded:
                status += "GEOCODER_QUOTA_EXCEEDED "
                results = {
                    'status':                   status,
                    'geocoder_quota_exceeded':  True,
                    'ballot_returned_found':    ballot_returned_found,
                    'ballot_returned':          ballot_returned,
                }
                return results
            except Exception as e:
                status += "GEOCODER_ERROR: " + str(e) + ' '
                location = None

        ballot = None
        if location is None:
            status += 'Geocoder could not find location matching "{}". Trying City, State. '.format(text_for_map_search)
            # If Geocoder is not able to give us a location, look to see if their voter entered their address as
            # "city_name, state_code" eg: "Sunnyvale, CA". If so, try to parse the entry and get ballot data
            # for that location
            if 'test' in sys.argv:
                ballot_returned_query = BallotReturned.objects.all()
            elif positive_value_exists(read_only):
                ballot_returned_query = BallotReturned.objects.using('readonly').all()
            else:
                ballot_returned_query = BallotReturned.objects.all()
            # Limit this query to entries stored for map points
            ballot_returned_query = ballot_returned_query.exclude(
                Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))

            if "," in text_for_map_search:
                address = text_for_map_search
                state_code = address.split(', ')[-1]
                state_code = state_code.upper()
                city = address.split(', ')[-2]
                city = city.lower()
                if positive_value_exists(state_code):
                    ballot_returned_query = ballot_returned_query.filter(normalized_state__iexact=state_code)
                # Searching by city is not critical for internal testing, and can cause problems
                # if positive_value_exists(city):
                #     ballot_returned_query = ballot_returned_query.filter(normalized_city__iexact=city)
            else:
                ballot_returned_query = ballot_returned_query.filter(text_for_map_search__icontains=text_for_map_search)

            if positive_value_exists(google_civic_election_id):
                ballot_returned_query = ballot_returned_query.filter(google_civic_election_id=google_civic_election_id)
            else:
                # If we have an active election coming up, including today
                # fetch_next_upcoming_election_in_this_state returns next election with ballot items
                upcoming_google_civic_election_id = self.fetch_next_upcoming_election_in_this_state(state_code)
                if positive_value_exists(upcoming_google_civic_election_id):
                    ballot_returned_query = ballot_returned_query.filter(
                        google_civic_election_id=upcoming_google_civic_election_id)
                else:
                    past_google_civic_election_id = self.fetch_last_election_in_this_state(state_code)
                    if positive_value_exists(past_google_civic_election_id):
                        # Limit the search to the most recent election with ballot items
                        ballot_returned_query = ballot_returned_query.filter(
                            google_civic_election_id=past_google_civic_election_id)

            try:
                ballot = ballot_returned_query.first()
            except Exception as e:
                ballot = None
                status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_LOCATION_NONE: " + str(e) + ' '
            # ballot_returned_list = list(ballot_returned_query)
            # if len(ballot_returned_list):
            #     ballot = ballot_returned_list[0]
        else:
            # If here, then the geocoder successfully found the address
            status += 'GEOCODER_FOUND_LOCATION '
            address = location.address
            # address has format "line_1, state zip, USA"

            if 'test' in sys.argv:
                ballot_returned_query = BallotReturned.objects.all()
            elif positive_value_exists(read_only):
                ballot_returned_query = BallotReturned.objects.using('readonly').all()
            else:
                ballot_returned_query = BallotReturned.objects.all()
            # Limit this query to entries stored for map points
            ballot_returned_query = ballot_returned_query.exclude(
                Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
            if positive_value_exists(address) and "," in address:
                raw_state_code = address.split(', ')
                if positive_value_exists(raw_state_code):
                    state_code = raw_state_code[-2][:2]
            if positive_value_exists(state_code):
                # This search for normalized_state is NOT redundant because some elections are in many states
                ballot_returned_query = ballot_returned_query.filter(normalized_state__iexact=state_code)

            try:
                lat_rads_ploc = location.latitude * DEG_TO_RADS
                lon_rads_ploc = location.longitude * DEG_TO_RADS
                ballot_returned_query = ballot_returned_query.annotate(
                    # Calculate the approximate great circle distance between two coordinates
                    # https://medium.com/@petehouston/calculate-distance-of-two-locations-on-earth-using-python-1501b1944d97
                    distance=ExpressionWrapper(
                         (RADIUS_OF_EARTH_IN_MILES * (
                             ACos(
                                 (Sin(F('latitude') * DEG_TO_RADS) *
                                  Sin(lat_rads_ploc)) +
                                 (Cos(F('latitude') * DEG_TO_RADS) *
                                  Cos(lat_rads_ploc) *
                                  Cos((F('longitude') * DEG_TO_RADS) - lon_rads_ploc))
                             )
                           )),
                         output_field=FloatField()))
            except Exception as e:
                status += "EXCEPTION_IN_ANNOTATE_CALCULATION1-" + str(e) + ' '

            # Do not return ballots more than 25 miles away
            ballot_returned_query = ballot_returned_query.filter(distance__lte=DISTANCE_LIMIT_IN_MILES)

            ballot_returned_query = ballot_returned_query.order_by('distance')

            if positive_value_exists(google_civic_election_id):
                status += "SEARCHING_BY_GOOGLE_CIVIC_ID "
                ballot_returned_query = ballot_returned_query.filter(google_civic_election_id=google_civic_election_id)
                try:
                    ballot = ballot_returned_query.first()
                    if ballot == None:
                        status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_HAS_LOCATION_AND_POSITIVE_GOOGLE_CIVIC_ID__BALLOT_NONE "
                    else:
                        status += "SUBSTITUTED_BALLOT_DISTANCE1: " + str(ballot.distance) + " "
                        # print('===== 1 ===== ballot.distance', ballot.distance, ballot.latitude, ballot.longitude,
                        #       text_for_map_search)
                except Exception as e:
                    ballot = None
                    status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_HAS_LOCATION_AND_POSITIVE_GOOGLE_CIVIC_ID: " + str(e) + ' '
                # ballot_returned_list = list(ballot_returned_query)
                # if len(ballot_returned_list):
                #     ballot = ballot_returned_list[0]
            else:
                # If we have an active election coming up, including today
                # fetch_next_upcoming_election_in_this_state returns next election with ballot items
                status += "FETCH_NEXT_UPCOMING_ELECTION_IN_THIS_STATE "
                upcoming_google_civic_election_id = self.fetch_next_upcoming_election_in_this_state(state_code)
                if positive_value_exists(upcoming_google_civic_election_id):
                    ballot_returned_query_without_election_id = ballot_returned_query
                    ballot_returned_query = ballot_returned_query.filter(
                        google_civic_election_id=upcoming_google_civic_election_id)
                    try:
                        ballot = ballot_returned_query.first()
                        if ballot == None:
                            status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_HAS_LOCATION_AND_POSITIVE_UPCOMING_GOOGLE_CIVIC_ID__BALLOT_NONE "
                        else:
                            status += "SUBSTITUTED_BALLOT_DISTANCE2: " + str(ballot.distance) + " "
                            # print('===== 2 ===== ballot.distance', ballot.distance, ballot.latitude, ballot.longitude,
                            #       text_for_map_search)
                    except Exception as e:
                        ballot = None
                        status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_HAS_LOCATION_AND_POSITIVE_UPCOMING_GOOGLE_CIVIC_ID: " + str(e) + ' '
                    # ballot_returned_list = list(ballot_returned_query)
                    # if len(ballot_returned_list):
                    #     ballot = ballot_returned_list[0]
                    # What if this is a National election, but there aren't any races in the state the voter is in?
                    # We want to find the *next* upcoming election
                    if ballot is None:
                        ballot_not_found = True
                        more_elections_exist = True
                        skip_these_elections = []
                        safety_valve_count = 0
                        while ballot_not_found and more_elections_exist and safety_valve_count < 20:
                            safety_valve_count += 1
                            # Reset ballot_returned_query
                            ballot_returned_query = ballot_returned_query_without_election_id
                            skip_these_elections.append(upcoming_google_civic_election_id)
                            upcoming_google_civic_election_id = self.fetch_next_upcoming_election_in_this_state(
                                state_code, skip_these_elections)
                            if positive_value_exists(upcoming_google_civic_election_id):
                                ballot_returned_query = ballot_returned_query.filter(
                                    google_civic_election_id=upcoming_google_civic_election_id)
                                try:
                                    ballot = ballot_returned_query.first()
                                    if ballot == None:
                                        status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_BALLOT_NONE_POSITIVE_UPCOMING_GOOGLE_CIVIC_ID__BALLOT_NONE "
                                    else:
                                        status += "SUBSTITUTED_BALLOT_DISTANCE3: " + str(ballot.distance) + " "
                                        # print('===== 3 ===== ballot.distance', ballot.distance, ballot.latitude,
                                        #       ballot.longitude, text_for_map_search)
                                except Exception as e:
                                    ballot = None
                                    status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_BALLOT_NONE_POSITIVE_UPCOMING_GOOGLE_CIVIC_ID: " + str(e) + ' '
                                # ballot_returned_list = list(ballot_returned_query)
                                # if len(ballot_returned_list):
                                #     ballot = ballot_returned_list[0]
                                if ballot is not None:
                                    ballot_not_found = False
                            else:
                                more_elections_exist = False
                else:
                    ballot = None
                    status += "NOT_LOOKING_FOR_PREVIOUS_ELECTION "
                    # We no longer want to automatically return the previous election for this voter
                    # past_google_civic_election_id = self.fetch_last_election_in_this_state(state_code)
                    # if positive_value_exists(past_google_civic_election_id):
                    #     # Limit the search to the most recent election with ballot items
                    #     ballot_returned_query = ballot_returned_query.filter(
                    #         google_civic_election_id=past_google_civic_election_id)
                    # try:
                    #     ballot = ballot_returned_query.first()
                    # except Exception as e:
                    #     ballot = None
                    #     status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_HAS_PAST_GOOGLE_CIVIC_ID: " + str(e) + ' '
                    # # ballot_returned_list = list(ballot_returned_query)
                    # # if len(ballot_returned_list):
                    # #     ballot = ballot_returned_list[0]

        if ballot is not None:
            ballot_returned = ballot
            ballot_returned_found = True
            status += 'BALLOT_RETURNED_FOUND '
        else:
            status += 'NO_STORED_BALLOT_MATCHES_STATE: {}. '.format(state_code)
            # Now Try the search again without the limitation of the state_code
            if location is not None and positive_value_exists(google_civic_election_id):
                # If here, then the geocoder successfully found the address
                status += 'GEOCODER_FOUND_LOCATION-ATTEMPT2 '
                address = location.address
                # address has format "line_1, state zip, USA"

                if 'test' in sys.argv:
                    ballot_returned_query = BallotReturned.objects.all()
                elif positive_value_exists(read_only):
                    ballot_returned_query = BallotReturned.objects.using('readonly').all()
                else:
                    ballot_returned_query = BallotReturned.objects.all()
                # Limit this query to entries stored for map points
                ballot_returned_query = ballot_returned_query.exclude(
                    Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))

                try:
                    lat_rads_ploc = location.latitude * DEG_TO_RADS
                    lon_rads_ploc = location.longitude * DEG_TO_RADS
                    ballot_returned_query = ballot_returned_query.annotate(
                        # Calculate the approximate great circle distance between two coordinates
                        # https://medium.com/@petehouston/calculate-distance-of-two-locations-on-earth-using-python-1501b1944d97
                        distance=ExpressionWrapper(
                            (RADIUS_OF_EARTH_IN_MILES * (
                                ACos(
                                    (Sin(F('latitude') * DEG_TO_RADS) *
                                     Sin(lat_rads_ploc)) +
                                    (Cos(F('latitude') * DEG_TO_RADS) *
                                     Cos(lat_rads_ploc) *
                                     Cos((F('longitude') * DEG_TO_RADS) - lon_rads_ploc))
                                )
                            )),
                            output_field=FloatField()))
                except Exception as e:
                    status += "EXCEPTION_IN_ANNOTATE_CALCULATION2-" + str(e) + ' '

                # Do not return ballots more than 25 miles away
                ballot_returned_query = ballot_returned_query.filter(distance__lte=DISTANCE_LIMIT_IN_MILES)

                ballot_returned_query = ballot_returned_query.order_by('distance')

                status += "SEARCHING_BY_GOOGLE_CIVIC_ID-ATTEMPT2 "
                ballot_returned_query = ballot_returned_query.filter(
                    google_civic_election_id=google_civic_election_id)
                try:
                    ballot_returned = ballot_returned_query.first()
                    status += "SUBSTITUTED_BALLOT_DISTANCE4: " + str(ballot_returned.distance) + " "
                except Exception as e:
                    ballot_returned = None
                    status += "BALLOT_RETURNED_QUERY_FIRST_FAILED_HAS_BALLOT_LOCATION_AND_POSITIVE_GOOGLE_CIVIC_ID: " + str(e) + ' '
                # ballot_returned_list = list(ballot_returned_query)
                # if len(ballot_returned_list):
                #     ballot_returned = ballot_returned_list[0]
                if ballot_returned is not None:
                    ballot_returned_found = True
                    status += 'BALLOT_RETURNED_FOUND-ATTEMPT2 '

        status += 'END_OF_FIND_CLOSEST_BALLOT_RETURNED '

        return {
            'status':                   status,
            'geocoder_quota_exceeded':  False,
            'ballot_returned_found':    ballot_returned_found,
            'ballot_returned':          ballot_returned,
        }

    @staticmethod
    def should_election_search_data_be_saved(google_civic_election_id):
        if not positive_value_exists(google_civic_election_id):
            return False
        else:
            ballot_returned_list_manager = BallotReturnedListManager()
            ballot_returned_list_count = ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                google_civic_election_id)
            if positive_value_exists(ballot_returned_list_count):
                return True
            return False

    @staticmethod
    def update_or_create_ballot_returned(
            polling_location_we_vote_id='',
            voter_id=0,
            google_civic_election_id='',
            election_day_text=False,
            election_description_text=False,
            latitude=False,
            longitude=False,
            normalized_city=False,
            normalized_line1=False,
            normalized_line2=False,
            normalized_state=False,
            normalized_zip=False,
            text_for_map_search=False,
            ballot_location_display_name=False):
        status = ""

        exception_multiple_object_returned = False
        new_ballot_returned_created = False
        google_civic_election_id = convert_to_int(google_civic_election_id)
        ballot_returned = None
        ballot_returned_found = False
        delete_extra_ballot_returned_entries = False
        success = True

        if not google_civic_election_id:
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID-update_or_create_ballot_returned '
        elif (not polling_location_we_vote_id) and (not voter_id):
            success = False
            status += 'MISSING_BALLOT_RETURNED_POLLING_LOCATION_AND_VOTER_ID-update_or_create_ballot_returned '
        else:
            try:
                if positive_value_exists(polling_location_we_vote_id):
                    ballot_returned, new_ballot_returned_created = BallotReturned.objects.get_or_create(
                        google_civic_election_id=google_civic_election_id,
                        polling_location_we_vote_id=polling_location_we_vote_id,
                    )
                    ballot_returned_found = True
                elif positive_value_exists(voter_id):
                    ballot_returned, new_ballot_returned_created = BallotReturned.objects.get_or_create(
                        google_civic_election_id=google_civic_election_id,
                        voter_id=voter_id
                    )
                    ballot_returned_found = True

            except BallotReturned.MultipleObjectsReturned as e:
                status += 'MULTIPLE_MATCHING_BALLOT_RETURNED_FOUND ' + str(e) + ' '
                status += 'google_civic_election_id: ' + str(google_civic_election_id) + " "
                status += 'polling_location_we_vote_id: ' + str(polling_location_we_vote_id) + " "
                status += 'voter_id: ' + str(voter_id) + " "
                handle_record_found_more_than_one_exception(e, logger=logger, exception_message_optional=status)
                success = False
                exception_multiple_object_returned = True
                delete_extra_ballot_returned_entries = True
            except Exception as e:
                status += 'UNABLE_TO_GET_OR_CREATE_BALLOT_RETURNED ' + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)
                success = False
                delete_extra_ballot_returned_entries = True

            if positive_value_exists(delete_extra_ballot_returned_entries):
                success = False
                ballot_returned_manager = BallotReturnedManager()
                results = ballot_returned_manager.remove_duplicate_ballot_returned_entries(
                    google_civic_election_id, polling_location_we_vote_id, voter_id)
                if results['ballot_returned_found']:
                    ballot_returned_found = True
                    ballot_returned = results['ballot_returned']
                    success = True

            if positive_value_exists(ballot_returned_found):
                try:
                    if not positive_value_exists(ballot_returned.google_civic_election_id):
                        ballot_returned.google_civic_election_id = google_civic_election_id
                    if not positive_value_exists(ballot_returned.voter_id):
                        ballot_returned.voter_id = voter_id
                    if ballot_location_display_name is not False:
                        ballot_returned.ballot_location_display_name = ballot_location_display_name
                    if election_day_text is not False and election_day_text is not None:
                        ballot_returned.election_date = datetime.strptime(election_day_text, "%Y-%m-%d").date()
                    if election_description_text is not False:
                        ballot_returned.election_description_text = election_description_text
                    if latitude is not False:
                        ballot_returned.latitude = latitude
                    if longitude is not False:
                        ballot_returned.longitude = longitude
                    if normalized_city is not False:
                        ballot_returned.normalized_city = normalized_city
                    if normalized_line1 is not False:
                        ballot_returned.normalized_line1 = normalized_line1
                    if normalized_line2 is not False:
                        ballot_returned.normalized_line2 = normalized_line2
                    if normalized_state is not False:
                        ballot_returned.normalized_state = normalized_state
                    if normalized_zip is not False:
                        ballot_returned.normalized_zip = normalized_zip
                    if text_for_map_search is not False:
                        ballot_returned.text_for_map_search = text_for_map_search

                    if not positive_value_exists(ballot_returned.state_code):
                        # Can we get state_code from normalized_state?
                        if positive_value_exists(ballot_returned.normalized_state):
                            ballot_returned.state_code = ballot_returned.normalized_state

                    if not positive_value_exists(ballot_returned.state_code):
                        # Can we get state_code from text_for_map_search?
                        if positive_value_exists(ballot_returned.text_for_map_search):
                            ballot_returned.state_code = extract_state_code_from_address_string(
                                ballot_returned.text_for_map_search)

                    # We always save so date_last_updated resets to current date
                    ballot_returned.save()

                    if new_ballot_returned_created:
                        success = True
                        status += 'BALLOT_RETURNED_CREATED '
                    else:
                        success = True
                        status += 'BALLOT_RETURNED_UPDATED '

                except Exception as e:
                    status += 'UNABLE_TO_SAVE_BALLOT_RETURNED: ' + str(e) + " "
                    handle_exception(e, logger=logger, exception_message=status)
                    success = False

        results = {
            'success':                      success,
            'status':                       status,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'ballot_returned_found':        ballot_returned_found,
            'ballot_returned':              ballot_returned,
            'new_ballot_returned_created':  new_ballot_returned_created,
        }
        return results

    def populate_latitude_and_longitude_for_ballot_returned(self, ballot_returned_object):
        """
        We use the google geocoder in partnership with geoip
        :param ballot_returned_object:
        :return:
        """
        status = ""
        # We try to use existing google_client
        if not hasattr(self, 'google_client') or not self.google_client:
            self.google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)

        if not hasattr(ballot_returned_object, "normalized_line1"):
            results = {
                'status':                   "POPULATE_LATITUDE_AND_LONGITUDE-NOT_A_BALLOT_RETURNED_OBJECT ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
            }
            return results

        if not positive_value_exists(ballot_returned_object.normalized_line1) or not \
                positive_value_exists(ballot_returned_object.normalized_city) or not \
                positive_value_exists(ballot_returned_object.normalized_state) or not \
                positive_value_exists(ballot_returned_object.normalized_zip):
            # We require all four values
            results = {
                'status':                   "POPULATE_LATITUDE_AND_LONGITUDE-MISSING_REQUIRED_ADDRESS_INFO ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
            }
            return results

        full_ballot_address = '{}, {}, {} {}'.format(
            ballot_returned_object.normalized_line1,
            ballot_returned_object.normalized_city,
            ballot_returned_object.normalized_state,
            ballot_returned_object.normalized_zip)
        try:
            location = self.google_client.geocode(full_ballot_address, sensor=False, timeout=GEOCODE_TIMEOUT)
        except GeocoderQuotaExceeded:
            status += "GeocoderQuotaExceeded "
            results = {
                'status':                   status,
                'geocoder_quota_exceeded':  True,
                'success':                  False,
            }
            return results
        except Exception as e:
            status += "Geocoder-Exception: " + str(e) + " "
            results = {
                'status':                   status,
                'geocoder_quota_exceeded':  False,
                'success':                  False,
            }
            return results

        if location is None:
            results = {
                'status':                   "POPULATE_LATITUDE_AND_LONGITUDE-LOCATION_NOT_RETURNED_FROM_GEOCODER ",
                'geocoder_quota_exceeded':  False,
                'success':                  False,
            }
            return results

        try:
            ballot_returned_object.latitude, ballot_returned_object.longitude = location.latitude, location.longitude
            ballot_returned_object.save()
            status += "BALLOT_RETURNED_SAVED_WITH_LATITUDE_AND_LONGITUDE "
            success = True
        except Exception as e:
            status += "BALLOT_RETURNED_NOT_SAVED_WITH_LATITUDE_AND_LONGITUDE "
            success = False

        results = {
            'status':                   status,
            'geocoder_quota_exceeded':  False,
            'success':                  success,
        }
        return results


class BallotReturnedListManager(models.Manager):
    """
    A way to work with a list of ballot_returned entries
    """
    @staticmethod
    def fetch_ballot_location_display_option_on_count_for_election(google_civic_election_id, state_code=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        try:
            ballot_returned_queryset = BallotReturned.objects.using('readonly').all()
            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            ballot_returned_queryset = ballot_returned_queryset.filter(ballot_location_display_option_on=True)
            if positive_value_exists(state_code):
                ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state_code)

            return ballot_returned_queryset.count()
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            pass
        except Exception as e:
            pass

        return 0

    @staticmethod
    def retrieve_ballot_returned_list(
            google_civic_election_id,
            polling_location_we_vote_id='',
            for_voters=False,
            state_code='',
            date_last_updated_should_not_exceed=None,
            limit=0):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        ballot_returned_list = []
        ballot_returned_list_found = False
        status = ''
        success = True

        if not positive_value_exists(google_civic_election_id) \
                and not (positive_value_exists(polling_location_we_vote_id) or positive_value_exists(for_voters)):
            success = False
            status += "RETRIEVE_BALLOT_RETURNED_MISSING_REQUIRED_VARIABLES "
            results = {
                'status': status,
                'success': success,
                'ballot_returned_list_found': ballot_returned_list_found,
                'ballot_returned_list': ballot_returned_list,
            }
            return results

        try:
            ballot_returned_queryset = BallotReturned.objects.all().order_by('-date_last_updated')
            if positive_value_exists(google_civic_election_id):
                ballot_returned_queryset = \
                    ballot_returned_queryset.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                ballot_returned_queryset = ballot_returned_queryset.filter(state_code__iexact=state_code)
            if positive_value_exists(polling_location_we_vote_id):
                ballot_returned_queryset = \
                    ballot_returned_queryset.filter(polling_location_we_vote_id=polling_location_we_vote_id)
            elif for_voters:
                ballot_returned_queryset = \
                    ballot_returned_queryset.exclude(Q(voter_id__isnull=True) | Q(voter_id=0))
            if positive_value_exists(date_last_updated_should_not_exceed):
                ballot_returned_queryset = \
                    ballot_returned_queryset.filter(date_last_updated__lt=date_last_updated_should_not_exceed)
            if positive_value_exists(limit):
                ballot_returned_list = ballot_returned_queryset[:limit]
            else:
                ballot_returned_list = list(ballot_returned_queryset)

            if len(ballot_returned_list):
                ballot_returned_list_found = True
                status += 'BALLOT_RETURNED_LIST_FOUND '
            else:
                status += 'NO_BALLOT_RETURNED_LIST_FOUND '
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_RETURNED_LIST_FOUND_DOES_NOT_EXIST '
            ballot_returned_list = []
        except Exception as e:
            success = False
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_returned_list ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        results = {
            'success':                      success,
            'status':                       status,
            'ballot_returned_list_found':   ballot_returned_list_found,
            'ballot_returned_list':         ballot_returned_list,
        }
        return results

    @staticmethod
    def retrieve_ballot_returned_duplicate_list(google_civic_election_id, polling_location_we_vote_id, voter_id):
        success = True
        status = ""

        google_civic_election_id = convert_to_int(google_civic_election_id)
        ballot_returned_list = []
        ballot_returned_list_found = False
        ballot_returned_list_count = 0

        if not positive_value_exists(google_civic_election_id) \
                or not positive_value_exists(polling_location_we_vote_id) \
                or not positive_value_exists(voter_id):
            status += "RETRIEVE_BALLOT_RETURNED_DUPLICATE_LIST_MISSING_REQUIRED_VARIABLES "
            results = {
                'success': False,
                'status': status,
                'ballot_returned_list': ballot_returned_list,
                'ballot_returned_list_count': ballot_returned_list_count,
                'ballot_returned_list_found': ballot_returned_list_found,
            }
            return results

        try:
            ballot_returned_queryset = BallotReturned.objects.all()
            ballot_returned_queryset = \
                ballot_returned_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_returned_queryset = \
                ballot_returned_queryset.filter(polling_location_we_vote_id__iexact=polling_location_we_vote_id)
            ballot_returned_queryset = ballot_returned_queryset.filter(voter_id=voter_id)

            ballot_returned_list = list(ballot_returned_queryset)
            ballot_returned_list_count = len(ballot_returned_list)

            if positive_value_exists(ballot_returned_list_count):
                ballot_returned_list_found = True
                status += 'BALLOT_RETURNED_DUPLICATE_LIST_FOUND'
            else:
                status += 'NO_BALLOT_RETURNED_DUPLICATE_LIST_FOUND'
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_RETURNED_DUPLICATE_LIST_FOUND_DOES_NOT_EXIST'
            ballot_returned_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_returned_duplicate_list ' \
                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'ballot_returned_list':         ballot_returned_list,
            'ballot_returned_list_count':   ballot_returned_list_count,
            'ballot_returned_list_found': ballot_returned_list_found,
        }
        return results

    @staticmethod
    def retrieve_polling_location_we_vote_id_list_from_ballot_returned(
            google_civic_election_id,
            state_code='',
            limit=750):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        polling_location_we_vote_id_list = []
        status = ''
        success = True
        status += "BallotReturned LIMIT: " + str(limit) + " "
        status += "google_civic_election_id: " + str(google_civic_election_id) + " "

        try:
            if positive_value_exists(state_code):
                query = BallotReturned.objects.using('readonly')\
                    .order_by('-date_last_updated')\
                    .filter(google_civic_election_id=google_civic_election_id, normalized_state__iexact=state_code)\
                    .exclude(Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
            else:
                query = BallotReturned.objects.using('readonly')\
                    .order_by('-date_last_updated') \
                    .filter(google_civic_election_id=google_civic_election_id) \
                    .exclude(Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
            query = \
                query.values_list('polling_location_we_vote_id', flat=True).distinct()
            if positive_value_exists(limit):
                polling_location_we_vote_id_list = query[:limit]
            else:
                polling_location_we_vote_id_list = list(query)
        except Exception as e:
            status += "COULD_NOT_RETRIEVE_POLLING_LOCATION_LIST " + str(e) + " "
        # status += "PL_LIST: " + str(polling_location_we_vote_id_list) + " "
        polling_location_we_vote_id_list_found = positive_value_exists(len(polling_location_we_vote_id_list))
        results = {
            'success':                                  success,
            'status':                                   status,
            'polling_location_we_vote_id_list_found':   polling_location_we_vote_id_list_found,
            'polling_location_we_vote_id_list':         polling_location_we_vote_id_list,
        }
        return results

    @staticmethod
    def retrieve_polling_location_we_vote_id_list_from_ballot_returned_empty(
            batch_process_date_started=None,
            is_from_ctcl=False,
            is_from_vote_usa=False,
            google_civic_election_id='',
            state_code=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        polling_location_we_vote_id_list = []
        status = ''
        success = True
        # status += "google_civic_election_id: " + str(google_civic_election_id) + " "

        try:
            query = BallotReturnedEmpty.objects.using('readonly')\
                .order_by('-date_last_updated')\
                .filter(google_civic_election_id=google_civic_election_id, )\
                .exclude(Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
            if batch_process_date_started:
                query = query.filter(date_last_updated__gt=batch_process_date_started)
            if positive_value_exists(is_from_ctcl):
                query = query.filter(is_from_ctcl=True)
            if positive_value_exists(is_from_vote_usa):
                query = query.filter(is_from_vote_usa=True)
            if positive_value_exists(state_code):
                query = query.filter(state_code__iexact=state_code)
            query = query.values_list('polling_location_we_vote_id', flat=True).distinct()
            polling_location_we_vote_id_list = list(query)
        except Exception as e:
            status += "COULD_NOT_RETRIEVE_POLLING_LOCATION_LIST-EMPTY: " + str(e) + " "
        # status += "PL_LIST: " + str(polling_location_we_vote_id_list) + " "
        polling_location_we_vote_id_list_found = positive_value_exists(len(polling_location_we_vote_id_list))
        results = {
            'success':                                  success,
            'status':                                   status,
            'polling_location_we_vote_id_list_found':   polling_location_we_vote_id_list_found,
            'polling_location_we_vote_id_list':         polling_location_we_vote_id_list,
        }
        return results

    @staticmethod
    def retrieve_ballot_returned_list_for_election(
            google_civic_election_id,
            state_code='',
            limit=0,
            ballot_returned_search_str='',
            read_only=False):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        ballot_returned_list = []
        ballot_returned_list_found = False
        status = ''
        success = True

        try:
            if positive_value_exists(read_only):
                ballot_returned_queryset = BallotReturned.objects.using('readonly').order_by('-id')
            else:
                ballot_returned_queryset = BallotReturned.objects.order_by('-id')
            if positive_value_exists(ballot_returned_search_str):
                filters = []
                new_filter = Q(id__iexact=ballot_returned_search_str)
                filters.append(new_filter)

                new_filter = Q(ballot_location_display_name__icontains=ballot_returned_search_str)
                filters.append(new_filter)

                new_filter = Q(ballot_location_shortcut__icontains=ballot_returned_search_str)
                filters.append(new_filter)

                new_filter = Q(text_for_map_search__icontains=ballot_returned_search_str)
                filters.append(new_filter)

                new_filter = Q(normalized_state__icontains=ballot_returned_search_str)
                filters.append(new_filter)

                new_filter = Q(we_vote_id__iexact=ballot_returned_search_str)
                filters.append(new_filter)

                new_filter = Q(voter_id__iexact=ballot_returned_search_str)
                filters.append(new_filter)

                new_filter = Q(polling_location_we_vote_id__iexact=ballot_returned_search_str)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    ballot_returned_queryset = ballot_returned_queryset.filter(final_filters)

            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state_code)
            ballot_returned_queryset = ballot_returned_queryset.order_by("ballot_location_display_name")
            if positive_value_exists(limit):
                ballot_returned_queryset = ballot_returned_queryset[:limit]
            ballot_returned_list = ballot_returned_queryset

            if len(ballot_returned_list):
                ballot_returned_list_found = True
                status += 'BALLOT_RETURNED_LIST_FOUND'
            else:
                status += 'NO_BALLOT_RETURNED_LIST_FOUND'
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_RETURNED_LIST_FOUND_DOES_NOT_EXIST'
            ballot_returned_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_returned_list_for_election ' \
                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'ballot_returned_list_found':   ballot_returned_list_found,
            'ballot_returned_list':         ballot_returned_list,
        }
        return results

    @staticmethod
    def retrieve_state_codes_in_election(google_civic_election_id):
        """
        Return a simple list of state_codes that have ballot items in an election.
        :param google_civic_election_id:
        :return:
        """
        status = ''
        success = False
        unique_state_code_list = []
        try:
            # Make sure there is at least one BallotReturned for this election. If so, then check for each state
            queryset = BallotReturned.objects.using('readonly').all()
            queryset = queryset.filter(google_civic_election_id=google_civic_election_id)
            one_found = queryset[:1]
            if len(one_found):
                for state_code, state_name in STATE_CODE_MAP.items():
                    if state_code.upper() not in unique_state_code_list:
                        queryset = BallotReturned.objects.using('readonly').all()
                        queryset = queryset.filter(google_civic_election_id=google_civic_election_id)
                        queryset = queryset.filter(
                            Q(state_code__iexact=state_code) | Q(normalized_state__iexact=state_code))
                        one_found = queryset[:1]
                        if len(one_found):
                            unique_state_code_list.append(state_code.upper())
            status += 'RETRIEVE_STATE_CODES_IN_ELECTION-QUERY_SUCCESSFUL '
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'RETRIEVE_STATE_CODES_IN_ELECTION-FAILED: ' + str(e) + ' '

        results = {
            'success':          success,
            'status':           status,
            'state_code_list':  unique_state_code_list,
        }
        return results

    @staticmethod
    def fetch_oldest_date_last_updated(google_civic_election_id=0, state_code='', for_voter=False):
        """

        :param google_civic_election_id:
        :param state_code:
        :param for_voter:
        :return:
        """
        google_civic_election_id = convert_to_int(google_civic_election_id)
        status = ''
        try:
            ballot_returned_queryset = BallotReturned.objects.using('readonly').order_by('date_last_updated').all()
            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            if positive_value_exists(for_voter):
                # Find entries where the voter_id is not null or 0
                ballot_returned_queryset = ballot_returned_queryset.exclude(
                    Q(voter_id__isnull=True) | Q(voter_id=0))
            else:
                # Default is to find BallotReturned entries for polling_locations
                ballot_returned_queryset = ballot_returned_queryset.exclude(
                    Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
                if positive_value_exists(state_code):
                    ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state_code)

            ballot_returned = ballot_returned_queryset.first()
            return ballot_returned.date_last_updated
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_RETURNED_FOUND '
        except Exception as e:
            status += 'FAILED fetch_oldest_last_updated_date ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        return None

    @staticmethod
    def fetch_ballot_returned_list_count_for_election(google_civic_election_id, state_code=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        status = ''
        try:
            ballot_returned_queryset = BallotReturned.objects.using('readonly').all()
            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state_code)

            return ballot_returned_queryset.count()
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_RETURNED_LIST_FOUND_DOES_NOT_EXIST'
            ballot_returned_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_returned_list_for_election ' \
                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        return 0

    @staticmethod
    def fetch_ballot_returned_entries_needed_lat_long_for_election(google_civic_election_id, state_code=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        status = ''
        try:
            ballot_returned_queryset = BallotReturned.objects.using('readonly').all()
            ballot_returned_queryset = ballot_returned_queryset.exclude(
                Q(polling_location_we_vote_id=None) |
                Q(polling_location_we_vote_id=""))
            ballot_returned_queryset = ballot_returned_queryset.filter(latitude=None)
            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state_code)

            return ballot_returned_queryset.count()
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_BALLOT_RETURNED_LIST_FOUND_DOES_NOT_EXIST'
            ballot_returned_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_ballot_returned_list_for_election ' \
                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        return 0

    @staticmethod
    def merge_ballot_returned_duplicates(google_civic_election_id=0, state_code=''):
        status = ''
        success = True

        if not positive_value_exists(google_civic_election_id):
            status += "MISSING_GOOGLE_CIVIC_ELECTION_ID "
            results = {
                'success':          False,
                'status':           status,
                'total_updated':    0,
            }
            return results

        # We don't put the following in a try block, because we want it to fail immediately if there is a problem

        # Get a list of all of the polling_location_we_vote_id's that have duplicate entries for this election
        duplicate_query = BallotReturned.objects.filter(google_civic_election_id=google_civic_election_id)
        if positive_value_exists(state_code):
            duplicate_query = duplicate_query.filter(state_code__iexact=state_code)
        duplicates = duplicate_query.values('polling_location_we_vote_id')\
            .annotate(entry_count=Count('polling_location_we_vote_id'))\
            .filter(entry_count__gt=1)
        duplicates_count = len(duplicates)
        status += "DUPLICATES_COUNT: " + str(duplicates_count) + " "

        # duplicates = [{'polling_location_we_vote_id': 'wv02ploc54063', 'entry_count': 2}]
        total_updated = 0
        for one_duplicate in duplicates:
            polling_location_we_vote_id = one_duplicate['polling_location_we_vote_id']
            if not positive_value_exists(polling_location_we_vote_id):
                status += "POLLING_LOCATION_WE_VOTE_ID-EMPTY "
                continue
            # status += " " + str(polling_location_we_vote_id) + " "
            duplicate_query = BallotReturned.objects.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                duplicate_query = duplicate_query.filter(state_code__iexact=state_code)
            duplicate_query = duplicate_query.filter(
                polling_location_we_vote_id=polling_location_we_vote_id)
            duplicate_list = list(duplicate_query)
            # status += "DUP_LIST_COUNT: " + str(len(duplicate_list)) + " "
            is_first = True
            to_ballot_returned_we_vote_id = ''
            for ballot_returned in duplicate_list:
                ballot_returned_we_vote_id = ballot_returned.we_vote_id
                # status += " " + str(ballot_returned_we_vote_id) + " "
                if is_first:
                    to_ballot_returned_we_vote_id = ballot_returned.we_vote_id
                    is_first = False
                if positive_value_exists(ballot_returned_we_vote_id) \
                        and positive_value_exists(to_ballot_returned_we_vote_id) \
                        and ballot_returned_we_vote_id != to_ballot_returned_we_vote_id:
                    # Find Voter Ballot Saved entries that are copied from this polling_location
                    # number_query = VoterBallotSaved.objects.filter(
                    #     ballot_returned_we_vote_id__iexact=ballot_returned_we_vote_id)
                    # number_updated = number_query.count()

                    number_updated = VoterBallotSaved.objects.filter(
                        ballot_returned_we_vote_id__iexact=ballot_returned_we_vote_id)\
                        .update(ballot_returned_we_vote_id=to_ballot_returned_we_vote_id)
                    total_updated += number_updated
                    # If still here, delete the ballot_returned we are looking at
                    ballot_returned.delete()

        results = {
            'success':          success,
            'status':           status,
            'total_updated':    total_updated,
        }
        return results

    @staticmethod
    def retrieve_possible_duplicate_ballot_returned(
            google_civic_election_id,
            normalized_line1,
            normalized_zip,
            polling_location_we_vote_id):
        ballot_returned_list_objects = []
        ballot_returned_list_found = False
        status = ''

        if not positive_value_exists(normalized_line1) \
                and not positive_value_exists(normalized_zip):
            results = {
                'success':                      False,
                'status':                       "MISSING_LINE1_AND_ZIP",
                'google_civic_election_id':     google_civic_election_id,
                'ballot_returned_list_found':   ballot_returned_list_found,
                'ballot_returned_list':         ballot_returned_list_objects,
            }
            return results

        try:
            ballot_returned_queryset = BallotReturned.objects.all()
            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            ballot_returned_queryset = ballot_returned_queryset.filter(normalized_line1__iexact=normalized_line1)
            ballot_returned_queryset = ballot_returned_queryset.filter(normalized_zip__iexact=normalized_zip)

            # Ignore entries with polling_location_we_vote_id coming in from master server
            ballot_returned_queryset = ballot_returned_queryset.filter(~Q(
                polling_location_we_vote_id__iexact=polling_location_we_vote_id))

            ballot_returned_list_objects = ballot_returned_queryset

            if len(ballot_returned_list_objects):
                ballot_returned_list_found = True
                status += 'DUPLICATE_BALLOT_RETURNED_ITEMS_RETRIEVED'
                success = True
            else:
                status += 'NO_DUPLICATE_BALLOT_RETURNED_ITEMS_RETRIEVED'
                success = True
        except BallotReturned.DoesNotExist:
            # No ballot_returned found. Not a problem.
            status += 'NO_DUPLICATE_BALLOT_RETURNED_ITEMS_FOUND_DoesNotExist'
            ballot_returned_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_possible_duplicate_ballot_returned ' \
                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'google_civic_election_id':     google_civic_election_id,
            'ballot_returned_list_found':   ballot_returned_list_found,
            'ballot_returned_list':         ballot_returned_list_objects,
        }
        return results


class VoterBallotSaved(models.Model):
    """
    This is a table with a meta data about a voter's various elections they have looked at and might return to
    """
    # The unique id of the voter for which this ballot was retrieved
    voter_id = models.IntegerField(verbose_name="the voter unique id", default=0, null=False, blank=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False)
    state_code = models.CharField(verbose_name="state the ballot item is related to", max_length=2, null=True)

    election_description_text = models.CharField(max_length=255, blank=False, null=False,
                                                 verbose_name='text label for this election')
    # Note that internally we often use election_day_text ("YYYY-MM-DD") and then save it as election_date (DateField)
    election_date = models.DateField(verbose_name='election start date', null=True, auto_now=False)

    original_text_for_map_search = models.CharField(max_length=255, blank=False, null=False,
                                                    verbose_name='address as entered')
    original_text_city = models.CharField(max_length=255, null=True)
    original_text_state = models.CharField(max_length=255, null=True)
    original_text_zip = models.CharField(max_length=255, null=True)

    substituted_address_city = models.CharField(max_length=255, null=True)
    substituted_address_state = models.CharField(max_length=255, null=True)
    substituted_address_zip = models.CharField(max_length=255, null=True)
    substituted_address_nearby = models.CharField(max_length=255, blank=False, null=False,
                                                  verbose_name='address from nearby ballot_returned')

    is_from_substituted_address = models.BooleanField(default=False)
    is_from_test_ballot = models.BooleanField(default=False)

    # The map point for which this ballot was retrieved
    polling_location_we_vote_id_source = models.CharField(
        verbose_name="we vote permanent id of the map point this was copied from",
        max_length=255, default=None, null=True, blank=True, unique=False)

    # When we copy a ballot from a master ballot_returned entry, we want to store a link back to that source
    ballot_returned_we_vote_id = models.CharField(
        verbose_name="ballot_returned we_vote_id this was copied from",
        max_length=255, default=None, null=True, blank=True, unique=False)
    ballot_location_display_name = models.CharField(
        verbose_name="the name of the ballot the voter is looking at",
        max_length=255, default=None, null=True, blank=True, unique=False)
    ballot_location_shortcut = models.CharField(
        verbose_name="the url string used to find specific ballot",
        max_length=255, default=None, null=True, blank=True, unique=False)

    def election_day_text(self):
        if isinstance(self.election_date, date):
            return self.election_date.strftime('%Y-%m-%d')
        else:
            return ""

    def ballot_caveat(self):
        message = ''
        if self.is_from_substituted_address:
            message += "Ballot displayed is from a nearby address: '{substituted_address_nearby}'." \
                       "".format(substituted_address_nearby=self.substituted_address_nearby)
        if self.is_from_test_ballot:
            message += "Ballot displayed is a TEST ballot, and is for demonstration purposes only."
        return message


class VoterBallotSavedManager(models.Manager):

    @staticmethod
    def retrieve_ballots_per_voter_id(voter_id):
        voter_ballot_list = []
        voter_ballot_list_found = False
        status = ""
        success = False

        if positive_value_exists(voter_id):
            try:
                voter_ballot_list_queryset = VoterBallotSaved.objects.using('readonly').filter(voter_id=voter_id)
                voter_ballot_list_queryset = voter_ballot_list_queryset.order_by("-election_date")  # Newest first
                voter_ballot_list = list(voter_ballot_list_queryset)
                success = True
                status += "VOTER_BALLOT_LIST_RETRIEVED_PER_VOTER_ID"
                voter_ballot_list_found = len(voter_ballot_list)
            except Exception as e:
                success = False
                status += "VOTER_BALLOT_LIST_FAILED_TO_RETRIEVE_PER_VOTER_ID"
        else:
            status += "VOTER_BALLOT_LIST_NOT_RETRIEVED-MISSING_VOTER_ID"

        results = {
            'success':                  success,
            'status':                   status,
            'voter_ballot_list_found':  voter_ballot_list_found,
            'voter_ballot_list':        voter_ballot_list,
        }
        return results

    def __unicode__(self):
        return "VoterBallotSavedManager"

    def delete_voter_ballot_saved_by_voter_id(self, voter_id, google_civic_election_id):
        voter_ballot_saved_id = 0
        return self.delete_voter_ballot_saved(voter_ballot_saved_id, voter_id, google_civic_election_id)

    @staticmethod
    def delete_voter_ballot_saved(
            voter_ballot_saved_id=0,
            voter_id=0,
            google_civic_election_id=0,
            ballot_returned_we_vote_id="",
            ballot_location_shortcut=""):
        """

        :param voter_ballot_saved_id:
        :param voter_id:
        :param google_civic_election_id:
        :param ballot_returned_we_vote_id:
        :param ballot_location_shortcut:
        :return:
        """
        voter_ballot_saved_found = False
        voter_ballot_saved_deleted = False
        voter_ballot_saved = None
        status = ""

        try:
            if positive_value_exists(voter_ballot_saved_id):
                VoterBallotSaved.objects.get(id=voter_ballot_saved_id).delete()
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_deleted = True
                success = True
                status += "DELETE_VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_BALLOT_SAVED_ID "
            elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                voter_ballot_query = VoterBallotSaved.objects.filter(
                    voter_id=voter_id, google_civic_election_id=google_civic_election_id)
                voter_ballot_list = list(voter_ballot_query)
                for one_voter_ballot_saved in voter_ballot_list:
                    voter_ballot_saved_found = True
                    one_voter_ballot_saved.delete()
                    voter_ballot_saved_deleted = True
                # If still here, we found an existing voter_ballot_saved
                success = True
                status += "DELETE_VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ID_AND_GOOGLE_CIVIC "
            elif positive_value_exists(voter_id) and positive_value_exists(ballot_returned_we_vote_id):
                voter_ballot_query = VoterBallotSaved.objects.filter(
                    voter_id=voter_id, ballot_returned_we_vote_id=ballot_returned_we_vote_id)
                voter_ballot_list = list(voter_ballot_query)
                for one_voter_ballot_saved in voter_ballot_list:
                    voter_ballot_saved_found = True
                    one_voter_ballot_saved.delete()
                    voter_ballot_saved_deleted = True
                # If still here, we found an existing voter_ballot_saved
                success = True
                status += "DELETE_VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ID_AND_BALLOT_RETURNED_WE_VOTE_ID "
            elif positive_value_exists(voter_id) and positive_value_exists(ballot_location_shortcut):
                voter_ballot_query = VoterBallotSaved.objects.filter(
                    voter_id=voter_id, ballot_location_shortcut__iexact=ballot_location_shortcut)
                voter_ballot_list = list(voter_ballot_query)
                for one_voter_ballot_saved in voter_ballot_list:
                    voter_ballot_saved_found = True
                    one_voter_ballot_saved.delete()
                    voter_ballot_saved_deleted = True
                # If still here, we found an existing voter_ballot_saved
                success = True
                status += "DELETE_VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ID_AND_BALLOT_LOCATION_SHORTCUT "
            else:
                voter_ballot_saved_found = False
                voter_ballot_saved_deleted = False
                success = False
                status += "DELETE_VOTER_BALLOT_SAVED-COULD_NOT_RETRIEVE_VOTER_BALLOT_SAVED-MISSING_VARIABLES-DELETE "

        except VoterBallotSaved.DoesNotExist:
            success = True
            status += "DELETE_VOTER_BALLOT_SAVED_NOT_FOUND "
        except Exception as e:
            success = False
            status += "DELETE_VOTER_BALLOT_SAVED-CANNOT_DELETE " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'voter_ballot_saved_deleted':   voter_ballot_saved_deleted,
            'voter_ballot_saved_found':     voter_ballot_saved_found,
            'voter_ballot_saved':           voter_ballot_saved,
        }
        return results

    def retrieve_voter_ballot_saved_by_id(self, voter_ballot_saved_id):
        return self.retrieve_voter_ballot_saved(voter_ballot_saved_id)

    def retrieve_voter_ballot_saved_by_voter_id(self, voter_id, google_civic_election_id):
        voter_ballot_saved_id = 0
        return self.retrieve_voter_ballot_saved(voter_ballot_saved_id, voter_id, google_civic_election_id)

    def retrieve_voter_ballot_saved_by_ballot_returned_we_vote_id(self, voter_id, ballot_returned_we_vote_id):
        voter_ballot_saved_id = 0
        google_civic_election_id = 0
        text_for_map_search = ''
        return self.retrieve_voter_ballot_saved(
            voter_ballot_saved_id, voter_id, google_civic_election_id, text_for_map_search, ballot_returned_we_vote_id)

    def retrieve_voter_ballot_saved_by_ballot_location_shortcut(self, voter_id, ballot_location_shortcut):
        voter_ballot_saved_id = 0
        google_civic_election_id = 0
        text_for_map_search = ''
        ballot_returned_we_vote_id = ''
        return self.retrieve_voter_ballot_saved(
            voter_ballot_saved_id, voter_id, google_civic_election_id, text_for_map_search,
            ballot_returned_we_vote_id, ballot_location_shortcut)

    def retrieve_voter_ballot_saved_by_address_text(self, voter_id, text_for_map_search):
        voter_ballot_saved_id = 0
        google_civic_election_id = 0
        return self.retrieve_voter_ballot_saved(voter_ballot_saved_id, voter_id, google_civic_election_id,
                                                text_for_map_search)

    @staticmethod
    def retrieve_voter_ballot_saved(
            voter_ballot_saved_id,
            voter_id=0,
            google_civic_election_id=0,
            text_for_map_search='',
            ballot_returned_we_vote_id='',
            ballot_location_shortcut=''):
        """

        :param voter_ballot_saved_id:
        :param voter_id:
        :param google_civic_election_id:
        :param text_for_map_search:
        :param ballot_returned_we_vote_id:
        :param ballot_location_shortcut:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_ballot_saved_found = False
        voter_ballot_saved = None
        status = ""
        # Are we looking for a specific ballot?
        specific_ballot_requested = positive_value_exists(ballot_returned_we_vote_id) or \
            positive_value_exists(ballot_location_shortcut)

        # Note: We are not using the 'readonly' here intentionally
        try:
            if positive_value_exists(voter_ballot_saved_id):
                voter_ballot_saved = VoterBallotSaved.objects.get(id=voter_ballot_saved_id)
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_id = voter_ballot_saved.id
                voter_ballot_saved_found = True if positive_value_exists(voter_ballot_saved_id) else False
                success = True
                status += "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_BALLOT_SAVED_ID "
            elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                voter_ballot_saved = VoterBallotSaved.objects.get(
                    voter_id=voter_id, google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_id = voter_ballot_saved.id
                voter_ballot_saved_found = True if positive_value_exists(voter_ballot_saved_id) else False
                success = True
                status += "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ID_AND_GOOGLE_CIVIC "
            elif positive_value_exists(voter_id) and positive_value_exists(ballot_returned_we_vote_id):
                voter_ballot_saved = VoterBallotSaved.objects.get(
                    voter_id=voter_id, ballot_returned_we_vote_id__iexact=ballot_returned_we_vote_id)
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_id = voter_ballot_saved.id
                voter_ballot_saved_found = True if positive_value_exists(voter_ballot_saved_id) else False
                success = True
                status += "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ID_AND_BALLOT_RETURNED_ID "
            elif positive_value_exists(voter_id) and positive_value_exists(ballot_location_shortcut):
                voter_ballot_saved = VoterBallotSaved.objects.get(
                    voter_id=voter_id, ballot_location_shortcut__iexact=ballot_location_shortcut)
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_id = voter_ballot_saved.id
                voter_ballot_saved_found = True if positive_value_exists(voter_ballot_saved_id) else False
                success = True
                status += "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ID_AND_BALLOT_LOCATION_SHORTCUT "
            else:
                voter_ballot_saved_found = False
                success = False
                status += "COULD_NOT_RETRIEVE_VOTER_BALLOT_SAVED-MISSING_VARIABLES1 "

        except VoterBallotSaved.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            success = False
            status += "MULTIPLE_VOTER_BALLOT_SAVED_FOUND-MUST_DELETE_ALL "
        except VoterBallotSaved.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "VOTER_BALLOT_SAVED_NOT_FOUND1 "

        # If here, a voter_ballot_saved not found yet, and not looking for specific ballot or
        # a ballot by google_civic_election_id, then try to find list of entries saved under this address
        # and return the most recent
        if not voter_ballot_saved_found and not specific_ballot_requested and not \
                positive_value_exists(google_civic_election_id):
            try:
                if positive_value_exists(text_for_map_search) and positive_value_exists(voter_id):
                    # Start with narrowest search
                    voter_ballot_saved_queryset = VoterBallotSaved.objects.all()
                    voter_ballot_saved_queryset = voter_ballot_saved_queryset.filter(
                        voter_id=voter_id, original_text_for_map_search__iexact=text_for_map_search)
                    # Return the latest google_civic_election_id first
                    voter_ballot_saved_queryset = voter_ballot_saved_queryset.order_by('-google_civic_election_id')
                    voter_ballot_saved = voter_ballot_saved_queryset.first()

                    status += "VOTER_BALLOT_SAVED_LIST_FOUND2 "
                    voter_ballot_saved_found = True
                    success = True
                else:
                    voter_ballot_saved_found = False
                    success = False
                    status += "COULD_NOT_RETRIEVE_VOTER_BALLOT_SAVED-MISSING_VARIABLES2 "

            except VoterBallotSaved.DoesNotExist:
                exception_does_not_exist = True
                success = True
                status += "VOTER_BALLOT_SAVED_NOT_FOUND2 "

        if positive_value_exists(voter_ballot_saved_found):
            # If an address exists
            if positive_value_exists(voter_ballot_saved.original_text_for_map_search):
                # ...we want to make sure we have the city/state/zip breakdown
                if not positive_value_exists(voter_ballot_saved.original_text_city) \
                        or not positive_value_exists(voter_ballot_saved.original_text_state) \
                        or not positive_value_exists(voter_ballot_saved.original_text_zip):
                    retrieve_results = \
                        retrieve_address_fields_from_geocoder(voter_ballot_saved.original_text_for_map_search)
                    if positive_value_exists(retrieve_results['success']):
                        try:
                            voter_ballot_saved.original_text_city = retrieve_results['city']
                            voter_ballot_saved.original_text_state = retrieve_results['state_code']
                            voter_ballot_saved.original_text_zip = retrieve_results['zip_long']
                            voter_ballot_saved.save()
                            status += "ORIGINAL_TEXT_UPDATED "
                        except Exception as e:
                            status += "COULD_NOT_SAVE_VOTER_BALLOT_SAVED-ORIGINAL_TEXT: " + str(e) + " "
            # If a substituted address exists
            if positive_value_exists(voter_ballot_saved.substituted_address_nearby):
                # ...we want to make sure we have the city/state/zip breakdown
                if not positive_value_exists(voter_ballot_saved.substituted_address_city) \
                        or not positive_value_exists(voter_ballot_saved.substituted_address_state) \
                        or not positive_value_exists(voter_ballot_saved.substituted_address_zip):
                    retrieve_results = \
                        retrieve_address_fields_from_geocoder(voter_ballot_saved.substituted_address_nearby)
                    if positive_value_exists(retrieve_results['success']):
                        try:
                            voter_ballot_saved.substituted_address_city = retrieve_results['city']
                            voter_ballot_saved.substituted_address_state = retrieve_results['state_code']
                            voter_ballot_saved.substituted_address_zip = retrieve_results['zip_long']
                            voter_ballot_saved.save()
                            status += "SUBSTITUTED_ADDRESS_UPDATED "
                        except Exception as e:
                            status += "COULD_NOT_SAVE_VOTER_BALLOT_SAVED-SUBSTITUTED_ADDRESS: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_ballot_saved_found': voter_ballot_saved_found,
            'voter_ballot_saved':       voter_ballot_saved,
        }
        return results
    
    @staticmethod
    def retrieve_voter_ballot_saved_list_for_election(
            google_civic_election_id,
            polling_location_we_vote_id_source="",
            state_code="",
            find_only_entries_not_copied_from_polling_location=False,
            find_all_entries_for_election=False,
            read_only=False):
        status = ""
        google_civic_election_id = convert_to_int(google_civic_election_id)
        voter_ballot_saved_list = []
        voter_ballot_saved_list_found = False
        sufficient_variables_received = positive_value_exists(polling_location_we_vote_id_source) \
            or find_only_entries_not_copied_from_polling_location or find_all_entries_for_election
        if not positive_value_exists(google_civic_election_id) or not sufficient_variables_received:
            status += "RETRIEVE_VOTER_BALLOT_SAVED_LIST-MISSING_REQUIRED_VARIABLE(S) "
            results = {
                'success':                          True if voter_ballot_saved_list_found else False,
                'status':                           status,
                'voter_ballot_saved_list_found':    voter_ballot_saved_list_found,
                'voter_ballot_saved_list':          voter_ballot_saved_list,
            }
            return results

        try:
            if positive_value_exists(read_only):
                voter_ballot_saved_queryset = VoterBallotSaved.objects.using('readonly').order_by('-id')
            else:
                voter_ballot_saved_queryset = VoterBallotSaved.objects.order_by('-id')

            voter_ballot_saved_queryset = voter_ballot_saved_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                voter_ballot_saved_queryset = voter_ballot_saved_queryset.filter(
                    state_code__iexact=state_code)
            if positive_value_exists(polling_location_we_vote_id_source):
                voter_ballot_saved_queryset = voter_ballot_saved_queryset.filter(
                    polling_location_we_vote_id_source__iexact=polling_location_we_vote_id_source)
            elif positive_value_exists(find_only_entries_not_copied_from_polling_location):
                voter_ballot_saved_queryset = voter_ballot_saved_queryset.filter(
                    Q(polling_location_we_vote_id_source=None) | Q(polling_location_we_vote_id_source=""))
            voter_ballot_saved_list = list(voter_ballot_saved_queryset)

            if len(voter_ballot_saved_list):
                voter_ballot_saved_list_found = True
                status += 'VOTER_BALLOT_SAVED_LIST_FOUND '
            else:
                status += 'NO_VOTER_BALLOT_SAVED_LIST_FOUND '
        except VoterBallotSaved.DoesNotExist:
            # No ballot items found. Not a problem.
            status += 'NO_VOTER_BALLOT_SAVED_LIST_FOUND_DOES_NOT_EXIST '
            voter_ballot_saved_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_voter_ballot_saved_list_for_election ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        results = {
            'success':                          True if voter_ballot_saved_list_found else False,
            'status':                           status,
            'voter_ballot_saved_list_found':    voter_ballot_saved_list_found,
            'voter_ballot_saved_list':          voter_ballot_saved_list,
        }
        return results

    def update_or_create_voter_ballot_saved(
            self,
            voter_id=0,
            google_civic_election_id='',
            state_code='',
            election_day_text='',
            election_description_text='',
            original_text_for_map_search='',
            substituted_address_nearby='',
            is_from_substituted_address=False,
            is_from_test_ballot=False,
            polling_location_we_vote_id_source='',
            ballot_location_display_name=None,
            ballot_returned_we_vote_id=None,
            ballot_location_shortcut='',
            called_recursively=False,
            original_text_city='',
            original_text_state='',
            original_text_zip='',
            substituted_address_city='',
            substituted_address_state='',
            substituted_address_zip=''):
        # We assume that we tried to find an entry for this voter
        success = False
        status = ""
        voter_ballot_saved_found = False

        ballot_location_shortcut = str(ballot_location_shortcut)
        ballot_location_shortcut = ballot_location_shortcut.strip().lower()
        try:
            defaults = {
                'ballot_location_display_name': ballot_location_display_name,
                'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
                'ballot_location_shortcut': ballot_location_shortcut,
                'google_civic_election_id': google_civic_election_id,
                'election_description_text': election_description_text,
                'is_from_substituted_address': is_from_substituted_address,
                'is_from_test_ballot': is_from_test_ballot,
                'original_text_for_map_search': original_text_for_map_search,
                'original_text_city': original_text_city,
                'original_text_state': original_text_state,
                'original_text_zip': original_text_zip,
                'polling_location_we_vote_id_source': polling_location_we_vote_id_source,
                'state_code': state_code,
                'substituted_address_nearby': substituted_address_nearby,
                'substituted_address_city': substituted_address_city,
                'substituted_address_state': substituted_address_state,
                'substituted_address_zip': substituted_address_zip,
                'voter_id': voter_id,
            }
            if positive_value_exists(election_day_text):
                defaults['election_date'] = election_day_text

            if positive_value_exists(voter_id) and positive_value_exists(ballot_returned_we_vote_id):
                status += "SAVING_WITH_VOTER_ID_AND_BALLOT_RETURNED_WE_VOTE_ID "
                voter_ballot_saved, created = VoterBallotSaved.objects.update_or_create(
                    voter_id=voter_id,
                    ballot_returned_we_vote_id=ballot_returned_we_vote_id,
                    defaults=defaults,
                )
                voter_ballot_saved_found = voter_ballot_saved.id
                status += "BALLOT_SAVED-ballot_returned_we_vote_id "
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(ballot_location_shortcut):
                status += "SAVING_WITH_VOTER_ID_AND_BALLOT_LOCATION_SHORTCUT "
                voter_ballot_saved, created = VoterBallotSaved.objects.update_or_create(
                    voter_id=voter_id,
                    ballot_location_shortcut=ballot_location_shortcut,
                    defaults=defaults,
                )
                voter_ballot_saved_found = voter_ballot_saved.id
                status += "BALLOT_SAVED-BALLOT_LOCATION_SHORTCUT "
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                status += "SAVING_WITH_VOTER_ID_AND_GOOGLE_CIVIC_ELECTION_ID "
                voter_ballot_saved, created = VoterBallotSaved.objects.update_or_create(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    defaults=defaults,
                )
                voter_ballot_saved_found = voter_ballot_saved.id
                status += "BALLOT_SAVED-VOTER_ID_AND_ELECTION_ID "
                success = True
            else:
                voter_ballot_saved = None
                status += "UNABLE_TO_CREATE_BALLOT_SAVED "
                success = False
                google_civic_election_id = 0
        except VoterBallotSaved.MultipleObjectsReturned as e:
            status += "EXCEPTION-MultipleObjectsReturned "
            voter_ballot_saved = None
            voter_ballot_saved_manager = VoterBallotSavedManager()
            voter_ballot_saved_manager.delete_voter_ballot_saved(
                voter_ballot_saved_id=0,
                voter_id=voter_id,
                google_civic_election_id=google_civic_election_id,
                ballot_returned_we_vote_id=ballot_returned_we_vote_id,
                ballot_location_shortcut=ballot_location_shortcut)
            if not positive_value_exists(called_recursively):
                called_recursively = True
                return self.update_or_create_voter_ballot_saved(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    election_day_text=election_day_text,
                    election_description_text=election_description_text,
                    original_text_for_map_search=original_text_for_map_search,
                    substituted_address_nearby=substituted_address_nearby,
                    is_from_substituted_address=is_from_substituted_address,
                    is_from_test_ballot=is_from_test_ballot,
                    polling_location_we_vote_id_source=polling_location_we_vote_id_source,
                    ballot_location_display_name=ballot_location_display_name,
                    ballot_returned_we_vote_id=ballot_returned_we_vote_id,
                    ballot_location_shortcut=ballot_location_shortcut,
                    called_recursively=called_recursively,
                    original_text_city=original_text_city,
                    original_text_state=original_text_state,
                    original_text_zip=original_text_zip,
                    substituted_address_city=substituted_address_city,
                    substituted_address_state=substituted_address_state,
                    substituted_address_zip=substituted_address_zip)

        except Exception as e:
            status += 'UNABLE_TO_CREATE_BALLOT_SAVED_EXCEPTION: ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            success = False
            voter_ballot_saved = None
            google_civic_election_id = 0

        results = {
            'status':                   status,
            'success':                  success,
            'voter_ballot_saved_found': voter_ballot_saved_found,
            'voter_ballot_saved':       voter_ballot_saved,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               state_code,
        }
        return results


def find_best_previously_stored_ballot_returned(
        voter_id,
        text_for_map_search,
        google_civic_election_id=0,
        ballot_returned_we_vote_id='',
        ballot_location_shortcut=''):
    """
    We are looking for the most recent ballot near this voter. We may or may not have a google_civic_election_id
    :param voter_id:
    :param text_for_map_search:
    :param google_civic_election_id:
    :param ballot_returned_we_vote_id:
    :param ballot_location_shortcut:
    :return:
    """
    status = ""
    ballot_returned_manager = BallotReturnedManager()
    # voter_ballot_saved_manager = VoterBallotSavedManager()
    # ballot_item_list_manager = BallotItemListManager()

    text_for_map_search_empty = not positive_value_exists(text_for_map_search) or text_for_map_search == ""

    if positive_value_exists(ballot_returned_we_vote_id):
        find_results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(
            ballot_returned_we_vote_id)
        status += "CALLING-RETRIEVE_BALLOT_RETURNED_FROM_WE_VOTE_ID, status: [["
        status += find_results['status']
        status += "]] "

        if not find_results['ballot_returned_found']:
            error_results = {
                'ballot_returned_found':               False,
                'ballot_location_display_name':        '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'election_day_text':                   '',
                'election_description_text':            '',
                'google_civic_election_id':             google_civic_election_id,
                'polling_location_we_vote_id_source':   '',
                'state_code':                           '',
                'status':                               status,
                'substituted_address_nearby':           '',
                'substituted_address_city':             '',
                'substituted_address_state':            '',
                'substituted_address_zip':              '',
                'text_for_map_search':                  text_for_map_search,
                'original_text_city':                   '',
                'original_text_state':                  '',
                'original_text_zip':                    '',
                'voter_id':                             voter_id,
            }
            return error_results

        # A specific ballot was found.
        closest_ballot_returned = find_results['ballot_returned']
    elif positive_value_exists(ballot_location_shortcut):
        find_results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_location_shortcut(
            ballot_location_shortcut)
        status += "CALLING-RETRIEVE_BALLOT_RETURNED_FROM_BALLOT_LOCATION_SHORTCUT, status: [["
        status += find_results['status']
        status += "]] "

        if not find_results['ballot_returned_found']:
            error_results = {
                'ballot_returned_found':               False,
                'ballot_location_display_name':        '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'election_day_text':                   '',
                'election_description_text':            '',
                'google_civic_election_id':             google_civic_election_id,
                'polling_location_we_vote_id_source':   '',
                'state_code':                           '',
                'status':                               status,
                'substituted_address_nearby':           '',
                'substituted_address_city':             '',
                'substituted_address_state':            '',
                'substituted_address_zip':              '',
                'text_for_map_search':                  text_for_map_search,
                'original_text_city':                   '',
                'original_text_state':                  '',
                'original_text_zip':                    '',
                'voter_id':                             voter_id,
            }
            return error_results

        # A specific ballot was found.
        closest_ballot_returned = find_results['ballot_returned']
    elif positive_value_exists(google_civic_election_id) and text_for_map_search_empty:
        find_results = ballot_returned_manager.retrieve_ballot_returned_from_google_civic_election_id(
            google_civic_election_id)
        status += "1-CALLING-RETRIEVE_BALLOT_RETURNED_FROM_GOOGLE_CIVIC_ELECTION_ID, status: [["
        status += find_results['status']
        status += "]] "

        if not find_results['ballot_returned_found']:
            error_results = {
                'ballot_returned_found':               False,
                'ballot_location_display_name':        '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'election_day_text':                   '',
                'election_description_text':            '',
                'google_civic_election_id':             google_civic_election_id,
                'polling_location_we_vote_id_source':   '',
                'state_code':                           '',
                'status':                               status,
                'substituted_address_nearby':           '',
                'substituted_address_city':             '',
                'substituted_address_state':            '',
                'substituted_address_zip':              '',
                'text_for_map_search':                  text_for_map_search,
                'original_text_city':                   '',
                'original_text_state':                  '',
                'original_text_zip':                    '',
                'voter_id':                             voter_id,
            }
            return error_results

        # A specific ballot was found.
        closest_ballot_returned = find_results['ballot_returned']
    elif text_for_map_search_empty:
        status += "TEXT_FOR_MAP_SEARCH_EMPTY "

        error_results = {
            'ballot_returned_found': False,
            'ballot_location_display_name': '',
            'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
            'ballot_location_shortcut': ballot_location_shortcut,
            'election_day_text': '',
            'election_description_text': '',
            'google_civic_election_id': google_civic_election_id,
            'polling_location_we_vote_id_source': '',
            'state_code': '',
            'status': status,
            'substituted_address_nearby': '',
            'substituted_address_city': '',
            'substituted_address_state': '',
            'substituted_address_zip': '',
            'text_for_map_search': text_for_map_search,
            'original_text_city': '',
            'original_text_state': '',
            'original_text_zip': '',
            'voter_id': voter_id,
        }
        return error_results
    else:
        find_results = ballot_returned_manager.find_closest_ballot_returned(
            text_for_map_search, google_civic_election_id)
        status += "CALLING-FIND_CLOSEST_BALLOT_RETURNED, status: [["
        status += find_results['status']
        status += "]] "

        if not find_results['ballot_returned_found']:
            error_results = {
                'ballot_returned_found':               False,
                'ballot_location_display_name':        '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'election_day_text':                   '',
                'election_description_text':            '',
                'google_civic_election_id':             google_civic_election_id,
                'polling_location_we_vote_id_source':   '',
                'state_code':                           '',
                'status':                               status,
                'substituted_address_nearby':           '',
                'substituted_address_city':             '',
                'substituted_address_state':            '',
                'substituted_address_zip':              '',
                'text_for_map_search':                  text_for_map_search,
                'original_text_city':                   '',
                'original_text_state':                  '',
                'original_text_zip':                    '',
                'voter_id':                             voter_id,
            }
            return error_results

        # A ballot at a nearby address was found.
        closest_ballot_returned = find_results['ballot_returned']  # Was ballot_returned_to_copy

    # DALE NOTE: I don't think this is correct, but I'm not ready to delete
    # # Remove all prior ballot items, so we make room for copy_ballot_items to save ballot items
    # # 2017-11-03 We only want to delete if the ballot_returned in question has a polling_location_we_vote_id
    # if positive_value_exists(ballot_returned_to_copy.google_civic_election_id) and \
    #         positive_value_exists(ballot_returned_to_copy.polling_location_we_vote_id):
    #     voter_ballot_saved_id = 0
    #     voter_ballot_saved_results = voter_ballot_saved_manager.delete_voter_ballot_saved(
    #         voter_ballot_saved_id, voter_id, ballot_returned_to_copy.google_civic_election_id)
    #
    #     # We include a google_civic_election_id, so only the ballot info for this election is removed
    #     ballot_item_list_manager.delete_all_ballot_items_for_voter(
    #         voter_id, ballot_returned_to_copy.google_civic_election_id)
    # else:
    #     status += "NOT_DELETED-voter_ballot_saved-AND-VOTER_BALLOT_ITEMS "
    #
    # # ...and then copy it for the voter as long as it doesn't already belong to the voter
    # if ballot_returned_to_copy.voter_id != voter_id:
    #     copy_item_results = ballot_item_list_manager.copy_ballot_items(ballot_returned_to_copy, voter_id)
    #     status += copy_item_results['status']
    #
    #     if not copy_item_results['ballot_returned_copied']:
    #         error_results = {
    #             'ballot_returned_found':               False,
    #             'ballot_location_display_name':        '',
    #             'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
    #             'ballot_location_shortcut':             ballot_location_shortcut,
    #             'election_day_text':                   '',
    #             'election_description_text':            '',
    #             'google_civic_election_id':             google_civic_election_id,
    #             'polling_location_we_vote_id_source':   '',
    #             'state_code':                           '',
    #             'status':                               status,
    #             'substituted_address_nearby':           '',
    #             'substituted_address_city':             '',
    #             'substituted_address_state':            '',
    #             'substituted_address_zip':              '',
    #             'text_for_map_search':                  text_for_map_search,
    #             'original_text_city':                   '',
    #             'original_text_state':                  '',
    #             'original_text_zip':                    '',
    #             'voter_id':                             voter_id,
    #         }
    #         return error_results

    # VoterBallotSaved is updated, outside this function

    if closest_ballot_returned:
        results = {
            'voter_id': voter_id,
            'google_civic_election_id': closest_ballot_returned.google_civic_election_id,
            'state_code': closest_ballot_returned.normalized_state,
            'election_day_text': closest_ballot_returned.election_day_text(),
            'election_description_text': closest_ballot_returned.election_description_text,
            'text_for_map_search': closest_ballot_returned.text_for_map_search,
            'original_text_city': closest_ballot_returned.normalized_city,
            'original_text_state': closest_ballot_returned.normalized_state,
            'original_text_zip': closest_ballot_returned.normalized_zip,
            'substituted_address_nearby': closest_ballot_returned.text_for_map_search,
            'substituted_address_city': closest_ballot_returned.normalized_city,
            'substituted_address_state': closest_ballot_returned.normalized_state,
            'substituted_address_zip': closest_ballot_returned.normalized_zip,
            'ballot_returned_found': True,
            'ballot_location_display_name': closest_ballot_returned.ballot_location_display_name,
            'ballot_returned_we_vote_id': closest_ballot_returned.we_vote_id,
            'ballot_location_shortcut': closest_ballot_returned.ballot_location_shortcut if
            closest_ballot_returned.ballot_location_shortcut else '',
            'polling_location_we_vote_id_source': closest_ballot_returned.polling_location_we_vote_id,
            'status': status,
        }
    else:
        status += "CLOSEST_BALLOT_RETURNED_NOT_FOUND "
        results = {
            'voter_id': voter_id,
            'google_civic_election_id': 0,
            'state_code': '',
            'election_day_text': '',
            'election_description_text': '',
            'text_for_map_search': '',
            'original_text_city': '',
            'original_text_state': '',
            'original_text_zip': '',
            'substituted_address_nearby': '',
            'substituted_address_city': '',
            'substituted_address_state': '',
            'substituted_address_zip': '',
            'ballot_returned_found': False,
            'ballot_location_display_name': '',
            'ballot_returned_we_vote_id': '',
            'ballot_location_shortcut': '',
            'polling_location_we_vote_id_source': '',
            'status': status,
        }
    return results


def retrieve_address_fields_from_geocoder(text_for_map_search):
    success = True
    status = ""
    city = ""
    longitude = None
    latitude = None
    state_code = ""
    zip_long = ""
    try:
        google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
        location = google_client.geocode(text_for_map_search, sensor=False, timeout=GEOCODE_TIMEOUT)
        if location is None:
            status += 'REFRESH_ADDRESS_FIELDS: Could not find location matching "{}" '.format(text_for_map_search)
            logger.debug(status)
        else:
            latitude = location.latitude
            longitude = location.longitude
            # Retrieve the ZIP code
            if hasattr(location, 'raw'):
                if 'address_components' in location.raw:
                    for one_address_component in location.raw['address_components']:
                        if 'administrative_area_level_1' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['short_name']):
                            state_code = one_address_component['short_name']
                        if 'locality' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['long_name']):
                            city = one_address_component['long_name']
                        if 'postal_code' in one_address_component['types'] \
                                and positive_value_exists(one_address_component['long_name']):
                            zip_long = one_address_component['long_name']
            status += "GEOCODER_WORKED "
    except Exception as e:
        status += "RETRIEVE_ADDRESS_FIELDS_FROM_GEOCODER_FAILED " + str(e) + " "
    results = {
        'success':      success,
        'status':       status,
        'city':         city,
        'latitude':     latitude,
        'longitude':    longitude,
        'state_code':   state_code,
        'zip_long':     zip_long,
    }
    return results
