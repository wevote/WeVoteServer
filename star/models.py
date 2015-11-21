# star/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
import wevote_functions.admin
from wevote_functions.models import positive_value_exists
from voter.models import VoterManager


ITEM_STARRED = 'ITEM_STARRED'
ITEM_NOT_STARRED = 'ITEM_NOT_STARRED'
STAR_CHOICES = (
    (ITEM_STARRED,      'Item Starred'),
    (ITEM_NOT_STARRED,  'Item Not Starred'),
)

logger = wevote_functions.admin.get_logger(__name__)


class StarItem(models.Model):
    # We are relying on built-in Python id field
    # The voter following the organization
    voter_id = models.BigIntegerField(null=True, blank=True)

    # The candidate being starred
    candidate_campaign_id = models.BigIntegerField(null=True, blank=True)
    # The office being starred
    contest_office_id = models.BigIntegerField(null=True, blank=True)
    # The measure being starred
    contest_measure_id = models.BigIntegerField(null=True, blank=True)

    # Is this person following or ignoring this organization?
    star_status = models.CharField(max_length=15, choices=STAR_CHOICES, default=ITEM_STARRED)

    # The date the voter followed or stopped following this organization
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # This is used when we want to export the organizations that a voter is following
    def voter_we_vote_id(self):
        voter_manager = VoterManager()
        return voter_manager.fetch_we_vote_id_from_local_id(self.voter_id)

    # This is used when we want to export the organizations that a voter is following
    # def candidate_campaign_we_vote_id(self):
    #     organization_manager = OrganizationManager()
    #     return organization_manager.fetch_we_vote_id_from_local_id(self.organization_id)

    def is_starred(self):
        if self.star_status == ITEM_STARRED:
            return True
        return False

    def is_not_starred(self):
        if self.star_status == ITEM_NOT_STARRED:
            return True
        return False


class StarItemManager(models.Model):

    def __unicode__(self):
        return "StarItemManager"

    # STAR ON
    def toggle_on_voter_starred_candidate(self, voter_id, candidate_campaign_id):
        star_status = ITEM_STARRED
        contest_office_id = 0
        contest_measure_id = 0
        star_item_manager = StarItemManager()
        return star_item_manager.toggle_voter_starred_item(
            voter_id, star_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_on_voter_starred_office(self, voter_id, contest_office_id):
        star_status = ITEM_STARRED
        candidate_campaign_id = 0
        contest_measure_id = 0
        star_item_manager = StarItemManager()
        return star_item_manager.toggle_voter_starred_item(
            voter_id, star_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_on_voter_starred_measure(self, voter_id, contest_measure_id):
        star_status = ITEM_STARRED
        candidate_campaign_id = 0
        contest_office_id = 0
        star_item_manager = StarItemManager()
        return star_item_manager.toggle_voter_starred_item(
            voter_id, star_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    # STAR OFF
    def toggle_off_voter_starred_candidate(self, voter_id, candidate_campaign_id):
        star_status = ITEM_NOT_STARRED
        contest_office_id = 0
        contest_measure_id = 0
        star_item_manager = StarItemManager()
        return star_item_manager.toggle_voter_starred_item(
            voter_id, star_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_off_voter_starred_office(self, voter_id, contest_office_id):
        star_status = ITEM_NOT_STARRED
        candidate_campaign_id = 0
        contest_measure_id = 0
        star_item_manager = StarItemManager()
        return star_item_manager.toggle_voter_starred_item(
            voter_id, star_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_off_voter_starred_measure(self, voter_id, contest_measure_id):
        star_status = ITEM_NOT_STARRED
        candidate_campaign_id = 0
        contest_office_id = 0
        star_item_manager = StarItemManager()
        return star_item_manager.toggle_voter_starred_item(
            voter_id, star_status, candidate_campaign_id, contest_office_id, contest_measure_id)

    def toggle_voter_starred_item(self, voter_id, star_status,
                                  candidate_campaign_id=0, contest_office_id=0, contest_measure_id=0):
        # Does a star_item entry exist from this voter already exist?
        star_item_manager = StarItemManager()
        star_item_id = 0
        results = star_item_manager.retrieve_star_item(star_item_id, voter_id,
                                                       candidate_campaign_id, contest_office_id, contest_measure_id)

        star_item_on_stage_found = False
        star_item_on_stage_id = 0
        star_item_on_stage = StarItem()
        if results['star_item_found']:
            star_item_on_stage = results['star_item']

            # Update this star_item entry with new values - we do not delete because we might be able to use
            try:
                star_item_on_stage.star_status = star_status
                # We don't need to update date_last_changed here because set set auto_now=True in the field
                star_item_on_stage.save()
                star_item_on_stage_id = star_item_on_stage.id
                star_item_on_stage_found = True
                status = 'UPDATE ' + star_status
            except Exception as e:
                status = 'FAILED_TO_UPDATE ' + star_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        elif results['MultipleObjectsReturned']:
            logger.warn("star_item: delete all but one and take it over?")
            status = 'TOGGLE_ITEM_STARRED MultipleObjectsReturned ' + star_status
        elif results['DoesNotExist']:
            try:
                # Create new star_item entry
                # NOTE: For speed purposes, we are not validating the existence of the items being starred
                star_item_on_stage = StarItem(
                    voter_id=voter_id,
                    candidate_campaign_id=candidate_campaign_id,
                    contest_office_id=contest_office_id,
                    contest_measure_id=contest_measure_id,
                    star_status=star_status,
                    # We don't need to update date_last_changed here because set set auto_now=True in the field
                )
                star_item_on_stage.save()
                star_item_on_stage_id = star_item_on_stage.id
                star_item_on_stage_found = True
                status = 'CREATE ' + star_status
            except Exception as e:
                status = 'FAILED_TO_UPDATE ' + star_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            status = results['status']

        results = {
            'success':            True if star_item_on_stage_found else False,
            'status':             status,
            'star_item_found':    star_item_on_stage_found,
            'star_item_id':       star_item_on_stage_id,
            'star_item':          star_item_on_stage,
        }
        return results

    def retrieve_star_item(self, star_item_id, voter_id, candidate_campaign_id, contest_office_id, contest_measure_id):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        star_item_on_stage = StarItem()
        star_item_on_stage_id = 0

        try:
            if positive_value_exists(star_item_id):
                star_item_on_stage = StarItem.objects.get(id=star_item_id)
                star_item_on_stage_id = star_item_on_stage.id
                status = 'STAR_ITEM_FOUND_WITH_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_id):
                star_item_on_stage = StarItem.objects.get(
                    voter_id=voter_id,
                    candidate_campaign_id=candidate_campaign_id)
                star_item_on_stage_id = star_item_on_stage.id
                status = 'STAR_ITEM_FOUND_WITH_VOTER_ID_AND_CANDIDATE_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_id):
                star_item_on_stage = StarItem.objects.get(
                    voter_id=voter_id,
                    contest_office_id=contest_office_id)
                star_item_on_stage_id = star_item_on_stage.id
                status = 'STAR_ITEM_FOUND_WITH_VOTER_ID_AND_OFFICE_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_id):
                star_item_on_stage = StarItem.objects.get(
                    voter_id=voter_id,
                    contest_measure_id=contest_measure_id)
                star_item_on_stage_id = star_item_on_stage.id
                status = 'STAR_ITEM_FOUND_WITH_VOTER_ID_AND_MEASURE_ID'
                success = True
            else:
                status = 'STAR_ITEM_NOT_FOUND-MISSING_VARIABLES'
                success = False
        except StarItem.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            status = 'STAR_ITEM_NOT_FOUND_MultipleObjectsReturned'
            success = False
        except StarItem.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            status = 'STAR_ITEM_NOT_FOUND_DoesNotExist'
            success = True

        star_item_on_stage_found = True if star_item_on_stage_id > 0 else False
        results = {
            'status':                       status,
            'success':                      success,
            'star_item_found':              star_item_on_stage_found,
            'star_item_id':                 star_item_on_stage_id,
            'star_item':                    star_item_on_stage,
            'is_starred':                   star_item_on_stage.is_starred(),
            'is_not_starred':               star_item_on_stage.is_not_starred(),
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results


class StarItemList(models.Model):
    """
    A way to retrieve all of the star_item information
    """
    def retrieve_star_item_info_for_voter(self, voter_id):
        # Retrieve a list of star_item entries for this voter
        star_item_list_found = False
        star_status = ITEM_STARRED
        star_item_list = {}
        try:
            star_item_list = StarItem.objects.all()
            star_item_list = star_item_list.filter(voter_id=voter_id)
            star_item_list = star_item_list.filter(star_status=star_status)
            if len(star_item_list):
                star_item_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if star_item_list_found:
            return star_item_list
        else:
            star_item_list = {}
            return star_item_list
