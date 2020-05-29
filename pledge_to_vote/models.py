# pledge_to_vote/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from wevote_functions.functions import positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_pledge_integer, fetch_site_unique_id_prefix


class PledgeToVote(models.Model):
    """
    When a voter pledges to vote or “stand with” an organization for a particular election.
    """
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "pledge", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_pledge_integer
    we_vote_id = models.CharField(
        verbose_name="we vote id of this pledge", max_length=255, default=None, null=True,
        blank=True, unique=True)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the voter who made the pledge", max_length=255, null=True, unique=False)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote id for the organization running pledge campaign", max_length=255, null=True, unique=False)
    voter_guide_we_vote_id = models.CharField(
        verbose_name="we vote id for the voter guide of pledge campaign", max_length=255, null=True, unique=False)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    # Was this pledge one that included taking the same positions? ("I stand with" vs. "I pledge to vote")
    take_same_positions = models.BooleanField(default=False)
    # Is this a public pledge?
    visible_to_public = models.BooleanField(default=False)
    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now_add=True)
    deleted = models.BooleanField(default=False)  # Undo a pledge

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_pledge_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "pledge" = tells us this is a unique id for a PledgeToVote
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}pledge{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(PledgeToVote, self).save(*args, **kwargs)


class PledgeToVoteManager(models.Model):
    # Extending models.Models creates a useless empty table, we probably want to extend models.Manager here
    def __unicode__(self):
        return "PledgeToVoteManager"

    def delete_duplicate_pledges(self, voter_we_vote_id, voter_guide_we_vote_id):
        """
        Delete all existing pledges. We will save a new one.
        :param voter_we_vote_id:
        :param voter_guide_we_vote_id:
        :return:
        """
        status = ""
        try:
            pledge_queryset = PledgeToVote.objects.all()
            pledge_queryset = pledge_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            pledge_queryset = pledge_queryset.filter(voter_guide_we_vote_id__iexact=voter_guide_we_vote_id)
            pledge_list = list(pledge_queryset)
            for one_pledge in pledge_list:
                one_pledge.delete()
        except Exception as e:
            success = False
            status += 'CURRENT_PLEDGE_NOT_FOUND-QUERY_ERROR '
        return

    def update_or_create_pledge_to_vote(
            self, voter_we_vote_id, voter_guide_we_vote_id, organization_we_vote_id, google_civic_election_id,
            take_same_positions='', visible_to_public='', pledge_to_vote_we_vote_id=''):

        # If we have variables that we might want to update, check to see if an entry already exists
        # organization_we_vote_id, visible_to_public, pledge_to_vote_we_vote_id

        pledge_to_vote = PledgeToVote()
        pledge_to_vote_saved = False
        pledge_found = False
        voter_has_pledged = False
        success = False
        status = ""
        try:
            pledge_queryset = PledgeToVote.objects.using('readonly').all()
            if positive_value_exists(pledge_to_vote_we_vote_id):
                pledge_queryset = pledge_queryset.filter(we_vote_id__iexact=pledge_to_vote_we_vote_id)
            else:
                pledge_queryset = pledge_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
                if positive_value_exists(voter_guide_we_vote_id):
                    pledge_queryset = pledge_queryset.filter(
                        voter_guide_we_vote_id__iexact=voter_guide_we_vote_id)
                else:
                    pledge_queryset = pledge_queryset.filter(
                        organization_we_vote_id__iexact=organization_we_vote_id)
            pledge_to_vote = pledge_queryset.get()
            pledge_found = True
            success = True
            status += 'PLEDGE_FOUND '
            voter_has_pledged = True
        except PledgeToVote.MultipleObjectsReturned as e:
            self.delete_duplicate_pledges(voter_we_vote_id, voter_guide_we_vote_id)
            status += 'MULTIPLE_PLEDGES_FOUND-DELETING '
        except PledgeToVote.DoesNotExist:
            status += 'PLEDGE_NOT_FOUND-NOT_A_PROBLEM '
        except Exception as e:
            success = False
            status += 'CURRENT_PLEDGE_NOT_FOUND-QUERY_ERROR '
            voter_has_pledged = False

        if pledge_found:
            pass
        else:
            try:
                pledge_to_vote = PledgeToVote.objects.create(
                    voter_we_vote_id=voter_we_vote_id,
                    voter_guide_we_vote_id=voter_guide_we_vote_id,
                    organization_we_vote_id=organization_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    take_same_positions=take_same_positions,
                    visible_to_public=visible_to_public,
                )
                pledge_to_vote_saved = True
                success = True
                status += "PLEDGE_TO_VOTE_CREATED "
                voter_has_pledged = True
            except Exception as e:
                pledge_to_vote_saved = False
                pledge_to_vote = PledgeToVote()
                success = False
                status += "PLEDGE_TO_VOTE_NOT_CREATED "
                voter_has_pledged = False

        results = {
            'success':              success,
            'status':               status,
            'pledge_to_vote_saved': pledge_to_vote_saved,
            'pledge_to_vote':       pledge_to_vote,
            'voter_has_pledged':    voter_has_pledged,
        }
        return results

    def retrieve_pledge_to_vote(self, pledge_to_vote_we_vote_id, voter_we_vote_id="", voter_guide_we_vote_id="",
                                organization_we_vote_id="", google_civic_election_id=""):

        pledge_to_vote = PledgeToVote()
        pledge_to_vote_saved = False
        pledge_found = False
        voter_has_pledged = False
        success = False
        status = ""
        try:
            pledge_queryset = PledgeToVote.objects.using('readonly').all()
            if positive_value_exists(pledge_to_vote_we_vote_id):
                pledge_queryset = pledge_queryset.filter(we_vote_id__iexact=pledge_to_vote_we_vote_id)
            else:
                pledge_queryset = pledge_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
                if positive_value_exists(voter_guide_we_vote_id):
                    pledge_queryset = pledge_queryset.filter(
                        voter_guide_we_vote_id__iexact=voter_guide_we_vote_id)
                else:
                    pledge_queryset = pledge_queryset.filter(
                        organization_we_vote_id__iexact=organization_we_vote_id)
                    pledge_queryset = pledge_queryset.filter(
                        google_civic_election_id__iexact=google_civic_election_id)
            pledge_to_vote = pledge_queryset.get()
            pledge_found = True
            success = True
            status += 'PLEDGE_FOUND '
            voter_has_pledged = True
        except PledgeToVote.MultipleObjectsReturned as e:
            status += 'MULTIPLE_PLEDGES_FOUND '
        except PledgeToVote.DoesNotExist:
            status += 'PLEDGE_NOT_FOUND-NOT_A_PROBLEM '
            pledge_found = False
        except Exception as e:
            success = False
            status += 'CURRENT_PLEDGE_NOT_FOUND-QUERY_ERROR '
            voter_has_pledged = False

        results = {
            'success':              success,
            'status':               status,
            'pledge_to_vote_saved': pledge_to_vote_saved,
            'pledge_to_vote':       pledge_to_vote,
            'pledge_found':         pledge_found,
            'voter_has_pledged':    voter_has_pledged,
        }
        return results

    # def retrieve_voter_pledges_list(self, voter_we_vote_id):  # TODO Implement this
    #     """
    #
    #     :param voter_we_vote_id:
    #     :return:
    #     """
    #     if not positive_value_exists(voter_we_vote_id):
    #         success = False
    #         status = 'VALID_VOTER_WE_VOTE_ID_MISSING'
    #         results = {
    #             'success':                  success,
    #             'status':                   status,
    #             'voter_we_vote_id':         voter_we_vote_id,
    #             'email_address_list_found': False,
    #             'email_address_list':       [],
    #         }
    #         return results
    #
    #     email_address_list = []
    #     try:
    #         email_address_queryset = EmailAddress.objects.all()
    #         email_address_queryset = email_address_queryset.filter(
    #             voter_we_vote_id__iexact=voter_we_vote_id,
    #             deleted=False
    #         )
    #         email_address_queryset = email_address_queryset.order_by('-id')  # Put most recent email at top of list
    #         email_address_list = email_address_queryset
    #
    #         if len(email_address_list):
    #             success = True
    #             email_address_list_found = True
    #             status = 'EMAIL_ADDRESS_LIST_RETRIEVED'
    #         else:
    #             success = True
    #             email_address_list_found = False
    #             status = 'NO_EMAIL_ADDRESS_LIST_RETRIEVED'
    #     except EmailAddress.DoesNotExist:
    #         # No data found. Not a problem.
    #         success = True
    #         email_address_list_found = False
    #         status = 'NO_EMAIL_ADDRESS_LIST_RETRIEVED_DoesNotExist'
    #         email_address_list = []
    #     except Exception as e:
    #         success = False
    #         email_address_list_found = False
    #         status = 'FAILED retrieve_voter_email_address_list EmailAddress'
    #
    #     results = {
    #         'success': success,
    #         'status': status,
    #         'voter_we_vote_id': voter_we_vote_id,
    #         'email_address_list_found': email_address_list_found,
    #         'email_address_list': email_address_list,
    #     }
    #     return results

    def retrieve_pledge_count_from_organization_we_vote_id(self, organization_we_vote_id):
        return self.retrieve_pledge_count("", organization_we_vote_id)

    def retrieve_pledge_count(self, voter_guide_we_vote_id, organization_we_vote_id=''):
        """
        Return the latest pledge count for a pledge campaign
        :param voter_guide_we_vote_id:
        :param organization_we_vote_id:
        :return:
        """
        pledge_goal = 0
        pledge_count = 0
        status = ""

        if not positive_value_exists(voter_guide_we_vote_id) and not positive_value_exists(organization_we_vote_id):
            success = False
            status = 'RETRIEVE_PLEDGE_COUNT-VALID_WE_VOTE_ID_MISSING'
            results = {
                'success':                 success,
                'status':                  status,
                'voter_guide_we_vote_id':  voter_guide_we_vote_id,
                'pledge_count_found':      False,
                'pledge_count':            0,
            }
            return results

        try:
            pledge_queryset = PledgeToVote.objects.using('readonly').all()
            if positive_value_exists(organization_we_vote_id):
                pledge_queryset = pledge_queryset.filter(
                    organization_we_vote_id__iexact=organization_we_vote_id)
            else:
                pledge_queryset = pledge_queryset.filter(
                    voter_guide_we_vote_id__iexact=voter_guide_we_vote_id)
            pledge_count = pledge_queryset.count()
            pledge_count_found = True
            success = True
            status += 'PLEDGE_COUNT_FOUND '
        except Exception as e:
            success = False
            pledge_count_found = False
            status += 'PLEDGE_COUNT_NOT_FOUND '

        results = {
            'success':                  success,
            'status':                   status,
            'voter_guide_we_vote_id':   voter_guide_we_vote_id,
            'pledge_count_found':       pledge_count_found,
            'pledge_count':             pledge_count,
        }
        return results

    def retrieve_pledge_statistics(self, voter_guide_we_vote_id):
        """
        Return the latest statistics on a pledge campaign
        :param voter_guide_we_vote_id:
        :return:
        """
        pledge_statistics_found = False
        pledge_goal = 0
        pledge_count = 0
        status = ""

        if not positive_value_exists(voter_guide_we_vote_id):
            success = False
            status = 'VALID_VOTER_GUIDE_WE_VOTE_ID_MISSING'
            results = {
                'success':                      success,
                'status':                       status,
                'voter_guide_we_vote_id':       voter_guide_we_vote_id,
                'pledge_statistics_found':      False,
                'pledge_goal':                  0,
                'pledge_count':                 0,
            }
            return results

        results = self.retrieve_pledge_count(voter_guide_we_vote_id)
        status += results['status']
        if results['pledge_count_found']:
            pledge_count = results['pledge_count']
            success = True
        else:
            success = False

        if success:
            pledge_statistics_found = True
            pledge_goal = 300  # TODO Get this from voter_guide

        results = {
            'success':                  success,
            'status':                   status,
            'voter_guide_we_vote_id':   voter_guide_we_vote_id,
            'pledge_statistics_found':  pledge_statistics_found,
            'pledge_goal':              pledge_goal,
            'pledge_count':             pledge_count,
        }
        return results

    def retrieve_pledge_to_vote_list(self, google_civic_election_id=0, organization_we_vote_id=""):
        success = False
        status = ""
        pledge_to_vote_list = []

        try:
            list_query = PledgeToVote.objects.all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                list_query = list_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            pledge_to_vote_list = list(list_query)
            pledge_to_vote_list_found = True
            status += "PLEDGE_TO_VOTE_LIST_FOUND "
        except Exception as e:
            pledge_to_vote_list_found = False
            status += "PLEDGE_TO_VOTE_LIST_NOT_FOUND-EXCEPTION "

        results = {
            'success': success,
            'status': status,
            'pledge_to_vote_list': pledge_to_vote_list,
            'pledge_to_vote_list_found': pledge_to_vote_list_found,
        }
        return results
