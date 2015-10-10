# office/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_id_we_vote_last_contest_office_integer, fetch_site_unique_id_prefix
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class ContestOffice(models.Model):
    # The id_we_vote identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "off", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.id_we_vote_last_contest_office_integer
    id_we_vote = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)
    # The name of the office for this contest.
    office_name = models.CharField(verbose_name="google civic office", max_length=254, null=False, blank=False)
    # The We Vote unique id for the election
    election_id = models.CharField(verbose_name="we vote election id", max_length=254, null=False, blank=False)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=254, null=False, blank=False)
    id_cicero = models.CharField(
        verbose_name="azavea cicero unique identifier", max_length=254, null=True, blank=True, unique=True)
    id_maplight = models.CharField(
        verbose_name="maplight unique identifier", max_length=254, null=True, blank=True, unique=True)
    id_ballotpedia = models.CharField(
        verbose_name="ballotpedia unique identifier", max_length=254, null=True, blank=True)
    id_wikipedia = models.CharField(verbose_name="wikipedia unique identifier", max_length=254, null=True, blank=True)
    # vote_type (ranked choice, majority)

    # ballot_placement: NOTE - even though GoogleCivicContestOffice has this field, we store this value
    #  in the BallotItem table instead because it is different for each voter

    # The number of candidates that a voter may vote for in this contest.
    number_voting_for = models.CharField(verbose_name="number of candidates to vote for",
                                         max_length=254, null=True, blank=True)
    # The number of candidates that will be elected to office in this contest.
    number_elected = models.CharField(verbose_name="number of candidates who will be elected",
                                      max_length=254, null=True, blank=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="primary party", max_length=254, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="district name", max_length=254, null=False, blank=False)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="district scope", max_length=254, null=False, blank=False)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_ocd_id = models.CharField(verbose_name="open civic data id", max_length=254, null=False, blank=False)

    # We override the save function so we can auto-generate id_we_vote
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique id_we_vote
        if self.id_we_vote:
            self.id_we_vote = self.id_we_vote.strip()
        if self.id_we_vote == "" or self.id_we_vote is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_id_we_vote_last_contest_office_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "off" = tells us this is a unique id for a ContestOffice
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.id_we_vote = "wv{site_unique_id_prefix}off{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ContestOffice, self).save(*args, **kwargs)


class ContestOfficeManager(models.Model):

    def __unicode__(self):
        return "ContestOfficeManager"

    def retrieve_contest_office_from_id(self, contest_office_id):
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id)

    def retrieve_contest_office_from_id_maplight(self, id_maplight):
        contest_office_id = 0
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, id_maplight)

    def fetch_contest_office_id_from_id_maplight(self, id_maplight):
        contest_office_id = 0
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office(contest_office_id, id_maplight)
        if results['success']:
            return results['contest_office_id']
        return 0

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_contest_office(self, contest_office_id, id_maplight=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        contest_office_on_stage = ContestOffice()

        try:
            if contest_office_id > 0:
                contest_office_on_stage = ContestOffice.objects.get(id=contest_office_id)
                contest_office_id = contest_office_on_stage.id
            elif len(id_maplight) > 0:
                contest_office_on_stage = ContestOffice.objects.get(id_maplight=id_maplight)
                contest_office_id = contest_office_on_stage.id
        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
        except ContestOffice.DoesNotExist:
            exception_does_not_exist = True

        results = {
            'success':                  True if contest_office_id > 0 else False,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'contest_office_found':     True if contest_office_id > 0 else False,
            'contest_office_id':        contest_office_id,
            'contest_office':           contest_office_on_stage,
        }
        return results
