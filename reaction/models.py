# reaction/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# Any item is liked if there is an entry, and NOT liked if there is no entry
class ReactionLike(models.Model):

    def __unicode__(self):
        return "ReactionLike"

    # We are relying on built-in Python id field
    # We include voter_id for fastest retrieve, and voter_we_vote_id for the WebApp functions
    voter_id = models.PositiveIntegerField(default=None, null=True, db_index=True)
    voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    voter_display_name = models.CharField(max_length=255, null=True)

    # The item being liked
    liked_item_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    # The parent of the liked item so we can group together all related likes
    activity_tidbit_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)

    # The date the voter liked this position
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class ReactionLikeManager(models.Manager):

    def __unicode__(self):
        return "ReactionLikeManager"

    def count_all_reaction_likes(self, liked_item_we_vote_id):
        # How many people, across the entire network, like this position?
        try:
            reaction_like_query = ReactionLike.objects.all()
            reaction_like_query = reaction_like_query.filter(liked_item_we_vote_id=liked_item_we_vote_id)
            number_of_likes = reaction_like_query.count()
            status = "REACTION_LIKE_ALL_COUNT_RETRIEVED"
            success = True
        except Exception as e:
            status = "REACTION_LIKE_ALL_COUNT_FAILED: {error}".format(error=e)
            success = True
            number_of_likes = 0

        results = {
            'status':                   status,
            'success':                  success,
            'number_of_likes':          number_of_likes,
            'liked_item_we_vote_id':    liked_item_we_vote_id,
        }
        return results

    def retrieve_reaction_like(
            self,
            reaction_like_id=0,
            voter_id=0,
            liked_item_we_vote_id=''):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        reaction_like = ReactionLike()

        try:
            if positive_value_exists(reaction_like_id):
                reaction_like = ReactionLike.objects.get(id=reaction_like_id)
                reaction_like_id = reaction_like.id
                status = 'REACTION_LIKE_FOUND_WITH_ID'
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(liked_item_we_vote_id):
                reaction_like = ReactionLike.objects.get(
                    voter_id=voter_id,
                    liked_item_we_vote_id=liked_item_we_vote_id)
                reaction_like_id = reaction_like.id
                status = 'REACTION_LIKE_FOUND_WITH_VOTER_ID_AND_POSITION_ID'
                success = True
            else:
                status = 'REACTION_LIKE_NOT_FOUND-MISSING_VARIABLES'
                success = False
        except ReactionLike.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            status = 'REACTION_LIKE_NOT_FOUND_MultipleObjectsReturned'
            success = False
        except ReactionLike.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            status = 'REACTION_LIKE_NOT_FOUND_DoesNotExist'
            success = True

        reaction_like_found = True if reaction_like_id > 0 else False
        results = {
            'status':                   status,
            'success':                  success,
            'reaction_like_found':      reaction_like_found,
            'reaction_like_id':         reaction_like_id,
            'reaction':            reaction_like,
            'is_liked':                 reaction_like_found,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results

    def retrieve_reaction_like_list_for_voter(self, voter_id):
        # Retrieve a list of reaction entries for this voter
        reaction_like_list_found = False
        reaction_like_list = {}
        try:
            reaction_like_list = ReactionLike.objects.all()
            reaction_like_list = reaction_like_list.filter(voter_id=voter_id)
            if len(reaction_like_list):
                reaction_like_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if reaction_like_list_found:
            return reaction_like_list
        else:
            reaction_like_list = {}
            return reaction_like_list

    def count_voter_network_reaction_likes(self, liked_item_we_vote_id, voter_id):
        # How many people, limited to the voter's network, like this position?  # TODO limit to just the voter's network
        try:
            reaction_like_query = ReactionLike.objects.all()
            reaction_like_query = reaction_like_query.filter(liked_item_we_vote_id=liked_item_we_vote_id)
            number_of_likes = reaction_like_query.count()
            status = "REACTION_LIKE_VOTER_NETWORK_COUNT_RETRIEVED"
            success = True
        except Exception as e:
            status = "REACTION_LIKE_VOTER_NETWORK_COUNT_FAILED: {error}".format(error=e)
            success = True
            number_of_likes = 0

        results = {
            'status':                   status,
            'success':                  success,
            'number_of_likes':          number_of_likes,
            'liked_item_we_vote_id':      liked_item_we_vote_id,
        }
        return results

    def toggle_off_voter_reaction_like(
            self,
            liked_item_we_vote_id='',
            reaction_like_id=0,
            voter_id=0):
        status = ''
        success = True
        if positive_value_exists(reaction_like_id):
            try:
                ReactionLike.objects.filter(id=reaction_like_id).delete()
                status += "DELETED_BY_REACTION_LIKE_ID "
            except Exception as e:
                status += "UNABLE_TO_DELETE_BY_REACTION_LIKE_ID: " + str(e) + ' '
                success = False
        elif positive_value_exists(voter_id) and positive_value_exists(liked_item_we_vote_id):
            try:
                ReactionLike.objects.filter(voter_id=voter_id, liked_item_we_vote_id=liked_item_we_vote_id).delete()
                status += "DELETED_BY_VOTER_ID_AND_LIKED_ITEM_WE_VOTE_ID "
            except Exception as e:
                status += "UNABLE_TO_DELETE_BY_VOTER_ID_AND_LIKED_ITEM_WE_VOTE_ID: " + str(e) + ' '
                success = False
        else:
            status += "UNABLE_TO_DELETE_NO_VARIABLES "
            success = False

        results = {
            'status':   status,
            'success':  success,
        }
        return results

    def toggle_on_voter_reaction_like(
            self,
            voter_id=0,
            voter_we_vote_id=0,
            voter_display_name='',
            liked_item_we_vote_id='',
            activity_tidbit_we_vote_id=''):
        status = ''
        success = True
        # Does a reaction entry exist from this voter already exist?
        reaction_like_manager = ReactionLikeManager()
        reaction_like_id = 0
        results = reaction_like_manager.retrieve_reaction_like(
            reaction_like_id=0,
            voter_id=voter_id,
            liked_item_we_vote_id=liked_item_we_vote_id)

        reaction_like_found = False
        reaction_like = ReactionLike()
        if results['reaction_like_found']:
            # This means there is already an entry
            reaction_like = results['reaction']
            # Update the activity_tidbit_we_vote_id
            try:
                reaction_like.activity_tidbit_we_vote_id = activity_tidbit_we_vote_id
                reaction_like.save()
            except Exception as e:
                status += "COULD_NOT_UPDATE_REACTION_LIKE: " + str(e) + " "
            reaction_like_id = results['reaction_like_id']
            reaction_like_found = True
            status += results['status']
        elif results['DoesNotExist']:
            try:
                # Create new reaction entry
                reaction_like = ReactionLike(
                    voter_id=voter_id,
                    voter_we_vote_id=voter_we_vote_id,
                    voter_display_name=voter_display_name,
                    liked_item_we_vote_id=liked_item_we_vote_id,
                    activity_tidbit_we_vote_id=activity_tidbit_we_vote_id
                )
                reaction_like.save()
                reaction_like_id = reaction_like.id
                reaction_like_found = True
                status += 'REACTION_LIKE_CREATED '
            except Exception as e:
                status += "REACTION_LIKE_NOT_CREATED: " + str(e) + ' '
                success = False
        else:
            status += results['status']
            success = False

        results = {
            'success':              success,
            'status':               status,
            'reaction_like':        reaction_like,
            'reaction_like_found':  reaction_like_found,
            'reaction_like_id':     reaction_like_id,
        }
        return results
