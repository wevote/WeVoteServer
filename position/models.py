# position/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
# Diagrams here: https://docs.google.com/drawings/d/1DsPnl97GKe9f14h41RPeZDssDUztRETGkXGaolXCeyo/edit

from candidate.models import CandidateCampaign
from django.db import models
from election.models import Election
from exception.models import handle_exception, handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from measure.models import ContestMeasure
from office.models import ContestOffice
from organization.models import Organization
from twitter.models import TwitterUser
from voter.models import Voter, VoterManager
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_position_integer, fetch_site_unique_id_prefix


ANY = 'ANY'  # This is a way to indicate when we want to return any stance (support, oppose, no_stance)
SUPPORT = 'SUPPORT'
STILL_DECIDING = 'STILL_DECIDING'
NO_STANCE = 'NO_STANCE'
INFORMATION_ONLY = 'INFO_ONLY'
OPPOSE = 'OPPOSE'
POSITION_CHOICES = (
    # ('SUPPORT_STRONG',    'Strong Supports'),  # I do not believe we will be offering 'SUPPORT_STRONG' as an option
    (SUPPORT,           'Supports'),
    (STILL_DECIDING,    'Still deciding'),  # Still undecided
    (NO_STANCE,         'No stance'),  # We don't know the stance
    (INFORMATION_ONLY,  'Information only'),  # This entry is meant as food-for-thought and is not advocating
    (OPPOSE,            'Opposes'),
    # ('OPPOSE_STRONG',     'Strongly Opposes'),  # I do not believe we will be offering 'OPPOSE_STRONG' as an option
)

logger = wevote_functions.admin.get_logger(__name__)


class PositionEntered(models.Model):
    """
    Any position entered by any person gets its own PositionEntered entry. We then
    generate Position entries that get used to display an particular org's position.
    """
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our org info with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "pos", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_position_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)

    # The id for the generated position that this PositionEntered entry influences
    position_id = models.BigIntegerField(null=True, blank=True)  # NOT USED CURRENTLY
    test = models.BigIntegerField(null=True, blank=True)
    ballot_item_label = models.CharField(verbose_name="text name for ballot item",
                                         max_length=255, null=True, blank=True)

    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now=True)
    # The organization this position is for
    organization_id = models.BigIntegerField(null=True, blank=True)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the organization", max_length=255, null=True,
        blank=True, unique=False)

    # The voter expressing the opinion
    voter_id = models.BigIntegerField(null=True, blank=True)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the voter expressing the opinion", max_length=255, null=True,
        blank=True, unique=False)

    # The unique id of the public figure expressing the opinion. May be null if position is from org or voter
    # instead of public figure.
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=False, blank=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)

    # The unique We Vote id of the tweet that is the source of the position
    tweet_source_id = models.BigIntegerField(null=True, blank=True)
    # This is the voter / authenticated user who entered the position for an organization
    #  (NOT the voter expressing opinion)
    voter_entering_position = models.ForeignKey(
        Voter, verbose_name='authenticated user who entered position', null=True, blank=True)
    # The Twitter user account that generated this position
    twitter_user_entered_position = models.ForeignKey(TwitterUser, null=True, verbose_name='')

    # This is the office that the position refers to.
    #  Either contest_measure is filled, contest_office OR candidate_campaign, but not all three
    contest_office_id = models.BigIntegerField(verbose_name='id of contest_office', null=True, blank=True)
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the contest_office", max_length=255, null=True, blank=True, unique=False)

    # This is the candidate/politician that the position refers to.
    #  Either candidate_campaign is filled, contest_office OR contest_measure, but not all three
    candidate_campaign_id = models.BigIntegerField(verbose_name='id of candidate_campaign', null=True, blank=True)
    candidate_campaign_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the candidate_campaign", max_length=255, null=True,
        blank=True, unique=False)
    # The candidate's name as passed over by Google Civic. We save this so we can match to this candidate if an import
    # doesn't include a we_vote_id we recognize.
    google_civic_candidate_name = models.CharField(verbose_name="candidate name exactly as received from google civic",
                                                   max_length=255, null=True, blank=True)
    # Useful for queries based on Politicians -- not the main table we use for ballot display though
    politician_id = models.BigIntegerField(verbose_name='', null=True, blank=True)
    politician_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for politician", max_length=255, null=True,
        blank=True, unique=False)

    # This is the measure/initiative/proposition that the position refers to.
    #  Either contest_measure is filled, contest_office OR candidate_campaign, but not all three
    contest_measure_id = models.BigIntegerField(verbose_name='id of contest_measure', null=True, blank=True)
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the contest_measure", max_length=255, null=True,
        blank=True, unique=False)

    # Strategic denormalization - this is redundant but will make generating the voter guide easier.
    # geo = models.ForeignKey(Geo, null=True, related_name='pos_geo')
    # issue = models.ForeignKey(Issue, null=True, blank=True, related_name='')

    stance = models.CharField(max_length=15, choices=POSITION_CHOICES, default=NO_STANCE)  # supporting/opposing

    statement_text = models.TextField(null=True, blank=True,)
    statement_html = models.TextField(null=True, blank=True,)
    # A link to any location with more information about this position
    more_info_url = models.URLField(blank=True, null=True, verbose_name='url with more info about this position')

    # Did this position come from a web scraper?
    from_scraper = models.BooleanField(default=False)
    # Was this position certified by an official with the organization?
    organization_certified = models.BooleanField(default=False)
    # Was this position certified by an official We Vote volunteer?
    volunteer_certified = models.BooleanField(default=False)

    # link = models.URLField(null=True, blank=True,)
    # link_title = models.TextField(null=True, blank=True, max_length=128)
    # link_site = models.TextField(null=True, blank=True, max_length=64)
    # link_txt = models.TextField(null=True, blank=True)
    # link_img = models.URLField(null=True, blank=True)
    # Set this to True after getting all the link details (title, txt, img etc)
    # details_loaded = models.BooleanField(default=False)
    # video_embed = models.URLField(null=True, blank=True)
    # spam_flag = models.BooleanField(default=False)
    # abuse_flag = models.BooleanField(default=False)
    # orig_json = models.TextField(blank=True)

    def __unicode__(self):
        return self.stance

    class Meta:
        ordering = ('date_entered',)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this organization came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_position_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "pos" = tells us this is a unique id for an pos
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}pos{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(PositionEntered, self).save(*args, **kwargs)

    def is_support(self):
        if self.stance == SUPPORT:
            return True
        return False

    def is_oppose(self):
        if self.stance == OPPOSE:
            return True
        return False

    def is_no_stance(self):
        if self.stance == NO_STANCE:
            return True
        return False

    def is_information_only(self):
        if self.stance == INFORMATION_ONLY:
            return True
        return False

    def is_still_deciding(self):
        if self.stance == STILL_DECIDING:
            return True
        return False

    def candidate_campaign(self):
        try:
            candidate_campaign = CandidateCampaign.objects.get(id=self.candidate_campaign_id)
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.candidate_campaign Found multiple")
            return
        except CandidateCampaign.DoesNotExist:
            logger.error("position.candidate_campaign did not find")
            return
        return candidate_campaign

    def election(self):
        try:
            election = Election.objects.get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.election Found multiple")
            return
        except Election.DoesNotExist:
            logger.error("position.election did not find")
            return
        return election

    def organization(self):
        try:
            organization = Organization.objects.get(id=self.organization_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("position.organization did not find")
            return
        return organization

    def fetch_organization_we_vote_id(self, organization_id=0):
        try:
            if positive_value_exists(organization_id):
                organization_on_stage = Organization.objects.get(id=organization_id)
            else:
                organization_on_stage = Organization.objects.get(id=self.organization_id)
            if organization_on_stage.we_vote_id:
                return organization_on_stage.we_vote_id
        except Organization.DoesNotExist:
            logger.error("position.organization fetch_organization_we_vote_id did not find we_vote_id")
            return
        return

    def fetch_organization_id_from_we_vote_id(self, organization_we_vote_id=''):
        try:
            if positive_value_exists(organization_we_vote_id):
                organization_on_stage = Organization.objects.get(we_vote_id=organization_we_vote_id)
            else:
                organization_on_stage = Organization.objects.get(we_vote_id=self.organization_we_vote_id)
            if organization_on_stage.id:
                return organization_on_stage.id
        except Organization.DoesNotExist:
            logger.error("position.organization fetch_organization_id_from_we_vote_id did not find id")
            return
        return

    def fetch_contest_office_we_vote_id(self, office_id=0):
        try:
            if positive_value_exists(office_id):
                contest_office_on_stage = ContestOffice.objects.get(id=office_id)
            else:
                contest_office_on_stage = ContestOffice.objects.get(id=self.contest_office_id)
            if contest_office_on_stage.we_vote_id:
                return contest_office_on_stage.we_vote_id
        except ContestOffice.DoesNotExist:
            logger.error("position.contest_office fetch_contest_office_we_vote_id did not find we_vote_id")
            pass
        return

    def fetch_contest_office_id_from_we_vote_id(self, office_we_vote_id=''):
        try:
            if positive_value_exists(office_we_vote_id):
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id=office_we_vote_id)
            else:
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id=self.contest_office_we_vote_id)
            if contest_office_on_stage.id:
                return contest_office_on_stage.id
        except ContestOffice.DoesNotExist:
            logger.error("position.contest_office fetch_contest_office_id_from_we_vote_id did not find id")
            pass
        return

    def fetch_candidate_campaign_we_vote_id(self, candidate_campaign_id=0):
        try:
            if positive_value_exists(candidate_campaign_id):
                candidate_campaign_on_stage = CandidateCampaign.objects.get(id=candidate_campaign_id)
            else:
                candidate_campaign_on_stage = CandidateCampaign.objects.get(id=self.candidate_campaign_id)
            if candidate_campaign_on_stage.we_vote_id:
                return candidate_campaign_on_stage.we_vote_id
        except CandidateCampaign.DoesNotExist:
            logger.error("position.candidate_campaign fetch_candidate_campaign_we_vote_id did not find we_vote_id")
            return
        return

    def fetch_candidate_campaign_id_from_we_vote_id(self, candidate_campaign_we_vote_id=''):
        try:
            if positive_value_exists(candidate_campaign_we_vote_id):
                candidate_campaign_on_stage = CandidateCampaign.objects.get(we_vote_id=candidate_campaign_we_vote_id)
            else:
                candidate_campaign_on_stage = \
                    CandidateCampaign.objects.get(we_vote_id=self.candidate_campaign_we_vote_id)
            if candidate_campaign_on_stage.id:
                return candidate_campaign_on_stage.id
        except CandidateCampaign.DoesNotExist:
            logger.error("position.candidate_campaign fetch_candidate_campaign_id_from_we_vote_id did not find id")
            return
        return

    def fetch_contest_measure_we_vote_id(self, contest_measure_id=0):
        try:
            if positive_value_exists(contest_measure_id):
                measure_campaign_on_stage = ContestMeasure.objects.get(id=contest_measure_id)
            else:
                measure_campaign_on_stage = ContestMeasure.objects.get(id=self.contest_measure_id)
            if measure_campaign_on_stage.we_vote_id:
                return measure_campaign_on_stage.we_vote_id
        except ContestMeasure.DoesNotExist:
            logger.error("position.measure_campaign fetch_contest_measure_we_vote_id did not find we_vote_id")
            pass
        return

    def fetch_contest_measure_id_from_we_vote_id(self, contest_measure_we_vote_id=''):
        try:
            if positive_value_exists(contest_measure_we_vote_id):
                contest_measure_on_stage = ContestMeasure.objects.get(we_vote_id=contest_measure_we_vote_id)
            else:
                contest_measure_on_stage = ContestMeasure.objects.get(we_vote_id=self.contest_measure_we_vote_id)
            if contest_measure_on_stage.id:
                return contest_measure_on_stage.id
        except ContestMeasure.DoesNotExist:
            logger.error("position.contest_measure fetch_contest_measure_id_from_we_vote_id did not find id")
            pass
        return


# NOTE: 2015-11 We are still using PositionEntered instead of Position
class Position(models.Model):
    """
    This is a table of data generated from PositionEntered. Not all fields copied over from PositionEntered
    """
    # We are relying on built-in Python id field

    # The PositionEntered entry that was copied into this entry based on verification rules
    position_entered_id = models.BigIntegerField(null=True, blank=True)

    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now=True)
    # The organization this position is for
    organization_id = models.BigIntegerField(null=True, blank=True)
    # The election this position is for
    # election_id = models.BigIntegerField(verbose_name='election id', null=True, blank=True)  # DEPRECATED
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=255, null=True, blank=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)

    candidate_campaign = models.ForeignKey(
        CandidateCampaign, verbose_name='candidate campaign', null=True, blank=True, related_name='position_candidate')

    # Useful for queries based on Politicians -- not the main table we use for ballot display though
    politician_id = models.BigIntegerField(verbose_name='', null=True, blank=True)
    # This is the measure/initiative/proposition that the position refers to.
    #  Either measure_campaign is filled OR candidate_campaign, but not both
    measure_campaign = models.ForeignKey(
        ContestMeasure, verbose_name='measure campaign', null=True, blank=True, related_name='position_measure')

    stance = models.CharField(max_length=15, choices=POSITION_CHOICES)  # supporting/opposing

    statement_text = models.TextField(null=True, blank=True,)
    statement_html = models.TextField(null=True, blank=True,)
    # A link to any location with more information about this position
    more_info_url = models.URLField(blank=True, null=True, verbose_name='url with more info about this position')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('date_entered',)

    # def display_ballot_item_name(self):
    #     """
    #     Organization supports 'ballot_item_name' (which could be a campaign name, or measure name
    #     :return:
    #     """
    #     # Try to retrieve the candidate_campaign
    #     if candidate_campaign.id:


class PositionListForCandidateCampaign(models.Model):
    """
    A way to retrieve all of the positions stated about this CandidateCampaign
    """
    # candidate_campaign = models.ForeignKey(
    #     CandidateCampaign, null=False, blank=False, verbose_name='candidate campaign')
    # position = models.ForeignKey(
    #     PositionEntered, null=False, blank=False, verbose_name='position about candidate')
    def retrieve_all_positions_for_candidate_campaign(self, candidate_campaign_id, stance_we_are_looking_for):
        # TODO Error check stance_we_are_looking_for

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY' which means we want to return
        #  all stances

        # Retrieve the support positions for this candidate_campaign_id
        organization_position_list = PositionEntered()
        organization_position_list_found = False
        try:
            organization_position_list = PositionEntered.objects.order_by('date_entered')
            organization_position_list = organization_position_list.filter(candidate_campaign_id=candidate_campaign_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE
            if stance_we_are_looking_for != ANY:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                organization_position_list = organization_position_list.filter(stance=stance_we_are_looking_for)
            # organization_position_list = organization_position_list.filter(election_id=election_id)
            if len(organization_position_list):
                organization_position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if organization_position_list_found:
            return organization_position_list
        else:
            organization_position_list = []
            return organization_position_list

    def calculate_positions_followed_by_voter(
            self, voter_id, all_positions_list_for_candidate_campaign, organizations_followed_by_voter):
        """
        We need a list of positions that were made by an organization that this voter follows
        :param all_positions_list_for_candidate_campaign:
        :param organizations_followed_by_voter:
        :return:
        """

        positions_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list_for_candidate_campaign:
            if position.voter_id == voter_id:  # We include the voter currently viewing the ballot in this list
                positions_followed_by_voter.append(position)
            # TODO Include a check against a list of "people_followed_by_voter" so we can include friends
            elif position.organization_id in organizations_followed_by_voter:
                logger.debug("position {position_id} followed by voter (org {org_id})".format(
                    position_id=position.id, org_id=position.organization_id
                ))
                positions_followed_by_voter.append(position)

        return positions_followed_by_voter

    def calculate_positions_not_followed_by_voter(
            self, all_positions_list_for_candidate_campaign, organizations_followed_by_voter):
        """
        We need a list of positions that were made by an organization that this voter follows
        :param all_positions_list_for_candidate_campaign:
        :param organizations_followed_by_voter:
        :return:
        """
        positions_not_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list_for_candidate_campaign:
            # Some positions are for individual voters, so we want to filter those out
            if position.organization_id \
                    and position.organization_id not in organizations_followed_by_voter:
                logger.debug("position {position_id} NOT followed by voter (org {org_id})".format(
                    position_id=position.id, org_id=position.organization_id
                ))
                positions_not_followed_by_voter.append(position)

        return positions_not_followed_by_voter


class PositionListForContestMeasure(models.Model):
    """
    A way to retrieve all of the positions stated about this ContestMeasure
    """
    def retrieve_all_positions_for_contest_measure(self, candidate_campaign_id, stance_we_are_looking_for):
        # TODO Error check stance_we_are_looking_for

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY' which means we want to return
        #  all stances

        # Retrieve the support positions for this candidate_campaign_id
        organization_position_list = PositionEntered()
        organization_position_list_found = False
        try:
            organization_position_list = PositionEntered.objects.order_by('date_entered')
            organization_position_list = organization_position_list.filter(candidate_campaign_id=candidate_campaign_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE
            if stance_we_are_looking_for != ANY:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                organization_position_list = organization_position_list.filter(stance=stance_we_are_looking_for)
            # organization_position_list = organization_position_list.filter(election_id=election_id)
            if len(organization_position_list):
                organization_position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if organization_position_list_found:
            return organization_position_list
        else:
            organization_position_list = []
            return organization_position_list

    def calculate_positions_followed_by_voter(
            self, voter_id, all_positions_list_for_candidate_campaign, organizations_followed_by_voter):
        """
        We need a list of positions that were made by an organization that this voter follows
        :param all_positions_list_for_candidate_campaign:
        :param organizations_followed_by_voter:
        :return:
        """

        positions_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list_for_candidate_campaign:
            if position.voter_id == voter_id:  # We include the voter currently viewing the ballot in this list
                positions_followed_by_voter.append(position)
            # TODO Include a check against a list of "people_followed_by_voter" so we can include friends
            elif position.organization_id in organizations_followed_by_voter:
                logger.debug("position {position_id} followed by voter (org {org_id})".format(
                    position_id=position.id, org_id=position.organization_id
                ))
                positions_followed_by_voter.append(position)

        return positions_followed_by_voter

    def calculate_positions_not_followed_by_voter(
            self, all_positions_list_for_candidate_campaign, organizations_followed_by_voter):
        """
        We need a list of positions that were made by an organization that this voter follows
        :param all_positions_list_for_candidate_campaign:
        :param organizations_followed_by_voter:
        :return:
        """
        positions_not_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list_for_candidate_campaign:
            # Some positions are for individual voters, so we want to filter those out
            if position.organization_id \
                    and position.organization_id not in organizations_followed_by_voter:
                logger.debug("position {position_id} NOT followed by voter (org {org_id})".format(
                    position_id=position.id, org_id=position.organization_id
                ))
                positions_not_followed_by_voter.append(position)

        return positions_not_followed_by_voter


class PositionEnteredManager(models.Model):

    def __unicode__(self):
        return "PositionEnteredManager"

    def retrieve_organization_candidate_campaign_position(self, organization_id, candidate_campaign_id):
        """
        Find a position based on the organization_id & candidate_campaign_id
        :param organization_id:
        :param candidate_campaign_id:
        :return:
        """
        position_id = 0
        position_we_vote_id = ''
        voter_id = 0
        contest_office_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_voter_contest_office_position(self, voter_id, contest_office_id):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_voter_contest_office_position_with_we_vote_id(self, voter_id, contest_office_we_vote_id):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        contest_office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        candidate_campaign_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_voter_candidate_campaign_position(self, voter_id, candidate_campaign_id):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        contest_office_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_voter_candidate_campaign_position_with_we_vote_id(self, voter_id, candidate_campaign_we_vote_id):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        contest_office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        contest_office_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_voter_contest_measure_position(self, voter_id, contest_measure_id):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        contest_office_id = 0
        candidate_campaign_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_voter_contest_measure_position_with_we_vote_id(self, voter_id, contest_measure_we_vote_id):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        contest_office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        contest_office_we_vote_id = ''
        candidate_campaign_we_vote_id = ''
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_position_from_id(self, position_id):
        position_we_vote_id = ''
        organization_id = 0
        voter_id = 0
        contest_office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_position_from_we_vote_id(self, position_we_vote_id):
        position_id = 0
        organization_id = 0
        voter_id = 0
        contest_office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_position(self, position_id, position_we_vote_id, organization_id, voter_id,
                          contest_office_id, candidate_campaign_id, contest_measure_id,
                          contest_office_we_vote_id='', candidate_campaign_we_vote_id='', contest_measure_we_vote_id=''):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        position_on_stage = PositionEntered()
        success = False

        try:
            if positive_value_exists(position_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_POSITION_ID"
                position_on_stage = PositionEntered.objects.get(id=position_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(position_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_WE_VOTE_ID"
                position_on_stage = PositionEntered.objects.get(we_vote_id=position_we_vote_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_office_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_OFFICE"
                position_on_stage = PositionEntered.objects.get(
                    organization_id=organization_id, contest_office_id=contest_office_id)
                # If still here, we found an existing position
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(organization_id) and positive_value_exists(candidate_campaign_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_CANDIDATE"
                position_on_stage = PositionEntered.objects.get(
                    organization_id=organization_id, candidate_campaign_id=candidate_campaign_id)
                # If still here, we found an existing position
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_measure_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_MEASURE"
                position_on_stage = PositionEntered.objects.get(
                    organization_id=organization_id, contest_measure_id=contest_measure_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_OFFICE"
                position_on_stage = PositionEntered.objects.get(
                    voter_id=voter_id, contest_office_id=contest_office_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_OFFICE_WE_VOTE_ID"
                position_on_stage = PositionEntered.objects.get(
                    voter_id=voter_id, contest_office_we_vote_id=contest_office_we_vote_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_CANDIDATE"
                position_on_stage = PositionEntered.objects.get(
                    voter_id=voter_id, candidate_campaign_id=candidate_campaign_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_CANDIDATE_WE_VOTE_ID"
                position_on_stage = PositionEntered.objects.get(
                    voter_id=voter_id, candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_MEASURE"
                position_on_stage = PositionEntered.objects.get(
                    voter_id=voter_id, contest_measure_id=contest_measure_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_MEASURE_WE_VOTE_ID"
                position_on_stage = PositionEntered.objects.get(
                    voter_id=voter_id, contest_measure_we_vote_id=contest_measure_we_vote_id)
                position_id = position_on_stage.id
                success = True
            else:
                status = "RETRIEVE_POSITION_INSUFFICIENT_VARIABLES"
        except PositionEntered.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status = "RETRIEVE_POSITION_MULTIPLE_FOUND"
        except PositionEntered.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status = "RETRIEVE_POSITION_NONE_FOUND"

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'position_found':           True if position_id > 0 else False,
            'position_id':              position_id,
            'position':                 position_on_stage,
            'is_support':               position_on_stage.is_support(),
            'is_oppose':                position_on_stage.is_oppose(),
            'is_no_stance':             position_on_stage.is_no_stance(),
            'is_information_only':      position_on_stage.is_information_only(),
            'is_still_deciding':        position_on_stage.is_still_deciding(),
        }
        return results

    def toggle_on_voter_support_for_candidate_campaign(self, voter_id, candidate_campaign_id):
        stance = SUPPORT
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance)

    def toggle_off_voter_support_for_candidate_campaign(self, voter_id, candidate_campaign_id):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance)

    def toggle_on_voter_oppose_for_candidate_campaign(self, voter_id, candidate_campaign_id):
        stance = OPPOSE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance)

    def toggle_off_voter_oppose_for_candidate_campaign(self, voter_id, candidate_campaign_id):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance)

    def toggle_on_voter_position_for_candidate_campaign(self, voter_id, candidate_campaign_id, stance):
        # Does a position from this voter already exist?
        position_entered_manager = PositionEnteredManager()
        results = position_entered_manager.retrieve_voter_candidate_campaign_position(voter_id, candidate_campaign_id)

        if results['MultipleObjectsReturned']:
            logger.warn("delete all but one and take it over?")
            status = 'MultipleObjectsReturned-WORK_NEEDED'
            voter_position_on_stage = PositionEntered
            results = {
                'status':       status,
                'success':      False,
                'position_id':  0,
                'position':     voter_position_on_stage,
            }
            return results

        voter_position_found = results['position_found']
        voter_position_on_stage = results['position']
        contest_measure_id = 0

        return position_entered_manager.toggle_voter_position(voter_id, voter_position_found, voter_position_on_stage,
                                                              stance, candidate_campaign_id, contest_measure_id)

    def toggle_voter_position(self, voter_id, voter_position_found, voter_position_on_stage, stance,
                              candidate_campaign_id, contest_measure_id):
        voter_position_on_stage_found = False
        position_id = 0
        if voter_position_found:
            # Update this position with new values
            try:
                voter_position_on_stage.stance = stance
                if voter_position_on_stage.candidate_campaign_id:
                    if not positive_value_exists(voter_position_on_stage.candidate_campaign_we_vote_id):
                        # Heal the data, and fill in the candidate_campaign_we_vote_id
                        voter_position_on_stage.candidate_campaign_we_vote_id = \
                            voter_position_on_stage.fetch_candidate_campaign_we_vote_id(
                                voter_position_on_stage.candidate_campaign_id)
                if voter_position_on_stage.contest_measure_id:
                    if not positive_value_exists(voter_position_on_stage.contest_measure_we_vote_id):
                        # Heal the data, and fill in the contest_measure_we_vote_id
                        voter_position_on_stage.contest_measure_we_vote_id = \
                            voter_position_on_stage.fetch_contest_measure_we_vote_id(
                                voter_position_on_stage.contest_measure_id)
                voter_position_on_stage.save()
                position_id = voter_position_on_stage.id
                voter_position_on_stage_found = True
                status = 'STANCE_UPDATED'
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                status = 'STANCE_COULD_NOT_BE_UPDATED'
        else:
            try:
                # Create new
                if candidate_campaign_id:
                    candidate_campaign_we_vote_id = \
                            voter_position_on_stage.fetch_candidate_campaign_we_vote_id(candidate_campaign_id)
                else:
                    candidate_campaign_we_vote_id = None

                if contest_measure_id:
                    contest_measure_we_vote_id = \
                            voter_position_on_stage.fetch_contest_measure_we_vote_id(contest_measure_id)
                else:
                    contest_measure_we_vote_id = None

                voter_position_on_stage = PositionEntered(
                    voter_id=voter_id,
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=contest_measure_we_vote_id,
                    stance=stance,
                    #  statement_text=statement_text,
                )
                voter_position_on_stage.save()
                position_id = voter_position_on_stage.id
                voter_position_on_stage_found = True
                status = 'NEW_STANCE_SAVED'
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                status = 'NEW_STANCE_COULD_NOT_BE_SAVED'

        results = {
            'status':       status,
            'success':      True if voter_position_on_stage_found else False,
            'position_id':  position_id,
            'position':     voter_position_on_stage,
        }
        return results

    def toggle_on_voter_support_for_contest_measure(self, voter_id, contest_measure_id):
        stance = SUPPORT
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance)

    def toggle_off_voter_support_for_contest_measure(self, voter_id, contest_measure_id):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance)

    def toggle_on_voter_oppose_for_contest_measure(self, voter_id, contest_measure_id):
        stance = OPPOSE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance)

    def toggle_off_voter_oppose_for_contest_measure(self, voter_id, contest_measure_id):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance)

    def toggle_on_voter_position_for_contest_measure(self, voter_id, contest_measure_id, stance):
        # Does a position from this voter already exist?
        position_entered_manager = PositionEnteredManager()
        results = position_entered_manager.retrieve_voter_contest_measure_position(voter_id, contest_measure_id)

        if results['MultipleObjectsReturned']:
            logger.warn("delete all but one and take it over?")
            status = 'MultipleObjectsReturned-WORK_NEEDED'
            voter_position_on_stage = PositionEntered
            results = {
                'status':       status,
                'success':      False,
                'position_id':  0,
                'position':     voter_position_on_stage,
            }
            return results

        voter_position_found = results['position_found']
        voter_position_on_stage = results['position']
        candidate_campaign_id = 0

        return position_entered_manager.toggle_voter_position(voter_id, voter_position_found, voter_position_on_stage,
                                                              stance, candidate_campaign_id, contest_measure_id)

    # We rely on these unique identifiers:
    #   position_id, position_we_vote_id
    # Pass in a value if we want it saved. Pass in "False" if we want to leave it the same.
    def update_or_create_position(
            self, position_id, position_we_vote_id,
            organization_we_vote_id=False,
            public_figure_we_vote_id=False,
            voter_we_vote_id=False,
            google_civic_election_id=False,
            ballot_item_label=False,
            office_we_vote_id=False,
            candidate_we_vote_id=False,
            measure_we_vote_id=False,
            stance=False,
            statement_text=False,
            statement_html=False,
            more_info_url=False):
        """
        Either update or create a position entry.
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        failed_saving_existing_position = False
        position_on_stage_found = False
        new_position_created = False
        too_many_unique_actor_variables_received = False
        no_unique_actor_variables_received = False
        too_many_unique_ballot_item_variables_received = False
        no_unique_ballot_item_variables_received = False
        position_on_stage = PositionEntered()
        status = "ENTERING_UPDATE_OR_CREATE_POSITION"

        # In order of authority
        # 1) position_id exists? Find it with position_id or fail
        # 2) we_vote_id exists? Find it with we_vote_id or fail
        # 3-5) organization_we_vote_id related position?
        # 6-8) public_figure_we_vote_id related position?
        # 9-11) voter_we_vote_id related position?

        success = False
        if positive_value_exists(position_id) or positive_value_exists(position_we_vote_id):
            # If here, we know we are updating
            # 1) position_id exists? Find it with position_id or fail
            # 2) we_vote_id exists? Find it with we_vote_id or fail
            position_entered_manager = PositionEnteredManager()
            position_results = {
                'success': False,
            }
            found_with_id = False
            found_with_we_vote_id = False
            if positive_value_exists(position_id):
                position_results = position_entered_manager.retrieve_position_from_id(position_id)
                found_with_id = True
            elif positive_value_exists(position_we_vote_id):
                position_results = position_entered_manager.retrieve_position_from_we_vote_id(position_we_vote_id)
                found_with_we_vote_id = True

            if position_results['success']:
                position_on_stage = position_results['position']
                position_on_stage_found = True

                if organization_we_vote_id:
                    position_on_stage.organization_we_vote_id = organization_we_vote_id
                    # Lookup organization_id based on organization_we_vote_id and update
                    position_on_stage.organization_id = \
                        position_on_stage.fetch_organization_id_from_we_vote_id(organization_we_vote_id)
                if google_civic_election_id:
                    position_on_stage.google_civic_election_id = google_civic_election_id
                if ballot_item_label:
                    position_on_stage.ballot_item_label = ballot_item_label
                if office_we_vote_id:
                    position_on_stage.contest_office_we_vote_id = office_we_vote_id
                    # Lookup contest_office_id based on office_we_vote_id and update
                    position_on_stage.contest_office_id = \
                        position_on_stage.fetch_contest_office_id_from_we_vote_id(office_we_vote_id)
                if candidate_we_vote_id:
                    position_on_stage.candidate_campaign_we_vote_id = candidate_we_vote_id
                    # Lookup candidate_campaign_id based on candidate_campaign_we_vote_id and update
                    position_on_stage.candidate_campaign_id = \
                        position_on_stage.fetch_candidate_campaign_id_from_we_vote_id(candidate_we_vote_id)
                if measure_we_vote_id:
                    position_on_stage.contest_measure_we_vote_id = measure_we_vote_id
                    # Lookup contest_measure_id based on contest_measure_we_vote_id and update
                    position_on_stage.contest_measure_id = \
                        position_on_stage.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)
                # if positive_value_exists(stance):
                if stance:
                    # TODO Verify stance is a legal value
                    position_on_stage.stance = stance
                if statement_text:
                    position_on_stage.statement_text = statement_text
                if statement_html:
                    position_on_stage.statement_html = statement_html
                if more_info_url:
                    position_on_stage.more_info_url = more_info_url

                # As long as at least one of the above variables has changed, then save
                if organization_we_vote_id or google_civic_election_id or ballot_item_label or office_we_vote_id \
                        or candidate_we_vote_id or measure_we_vote_id or stance or statement_text \
                        or statement_html or more_info_url:
                    position_on_stage.save()
                    success = True
                    if found_with_id:
                        status = "POSITION_SAVED_WITH_POSITION_ID"
                    elif found_with_we_vote_id:
                        status = "POSITION_SAVED_WITH_POSITION_WE_VOTE_ID"
                    else:
                        status = "POSITION_CHANGES_SAVED"
                else:
                    success = True
                    if found_with_id:
                        status = "NO_POSITION_CHANGES_SAVED_WITH_POSITION_ID"
                    elif found_with_we_vote_id:
                        status = "NO_POSITION_CHANGES_SAVED_WITH_POSITION_WE_VOTE_ID"
                    else:
                        status = "NO_POSITION_CHANGES_SAVED"
            else:
                status = "POSITION_COULD_NOT_BE_FOUND_WITH_POSITION_ID_OR_WE_VOTE_ID"
        # else for this: if positive_value_exists(position_id) or positive_value_exists(position_we_vote_id):
        else:
            # We also want to retrieve a position with the following sets of variables:
            # 3) organization_we_vote_id, google_civic_election_id, candidate_we_vote_id: DONE
            # 4) organization_we_vote_id, google_civic_election_id, measure_we_vote_id: DONE
            # 5) organization_we_vote_id, google_civic_election_id, office_we_vote_id: DONE
            # 6) TODO public_figure_we_vote_id, google_civic_election_id, office_we_vote_id
            # 7) TODO public_figure_we_vote_id, google_civic_election_id, candidate_we_vote_id
            # 8) TODO public_figure_we_vote_id, google_civic_election_id, measure_we_vote_id
            # NOTE: Voters storing a public version of their voter guides store it as a public_figure_we_vote_id
            # 9) voter_we_vote_id, google_civic_election_id, office_we_vote_id
            # 10) voter_we_vote_id, google_civic_election_id, candidate_we_vote_id
            # 11) voter_we_vote_id, google_civic_election_id, measure_we_vote_id
            found_with_status = ''

            # Make sure that too many ballot item identifier variables weren't passed in
            number_of_unique_ballot_item_identifiers = 0
            if positive_value_exists(candidate_we_vote_id):
                number_of_unique_ballot_item_identifiers += 1
            if positive_value_exists(measure_we_vote_id):
                number_of_unique_ballot_item_identifiers += 1
            if positive_value_exists(office_we_vote_id):
                number_of_unique_ballot_item_identifiers += 1

            if number_of_unique_ballot_item_identifiers > 1:
                too_many_unique_ballot_item_variables_received = True
                status = "FAILED-TOO_MANY_UNIQUE_BALLOT_ITEM_VARIABLES"
                success = False
            elif number_of_unique_ballot_item_identifiers is 0:
                no_unique_ballot_item_variables_received = True
                status = "FAILED-NO_UNIQUE_BALLOT_ITEM_VARIABLES_RECEIVED"
                success = False

            # Make sure that too many "actor" identifier variables weren't passed in
            number_of_unique_actor_identifiers = 0
            if positive_value_exists(organization_we_vote_id):
                number_of_unique_actor_identifiers += 1
            if positive_value_exists(public_figure_we_vote_id):
                number_of_unique_actor_identifiers += 1
            if positive_value_exists(voter_we_vote_id):
                number_of_unique_actor_identifiers += 1

            if number_of_unique_actor_identifiers > 1:
                too_many_unique_actor_variables_received = True
                status = "FAILED-TOO_MANY_UNIQUE_ACTOR_VARIABLES"
                success = False
            elif number_of_unique_actor_identifiers is 0:
                no_unique_actor_variables_received = True
                status = "FAILED-NO_UNIQUE_ACTOR_VARIABLES_RECEIVED"
                success = False

            # Only proceed if the correct number of unique identifiers was received
            if not too_many_unique_ballot_item_variables_received and \
                    not too_many_unique_actor_variables_received and \
                    not no_unique_actor_variables_received and \
                    not no_unique_ballot_item_variables_received:
                # 3-5: Organization-related cases
                # 3) candidate_we_vote_id + organization_we_vote_id exists? Try to find it. If not, go to step 4
                if positive_value_exists(candidate_we_vote_id) and \
                        positive_value_exists(organization_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            candidate_campaign_we_vote_id=candidate_we_vote_id,
                            organization_we_vote_id=organization_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 4) measure_we_vote_id + organization_we_vote_id exists? Try to find it. If not, go to step 5
                if positive_value_exists(measure_we_vote_id) and \
                        positive_value_exists(organization_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            contest_measure_we_vote_id=measure_we_vote_id,
                            organization_we_vote_id=organization_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_MEASURE_AND_ORGANIZATION_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_MEASURE_AND_ORGANIZATION_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 5) office_we_vote_id + organization_we_vote_id exists? Try to find it. If not, go to step 6
                if positive_value_exists(office_we_vote_id) and \
                        positive_value_exists(organization_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            contest_office_we_vote_id=office_we_vote_id,
                            organization_we_vote_id=organization_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_OFFICE_AND_ORGANIZATION_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_OFFICE_AND_ORGANIZATION_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this office_we_vote_id wasn't found
                        pass

                # TODO Test public_figure (6-8) and voter (9-11) related cases
                # 6-8: Public-Figure-related cases
                # 6) candidate_we_vote_id + public_figure_we_vote_id exists? Try to find it. If not, go to step 7
                if positive_value_exists(candidate_we_vote_id) and \
                        positive_value_exists(public_figure_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            candidate_campaign_we_vote_id=candidate_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_CANDIDATE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 7) measure_we_vote_id + public_figure_we_vote_id exists? Try to find it. If not, go to step 8
                if positive_value_exists(measure_we_vote_id) and \
                        positive_value_exists(public_figure_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            contest_measure_we_vote_id=measure_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_MEASURE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_MEASURE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 8) office_we_vote_id + public_figure_we_vote_id exists? Try to find it. If not, go to step 9
                if positive_value_exists(office_we_vote_id) and \
                        positive_value_exists(public_figure_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            contest_office_we_vote_id=office_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this office_we_vote_id wasn't found
                        pass

                # 9-11: Voter-related cases
                # 9) candidate_we_vote_id + organization_we_vote_id exists? Try to find it. If not, go to step 10
                if positive_value_exists(candidate_we_vote_id) and \
                        positive_value_exists(voter_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            candidate_campaign_we_vote_id=candidate_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_CANDIDATE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 10) measure_we_vote_id + voter_we_vote_id exists? Try to find it. If not, go to step 11
                if positive_value_exists(measure_we_vote_id) and \
                        positive_value_exists(voter_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            contest_measure_we_vote_id=measure_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_MEASURE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_MEASURE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 11) office_we_vote_id + organization_we_vote_id exists? Try to find it.
                if positive_value_exists(office_we_vote_id) and \
                        positive_value_exists(voter_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = PositionEntered.objects.get(
                            contest_office_we_vote_id=office_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except PositionEntered.DoesNotExist as e:
                        # Not a problem -- a position matching this office wasn't found
                        pass

                # Save values entered in steps 3-11
                if position_on_stage_found:
                    try:
                        if ballot_item_label or stance or statement_text or statement_html or more_info_url:
                            if ballot_item_label:
                                position_on_stage.ballot_item_label = ballot_item_label
                            if stance:
                                position_on_stage.stance = stance
                            if statement_text:
                                position_on_stage.statement_text = statement_text
                            if statement_html:
                                position_on_stage.statement_html = statement_html
                            if more_info_url:
                                position_on_stage.more_info_url = more_info_url

                            position_on_stage.save()
                            success = True
                            status = found_with_status + " SAVED"
                        else:
                            success = True
                            status = found_with_status + " NO_CHANGES_SAVED"
                    except Exception as e:
                        handle_record_not_saved_exception(e, logger=logger)
                        failed_saving_existing_position = True

        if not position_on_stage_found \
                and not exception_multiple_object_returned \
                and not failed_saving_existing_position \
                and not too_many_unique_ballot_item_variables_received and not too_many_unique_actor_variables_received:
            try:
                # If here, create new position
                # Some functions pass in these values with "False" if we don't want to update the value. Because of
                # this we want to change the value away from "False" when we create a new entry.
                if organization_we_vote_id:
                    organization_id = \
                        position_on_stage.fetch_organization_id_from_we_vote_id(organization_we_vote_id)
                else:
                    # We don't need to ever look up the organization_we_vote_id from the organization_id
                    organization_id = 0
                    organization_we_vote_id = None

                if voter_we_vote_id:
                    voter_manager = VoterManager()
                    voter_id = \
                        voter_manager.fetch_local_id_from_we_vote_id(voter_we_vote_id)
                else:
                    # We don't need to ever look up the voter_we_vote_id from the voter_id
                    voter_id = 0
                    voter_we_vote_id = None

                if google_civic_election_id is False:
                    google_civic_election_id = None

                if ballot_item_label is False:
                    ballot_item_label = None

                if office_we_vote_id:
                    contest_office_id = \
                        position_on_stage.fetch_contest_office_id_from_we_vote_id(office_we_vote_id)
                else:
                    # We don't need to ever look up the office_we_vote_id from the contest_office_id
                    contest_office_id = 0
                    office_we_vote_id = None

                if candidate_we_vote_id:
                    candidate_campaign_id = \
                        position_on_stage.fetch_candidate_campaign_id_from_we_vote_id(candidate_we_vote_id)
                else:
                    # We don't need to ever look up the candidate_we_vote_id from the candidate_campaign_id
                    candidate_campaign_id = 0
                    candidate_we_vote_id = None

                if measure_we_vote_id:
                    contest_measure_id = \
                        position_on_stage.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)
                else:
                    # We don't need to ever look up the measure_we_vote_id from the contest_measure_id
                    contest_measure_id = 0
                    measure_we_vote_id = None

                if stance not in(SUPPORT, NO_STANCE, INFORMATION_ONLY, STILL_DECIDING, OPPOSE):
                    stance = NO_STANCE

                if statement_text is False:
                    statement_text = None

                if statement_html is False:
                    statement_html = None

                if more_info_url is False:
                    more_info_url = None

                position_on_stage = PositionEntered.objects.create(
                    organization_we_vote_id=organization_we_vote_id,
                    organization_id=organization_id,
                    voter_we_vote_id=voter_we_vote_id,
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    ballot_item_label=ballot_item_label,
                    contest_office_we_vote_id=office_we_vote_id,
                    contest_office_id=contest_office_id,
                    candidate_campaign_we_vote_id=candidate_we_vote_id,
                    candidate_campaign_id=candidate_campaign_id,
                    contest_measure_we_vote_id=measure_we_vote_id,
                    contest_measure_id=contest_measure_id,
                    stance=stance,
                    statement_text=statement_text,
                    statement_html=statement_html,
                    more_info_url=more_info_url
                )
                status = "CREATE_POSITION_SUCCESSFUL"
                success = True

                new_position_created = True
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                success = False
                status = "NEW_POSITION_COULD_NOT_BE_CREATED"
                position_on_stage = PositionEntered

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'position':                 position_on_stage,
            'new_position_created':     new_position_created,
        }
        return results

    def delete_position(self, position_id):
        position_id = convert_to_int(position_id)
        position_deleted = False

        try:
            if position_id:
                results = self.retrieve_position(position_id)  # TODO This is not correct -- doesn't include all vars
                if results['position_found']:
                    position = results['position']
                    position_id = position.id
                    position.delete()
                    position_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':              position_deleted,
            'position_deleted': position_deleted,
            'position_id':      position_id,
        }
        return results


class PositionList(models.Model):
    """
    A way to retrieve lists of positions
    """
    def retrieve_all_positions_for_contest_measure(self, candidate_campaign_id, stance_we_are_looking_for):
        # TODO Error check stance_we_are_looking_for

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY' which means we want to return
        #  all stances

        # Retrieve the support positions for this candidate_campaign_id
        position_list = PositionEntered()
        position_list_found = False
        try:
            position_list = PositionEntered.objects.order_by('date_entered')
            position_list = position_list.filter(candidate_campaign_id=candidate_campaign_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE
            if stance_we_are_looking_for != ANY:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                position_list = position_list.filter(stance=stance_we_are_looking_for)
            # position_list = position_list.filter(election_id=election_id)
            if len(position_list):
                position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if position_list_found:
            return position_list
        else:
            position_list = []
            return position_list
