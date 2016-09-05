# position_like/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception
from position.models import PositionManager
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# Position is liked if there is an entry, and NOT liked if there is no entry
class PositionLike(models.Model):

    def __unicode__(self):
        return "PositionLike"

    # We are relying on built-in Python id field
    # The voter following the organization
    voter_id = models.BigIntegerField(null=True, blank=True)

    # The position being liked
    position_entered_id = models.BigIntegerField(null=True, blank=True)

    # The date the voter liked this position
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class PositionLikeManager(models.Model):

    def __unicode__(self):
        return "PositionLikeManager"

    def toggle_off_voter_position_like(self, position_like_id, voter_id, position_entered_id):
        if positive_value_exists(position_like_id):
            try:
                PositionLike.objects.filter(id=position_like_id).delete()
                status = "DELETED_BY_POSITION_LIKE_ID"
                success = True
            except Exception as e:
                status = "UNABLE_TO_DELETE_BY_POSITION_LIKE_ID: {error}".format(
                    error=e
                )
                success = False
        elif positive_value_exists(voter_id) and positive_value_exists(position_entered_id):
            try:
                PositionLike.objects.filter(voter_id=voter_id, position_entered_id=position_entered_id).delete()
                status = "DELETED_BY_VOTER_ID_AND_POSITION_ENTERED_ID"
                success = True
            except Exception as e:
                status = "UNABLE_TO_DELETE_BY_VOTER_ID_AND_POSITION_ENTERED_ID: {error}".format(
                    error=e
                )
                success = False
        else:
            status = "UNABLE_TO_DELETE_NO_VARIABLES"
            success = False

        results = {
            'status':   status,
            'success':  success,
        }
        return results

    def toggle_on_voter_position_like(self, voter_id, position_entered_id):
        # Does a position_like entry exist from this voter already exist?
        position_like_manager = PositionLikeManager()
        position_like_id = 0
        results = position_like_manager.retrieve_position_like(position_like_id, voter_id, position_entered_id)

        position_like_found = False
        position_like = PositionLike()
        if results['position_like_found']:
            # We don't need to do anything because this means there is already an entry
            position_like = results['position_like']
            position_like_id = results['position_like_id']
            position_like_found = True
            status = results['status']
        elif results['DoesNotExist']:
            try:
                # Create new position_like entry
                position_like = PositionLike(
                    voter_id=voter_id,
                    position_entered_id=position_entered_id,
                    # We don't need to update date_last_changed here because set set auto_now=True in the field
                )
                position_like.save()
                position_like_id = position_like.id
                position_like_found = True
                status = 'POSITION_LIKE_CREATED'
            except Exception as e:
                status = "POSITION_LIKE_NOT_CREATED: {error}".format(error=e)
        else:
            status = results['status']

        results = {
            'success':              True if position_like_found else False,
            'status':               status,
            'position_like_found':  position_like_found,
            'position_like_id':     position_like_id,
            'position_like':        position_like,
        }
        return results

    def retrieve_position_like(self, position_like_id, voter_id, position_entered_id):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        position_like = PositionLike()

        try:
            if positive_value_exists(position_like_id):
                position_like = PositionLike.objects.get(id=position_like_id)
                position_like_id = position_like.id
                status = 'POSITION_LIKE_FOUND_WITH_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(position_entered_id):
                position_like = PositionLike.objects.get(
                    voter_id=voter_id,
                    position_entered_id=position_entered_id)
                position_like_id = position_like.id
                status = 'POSITION_LIKE_FOUND_WITH_VOTER_ID_AND_POSITION_ID'
                success = True
            else:
                status = 'POSITION_LIKE_NOT_FOUND-MISSING_VARIABLES'
                success = False
        except PositionLike.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            status = 'POSITION_LIKE_NOT_FOUND_MultipleObjectsReturned'
            success = False
        except PositionLike.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            status = 'POSITION_LIKE_NOT_FOUND_DoesNotExist'
            success = True

        position_like_found = True if position_like_id > 0 else False
        results = {
            'status':                   status,
            'success':                  success,
            'position_like_found':      position_like_found,
            'position_like_id':         position_like_id,
            'position_like':            position_like,
            'is_liked':                 position_like_found,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results


class PositionLikeListManager(models.Model):
    """
    A way to retrieve all of the position_like information
    """
    def retrieve_position_like_list_for_voter(self, voter_id):
        # Retrieve a list of position_like entries for this voter
        position_like_list_found = False
        position_like_list = {}
        try:
            position_like_list = PositionLike.objects.all()
            position_like_list = position_like_list.filter(voter_id=voter_id)
            if len(position_like_list):
                position_like_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if position_like_list_found:
            return position_like_list
        else:
            position_like_list = {}
            return position_like_list

    def count_all_position_likes(self, position_entered_id):
        # How many people, across the entire network, like this position?
        try:
            position_like_query = PositionLike.objects.all()
            position_like_query = position_like_query.filter(position_entered_id=position_entered_id)
            number_of_likes = position_like_query.count()
            status = "POSITION_LIKE_ALL_COUNT_RETRIEVED"
            success = True
        except Exception as e:
            status = "POSITION_LIKE_ALL_COUNT_FAILED: {error}".format(error=e)
            success = True
            number_of_likes = 0

        results = {
            'status':                   status,
            'success':                  success,
            'number_of_likes':          number_of_likes,
            'position_entered_id':      position_entered_id,
        }
        return results

    def count_voter_network_position_likes(self, position_entered_id, voter_id):
        # How many people, limited to the voter's network, like this position?  # TODO limit to just the voter's network
        try:
            position_like_query = PositionLike.objects.all()
            position_like_query = position_like_query.filter(position_entered_id=position_entered_id)
            number_of_likes = position_like_query.count()
            status = "POSITION_LIKE_VOTER_NETWORK_COUNT_RETRIEVED"
            success = True
        except Exception as e:
            status = "POSITION_LIKE_VOTER_NETWORK_COUNT_FAILED: {error}".format(error=e)
            success = True
            number_of_likes = 0

        results = {
            'status':                   status,
            'success':                  success,
            'number_of_likes':          number_of_likes,
            'position_entered_id':      position_entered_id,
        }
        return results
