# ballot/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateCampaign
from django.db import models
from exception.models import handle_exception, handle_record_found_more_than_one_exception, \
    handle_record_not_found_exception
import wevote_functions.admin
from wevote_functions.models import positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


class BallotItem(models.Model):
    """
    This is a generated table with ballot item data from a variety of sources, including Google Civic
    One ballot item is either 1) a measure/referendum or 2) an office that is being competed for
    """
    # The unique id of the voter
    voter_id = models.IntegerField(verbose_name="the voter unique id", default=0, null=False, blank=False)

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
        blank=True, unique=True)
    # The local database id for this measure, specific to this server.
    # TODO contest_measure_id should be positive integer as opposed to CharField
    contest_measure_id = models.CharField(
        verbose_name="contest_measure unique id", max_length=255, null=True, blank=True)
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this measure", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # This is a sortable name
    ballot_item_label = models.CharField(verbose_name="a label we can sort by", max_length=255, null=True, blank=True)

    def is_contest_office(self):
        if self.contest_office_id:
            return True
        return False

    def is_contest_measure(self):
        if self.contest_measure_id:
            return True
        return False

    def display_ballot_item(self):
        return self.ballot_item_label

    def candidates_list(self):
        candidates_list_temp = CandidateCampaign.objects.all()
        candidates_list_temp = candidates_list_temp.filter(google_civic_election_id=self.google_civic_election_id)
        candidates_list_temp = candidates_list_temp.filter(contest_office_id=self.contest_office_id)
        return candidates_list_temp


class BallotItemManager(models.Model):
    # NOTE: This method only needs to hit the database at most once per day.
    # We should cache the results in a JSON file that gets cached on the server and locally in the
    # voter's browser for speed.
    def retrieve_my_ballot(self, voter_on_stage, election_on_stage):
        # Retrieve all of the jurisdictions the voter is in
        print voter_on_stage
        print election_on_stage

        # Retrieve all of the office_contests in each of those jurisdictions

        # Retrieve all of the measure_contests in each of those jurisdictions
        return True

    def update_or_create_ballot_item_for_voter(
            self, voter_id, google_civic_election_id, google_ballot_placement, ballot_item_label,
            local_ballot_order, contest_measure_id=0, contest_office_id=0, contest_office_we_vote_id=''):
        exception_multiple_object_returned = False
        new_ballot_item_created = False

        if not contest_measure_id and not contest_office_id:
            success = False
            status = 'MISSING_OFFICE_AND_MEASURE_IDS'
        elif not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID'
        elif not voter_id:
            success = False
            status = 'MISSING_VOTER_ID'
        else:
            try:
                updated_values = {
                    # Values we search against
                    'contest_measure_id': contest_measure_id,
                    'contest_office_id': contest_office_id,
                    'google_civic_election_id': google_civic_election_id,
                    'voter_id': voter_id,
                    # The rest of the values
                    'google_ballot_placement': google_ballot_placement,
                    'local_ballot_order': local_ballot_order,
                    'ballot_item_label': ballot_item_label,
                    'contest_office_we_vote_id': contest_office_we_vote_id,
                }
                ballot_item_on_stage, new_ballot_item_created = BallotItem.objects.update_or_create(
                    contest_measure_id__exact=contest_measure_id,
                    contest_office_id__exact=contest_office_id,
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_id__exact=voter_id,
                    defaults=updated_values)
                success = True
                status = 'BALLOT_ITEM_SAVED'
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
            except BallotItem.DoesNotExist as e:
                exception_does_not_exist = True

        results = {
            'success':                          True if google_civic_ballot_item_id > 0 else False,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'google_civic_ballot_item':         google_civic_ballot_item_on_stage,
        }
        return results

    def fetch_ballot_order(self, voter_id, google_civic_election_id, google_civic_district_ocd_id):
        # voter_id, google_civic_contest_office_on_stage.google_civic_election_id,
        # google_civic_contest_office_on_stage.district_ocd_id)

        return 3


class BallotItemList(models.Model):
    """
    A way to retrieve a list of ballot_items
    """
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
        except BallotItem.DoesNotExist as e:
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
        ballot_item_list = []
        ballot_item_list_found = False
        try:
            ballot_item_queryset = BallotItem.objects.order_by('local_ballot_order')
            ballot_item_list = ballot_item_queryset

            if len(ballot_item_list):
                ballot_item_list_found = True
                status = 'BALLOT_ITEMS_FOUND, retrieve_all_ballot_items_for_voter'
            else:
                status = 'NO_BALLOT_ITEMS_FOUND_0'
        except BallotItem.DoesNotExist as e:
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
            'ballot_item_list_found':       ballot_item_list_found,
            'ballot_item_list':             ballot_item_list,
        }
        return results
