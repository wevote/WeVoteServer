# ballot/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class BallotItem(models.Model):
    """
    This is a generated table with ballot item data from a variety of sources, including Google Civic
    (and MapLight, Ballot API Code for America project, and Azavea Cicero in the future)
    """
    # The unique id of the voter
    voter_id = models.IntegerField(verbose_name="the voter unique id", default=0, null=False, blank=False)
    # The We Vote unique ID of this election
    election_id = models.CharField(verbose_name="election id", max_length=20, null=True)
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id", max_length=20, null=True)
    # The internal We Vote id for the ContestOffice that this candidate is competing for
    contest_office_id = models.CharField(verbose_name="contest_office_id id", max_length=254, null=True, blank=True)
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_measure_id = models.CharField(
        verbose_name="contest_measure unique id", max_length=254, null=True, blank=True)
    ballot_order = models.SmallIntegerField(
        verbose_name="the order this item should appear on the ballot", null=True, blank=True)
    # This is a sortable name
    ballot_item_label = models.CharField(verbose_name="a label we can sort by", max_length=254, null=True, blank=True)

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
        candidates_list_temp = candidates_list_temp.filter(election_id=self.election_id)
        candidates_list_temp = candidates_list_temp.filter(contest_office_id=self.contest_office_id)
        return candidates_list_temp


class BallotItemManager(models.Model):

    def retrieve_all_ballot_items_for_voter(self, voter_id, election_id=0):
        ballot_item_list = BallotItem.objects.order_by('ballot_order')

        results = {
            'election_id':      election_id,
            'voter_id':         voter_id,
            'ballot_item_list': ballot_item_list,
        }
        return results

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
