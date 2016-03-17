# ballot/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateCampaign
from django.db import models
from election.models import ElectionManager
from exception.models import handle_exception, handle_record_found_more_than_one_exception
import usaddress
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

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

    google_ballot_placement = models.SmallIntegerField(
        verbose_name="the order this item should appear on the ballot", null=True, blank=True, unique=False)
    local_ballot_order = models.SmallIntegerField(
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
    # This is a sortable name
    ballot_item_display_name = models.CharField(verbose_name="a label we can sort by", max_length=255, null=True, blank=True)

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
    def update_or_create_ballot_item_for_voter(
            self, voter_id, google_civic_election_id, google_ballot_placement,
            ballot_item_display_name, local_ballot_order,
            contest_office_id=0, contest_office_we_vote_id='',
            contest_measure_id=0, contest_measure_we_vote_id=''):
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
            status = 'MISSING_SUFFICIENT_OFFICE_OR_MEASURE_IDS'
        # If here, then we know that there are sufficient office or measure ids
        elif not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID'
        elif not voter_id:
            success = False
            status = 'MISSING_VOTER_ID'
        else:
            try:
                # Use get_or_create to see if a ballot item exists
                create_values = {
                    # Values we search against
                    'google_civic_election_id': google_civic_election_id,
                    'voter_id': voter_id,
                    # The rest of the values
                    'contest_office_id': contest_office_id,
                    'contest_office_we_vote_id': contest_office_we_vote_id,
                    'contest_measure_id': contest_measure_id,
                    'contest_measure_we_vote_id': contest_measure_we_vote_id,
                    'google_ballot_placement': google_ballot_placement,
                    'local_ballot_order': local_ballot_order,
                    'ballot_item_display_name': ballot_item_display_name,
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
                    ballot_item_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                    ballot_item_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                    ballot_item_on_stage.save()

                    success = True
                    status = 'BALLOT_ITEM_UPDATED'
                else:
                    success = True
                    status = 'BALLOT_ITEM_CREATED'

            except BallotItemManager.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_BALLOT_ITEMS_FOUND'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_ballot_item_created':  new_ballot_item_created,
        }
        return results

    def update_or_create_ballot_item_for_polling_location(
            self, polling_location_we_vote_id, google_civic_election_id, google_ballot_placement,
            ballot_item_display_name, local_ballot_order,
            contest_office_id=0, contest_office_we_vote_id='',
            contest_measure_id=0, contest_measure_we_vote_id=''):
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
            status = 'MISSING_SUFFICIENT_OFFICE_OR_MEASURE_IDS-POLLING_LOCATION'
        # If here, then we know that there are sufficient office or measure ids
        elif not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID-POLLING_LOCATION'
        elif not polling_location_we_vote_id:
            success = False
            status = 'MISSING_POLLING_LOCATION_WE_VOTE_ID'
        else:
            try:
                # Use get_or_create to see if a ballot item exists
                create_values = {
                    # Values we search against
                    'google_civic_election_id': google_civic_election_id,
                    'polling_location_we_vote_id': polling_location_we_vote_id,
                    # The rest of the values
                    'contest_office_id': contest_office_id,
                    'contest_office_we_vote_id': contest_office_we_vote_id,
                    'contest_measure_id': contest_measure_id,
                    'contest_measure_we_vote_id': contest_measure_we_vote_id,
                    'google_ballot_placement': google_ballot_placement,
                    'local_ballot_order': local_ballot_order,
                    'ballot_item_display_name': ballot_item_display_name,
                }
                # We search with contest_measure_id and contest_office_id because they are (will be) integers,
                #  which will be a faster search
                ballot_item_on_stage, new_ballot_item_created = BallotItem.objects.get_or_create(
                    contest_measure_id__exact=contest_measure_id,
                    contest_office_id__exact=contest_office_id,
                    google_civic_election_id__exact=google_civic_election_id,
                    polling_location_we_vote_id__exact=polling_location_we_vote_id,
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
                    ballot_item_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                    ballot_item_on_stage.contest_measure_we_vote_id = contest_measure_we_vote_id
                    ballot_item_on_stage.save()

                    success = True
                    status = 'BALLOT_ITEM_UPDATED-POLLING_LOCATION'
                else:
                    success = True
                    status = 'BALLOT_ITEM_CREATED-POLLING_LOCATION'

            except BallotItemManager.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_BALLOT_ITEMS_FOUND-POLLING_LOCATION'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_ballot_item_created':  new_ballot_item_created,
        }
        return results

    def retrieve_ballot_item_for_voter(self, voter_id, google_civic_election_id, google_civic_district_ocd_id):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        google_civic_ballot_item_on_stage = BallotItem()
        google_civic_ballot_item_id = 0

        if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id) and \
                positive_value_exists(google_civic_district_ocd_id):
            try:
                google_civic_ballot_item_on_stage = BallotItem.objects.get(
                    voter_id__exact=voter_id,
                    google_civic_election_id__exact=google_civic_election_id,
                    district_ocd_id=google_civic_district_ocd_id,  # TODO This needs to be rethunk
                )
                google_civic_ballot_item_id = google_civic_ballot_item_on_stage.id
            except BallotItem.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                exception_multiple_object_returned = True
            except BallotItem.DoesNotExist:
                exception_does_not_exist = True

        results = {
            'success':                          True if google_civic_ballot_item_id > 0 else False,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'google_civic_ballot_item':         google_civic_ballot_item_on_stage,
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
            'success':                      True if ballot_item_list_deleted else False,
            'status':                       status,
            'google_civic_election_id':     google_civic_election_id,
            'voter_id':                     voter_id,
            'ballot_item_list_deleted':     ballot_item_list_deleted,
        }
        return results

    def retrieve_ballot_items_for_election(self, google_civic_election_id):
        ballot_item_list = []
        ballot_item_list_found = False
        try:
            ballot_item_queryset = BallotItem.objects.order_by('local_ballot_order')
            ballot_item_list = ballot_item_queryset.filter(
                google_civic_election_id=google_civic_election_id)

            if positive_value_exists(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND'
            else:
                status = 'NO_BALLOT_ITEMS_FOUND, not positive_value_exists'
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_FOUND'
            ballot_item_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_ballot_items_for_election ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if ballot_item_list_found else False,
            'status':                       status,
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results

    def retrieve_all_ballot_items_for_voter(self, voter_id, google_civic_election_id):
        polling_location_we_vote_id = ''
        ballot_item_list = []
        ballot_item_list_found = False
        try:
            ballot_item_queryset = BallotItem.objects.order_by('local_ballot_order')
            ballot_item_queryset = ballot_item_queryset.filter(voter_id=voter_id)
            if positive_value_exists(google_civic_election_id):
                ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_list = ballot_item_queryset

            if len(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_voter'
            else:
                status = 'NO_BALLOT_ITEMS_FOUND_0'
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_FOUND_DoesNotExist'
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
            ballot_item_queryset = BallotItem.objects.order_by('local_ballot_order')
            ballot_item_queryset = ballot_item_queryset.filter(polling_location_we_vote_id=polling_location_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                ballot_item_queryset = ballot_item_queryset.filter(google_civic_election_id=google_civic_election_id)
            ballot_item_list = ballot_item_queryset

            if len(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_polling_location'
            else:
                status = 'NO_BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_polling_location'
        except BallotItem.DoesNotExist:
            # No ballot items found. Not a problem.
            status = 'NO_BALLOT_ITEMS_FOUND_DoesNotExist, retrieve_all_ballot_items_for_polling_location'
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

    def copy_ballot_items(self, ballot_returned, to_voter_id):

        # Get all ballot items from the reference ballot_returned
        if positive_value_exists(ballot_returned.polling_location_we_vote_id):
            retrieve_results = self.retrieve_all_ballot_items_for_polling_location(
                ballot_returned.polling_location_we_vote_id, ballot_returned.google_civic_election_id)
        else:
            retrieve_results = self.retrieve_all_ballot_items_for_voter(ballot_returned.voter_id,
                                                                        ballot_returned.google_civic_election_id)
        if not retrieve_results['ballot_item_list_found']:
            error_results = {
                'ballot_returned_copied': False,
            }
            return error_results

        ballot_item_list = retrieve_results['ballot_item_list']
        ballot_item_manager = BallotItemManager()

        for ballot_item in ballot_item_list:
            create_results = ballot_item_manager.update_or_create_ballot_item_for_voter(
                to_voter_id, ballot_returned.google_civic_election_id,
                ballot_item.google_ballot_placement,
                ballot_item.ballot_item_display_name, ballot_item.local_ballot_order,
                ballot_item.contest_office_id, ballot_item.contest_office_we_vote_id,
                ballot_item.contest_measure_id, ballot_item.contest_measure_we_vote_id)

        results = {
            'ballot_returned_copied': True,
        }
        return results


class BallotReturned(models.Model):
    """
    This is a generated table with a summary of address + election combinations returned ballot data
    """
    # The unique id of the voter for which this ballot was retrieved
    voter_id = models.IntegerField(verbose_name="the voter unique id", default=0, null=False, blank=False)
    # The polling location for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the polling location", max_length=255, default=None, null=True,
        blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False)

    election_description_text = models.CharField(max_length=255, blank=False, null=False,
                                                 verbose_name='text label for this election')
    election_date = models.DateField(verbose_name='election start date', null=True, auto_now=False)

    text_for_map_search = models.CharField(max_length=255, blank=False, null=False, verbose_name='address as entered')

    latitude = models.CharField(max_length=255, blank=True, null=True, verbose_name='latitude returned from Google')
    longitude = models.CharField(max_length=255, blank=True, null=True, verbose_name='longitude returned from Google')
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

    def election_date_text(self):
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

    def retrieve_ballot_returned_from_voter_id(self, voter_id, google_civic_election_id):
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(google_civic_election_id,
                                                                                       voter_id)

    def retrieve_ballot_returned_from_polling_location_we_vote_id(self, polling_location_we_vote_id,
                                                                  google_civic_election_id):
        voter_id = 0
        ballot_returned_manager = BallotReturnedManager()
        return ballot_returned_manager.retrieve_existing_ballot_returned_by_identifier(google_civic_election_id,
                                                                                       voter_id,
                                                                                       polling_location_we_vote_id)

    def retrieve_existing_ballot_returned_by_identifier(self, google_civic_election_id,
                                                        voter_id=0, polling_location_we_vote_id=''):
        """
        Search by voter_id (or polling_location_we_vote_id) + google_civic_election_id to see if have an entry
        :param google_civic_election_id:
        :param voter_id:
        :param polling_location_we_vote_id:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        ballot_returned_found = False
        ballot_returned = BallotReturned()

        try:
            if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.get(voter_id=voter_id,
                                                             google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status = "BALLOT_RETURNED_FOUND_FROM_VOTER_ID"
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.get(polling_location_we_vote_id=polling_location_we_vote_id,
                                                             google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing ballot_returned
                ballot_returned_id = ballot_returned.id
                ballot_returned_found = True if positive_value_exists(ballot_returned_id) else False
                success = True
                status = "BALLOT_RETURNED_FOUND_FROM_POLLING_LOCATION_WE_VOTE_ID"
            else:
                ballot_returned_found = False
                success = False
                status = "COULD_NOT_RETRIEVE_BALLOT_RETURNED-MISSING_VARIABLES"

        except BallotReturned.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            success = False
            status = "MULTIPLE_BALLOT_RETURNED-MUST_DELETE_ALL"
        except BallotReturned.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status = "BALLOT_RETURNED_NOT_FOUND"

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
                                                      election_date_text, election_description_text,
                                                      google_civic_election_id,
                                                      voter_id=0, polling_location_we_vote_id=''):
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
                                                                election_date=election_date_text,
                                                                election_description_text=election_description_text)
                ballot_returned_id = ballot_returned.id
            elif positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                ballot_returned = BallotReturned.objects.create(google_civic_election_id=google_civic_election_id,
                                                                polling_location_we_vote_id=polling_location_we_vote_id,
                                                                election_date=election_date_text,
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

    def update_ballot_returned_with_normalized_values(self, google_civic_address_dict, ballot_returned):
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
            ballot_returned = BallotReturned()

        results = {
            'status':   status,
            'success':  success,
            'ballot_returned': ballot_returned,
        }
        return results

    def find_closest_ballot_returned(self, text_for_map_search, google_civic_election_id=0):
        """
        We search for the closest address for this election in the ballot_returned table.
        :param text_for_map_search:
        :param google_civic_election_id:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        ballot_returned_found = False
        ballot_returned = BallotReturned()
        city = ''
        state = ''
        zip_code = ''
        success = False

        address_as_ordered_dict = usaddress.tag(text_for_map_search)
        # Docs: http://usaddress.readthedocs.org/en/latest/
        address_element_found = False
        for one_address in address_as_ordered_dict:
            if 'PlaceName' in one_address:
                city = one_address['PlaceName']
                address_element_found = True
            if 'StateName' in one_address:
                state = one_address['StateName']
                address_element_found = True
            if 'ZipCode' in one_address:
                zip_code = one_address['ZipCode']
                address_element_found = True
            if address_element_found:
                break

        # This is an extremely rudimentary location search for basic testing
        try:
            if positive_value_exists(city) or positive_value_exists(state) or positive_value_exists(zip_code):
                # Start with narrowest search
                ballot_returned_queryset = BallotReturned.objects.all()
                if positive_value_exists(google_civic_election_id):
                    ballot_returned_queryset = ballot_returned_queryset.filter(
                        google_civic_election_id=google_civic_election_id)
                # Use both zip and city if they exist
                if positive_value_exists(city):
                    ballot_returned_queryset = ballot_returned_queryset.filter(normalized_city__iexact=city)
                if positive_value_exists(zip_code):
                    ballot_returned_queryset = ballot_returned_queryset.filter(normalized_zip__iexact=zip_code)
                if positive_value_exists(state):
                    ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state)
                # Return the latest google_civic_election_id first
                ballot_returned_list = ballot_returned_queryset.order_by('-google_civic_election_id')

                if len(ballot_returned_list):
                    status = "BALLOT_RETURNED_LIST_FOUND1: {city}, {state} {zip}" \
                             "".format(city=city, state=state, zip=zip_code)
                    for ballot_returned in ballot_returned_list:
                        ballot_returned_found = True
                        success = True
                        break
                elif positive_value_exists(city) or positive_value_exists(state):
                    # ...and expand the search to city/state if needed
                    ballot_returned_queryset = BallotReturned.objects.all()
                    if positive_value_exists(google_civic_election_id):
                        ballot_returned_queryset = ballot_returned_queryset.filter(
                            google_civic_election_id=google_civic_election_id)
                    # Only search by city and/or state
                    if positive_value_exists(city):
                        ballot_returned_queryset = ballot_returned_queryset.filter(normalized_city__iexact=city)
                    if positive_value_exists(state):
                        ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state)
                    # Return the latest google_civic_election_id first
                    ballot_returned_list = ballot_returned_queryset.order_by('-google_civic_election_id')

                    if len(ballot_returned_list):
                        status = "BALLOT_RETURNED_LIST_FOUND2: {city}, {state} {zip}" \
                                 "".format(city=city, state=state, zip=zip_code)
                        for ballot_returned in ballot_returned_list:
                            ballot_returned_found = True
                            success = True
                            break
                    elif positive_value_exists(state):
                        # ...and expand the search to just state if needed
                        ballot_returned_queryset = BallotReturned.objects.all()
                        if positive_value_exists(google_civic_election_id):
                            ballot_returned_queryset = ballot_returned_queryset.filter(
                                google_civic_election_id=google_civic_election_id)
                        # Only search by state
                        if positive_value_exists(state):
                            ballot_returned_queryset = ballot_returned_queryset.filter(normalized_state__iexact=state)
                        # Return the latest google_civic_election_id first
                        ballot_returned_list = ballot_returned_queryset.order_by('-google_civic_election_id')

                        if len(ballot_returned_list):
                            status = "BALLOT_RETURNED_LIST_FOUND2: {city}, {state} {zip}" \
                                     "".format(city=city, state=state, zip=zip_code)
                            for ballot_returned in ballot_returned_list:
                                ballot_returned_found = True
                                success = True
                                break
                        else:
                            success = True
                            status = "BALLOT_RETURNED_LIST_NOT_FOUND"
                    else:
                        ballot_returned_found = False
                        success = False
                        status = "COULD_NOT_RETRIEVE_BALLOT_RETURNED-MISSING_VARIABLES3"
                else:
                    ballot_returned_found = False
                    success = False
                    status = "COULD_NOT_RETRIEVE_BALLOT_RETURNED-MISSING_VARIABLES2"
            else:
                ballot_returned_found = False
                success = False
                status = "COULD_NOT_RETRIEVE_BALLOT_RETURNED-MISSING_VARIABLES1"

        except BallotReturned.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status = "BALLOT_RETURNED_NOT_FOUND"

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'ballot_returned_found':    ballot_returned_found,
            'ballot_returned':          ballot_returned,
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

    election_description_text = models.CharField(max_length=255, blank=False, null=False,
                                                 verbose_name='text label for this election')
    election_date = models.DateField(verbose_name='election start date', null=True, auto_now=False)

    original_text_for_map_search = models.CharField(max_length=255, blank=False, null=False,
                                                    verbose_name='address as entered')
    substituted_address_nearby = models.CharField(max_length=255, blank=False, null=False,
                                                  verbose_name='address from nearby ballot_returned')

    is_from_substituted_address = models.BooleanField(default=False)
    is_from_test_ballot = models.BooleanField(default=False)

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

    def __unicode__(self):
        return "VoterBallotSavedManager"

    def retrieve_voter_ballot_saved_by_id(self, voter_ballot_saved_id):
        return self.retrieve_voter_ballot_saved(voter_ballot_saved_id)

    def retrieve_voter_ballot_saved_by_voter_id(self, voter_id, google_civic_election_id):
        voter_ballot_saved_id = 0
        return self.retrieve_voter_ballot_saved(voter_ballot_saved_id, voter_id, google_civic_election_id)

    def retrieve_voter_ballot_saved_by_address_text(self, voter_id, text_for_map_search):
        voter_ballot_saved_id = 0
        google_civic_election_id = 0
        return self.retrieve_voter_ballot_saved(voter_ballot_saved_id, voter_id, google_civic_election_id,
                                               text_for_map_search)

    def retrieve_voter_ballot_saved(self, voter_ballot_saved_id, voter_id=0, google_civic_election_id=0,
                                    text_for_map_search=''):
        """
        Search by voter_id & google_civic_election_id to see if have an entry
        :param google_civic_election_id:
        :param voter_id:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_ballot_saved_found = False
        voter_ballot_saved = None

        try:
            if positive_value_exists(voter_ballot_saved_id):
                voter_ballot_saved = VoterBallotSaved.objects.get(id=voter_ballot_saved_id)
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_id = voter_ballot_saved.id
                voter_ballot_saved_found = True if positive_value_exists(voter_ballot_saved_id) else False
                success = True
                status = "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_BALLOT_SAVED_ID"
            elif positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                voter_ballot_saved = VoterBallotSaved.objects.get(
                    voter_id=voter_id, google_civic_election_id=google_civic_election_id)
                # If still here, we found an existing voter_ballot_saved
                voter_ballot_saved_id = voter_ballot_saved.id
                voter_ballot_saved_found = True if positive_value_exists(voter_ballot_saved_id) else False
                success = True
                status = "VOTER_BALLOT_SAVED_FOUND_FROM_VOTER_ID_AND_GOOGLE_CIVIC"
            else:
                voter_ballot_saved_found = False
                success = False
                status = "COULD_NOT_RETRIEVE_VOTER_BALLOT_SAVED-MISSING_VARIABLES"

        except VoterBallotSaved.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            success = False
            status = "MULTIPLE_VOTER_BALLOT_SAVED_FOUND-MUST_DELETE_ALL"
        except VoterBallotSaved.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status = "VOTER_BALLOT_SAVED_NOT_FOUND1"

        # If here and a voter_ballot_saved not found yet, then try to find list of entries saved under this address
        # and return the most recent
        if not voter_ballot_saved_found:
            try:
                if positive_value_exists(text_for_map_search) and positive_value_exists(voter_id):
                    # Start with narrowest search
                    voter_ballot_saved_queryset = VoterBallotSaved.objects.all()
                    voter_ballot_saved_queryset = voter_ballot_saved_queryset.filter(
                        voter_id=voter_id, original_text_for_map_search__iexact=text_for_map_search)
                    # Return the latest google_civic_election_id first
                    voter_ballot_saved_list = voter_ballot_saved_queryset.order_by('-google_civic_election_id')

                    if len(voter_ballot_saved_list):
                        status = "VOTER_BALLOT_SAVED_LIST_FOUND"
                        for voter_ballot_saved in voter_ballot_saved_list:
                            voter_ballot_saved_found = True
                            success = True
                            break
                else:
                    voter_ballot_saved_found = False
                    success = False
                    status = "COULD_NOT_RETRIEVE_VOTER_BALLOT_SAVED-MISSING_VARIABLES"

            except VoterBallotSaved.DoesNotExist:
                exception_does_not_exist = True
                success = True
                status = "VOTER_BALLOT_SAVED_NOT_FOUND2"

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_ballot_saved_found': voter_ballot_saved_found,
            'voter_ballot_saved':       voter_ballot_saved,
        }
        return results

    def create_voter_ballot_saved(
            self, voter_id,
            google_civic_election_id,
            election_date_text,
            election_description_text,
            original_text_for_map_search,
            substituted_address_nearby='',
            is_from_substituted_address=False,
            is_from_test_ballot=False):
        # We assume that we tried to find an entry for this voter
        voter_ballot_saved_found = False
        try:
            if positive_value_exists(voter_id) and positive_value_exists(google_civic_election_id):
                voter_ballot_saved, created = VoterBallotSaved.objects.update_or_create(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    defaults={
                        'voter_id': voter_id,
                        'google_civic_election_id': google_civic_election_id,
                        'election_date': election_date_text,
                        'election_description_text': election_description_text,
                        'original_text_for_map_search': original_text_for_map_search,
                        'substituted_address_nearby': substituted_address_nearby,
                        'is_from_substituted_address': is_from_substituted_address,
                        'is_from_test_ballot': is_from_test_ballot
                    }
                )
                voter_ballot_saved_found = voter_ballot_saved.id
                status = "BALLOT_SAVED"
                success = True
            else:
                voter_ballot_saved = None
                status = "UNABLE_TO_CREATE_BALLOT_SAVED"
                success = False
                google_civic_election_id = 0
        except Exception as e:
            status = "UNABLE_TO_CREATE_BALLOT_SAVED_EXCEPTION"
            success = False
            voter_ballot_saved = None
            google_civic_election_id = 0

        results = {
            'status':                   status,
            'success':                  success,
            'voter_ballot_saved_found': voter_ballot_saved_found,
            'voter_ballot_saved':       voter_ballot_saved,
            'google_civic_election_id': google_civic_election_id,
        }
        return results


def copy_existing_ballot_items_from_stored_ballot(voter_id, text_for_map_search, google_civic_election_id=0):
    """
    We are looking for the most recent ballot near this voter. We may or may not have a google_civic_election_id
    :param voter_id:
    :param text_for_map_search:
    :param google_civic_election_id:
    :return:
    """
    #
    ballot_returned_manager = BallotReturnedManager()
    find_results = ballot_returned_manager.find_closest_ballot_returned(text_for_map_search, google_civic_election_id)

    if not find_results['ballot_returned_found']:
        error_results = {
            'voter_id':                     voter_id,
            'google_civic_election_id':     0,
            'election_date_text':           '',
            'election_description_text':    '',
            'text_for_map_search':          text_for_map_search,
            'substituted_address_nearby':   '',
            'ballot_returned_copied':       False,
        }
        return error_results

    # A ballot at a nearby address was found. Copy it for the voter.
    ballot_returned = find_results['ballot_returned']
    ballot_item_list_manager = BallotItemListManager()
    copy_item_results = ballot_item_list_manager.copy_ballot_items(ballot_returned, voter_id)

    if not copy_item_results['ballot_returned_copied']:
        error_results = {
            'voter_id':                     voter_id,
            'google_civic_election_id':     0,
            'election_date_text':           '',
            'election_description_text':    '',
            'text_for_map_search':          text_for_map_search,
            'substituted_address_nearby':   '',
            'ballot_returned_copied':       False,
        }
        return error_results

    # VoterBallotSaved is updated outside of this function

    results = {
        'voter_id':                     voter_id,
        'google_civic_election_id':     ballot_returned.google_civic_election_id,
        'election_date_text':           ballot_returned.election_date_text(),
        'election_description_text':    ballot_returned.election_description_text,
        'text_for_map_search':          text_for_map_search,
        'substituted_address_nearby':   ballot_returned.text_for_map_search,
        'ballot_returned_copied':       True,
    }
    return results
