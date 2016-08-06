# position/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
# Diagrams here: https://docs.google.com/drawings/d/1DsPnl97GKe9f14h41RPeZDssDUztRETGkXGaolXCeyo/edit

from candidate.models import CandidateCampaign, CandidateCampaignManager, CandidateCampaignListManager
from ballot.controllers import figure_out_google_civic_election_id_voter_is_watching
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.db.models import Q
from election.models import Election
from exception.models import handle_exception, handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from measure.models import ContestMeasure, ContestMeasureList
from office.models import ContestOffice
from organization.models import Organization, OrganizationManager
from twitter.models import TwitterUser
from voter.models import Voter, VoterAddress, VoterAddressManager, VoterDeviceLinkManager, VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_position_integer, fetch_site_unique_id_prefix


ANY_STANCE = 'ANY_STANCE'  # This is a way to indicate when we want to return any stance (support, oppose, no_stance)
SUPPORT = 'SUPPORT'
STILL_DECIDING = 'STILL_DECIDING'
NO_STANCE = 'NO_STANCE'
INFORMATION_ONLY = 'INFO_ONLY'
OPPOSE = 'OPPOSE'
PERCENT_RATING = 'PERCENT_RATING'
POSITION_CHOICES = (
    # ('SUPPORT_STRONG',    'Strong Supports'),  # I do not believe we will be offering 'SUPPORT_STRONG' as an option
    (SUPPORT,           'Supports'),
    (STILL_DECIDING,    'Still deciding'),  # Still undecided
    (NO_STANCE,         'No stance'),  # We don't know the stance
    (INFORMATION_ONLY,  'Information only'),  # This entry is meant as food-for-thought and is not advocating
    (OPPOSE,            'Opposes'),
    (PERCENT_RATING,    'Percentage point rating'),
    # ('OPPOSE_STRONG',     'Strongly Opposes'),  # I do not believe we will be offering 'OPPOSE_STRONG' as an option
)
# friends_vs_public
FRIENDS_AND_PUBLIC = 'FRIENDS_AND_PUBLIC'
PUBLIC_ONLY = 'PUBLIC_ONLY'
FRIENDS_ONLY = 'FRIENDS_ONLY'

logger = wevote_functions.admin.get_logger(__name__)


# TODO DALE Consider adding vote_smart_sig_id and vote_smart_candidate_id fields so we can export them and to prevent
# duplicate position entries from Vote Smart

class PositionEntered(models.Model):
    """
    Any public position entered by any organization or candidate gets its own PositionEntered entry.
    NOTE: We also have PositionForFriends table that is exactly the same structure as PositionEntered. It holds
    opinions that voters only want to share with friends.
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
    ballot_item_display_name = models.CharField(verbose_name="text name for ballot item",
                                                max_length=255, null=True, blank=True)
    # We cache the url to an image for the candidate, measure or office for rapid display
    ballot_item_image_url_https = models.URLField(verbose_name='url of https image for candidate, measure or office',
                                                  blank=True, null=True)
    ballot_item_twitter_handle = models.CharField(verbose_name='twitter screen_name for candidate, measure, or office',
                                                  max_length=255, null=True, unique=False)

    # What is the organization name, voter name, or public figure name? We cache this here for rapid display
    speaker_display_name = models.CharField(
        verbose_name="name of the org or person with position", max_length=255, null=True, blank=True, unique=False)
    # We cache the url to an image for the org, voter, or public_figure for rapid display
    speaker_image_url_https = models.URLField(verbose_name='url of https image for org or person with position',
                                              blank=True, null=True)
    speaker_twitter_handle = models.CharField(verbose_name='twitter screen_name for org or person with position',
                                              max_length=255, null=True, unique=False)

    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now=True)
    # The date the this position last changed
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # The organization this position is for
    organization_id = models.BigIntegerField(null=True, blank=True)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the organization", max_length=255, null=True,
        blank=True, unique=False)

    # The voter expressing the opinion
    # Note that for organizations who have friends, the voter_we_vote_id is what we use to link to the friends
    # (in the PositionForFriends table).
    # Public positions from an organization are shared via organization_we_vote_id (in PositionEntered table), while
    # friend's-only  positions are shared via voter_we_vote_id.
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
                                                max_length=255, null=True, blank=False, default=0)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="us state of the ballot item position is for", max_length=2, null=True, blank=True)
    # ### Values from Vote Smart ###
    vote_smart_rating_id = models.BigIntegerField(null=True, blank=True, unique=False)
    # Usually in one of these two formats 2015, 2014-2015
    vote_smart_time_span = models.CharField(
        verbose_name="the period in which the organization stated this position", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating = models.CharField(
        verbose_name="vote smart value between 0-100", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating_name = models.CharField(max_length=255, null=True, blank=True, unique=False)

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
            self.we_vote_id = self.we_vote_id.strip().lower()
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

    # Is the position is an actual endorsement?
    def is_support(self):
        if self.stance == SUPPORT:
            return True
        return False

    # Is the position a rating that is 66% or greater?
    def is_positive_rating(self):
        if self.stance == PERCENT_RATING:
            rating_percentage = convert_to_int(self.vote_smart_rating)
            if rating_percentage >= 66:
                return True
        return False

    # Is the position is an actual endorsement or a rating that is 66% or greater?
    def is_support_or_positive_rating(self):
        if self.is_support():
            return True
        elif self.is_positive_rating():
            return True
        return False

    # Is the position an anti-endorsement?
    def is_oppose(self):
        if self.stance == OPPOSE:
            return True
        return False

    # Is the position a rating that is 33% or less?
    def is_negative_rating(self):
        if self.stance == PERCENT_RATING:
            rating_percentage = convert_to_int(self.vote_smart_rating)
            if rating_percentage <= 33:
                return True
        return False

    # Is the position is an actual endorsement or a rating that is 66% or greater?
    def is_oppose_or_negative_rating(self):
        if self.is_oppose():
            return True
        elif self.is_negative_rating():
            return True
        return False

    def is_no_stance(self):
        if self.stance == NO_STANCE:
            return True
        elif self.stance == PERCENT_RATING:
            rating_percentage = convert_to_int(self.vote_smart_rating)
            if (rating_percentage > 33) and (rating_percentage < 66):
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

    def last_updated(self):
        if positive_value_exists(self.date_last_changed):
            return str(self.date_last_changed)
        elif positive_value_exists(self.date_entered):
            return str(self.date_entered)
        return ''

    def candidate_campaign(self):
        if not self.candidate_campaign_id:
            return
        try:
            candidate_campaign = CandidateCampaign.objects.get(id=self.candidate_campaign_id)
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.candidate_campaign Found multiple")
            return
        except CandidateCampaign.DoesNotExist:
            return
        return candidate_campaign

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            election = Election.objects.get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.election Found multiple")
            return
        except Election.DoesNotExist:
            return
        return election

    def organization(self):
        if not self.organization_id:
            return
        try:
            organization = Organization.objects.get(id=self.organization_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.organization Found multiple")
            return
        except Organization.DoesNotExist:
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


class PositionForFriends(models.Model):
    """
    Any position intended for friends only that is entered by any organization or candidate gets its own
    PositionForFriends entry.
    NOTE: We also have PositionEntered table that is exactly the same structure as PositionForFriends. It holds
    opinions that voters only want to share with friends.
    """
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our org info with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "pos", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_position_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)

    # The id for the generated position that this PositionForFriends entry influences
    position_id = models.BigIntegerField(null=True, blank=True)  # NOT USED CURRENTLY
    test = models.BigIntegerField(null=True, blank=True)
    ballot_item_display_name = models.CharField(verbose_name="text name for ballot item",
                                                max_length=255, null=True, blank=True)
    # We cache the url to an image for the candidate, measure or office for rapid display
    ballot_item_image_url_https = models.URLField(
        verbose_name='url of https image for candidate, measure or office',
        blank=True, null=True)
    ballot_item_twitter_handle = models.CharField(
        verbose_name='twitter screen_name for candidate, measure, or office',
        max_length=255, null=True, unique=False)

    # What is the organization name, voter name, or public figure name? We cache this here for rapid display
    speaker_display_name = models.CharField(
        verbose_name="name of the org or person with position", max_length=255, null=True, blank=True, unique=False)
    # We cache the url to an image for the org, voter, or public_figure for rapid display
    speaker_image_url_https = models.URLField(verbose_name='url of https image for org or person with position',
                                              blank=True, null=True)
    speaker_twitter_handle = models.CharField(verbose_name='twitter screen_name for org or person with position',
                                              max_length=255, null=True, unique=False)

    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now=True)
    # The date the this position last changed
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # The organization this position is for
    organization_id = models.BigIntegerField(null=True, blank=True)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the organization", max_length=255, null=True,
        blank=True, unique=False)

    # The voter expressing the opinion
    # Note that for organizations who have friends, the voter_we_vote_id is what we use to link to the friends.
    # Public positions from an organization are shared via organization_we_vote_id (in PositionEntered table), while
    # friend's-only  positions are shared via voter_we_vote_id.
    voter_id = models.BigIntegerField(null=True, blank=True)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the voter expressing the opinion", max_length=255, null=True,
        blank=True, unique=False)

    # The unique id of the public figure expressing the opinion. May be null if position is from org or voter
    # instead of public figure.
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="us state of the ballot item position is for", max_length=2,
                                  null=True, blank=True)
    # ### Values from Vote Smart ###
    vote_smart_rating_id = models.BigIntegerField(null=True, blank=True, unique=False)
    # Usually in one of these two formats 2015, 2014-2015
    vote_smart_time_span = models.CharField(
        verbose_name="the period in which the organization stated this position", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating = models.CharField(
        verbose_name="vote smart value between 0-100", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating_name = models.CharField(max_length=255, null=True, blank=True, unique=False)

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
        verbose_name="we vote permanent id for the contest_office", max_length=255, null=True, blank=True,
        unique=False)

    # This is the candidate/politician that the position refers to.
    #  Either candidate_campaign is filled, contest_office OR contest_measure, but not all three
    candidate_campaign_id = models.BigIntegerField(verbose_name='id of candidate_campaign', null=True, blank=True)
    candidate_campaign_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the candidate_campaign", max_length=255, null=True,
        blank=True, unique=False)
    # The candidate's name as passed over by Google Civic. We save this so we can match to this candidate if an import
    # doesn't include a we_vote_id we recognize.
    google_civic_candidate_name = models.CharField(
        verbose_name="candidate name exactly as received from google civic",
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

    statement_text = models.TextField(null=True, blank=True, )
    statement_html = models.TextField(null=True, blank=True, )
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
            self.we_vote_id = self.we_vote_id.strip().lower()
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
        super(PositionForFriends, self).save(*args, **kwargs)

    # Is the position is an actual endorsement?
    def is_support(self):
        if self.stance == SUPPORT:
            return True
        return False

    # Is the position a rating that is 66% or greater?
    def is_positive_rating(self):
        if self.stance == PERCENT_RATING:
            rating_percentage = convert_to_int(self.vote_smart_rating)
            if rating_percentage >= 66:
                return True
        return False

    # Is the position is an actual endorsement or a rating that is 66% or greater?
    def is_support_or_positive_rating(self):
        if self.is_support():
            return True
        elif self.is_positive_rating():
            return True
        return False

    # Is the position an anti-endorsement?
    def is_oppose(self):
        if self.stance == OPPOSE:
            return True
        return False

    # Is the position a rating that is 33% or less?
    def is_negative_rating(self):
        if self.stance == PERCENT_RATING:
            rating_percentage = convert_to_int(self.vote_smart_rating)
            if rating_percentage <= 33:
                return True
        return False

    # Is the position is an actual endorsement or a rating that is 66% or greater?
    def is_oppose_or_negative_rating(self):
        if self.is_oppose():
            return True
        elif self.is_negative_rating():
            return True
        return False

    def is_no_stance(self):
        if self.stance == NO_STANCE:
            return True
        elif self.stance == PERCENT_RATING:
            rating_percentage = convert_to_int(self.vote_smart_rating)
            if (rating_percentage > 33) and (rating_percentage < 66):
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

    def last_updated(self):
        if positive_value_exists(self.date_last_changed):
            return str(self.date_last_changed)
        elif positive_value_exists(self.date_entered):
            return str(self.date_entered)
        return ''

    def candidate_campaign(self):
        if not self.candidate_campaign_id:
            return
        try:
            candidate_campaign = CandidateCampaign.objects.get(id=self.candidate_campaign_id)
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.candidate_campaign Found multiple")
            return
        except CandidateCampaign.DoesNotExist:
            return
        return candidate_campaign

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            election = Election.objects.get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.election Found multiple")
            return
        except Election.DoesNotExist:
            return
        return election

    def organization(self):
        if not self.organization_id:
            return
        try:
            organization = Organization.objects.get(id=self.organization_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.organization Found multiple")
            return
        except Organization.DoesNotExist:
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
                candidate_campaign_on_stage = CandidateCampaign.objects.get(
                    we_vote_id=candidate_campaign_we_vote_id)
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


# NOTE: 2015-11 We are still using PositionEntered and PositionForFriends instead of Position
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


class PositionListManager(models.Model):

    def calculate_positions_followed_by_voter(
            self, voter_id, all_positions_list, organizations_followed_by_voter):
        """
        We need a list of positions that were made by an organization, public figure or friend that this voter follows
        :param voter_id:
        :param all_positions_list:
        :param organizations_followed_by_voter:
        :return:
        """

        positions_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list:
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
            self, all_positions_list, organizations_followed_by_voter):
        """
        We need a list of positions that were NOT made by an organization, public figure or friend
        that this voter follows
        :param all_positions_list:
        :param organizations_followed_by_voter:
        :return:
        """
        positions_not_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list:
            # Some positions are for individual voters, so we want to filter those out
            if position.organization_id \
                    and position.organization_id not in organizations_followed_by_voter:
                logger.debug("position {position_id} NOT followed by voter (org {org_id})".format(
                    position_id=position.id, org_id=position.organization_id
                ))
                positions_not_followed_by_voter.append(position)

        return positions_not_followed_by_voter

    def remove_positions_ignored_by_voter(
            self, positions_list, organizations_ignored_by_voter):
        """
        We need a list of positions that were NOT made by an organization, public figure or friend
        that this voter follows
        :param positions_list:
        :param organizations_ignored_by_voter:
        :return:
        """
        positions_ignored_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in positions_list:
            # Some positions are for individual voters, so we want to filter those out
            if position.organization_id \
                    and position.organization_id not in organizations_ignored_by_voter:
                logger.debug("position {position_id} ignored by voter (org {org_id})".format(
                    position_id=position.id, org_id=position.organization_id
                ))
                positions_ignored_by_voter.append(position)

        return positions_ignored_by_voter

    def retrieve_all_positions_for_candidate_campaign(self, retrieve_public_positions,
                                                      candidate_campaign_id, candidate_campaign_we_vote_id='',
                                                      stance_we_are_looking_for=ANY_STANCE, most_recent_only=True,
                                                      friends_we_vote_id_list=False):
        """
        We do not attempt to retrieve public positions and friend's-only positions in the same call.
        :param retrieve_public_positions:
        :param candidate_campaign_id:
        :param candidate_campaign_we_vote_id:
        :param stance_we_are_looking_for:
        :param most_recent_only:
        :param friends_we_vote_id_list: If this comes in as a list, use that list. If it comes in as False,
         we can consider looking up the values if they are needed, but we will then need voter_device_id passed in too.
        :return:
        """
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            position_list = []
            return position_list

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(candidate_campaign_id) and not \
                positive_value_exists(candidate_campaign_we_vote_id):
            position_list = []
            return position_list

        # Retrieve the support positions for this candidate_campaign_id
        position_list = []
        position_list_found = False
        try:
            if retrieve_public_positions:
                position_list = PositionEntered.objects.order_by('date_entered')
                retrieve_friends_positions = False
            else:
                position_list = PositionForFriends.objects.order_by('date_entered')
                retrieve_friends_positions = True

            if positive_value_exists(candidate_campaign_id):
                position_list = position_list.filter(candidate_campaign_id=candidate_campaign_id)
            else:
                position_list = position_list.filter(candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                    position_list = position_list.filter(
                        Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                else:
                    position_list = position_list.filter(stance=stance_we_are_looking_for)
            if retrieve_friends_positions and friends_we_vote_id_list is not False:
                # Find positions from friends. Look for we_vote_id case insensitive.
                we_vote_id_filter = Q()
                for we_vote_id in friends_we_vote_id_list:
                    we_vote_id_filter |= Q(voter_we_vote_id__iexact=we_vote_id)
                position_list = position_list.filter(we_vote_id_filter)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)

            # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
            if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                revised_position_list = []
                for one_position in position_list:
                    if stance_we_are_looking_for == SUPPORT:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_positive_rating():  # This was "is_support"
                                revised_position_list.append(one_position)
                        else:
                            revised_position_list.append(one_position)
                    elif stance_we_are_looking_for == OPPOSE:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_negative_rating():  # This was "is_oppose"
                                revised_position_list.append(one_position)
                        else:
                            revised_position_list.append(one_position)
                position_list = revised_position_list

            if len(position_list):
                position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        # If we have multiple positions for one org, we only want to show the most recent.
        if most_recent_only:
            if position_list_found:
                position_list_filtered = self.remove_older_positions_for_each_org(position_list)
            else:
                position_list_filtered = []
        else:
            position_list_filtered = position_list

        if position_list_found:
            return position_list_filtered
        else:
            position_list_filtered = []
            return position_list_filtered

    def retrieve_all_positions_for_contest_measure(self, retrieve_public_positions,
                                                   contest_measure_id, contest_measure_we_vote_id,
                                                   stance_we_are_looking_for,
                                                   most_recent_only=True, friends_we_vote_id_list=False):
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            position_list = []
            return position_list

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY' which means we want to return
        #  all stances

        if not positive_value_exists(contest_measure_id) and not \
                positive_value_exists(contest_measure_we_vote_id):
            position_list = []
            return position_list

        # Retrieve the support positions for this contest_measure_id
        position_list = []
        position_list_found = False
        try:
            if retrieve_public_positions:
                position_list = PositionEntered.objects.order_by('date_entered')
                retrieve_friends_positions = False
            else:
                position_list = PositionForFriends.objects.order_by('date_entered')
                retrieve_friends_positions = True

            if positive_value_exists(contest_measure_id):
                position_list = position_list.filter(contest_measure_id=contest_measure_id)
            else:
                position_list = position_list.filter(contest_measure_we_vote_id=contest_measure_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                position_list = position_list.filter(stance=stance_we_are_looking_for)
                # NOTE: We don't have a special case for
                # "if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE"
                # for contest_measure (like we do for candidate_campaign) because we don't have to deal with
                # PERCENT_RATING data with measures
            if retrieve_friends_positions and friends_we_vote_id_list is not False:
                # Find positions from friends. Look for we_vote_id case insensitive.
                we_vote_id_filter = Q()
                for we_vote_id in friends_we_vote_id_list:
                    we_vote_id_filter |= Q(voter_we_vote_id__iexact=we_vote_id)
                position_list = position_list.filter(we_vote_id_filter)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)

            # We don't need to filter out the positions that have a percent rating that doesn't match
            # the stance_we_are_looking_for (like we do for candidates)

            if len(position_list):
                position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        # If we have multiple positions for one org, we only want to show the most recent.
        if most_recent_only:
            if position_list_found:
                position_list_filtered = self.remove_older_positions_for_each_org(position_list)
            else:
                position_list_filtered = []
        else:
            position_list_filtered = position_list

        if position_list_found:
            return position_list_filtered
        else:
            position_list_filtered = []
            return position_list_filtered

    def retrieve_all_positions_for_organization(self, organization_id, organization_we_vote_id,
                                                stance_we_are_looking_for, friends_vs_public,
                                                filter_for_voter, filter_out_voter, voter_device_id,
                                                google_civic_election_id, state_code):
        """
        Return a position list with all of the organization's positions.
        Incoming filters include: stance_we_are_looking_for, friends_vs_public, filter_for_voter, filter_out_voter,
          google_civic_election_id, state_code
        :param organization_id:
        :param organization_we_vote_id:
        :param stance_we_are_looking_for:
        :param friends_vs_public:
        :param filter_for_voter: Show the positions relevant to the election the voter is currently looking at
        :param filter_out_voter: Show positions for all elections the voter is NOT looking at
        :param voter_device_id:
        :param google_civic_election_id:
        :param state_code:
        :return:
        """
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            position_list = []
            return position_list

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(organization_id) and not \
                positive_value_exists(organization_we_vote_id):
            position_list = []
            return position_list

        retrieve_friends_positions = friends_vs_public in (FRIENDS_ONLY, FRIENDS_AND_PUBLIC)
        retrieve_public_positions = friends_vs_public in (PUBLIC_ONLY, FRIENDS_AND_PUBLIC)

        # Retrieve public positions for this organization
        public_positions_list = []
        friends_positions_list = []
        position_list_found = False

        if retrieve_public_positions:
            try:
                public_positions_list = PositionEntered.objects.order_by('-vote_smart_time_span',
                                                                         '-google_civic_election_id')
                if positive_value_exists(organization_id):
                    public_positions_list = public_positions_list.filter(organization_id=organization_id)
                else:
                    public_positions_list = public_positions_list.filter(
                        organization_we_vote_id=organization_we_vote_id)
                # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
                if stance_we_are_looking_for != ANY_STANCE:
                    # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                    if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                        public_positions_list = public_positions_list.filter(
                            Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                    else:
                        public_positions_list = public_positions_list.filter(stance=stance_we_are_looking_for)

                # Gather the ids for all positions in this election
                public_only = True
                ids_for_all_positions_for_this_election = []
                google_civic_election_id_local_scope = 0
                if positive_value_exists(filter_for_voter) or positive_value_exists(filter_out_voter):
                    results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
                    google_civic_election_id_local_scope = results['google_civic_election_id']
                    if positive_value_exists(google_civic_election_id_local_scope):
                        all_positions_for_this_election = self.retrieve_all_positions_for_election(
                            google_civic_election_id_local_scope, stance_we_are_looking_for, public_only)
                        ids_for_all_positions_for_this_election = []
                        for one_position in all_positions_for_this_election:
                            ids_for_all_positions_for_this_election.append(one_position.id)

                # We can filter by only one of these
                if positive_value_exists(filter_for_voter):  # This is the default option
                    if positive_value_exists(google_civic_election_id_local_scope):
                        # Limit positions we can retrieve for an org to only the items in this election
                        public_positions_list = public_positions_list.filter(
                            id__in=ids_for_all_positions_for_this_election)
                    else:
                        # If no election is found for the voter, don't show any positions
                        public_positions_list = []
                elif positive_value_exists(filter_out_voter):
                    if positive_value_exists(google_civic_election_id_local_scope):
                        # Limit positions we can retrieve for an org to only the items NOT in this election
                        public_positions_list = public_positions_list.exclude(
                            id__in=ids_for_all_positions_for_this_election)
                    else:
                        # Leave the position_list as is.
                        pass
                elif positive_value_exists(google_civic_election_id):
                    # Please note that this option doesn't catch Vote Smart ratings, which are not
                    # linked by google_civic_election_id
                    public_positions_list = public_positions_list.filter(
                        google_civic_election_id=google_civic_election_id)
                elif positive_value_exists(state_code):
                    public_positions_list = public_positions_list.filter(state_code__iexact=state_code)

                # And finally, make sure there is a stance, or text commentary -- exclude these cases
                    public_positions_list = public_positions_list.exclude(
                        Q(stance__iexact=NO_STANCE) & Q(statement_text__isnull=True) & Q(statement_html__isnull=True)
                    )
            except Exception as e:
                handle_record_not_found_exception(e, logger=logger)

        if retrieve_friends_positions:
            try:
                # Current voter visiting the site
                current_voter_we_vote_id = ""
                voter_manager = VoterManager()
                results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
                if results['voter_found']:
                    voter = results['voter']
                    current_voter_we_vote_id = voter.we_vote_id  # Probably a wee bit slower

                voter_manager = VoterManager()
                # We need organization_we_vote_id, so look it up if only organization_id was passed in
                if not organization_we_vote_id:
                    organization_manager = OrganizationManager()
                    organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(organization_id)

                # Find the Voter id for the organization showing the positions. Organizations that sign in with
                #  their Twitter accounts get a Voter entry, with "voter.linked_organization_we_vote_id" containing
                #  the organizations we_vote_id.
                results = voter_manager.retrieve_voter_from_organization_we_vote_id(organization_we_vote_id)
                organization_voter_local_id = 0
                organization_voter_we_vote_id = ""
                if results['voter_found']:
                    organization_voter = results['voter']
                    organization_voter_local_id = organization_voter.id
                    organization_voter_we_vote_id = organization_voter.we_vote_id  # Probably a wee bit slower

                # Is the viewer a friend of this organization? If NOT, then there is no need to proceed
                voter_is_friend_of_organization = False
                if positive_value_exists(current_voter_we_vote_id) and \
                        organization_voter_we_vote_id.lower() == current_voter_we_vote_id.lower():
                    # If the current viewer is looking at own entry, then show what should be shown to friends
                    voter_is_friend_of_organization = True
                else:
                    # TODO DALE Check to see if current voter is in list of friends
                    voter_is_friend_of_organization = False  # Temp hard coding

                friends_positions_list = []
                if voter_is_friend_of_organization:
                    # If here, then the viewer is a friend with the organization. Look up positions that
                    #  are only shown to friends.
                    friends_positions_list = PositionForFriends.objects.order_by('-vote_smart_time_span',
                                                                                 '-google_civic_election_id')
                    # Get the entries saved by the organization's voter account
                    if positive_value_exists(organization_voter_local_id):
                        friends_positions_list = friends_positions_list.filter(
                            voter_id=organization_voter_local_id)
                    else:
                        friends_positions_list = friends_positions_list.filter(
                            voter_we_vote_id=organization_voter_we_vote_id)

                    # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
                    if stance_we_are_looking_for != ANY_STANCE:
                        # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                        if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                            friends_positions_list = friends_positions_list.filter(
                                Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))
                            # | Q(stance=GRADE_RATING))
                        else:
                            friends_positions_list = friends_positions_list.filter(stance=stance_we_are_looking_for)

                    # Gather the ids for all positions in this election so we can figure out which positions
                    # relate to the election the voter is currently looking at, vs. for all other elections
                    public_only = False
                    ids_for_all_positions_for_this_election = []
                    google_civic_election_id_local_scope = 0
                    if positive_value_exists(filter_for_voter) or positive_value_exists(filter_out_voter):
                        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
                        google_civic_election_id_local_scope = results['google_civic_election_id']
                        if positive_value_exists(google_civic_election_id_local_scope):
                            all_positions_for_this_election = self.retrieve_all_positions_for_election(
                                google_civic_election_id_local_scope, stance_we_are_looking_for, public_only)
                            ids_for_all_positions_for_this_election = []
                            for one_position in all_positions_for_this_election:
                                ids_for_all_positions_for_this_election.append(one_position.id)

                    # We can filter by only one of these
                    if positive_value_exists(filter_for_voter):  # This is the default option
                        if positive_value_exists(google_civic_election_id_local_scope):
                            # Limit positions we can retrieve for an org to only the items in this election
                            friends_positions_list = friends_positions_list.filter(
                                id__in=ids_for_all_positions_for_this_election)
                        else:
                            # If no election is found for the voter, don't show any positions
                            friends_positions_list = []
                    elif positive_value_exists(filter_out_voter):
                        if positive_value_exists(google_civic_election_id_local_scope):
                            # Limit positions we can retrieve for an org to only the items NOT in this election
                            friends_positions_list = friends_positions_list.exclude(
                                id__in=ids_for_all_positions_for_this_election)
                        else:
                            # Leave the position_list as is.
                            pass
                    elif positive_value_exists(google_civic_election_id):
                        # Please note that this option doesn't catch Vote Smart ratings, which are not
                        # linked by google_civic_election_id
                        # We are only using this if google_civic_election_id was passed
                        # into retrieve_all_positions_for_organization
                        friends_positions_list = friends_positions_list.filter(
                            google_civic_election_id=google_civic_election_id)
                    elif positive_value_exists(state_code):
                        friends_positions_list = friends_positions_list.filter(state_code__iexact=state_code)

                    # And finally, make sure there is a stance, or text commentary -- exclude these cases
                    friends_positions_list = friends_positions_list.exclude(
                        Q(stance__iexact=NO_STANCE) & Q(statement_text__isnull=True) & Q(statement_html__isnull=True)
                    )
            except Exception as e:
                handle_record_not_found_exception(e, logger=logger)

        # Merge public positions and "For friends" positions
        public_positions_list = list(public_positions_list)  # Force the query to run
        # Flag all of these entries as "is_for_friends_only = False"
        revised_position_list = []
        for one_position in public_positions_list:
            one_position.is_for_friends_only = False  # Add this value
            revised_position_list.append(one_position)
        public_positions_list = revised_position_list

        friends_positions_list = list(friends_positions_list)  # Force the query to run
        # Flag all of these entries as "is_for_friends_only = True"
        revised_position_list = []
        for one_position in friends_positions_list:
            one_position.is_for_friends_only = True  # Add this value
            revised_position_list.append(one_position)
        friends_positions_list = revised_position_list

        position_list = public_positions_list + friends_positions_list

        # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
        if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
            revised_position_list = []
            for one_position in position_list:
                if stance_we_are_looking_for == SUPPORT:
                    if one_position.stance == PERCENT_RATING:
                        if one_position.is_support():
                            revised_position_list.append(one_position)
                    else:
                        revised_position_list.append(one_position)
                elif stance_we_are_looking_for == OPPOSE:
                    if one_position.stance == PERCENT_RATING:
                        if one_position.is_oppose():
                            revised_position_list.append(one_position)
                    else:
                        revised_position_list.append(one_position)
            position_list = revised_position_list

        if len(position_list):
            position_list_found = True

        if position_list_found:
            return position_list
        else:
            position_list = []
            return position_list

    def retrieve_all_positions_for_public_figure(self, public_figure_id, public_figure_we_vote_id,
                                                 stance_we_are_looking_for,
                                                 filter_for_voter, voter_device_id,
                                                 google_civic_election_id, state_code):
        # TODO DALE Implement this: retrieve_all_positions_for_public_figure,
        # model after retrieve_all_positions_for_organization
        position_list = []
        return position_list

    def retrieve_all_positions_for_voter_simple(self, voter_id=0, voter_we_vote_id='', google_civic_election_id=0):
        if not positive_value_exists(voter_id) and not positive_value_exists(voter_we_vote_id):
            position_list = []
            results = {
                'status':               'MISSING_VOTER_ID',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        # Retrieve all positions for this voter

        ############################
        # Retrieve public positions
        try:
            public_positions_list = PositionEntered.objects.all()
            if positive_value_exists(voter_id):
                public_positions_list = public_positions_list.filter(voter_id=voter_id)
            else:
                public_positions_list = public_positions_list.filter(voter_we_vote_id=voter_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                public_positions_list = public_positions_list.filter(google_civic_election_id=google_civic_election_id)
            public_positions_list = public_positions_list.order_by('-google_civic_election_id')
        except Exception as e:
            position_list = []
            results = {
                'status':               'VOTER_POSITION_ENTERED_SEARCH_FAILED',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        ############################
        # Retrieve positions meant for friends only
        try:
            friends_positions_list = PositionForFriends.objects.all()
            if positive_value_exists(voter_id):
                friends_positions_list = friends_positions_list.filter(voter_id=voter_id)
            else:
                friends_positions_list = friends_positions_list.filter(voter_we_vote_id=voter_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                friends_positions_list = friends_positions_list.filter(google_civic_election_id=google_civic_election_id)
            friends_positions_list = friends_positions_list.order_by('-google_civic_election_id')
        except Exception as e:
            position_list = []
            results = {
                'status':               'VOTER_POSITION_FOR_FRIENDS_SEARCH_FAILED',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        # Merge public positions and "For friends" positions
        public_positions_list = list(public_positions_list)  # Force the query to run
        friends_positions_list = list(friends_positions_list)  # Force the query to run
        position_list = public_positions_list + friends_positions_list
        position_list_found = len(position_list)

        if position_list_found:
            simple_position_list = []
            for position in position_list:
                if positive_value_exists(position.candidate_campaign_we_vote_id):
                    ballot_item_we_vote_id = position.candidate_campaign_we_vote_id
                elif positive_value_exists(position.contest_measure_we_vote_id):
                    ballot_item_we_vote_id = position.contest_measure_we_vote_id
                else:
                    continue

                one_position = {
                    'ballot_item_we_vote_id':   ballot_item_we_vote_id,
                    'is_support':               position.is_support(),
                    'is_oppose':                position.is_oppose(),
                }
                simple_position_list.append(one_position)

            results = {
                'status':               'VOTER_POSITION_LIST_FOUND',
                'success':              True,
                'position_list_found':  True,
                'position_list':        simple_position_list,
            }
            return results
        else:
            position_list = []
            results = {
                'status':               'VOTER_POSITION_LIST_NOT_FOUND',
                'success':              True,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

    def retrieve_all_positions_for_election(self, google_civic_election_id, stance_we_are_looking_for=ANY_STANCE,
                                            public_only=False):
        """
        Since we don't have a single way to ask the positions tables for only the positions related to a single
        election, we need to look up the data in a round-about way. We get all candidates and measures in the election,
        then return all positions that are about any of those candidates or measures.
        :param google_civic_election_id:
        :param stance_we_are_looking_for:
        :param public_only:
        :return:
        """
        position_list = []

        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            position_list = []
            return position_list

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(google_civic_election_id):
            position_list = []
            return position_list

        # We aren't going to search directly on google_civic_election_id, but instead assemble a list of the items
        #  on the ballot and then retrieve positions relating to any of those ballot_items (candidates or measures)
        # TODO DALE Running this code every time is not scalable. We should cache a link between positions and the
        #  elections that we can use to look up when we need the link.

        # Candidate related positions
        candidate_campaign_we_vote_ids = []
        candidate_campaign_list_manager = CandidateCampaignListManager()
        candidate_results = candidate_campaign_list_manager.retrieve_all_candidates_for_upcoming_election(
            google_civic_election_id)
        if candidate_results['candidate_list_found']:
            candidate_list_light = candidate_results['candidate_list_light']
            for one_candidate in candidate_list_light:
                candidate_campaign_we_vote_ids.append(one_candidate['candidate_we_vote_id'])

        # Measure related positions
        contest_measure_we_vote_ids = []
        contest_measure_list_manager = ContestMeasureList()
        measure_results = contest_measure_list_manager.retrieve_all_measures_for_upcoming_election(
            google_civic_election_id)
        if measure_results['measure_list_found']:
            measure_list_light = measure_results['measure_list_light']
            for one_measure in measure_list_light:
                contest_measure_we_vote_ids.append(one_measure['measure_we_vote_id'])

        position_list_found = False
        try:
            if public_only:
                position_list = PositionEntered.objects.order_by('date_entered')
                # We are removing old entries from voters that should be private
                position_list = position_list.filter(
                    Q(voter_id__isnull=True) |
                    Q(voter_id__exact=0))
            else:
                position_list = PositionForFriends.objects.order_by('date_entered')
            position_list = position_list.filter(
                Q(candidate_campaign_we_vote_id__in=candidate_campaign_we_vote_ids) |
                Q(contest_measure_we_vote_id__in=contest_measure_we_vote_ids))
            # position_list = position_list.filter(contest_measure_we_vote_id=contest_measure_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                position_list = position_list.filter(stance=stance_we_are_looking_for)
            if len(position_list):
                position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if position_list_found:
            return position_list
        else:
            position_list = []
            return position_list

    def remove_older_positions_for_each_org(self, position_list):
        # If we have multiple positions for one org, we only want to show the most recent
        organization_already_reviewed = []
        organization_with_multiple_positions = []
        newest_position_for_org = {}  # Figure out the newest position per org that we should show
        for one_position in position_list:
            if one_position.organization_we_vote_id:
                if one_position.organization_we_vote_id not in organization_already_reviewed:
                    organization_already_reviewed.append(one_position.organization_we_vote_id)
                # Are we dealing with a time span (instead of google_civic_election_id)?
                if positive_value_exists(one_position.vote_smart_time_span):
                    # Take the first four digits of one_position.vote_smart_time_span
                    first_four_digits = convert_to_int(one_position.vote_smart_time_span[:4])
                    # And figure out the newest position for each org
                    if one_position.organization_we_vote_id in newest_position_for_org:
                        # If we are here, it means we have seen this organization once already
                        if one_position.organization_we_vote_id not in organization_with_multiple_positions:
                            organization_with_multiple_positions.append(one_position.organization_we_vote_id)
                        # If this position is newer than the one already looked at, update newest_position_for_org
                        if first_four_digits > newest_position_for_org[one_position.organization_we_vote_id]:
                            newest_position_for_org[one_position.organization_we_vote_id] = first_four_digits
                    else:
                        newest_position_for_org[one_position.organization_we_vote_id] = first_four_digits

        position_list_filtered = []
        position_included_for_this_org = {}
        for one_position in position_list:
            if one_position.organization_we_vote_id in organization_with_multiple_positions:
                first_four_digits = convert_to_int(one_position.vote_smart_time_span[:4])
                if (newest_position_for_org[one_position.organization_we_vote_id] == first_four_digits) and \
                        (one_position.organization_we_vote_id not in position_included_for_this_org):
                    # If this position is the newest from among the organization's positions, include in results
                    position_list_filtered.append(one_position)
                    # Only add one position to position_list_filtered once
                    position_included_for_this_org[one_position.organization_we_vote_id] = True
            else:
                position_list_filtered.append(one_position)

        return position_list_filtered

    def retrieve_public_positions_count_for_candidate_campaign(self, candidate_campaign_id,
                                                               candidate_campaign_we_vote_id,
                                                               stance_we_are_looking_for):
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            return 0

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(candidate_campaign_id) and not \
                positive_value_exists(candidate_campaign_we_vote_id):
            return 0

        # Retrieve the support positions for this candidate_campaign_id
        position_count = 0
        try:
            position_list = PositionEntered.objects.order_by('date_entered')
            if positive_value_exists(candidate_campaign_id):
                position_list = position_list.filter(candidate_campaign_id=candidate_campaign_id)
            else:
                position_list = position_list.filter(candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT:
                    position_list = position_list.filter(
                        Q(stance=stance_we_are_looking_for) |  # Matches "is_support"
                        (Q(stance=PERCENT_RATING) & Q(vote_smart_rating__gte=66))  # Matches "is_positive_rating"
                    )  # | Q(stance=GRADE_RATING))
                elif stance_we_are_looking_for == OPPOSE:
                    position_list = position_list.filter(
                        Q(stance=stance_we_are_looking_for) |  # Matches "is_oppose"
                        (Q(stance=PERCENT_RATING) & Q(vote_smart_rating__lte=33))  # Matches "is_negative_rating"
                    )  # | Q(stance=GRADE_RATING))
                else:
                    position_list = position_list.filter(stance=stance_we_are_looking_for)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)

            position_count = position_list.count()
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        return position_count

    def retrieve_public_positions_count_for_contest_measure(self, contest_measure_id,
                                                            contest_measure_we_vote_id,
                                                            stance_we_are_looking_for):
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            return 0

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY' which means we want to return
        #  all stances

        if not positive_value_exists(contest_measure_id) and not \
                positive_value_exists(contest_measure_we_vote_id):
            return 0

        # Retrieve the support positions for this contest_measure_id
        position_count = 0
        try:
            position_list = PositionEntered.objects.order_by('date_entered')
            if positive_value_exists(contest_measure_id):
                position_list = position_list.filter(contest_measure_id=contest_measure_id)
            else:
                position_list = position_list.filter(contest_measure_we_vote_id=contest_measure_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                position_list = position_list.filter(stance=stance_we_are_looking_for)
            # position_list = position_list.filter(election_id=election_id)

            position_count = position_list.count()
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        return position_count

    def retrieve_possible_duplicate_positions(self, google_civic_election_id, organization_we_vote_id,
                                              candidate_we_vote_id, measure_we_vote_id,
                                              we_vote_id_from_master=''):
        position_list_objects = []
        filters = []
        position_list_found = False

        try:
            position_queryset = PositionEntered.objects.all()
            position_queryset = position_queryset.filter(google_civic_election_id=google_civic_election_id)
            # We don't look for office_we_vote_id because of the chance that locally we are using a
            # different we_vote_id
            # position_queryset = position_queryset.filter(contest_office_we_vote_id__iexact=office_we_vote_id)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                position_queryset = position_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            # Situation 1 organization_we_vote_id + candidate_we_vote_id matches an entry already in the db
            if positive_value_exists(organization_we_vote_id) and positive_value_exists(candidate_we_vote_id):
                new_filter = (Q(organization_we_vote_id__iexact=organization_we_vote_id) &
                              Q(candidate_campaign_we_vote_id__iexact=candidate_we_vote_id))
                filters.append(new_filter)

            # Situation 2 organization_we_vote_id + measure_we_vote_id matches an entry already in the db
            if positive_value_exists(organization_we_vote_id) and positive_value_exists(measure_we_vote_id):
                new_filter = (Q(organization_we_vote_id__iexact=organization_we_vote_id) &
                              Q(contest_measure_we_vote_id__iexact=measure_we_vote_id))
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                position_queryset = position_queryset.filter(final_filters)

            position_list_objects = position_queryset

            if len(position_list_objects):
                position_list_found = True
                status = 'DUPLICATE_POSITIONS_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_POSITIONS_RETRIEVED'
                success = True
        except PositionEntered.DoesNotExist:
            # No candidates found. Not a problem.
            status = 'NO_DUPLICATE_POSITIONS_FOUND_DoesNotExist'
            position_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_positions ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'position_list_found':      position_list_found,
            'position_list':            position_list_objects,
        }
        return results


class PositionEnteredManager(models.Model):

    def __unicode__(self):
        return "PositionEnteredManager"

    def fetch_we_vote_id_from_local_id(self, position_id):
        if positive_value_exists(position_id):
            results = self.retrieve_organization_from_id(position_id)
            if results['position_found']:
                position = results['position']
                return position.we_vote_id
            else:
                return None
        else:
            return None

    def retrieve_organization_candidate_campaign_position(self, organization_id, candidate_campaign_id,
                                                          retrieve_position_for_friends=False,
                                                          google_civic_election_id=False):
        """
        Find a position based on the organization_id & candidate_campaign_id
        :param organization_id:
        :param candidate_campaign_id:
        :param retrieve_position_for_friends:
        :param google_civic_election_id:
        :return:
        """
        position_id = 0
        position_we_vote_id = ''
        voter_id = 0
        contest_office_id = 0
        contest_measure_id = 0
        contest_office_we_vote_id = ''
        candidate_campaign_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id,
            retrieve_position_for_friends,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            google_civic_election_id)

    def retrieve_organization_candidate_campaign_position_with_we_vote_id(self, organization_id,
                                                                          candidate_campaign_we_vote_id,
                                                                          retrieve_position_for_friends=False,
                                                                          google_civic_election_id=False):
        """
        Find a position based on the organization_id & candidate_campaign_id
        :param organization_id:
        :param candidate_campaign_we_vote_id:
        :param retrieve_position_for_friends:
        :param google_civic_election_id:
        :return:
        """
        position_id = 0
        position_we_vote_id = ''
        voter_id = 0
        contest_office_id = 0
        contest_measure_id = 0
        contest_office_we_vote_id = ''
        candidate_campaign_id = 0
        contest_measure_we_vote_id = ''
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id,
            retrieve_position_for_friends,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            google_civic_election_id)

    def retrieve_voter_contest_office_position(self, voter_id, contest_office_id, retrieve_position_for_friends=False):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends)

    def retrieve_voter_contest_office_position_with_we_vote_id(self, voter_id, contest_office_we_vote_id,
                                                               retrieve_position_for_friends=False):
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
            retrieve_position_for_friends,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_voter_candidate_campaign_position(self, voter_id, candidate_campaign_id,
                                                   retrieve_position_for_friends=False):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        contest_office_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends)

    def retrieve_voter_candidate_campaign_position_with_we_vote_id(self, voter_id, candidate_campaign_we_vote_id,
                                                                   retrieve_position_for_friends=False):
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
            retrieve_position_for_friends,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_voter_contest_measure_position(self, voter_id, contest_measure_id, retrieve_position_for_friends=True):
        organization_id = 0
        position_id = 0
        position_we_vote_id = ''
        contest_office_id = 0
        candidate_campaign_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends)

    def retrieve_voter_contest_measure_position_with_we_vote_id(self, voter_id, contest_measure_we_vote_id,
                                                                retrieve_position_for_friends=False):
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
            retrieve_position_for_friends,
            contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_position_from_id(self, position_id, retrieve_position_for_friends=False):
        position_we_vote_id = ''
        organization_id = 0
        voter_id = 0
        contest_office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends)

    def retrieve_position_from_we_vote_id(self, position_we_vote_id, retrieve_position_for_friends=False):
        position_id = 0
        organization_id = 0
        voter_id = 0
        contest_office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.retrieve_position(
            position_id, position_we_vote_id, organization_id, voter_id,
            contest_office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends)

    def retrieve_position(self, position_id, position_we_vote_id, organization_id, voter_id,
                          contest_office_id, candidate_campaign_id, contest_measure_id,
                          retrieve_position_for_friends=False,
                          contest_office_we_vote_id='', candidate_campaign_we_vote_id='',
                          contest_measure_we_vote_id='', google_civic_election_id=False):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        if retrieve_position_for_friends:
            position_on_stage = PositionForFriends
        else:
            position_on_stage = PositionEntered

        success = False

        try:
            if positive_value_exists(position_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_POSITION_ID"
                position_on_stage = position_on_stage.objects.get(id=position_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(position_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_WE_VOTE_ID"
                position_on_stage = position_on_stage.objects.get(we_vote_id=position_we_vote_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_office_id):
                if positive_value_exists(google_civic_election_id):
                    status = "RETRIEVE_POSITION_FOUND_WITH_ORG_OFFICE_AND_ELECTION"
                    position_on_stage = position_on_stage.objects.get(
                        organization_id=organization_id, contest_office_id=contest_office_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_id = position_on_stage.id
                    success = True
                else:
                    status = "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_OFFICE"
                    position_on_stage = position_on_stage.objects.get(
                        organization_id=organization_id, contest_office_id=contest_office_id)
                    # If still here, we found an existing position
                    position_id = position_on_stage.id
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(candidate_campaign_id):
                if positive_value_exists(google_civic_election_id):
                    status = "RETRIEVE_POSITION_FOUND_WITH_ORG_CANDIDATE_AND_ELECTION"
                    position_on_stage = position_on_stage.objects.get(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_id = position_on_stage.id
                    success = True
                else:
                    status = "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_CANDIDATE"
                    position_on_stage = position_on_stage.objects.get(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id)
                    # If still here, we found an existing position
                    position_id = position_on_stage.id
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(candidate_campaign_we_vote_id):
                if positive_value_exists(google_civic_election_id):
                    status = "RETRIEVE_POSITION_FOUND_WITH_ORG_CANDIDATE_WE_VOTE_ID_AND_ELECTION"
                    position_on_stage = position_on_stage.objects.get(
                        organization_id=organization_id, candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_id = position_on_stage.id
                    success = True
                else:
                    status = "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_CANDIDATE_WE_VOTE_ID"
                    position_on_stage = position_on_stage.objects.get(
                        organization_id=organization_id, candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
                    # If still here, we found an existing position
                    position_id = position_on_stage.id
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_measure_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_MEASURE"
                position_on_stage = position_on_stage.objects.get(
                    organization_id=organization_id, contest_measure_id=contest_measure_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_OFFICE"
                position_on_stage = position_on_stage.objects.get(
                    voter_id=voter_id, contest_office_id=contest_office_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_OFFICE_WE_VOTE_ID"
                position_on_stage = position_on_stage.objects.get(
                    voter_id=voter_id, contest_office_we_vote_id=contest_office_we_vote_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_CANDIDATE"
                position_on_stage = position_on_stage.objects.get(
                    voter_id=voter_id, candidate_campaign_id=candidate_campaign_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_CANDIDATE_WE_VOTE_ID"
                position_on_stage = position_on_stage.objects.get(
                    voter_id=voter_id, candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_MEASURE"
                position_on_stage = position_on_stage.objects.get(
                    voter_id=voter_id, contest_measure_id=contest_measure_id)
                position_id = position_on_stage.id
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_we_vote_id):
                status = "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_MEASURE_WE_VOTE_ID"
                position_on_stage = position_on_stage.objects.get(
                    voter_id=voter_id, contest_measure_we_vote_id=contest_measure_we_vote_id)
                position_id = position_on_stage.id
                success = True
            else:
                status = "RETRIEVE_POSITION_INSUFFICIENT_VARIABLES"
        except MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status = "RETRIEVE_POSITION_MULTIPLE_FOUND"
            if retrieve_position_for_friends:
                position_on_stage = PositionForFriends()
            else:
                position_on_stage = PositionEntered()
        except ObjectDoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status = "RETRIEVE_POSITION_NONE_FOUND"
            if retrieve_position_for_friends:
                position_on_stage = PositionForFriends()
            else:
                position_on_stage = PositionEntered()

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'position_found':           True if position_id > 0 else False,
            'position_id':              position_id,
            'position':                 position_on_stage,
            'is_support':                       position_on_stage.is_support(),
            'is_positive_rating':               position_on_stage.is_positive_rating(),
            'is_support_or_positive_rating':    position_on_stage.is_support_or_positive_rating(),
            'is_oppose':                        position_on_stage.is_oppose(),
            'is_negative_rating':               position_on_stage.is_negative_rating(),
            'is_oppose_or_negative_rating':     position_on_stage.is_oppose_or_negative_rating(),
            'is_no_stance':             position_on_stage.is_no_stance(),
            'is_information_only':      position_on_stage.is_information_only(),
            'is_still_deciding':        position_on_stage.is_still_deciding(),
            'date_last_changed':        position_on_stage.date_last_changed,
            'date_entered':             position_on_stage.date_entered,
            'google_civic_election_id': google_civic_election_id,
        }
        return results

    def toggle_on_voter_support_for_candidate_campaign(self, voter_id, candidate_campaign_id, set_as_public_position):
        stance = SUPPORT
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, set_as_public_position)

    def toggle_off_voter_support_for_candidate_campaign(self, voter_id, candidate_campaign_id, set_as_public_position):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, set_as_public_position)

    def toggle_on_voter_oppose_for_candidate_campaign(self, voter_id, candidate_campaign_id, set_as_public_position):
        stance = OPPOSE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, set_as_public_position)

    def toggle_off_voter_oppose_for_candidate_campaign(self, voter_id, candidate_campaign_id, set_as_public_position):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, set_as_public_position)

    def toggle_on_voter_position_for_candidate_campaign(self, voter_id, candidate_campaign_id,
                                                        stance, set_as_public_position):
        # Does a position from this voter already exist?
        position_entered_manager = PositionEnteredManager()
        retrieve_position_for_friends = not set_as_public_position
        results = position_entered_manager.retrieve_voter_candidate_campaign_position(voter_id, candidate_campaign_id,
                                                                                      retrieve_position_for_friends)

        if results['MultipleObjectsReturned']:
            logger.warn("delete all but one and take it over?")
            status = 'MultipleObjectsReturned-WORK_NEEDED'
            if set_as_public_position:
                voter_position_on_stage = PositionEntered
            else:
                voter_position_on_stage = PositionForFriends
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
                                                              stance, candidate_campaign_id, contest_measure_id,
                                                              set_as_public_position)

    def toggle_voter_position(self, voter_id, voter_position_found, voter_position_on_stage, stance,
                              candidate_campaign_id, contest_measure_id, set_as_public_position):
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

                if set_as_public_position:
                    voter_position_on_stage = PositionEntered(
                        voter_id=voter_id,
                        candidate_campaign_id=candidate_campaign_id,
                        candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                        contest_measure_id=contest_measure_id,
                        contest_measure_we_vote_id=contest_measure_we_vote_id,
                        stance=stance,
                        #  statement_text=statement_text,
                    )
                else:
                    voter_position_on_stage = PositionForFriends(
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

    def toggle_on_voter_support_for_contest_measure(self, voter_id, contest_measure_id, set_as_public_position):
        stance = SUPPORT
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, set_as_public_position)

    def toggle_off_voter_support_for_contest_measure(self, voter_id, contest_measure_id, set_as_public_position):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, set_as_public_position)

    def toggle_on_voter_oppose_for_contest_measure(self, voter_id, contest_measure_id, set_as_public_position):
        stance = OPPOSE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, set_as_public_position)

    def toggle_off_voter_oppose_for_contest_measure(self, voter_id, contest_measure_id, set_as_public_position):
        stance = NO_STANCE
        position_entered_manager = PositionEnteredManager()
        return position_entered_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, set_as_public_position)

    def toggle_on_voter_position_for_contest_measure(self, voter_id, contest_measure_id, stance,
                                                     set_as_public_position):
        # Does a position from this voter already exist?
        position_entered_manager = PositionEnteredManager()
        retrieve_position_for_friends = not set_as_public_position
        results = position_entered_manager.retrieve_voter_contest_measure_position(voter_id, contest_measure_id,
                                                                                   retrieve_position_for_friends)

        if results['MultipleObjectsReturned']:
            logger.warn("delete all but one and take it over?")
            status = 'MultipleObjectsReturned-WORK_NEEDED'
            if set_as_public_position:
                voter_position_on_stage = PositionEntered
            else:
                voter_position_on_stage = PositionForFriends
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
                                                              stance, candidate_campaign_id, contest_measure_id,
                                                              set_as_public_position)

    # We rely on these unique identifiers:
    #   position_id, position_we_vote_id
    # Pass in a value if we want it saved. Pass in "False" if we want to leave it the same.
    def update_or_create_position(
            self, position_id, position_we_vote_id,
            organization_we_vote_id=False,
            public_figure_we_vote_id=False,
            voter_we_vote_id=False,
            google_civic_election_id=False,
            state_code=False,
            ballot_item_display_name=False,
            office_we_vote_id=False,
            candidate_we_vote_id=False,
            measure_we_vote_id=False,
            stance=False,
            set_as_public_position=False,
            statement_text=False,
            statement_html=False,
            more_info_url=False,
            vote_smart_time_span=False,
            vote_smart_rating_id=False,
            vote_smart_rating=False,
            vote_smart_rating_name=False):
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
        if set_as_public_position:
            position_on_stage = PositionEntered()
            retrieve_position_for_friends = False
        else:
            position_on_stage = PositionForFriends()
            retrieve_position_for_friends = True
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
                position_results = position_entered_manager.retrieve_position_from_id(position_id,
                                                                                      retrieve_position_for_friends)
                found_with_id = True
            elif positive_value_exists(position_we_vote_id):
                position_results = position_entered_manager.retrieve_position_from_we_vote_id(
                    position_we_vote_id, retrieve_position_for_friends)
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
                if state_code:
                    position_on_stage.state_code = state_code
                if ballot_item_display_name:
                    position_on_stage.ballot_item_display_name = ballot_item_display_name
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
                    # TODO Verify that "stance" contains a legal value
                    position_on_stage.stance = stance
                if statement_text:
                    position_on_stage.statement_text = statement_text
                if statement_html:
                    position_on_stage.statement_html = statement_html
                if more_info_url:
                    position_on_stage.more_info_url = more_info_url
                if vote_smart_time_span:
                    position_on_stage.vote_smart_time_span = vote_smart_time_span
                if vote_smart_rating_id:
                    position_on_stage.vote_smart_rating_id = vote_smart_rating_id
                if vote_smart_rating:
                    position_on_stage.vote_smart_rating = vote_smart_rating
                if vote_smart_rating_name:
                    position_on_stage.vote_smart_rating_name = vote_smart_rating_name

                # As long as at least one of the above variables has changed, then save
                if organization_we_vote_id or google_civic_election_id or ballot_item_display_name or office_we_vote_id \
                        or candidate_we_vote_id or measure_we_vote_id or stance or statement_text \
                        or statement_html or more_info_url \
                        or vote_smart_time_span or vote_smart_rating_id or vote_smart_rating or vote_smart_rating_name:
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
                        position_on_stage = position_on_stage.objects.get(
                            candidate_campaign_we_vote_id=candidate_we_vote_id,
                            organization_we_vote_id=organization_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass
                # If there wasn't a google_civic_election_id, look for vote_smart_time_span
                elif positive_value_exists(candidate_we_vote_id) and \
                        positive_value_exists(organization_we_vote_id) and \
                        positive_value_exists(vote_smart_time_span):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            candidate_campaign_we_vote_id=candidate_we_vote_id,
                            organization_we_vote_id=organization_we_vote_id,
                            vote_smart_time_span=vote_smart_time_span
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID_WITH_TIME_SPAN"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID_WITH_TIME_SPAN"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 4) measure_we_vote_id + organization_we_vote_id exists? Try to find it. If not, go to step 5
                if positive_value_exists(measure_we_vote_id) and \
                        positive_value_exists(organization_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            contest_measure_we_vote_id=measure_we_vote_id,
                            organization_we_vote_id=organization_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_MEASURE_AND_ORGANIZATION_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_MEASURE_AND_ORGANIZATION_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 5) office_we_vote_id + organization_we_vote_id exists? Try to find it. If not, go to step 6
                if positive_value_exists(office_we_vote_id) and \
                        positive_value_exists(organization_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            contest_office_we_vote_id=office_we_vote_id,
                            organization_we_vote_id=organization_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_OFFICE_AND_ORGANIZATION_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_OFFICE_AND_ORGANIZATION_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this office_we_vote_id wasn't found
                        pass

                # TODO Test public_figure (6-8) and voter (9-11) related cases
                # 6-8: Public-Figure-related cases
                # 6) candidate_we_vote_id + public_figure_we_vote_id exists? Try to find it. If not, go to step 7
                if positive_value_exists(candidate_we_vote_id) and \
                        positive_value_exists(public_figure_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            candidate_campaign_we_vote_id=candidate_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_CANDIDATE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 7) measure_we_vote_id + public_figure_we_vote_id exists? Try to find it. If not, go to step 8
                if positive_value_exists(measure_we_vote_id) and \
                        positive_value_exists(public_figure_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            contest_measure_we_vote_id=measure_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_MEASURE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_MEASURE_AND_PUBLIC_FIGURE_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 8) office_we_vote_id + public_figure_we_vote_id exists? Try to find it. If not, go to step 9
                if positive_value_exists(office_we_vote_id) and \
                        positive_value_exists(public_figure_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            contest_office_we_vote_id=office_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this office_we_vote_id wasn't found
                        pass

                # 9-11: Voter-related cases
                # 9) candidate_we_vote_id + organization_we_vote_id exists? Try to find it. If not, go to step 10
                if positive_value_exists(candidate_we_vote_id) and \
                        positive_value_exists(voter_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            candidate_campaign_we_vote_id=candidate_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_CANDIDATE_AND_VOTER_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_VOTER_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 10) measure_we_vote_id + voter_we_vote_id exists? Try to find it. If not, go to step 11
                if positive_value_exists(measure_we_vote_id) and \
                        positive_value_exists(voter_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            contest_measure_we_vote_id=measure_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_MEASURE_AND_VOTER_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_MEASURE_AND_VOTER_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass

                # 11) office_we_vote_id + organization_we_vote_id exists? Try to find it.
                if positive_value_exists(office_we_vote_id) and \
                        positive_value_exists(voter_we_vote_id) and \
                        positive_value_exists(google_civic_election_id):
                    try:
                        position_on_stage = position_on_stage.objects.get(
                            contest_office_we_vote_id=office_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            google_civic_election_id=google_civic_election_id
                        )
                        position_on_stage_found = True
                        found_with_status = "FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_OFFICE_AND_VOTER_WE_VOTE_ID"
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this office wasn't found
                        pass

                # Save values entered in steps 3-11
                if position_on_stage_found:
                    try:
                        if ballot_item_display_name or stance or statement_text or statement_html or more_info_url:
                            if ballot_item_display_name:
                                position_on_stage.ballot_item_display_name = ballot_item_display_name
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

                if state_code is False:
                    state_code = None

                if ballot_item_display_name is False:
                    ballot_item_display_name = None

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

                if stance not in(SUPPORT, NO_STANCE, INFORMATION_ONLY, STILL_DECIDING, OPPOSE, PERCENT_RATING):
                    stance = NO_STANCE

                if statement_text is False:
                    statement_text = None

                if statement_html is False:
                    statement_html = None

                if more_info_url is False:
                    more_info_url = None

                if vote_smart_time_span is False:
                    vote_smart_time_span = None

                if vote_smart_rating_id is False:
                    vote_smart_rating_id = None

                if vote_smart_rating is False:
                    vote_smart_rating = None

                if vote_smart_rating_name is False:
                    vote_smart_rating_name = None

                position_on_stage = position_on_stage.objects.create(
                    organization_we_vote_id=organization_we_vote_id,
                    organization_id=organization_id,
                    voter_we_vote_id=voter_we_vote_id,
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    ballot_item_display_name=ballot_item_display_name,
                    contest_office_we_vote_id=office_we_vote_id,
                    contest_office_id=contest_office_id,
                    candidate_campaign_we_vote_id=candidate_we_vote_id,
                    candidate_campaign_id=candidate_campaign_id,
                    contest_measure_we_vote_id=measure_we_vote_id,
                    contest_measure_id=contest_measure_id,
                    stance=stance,
                    statement_text=statement_text,
                    statement_html=statement_html,
                    more_info_url=more_info_url,
                    vote_smart_time_span=vote_smart_time_span,
                    vote_smart_rating_id=vote_smart_rating_id,
                    vote_smart_rating=vote_smart_rating,
                    vote_smart_rating_name=vote_smart_rating_name
                )
                status = "CREATE_POSITION_SUCCESSFUL"
                success = True

                new_position_created = True
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                success = False
                status = "NEW_POSITION_COULD_NOT_BE_CREATED"
                if set_as_public_position:
                    position_on_stage = PositionEntered
                else:
                    position_on_stage = PositionForFriends

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'position':                 position_on_stage,
            'new_position_created':     new_position_created,
        }
        return results

    def refresh_cached_position_info(self, position_object):
        position_change = False

        # Start with "speaker" information (Organization, Voter, or Public Figure)
        if positive_value_exists(position_object.organization_we_vote_id):
            if not positive_value_exists(position_object.speaker_display_name) \
                    or not positive_value_exists(position_object.speaker_image_url_https) \
                    or not positive_value_exists(position_object.speaker_twitter_handle):
                try:
                    # We need to look in the organization table for speaker_display_name & speaker_image_url_https
                    organization_manager = OrganizationManager()
                    organization_id = 0
                    results = organization_manager.retrieve_organization(organization_id,
                                                                         position_object.organization_we_vote_id)
                    if results['organization_found']:
                        organization = results['organization']
                        if not positive_value_exists(position_object.speaker_display_name):
                            # speaker_display_name is missing so look it up from source
                            position_object.speaker_display_name = organization.organization_name
                            position_change = True
                        if not positive_value_exists(position_object.speaker_image_url_https):
                            # speaker_image_url_https is missing so look it up from source
                            position_object.speaker_image_url_https = organization.organization_photo_url()
                            position_change = True
                        if not positive_value_exists(position_object.speaker_twitter_handle):
                            # speaker_twitter_handle is missing so look it up from source
                            position_object.speaker_twitter_handle = organization.organization_twitter_handle
                            position_change = True
                except Exception as e:
                    pass
        elif positive_value_exists(position_object.voter_id):
            if not positive_value_exists(position_object.speaker_display_name) or \
                    not positive_value_exists(position_object.voter_we_vote_id) or \
                    not positive_value_exists(position_object.speaker_image_url_https) or \
                    not positive_value_exists(position_object.speaker_twitter_handle):
                try:
                    # We need to look in the voter table for speaker_display_name
                    voter_manager = VoterManager()
                    results = voter_manager.retrieve_voter_by_id(position_object.voter_id)
                    if results['voter_found']:
                        voter = results['voter']
                        if not positive_value_exists(position_object.speaker_display_name):
                            # speaker_display_name is missing so look it up from source
                            position_object.speaker_display_name = voter.get_full_name()
                            position_change = True
                        if not positive_value_exists(position_object.voter_we_vote_id):
                            # speaker_we_vote_id is missing so look it up from source
                            position_object.voter_we_vote_id = voter.we_vote_id
                            position_change = True
                        if not positive_value_exists(position_object.speaker_image_url_https):
                            # speaker_image_url_https is missing so look it up from source
                            position_object.speaker_image_url_https = voter.voter_photo_url()
                            position_change = True
                        if not positive_value_exists(position_object.speaker_twitter_handle):
                            # speaker_twitter_handle is missing so look it up from source
                            position_object.speaker_twitter_handle = voter.twitter_screen_name
                            position_change = True
                except Exception as e:
                    pass

        elif positive_value_exists(position_object.public_figure_we_vote_id):
            pass

        # Now move onto "ballot_item" information
        if not positive_value_exists(position_object.ballot_item_display_name) \
                or not positive_value_exists(position_object.ballot_item_image_url_https) \
                or not positive_value_exists(position_object.ballot_item_twitter_handle) \
                or not positive_value_exists(position_object.state_code):
            # Candidate
            if positive_value_exists(position_object.candidate_campaign_id) or \
                    positive_value_exists(position_object.candidate_campaign_we_vote_id):
                try:
                    # We need to look in the voter table for speaker_display_name
                    candidate_campaign_manager = CandidateCampaignManager()
                    results = candidate_campaign_manager.retrieve_candidate_campaign(
                        position_object.candidate_campaign_id, position_object.candidate_campaign_we_vote_id)
                    if results['candidate_campaign_found']:
                        candidate = results['candidate_campaign']
                        if not positive_value_exists(position_object.ballot_item_display_name):
                            # ballot_item_display_name is missing so look it up from source
                            position_object.ballot_item_display_name = candidate.display_candidate_name()
                            position_change = True
                        if not positive_value_exists(position_object.ballot_item_image_url_https):
                            # ballot_item_image_url_https is missing so look it up from source
                            position_object.ballot_item_image_url_https = candidate.candidate_photo_url()
                            position_change = True
                        if not positive_value_exists(position_object.ballot_item_twitter_handle):
                            # ballot_item_image_twitter_handle is missing so look it up from source
                            position_object.ballot_item_twitter_handle = candidate.candidate_twitter_handle
                            position_change = True
                        if not positive_value_exists(position_object.state_code):
                            # state_code is missing so look it up from source
                            position_object.state_code = candidate.get_candidate_state()
                            position_change = True
                except Exception as e:
                    pass
            # Measure
            elif positive_value_exists(position_object.contest_measure_id) or \
                    positive_value_exists(position_object.contest_measure_we_vote_id):
                # TODO DALE Build out refresh_cached_position_info for measures
                pass
            # Office
            elif positive_value_exists(position_object.contest_office_id) or \
                    positive_value_exists(position_object.contest_office_we_vote_id):
                pass

        if position_change:
            position_object.save()

        return position_object
