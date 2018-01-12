# bookmark/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateCampaignManager
from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from measure.models import ContestMeasureManager
from office.models import ContestOfficeManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from voter.models import VoterManager


ITEM_BOOKMARKED = 'BOOKMARKED'
ITEM_NOT_BOOKMARKED = 'NOT_BOOKMARKED'
BOOKMARK_CHOICES = (
    (ITEM_BOOKMARKED,      'Item Bookmarked'),
    (ITEM_NOT_BOOKMARKED,  'Item Not Bookmarked'),
)

logger = wevote_functions.admin.get_logger(__name__)


class BookmarkItem(models.Model):
    # We are relying on built-in Python id field
    # The voter following the organization
    voter_id = models.BigIntegerField(null=True, blank=True)

    # The candidate being bookmarked
    candidate_campaign_id = models.BigIntegerField(null=True, blank=True)
    candidate_campaign_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)
    # The office being bookmarked
    contest_office_id = models.BigIntegerField(null=True, blank=True)
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)
    # The measure being bookmarked
    contest_measure_id = models.BigIntegerField(null=True, blank=True)
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # Is this person following or ignoring this organization?
    bookmark_status = models.CharField(max_length=16, choices=BOOKMARK_CHOICES, default=ITEM_NOT_BOOKMARKED)

    # The date the voter bookmarked or unbookmarked this ballot_item
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # This is used when we want to export the organizations that a voter is following
    def voter_we_vote_id(self):
        voter_manager = VoterManager()
        return voter_manager.fetch_we_vote_id_from_local_id(self.voter_id)

    def ballot_item_we_vote_id(self):
        if self.candidate_campaign_we_vote_id:
            return self.candidate_campaign_we_vote_id
        elif self.contest_office_we_vote_id:
            return self.contest_office_we_vote_id
        elif self.contest_measure_we_vote_id:
            return self.contest_measure_we_vote_id
        elif self.candidate_campaign_id:
            candidate_campaign_manager = CandidateCampaignManager()
            return candidate_campaign_manager.fetch_candidate_campaign_we_vote_id_from_id(self.candidate_campaign_id)
        elif self.contest_measure_id:
            contest_measure_manager = ContestMeasureManager()
            return contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(self.contest_measure_id)
        elif self.contest_office_id:
            contest_office_manager = ContestOfficeManager()
            return contest_office_manager.fetch_contest_office_we_vote_id_from_id(self.contest_office_id)
        else:
            return 'not_found'

    def is_bookmarked(self):
        if self.bookmark_status == ITEM_BOOKMARKED:
            return True
        return False

    def is_not_bookmarked(self):
        if self.bookmark_status == ITEM_NOT_BOOKMARKED:
            return True
        return False


class BookmarkItemManager(models.Model):

    def __unicode__(self):
        return "BookmarkItemManager"

    # BOOKMARK ON
    def toggle_on_voter_bookmarked_candidate(self, voter_id, candidate_campaign_id):
        bookmark_status = ITEM_BOOKMARKED
        contest_office_id = None
        contest_measure_id = None
        bookmark_item_manager = BookmarkItemManager()
        return bookmark_item_manager.toggle_voter_bookmarked_item(
            voter_id, bookmark_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_on_voter_bookmarked_office(self, voter_id, contest_office_id):
        bookmark_status = ITEM_BOOKMARKED
        candidate_campaign_id = None
        contest_measure_id = None
        bookmark_item_manager = BookmarkItemManager()
        return bookmark_item_manager.toggle_voter_bookmarked_item(
            voter_id, bookmark_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_on_voter_bookmarked_measure(self, voter_id, contest_measure_id):
        bookmark_status = ITEM_BOOKMARKED
        candidate_campaign_id = None
        contest_office_id = None
        bookmark_item_manager = BookmarkItemManager()
        return bookmark_item_manager.toggle_voter_bookmarked_item(
            voter_id, bookmark_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    # BOOKMARK OFF
    def toggle_off_voter_bookmarked_candidate(self, voter_id, candidate_campaign_id):
        bookmark_status = ITEM_NOT_BOOKMARKED
        contest_office_id = None
        contest_measure_id = None
        bookmark_item_manager = BookmarkItemManager()
        return bookmark_item_manager.toggle_voter_bookmarked_item(
            voter_id, bookmark_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_off_voter_bookmarked_office(self, voter_id, contest_office_id):
        bookmark_status = ITEM_NOT_BOOKMARKED
        candidate_campaign_id = None
        contest_measure_id = None
        bookmark_item_manager = BookmarkItemManager()
        return bookmark_item_manager.toggle_voter_bookmarked_item(
            voter_id, bookmark_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_off_voter_bookmarked_measure(self, voter_id, contest_measure_id):
        bookmark_status = ITEM_NOT_BOOKMARKED
        candidate_campaign_id = None
        contest_office_id = None
        bookmark_item_manager = BookmarkItemManager()
        return bookmark_item_manager.toggle_voter_bookmarked_item(
            voter_id, bookmark_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_voter_bookmarked_item(
            self, voter_id, bookmark_status, candidate_campaign_id=None, contest_office_id=None, contest_measure_id=None,
            contest_office_we_vote_id='', candidate_campaign_we_vote_id='', contest_measure_we_vote_id=''):
        # Does a bookmark_item entry exist from this voter already exist?
        bookmark_item_manager = BookmarkItemManager()
        bookmark_item_id = 0
        results = bookmark_item_manager.retrieve_bookmark_item(
            bookmark_item_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id)

        bookmark_item_on_stage_found = False
        bookmark_item_on_stage_id = 0
        bookmark_item_on_stage = BookmarkItem()
        if results['bookmark_item_found']:
            bookmark_item_on_stage = results['bookmark_item']

            # Update this bookmark_item entry with new values - we do not delete because we might be able to use
            try:
                bookmark_item_on_stage.bookmark_status = bookmark_status
                # We don't need to update date_last_changed here because set set auto_now=True in the field
                bookmark_item_on_stage.save()
                bookmark_item_on_stage_id = bookmark_item_on_stage.id
                bookmark_item_on_stage_found = True
                status = 'UPDATE ' + bookmark_status
            except Exception as e:
                status = 'FAILED_TO_UPDATE ' + bookmark_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        elif results['MultipleObjectsReturned']:
            logger.warning("bookmark_item: delete all but one and take it over?")
            status = 'TOGGLE_ITEM_BOOKMARKED MultipleObjectsReturned ' + bookmark_status
        elif results['DoesNotExist']:
            try:
                # Create new bookmark_item entry
                if candidate_campaign_id and not candidate_campaign_we_vote_id:
                    candidate_campaign_manager = CandidateCampaignManager()
                    candidate_campaign_we_vote_id = \
                        candidate_campaign_manager.fetch_candidate_campaign_we_vote_id_from_id(candidate_campaign_id)
                if contest_measure_id and not contest_measure_we_vote_id:
                    contest_measure_manager = ContestMeasureManager()
                    contest_measure_we_vote_id = contest_measure_manager.fetch_contest_measure_we_vote_id_from_id(
                        contest_measure_id)
                if contest_office_id and not contest_office_we_vote_id:
                    contest_office_manager = ContestOfficeManager()
                    contest_office_we_vote_id = contest_office_manager.fetch_contest_office_we_vote_id_from_id(
                        contest_office_id)

                # NOTE: For speed purposes, we are not validating the existence of the items being bookmarked
                #  although we could if the we_vote_id is not returned.
                bookmark_item_on_stage = BookmarkItem(
                    voter_id=voter_id,
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                    contest_office_id=contest_office_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=contest_measure_we_vote_id,
                    bookmark_status=bookmark_status,
                    # We don't need to update date_last_changed here because set set auto_now=True in the field
                )
                bookmark_item_on_stage.save()
                bookmark_item_on_stage_id = bookmark_item_on_stage.id
                bookmark_item_on_stage_found = True
                status = 'CREATE ' + bookmark_status
            except Exception as e:
                status = 'FAILED_TO_UPDATE ' + bookmark_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            status = results['status']

        results = {
            'success':            True if bookmark_item_on_stage_found else False,
            'status':             status,
            'bookmark_item_found':    bookmark_item_on_stage_found,
            'bookmark_item_id':       bookmark_item_on_stage_id,
            'bookmark_item':          bookmark_item_on_stage,
        }
        return results

    def retrieve_bookmark_item(self, bookmark_item_id, voter_id, contest_office_id, candidate_campaign_id, contest_measure_id):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        bookmark_item_on_stage = BookmarkItem()
        bookmark_item_on_stage_id = 0

        try:
            if positive_value_exists(bookmark_item_id):
                bookmark_item_on_stage = BookmarkItem.objects.get(id=bookmark_item_id)
                bookmark_item_on_stage_id = bookmark_item_on_stage.id
                status = 'BOOKMARK_ITEM_FOUND_WITH_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_id):
                bookmark_item_on_stage = BookmarkItem.objects.get(
                    voter_id=voter_id,
                    candidate_campaign_id=candidate_campaign_id)
                bookmark_item_on_stage_id = bookmark_item_on_stage.id
                status = 'BOOKMARK_ITEM_FOUND_WITH_VOTER_ID_AND_CANDIDATE_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_id):
                bookmark_item_on_stage = BookmarkItem.objects.get(
                    voter_id=voter_id,
                    contest_office_id=contest_office_id)
                bookmark_item_on_stage_id = bookmark_item_on_stage.id
                status = 'BOOKMARK_ITEM_FOUND_WITH_VOTER_ID_AND_OFFICE_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_id):
                bookmark_item_on_stage = BookmarkItem.objects.get(
                    voter_id=voter_id,
                    contest_measure_id=contest_measure_id)
                bookmark_item_on_stage_id = bookmark_item_on_stage.id
                status = 'BOOKMARK_ITEM_FOUND_WITH_VOTER_ID_AND_MEASURE_ID'
                success = True
            else:
                status = 'BOOKMARK_ITEM_NOT_FOUND-MISSING_VARIABLES'
                success = False
        except BookmarkItem.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            status = 'BOOKMARK_ITEM_NOT_FOUND_MultipleObjectsReturned'
            success = False
        except BookmarkItem.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            status = 'BOOKMARK_ITEM_NOT_FOUND_DoesNotExist'
            success = True

        bookmark_item_on_stage_found = True if bookmark_item_on_stage_id > 0 else False
        results = {
            'status':                       status,
            'success':                      success,
            'bookmark_item_found':              bookmark_item_on_stage_found,
            'bookmark_item_id':                 bookmark_item_on_stage_id,
            'bookmark_item':                    bookmark_item_on_stage,
            'is_bookmarked':                   bookmark_item_on_stage.is_bookmarked(),
            'is_not_bookmarked':               bookmark_item_on_stage.is_not_bookmarked(),
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results


class BookmarkItemList(models.Model):
    """
    A way to retrieve all of the bookmark_item information
    """
    def retrieve_bookmark_item_list_for_voter(self, voter_id):
        return self.retrieve_bookmark_item_list(voter_id=voter_id)

    def retrieve_bookmark_item_list_for_candidate(self, candidate_campaign_we_vote_id):
        return self.retrieve_bookmark_item_list(candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)

    def retrieve_bookmark_item_list(self, voter_id=0, candidate_campaign_we_vote_id=""):
        # Retrieve a list of bookmark_item entries
        bookmark_item_list_found = False
        bookmark_item_list = []
        try:
            bookmark_item_list = BookmarkItem.objects.using('readonly').all()
            if positive_value_exists(voter_id):
                bookmark_item_list = bookmark_item_list.filter(voter_id=voter_id)
            if positive_value_exists(candidate_campaign_we_vote_id):
                bookmark_item_list = bookmark_item_list.filter(
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
            if len(bookmark_item_list):
                bookmark_item_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if bookmark_item_list_found:
            results = {
                'status':                   "BOOKMARK_ITEMS_FOUND",
                'success':                  True,
                'bookmark_item_list':       bookmark_item_list,
                'bookmark_item_list_found': bookmark_item_list_found,
            }
            return results
        else:
            results = {
                'status':                   "BOOKMARK_ITEMS_NOT_FOUND",
                'success':                  True,
                'bookmark_item_list':       [],
                'bookmark_item_list_found': bookmark_item_list_found,
            }
            return results
