# ballot/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateCampaign
from config.base import get_environment_variable
from datetime import date, datetime
from django.db import models
from django.db.models import F, Q, Count
from election.models import ElectionManager
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from geopy.geocoders import get_geocoder_for_service
from geopy.exc import GeocoderQuotaExceeded
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
from polling_location.models import PollingLocationManager
import wevote_functions.admin
from wevote_functions.functions import convert_date_to_date_as_integer, convert_to_int, positive_value_exists
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

logger = wevote_functions.admin.get_logger(__name__)


class BallotItem(models.Model):
    """
    This is a generated table with ballot item data from a variety of sources, including Google Civic
    One ballot item is either 1) a measure/referendum or 2) an office that is being competed for
    """
    # The unique id of the voter for which this ballot was retrieved
    voter_id = models.IntegerField(verbose_name="the voter unique id", default=0, null=False, blank=False)
    # The polling location for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the polling location", max_length=255, default=None, null=True,
        blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id", max_length=20, null=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False)
    state_code = models.CharField(verbose_name="state the ballot item is related to", max_length=2, null=True)

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
        blank=True, unique=False)
    # The local database id for this measure, specific to this server.
    # TODO contest_measure_id should be positive integer as opposed to CharField
    contest_measure_id = models.CharField(
        verbose_name="contest_measure unique id", max_length=255, null=True, blank=True)
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this measure", max_length=255, default=None, null=True,
        blank=True, unique=False)
    # This is a sortable name, either the candidate name or the measure name
    ballot_item_display_name = models.CharField(verbose_name="a label we can sort by", max_length=255, null=True,
                                                blank=True)

    measure_subtitle = models.TextField(verbose_name="google civic referendum subtitle",
                                        null=True, blank=True, default="")
    measure_text = models.TextField(verbose_name="measure text", null=True, blank=True, default="")

    def is_contest_office(self):
        if self.contest_office_id:
            return True
        return False

    def is_contest_measure(self):
        if self.contest_measure_id:
            return True
        return False

    def display_ballot_item(self):
        return self.ballot_item_display_name

    def fetch_ballot_order(self):
        return 3

    def candidates_list(self):
        candidates_list_temp = CandidateCampaign.objects.all()
        candidates_list_temp = candidates_list_temp.filter(google_civic_election_id=self.google_civic_election_id)
        candidates_list_temp = candidates_list_temp.filter(contest_office_id=self.contest_office_id)
        return candidates_list_temp


class BallotItemManager(models.Model):

    def retrieve_ballot_item(self, ballot_item_id=0):

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
            handle_record_found_more_than_one_exception(e, logger)
            ballot_item_found = False
            status = "ERROR_MORE_THAN_ONE_ELECTION_FOUND"
            success = False
        except BallotItem.DoesNotExist:
            ballot_item_found = False
            status = "ELECTION_NOT_FOUND"
            success = True

        results = {
            'success':              success,
            'status':               status,
            'ballot_item_found':    ballot_item_found,
            'ballot_item':          ballot_item,
        }
        return results

    def update_or_create_ballot_item_for_voter(
            self, voter_id, google_civic_election_id, google_ballot_placement,
            ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
            contest_office_id=0, contest_office_we_vote_id='',
            contest_measure_id=0, contest_measure_we_vote_id='', state_code=''):
        exception_multiple_object_returned = False
        new_ballot_item_created = False

        # We require both contest_office_id and contest_office_we_vote_id
        #  OR both contest_measure_id and contest_measure_we_vote_id
        required_office_ids_found = positive_value_exists(contest_office_id) \
            and positive_value_exists(contest_office_we_vote_id)
        required_measure_ids_found = positive_value_exists(contest_measure_id) \
            and positive_value_exists(contest_measure_we_vote_id)
        contest_or_measure_identifier_found = required_office_ids_found or required_measure_ids_found
        if not contest_or_measure_identifier_found:
            success = False
            status = 'MISSING_SUFFICIENT_OFFICE_OR_MEASURE_IDS '
        # If here, then we know that there are sufficient office or measure ids
        elif not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID '
        elif not voter_id:
            success = False
            status = 'MISSING_VOTER_ID '
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
                # We search with contest_measure_id and contest_office_id because they are (will be) integers,
                #  which will be a faster search
                ballot_item_on_stage, new_ballot_item_created = BallotItem.objects.get_or_create(
                    contest_measure_id__exact=contest_measure_id,
                    contest_office_id__exact=contest_office_id,
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_id__exact=voter_id,
                    defaults=create_values)

                # if a ballot_item is found (instead of just created), *then* update it
                # Note, we never update google_civic_election_id or voter_id
                if not new_ballot_item_created:
                    ballot_item_on_stage.contest_office_id = contest_office_id
                    ballot_item_on_stage.contest_office_we_vote_id = contest_office_we_vote_id
                    ballot_item_on_stage.contest_measure_id = contest_measure_id
                    ballot_item_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                    ballot_item_on_stage.google_ballot_placement = google_ballot_placement
                    ballot_item_on_stage.local_ballot_order = local_ballot_order
                    ballot_item_on_stage.ballot_item_display_name = ballot_item_display_name
                    ballot_item_on_stage.measure_subtitle = measure_subtitle
                    ballot_item_on_stage.measure_text = measure_text
                    ballot_item_on_stage.save()

                    success = True
                    status = 'BALLOT_ITEM_UPDATED '
                else:
                    success = True
                    status = 'BALLOT_ITEM_CREATED '

            except BallotItemManager.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_BALLOT_ITEMS_FOUND '
                exception_multiple_object_returned = True

        results = {
            'success':                 success,
            'status':                  status,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'new_ballot_item_created': new_ballot_item_created,
        }
        return results

    def update_or_create_ballot_item_for_polling_location(
            self, polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
            ballot_item_display_name, measure_subtitle, measure_text, local_ballot_order,
            contest_office_id=0, contest_office_we_vote_id='',
            contest_measure_id=0, contest_measure_we_vote_id='', state_code=''):
        exception_multiple_object_returned = False
        new_ballot_item_created = False

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
            status = 'MISSING_SUFFICIENT_OFFICE_OR_MEASURE_IDS-POLLING_LOCATION'
        # If here, then we know that there are sufficient office or measure ids
        elif not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID-POLLING_LOCATION'
        elif not polling_location_we_vote_id:
            success = False
            status = 'MISSING_POLLING_LOCATION_WE_VOTE_ID'
        #  We Vote Server doesn't have a matching polling location yet.
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
                # We search with contest_measure_id and contest_office_id because they are (will be) integers,
                #  which will be a faster search
                ballot_item_on_stage, new_ballot_item_created = BallotItem.objects.get_or_create(
                    contest_measure_id__exact=contest_measure_id,
                    contest_office_id__exact=contest_office_id,
                    google_civic_election_id__exact=google_civic_election_id,
                    polling_location_we_vote_id__iexact=polling_location_we_vote_id,
                    defaults=create_values)

                # if a ballot_item is found (instead of just created), *then* update it
                # Note, we never update google_civic_election_id or voter_id
                if not new_ballot_item_created:
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
                    ballot_item_on_stage.save()

                    success = True
                    status = 'BALLOT_ITEM_UPDATED-POLLING_LOCATION'
                else:
                    success = True
                    status = 'BALLOT_ITEM_CREATED-POLLING_LOCATION'

            except BallotItemManager.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_BALLOT_ITEMS_FOUND-POLLING_LOCATION '
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_ballot_item_created':  new_ballot_item_created,
        }
        return results


class BallotItemListManager(models.Model):
    """
    A way to work with a list of ballot_items
    """

    def delete_all_ballot_items_for_voter(self, voter_id, google_civic_election_id):
        ballot_item_list_deleted = False
        try:
            ballot_item_queryset = BallotItem.objects.filter(voter_id=voter_id)
            if positive_value_exists(google_civic_election_id):
                ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_queryset.delete()

            ballot_item_list_deleted = True
            status = 'BALLOT_ITEMS_DELETED'
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_DELETED_DoesNotExist'
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED delete_all_ballot_items_for_voter ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                  True if ballot_item_list_deleted else False,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'voter_id':                 voter_id,
            'ballot_item_list_deleted': ballot_item_list_deleted,
        }
        return results

    def retrieve_ballot_items_for_election(self, google_civic_election_id):
        ballot_item_list = []
        ballot_item_list_found = False
        try:
            # We cannot use 'readonly' because the result set sometimes gets modified with .save()
            ballot_item_queryset = BallotItem.objects.all()
            ballot_item_queryset = ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            ballot_item_list = list(ballot_item_queryset)

            if positive_value_exists(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND '
            else:
                status = 'NO_BALLOT_ITEMS_FOUND, not positive_value_exists '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_FOUND '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_ballot_items_for_election ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        results = {
            'success':                  True if ballot_item_list_found else False,
            'status':                   status,
            'ballot_item_list_found':   ballot_item_list_found,
            'ballot_item_list':         ballot_item_list,
        }
        return results

    def retrieve_ballot_items_for_election_lacking_state(self, google_civic_election_id, number_to_retrieve=5000):
        """

        :param google_civic_election_id:
        :param number_to_retrieve: Repairing 1000 ballot items takes about 9 seconds.
        :return:
        """
        ballot_item_list = []
        ballot_item_list_found = False
        try:
            ballot_item_queryset = BallotItem.objects.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_queryset = ballot_item_queryset.filter(Q(state_code=None) | Q(state_code=""))
            ballot_item_list = list(ballot_item_queryset[:number_to_retrieve])

            if positive_value_exists(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND_WITHOUT_STATE '
            else:
                status = 'NO_BALLOT_ITEMS_WITHOUT_STATE_FOUND, not positive_value_exists '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_WITHOUT_STATE_FOUND '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_ballot_items_for_election_lacking_state ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                  True if ballot_item_list_found else False,
            'status':                   status,
            'ballot_item_list_found':   ballot_item_list_found,
            'ballot_item_list':         ballot_item_list,
        }
        return results

    def count_ballot_items_for_election_lacking_state(self, google_civic_election_id):
        ballot_item_list_count = 0
        success = False
        try:
            ballot_item_queryset = BallotItem.objects.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_queryset = ballot_item_queryset.filter(Q(state_code=None) | Q(state_code=""))
            ballot_item_list_count = ballot_item_queryset.count()

            status = 'BALLOT_ITEMS_WITHOUT_STATE_FOUND '
            success = True
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_WITHOUT_STATE_FOUND '
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_ballot_items_for_election_lacking_state ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                  success,
            'status':                   status,
            'ballot_item_list_count':   ballot_item_list_count,
        }
        return results

    def retrieve_all_ballot_items_for_voter(self, voter_id, google_civic_election_id):
        polling_location_we_vote_id = ''
        ballot_item_list = []
        ballot_item_list_found = False
        try:
            # Intentionally not using 'readonly' here
            ballot_item_queryset = BallotItem.objects.all()
            ballot_item_queryset = ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(voter_id=voter_id)
            if positive_value_exists(google_civic_election_id):
                ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_list = ballot_item_queryset

            if len(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_voter '
            else:
                status = 'NO_BALLOT_ITEMS_FOUND_0 '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_FOUND_DoesNotExist '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_ballot_items_for_voter ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if ballot_item_list_found else False,
            'status':                       status,
            'google_civic_election_id':     google_civic_election_id,
            'voter_id':                     voter_id,
            'polling_location_we_vote_id':  polling_location_we_vote_id,
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results

    def retrieve_all_ballot_items_for_polling_location(self, polling_location_we_vote_id, google_civic_election_id):
        voter_id = 0
        ballot_item_list = []
        ballot_item_list_found = False
        try:
            ballot_item_queryset = BallotItem.objects.using('readonly').all()
            ballot_item_queryset = ballot_item_queryset.order_by('local_ballot_order', 'google_ballot_placement')
            ballot_item_queryset = ballot_item_queryset.filter(polling_location_we_vote_id=polling_location_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_list = ballot_item_queryset

            if len(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_polling_location '
            else:
                status = 'NO_BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_polling_location '
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_FOUND_DoesNotExist, retrieve_all_ballot_items_for_polling_location '
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_ballot_items_for_polling_location ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if ballot_item_list_found else False,
            'status':                       status,
            'google_civic_election_id':     google_civic_election_id,
            'voter_id':                     voter_id,
            'polling_location_we_vote_id':  polling_location_we_vote_id,
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results

    def fetch_most_recent_google_civic_election_id(self):
        election_manager = ElectionManager()
        results = election_manager.retrieve_elections_by_date()
        if results['success']:
            election_list = results['election_list']
            for one_election in election_list:
                ballot_item_queryset = BallotItem.objects.all()
                ballot_item_queryset = ballot_item_queryset.filter(
                    google_civic_election_id=one_election.google_civic_election_id)
                number_found = ballot_item_queryset.count()
                if positive_value_exists(number_found):
                    # Since we are starting with the most recent election, as soon as we find
                    # any election with ballot items, we can exit.
                    return one_election.google_civic_election_id
        return 0

    def fetch_ballot_item_list_count_for_ballot_returned(self, polling_location_we_vote_id, google_civic_election_id):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        try:
            ballot_item_queryset = BallotItem.objects.all()
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

    def copy_ballot_items(self, ballot_returned, to_voter_id):
        status = ""
        # Get all ballot items from the reference ballot_returned
        if positive_value_exists(ballot_returned.polling_location_we_vote_id):
            retrieve_results = self.retrieve_all_ballot_items_for_polling_location(
                ballot_returned.polling_location_we_vote_id, ballot_returned.google_civic_election_id)
            status += retrieve_results['status']
        else:
            retrieve_results = self.retrieve_all_ballot_items_for_voter(ballot_returned.voter_id,
                                                                        ballot_returned.google_civic_election_id)
            status += retrieve_results['status']
        if not retrieve_results['ballot_item_list_found']:
            error_results = {
                'ballot_returned_copied':   False,
                'success':                  False,
                'status':                   status,
            }
            return error_results

        ballot_item_list = retrieve_results['ballot_item_list']
        ballot_item_manager = BallotItemManager()

        for ballot_item in ballot_item_list:
            create_results = ballot_item_manager.update_or_create_ballot_item_for_voter(
                to_voter_id, ballot_returned.google_civic_election_id, ballot_item.google_ballot_placement,
                ballot_item.ballot_item_display_name, ballot_item.measure_subtitle, ballot_item.measure_text,
                ballot_item.local_ballot_order,
                ballot_item.contest_office_id, ballot_item.contest_office_we_vote_id,
                ballot_item.contest_measure_id, ballot_item.contest_measure_we_vote_id, ballot_item.state_code)
            if not create_results['success']:
                status += create_results['status']

        results = {
            'ballot_returned_copied':   True,
            'success':                  True,
            'status':                   status,
        }
        return results

    def retrieve_possible_duplicate_ballot_items(self, ballot_item_display_name, google_civic_election_id,
                                                 polling_location_we_vote_id,
                                                 contest_office_we_vote_id, contest_measure_we_vote_id, state_code):
        ballot_item_list_objects = []
        filters = []
        ballot_item_list_found = False

        if not positive_value_exists(google_civic_election_id):
            # We must have a google_civic_election_id
            results = {
                'success':                  False,
                'status':                   "MISSING_GOOGLE_CIVIC_ELECTION_ID",
                'google_civic_election_id': google_civic_election_id,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list_objects,
            }
            return results
        elif not positive_value_exists(polling_location_we_vote_id):
            # We must have a polling_location_we_vote_id to look up
            results = {
                'success':                  False,
                'status':                   "MISSING_POLLING_LOCATION_WE_VOTE_ID",
                'google_civic_election_id': google_civic_election_id,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list_objects,
            }
            return results
        elif not positive_value_exists(ballot_item_display_name):
            # We must have a ballot_item_display_name to look up
            results = {
                'success':                  False,
                'status':                   "MISSING_BALLOT_ITEM_DISPLAY_NAME",
                'google_civic_election_id': google_civic_election_id,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list_objects,
            }
            return results
        elif not positive_value_exists(contest_office_we_vote_id) \
                and not positive_value_exists(contest_measure_we_vote_id):
            results = {
                'success':                  False,
                'status':                   "MISSING_MEASURE_AND_OFFICE_WE_VOTE_ID",
                'google_civic_election_id': google_civic_election_id,
                'ballot_item_list_found':   ballot_item_list_found,
                'ballot_item_list':         ballot_item_list_objects,
            }
            return results

        try:
            ballot_item_queryset = BallotItem.objects.all()
            ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_queryset = ballot_item_queryset.filter(
                polling_location_we_vote_id__iexact=polling_location_we_vote_id)
            if positive_value_exists(state_code):
                ballot_item_queryset = ballot_item_queryset.filter(state_code=state_code)

            if positive_value_exists(contest_office_we_vote_id):
                # Ignore entries with contest_office_we_vote_id coming in from master server
                ballot_item_queryset = ballot_item_queryset.filter(~Q(
                    contest_office_we_vote_id__iexact=contest_office_we_vote_id))
            elif positive_value_exists(contest_measure_we_vote_id):
                # Ignore entries with contest_measure_we_vote_id coming in from master server
                ballot_item_queryset = ballot_item_queryset.filter(~Q(
                    contest_measure_we_vote_id__iexact=contest_measure_we_vote_id))

            # We want to find candidates with *any* of these values
            if positive_value_exists(ballot_item_display_name):
                new_filter = Q(ballot_item_display_name__iexact=ballot_item_display_name)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                ballot_item_queryset = ballot_item_queryset.filter(final_filters)

            ballot_item_list_objects = ballot_item_queryset

            if len(ballot_item_list_objects):
                ballot_item_list_found = True
                status = 'DUPLICATE_BALLOT_ITEMS_RETRIEVED '
                success = True
            else:
                status = 'NO_DUPLICATE_BALLOT_ITEMS_RETRIEVED '
                success = True
        except BallotItem.DoesNotExist:
            # No ballot_items found. Not a problem.
            status = 'NO_DUPLICATE_BALLOT_ITEMS_FOUND_DoesNotExist '
            ballot_item_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_ballot_items ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
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

    # The unique id of the voter for which this ballot was retrieved
    voter_id = models.IntegerField(verbose_name="the voter unique id", null=True, blank=True)
    # The polling location for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the polling location", max_length=255, default=None, null=True,
        blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False)
    # state_code = models.CharField(verbose_name="state the ballot item is related to", max_length=2, null=True)

    election_description_text = models.CharField(max_length=255, blank=False, null=False,
                                                 verbose_name='text label for this election')
    election_date = models.DateField(verbose_name='election start date', null=True, auto_now=False)

    # Should we show this ballot as an option for this election?
    ballot_location_display_option_on = models.BooleanField(default=False)
    ballot_location_display_name = models.CharField(verbose_name='name that shows in button',
                                                    max_length=255, blank=True, null=True)
    ballot_location_shortcut = models.CharField(verbose_name='the url string to find this location',
                                                max_length=255, blank=True, null=True)
    ballot_location_order = models.PositiveIntegerField(
        verbose_name="order of these ballot locations in display", default=0, null=False)

    text_for_map_search = models.CharField(max_length=255, blank=False, null=False, verbose_name='address as entered')

    latitude = models.FloatField(null=True, verbose_name='latitude returned from Google')
    longitude = models.FloatField(null=True, verbose_name='longitude returned from Google')
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
        return self.election_date.strftime('%Y-%m-%d')


class BallotReturnedManager(models.Model):
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

    def retrieve_ballot_returned_from_google_civic_election_id(self, google_civic_election_id):
        ballot_returned_id = 0
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id,
                                                                                       google_civic_election_id)

    def retrieve_ballot_returned_from_voter_id(self, voter_id, google_civic_election_id):
        ballot_returned_id = 0
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id,
                                                                                       google_civic_election_id,
                                                                                       voter_id)

    def retrieve_ballot_returned_from_polling_location_we_vote_id(self, polling_location_we_vote_id,
                                                                  google_civic_election_id):
        ballot_returned_id = 0
        voter_id = 0
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(ballot_returned_id,
                                                                                       google_civic_election_id,
                                                                                       voter_id,
                                                                                       polling_location_we_vote_id)

    def retrieve_ballot_returned_from_ballot_returned_we_vote_id(self, ballot_returned_we_vote_id):
        ballot_returned_id = 0
        google_civic_election_id = 0
        voter_id = 0
        polling_location_we_vote_id = ''
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(
            ballot_returned_id, google_civic_election_id, voter_id, polling_location_we_vote_id,
            ballot_returned_we_vote_id)

    def retrieve_ballot_returned_from_ballot_location_shortcut(self, ballot_location_shortcut):
        ballot_returned_id = 0
        google_civic_election_id = 0
        voter_id = 0
        polling_location_we_vote_id = ''
        ballot_returned_we_vote_id = ''
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(
            ballot_returned_id, google_civic_election_id, voter_id, polling_location_we_vote_id,
            ballot_returned_we_vote_id, ballot_location_shortcut)

    def retrieve_existing_ballot_returned_by_identifier(
            self, ballot_returned_id, google_civic_election_id=0, voter_id=0, polling_location_we_vote_id='',
            ballot_returned_we_vote_id='', ballot_location_shortcut=''):
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

        try:
            if positive_value_exists(ballot_returned_id):
                ballot_returned = BallotReturned.objects.get(id=ballot_returned_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status = "BALLOT_RETURNED_FOUND_FROM_VOTER_ID "
            elif positive_value_exists(ballot_returned_we_vote_id):
                ballot_returned = BallotReturned.objects.get(we_vote_id__iexact=ballot_returned_we_vote_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status = "BALLOT_RETURNED_FOUND_FROM_BALLOT_RETURNED_WE_VOTE_ID "
            elif positive_value_exists(ballot_location_shortcut):
                ballot_returned = BallotReturned.objects.get(ballot_location_shortcut=ballot_location_shortcut)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status = "BALLOT_RETURNED_FOUND_FROM_BALLOT_RETURNED_LOCATION_SHORTCUT "
            elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.get(voter_id=voter_id,
                                                             google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status = "BALLOT_RETURNED_FOUND_FROM_VOTER_ID "
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.get(polling_location_we_vote_id=polling_location_we_vote_id,
                                                             google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status = "BALLOT_RETURNED_FOUND_FROM_POLLING_LOCATION_WE_VOTE_ID "
            elif positive_value_exists(google_civic_election_id):
                ballot_returned_query = BallotReturned.objects.filter(google_civic_election_id=google_civic_election_id)
                ballot_returned_query = ballot_returned_query.order_by("-ballot_location_shortcut")
                ballot_returned = ballot_returned_query.first()
                if ballot_returned and hasattr(ballot_returned, "id"):
                    # If still here, we found an existing ballot_returned
                    ballot_returned_id = ballot_returned.id
                    ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                    success = True
                    status = "BALLOT_RETURNED_FOUND_FROM_GOOGLE_CIVIC_ELECTION_ID "
                else:
                    ballot_returned_found = False
                    success = True
                    status = "BALLOT_RETURNED_NOT_FOUND_FROM_GOOGLE_CIVIC_ELECTION_ID "
            else:
                ballot_returned_found = False
                success = False
                status = "COULD_NOT_RETRIEVE_BALLOT_RETURNED-MISSING_VARIABLES "

        except BallotReturned.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            success = False
            status = "MULTIPLE_BALLOT_RETURNED-MUST_DELETE_ALL "
        except BallotReturned.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status = "BALLOT_RETURNED_NOT_FOUND "
        except Exception as e:
            success = False
            status = "COULD_NOT_RETRIEVE_BALLOT_RETURNED-EXCEPTION "

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'ballot_returned_found':    ballot_returned_found,
            'ballot_returned':          ballot_returned,
        }
        return results

    def create_ballot_returned_with_normalized_values(self, google_civic_address_dict,
                                                      election_day_text, election_description_text,
                                                      google_civic_election_id,
                                                      voter_id=0, polling_location_we_vote_id='',
                                                      latitude='', longitude=''):
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
                status = "SAVED_BALLOT_RETURNED_WITH_NORMALIZED_VALUES"
                success = True
                ballot_returned_found = True
            else:
                status = "UNABLE_TO_CREATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES"
                success = False
                ballot_returned_found = False

        except Exception as e:
            status = "UNABLE_TO_CREATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES_EXCEPTION"
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

    def is_ballot_returned_different(self, google_civic_address_dict, ballot_returned):
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
                status = "UPDATED_BALLOT_RETURNED_WITH_NORMALIZED_VALUES"
                success = True
            else:
                status = "UNABLE_TO_UPDATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES"
                success = False

        except Exception as e:
            status = "UNABLE_TO_UPDATE_BALLOT_RETURNED_WITH_NORMALIZED_VALUES_EXCEPTION"
            success = False

        results = {
            'status':           status,
            'success':          success,
            'ballot_returned':  ballot_returned,
        }
        return results

    def fetch_last_election_in_this_state(self, state_code):
        """
        Find the last election (in the past) that has at least one ballot at a polling location
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

    def fetch_next_upcoming_election_in_this_state(self, state_code):
        """
        Find the soonest upcoming election in the future with at least one ballot at a polling location
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

    def find_closest_ballot_returned(self, text_for_map_search, google_civic_election_id=0):
        """
        We search for the closest address for this election in the ballot_returned table. We never have to worry
        about test elections being returned with this routine, because we don't store ballot_returned entries for
        test elections.
        :param text_for_map_search:
        :param google_civic_election_id:
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

        try:
            location = self.google_client.geocode(text_for_map_search)
        except GeocoderQuotaExceeded:
            try_without_maps_key = True
            status += "GEOCODER_QUOTA_EXCEEDED "
        except Exception as e:
            try_without_maps_key = True
            status += 'GEOCODER_ERROR {error} [type: {error_type}] '.format(error=e, error_type=type(e))
            logger.info(status + " @ " + text_for_map_search + "  google_civic_election_id=" +
                        str(google_civic_election_id))

        if try_without_maps_key:
            # If we have exceeded our account, try without a maps key
            try:
                temp_google_client = get_geocoder_for_service('google')()
                location = temp_google_client.geocode(text_for_map_search)
            except GeocoderQuotaExceeded:
                results = {
                    'status':                   status,
                    'geocoder_quota_exceeded':  True,
                    'ballot_returned_found':    ballot_returned_found,
                    'ballot_returned':          ballot_returned,
                }
                return results
            except Exception as e:
                location = None

        ballot = None
        if location is None:
            status += 'Geocoder could not find location matching "{}". Trying City, State. '.format(text_for_map_search)
            # If Geocoder is not able to give us a location, look to see if their voter entered their address as
            # "city_name, state_code" eg: "Sunnyvale, CA". If so, try to parse the entry and get ballot data
            # for that location
            ballot_returned_query = BallotReturned.objects.all()

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

            ballot = ballot_returned_query.first()
        else:
            # If here, then the geocoder successfully found the address
            status += 'GEOCODER_FOUND_LOCATION '
            address = location.address
            # address has format "line_1, state zip, USA"
            ballot_returned_query = BallotReturned.objects.all()
            ballot_returned_query = ballot_returned_query.exclude(polling_location_we_vote_id=None)
            state_code = address.split(', ')[-2][:2]
            if positive_value_exists(state_code):
                # This search for normalized_state is NOT redundant because some elections are in many states
                ballot_returned_query = ballot_returned_query.filter(normalized_state__iexact=state_code)

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

            ballot_returned_query = ballot_returned_query.annotate(distance=(F('latitude') - location.latitude) ** 2 +
                                                                            (F('longitude') - location.longitude) ** 2)
            ballot = ballot_returned_query.order_by('distance').first()

        if ballot is not None:
            ballot_returned = ballot
            ballot_returned_found = True
            status += 'BALLOT_RETURNED_FOUND '
        else:
            status += 'NO_STORED_BALLOT_MATCHES_STATE {}. '.format(state_code)

        return {
            'status':                   status,
            'geocoder_quota_exceeded':  False,
            'ballot_returned_found':    ballot_returned_found,
            'ballot_returned':          ballot_returned,
        }

    def should_election_search_data_be_saved(self, google_civic_election_id):
        success = False
        status = ""
        if not google_civic_election_id:
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID-should_election_search_data_be_saved '
        else:
            ballot_returned_list_manager = BallotReturnedListManager()
            ballot_returned_list_count = ballot_returned_list_manager.fetch_ballot_returned_list_count_for_election(
                google_civic_election_id)
            if ballot_returned_list_count > 0:
                success = True
                status = 'ELECTION SEARCH DATA BE SAVED'

        results = {
            'success':  success,
            'status':   status,
        }
        return results

    def update_or_create_ballot_returned(
            self, polling_location_we_vote_id, voter_id, google_civic_election_id, election_day_text=False,
            election_description_text=False, latitude=False, longitude=False,
            normalized_city=False, normalized_line1=False, normalized_line2=False, normalized_state=False,
            normalized_zip=False, text_for_map_search=False):
        exception_multiple_object_returned = False
        new_ballot_returned_created = False

        if not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID-update_or_create_ballot_returned '
        elif (not polling_location_we_vote_id) and (not voter_id):
            success = False
            status = 'MISSING_BALLOT_RETURNED_POLLING_LOCATION_AND_VOTER_ID-update_or_create_ballot_returned '
        else:
            try:
                ballot_returned, new_ballot_returned_created = BallotReturned.objects.get_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    polling_location_we_vote_id=polling_location_we_vote_id,
                    voter_id=voter_id
                )

                if not positive_value_exists(ballot_returned.google_civic_election_id):
                    ballot_returned.google_civic_election_id = google_civic_election_id;
                if not positive_value_exists(ballot_returned.voter_id):
                    ballot_returned.voter_id = voter_id
                if election_day_text is not False:
                    ballot_returned.election_date = election_day_text
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
                ballot_returned.save()

                if new_ballot_returned_created:
                    success = True
                    status = 'BALLOT_RETURNED_CREATED '
                else:
                    success = True
                    status = 'BALLOT_RETURNED_UPDATED '

            except BallotReturned.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_BALLOT_RETURNED_FOUND '
                exception_multiple_object_returned = True

        results = {
            'success':                      success,
            'status':                       status,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
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
            location = self.google_client.geocode(full_ballot_address)
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


class BallotReturnedListManager(models.Model):
    """
    A way to work with a list of ballot_returned entries
    """

    def fetch_ballot_location_display_option_on_count_for_election(self, google_civic_election_id, state_code=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        try:
            ballot_returned_queryset = BallotReturned.objects.all()
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

    def retrieve_ballot_returned_list_for_election(self, google_civic_election_id, state_code='', limit=0,
                                                   ballot_returned_search_str=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        ballot_returned_list = []
        ballot_returned_list_found = False

        try:
            ballot_returned_queryset = BallotReturned.objects.all()
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
                status = 'BALLOT_RETURNED_LIST_FOUND'
            else:
                status = 'NO_BALLOT_RETURNED_LIST_FOUND'
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_RETURNED_LIST_FOUND_DOES_NOT_EXIST'
            ballot_returned_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_ballot_returned_list_for_election ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        results = {
            'success':                      True if ballot_returned_list_found else False,
            'status':                       status,
            'ballot_returned_list_found':   ballot_returned_list_found,
            'ballot_returned_list':         ballot_returned_list,
        }
        return results

    def fetch_ballot_returned_list_count_for_election(self, google_civic_election_id, state_code=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        try:
            ballot_returned_queryset = BallotReturned.objects.using('readonly').all()
            ballot_returned_queryset = ballot_returned_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state_code)

            return ballot_returned_queryset.count()
        except BallotReturned.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_RETURNED_LIST_FOUND_DOES_NOT_EXIST'
            ballot_returned_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_ballot_returned_list_for_election ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        return 0

    def fetch_ballot_returned_entries_needed_lat_long_for_election(self, google_civic_election_id, state_code=''):
        google_civic_election_id = convert_to_int(google_civic_election_id)
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
            status = 'NO_BALLOT_RETURNED_LIST_FOUND_DOES_NOT_EXIST'
            ballot_returned_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_ballot_returned_list_for_election ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        return 0

    def retrieve_possible_duplicate_ballot_returned(self, google_civic_election_id, normalized_line1, normalized_zip,
                                                    polling_location_we_vote_id):
        ballot_returned_list_objects = []
        ballot_returned_list_found = False

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
                status = 'DUPLICATE_BALLOT_RETURNED_ITEMS_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_BALLOT_RETURNED_ITEMS_RETRIEVED'
                success = True
        except BallotReturned.DoesNotExist:
            # No ballot_returned found. Not a problem.
            status = 'NO_DUPLICATE_BALLOT_RETURNED_ITEMS_FOUND_DoesNotExist'
            ballot_returned_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_ballot_returned ' \
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
    substituted_address_nearby = models.CharField(max_length=255, blank=False, null=False,
                                                  verbose_name='address from nearby ballot_returned')

    is_from_substituted_address = models.BooleanField(default=False)
    is_from_test_ballot = models.BooleanField(default=False)

    # The polling location for which this ballot was retrieved
    polling_location_we_vote_id_source = models.CharField(
        verbose_name="we vote permanent id of the polling location this was copied from",
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
        elif self.election_date:
            return self.election_date
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


class VoterBallotSavedManager(models.Model):
    """
    """

    def retrieve_ballots_per_voter_id(self, voter_id):
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

    def delete_voter_ballot_saved(self, voter_ballot_saved_id, voter_id=0, google_civic_election_id=0,
                                  ballot_returned_we_vote_id="", ballot_location_shortcut=""):
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
                voter_ballot_saved = VoterBallotSaved.objects.get(id=voter_ballot_saved_id)
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_found = True
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
                success = False
                status += "DELETE_VOTER_BALLOT_SAVED-COULD_NOT_RETRIEVE_VOTER_BALLOT_SAVED-MISSING_VARIABLES-DELETE "

        except VoterBallotSaved.DoesNotExist:
            success = True
            status += "DELETE_VOTER_BALLOT_SAVED_NOT_FOUND "
        except Exception as e:
            success = False
            status += "DELETE_VOTER_BALLOT_SAVED-CANNOT_DELETE "

        if voter_ballot_saved_found:
            try:
                voter_ballot_saved.delete()
                status += "DELETED "
                voter_ballot_saved_deleted = True
            except Exception as e:
                success = False
                status += "NOT_DELETED "

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

    def retrieve_voter_ballot_saved(self, voter_ballot_saved_id, voter_id=0, google_civic_election_id=0,
                                    text_for_map_search='', ballot_returned_we_vote_id='', ballot_location_shortcut=''):
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

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_ballot_saved_found': voter_ballot_saved_found,
            'voter_ballot_saved':       voter_ballot_saved,
        }
        return results

    def retrieve_voter_ballot_saved_list_for_election(self, google_civic_election_id):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        voter_ballot_saved_list = []
        voter_ballot_saved_list_found = False

        try:
            voter_ballot_saved_queryset = VoterBallotSaved.objects.all()

            voter_ballot_saved_queryset = voter_ballot_saved_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            voter_ballot_saved_list = list(voter_ballot_saved_queryset)

            if len(voter_ballot_saved_list):
                voter_ballot_saved_list_found = True
                status = 'VOTER_BALLOT_SAVED_LIST_FOUND '
            else:
                status = 'NO_VOTER_BALLOT_SAVED_LIST_FOUND '
        except VoterBallotSaved.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_VOTER_BALLOT_SAVED_LIST_FOUND_DOES_NOT_EXIST '
            voter_ballot_saved_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_voter_ballot_saved_list_for_election ' \
                     '{error} [type: {error_type}] '.format(error=e, error_type=type(e))

        results = {
            'success':                          True if voter_ballot_saved_list_found else False,
            'status':                           status,
            'voter_ballot_saved_list_found':    voter_ballot_saved_list_found,
            'voter_ballot_saved_list':          voter_ballot_saved_list,
        }
        return results

    def update_or_create_voter_ballot_saved(
            self, voter_id,
            google_civic_election_id,
            state_code,
            election_day_text,
            election_description_text,
            original_text_for_map_search,
            substituted_address_nearby='',
            is_from_substituted_address=False,
            is_from_test_ballot=False,
            polling_location_we_vote_id_source='',
            ballot_location_display_name=None,
            ballot_returned_we_vote_id=None,
            ballot_location_shortcut='',
            called_recursively=False):
        # We assume that we tried to find an entry for this voter
        success = False
        status = ""
        voter_ballot_saved_found = False

        ballot_location_shortcut = str(ballot_location_shortcut)
        ballot_location_shortcut = ballot_location_shortcut.strip().lower()
        try:
            defaults = {
                'voter_id': voter_id,
                'google_civic_election_id': google_civic_election_id,
                'state_code': state_code,
                'election_date': election_day_text,
                'election_description_text': election_description_text,
                'original_text_for_map_search': original_text_for_map_search,
                'substituted_address_nearby': substituted_address_nearby,
                'is_from_substituted_address': is_from_substituted_address,
                'is_from_test_ballot': is_from_test_ballot,
                'ballot_location_display_name': ballot_location_display_name,
                'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
                'ballot_location_shortcut': ballot_location_shortcut,
                'polling_location_we_vote_id_source': polling_location_we_vote_id_source,
            }

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
            voter_ballot_saved_manager.delete_voter_ballot_saved(0, voter_id, google_civic_election_id,
                                                                 ballot_returned_we_vote_id, ballot_location_shortcut)
            if not positive_value_exists(called_recursively):
                called_recursively = True
                return self.update_or_create_voter_ballot_saved(
                    voter_id,
                    google_civic_election_id,
                    state_code,
                    election_day_text,
                    election_description_text,
                    original_text_for_map_search,
                    substituted_address_nearby,
                    is_from_substituted_address,
                    is_from_test_ballot,
                    polling_location_we_vote_id_source,
                    ballot_location_display_name,
                    ballot_returned_we_vote_id,
                    ballot_location_shortcut,
                    called_recursively)

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


def copy_existing_ballot_items_from_stored_ballot(voter_id, text_for_map_search, google_civic_election_id=0,
                                                  ballot_returned_we_vote_id='', ballot_location_shortcut=''):
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
    voter_ballot_saved_manager = VoterBallotSavedManager()
    ballot_item_list_manager = BallotItemListManager()

    text_for_map_search_empty = not positive_value_exists(text_for_map_search) or text_for_map_search != ""

    if positive_value_exists(ballot_returned_we_vote_id):
        find_results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(
            ballot_returned_we_vote_id)
        status += find_results['status']

        if not find_results['ballot_returned_found']:
            error_results = {
                'voter_id':                             voter_id,
                'google_civic_election_id':             google_civic_election_id,
                'state_code':                           '',
                'election_day_text':                   '',
                'election_description_text':            '',
                'text_for_map_search':                  text_for_map_search,
                'substituted_address_nearby':           '',
                'ballot_returned_copied':               False,
                'polling_location_we_vote_id_source':   '',
                'ballot_location_display_name':        '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'status':                               status,
            }
            return error_results

        # A specific ballot was found.
        ballot_returned = find_results['ballot_returned']
    elif positive_value_exists(ballot_location_shortcut):
        find_results = ballot_returned_manager.retrieve_ballot_returned_from_ballot_location_shortcut(
            ballot_location_shortcut)
        status += find_results['status']

        if not find_results['ballot_returned_found']:
            error_results = {
                'voter_id':                             voter_id,
                'google_civic_election_id':             google_civic_election_id,
                'state_code':                           '',
                'election_day_text':                   '',
                'election_description_text':            '',
                'text_for_map_search':                  text_for_map_search,
                'substituted_address_nearby':           '',
                'ballot_returned_copied':               False,
                'ballot_location_display_name':        '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'polling_location_we_vote_id_source':   '',
                'status':                               status,
            }
            return error_results

        # A specific ballot was found.
        ballot_returned = find_results['ballot_returned']
    elif positive_value_exists(google_civic_election_id) and text_for_map_search_empty:
        find_results = ballot_returned_manager.retrieve_ballot_returned_from_google_civic_election_id(
            google_civic_election_id)
        status += find_results['status']

        if not find_results['ballot_returned_found']:
            error_results = {
                'voter_id': voter_id,
                'google_civic_election_id': google_civic_election_id,
                'state_code': '',
                'election_day_text': '',
                'election_description_text': '',
                'text_for_map_search': text_for_map_search,
                'substituted_address_nearby': '',
                'ballot_returned_copied': False,
                'ballot_location_display_name': '',
                'ballot_returned_we_vote_id': ballot_returned_we_vote_id,
                'ballot_location_shortcut': ballot_location_shortcut,
                'polling_location_we_vote_id_source': '',
                'status': status,
            }
            return error_results

        # A specific ballot was found.
        ballot_returned = find_results['ballot_returned']
    else:
        find_results = ballot_returned_manager.find_closest_ballot_returned(
            text_for_map_search, google_civic_election_id)
        status += find_results['status']

        if not find_results['ballot_returned_found']:
            error_results = {
                'voter_id':                             voter_id,
                'google_civic_election_id':             google_civic_election_id,
                'state_code':                           '',
                'election_day_text':                   '',
                'election_description_text':            '',
                'text_for_map_search':                  text_for_map_search,
                'substituted_address_nearby':           '',
                'ballot_returned_copied':               False,
                'ballot_location_display_name':        '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'polling_location_we_vote_id_source':   '',
                'status':                               status,
            }
            return error_results

        # A ballot at a nearby address was found.
        ballot_returned = find_results['ballot_returned']

    # Remove all prior ballot items, so we make room for copy_ballot_items to save ballot items
    # 2017-11-03 We only want to delete if the ballot_returned in question has a polling_location_we_vote_id
    if positive_value_exists(ballot_returned.google_civic_election_id) and \
            positive_value_exists(ballot_returned.polling_location_we_vote_id):
        voter_ballot_saved_id = 0
        voter_ballot_saved_results = voter_ballot_saved_manager.delete_voter_ballot_saved(
            voter_ballot_saved_id, voter_id, ballot_returned.google_civic_election_id)

        # We include a google_civic_election_id, so only the ballot info for this election is removed
        ballot_item_list_manager.delete_all_ballot_items_for_voter(voter_id, ballot_returned.google_civic_election_id)
    else:
        status += "NOT_DELETED-voter_ballot_saved-AND-VOTER_BALLOT_ITEMS "

    # ...and then copy it for the voter as long as it doesn't already belong to the voter
    if ballot_returned.voter_id != voter_id:
        copy_item_results = ballot_item_list_manager.copy_ballot_items(ballot_returned, voter_id)
        status += copy_item_results['status']

        if not copy_item_results['ballot_returned_copied']:
            error_results = {
                'voter_id':                             voter_id,
                'google_civic_election_id':             google_civic_election_id,
                'state_code':                           '',
                'election_day_text':                   '',
                'election_description_text':            '',
                'text_for_map_search':                  text_for_map_search,
                'substituted_address_nearby':           '',
                'ballot_returned_copied':               False,
                'ballot_location_display_name':         '',
                'ballot_returned_we_vote_id':           ballot_returned_we_vote_id,
                'ballot_location_shortcut':             ballot_location_shortcut,
                'polling_location_we_vote_id_source':   '',
                'status':                               status,
            }
            return error_results

    # VoterBallotSaved is updated outside of this function

    results = {
        'voter_id':                             ballot_returned.voter_id,
        'google_civic_election_id':             ballot_returned.google_civic_election_id,
        'state_code':                           ballot_returned.normalized_state,
        'election_day_text':                    ballot_returned.election_day_text(),
        'election_description_text':            ballot_returned.election_description_text,
        'text_for_map_search':                  ballot_returned.text_for_map_search,
        'substituted_address_nearby':           ballot_returned.text_for_map_search,
        'ballot_returned_copied':               True,
        'ballot_location_display_name':         ballot_returned.ballot_location_display_name,
        'ballot_returned_we_vote_id':           ballot_returned.we_vote_id,
        'ballot_location_shortcut':             ballot_returned.ballot_location_shortcut if
        ballot_returned.ballot_location_shortcut else '',
        'polling_location_we_vote_id_source':   ballot_returned.polling_location_we_vote_id,
        'status':                               status,
    }
    return results
