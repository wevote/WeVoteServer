# import_export_google_civic/models.py
# Brought to you by We Vote. Be good.
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.models import value_exists


logger = wevote_functions.admin.get_logger(__name__)


class GoogleCivicElection(models.Model):
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=20, null=False, unique=True)
    # The internal we vote unique ID of this election, so we can cross-check the data for integrity
    we_vote_election_id = models.CharField(
        verbose_name="we vote election id", max_length=20, null=True, blank=True, unique=True)
    # A displayable name for the election.
    name = models.CharField(verbose_name="google civic election name", max_length=254, null=False, blank=False)
    # Day of the election in YYYY-MM-DD format.
    election_day = models.CharField(verbose_name="google civic election day", max_length=254, null=False, blank=False)
    # is_by_election ???
    # is_primary_election = models.NullBooleanField(verbose_name="is primary election", null=True, blank=True)
    # is_runoff_election = models.NullBooleanField(verbose_name="is primary election", null=True, blank=True)
    # is_referendum
    # is_local
    # is_state
    # is_national
    # is_transnational
    # Has this entry been processed and transferred to the live We Vote tables?
    was_processed = models.BooleanField(verbose_name="is primary election", default=False, null=False, blank=False)


class GoogleCivicContestOffice(models.Model):
    # The name of the office for this contest.
    office = models.CharField(verbose_name="google civic office", max_length=254, null=False, blank=False)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=254, null=True, blank=True)
    # The internal We Vote unique ID of the election containing this contest, so we can check data-integrity of imports.
    we_vote_election_id = models.CharField(verbose_name="we vote election id", max_length=254, null=True, blank=True)
    # The internal We Vote unique ID of the election containing this contest, so we can check data-integrity of imports.
    we_vote_contest_office_id = models.CharField(
        verbose_name="we vote contest office id", max_length=254, null=True, blank=True)
    # The number of candidates that a voter may vote for in this contest.
    number_voting_for = models.CharField(verbose_name="google civic number of candidates to vote for",
                                         max_length=254, null=True, blank=True)
    # The number of candidates that will be elected to office in this contest.
    number_elected = models.CharField(verbose_name="google civic number of candidates who will be elected",
                                      max_length=254, null=True, blank=True)
    # The levels of government of the office for this contest. There may be more than one in cases where a
    # jurisdiction effectively acts at two different levels of government; for example, the mayor of the
    # District of Columbia acts at "locality" level, but also effectively at both
    # "administrative-area-2" and "administrative-area-1".
    contest_level0 = models.CharField(verbose_name="google civic level, option 0",
                                      max_length=254, null=True, blank=True)
    contest_level1 = models.CharField(verbose_name="google civic level, option 1",
                                      max_length=254, null=True, blank=True)
    contest_level2 = models.CharField(verbose_name="google civic level, option 2",
                                      max_length=254, null=True, blank=True)
    # A number specifying the position of this contest on the voter's ballot.
    ballot_placement = models.CharField(verbose_name="google civic ballot placement",
                                        max_length=254, null=True, blank=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=254, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="google civic district name", max_length=254, null=False, blank=False)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=254, null=False, blank=False)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_ocd_id = models.CharField(verbose_name="google civic district ocd id",
                                       max_length=254, null=False, blank=False)
    # A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = models.CharField(verbose_name="google civic primary party",
                                                 max_length=254, null=True, blank=True)
    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = models.CharField(verbose_name="google civic primary party", max_length=254, null=True, blank=True)
    # Has this entry been processed and transferred to the live We Vote tables?
    was_processed = models.BooleanField(verbose_name="is primary election", default=False, null=False, blank=False)


class GoogleCivicCandidateCampaign(models.Model):
    # The candidate's name.
    name = models.CharField(verbose_name="google civic candidate name", max_length=254, null=False, blank=False)
    # The full name of the party the candidate is a member of.
    party = models.CharField(verbose_name="google civic party", max_length=254, null=True, blank=True)
    # A URL for a photo of the candidate.
    photo_url = models.CharField(verbose_name="google civic photoUrl", max_length=254, null=True, blank=True)
    # The order the candidate appears on the ballot for this contest.
    order_on_ballot = models.CharField(
        verbose_name="google civic order on ballot", max_length=254, null=True, blank=True)
    # The internal temp google civic id for the ContestOffice that this candidate is competing for
    google_civic_contest_office_id = models.CharField(verbose_name="google civic internal temp contest_office_id id",
                                                      max_length=254, null=False, blank=False)
    # The internal master We Vote id for the ContestOffice that this candidate is competing for
    we_vote_contest_office_id = models.CharField(
        verbose_name="we vote contest_office_id id", max_length=254, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google election id",
                                                max_length=254, null=False, blank=False)
    # The internal We Vote unique ID of the election containing this contest, so we can check data-integrity of imports.
    we_vote_election_id = models.CharField(verbose_name="we vote election id", max_length=254, null=True, blank=True)
    # The internal We Vote unique ID of the candidate campaign, so we can check data-integrity of imports.
    we_vote_candidate_campaign_id = models.CharField(verbose_name="we vote candidate campaign id",
                                                     max_length=254, null=True, blank=True)
    # The internal We Vote unique ID of the Politician, so we can check data-integrity of imports.
    we_vote_politician_id = models.CharField(
        verbose_name="we vote politician id", max_length=254, null=True, blank=True)
    # The URL for the candidate's campaign web site.
    candidate_url = models.URLField(verbose_name='website url of candidate campaign', blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of candidate campaign', blank=True, null=True)
    twitter_url = models.URLField(verbose_name='twitter url of candidate campaign', blank=True, null=True)
    google_plus_url = models.URLField(verbose_name='google plus url of candidate campaign', blank=True, null=True)
    youtube_url = models.URLField(verbose_name='youtube url of candidate campaign', blank=True, null=True)
    # The email address for the candidate's campaign.
    email = models.CharField(verbose_name="google civic candidate campaign email",
                             max_length=254, null=True, blank=True)
    # The voice phone number for the candidate's campaign office.
    phone = models.CharField(verbose_name="google civic candidate campaign email",
                             max_length=254, null=True, blank=True)
    # Has this entry been processed and transferred to the live We Vote tables?
    was_processed = models.BooleanField(verbose_name="is primary election", default=False, null=False, blank=False)


class GoogleCivicContestReferendum(models.Model):
    # The title of the referendum (e.g. 'Proposition 42'). This field is only populated for contests
    # of type 'Referendum'.
    referendum_title = models.CharField(
        verbose_name="google civic referendum title", max_length=254, null=False, blank=False)
    # A brief description of the referendum. This field is only populated for contests of type 'Referendum'.
    referendum_subtitle = models.CharField(
        verbose_name="google civic referendum subtitle", max_length=254, null=False, blank=False)
    # A link to the referendum. This field is only populated for contests of type 'Referendum'.
    referendum_url = models.CharField(
        verbose_name="google civic referendum details url", max_length=254, null=True, blank=False)
    # The unique ID of the election containing this referendum. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=254, null=False, blank=False)
    # The internal We Vote unique ID of the election containing this referendum, so we can check integrity of imports.
    we_vote_election_id = models.CharField(
        verbose_name="we vote election id", max_length=254, null=True, blank=True)
    # A number specifying the position of this contest on the voter's ballot.
    ballot_placement = models.CharField(
        verbose_name="google civic ballot placement", max_length=254, null=True, blank=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=254, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="google civic district name", max_length=254, null=False, blank=False)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=254, null=False, blank=False)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_ocd_id = models.CharField(verbose_name="google civic district ocd id",
                                       max_length=254, null=False, blank=False)
    # A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = models.CharField(verbose_name="google civic primary party",
                                                 max_length=254, null=True, blank=True)
    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = models.CharField(verbose_name="google civic primary party", max_length=254, null=True, blank=True)
    # Has this entry been processed and transferred to the live We Vote tables?
    was_processed = models.BooleanField(verbose_name="is primary election", default=False, null=False, blank=False)


# TODO We need to add an index that forces each triplet of value to be unique
class GoogleCivicBallotItem(models.Model):
    """
    This is a generated table where we store the order items come in from Google Civic
    """
    # The unique id of the voter
    voter_id = models.IntegerField(verbose_name="the voter unique id", unique=False, null=False, blank=False)
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=20, null=False, unique=False)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_ocd_id = models.CharField(
        verbose_name="open civic data id", max_length=254, null=False, blank=False, unique=False)
    # This is the
    google_ballot_order = models.SmallIntegerField(
        verbose_name="the order this item should appear on the ballot", null=True, blank=True, unique=False)

    ballot_order = models.SmallIntegerField(
        verbose_name="locally calculated order this item should appear on the ballot", null=True, blank=True)


class GoogleCivicBallotItemManager(models.Model):

    def save_ballot_item_for_voter(
            self, voter_id, google_civic_election_id, google_civic_district_ocd_id, google_ballot_order,
            local_ballot_order):
        try:
            # Just try to save. If it is a duplicate entry, the save will fail due to unique requirements
            google_civic_ballot_item = GoogleCivicBallotItem(voter_id=voter_id,
                                                             google_civic_election_id=google_civic_election_id,
                                                             district_ocd_id=google_civic_district_ocd_id,
                                                             google_ballot_order=google_ballot_order,
                                                             ballot_order=local_ballot_order,)
            google_civic_ballot_item.save()
        except GoogleCivicBallotItem.DoesNotExist as e:
            pass

    def retrieve_ballot_item_for_voter(self, voter_id, google_civic_election_id, google_civic_district_ocd_id):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        google_civic_ballot_item_on_stage = GoogleCivicBallotItem()

        if value_exists(voter_id) and value_exists(google_civic_election_id) and value_exists(
                google_civic_district_ocd_id):
            try:
                google_civic_ballot_item_on_stage = GoogleCivicBallotItem.objects.get(
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    district_ocd_id=google_civic_district_ocd_id,
                )
                google_civic_ballot_item_id = google_civic_ballot_item_on_stage.id
            except GoogleCivicBallotItem.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                exception_multiple_object_returned = True
            except GoogleCivicBallotItem.DoesNotExist as e:
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
