# position/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
# Diagrams here: https://docs.google.com/drawings/d/1DsPnl97GKe9f14h41RPeZDssDUztRETGkXGaolXCeyo/edit

from analytics.models import ACTION_POSITION_TAKEN, AnalyticsManager
from candidate.models import CandidateCampaign, CandidateCampaignManager
from ballot.controllers import figure_out_google_civic_election_id_voter_is_watching
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.db.models import Q
from election.models import Election
from exception.models import handle_exception, handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from friend.models import FriendManager
from measure.models import ContestMeasure, ContestMeasureManager
from office.models import ContestOfficeManager
from organization.models import Organization, OrganizationManager
import robot_detection
from twitter.models import TwitterUser
from voter.models import fetch_voter_id_from_voter_we_vote_id, fetch_voter_we_vote_id_from_voter_id, Voter, VoterManager
from voter_guide.models import VoterGuideManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_position_integer, fetch_site_unique_id_prefix


ANY_STANCE = 'ANY_STANCE'  # This is a way to indicate when we want to return any stance (support, oppose, no_stance)
SUPPORT = 'SUPPORT'
STILL_DECIDING = 'STILL_DECIDING'
NO_STANCE = 'NO_STANCE'  # DALE 2016-8-29 We will want to deprecate NO_STANCE and replace with INFORMATION_ONLY
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
FRIENDS_ONLY = 'FRIENDS_ONLY'
PUBLIC_ONLY = 'PUBLIC_ONLY'
SHOW_PUBLIC = 'SHOW_PUBLIC'

# this_election_vs_others
THIS_ELECTION_ONLY = 'THIS_ELECTION_ONLY'
ALL_OTHER_ELECTIONS = 'ALL_OTHER_ELECTIONS'
ALL_ELECTIONS = 'ALL_ELECTIONS'

POSITION = 'POSITION'

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
    ballot_item_image_url_https_large = models.URLField(verbose_name='url of https large version image for candidate,'
                                                                     ' measure or office', blank=True, null=True)
    ballot_item_image_url_https_medium = models.URLField(verbose_name='url of https medium version image for candidate,'
                                                                      ' measure or office', blank=True, null=True)
    ballot_item_image_url_https_tiny = models.URLField(verbose_name='url of https tiny version image for candidate,'
                                                                    ' measure or office', blank=True, null=True)
    ballot_item_twitter_handle = models.CharField(verbose_name='twitter screen_name for candidate, measure, or office',
                                                  max_length=255, null=True, unique=False)

    # What is the organization name, voter name, or public figure name? We cache this here for rapid display
    speaker_display_name = models.CharField(
        verbose_name="name of the org or person with position", max_length=255, null=True, blank=True, unique=False)
    # We cache the url to an image for the org, voter, or public_figure for rapid display
    speaker_image_url_https = models.URLField(verbose_name='url of https image for org or person with position',
                                              blank=True, null=True)
    speaker_image_url_https_large = models.URLField(verbose_name='url of https large version image for org or '
                                                                 'person with position', blank=True, null=True)
    speaker_image_url_https_medium = models.URLField(verbose_name='url of https medium version image for org or '
                                                                  'person with position', blank=True, null=True)
    speaker_image_url_https_tiny = models.URLField(verbose_name='url of https tiny version image for org or '
                                                                'person with position', blank=True, null=True)
    speaker_twitter_handle = models.CharField(verbose_name='twitter screen_name for org or person with position',
                                              max_length=255, null=True, unique=False)

    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now_add=True)
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
    state_code = models.CharField(verbose_name="us state of the ballot item position is for",
                                  max_length=2, null=True, blank=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    # ### Values from Vote Smart ###
    vote_smart_rating_id = models.BigIntegerField(null=True, blank=True, unique=False)
    # Usually in one of these two formats 2015, 2014-2015
    vote_smart_time_span = models.CharField(
        verbose_name="the period in which the organization stated this position", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating = models.CharField(
        verbose_name="vote smart value between 0-100", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating_integer = models.PositiveIntegerField(
        verbose_name="vote smart value between 0-100", default=None, null=True, blank=True)
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
    contest_office_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)

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
    # The measure's title as passed over by Google Civic. We save this so we can match to this measure if an import
    # doesn't include a we_vote_id we recognize.
    google_civic_measure_title = models.CharField(verbose_name="measure title exactly as received from google civic",
                                                  max_length=255, null=True, blank=True)
    # Useful for queries based on Politicians -- not the main table we use for ballot display though
    politician_id = models.BigIntegerField(verbose_name='', null=True, blank=True)
    politician_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for politician", max_length=255, null=True,
        blank=True, unique=False)
    political_party = models.CharField(verbose_name="political party", max_length=255, null=True)

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
            self.generate_new_we_vote_id()
        super(PositionEntered, self).save(*args, **kwargs)

    def generate_new_we_vote_id(self):
        # ...generate a new id
        site_unique_id_prefix = fetch_site_unique_id_prefix()
        next_local_integer = fetch_next_we_vote_id_position_integer()
        # "wv" = We Vote
        # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
        # "pos" = tells us this is a unique id for an pos
        # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
        self.we_vote_id = "wv{site_unique_id_prefix}pos{next_integer}".format(
            site_unique_id_prefix=site_unique_id_prefix,
            next_integer=next_local_integer,
        )
        # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        return

    def get_kind_of_ballot_item(self):
        if positive_value_exists(self.candidate_campaign_we_vote_id):
            return "CANDIDATE"
        elif positive_value_exists(self.contest_measure_we_vote_id):
            return "MEASURE"
        elif positive_value_exists(self.contest_office_we_vote_id):
            return "OFFICE"
        return ""

    def get_ballot_item_id(self):
        if positive_value_exists(self.candidate_campaign_id):
            return self.candidate_campaign_id
        elif positive_value_exists(self.contest_measure_id):
            return self.contest_measure_id
        return ""

    def get_ballot_item_we_vote_id(self):
        if positive_value_exists(self.candidate_campaign_we_vote_id):
            return self.candidate_campaign_we_vote_id
        elif positive_value_exists(self.contest_measure_we_vote_id):
            return self.contest_measure_we_vote_id
        return ""

    # Is the position is an actual endorsement?
    def is_support(self):
        if self.stance == SUPPORT:
            return True
        return False

    # Is the position a rating that is 66% or greater?
    def is_positive_rating(self):
        if self.stance == PERCENT_RATING:
            if self.vote_smart_rating:
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
            if self.vote_smart_rating:
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
        """
        "is_no_stance" means that they may have a position, but we don't know the stance -- its not in the database
        DALE 2016-8-29 We will want to deprecate NO_STANCE and replace with INFORMATION_ONLY
        :return:
        """
        if self.stance == NO_STANCE:
            return True
        elif self.stance == PERCENT_RATING:
            if self.vote_smart_rating:
                rating_percentage = convert_to_int(self.vote_smart_rating)
                if (rating_percentage > 33) and (rating_percentage < 66):
                    return True
        return False

    def is_information_only(self):
        """
        "information_only" means that they are not taking a support/oppose position
        :return:
        """
        if self.stance == INFORMATION_ONLY:
            return True
        if positive_value_exists(self.statement_text) or positive_value_exists(self.statement_html):
            # If there is a text description, and no SUPPORT or OPPOSE, then it is INFORMATION_ONLY
            if self.stance != OPPOSE and self.stance != SUPPORT and self.stance != STILL_DECIDING \
                    and self.stance != PERCENT_RATING:
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
            logger.error("position.candidate_campaign Found multiple")
            return
        except CandidateCampaign.DoesNotExist:
            return
        return candidate_campaign

    def contest_measure(self):
        if not self.contest_measure_id:
            return
        try:
            contest_measure = ContestMeasure.objects.get(id=self.contest_measure_id)
        except ContestMeasure.MultipleObjectsReturned as e:
            logger.error("position.contest_measure Found multiple")
            return
        except ContestMeasure.DoesNotExist:
            return
        return contest_measure

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

    def voter(self):
        if not self.voter_we_vote_id:
            return
        try:
            voter = Voter.objects.get(we_vote_id=self.voter_we_vote_id)
        except Voter.MultipleObjectsReturned as e:
            return
        except Voter.DoesNotExist:
            return
        return voter


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
    ballot_item_image_url_https_large = models.URLField(verbose_name='url of https large version image for candidate,'
                                                                     ' measure or office', blank=True, null=True)
    ballot_item_image_url_https_medium = models.URLField(verbose_name='url of https medium version image for candidate,'
                                                                      ' measure or office', blank=True, null=True)
    ballot_item_image_url_https_tiny = models.URLField(verbose_name='url of https tiny version image for candidate,'
                                                                    ' measure or office', blank=True, null=True)
    ballot_item_twitter_handle = models.CharField(
        verbose_name='twitter screen_name for candidate, measure, or office',
        max_length=255, null=True, unique=False)

    # What is the organization name, voter name, or public figure name? We cache this here for rapid display
    speaker_display_name = models.CharField(
        verbose_name="name of the org or person with position", max_length=255, null=True, blank=True, unique=False)
    # We cache the url to an image for the org, voter, or public_figure for rapid display
    speaker_image_url_https = models.URLField(verbose_name='url of https image for org or person with position',
                                              blank=True, null=True)
    speaker_image_url_https_large = models.URLField(verbose_name='url of https large version image for org or '
                                                                 'person with position', blank=True, null=True)
    speaker_image_url_https_medium = models.URLField(verbose_name='url of https medium version image for org or '
                                                                  'person with position', blank=True, null=True)
    speaker_image_url_https_tiny = models.URLField(verbose_name='url of https tiny version image for org or '
                                                                'person with position', blank=True, null=True)
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
    vote_smart_rating_integer = models.PositiveIntegerField(
        verbose_name="vote smart value between 0-100", default=None, null=True, blank=True)
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
    contest_office_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)

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
    political_party = models.CharField(verbose_name="candidate political party", max_length=255, null=True)

    # This is the measure/initiative/proposition that the position refers to.
    #  Either contest_measure is filled, contest_office OR candidate_campaign, but not all three
    contest_measure_id = models.BigIntegerField(verbose_name='id of contest_measure', null=True, blank=True)
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the contest_measure", max_length=255, null=True,
        blank=True, unique=False)
    # The measure's title as passed over by Google Civic. We save this so we can match to this measure if an import
    # doesn't include a we_vote_id we recognize.
    google_civic_measure_title = models.CharField(verbose_name="measure title exactly as received from google civic",
                                                  max_length=255, null=True, blank=True)

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
            self.generate_new_we_vote_id()
        super(PositionForFriends, self).save(*args, **kwargs)

    def generate_new_we_vote_id(self):
        # ...generate a new id
        site_unique_id_prefix = fetch_site_unique_id_prefix()
        next_local_integer = fetch_next_we_vote_id_position_integer()
        # "wv" = We Vote
        # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
        # "pos" = tells us this is a unique id for an pos
        # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
        self.we_vote_id = "wv{site_unique_id_prefix}pos{next_integer}".format(
            site_unique_id_prefix=site_unique_id_prefix,
            next_integer=next_local_integer,
        )
        # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        return

    def get_kind_of_ballot_item(self):
        if positive_value_exists(self.candidate_campaign_we_vote_id):
            return "CANDIDATE"
        elif positive_value_exists(self.contest_measure_we_vote_id):
            return "MEASURE"
        elif positive_value_exists(self.contest_office_we_vote_id):
            return "OFFICE"
        return ""

    def get_ballot_item_id(self):
        if positive_value_exists(self.candidate_campaign_id):
            return self.candidate_campaign_id
        elif positive_value_exists(self.contest_measure_id):
            return self.contest_measure_id
        return ""

    def get_ballot_item_we_vote_id(self):
        if positive_value_exists(self.candidate_campaign_we_vote_id):
            return self.candidate_campaign_we_vote_id
        elif positive_value_exists(self.contest_measure_we_vote_id):
            return self.contest_measure_we_vote_id
        return ""

    # Is the position is an actual endorsement?
    def is_support(self):
        if self.stance == SUPPORT:
            return True
        return False

    # Is the position a rating that is 66% or greater?
    def is_positive_rating(self):
        if self.stance == PERCENT_RATING:
            if self.vote_smart_rating:
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
            if self.vote_smart_rating:
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
        """
        "is_no_stance" means that they may have a position, but we don't know the stance -- its not in the database
        DALE 2016-8-29 We will want to deprecate NO_STANCE and replace with INFORMATION_ONLY
        :return:
        """
        if self.stance == NO_STANCE:
            return True
        elif self.stance == PERCENT_RATING:
            if self.vote_smart_rating:
                rating_percentage = convert_to_int(self.vote_smart_rating)
                if (rating_percentage > 33) and (rating_percentage < 66):
                    return True
        return False

    def is_information_only(self):
        """
        "information_only" means that they are not taking a support/oppose position
        :return:
        """
        if self.stance == INFORMATION_ONLY:
            return True
        if positive_value_exists(self.statement_text) or positive_value_exists(self.statement_html):
            # If there is a text description, and no SUPPORT or OPPOSE, then it is INFORMATION_ONLY
            if self.stance != OPPOSE and self.stance != SUPPORT and self.stance != STILL_DECIDING \
                    and self.stance != PERCENT_RATING:
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

    def contest_measure(self):
        if not self.contest_measure_id:
            return
        try:
            contest_measure = ContestMeasure.objects.get(id=self.contest_measure_id)
        except ContestMeasure.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("position.candidate_campaign Found multiple")
            return
        except ContestMeasure.DoesNotExist:
            return
        return contest_measure

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

    def voter(self):
        if not self.voter_we_vote_id:
            return
        try:
            voter = Voter.objects.get(we_vote_id=self.voter_we_vote_id)
        except Voter.MultipleObjectsReturned as e:
            return
        except Voter.DoesNotExist:
            return
        return voter


class PositionListManager(models.Model):
    def add_is_public_position(self, incoming_position_list, is_public_position):
        outgoing_position_list = []
        for one_position in incoming_position_list:
            one_position.is_public_position = is_public_position
            outgoing_position_list.append(one_position)

        return outgoing_position_list

    def calculate_positions_followed_by_voter(
            self, voter_id, all_positions_list, organizations_followed_by_voter_by_id, voter_friend_list=[]):
        """
        We need a list of positions that were made by an organization, public figure or friend that this voter follows
        :param voter_id:
        :param all_positions_list:
        :param organizations_followed_by_voter_by_id:
        :param voter_friend_list:
        :return:
        """

        positions_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list:
            if position.voter_id == voter_id:  # We include the voter currently viewing the ballot in this list
                positions_followed_by_voter.append(position)
            elif position.voter_we_vote_id in voter_friend_list:
                positions_followed_by_voter.append(position)
            elif position.organization_id in organizations_followed_by_voter_by_id:
                positions_followed_by_voter.append(position)

        return positions_followed_by_voter

    def calculate_positions_not_followed_by_voter(
            self, all_positions_list, organizations_followed_by_voter, voter_friend_list=[]):
        """
        We need a list of positions that were NOT made by an organization, public figure or friend
        that this voter follows
        :param all_positions_list:
        :param organizations_followed_by_voter:
        :param voter_friend_list:
        :return:
        """
        positions_not_followed_by_voter = []
        # Only return the positions if they are from organizations the voter follows
        for position in all_positions_list:
            # Some positions are for individual voters, so we want to filter those out
            if position.organization_id \
                    and position.organization_id in organizations_followed_by_voter:
                # Do not add
                pass
            elif position.voter_we_vote_id \
                    and position.voter_we_vote_id in voter_friend_list:
                # Do not add
                pass
            else:
                positions_not_followed_by_voter.append(position)

        return positions_not_followed_by_voter

    def fetch_voter_positions_count_for_candidate_campaign(
            self, candidate_campaign_id, candidate_campaign_we_vote_id='', stance_we_are_looking_for=ANY_STANCE):
        """
        We are only retrieving voter positions, not positions of organizations.
        :param candidate_campaign_id:
        :param candidate_campaign_we_vote_id:
        :param stance_we_are_looking_for:
        :return:
        """
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            return 0

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(candidate_campaign_id) and not \
                positive_value_exists(candidate_campaign_we_vote_id):
            return 0

        # Retrieve the support positions for this candidate_campaign
        total_count = 0
        # Public Positions
        try:
            public_position_list = PositionEntered.objects.using('readonly').all()
            public_position_list = public_position_list.exclude(voter_we_vote_id=None)  # Don't include if no we_vote_id

            if positive_value_exists(candidate_campaign_id):
                public_position_list = public_position_list.filter(candidate_campaign_id=candidate_campaign_id)
            else:
                public_position_list = public_position_list.filter(
                    candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                    public_position_list = public_position_list.filter(
                        Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                else:
                    public_position_list = public_position_list.filter(stance=stance_we_are_looking_for)

            # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
            if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                revised_public_position_list = []
                for one_position in public_position_list:
                    if stance_we_are_looking_for == SUPPORT:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_positive_rating():  # This was "is_support"
                                revised_public_position_list.append(one_position)
                        else:
                            revised_public_position_list.append(one_position)
                    elif stance_we_are_looking_for == OPPOSE:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_negative_rating():  # This was "is_oppose"
                                revised_public_position_list.append(one_position)
                        else:
                            revised_public_position_list.append(one_position)
                public_position_list = revised_public_position_list

            total_count += len(public_position_list)
        except Exception as e:
            pass

        # Friends-only Positions
        try:
            friends_only_position_list = PositionForFriends.objects.using('readonly').all()
            friends_only_position_list = friends_only_position_list.exclude(voter_we_vote_id=None)  # No we_vote_id

            if positive_value_exists(candidate_campaign_id):
                friends_only_position_list = friends_only_position_list.filter(
                    candidate_campaign_id=candidate_campaign_id)
            else:
                friends_only_position_list = friends_only_position_list.filter(
                    candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                    friends_only_position_list = friends_only_position_list.filter(
                        Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                else:
                    friends_only_position_list = friends_only_position_list.filter(stance=stance_we_are_looking_for)

            # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
            if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                revised_friends_only_position_list = []
                for one_position in friends_only_position_list:
                    if stance_we_are_looking_for == SUPPORT:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_positive_rating():  # This was "is_support"
                                revised_friends_only_position_list.append(one_position)
                        else:
                            revised_friends_only_position_list.append(one_position)
                    elif stance_we_are_looking_for == OPPOSE:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_negative_rating():  # This was "is_oppose"
                                revised_friends_only_position_list.append(one_position)
                        else:
                            revised_friends_only_position_list.append(one_position)
                friends_only_position_list = revised_friends_only_position_list

            total_count += len(friends_only_position_list)
        except Exception as e:
            pass

        return total_count

    def fetch_voter_positions_count_for_contest_measure(
            self, contest_measure_id, contest_measure_we_vote_id='', stance_we_are_looking_for=ANY_STANCE):
        """
        We are only retrieving voter positions, not positions of organizations.
        :param contest_measure_id:
        :param contest_measure_we_vote_id:
        :param stance_we_are_looking_for:
        :return:
        """
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            return 0

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(contest_measure_id) and not \
                positive_value_exists(contest_measure_we_vote_id):
            return 0

        # Retrieve the support positions for this contest_measure
        total_count = 0
        # Public Positions
        try:
            public_position_list = PositionEntered.objects.using('readonly').all()
            public_position_list = public_position_list.exclude(voter_we_vote_id=None)  # Don't include if no we_vote_id

            if positive_value_exists(contest_measure_id):
                public_position_list = public_position_list.filter(contest_measure_id=contest_measure_id)
            else:
                public_position_list = public_position_list.filter(
                    contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                    public_position_list = public_position_list.filter(
                        Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                else:
                    public_position_list = public_position_list.filter(stance=stance_we_are_looking_for)

            # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
            if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                revised_public_position_list = []
                for one_position in public_position_list:
                    if stance_we_are_looking_for == SUPPORT:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_positive_rating():  # This was "is_support"
                                revised_public_position_list.append(one_position)
                        else:
                            revised_public_position_list.append(one_position)
                    elif stance_we_are_looking_for == OPPOSE:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_negative_rating():  # This was "is_oppose"
                                revised_public_position_list.append(one_position)
                        else:
                            revised_public_position_list.append(one_position)
                public_position_list = revised_public_position_list

            total_count += len(public_position_list)
        except Exception as e:
            pass

        # Friends-only Positions
        try:
            friends_only_position_list = PositionForFriends.objects.using('readonly').all()
            friends_only_position_list = friends_only_position_list.exclude(voter_we_vote_id=None)  # No we_vote_id

            if positive_value_exists(contest_measure_id):
                friends_only_position_list = friends_only_position_list.filter(contest_measure_id=contest_measure_id)
            else:
                friends_only_position_list = friends_only_position_list.filter(
                    contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                    friends_only_position_list = friends_only_position_list.filter(
                        Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                else:
                    friends_only_position_list = friends_only_position_list.filter(stance=stance_we_are_looking_for)

            # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
            if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                revised_friends_only_position_list = []
                for one_position in friends_only_position_list:
                    if stance_we_are_looking_for == SUPPORT:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_positive_rating():  # This was "is_support"
                                revised_friends_only_position_list.append(one_position)
                        else:
                            revised_friends_only_position_list.append(one_position)
                    elif stance_we_are_looking_for == OPPOSE:
                        if one_position.stance == PERCENT_RATING:
                            if one_position.is_negative_rating():  # This was "is_oppose"
                                revised_friends_only_position_list.append(one_position)
                        else:
                            revised_friends_only_position_list.append(one_position)
                friends_only_position_list = revised_friends_only_position_list

            total_count += len(friends_only_position_list)
        except Exception as e:
            pass

        return total_count

    def fetch_positions_count_for_voter_guide(self, organization_we_vote_id, google_civic_election_id, state_code,
                                              retrieve_public_positions=True, stance_we_are_looking_for=ANY_STANCE):
        # Don't proceed unless we have a correct stance identifier
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            return 0

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        # Don't proceed unless we have organization identifier and the election we care about
        if not positive_value_exists(organization_we_vote_id) and not \
                positive_value_exists(google_civic_election_id):
            return 0

        position_count = 0
        try:
            if retrieve_public_positions:
                position_on_stage_starter = PositionEntered
                position_on_stage = PositionEntered()
            else:
                position_on_stage_starter = PositionForFriends
                position_on_stage = PositionForFriends()

            position_list = position_on_stage_starter.objects.using('readonly').order_by('date_entered')
            position_list = position_list.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            position_list = position_list.filter(google_civic_election_id=google_civic_election_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT:
                    position_list = position_list.filter(
                        Q(stance=stance_we_are_looking_for) |  # Matches "is_support"
                        (Q(stance=PERCENT_RATING) & Q(vote_smart_rating_integer__gte=66))
                    )  # Matches "is_positive_rating"
                elif stance_we_are_looking_for == OPPOSE:
                    position_list = position_list.filter(
                        Q(stance=stance_we_are_looking_for) |  # Matches "is_oppose"
                        (Q(stance=PERCENT_RATING) & Q(vote_smart_rating_integer__lte=33))
                    )  # Matches "is_negative_rating"
                else:
                    position_list = position_list.filter(stance=stance_we_are_looking_for)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)

            position_count = position_list.count()
        except Exception as e:
            pass

        return position_count

    def positions_exist_for_voter(self, voter_we_vote_id):
        # Don't proceed unless we have voter identifier
        if not positive_value_exists(voter_we_vote_id):
            return 0

        position_count = 0
        try:
            position_on_stage_starter = PositionForFriends

            position_list = position_on_stage_starter.objects.using('readonly').all()
            position_list = position_list.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            position_count = position_list.count()
        except Exception as e:
            pass

        if positive_value_exists(position_count):
            return True

        try:
            position_on_stage_starter = PositionEntered

            position_list = position_on_stage_starter.objects.using('readonly').all()
            position_list = position_list.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            position_count = position_list.count()
        except Exception as e:
            pass

        if positive_value_exists(position_count):
            return True

        return False

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
                positions_ignored_by_voter.append(position)

        return positions_ignored_by_voter

    def remove_positions_unrelated_to_issues(self, positions_list, organizations_related_to_issue):
        """
        We filter the list of organizations whose we_vote_id is present in organizations_related_to_issue
        :param positions_list: 
        :param organizations_related_to_issue: 
        :return: 
        """
        positions_related_to_organization = []
        for position in positions_list:
            if position.organization_we_vote_id in organizations_related_to_issue:
                positions_related_to_organization.append(position)

        return positions_related_to_organization

    def repair_all_positions_for_voter(self, incoming_voter_id=0, incoming_voter_we_vote_id=''):
        """
        Make sure that every position owned by the voter has matching identifiers (voter_id, voter_we_vote_id,
        organization_we_vote_id, organization_id).
        :param incoming_voter_id:
        :param incoming_voter_we_vote_id:
        :return:
        """
        if not positive_value_exists(incoming_voter_id) and not positive_value_exists(incoming_voter_we_vote_id):
            results = {
                'status':           'REPAIR_ALL_POSITIONS-MISSING_VOTER_ID_OR_WE_VOTE_ID ',
                'success':          False,
                'repair_complete':  False,
            }
            return results

        status = ""
        organization_manager = OrganizationManager()
        voter_manager = VoterManager()
        if positive_value_exists(incoming_voter_id):
            results = voter_manager.retrieve_voter_by_id(incoming_voter_id)
        else:
            results = voter_manager.retrieve_voter_by_we_vote_id(incoming_voter_we_vote_id)

        voter_id = 0
        voter_we_vote_id = ""
        organization_we_vote_id = ""
        organization_id = 0
        if results['voter_found']:
            voter = results['voter']
            voter_id = voter.id
            voter_we_vote_id = voter.we_vote_id
            if not positive_value_exists(voter.linked_organization_we_vote_id):
                # Heal the data
                repair_results = organization_manager.repair_missing_linked_organization_we_vote_id(voter)
                status += repair_results['status']
                if repair_results['voter_repaired']:
                    voter = repair_results['voter']

            organization_we_vote_id = voter.linked_organization_we_vote_id
            if positive_value_exists(organization_we_vote_id):
                # Look up the organization_id
                organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                    voter.linked_organization_we_vote_id)
                if organization_results['organization_found']:
                    organization = organization_results['organization']
                    organization_id = organization.id

        if not positive_value_exists(voter_id) or not positive_value_exists(voter_we_vote_id):
            results = {
                'status':           'REPAIR_ALL_POSITIONS-MISSING_VOTER_ID_OR_WE_VOTE_ID ',
                'success':          False,
                'repair_complete':  False,
            }
            return results

        if not positive_value_exists(organization_id) or not positive_value_exists(organization_we_vote_id):
            results = {
                'status':           'REPAIR_ALL_POSITIONS-MISSING_ORGANIZATION_ID_OR_WE_VOTE_ID ',
                'success':          False,
                'repair_complete':  False,
            }
            return results

        failure_counter = 0

        ############################
        # Retrieve public positions
        try:
            # Retrieve by voter_id
            public_positions_list_query = PositionEntered.objects.all()
            public_positions_list_query = public_positions_list_query.filter(voter_id=voter_id)
            public_positions_list = list(public_positions_list_query)  # Force the query to run
            for public_position in public_positions_list:
                public_position_to_be_saved = False
                try:
                    if public_position.voter_id != voter_id:
                        public_position.voter_id = voter_id
                        public_position_to_be_saved = True
                    if public_position.voter_we_vote_id != voter_we_vote_id:
                        public_position.voter_we_vote_id = voter_we_vote_id
                        public_position_to_be_saved = True
                    if public_position.organization_id != organization_id:
                        public_position.organization_id = organization_id
                        public_position_to_be_saved = True
                    if public_position.organization_we_vote_id != organization_we_vote_id:
                        public_position.organization_we_vote_id = organization_we_vote_id
                        public_position_to_be_saved = True

                    if public_position_to_be_saved:
                        public_position.save()

                except Exception as e:
                    failure_counter += 1

            # Retrieve by voter_we_vote_id
            public_positions_list_query = PositionEntered.objects.all()
            public_positions_list_query = public_positions_list_query.filter(
                voter_we_vote_id__iexact=voter_we_vote_id)
            public_positions_list = list(public_positions_list_query)  # Force the query to run
            for public_position in public_positions_list:
                public_position_to_be_saved = False
                try:
                    if public_position.voter_id != voter_id:
                        public_position.voter_id = voter_id
                        public_position_to_be_saved = True
                    if public_position.voter_we_vote_id != voter_we_vote_id:
                        public_position.voter_we_vote_id = voter_we_vote_id
                        public_position_to_be_saved = True
                    if public_position.organization_id != organization_id:
                        public_position.organization_id = organization_id
                        public_position_to_be_saved = True
                    if public_position.organization_we_vote_id != organization_we_vote_id:
                        public_position.organization_we_vote_id = organization_we_vote_id
                        public_position_to_be_saved = True

                    if public_position_to_be_saved:
                        public_position.save()

                except Exception as e:
                    failure_counter += 1

            # Retrieve by organization_id
            public_positions_list_query = PositionEntered.objects.all()
            public_positions_list_query = public_positions_list_query.filter(organization_id=organization_id)
            public_positions_list = list(public_positions_list_query)  # Force the query to run
            for public_position in public_positions_list:
                public_position_to_be_saved = False
                try:
                    if public_position.voter_id != voter_id:
                        public_position.voter_id = voter_id
                        public_position_to_be_saved = True
                    if public_position.voter_we_vote_id != voter_we_vote_id:
                        public_position.voter_we_vote_id = voter_we_vote_id
                        public_position_to_be_saved = True
                    if public_position.organization_id != organization_id:
                        public_position.organization_id = organization_id
                        public_position_to_be_saved = True
                    if public_position.organization_we_vote_id != organization_we_vote_id:
                        public_position.organization_we_vote_id = organization_we_vote_id
                        public_position_to_be_saved = True

                    if public_position_to_be_saved:
                        public_position.save()

                except Exception as e:
                    failure_counter += 1

            # Retrieve by organization_we_vote_id
            public_positions_list_query = PositionEntered.objects.all()
            public_positions_list_query = public_positions_list_query.filter(
                organization_we_vote_id__iexact=organization_we_vote_id)
            public_positions_list = list(public_positions_list_query)  # Force the query to run
            for public_position in public_positions_list:
                public_position_to_be_saved = False
                try:
                    if public_position.voter_id != voter_id:
                        public_position.voter_id = voter_id
                        public_position_to_be_saved = True
                    if public_position.voter_we_vote_id != voter_we_vote_id:
                        public_position.voter_we_vote_id = voter_we_vote_id
                        public_position_to_be_saved = True
                    if public_position.organization_id != organization_id:
                        public_position.organization_id = organization_id
                        public_position_to_be_saved = True
                    if public_position.organization_we_vote_id != organization_we_vote_id:
                        public_position.organization_we_vote_id = organization_we_vote_id
                        public_position_to_be_saved = True

                    if public_position_to_be_saved:
                        public_position.save()

                except Exception as e:
                    failure_counter += 1

        except Exception as e:
            results = {
                'status':           'REPAIR-VOTER_POSITION_FOR_PUBLIC_SEARCH_FAILED ',
                'success':          False,
                'repair_complete':  False,
            }
            return results

        ############################
        # Retrieve positions meant for friends only
        try:
            # Retrieve by voter_id
            friends_positions_list_query = PositionForFriends.objects.all()
            friends_positions_list_query = friends_positions_list_query.filter(voter_id=voter_id)
            friends_positions_list = list(friends_positions_list_query)  # Force the query to run
            for friends_position in friends_positions_list:
                friends_position_to_be_saved = False
                try:
                    if friends_position.voter_id != voter_id:
                        friends_position.voter_id = voter_id
                        friends_position_to_be_saved = True
                    if friends_position.voter_we_vote_id != voter_we_vote_id:
                        friends_position.voter_we_vote_id = voter_we_vote_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_id != organization_id:
                        friends_position.organization_id = organization_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_we_vote_id != organization_we_vote_id:
                        friends_position.organization_we_vote_id = organization_we_vote_id
                        friends_position_to_be_saved = True

                    if friends_position_to_be_saved:
                        friends_position.save()

                except Exception as e:
                    failure_counter += 1

            # Retrieve by voter_we_vote_id
            friends_positions_list_query = PositionForFriends.objects.all()
            friends_positions_list_query = friends_positions_list_query.filter(
                voter_we_vote_id__iexact=voter_we_vote_id)
            friends_positions_list = list(friends_positions_list_query)  # Force the query to run
            for friends_position in friends_positions_list:
                friends_position_to_be_saved = False
                try:
                    if friends_position.voter_id != voter_id:
                        friends_position.voter_id = voter_id
                        friends_position_to_be_saved = True
                    if friends_position.voter_we_vote_id != voter_we_vote_id:
                        friends_position.voter_we_vote_id = voter_we_vote_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_id != organization_id:
                        friends_position.organization_id = organization_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_we_vote_id != organization_we_vote_id:
                        friends_position.organization_we_vote_id = organization_we_vote_id
                        friends_position_to_be_saved = True

                    if friends_position_to_be_saved:
                        friends_position.save()

                except Exception as e:
                    failure_counter += 1

            # Retrieve by organization_id
            friends_positions_list_query = PositionForFriends.objects.all()
            friends_positions_list_query = friends_positions_list_query.filter(organization_id=organization_id)
            friends_positions_list = list(friends_positions_list_query)  # Force the query to run
            for friends_position in friends_positions_list:
                friends_position_to_be_saved = False
                try:
                    if friends_position.voter_id != voter_id:
                        friends_position.voter_id = voter_id
                        friends_position_to_be_saved = True
                    if friends_position.voter_we_vote_id != voter_we_vote_id:
                        friends_position.voter_we_vote_id = voter_we_vote_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_id != organization_id:
                        friends_position.organization_id = organization_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_we_vote_id != organization_we_vote_id:
                        friends_position.organization_we_vote_id = organization_we_vote_id
                        friends_position_to_be_saved = True

                    if friends_position_to_be_saved:
                        friends_position.save()

                except Exception as e:
                    failure_counter += 1

            # Retrieve by organization_we_vote_id
            friends_positions_list_query = PositionForFriends.objects.all()
            friends_positions_list_query = friends_positions_list_query.filter(
                organization_we_vote_id__iexact=organization_we_vote_id)
            friends_positions_list = list(friends_positions_list_query)  # Force the query to run
            for friends_position in friends_positions_list:
                friends_position_to_be_saved = False
                try:
                    if friends_position.voter_id != voter_id:
                        friends_position.voter_id = voter_id
                        friends_position_to_be_saved = True
                    if friends_position.voter_we_vote_id != voter_we_vote_id:
                        friends_position.voter_we_vote_id = voter_we_vote_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_id != organization_id:
                        friends_position.organization_id = organization_id
                        friends_position_to_be_saved = True
                    if friends_position.organization_we_vote_id != organization_we_vote_id:
                        friends_position.organization_we_vote_id = organization_we_vote_id
                        friends_position_to_be_saved = True

                    if friends_position_to_be_saved:
                        friends_position.save()

                except Exception as e:
                    failure_counter += 1

        except Exception as e:
            results = {
                'status':           'REPAIR-VOTER_POSITION_FOR_FRIENDS_SEARCH_FAILED ',
                'success':          False,
                'repair_complete':  False,
            }
            return results

        if positive_value_exists(failure_counter):
            results = {
                'status':           'VOTER_POSITION_LIST_PARTIALLY_REPAIRED ({failure_counter} failures) '
                                    ''.format(failure_counter=failure_counter),
                'success':          True,
                'repair_complete':  True,
            }
        else:
            results = {
                'status':           'VOTER_POSITION_LIST_FULLY_REPAIRED ',
                'success':          True,
                'repair_complete':  True,
            }

        return results

    def retrieve_all_positions_for_candidate_campaign(self, retrieve_public_positions,
                                                      candidate_campaign_id, candidate_campaign_we_vote_id='',
                                                      stance_we_are_looking_for=ANY_STANCE, most_recent_only=True,
                                                      friends_we_vote_id_list=False,
                                                      organizations_followed_we_vote_id_list=False,
                                                      retrieve_all_admin_override=False,
                                                      read_only=False):
        """
        We do not attempt to retrieve public positions and friend's-only positions in the same call.
        :param retrieve_public_positions:
        :param candidate_campaign_id:
        :param candidate_campaign_we_vote_id:
        :param stance_we_are_looking_for:
        :param most_recent_only:
        :param friends_we_vote_id_list: If this comes in as a list, use that list. If it comes in as False,
         we can consider looking up the values if they are needed, but we will then need voter_device_id passed in too.
        :param organizations_followed_we_vote_id_list: If this comes in as a list, use that list.
         If it comes in as False, we can consider looking up the values if they are needed,
         but we will then need voter_device_id passed in too.
        :param retrieve_all_admin_override:
        :param read_only:
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

        if retrieve_public_positions:
            # If retrieving PositionsEntered, make sure we have the necessary variables
            if type(organizations_followed_we_vote_id_list) is list \
                    and len(organizations_followed_we_vote_id_list) == 0:
                position_list = []
                return position_list
        else:
            # If retrieving PositionForFriends, make sure we have the necessary variables
            if not friends_we_vote_id_list and not retrieve_all_admin_override:
                position_list = []
                return position_list
            elif type(friends_we_vote_id_list) is list and len(friends_we_vote_id_list) == 0:
                position_list = []
                return position_list

        # Retrieve the support positions for this candidate_campaign_id
        position_list = []
        position_list_found = False
        try:
            if retrieve_public_positions:
                # We intentionally do not use 'readonly' here since we need to save based on the results of this query
                if read_only:
                    position_list_query = PositionEntered.objects.using('readonly').order_by('date_entered')
                else:
                    position_list_query = PositionEntered.objects.order_by('date_entered')
                retrieve_friends_positions = False
            else:
                # We intentionally do not use 'readonly' here since we need to save based on the results of this query
                if read_only:
                    position_list_query = PositionForFriends.objects.using('readonly').order_by('date_entered')
                else:
                    position_list_query = PositionForFriends.objects.order_by('date_entered')
                retrieve_friends_positions = True

            if positive_value_exists(candidate_campaign_id):
                position_list_query = position_list_query.filter(candidate_campaign_id=candidate_campaign_id)
            else:
                position_list_query = position_list_query.filter(
                    candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                    position_list_query = position_list_query.filter(
                        Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                else:
                    position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)

            # Only one of these blocks will be used at a time
            if retrieve_friends_positions and friends_we_vote_id_list is not False:
                # Find positions from friends. Look for we_vote_id case insensitive.
                we_vote_id_filter = Q()
                for we_vote_id in friends_we_vote_id_list:
                    we_vote_id_filter |= Q(voter_we_vote_id__iexact=we_vote_id)
                position_list_query = position_list_query.filter(we_vote_id_filter)
            if retrieve_public_positions and organizations_followed_we_vote_id_list is not False:
                # Find positions from organizations voter follows.
                we_vote_id_filter = Q()
                for we_vote_id in organizations_followed_we_vote_id_list:
                    we_vote_id_filter |= Q(organization_we_vote_id__iexact=we_vote_id)
                position_list_query = position_list_query.filter(we_vote_id_filter)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)
            position_list = list(position_list_query)

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
                if len(position_list) > 1:
                    position_list_filtered = self.remove_older_positions_for_each_org(position_list)
                else:
                    position_list_filtered = position_list
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
                                                   most_recent_only=True,
                                                   friends_we_vote_id_list=False,
                                                   organizations_followed_we_vote_id_list=False,
                                                   read_only=False):
        """

        :param retrieve_public_positions:
        :param contest_measure_id:
        :param contest_measure_we_vote_id:
        :param stance_we_are_looking_for:
        :param most_recent_only:
        :param friends_we_vote_id_list: If this comes in as a list, use that list. If it comes in as False,
         we can consider looking up the values if they are needed, but we will then need voter_device_id passed in too.
        :param organizations_followed_we_vote_id_list: If this comes in as a list, use that list.
         If it comes in as False, we can consider looking up the values if they are needed,
         but we will then need voter_device_id passed in too.
        :param read_only:
        :return:
        """
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

        if retrieve_public_positions:
            # If retrieving PositionsEntered, make sure we have the necessary variables
            if type(organizations_followed_we_vote_id_list) is list \
                    and len(organizations_followed_we_vote_id_list) == 0:
                position_list = []
                return position_list
        else:
            # If retrieving PositionForFriends, make sure we have the necessary variables
            if not friends_we_vote_id_list:
                position_list = []
                return position_list
            elif type(friends_we_vote_id_list) is list and len(friends_we_vote_id_list) == 0:
                position_list = []
                return position_list

        # Retrieve the support positions for this contest_measure_id
        position_list = []
        position_list_found = False
        try:
            if retrieve_public_positions:
                # We intentionally do not use 'readonly' here since we need to save based on the results of this query
                if read_only:
                    position_list_query = PositionEntered.objects.using('readonly').order_by('date_entered')
                else:
                    position_list_query = PositionEntered.objects.order_by('date_entered')
                retrieve_friends_positions = False
            else:
                # We intentionally do not use 'readonly' here since we need to save based on the results of this query
                if read_only:
                    position_list_query = PositionForFriends.objects.using('readonly').order_by('date_entered')
                else:
                    position_list_query = PositionForFriends.objects.order_by('date_entered')
                retrieve_friends_positions = True

            if positive_value_exists(contest_measure_id):
                position_list_query = position_list_query.filter(contest_measure_id=contest_measure_id)
            else:
                position_list_query = position_list_query.filter(
                    contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)
                # NOTE: We don't have a special case for
                # "if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE"
                # for contest_measure (like we do for candidate_campaign) because we don't have to deal with
                # PERCENT_RATING data with measures

            # Only one of these blocks will be used at a time
            if retrieve_friends_positions and friends_we_vote_id_list is not False:
                # Find positions from friends. Look for we_vote_id case insensitive.
                we_vote_id_filter = Q()
                for we_vote_id in friends_we_vote_id_list:
                    we_vote_id_filter |= Q(voter_we_vote_id__iexact=we_vote_id)
                position_list_query = position_list_query.filter(we_vote_id_filter)
            if retrieve_public_positions and organizations_followed_we_vote_id_list is not False:
                # Find positions from organizations voter follows.
                we_vote_id_filter = Q()
                for we_vote_id in organizations_followed_we_vote_id_list:
                    we_vote_id_filter |= Q(organization_we_vote_id__iexact=we_vote_id)
                position_list = position_list_query.filter(we_vote_id_filter)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)

            # We don't need to filter out the positions that have a percent rating that doesn't match
            # the stance_we_are_looking_for (like we do for candidates)
            position_list = list(position_list_query)
            if len(position_list):
                position_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        # If we have multiple positions for one org, we only want to show the most recent.
        if most_recent_only:
            if position_list_found:
                if len(position_list) > 1:
                    position_list_filtered = self.remove_older_positions_for_each_org(position_list)
                else:
                    position_list_filtered = position_list
            else:
                position_list_filtered = []
        else:
            position_list_filtered = position_list

        if position_list_found:
            return position_list_filtered
        else:
            position_list_filtered = []
            return position_list_filtered

    def retrieve_all_positions_for_contest_office(self, retrieve_public_positions,
                                                  contest_office_id, contest_office_we_vote_id,
                                                  stance_we_are_looking_for,
                                                  most_recent_only=True, friends_we_vote_id_list=False):
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            position_list = []
            return position_list

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY' which means we want to return
        #  all stances

        if not positive_value_exists(contest_office_id) and not \
                positive_value_exists(contest_office_we_vote_id):
            position_list = []
            return position_list

        # If retrieving PositionForFriends, make sure we have the necessary variables
        if not retrieve_public_positions:
            if not friends_we_vote_id_list:
                position_list = []
                return position_list
            elif type(friends_we_vote_id_list) is list and len(friends_we_vote_id_list) == 0:
                position_list = []
                return position_list

        # Retrieve the support positions for this contest_office_id
        position_list_found = False
        try:
            if retrieve_public_positions:
                # We intentionally do not use 'readonly' here since we need to save based on the results of this query
                position_list_query = PositionEntered.objects.order_by('date_entered')
                retrieve_friends_positions = False
            else:
                # We intentionally do not use 'readonly' here since we need to save based on the results of this query
                position_list_query = PositionForFriends.objects.order_by('date_entered')
                retrieve_friends_positions = True

            if positive_value_exists(contest_office_we_vote_id):
                position_list_query = position_list_query.filter(
                    contest_office_we_vote_id__iexact=contest_office_we_vote_id)
            else:
                position_list_query = position_list_query.filter(contest_office_id=contest_office_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)
                # NOTE: We don't have a special case for
                # "if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE"
                # for contest_office (like we do for candidate_campaign) because we don't have to deal with
                # PERCENT_RATING data with measures
            if retrieve_friends_positions and friends_we_vote_id_list is not False:
                # Find positions from friends. Look for we_vote_id case insensitive.
                we_vote_id_filter = Q()
                for we_vote_id in friends_we_vote_id_list:
                    we_vote_id_filter |= Q(voter_we_vote_id__iexact=we_vote_id)
                    position_list_query = position_list_query.filter(we_vote_id_filter)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)

            # We don't need to filter out the positions that have a percent rating that doesn't match
            # the stance_we_are_looking_for (like we do for candidates)
            position_list = list(position_list_query)
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

    def refresh_cached_position_info_for_organization(self, organization_we_vote_id):
        position_manager = PositionManager()
        public_positions_list = PositionEntered.objects.all()
        public_positions_list = public_positions_list.filter(organization_we_vote_id__iexact=organization_we_vote_id)
        force_update = True
        for one_position in public_positions_list:
            position_manager.refresh_cached_position_info(one_position, force_update)
        return True

    def retrieve_all_positions_for_organization(self, organization_id, organization_we_vote_id,
                                                stance_we_are_looking_for, friends_vs_public,
                                                show_positions_current_voter_election=False,
                                                exclude_positions_current_voter_election=False, voter_device_id='',
                                                google_civic_election_id=0, state_code=''):
        """
        Return a position list with all of the organization's positions.
        Incoming filters include: stance_we_are_looking_for, friends_vs_public, show_positions_current_voter_election,
          exclude_positions_current_voter_election, google_civic_election_id, state_code
        :param organization_id:
        :param organization_we_vote_id:
        :param stance_we_are_looking_for:
        :param friends_vs_public:
        :param show_positions_current_voter_election: Show the positions relevant to the election the voter is
          currently looking at
        :param exclude_positions_current_voter_election: Show positions for all elections the voter is NOT looking at
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
        public_query_exists = True
        if retrieve_public_positions:
            try:
                # We intentionally do not use 'readonly' here since we need to save based on the results of this query
                public_positions_list = PositionEntered.objects.order_by('ballot_item_display_name',
                                                                         '-vote_smart_time_span',
                                                                         '-google_civic_election_id')
                if positive_value_exists(organization_id):
                    public_positions_list = public_positions_list.filter(organization_id=organization_id)
                else:
                    public_positions_list = public_positions_list.filter(
                        organization_we_vote_id__iexact=organization_we_vote_id)
                # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
                if stance_we_are_looking_for != ANY_STANCE:
                    # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                    if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                        public_positions_list = public_positions_list.filter(
                            Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                    else:
                        public_positions_list = public_positions_list.filter(stance=stance_we_are_looking_for)

                google_civic_election_id_local_scope = 0
                if positive_value_exists(show_positions_current_voter_election) \
                        or positive_value_exists(exclude_positions_current_voter_election):
                    results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
                    google_civic_election_id_local_scope = results['google_civic_election_id']

                # We can filter by only one of these
                if positive_value_exists(show_positions_current_voter_election):  # This is the default option
                    if positive_value_exists(google_civic_election_id):
                        # Please note that this option doesn't catch Vote Smart ratings, which are not
                        # linked by google_civic_election_id
                        public_positions_list = public_positions_list.filter(
                            google_civic_election_id=google_civic_election_id)
                    elif positive_value_exists(google_civic_election_id_local_scope):
                        # Limit positions we can retrieve for an org to only the items in this election
                        public_positions_list = public_positions_list.filter(
                            google_civic_election_id=google_civic_election_id_local_scope)
                    else:
                        # If no election is found for the voter, don't show any positions
                        public_positions_list = []
                        public_query_exists = False
                elif positive_value_exists(exclude_positions_current_voter_election):
                    if positive_value_exists(google_civic_election_id):
                        # Please note that this option doesn't catch Vote Smart ratings, which are not
                        # linked by google_civic_election_id
                        public_positions_list = public_positions_list.filter(
                            google_civic_election_id=google_civic_election_id)
                    elif positive_value_exists(google_civic_election_id_local_scope):
                        # Limit positions we can retrieve for an org to only the items NOT in this election
                        public_positions_list = public_positions_list.exclude(
                            google_civic_election_id=google_civic_election_id_local_scope)
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

                # And finally, make sure there is a stance, or text commentary -- exclude cases where there isn't
                if public_query_exists:
                    public_positions_list = public_positions_list.exclude(
                        Q(stance__iexact=NO_STANCE) &
                        (Q(statement_text__isnull=True) | Q(statement_text__exact='')) &
                        (Q(statement_html__isnull=True) | Q(statement_html__exact=''))
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
                    current_voter_we_vote_id = voter.we_vote_id

                # We need organization_we_vote_id, so look it up if only organization_id was passed in
                if not organization_we_vote_id:
                    organization_manager = OrganizationManager()
                    organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(organization_id)

                # Find the Voter id for the organization showing the positions. Organizations that sign in with
                #  their Twitter accounts get a Voter entry, with "voter.linked_organization_we_vote_id" containing
                #  the organizations we_vote_id.
                results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization_we_vote_id)
                organization_voter_local_id = 0
                organization_voter_we_vote_id = ""
                if results['voter_found']:
                    organization_voter = results['voter']
                    organization_voter_local_id = organization_voter.id
                    organization_voter_we_vote_id = organization_voter.we_vote_id

                # Is the viewer a friend of this organization? If NOT, then there is no need to proceed
                voter_is_friend_of_organization = False
                if positive_value_exists(current_voter_we_vote_id) and \
                        organization_voter_we_vote_id.lower() == current_voter_we_vote_id.lower():
                    # If the current viewer is looking at own entry, then show what should be shown to friends
                    voter_is_friend_of_organization = True
                elif positive_value_exists(current_voter_we_vote_id):
                    friend_manager = FriendManager()
                    friend_results = friend_manager.retrieve_friends_we_vote_id_list(current_voter_we_vote_id)
                    if friend_results['friends_we_vote_id_list_found']:
                        friends_we_vote_id_list = friend_results['friends_we_vote_id_list']
                        # Check to see if current voter is in list of friends
                        if organization_voter_we_vote_id in friends_we_vote_id_list:
                            voter_is_friend_of_organization = True

                friends_positions_list = []
                friends_query_exists = True
                if voter_is_friend_of_organization:
                    # If here, then the viewer is a friend with the organization. Look up positions that
                    #  are only shown to friends.
                    friends_positions_list = PositionForFriends.objects.order_by('ballot_item_display_name',
                                                                                 '-vote_smart_time_span',
                                                                                 '-google_civic_election_id')
                    # Get the entries saved by the organization's voter account
                    if positive_value_exists(organization_voter_local_id):
                        friends_positions_list = friends_positions_list.filter(
                            voter_id=organization_voter_local_id)
                    else:
                        friends_positions_list = friends_positions_list.filter(
                            voter_we_vote_id__iexact=organization_voter_we_vote_id)

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
                    google_civic_election_id_local_scope = 0
                    if positive_value_exists(show_positions_current_voter_election) \
                            or positive_value_exists(exclude_positions_current_voter_election):
                        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
                        google_civic_election_id_local_scope = results['google_civic_election_id']

                    # We can filter by only one of these
                    if positive_value_exists(show_positions_current_voter_election):  # This is the default option
                        if positive_value_exists(google_civic_election_id_local_scope):
                            # Limit positions we can retrieve for an org to only the items in this election
                            friends_positions_list = friends_positions_list.filter(
                                google_civic_election_id=google_civic_election_id_local_scope)
                        else:
                            # If no election is found for the voter, don't show any positions
                            friends_positions_list = []
                            friends_query_exists = False
                    elif positive_value_exists(exclude_positions_current_voter_election):
                        if positive_value_exists(google_civic_election_id_local_scope):
                            # Limit positions we can retrieve for an org to only the items NOT in this election
                            friends_positions_list = friends_positions_list.exclude(
                                google_civic_election_id=google_civic_election_id_local_scope)
                        else:
                            # Leave the position_list as is.
                            pass
                    elif positive_value_exists(google_civic_election_id):
                        # Please note that this option doesn't catch Vote Smart ratings (yet), which are not
                        # linked by google_civic_election_id
                        # We are only using this if google_civic_election_id was passed
                        # into retrieve_all_positions_for_organization
                        friends_positions_list = friends_positions_list.filter(
                            google_civic_election_id=google_civic_election_id)
                    elif positive_value_exists(state_code):
                        friends_positions_list = friends_positions_list.filter(state_code__iexact=state_code)

                    if friends_query_exists:
                        # And finally, make sure there is a stance, or text commentary -- exclude cases when there isn't
                        friends_positions_list = friends_positions_list.exclude(
                            Q(stance__iexact=NO_STANCE) &
                            (Q(statement_text__isnull=True) | Q(statement_text__exact='')) &
                            (Q(statement_html__isnull=True) | Q(statement_html__exact=''))
                        )
            except Exception as e:
                handle_record_not_found_exception(e, logger=logger)

        # Merge public positions and "For friends" positions
        public_positions_list = list(public_positions_list)  # Force the query to run
        # Flag all of these entries as "is_public_position = True"
        revised_position_list = []
        for one_position in public_positions_list:
            one_position.is_public_position = True  # Add this value
            revised_position_list.append(one_position)
        public_positions_list = revised_position_list

        friends_positions_list = list(friends_positions_list)  # Force the query to run
        # Flag all of these entries as "is_public_position = False"
        revised_position_list = []
        for one_position in friends_positions_list:
            one_position.is_public_position = False  # Add this value
            revised_position_list.append(one_position)
        friends_positions_list = revised_position_list

        position_list = public_positions_list + friends_positions_list

        # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
        if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
            revised_position_list = []
            for one_position in position_list:
                if stance_we_are_looking_for == SUPPORT:
                    if one_position.stance == PERCENT_RATING:
                        if one_position.is_support_or_positive_rating():
                            revised_position_list.append(one_position)
                    else:
                        revised_position_list.append(one_position)
                elif stance_we_are_looking_for == OPPOSE:
                    if one_position.stance == PERCENT_RATING:
                        if one_position.is_oppose_or_negative_rating():
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

    def retrieve_all_positions_for_voter(self, voter_id=0, voter_we_vote_id='',
                                         stance_we_are_looking_for=ANY_STANCE, friends_vs_public=FRIENDS_AND_PUBLIC,
                                         google_civic_election_id=0, this_election_vs_others='', state_code=''):
        """
        We want the voter's position information for display prior to sign in
        :param voter_id:
        :param voter_we_vote_id:
        :param stance_we_are_looking_for:
        :param voter_we_vote_id:
        :param friends_vs_public:
        :param google_civic_election_id:
        :param this_election_vs_others:
        :param state_code:
        :return:
        """
        if not positive_value_exists(voter_id) and not positive_value_exists(voter_we_vote_id):
            position_list = []
            results = {
                'status':               'MISSING_VOTER_ID',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        # Retrieve all positions for this voter -- if here we know that either voter_id or voter_we_vote_id exist

        if stance_we_are_looking_for not \
                in (ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            position_list = []
            results = {
                'status':               'STANCE_WE_ARE_LOOKING_FOR_NOT_VALID',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        retrieve_friends_positions = friends_vs_public in (FRIENDS_ONLY, FRIENDS_AND_PUBLIC)
        retrieve_public_positions = friends_vs_public in (PUBLIC_ONLY, FRIENDS_AND_PUBLIC)

        # Give priority to retrieve_this_election_only
        retrieve_this_election_only = positive_value_exists(google_civic_election_id) \
            and this_election_vs_others in THIS_ELECTION_ONLY
        retrieve_all_other_elections = positive_value_exists(google_civic_election_id) \
            and not retrieve_this_election_only \
            and this_election_vs_others in ALL_OTHER_ELECTIONS
        one_election_filter_applied = retrieve_this_election_only or retrieve_all_other_elections
        retrieve_all_elections = this_election_vs_others in ALL_ELECTIONS \
            or not one_election_filter_applied

        # Retrieve public positions for this organization
        public_positions_list = []
        friends_positions_list = []
        position_list_found = False

        if retrieve_public_positions:
            ############################
            # Retrieve public positions
            try:
                public_positions_list_query = PositionEntered.objects.all()
                if positive_value_exists(voter_id):
                    public_positions_list_query = public_positions_list_query.filter(voter_id=voter_id)
                elif positive_value_exists(voter_we_vote_id):
                    public_positions_list_query = public_positions_list_query.filter(
                        voter_we_vote_id__iexact=voter_we_vote_id)
                if retrieve_this_election_only:
                    public_positions_list_query = public_positions_list_query.filter(
                        google_civic_election_id=google_civic_election_id)
                elif retrieve_all_other_elections:
                    public_positions_list_query = public_positions_list_query.exclude(
                        google_civic_election_id=google_civic_election_id)
                elif positive_value_exists(state_code):
                    public_positions_list_query = public_positions_list_query.filter(state_code__iexact=state_code)

                # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
                if stance_we_are_looking_for != ANY_STANCE:
                    # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                    if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                        public_positions_list_query = public_positions_list_query.filter(
                            Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                    else:
                        public_positions_list_query = public_positions_list_query.filter(
                            stance=stance_we_are_looking_for)

                # Force the position for the most recent election to show up last
                public_positions_list_query = public_positions_list_query.order_by('google_civic_election_id')
                public_positions_list = list(public_positions_list_query)  # Force the query to run
            except Exception as e:
                position_list = []
                results = {
                    'status':               'VOTER_POSITION_FOR_PUBLIC_SEARCH_FAILED',
                    'success':              False,
                    'position_list_found':  False,
                    'position_list':        position_list,
                }
                return results

        if retrieve_friends_positions:
            ############################
            # Retrieve positions meant for friends only
            try:
                friends_positions_list_query = PositionForFriends.objects.all()
                if positive_value_exists(voter_id):
                    friends_positions_list_query = friends_positions_list_query.filter(voter_id=voter_id)
                elif positive_value_exists(voter_we_vote_id):
                    friends_positions_list_query = friends_positions_list_query.filter(
                        voter_we_vote_id__iexact=voter_we_vote_id)
                if retrieve_this_election_only:
                    friends_positions_list_query = friends_positions_list_query.filter(
                        google_civic_election_id=google_civic_election_id)
                elif retrieve_all_other_elections:
                    friends_positions_list_query = friends_positions_list_query.exclude(
                        google_civic_election_id=google_civic_election_id)
                elif positive_value_exists(state_code):
                    friends_positions_list_query = friends_positions_list_query.filter(state_code__iexact=state_code)

                # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
                if stance_we_are_looking_for != ANY_STANCE:
                    # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                    if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
                        friends_positions_list_query = friends_positions_list_query.filter(
                            Q(stance=stance_we_are_looking_for) | Q(stance=PERCENT_RATING))  # | Q(stance=GRADE_RATING))
                    else:
                        friends_positions_list_query = friends_positions_list_query.filter(
                            stance=stance_we_are_looking_for)

                # Force the position for the most recent election to show up last
                friends_positions_list_query = friends_positions_list_query.order_by('google_civic_election_id')
                friends_positions_list = list(friends_positions_list_query)  # Force the query to run
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
        # Flag all of these entries as "is_public_position = True"
        revised_position_list = []
        for one_position in public_positions_list:
            one_position.is_public_position = True  # Add this value
            revised_position_list.append(one_position)
        public_positions_list = revised_position_list

        # Flag all of these entries as "is_public_position = False"
        revised_position_list = []
        for one_position in friends_positions_list:
            one_position.is_public_position = False  # Add this value
            revised_position_list.append(one_position)
        friends_positions_list = revised_position_list

        position_list = public_positions_list + friends_positions_list

        # Now filter out the positions that have a percent rating that doesn't match the stance_we_are_looking_for
        if stance_we_are_looking_for == SUPPORT or stance_we_are_looking_for == OPPOSE:
            revised_position_list = []
            for one_position in position_list:
                if stance_we_are_looking_for == SUPPORT:
                    if one_position.stance == PERCENT_RATING:
                        if one_position.is_support_or_positive_rating():
                            revised_position_list.append(one_position)
                    else:
                        revised_position_list.append(one_position)
                elif stance_we_are_looking_for == OPPOSE:
                    if one_position.stance == PERCENT_RATING:
                        if one_position.is_oppose_or_negative_rating():
                            revised_position_list.append(one_position)
                    else:
                        revised_position_list.append(one_position)
            position_list = revised_position_list

        if len(position_list):
            position_list_found = True

        if position_list_found:
            enhanced_position_list = []
            for position in position_list:
                # Make sure we have a ballot_item_we_vote_id
                if positive_value_exists(position.candidate_campaign_we_vote_id):
                    position.ballot_item_we_vote_id = position.candidate_campaign_we_vote_id
                elif positive_value_exists(position.contest_measure_we_vote_id):
                    position.ballot_item_we_vote_id = position.contest_measure_we_vote_id
                else:
                    continue

                enhanced_position_list.append(position)

            results = {
                'status':               'VOTER_POSITION_LIST_FOUND',
                'success':              True,
                'position_list_found':  True,
                'position_list':        enhanced_position_list,
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

    def retrieve_all_positions_for_voter_simple(self, voter_id=0, voter_we_vote_id='', google_civic_election_id=0):
        """
        We just want the barest of information.
        :param voter_id:
        :param voter_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        if not positive_value_exists(voter_id) and not positive_value_exists(voter_we_vote_id):
            position_list = []
            results = {
                'status':               'MISSING_VOTER_ID',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        # Retrieve all positions for this voter -- if here we know that either voter_id or voter_we_vote_id exist

        ############################
        # Retrieve public positions
        try:
            public_positions_list_query = PositionEntered.objects.all()
            if positive_value_exists(voter_id):
                public_positions_list_query = public_positions_list_query.filter(voter_id=voter_id)
            elif positive_value_exists(voter_we_vote_id):
                public_positions_list_query = public_positions_list_query.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                public_positions_list_query = public_positions_list_query.filter(
                    google_civic_election_id=google_civic_election_id)
            # Force the position for the most recent election to show up last
            public_positions_list_query = public_positions_list_query.order_by('google_civic_election_id')
            public_positions_list = list(public_positions_list_query)  # Force the query to run
        except Exception as e:
            position_list = []
            results = {
                'status':               'VOTER_POSITION_FOR_PUBLIC_SEARCH_FAILED',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        ############################
        # Retrieve positions meant for friends only
        try:
            friends_positions_list_query = PositionForFriends.objects.all()
            if positive_value_exists(voter_id):
                friends_positions_list_query = friends_positions_list_query.filter(voter_id=voter_id)
            elif positive_value_exists(voter_we_vote_id):
                friends_positions_list_query = friends_positions_list_query.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                friends_positions_list_query = friends_positions_list_query.filter(
                    google_civic_election_id=google_civic_election_id)
            # Force the position for the most recent election to show up last
            friends_positions_list_query = friends_positions_list_query.order_by('google_civic_election_id')
            friends_positions_list = list(friends_positions_list_query)  # Force the query to run
        except Exception as e:
            position_list = []
            results = {
                'status':               'VOTER_POSITION_FOR_FRIENDS_SEARCH_FAILED',
                'success':              False,
                'position_list_found':  False,
                'position_list':        position_list,
            }
            return results

        # Mark these positions as "is_public_position"
        public_positions_list2 = []
        for one_public_position in public_positions_list:
            one_public_position.is_public_position = True
            public_positions_list2.append(one_public_position)

        # Mark these positions as NOT "is_public_position"
        friends_positions_list2 = []
        for one_friends_position in friends_positions_list:
            one_friends_position.is_public_position = False
            friends_positions_list2.append(one_friends_position)

        # Merge public positions and "For friends" positions
        position_list = public_positions_list2 + friends_positions_list2
        position_list_found = len(position_list)

        if position_list_found:
            simple_position_list = []
            for position in position_list:
                # Make sure we have a ballot_item_we_vote_id
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
                    'statement_text':           position.statement_text,
                    'is_public_position':       position.is_public_position,
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
                                            public_only=False, limit_to_organization_we_vote_ids=[]):
        """
        Since we don't have a single way to ask the positions tables for only the positions related to a single
        election, we need to look up the data in a round-about way. We get all candidates and measures in the election,
        then return all positions that are about any of those candidates or measures.
        :param google_civic_election_id:
        :param stance_we_are_looking_for:
        :param public_only: Do we care about public positions? Or friend's only positions?
        :param limit_to_organization_we_vote_ids: Pass in a list of organizations
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

        position_list_found = False
        try:
            if public_only:
                # Only return public positions
                position_list_query = PositionEntered.objects.order_by('date_entered')
            else:
                # Only return PositionForFriends entries
                position_list_query = PositionForFriends.objects.order_by('date_entered')

            position_list_query = position_list_query.filter(google_civic_election_id=google_civic_election_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY" it means we want to not filter down the list
                position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)
            if positive_value_exists(limit_to_organization_we_vote_ids) and len(limit_to_organization_we_vote_ids):
                position_list_query = position_list_query.filter(
                    organization_we_vote_id__in=limit_to_organization_we_vote_ids)
            position_list = list(position_list_query)
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

    def fetch_public_positions_count_for_candidate_campaign(self, candidate_campaign_id,
                                                            candidate_campaign_we_vote_id,
                                                            stance_we_are_looking_for=ANY_STANCE):
        return self.fetch_positions_count_for_candidate_campaign(candidate_campaign_id,
                                                                 candidate_campaign_we_vote_id,
                                                                 stance_we_are_looking_for,
                                                                 PUBLIC_ONLY)

    def fetch_friends_only_positions_count_for_candidate_campaign(self, candidate_campaign_id,
                                                                  candidate_campaign_we_vote_id,
                                                                  stance_we_are_looking_for=ANY_STANCE):
        return self.fetch_positions_count_for_candidate_campaign(candidate_campaign_id,
                                                                 candidate_campaign_we_vote_id,
                                                                 stance_we_are_looking_for,
                                                                 FRIENDS_ONLY)

    @staticmethod
    def fetch_positions_count_for_candidate_campaign(candidate_campaign_id,
                                                     candidate_campaign_we_vote_id,
                                                     stance_we_are_looking_for,
                                                     public_or_private=PUBLIC_ONLY,
                                                     friends_we_vote_id_list=False,
                                                     organizations_followed_we_vote_id_list=False):
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            stance_we_are_looking_for = ANY_STANCE

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(candidate_campaign_id) and not \
                positive_value_exists(candidate_campaign_we_vote_id):
            return 0

        retrieve_friends_positions = False
        retrieve_public_positions = False
        if public_or_private not in(PUBLIC_ONLY, FRIENDS_ONLY):
            public_or_private = PUBLIC_ONLY
        if public_or_private == FRIENDS_ONLY:
            retrieve_friends_positions = True
            position_list_query = PositionForFriends.objects.using('readonly').all()
        else:
            retrieve_public_positions = True
            position_list_query = PositionEntered.objects.using('readonly').all()

        if retrieve_public_positions:
            # If retrieving PositionsEntered, make sure we have the necessary variables
            if type(organizations_followed_we_vote_id_list) is list \
                    and len(organizations_followed_we_vote_id_list) == 0:
                return 0
        else:
            # If retrieving PositionForFriends, make sure we have the necessary variables
            if type(friends_we_vote_id_list) is list and len(friends_we_vote_id_list) == 0:
                return 0

        # Retrieve the support positions for this candidate_campaign_id
        position_count = 0
        try:
            if positive_value_exists(candidate_campaign_id):
                position_list_query = position_list_query.filter(candidate_campaign_id=candidate_campaign_id)
            else:
                position_list_query = position_list_query.filter(
                    candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT:
                    if retrieve_public_positions:
                        # If here, include Vote Smart Ratings
                        position_list_query = position_list_query.filter(
                            Q(stance=stance_we_are_looking_for) |  # Matches "is_support"
                            (Q(stance=PERCENT_RATING) & Q(vote_smart_rating_integer__gte=66))
                        )  # Matches "is_positive_rating"
                    else:
                        # If looking for FRIENDS_ONLY positions, we can ignore Vote Smart data
                        position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)
                elif stance_we_are_looking_for == OPPOSE:
                    if retrieve_public_positions:
                        # If here, include Vote Smart Ratings
                        position_list_query = position_list_query.filter(
                            Q(stance=stance_we_are_looking_for) |  # Matches "is_oppose"
                            (Q(stance=PERCENT_RATING) & Q(vote_smart_rating_integer__lte=33))
                        )  # Matches "is_negative_rating"
                    else:
                        # If looking for FRIENDS_ONLY positions, we can ignore Vote Smart data
                        position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)
                else:
                    position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)

            # Only one of these blocks will be used at a time
            if retrieve_friends_positions and friends_we_vote_id_list is not False:
                # Find positions from friends. Look for we_vote_id case insensitive.
                we_vote_id_filter = Q()
                for we_vote_id in friends_we_vote_id_list:
                    we_vote_id_filter |= Q(voter_we_vote_id__iexact=we_vote_id)
                position_list_query = position_list_query.filter(we_vote_id_filter)
            if retrieve_public_positions and organizations_followed_we_vote_id_list is not False:
                # Find positions from organizations voter follows.
                we_vote_id_filter = Q()
                for we_vote_id in organizations_followed_we_vote_id_list:
                    we_vote_id_filter |= Q(organization_we_vote_id__iexact=we_vote_id)
                position_list_query = position_list_query.filter(we_vote_id_filter)

            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)
            position_list = list(position_list_query)

            position_count = len(position_list)
            # position_count = position_list_query.count()
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        return position_count

    def fetch_public_positions_count_for_contest_office(self, contest_office_id,
                                                        contest_office_we_vote_id,
                                                        stance_we_are_looking_for=ANY_STANCE):
        return self.fetch_positions_count_for_contest_office(contest_office_id,
                                                             contest_office_we_vote_id,
                                                             stance_we_are_looking_for,
                                                             PUBLIC_ONLY)

    def fetch_friends_only_positions_count_for_contest_office(self, contest_office_id,
                                                              contest_office_we_vote_id,
                                                              stance_we_are_looking_for=ANY_STANCE):
        return self.fetch_positions_count_for_contest_office(contest_office_id,
                                                             contest_office_we_vote_id,
                                                             stance_we_are_looking_for,
                                                             FRIENDS_ONLY)

    @staticmethod
    def fetch_positions_count_for_contest_office(contest_office_id,
                                                 contest_office_we_vote_id,
                                                 stance_we_are_looking_for,
                                                 public_or_private=PUBLIC_ONLY):
        if stance_we_are_looking_for not \
                in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
            stance_we_are_looking_for = ANY_STANCE

        # Note that one of the incoming options for stance_we_are_looking_for is 'ANY_STANCE'
        #  which means we want to return all stances

        if not positive_value_exists(contest_office_id) and not \
                positive_value_exists(contest_office_we_vote_id):
            return 0

        if public_or_private not in(PUBLIC_ONLY, FRIENDS_ONLY):
            public_or_private = PUBLIC_ONLY
        if public_or_private == FRIENDS_ONLY:
            position_list_query = PositionForFriends.objects.using('readonly').all()
        else:
            position_list_query = PositionEntered.objects.using('readonly').all()

        # Retrieve the support positions for this contest_office_id
        position_count = 0
        try:
            if positive_value_exists(contest_office_id):
                position_list_query = position_list_query.filter(contest_office_id=contest_office_id)
            else:
                position_list_query = position_list_query.filter(
                    contest_office_we_vote_id__iexact=contest_office_we_vote_id)
            # SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
            if stance_we_are_looking_for != ANY_STANCE:
                # If we passed in the stance "ANY_STANCE" it means we want to not filter down the list
                if stance_we_are_looking_for == SUPPORT:
                    position_list_query = position_list_query.filter(
                        Q(stance=stance_we_are_looking_for) |  # Matches "is_support"
                        (Q(stance=PERCENT_RATING) & Q(vote_smart_rating_integer__gte=66))  # Matches "is_positive_rating"
                    )  # | Q(stance=GRADE_RATING))
                elif stance_we_are_looking_for == OPPOSE:
                    position_list_query = position_list_query.filter(
                        Q(stance=stance_we_are_looking_for) |  # Matches "is_oppose"
                        (Q(stance=PERCENT_RATING) & Q(vote_smart_rating_integer__lte=33))  # Matches "is_negative_rating"
                    )  # | Q(stance=GRADE_RATING))
                else:
                    position_list_query = position_list_query.filter(stance=stance_we_are_looking_for)
            # Limit to positions in the last x years - currently we are not limiting
            # position_list = position_list.filter(election_id=election_id)

            position_count = position_list_query.count()
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
            position_list = PositionEntered.objects.using('readonly').order_by('date_entered')
            if positive_value_exists(contest_measure_id):
                position_list = position_list.filter(contest_measure_id=contest_measure_id)
            else:
                position_list = position_list.filter(
                    contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
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


class PositionManager(models.Model):

    def __unicode__(self):
        return "PositionManager"

    def create_position_for_visibility_change(self, voter_id, office_we_vote_id, candidate_we_vote_id,
                                              measure_we_vote_id, visibility_setting):
        position_we_vote_id = ""
        position_found = False
        google_civic_election_id = 0
        state_code = ''
        one_unique_ballot_item_variable_received = positive_value_exists(office_we_vote_id) or \
            positive_value_exists(candidate_we_vote_id) or \
            positive_value_exists(measure_we_vote_id)
        if visibility_setting in FRIENDS_ONLY:
            position_on_stage_starter = PositionForFriends
            position_on_stage = PositionForFriends()
            is_public_position = False
        else:
            position_on_stage_starter = PositionEntered
            position_on_stage = PositionEntered()
            is_public_position = True

        if not voter_id \
                or not one_unique_ballot_item_variable_received \
                or visibility_setting not in (FRIENDS_ONLY, SHOW_PUBLIC):
            status = "CREATE_POSITION_FOR_VISIBILITY_CHANGE-MISSING_REQUIRED_VARIABLE"
            success = False
            results = {
                'success':              success,
                'status':               status,
                'position_we_vote_id':  "",
                'position':             position_on_stage,
                'position_found':       position_found,
                'is_public_position':   is_public_position
            }
            return results

        problem_with_duplicate = False
        success = False
        status = "CREATE_POSITION_FOR_VISIBILITY_CHANGE"
        try:
            # Check for duplicate in other table
            position_we_vote_id = ""
            organization_id = 0
            organization_we_vote_id = ""
            contest_office_id = 0
            candidate_campaign_id = 0
            contest_measure_id = 0
            retrieve_position_for_friends = not is_public_position
            voter_we_vote_id = ""
            duplicate_results = self.retrieve_position(position_we_vote_id,
                                                       organization_id, organization_we_vote_id, voter_id,
                                                       contest_office_id, candidate_campaign_id, contest_measure_id,
                                                       retrieve_position_for_friends,
                                                       voter_we_vote_id,
                                                       office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)
            if duplicate_results['position_found']:
                problem_with_duplicate = True
                success = False
                status = 'CREATE_POSITION_FOR_VISIBILITY_CHANGE-EXISTING_POSITION_CHECK_FAILED'

        except Exception as e:
            problem_with_duplicate = True
            success = False
            status = 'CREATE_POSITION_FOR_VISIBILITY_CHANGE-EXISTING_POSITION_CHECK_FAILED'

        if problem_with_duplicate:
            results = {
                'success': success,
                'status': status,
                'position_we_vote_id': position_we_vote_id,
                'position': position_on_stage,
                'position_found': position_found,
                'is_public_position': is_public_position
            }
            return results

        # Now that we've checked to see that there isn't an entry from the other table, create a new one
        try:
            # Create new
            ballot_item_display_name = ""
            speaker_display_name = ""

            candidate_campaign_id = None
            if candidate_we_vote_id:
                candidate_campaign_manager = CandidateCampaignManager()
                results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(candidate_we_vote_id)
                if results['candidate_campaign_found']:
                    candidate_campaign = results['candidate_campaign']
                    candidate_campaign_id = candidate_campaign.id
                    google_civic_election_id = candidate_campaign.google_civic_election_id
                    state_code = candidate_campaign.state_code
                    ballot_item_display_name = candidate_campaign.candidate_name

            contest_measure_id = None
            if measure_we_vote_id:
                contest_measure_manager = ContestMeasureManager()
                results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)
                if results['contest_measure_found']:
                    contest_measure = results['contest_measure']
                    contest_measure_id = contest_measure.id
                    google_civic_election_id = contest_measure.google_civic_election_id
                    state_code = contest_measure.state_code
                    ballot_item_display_name = contest_measure.measure_title

            contest_office_id = None
            if office_we_vote_id:
                contest_office_manager = ContestOfficeManager()
                results = contest_office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)
                if results['contest_office_found']:
                    contest_office = results['contest_office']
                    contest_office_id = contest_office.id
                    google_civic_election_id = contest_office.google_civic_election_id
                    state_code = contest_office.state_code
                    ballot_item_display_name = contest_office.office_name

            # In order to show a position publicly we need to tie the position to either organization_we_vote_id,
            # public_figure_we_vote_id or candidate_we_vote_id. For now (2016-8-17) we assume organization
            voter_manager = VoterManager()
            results = voter_manager.retrieve_voter_by_id(voter_id)
            organization_id = 0
            organization_we_vote_id = ""
            voter_we_vote_id = ""
            if results['voter_found']:
                voter = results['voter']
                voter_we_vote_id = voter.we_vote_id
                organization_we_vote_id = voter.linked_organization_we_vote_id
                if positive_value_exists(organization_we_vote_id):
                    # Look up the organization_id
                    organization_manager = OrganizationManager()
                    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                        voter.linked_organization_we_vote_id)
                    if organization_results['organization_found']:
                        organization = organization_results['organization']
                        organization_id = organization.id
                        speaker_display_name = organization.organization_name

            position_on_stage = position_on_stage_starter(
                voter_id=voter_id,
                voter_we_vote_id=voter_we_vote_id,
                candidate_campaign_id=candidate_campaign_id,
                candidate_campaign_we_vote_id=candidate_we_vote_id,
                contest_measure_id=contest_measure_id,
                contest_measure_we_vote_id=measure_we_vote_id,
                contest_office_id=contest_office_id,
                contest_office_we_vote_id=office_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code,
                organization_id=organization_id,
                organization_we_vote_id=organization_we_vote_id,
                ballot_item_display_name=ballot_item_display_name,
                speaker_display_name=speaker_display_name,
            )

            position_on_stage.save()
            position_we_vote_id = position_on_stage.we_vote_id
            position_found = True
            success = True
            status = 'CREATE_POSITION_FOR_VISIBILITY_CHANGE-NEW_POSITION_SAVED'

            if positive_value_exists(organization_id) and positive_value_exists(organization_we_vote_id) \
                    and positive_value_exists(google_civic_election_id):
                voter_guide_manager = VoterGuideManager()
                # Make sure we have a voter guide so others can find
                if not voter_guide_manager.voter_guide_exists(organization_we_vote_id, google_civic_election_id):
                    voter_guide_we_vote_id = ''
                    voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                        voter_guide_we_vote_id, organization_we_vote_id, google_civic_election_id, state_code)

        except Exception as e:
            success = False
            status = 'CREATE_POSITION_FOR_VISIBILITY_CHANGE-NEW_POSITION_COULD_NOT_BE_SAVED'

        results = {
            'success':              success,
            'status':               status,
            'position_we_vote_id':  position_we_vote_id,
            'position':             position_on_stage,
            'position_found':       position_found,
            'is_public_position':   is_public_position
        }
        return results

    def retrieve_organization_candidate_campaign_position(self, organization_id, candidate_campaign_id,
                                                          google_civic_election_id=False, state_code=False):
        """
        Find a position based on the organization_id & candidate_campaign_id
        :param organization_id:
        :param candidate_campaign_id:
        :param google_civic_election_id:
        :param state_code:
        :return:
        """
        organization_we_vote_id = ''
        position_we_vote_id = ''
        voter_id = 0
        office_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        candidate_campaign_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            google_civic_election_id)

    def retrieve_organization_candidate_campaign_position_with_we_vote_id(self, organization_id,
                                                                          candidate_campaign_we_vote_id,
                                                                          google_civic_election_id=False,
                                                                          state_code=False):
        """
        Find a position based on the organization_id & candidate_campaign_we_vote_id
        :param organization_id:
        :param candidate_campaign_we_vote_id:
        :param google_civic_election_id:
        :param state_code:
        :return:
        """
        organization_we_vote_id = ''
        position_we_vote_id = ''
        voter_id = 0
        office_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        candidate_campaign_id = 0
        contest_measure_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            google_civic_election_id)

    def retrieve_organization_contest_measure_position(self, organization_id, contest_measure_id,
                                                       google_civic_election_id=False, state_code=False):
        """
        Find a position based on the organization_id & contest_measure_id
        :param organization_id:
        :param contest_measure_id:
        :param google_civic_election_id:
        :param state_code:
        :return:
        """
        organization_we_vote_id = ''
        position_we_vote_id = ''
        voter_id = 0
        office_id = 0
        candidate_campaign_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        candidate_campaign_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            google_civic_election_id)

    def retrieve_organization_contest_measure_position_with_we_vote_id(self, organization_id,
                                                                       contest_measure_we_vote_id,
                                                                       google_civic_election_id=False,
                                                                       state_code=False):
        """
        Find a position based on the organization_id & contest_measure_we_vote_id
        :param organization_id:
        :param contest_measure_we_vote_id:
        :param google_civic_election_id:
        :param state_code:
        :return:
        """
        organization_we_vote_id = ''
        position_we_vote_id = ''
        voter_id = 0
        office_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        candidate_campaign_id = 0
        candidate_campaign_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id,
            google_civic_election_id)

    def retrieve_voter_contest_office_position(self, voter_id, office_id):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_voter_contest_office_position_with_we_vote_id(self, voter_id, contest_office_we_vote_id):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ""
        candidate_campaign_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_voter_candidate_campaign_position(self, voter_id, candidate_campaign_id):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        contest_measure_id = 0
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_voter_candidate_campaign_position_with_we_vote_id(self, voter_id, candidate_campaign_we_vote_id):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_voter_contest_measure_position(self, voter_id, contest_measure_id):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        candidate_campaign_id = 0
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_voter_contest_measure_position_with_we_vote_id(self, voter_id, contest_measure_we_vote_id):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        candidate_campaign_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def retrieve_position_from_we_vote_id(self, position_we_vote_id):
        organization_id = 0
        organization_we_vote_id = ''
        voter_id = 0
        office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        position_manager = PositionManager()
        return position_manager.retrieve_position_table_unknown(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id)

    def retrieve_position_table_unknown(self, position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
                                        contest_office_id, candidate_campaign_id, contest_measure_id,
                                        voter_we_vote_id='', contest_office_we_vote_id='',
                                        candidate_campaign_we_vote_id='', contest_measure_we_vote_id='',
                                        google_civic_election_id=False, vote_smart_time_span=False):
        # Check public positions first
        retrieve_position_for_friends = False
        results = self.retrieve_position(position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
                                         contest_office_id, candidate_campaign_id, contest_measure_id,
                                         retrieve_position_for_friends,
                                         voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id,
                                         contest_measure_we_vote_id,
                                         google_civic_election_id, vote_smart_time_span)
        if results['position_found']:
            return results

        # If a public position wasn't found, now check for private position
        retrieve_position_for_friends = True
        return self.retrieve_position(position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
                                      contest_office_id, candidate_campaign_id, contest_measure_id,
                                      retrieve_position_for_friends,
                                      voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id,
                                      contest_measure_we_vote_id,
                                      google_civic_election_id, vote_smart_time_span)

    def merge_position_duplicates_voter_candidate_campaign_position(self, voter_id, candidate_campaign_id,
                                                                    retrieve_position_for_friends):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        contest_measure_id = 0
        position_manager = PositionManager()
        return position_manager.merge_position_duplicates(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends)

    def merge_position_duplicates_voter_candidate_campaign_position_with_we_vote_id(
            self, voter_id, candidate_campaign_we_vote_id, retrieve_position_for_friends):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        contest_measure_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.merge_position_duplicates(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def merge_position_duplicates_voter_contest_measure_position(self, voter_id, contest_measure_id,
                                                                 retrieve_position_for_friends):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        candidate_campaign_id = 0
        position_manager = PositionManager()
        return position_manager.merge_position_duplicates(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends)

    def merge_position_duplicates_voter_contest_measure_position_with_we_vote_id(
            self, voter_id, contest_measure_we_vote_id, retrieve_position_for_friends):
        organization_id = 0
        organization_we_vote_id = ''
        position_we_vote_id = ''
        office_id = 0
        candidate_campaign_id = 0
        contest_measure_id = 0
        voter_we_vote_id = ''
        contest_office_we_vote_id = ''
        candidate_campaign_we_vote_id = ''
        position_manager = PositionManager()
        return position_manager.merge_position_duplicates(
            position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
            office_id, candidate_campaign_id, contest_measure_id, retrieve_position_for_friends,
            voter_we_vote_id, contest_office_we_vote_id, candidate_campaign_we_vote_id, contest_measure_we_vote_id
        )

    def merge_position_duplicates(self, position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
                                  contest_office_id, candidate_campaign_id, contest_measure_id,
                                  retrieve_position_for_friends=False,
                                  voter_we_vote_id='', contest_office_we_vote_id='', candidate_campaign_we_vote_id='',
                                  contest_measure_we_vote_id='',
                                  google_civic_election_id=False, state_code=False, vote_smart_time_span=False):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        duplicates_found = False
        status = ""
        success = False
        is_public_position = None
        if retrieve_position_for_friends:
            duplicates_list_starter = PositionForFriends
            duplicates_list = []
            status += "MERGE_POSITION_DUPLICATES-FRIENDS "
        else:
            duplicates_list_starter = PositionEntered
            duplicates_list = []
            status += "MERGE_POSITION_DUPLICATES-PUBLIC "

        if positive_value_exists(organization_we_vote_id) and not positive_value_exists(organization_id):
            # Look up the organization_id
            organization_manager = OrganizationManager()
            organization_id = organization_manager.fetch_organization_id(organization_we_vote_id)

        if positive_value_exists(voter_we_vote_id) and not positive_value_exists(voter_id):
            # Look up the voter_id
            voter_manager = VoterManager()
            voter_id = voter_manager.fetch_local_id_from_we_vote_id(voter_we_vote_id)

        try:
            if positive_value_exists(position_we_vote_id):
                status += "MERGE_POSITION_DUPLICATES_WITH_WE_VOTE_ID "
                duplicates_list = duplicates_list_starter.objects.filter(
                    we_vote_id__iexact=position_we_vote_id)
                duplicates_count = len(duplicates_list)
                duplicates_found = True if duplicates_count > 1 else False
                success = True
            # ###############################
            # Organization
            elif positive_value_exists(organization_id) and positive_value_exists(contest_office_id):
                if positive_value_exists(google_civic_election_id):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_OFFICE_AND_ELECTION "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, contest_office_id=contest_office_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_OFFICE_AND_VOTE_SMART_TIME_SPAN "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, contest_office_id=contest_office_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                else:
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_AND_OFFICE "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, contest_office_id=contest_office_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(candidate_campaign_id):
                if positive_value_exists(google_civic_election_id):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_CANDIDATE_AND_ELECTION "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_CANDIDATE_AND_VOTE_SMART_TIME_SPAN "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                else:
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_AND_CANDIDATE "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(candidate_campaign_we_vote_id):
                if positive_value_exists(google_civic_election_id):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_CANDIDATE_WE_VOTE_ID_AND_ELECTION "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id,
                        candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_CANDIDATE_WE_VOTE_ID_AND_VOTE_SMART_TIME_SPAN "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id,
                        candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                else:
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_AND_CANDIDATE_WE_VOTE_ID "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id,
                        candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_measure_id):
                if positive_value_exists(google_civic_election_id):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_MEASURE_AND_ELECTION "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, contest_measure_id=contest_measure_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_MEASURE_AND_VOTE_SMART_TIME_SPAN "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, contest_measure_id=contest_measure_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                else:
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_AND_MEASURE "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, contest_measure_id=contest_measure_id)
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_measure_we_vote_id):
                if positive_value_exists(google_civic_election_id):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_MEASURE_WE_VOTE_ID_AND_ELECTION "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id,
                        contest_measure_we_vote_id__iexact=contest_measure_we_vote_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_MEASURE_WE_VOTE_ID_AND_VOTE_SMART_TIME_SPAN "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id,
                        contest_measure_we_vote_id__iexact=contest_measure_we_vote_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
                else:
                    status += "MERGE_POSITION_DUPLICATES_WITH_ORG_AND_MEASURE_WE_VOTE_ID "
                    duplicates_list = duplicates_list_starter.objects.filter(
                        organization_id=organization_id, contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
                    duplicates_count = len(duplicates_list)
                    duplicates_found = True if duplicates_count > 1 else False
                    success = True
            # ###############################
            # Voter
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_id):
                status += "MERGE_POSITION_DUPLICATES_WITH_VOTER_AND_OFFICE "
                duplicates_list = duplicates_list_starter.objects.filter(
                    voter_id=voter_id, contest_office_id=contest_office_id)
                duplicates_count = len(duplicates_list)
                duplicates_found = True if duplicates_count > 1 else False
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_we_vote_id):
                status += "MERGE_POSITION_DUPLICATES_WITH_VOTER_AND_OFFICE_WE_VOTE_ID "
                duplicates_list = duplicates_list_starter.objects.filter(
                    voter_id=voter_id, contest_office_we_vote_id__iexact=contest_office_we_vote_id)
                duplicates_count = len(duplicates_list)
                duplicates_found = True if duplicates_count > 1 else False
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_id):
                status += "MERGE_POSITION_DUPLICATES_WITH_VOTER_AND_CANDIDATE "
                duplicates_list = duplicates_list_starter.objects.filter(
                    voter_id=voter_id, candidate_campaign_id=candidate_campaign_id)
                duplicates_count = len(duplicates_list)
                duplicates_found = True if duplicates_count > 1 else False
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_we_vote_id):
                status += "MERGE_POSITION_DUPLICATES_WITH_VOTER_AND_CANDIDATE_WE_VOTE_ID "
                duplicates_list = duplicates_list_starter.objects.filter(
                    voter_id=voter_id, candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
                duplicates_count = len(duplicates_list)
                duplicates_found = True if duplicates_count > 1 else False
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_id):
                status += "MERGE_POSITION_DUPLICATES_WITH_VOTER_AND_MEASURE "
                duplicates_list = duplicates_list_starter.objects.filter(
                    voter_id=voter_id, contest_measure_id=contest_measure_id)
                duplicates_count = len(duplicates_list)
                duplicates_found = True if duplicates_count > 1 else False
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_we_vote_id):
                status += "MERGE_POSITION_DUPLICATES_WITH_VOTER_AND_MEASURE_WE_VOTE_ID "
                duplicates_list = duplicates_list_starter.objects.filter(
                    voter_id=voter_id, contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
                duplicates_count = len(duplicates_list)
                duplicates_found = True if duplicates_count > 1 else False
                success = True
            else:
                status += "MERGE_POSITION_DUPLICATES_INSUFFICIENT_VARIABLES "
        except ObjectDoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status += "MERGE_POSITION_DUPLICATES_NONE_FOUND "
            if retrieve_position_for_friends:
                duplicates_list = []
                is_public_position = False
            else:
                duplicates_list = []
                is_public_position = True

        duplicates_repaired = False
        if duplicates_found:
            first_position = True
            duplicates_repaired = True
            for position in duplicates_list:
                if first_position:
                    position_to_keep = position
                    first_position = False
                    continue
                else:
                    results = self.merge_position_visibility(position_to_keep, position)
                    if results['success']:
                        position_to_keep = results['position']
                    else:
                        duplicates_repaired = False
                        break

        if retrieve_position_for_friends:
            is_public_position = False
        else:
            is_public_position = True

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'duplicates_found':         duplicates_found,
            'duplicates_repaired':      duplicates_repaired,
            'duplicates_list':          duplicates_list,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               state_code,
        }
        return results

    def retrieve_position(self, position_we_vote_id, organization_id, organization_we_vote_id, voter_id,
                          contest_office_id, candidate_campaign_id, contest_measure_id,
                          retrieve_position_for_friends=False,
                          voter_we_vote_id='', contest_office_we_vote_id='', candidate_campaign_we_vote_id='',
                          contest_measure_we_vote_id='',
                          google_civic_election_id=False, vote_smart_time_span=False):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        position_found = False
        status = ""
        success = False
        is_public_position = None
        if retrieve_position_for_friends:
            position_on_stage_starter = PositionForFriends
            position_on_stage = PositionForFriends()
            status += "RETRIEVE_POSITION-FRIENDS "
        else:
            position_on_stage_starter = PositionEntered
            position_on_stage = PositionEntered()
            status += "RETRIEVE_POSITION-PUBLIC "

        if positive_value_exists(organization_we_vote_id) and not positive_value_exists(organization_id):
            # Look up the organization_id
            organization_manager = OrganizationManager()
            organization_id = organization_manager.fetch_organization_id(organization_we_vote_id)

        if positive_value_exists(voter_we_vote_id) and not positive_value_exists(voter_id):
            # Look up the voter_id
            voter_manager = VoterManager()
            voter_id = voter_manager.fetch_local_id_from_we_vote_id(voter_we_vote_id)

        try:
            if positive_value_exists(position_we_vote_id):
                status += "RETRIEVE_POSITION_FOUND_WITH_WE_VOTE_ID "
                position_on_stage = position_on_stage_starter.objects.get(we_vote_id__iexact=position_we_vote_id)
                position_found = True
                success = True
            # ###############################
            # Organization
            elif positive_value_exists(organization_id) and positive_value_exists(contest_office_id):
                if positive_value_exists(google_civic_election_id):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_OFFICE_AND_ELECTION "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_office_id=contest_office_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_OFFICE_AND_VOTE_SMART_TIME_SPAN "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_office_id=contest_office_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                else:
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_OFFICE "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_office_id=contest_office_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(candidate_campaign_id):
                if positive_value_exists(google_civic_election_id):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_CANDIDATE_AND_ELECTION "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_CANDIDATE_AND_VOTE_SMART_TIME_SPAN "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                else:
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_CANDIDATE "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, candidate_campaign_id=candidate_campaign_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(candidate_campaign_we_vote_id):
                if positive_value_exists(google_civic_election_id):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_CANDIDATE_WE_VOTE_ID_AND_ELECTION "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id,
                        candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_CANDIDATE_WE_VOTE_ID_AND_VOTE_SMART_TIME_SPAN "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id,
                        candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                else:
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_CANDIDATE_WE_VOTE_ID "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id,
                        candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_measure_id):
                if positive_value_exists(google_civic_election_id):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_MEASURE_AND_ELECTION "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_measure_id=contest_measure_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_MEASURE_AND_VOTE_SMART_TIME_SPAN "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_measure_id=contest_measure_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                else:
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_MEASURE "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_measure_id=contest_measure_id)
                    position_found = True
                    success = True
            elif positive_value_exists(organization_id) and positive_value_exists(contest_measure_we_vote_id):
                if positive_value_exists(google_civic_election_id):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_MEASURE_WE_VOTE_ID_AND_ELECTION "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_measure_we_vote_id__iexact=contest_measure_we_vote_id,
                        google_civic_election_id=google_civic_election_id)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                elif positive_value_exists(vote_smart_time_span):
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_MEASURE_WE_VOTE_ID_AND_VOTE_SMART_TIME_SPAN "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_measure_we_vote_id__iexact=contest_measure_we_vote_id,
                        vote_smart_time_span__iexact=vote_smart_time_span)
                    # If still here, we found an existing position
                    position_found = True
                    success = True
                else:
                    status += "RETRIEVE_POSITION_FOUND_WITH_ORG_AND_MEASURE_WE_VOTE_ID "
                    position_on_stage = position_on_stage_starter.objects.get(
                        organization_id=organization_id, contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
                    position_found = True
                    success = True
            # ###############################
            # Voter
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_id):
                status += "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_OFFICE "
                position_on_stage = position_on_stage_starter.objects.get(
                    voter_id=voter_id, contest_office_id=contest_office_id)
                position_found = True
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_office_we_vote_id):
                status += "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_OFFICE_WE_VOTE_ID "
                position_on_stage = position_on_stage_starter.objects.get(
                    voter_id=voter_id, contest_office_we_vote_id__iexact=contest_office_we_vote_id)
                position_found = True
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_id):
                status += "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_CANDIDATE "
                position_on_stage = position_on_stage_starter.objects.get(
                    voter_id=voter_id, candidate_campaign_id=candidate_campaign_id)
                position_found = True
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(candidate_campaign_we_vote_id):
                status += "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_CANDIDATE_WE_VOTE_ID "
                position_on_stage = position_on_stage_starter.objects.get(
                    voter_id=voter_id, candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
                position_found = True
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_id):
                status += "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_MEASURE "
                position_on_stage = position_on_stage_starter.objects.get(
                    voter_id=voter_id, contest_measure_id=contest_measure_id)
                position_found = True
                success = True
            elif positive_value_exists(voter_id) and positive_value_exists(contest_measure_we_vote_id):
                status += "RETRIEVE_POSITION_FOUND_WITH_VOTER_AND_MEASURE_WE_VOTE_ID "
                position_on_stage = position_on_stage_starter.objects.get(
                    voter_id=voter_id, contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)
                position_found = True
                success = True
            else:
                status += "RETRIEVE_POSITION_INSUFFICIENT_VARIABLES "
        except MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status += "RETRIEVE_POSITION_MULTIPLE_FOUND "
            if retrieve_position_for_friends:
                position_on_stage = PositionForFriends()
                is_public_position = False
            else:
                position_on_stage = PositionEntered()
                is_public_position = True
        except ObjectDoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_POSITION_NONE_FOUND "
            is_public_position = None
            if retrieve_position_for_friends:
                position_on_stage = PositionForFriends()
                is_public_position = False
            else:
                position_on_stage = PositionEntered()
                is_public_position = True

        if success:
            if retrieve_position_for_friends:
                is_public_position = False
                position_on_stage.is_public_position = is_public_position
            else:
                is_public_position = True
                position_on_stage.is_public_position = is_public_position

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'position_found':           position_found,
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
            'is_public_position':       is_public_position,
            'date_last_changed':        position_on_stage.date_last_changed,
            'date_entered':             position_on_stage.date_entered,
            'google_civic_election_id': google_civic_election_id,
        }
        return results

    def transfer_to_public_position(self, existing_position):
        # Check to make sure existing_position comes from PositionForFriends
        if not existing_position._meta.object_name == "PositionForFriends":
            results = {
                'success':              False,
                'status':               "SWITCH_TO_PUBLIC_POSITION_SUCCESS-NOT_PositionForFriends",
                'position_copied':      False,
                'position_deleted':     False,
                'position':             PositionEntered(),
                'is_public_position':   None,
            }
            return results

        status = ""
        # In order to show a position publicly we need to tie the position to either organization_we_vote_id,
        # public_figure_we_vote_id or candidate_we_vote_id. For now (2016-8-17) we use only organization

        # Heal data: Make sure we have both org id and org we_vote_id
        organization_we_vote_id_missing = positive_value_exists(existing_position.organization_id) \
            and not positive_value_exists(existing_position.organization_we_vote_id)
        organization_id_missing = positive_value_exists(existing_position.organization_we_vote_id) \
            and not positive_value_exists(existing_position.organization_id)
        if organization_id_missing or organization_we_vote_id_missing:
            organization_manager = OrganizationManager()
            # Heal data: Make sure we have both org_id and org_we_vote_id
            if organization_id_missing:
                existing_position.organization_id = organization_manager.fetch_organization_id(
                    existing_position.organization_we_vote_id)
            elif organization_we_vote_id_missing:
                existing_position.organization_we_vote_id = organization_manager.fetch_we_vote_id_from_local_id(
                    existing_position.organization_id)

        # Heal data: Make sure we have both voter_id and voter_we_vote_id
        voter_id_missing = positive_value_exists(existing_position.voter_we_vote_id) \
            and not positive_value_exists(existing_position.voter_id)
        voter_we_vote_id_missing = positive_value_exists(existing_position.voter_id) \
            and not positive_value_exists(existing_position.voter_we_vote_id)
        if voter_id_missing:
            existing_position.voter_id = fetch_voter_id_from_voter_we_vote_id(existing_position.voter_we_vote_id)
        elif voter_we_vote_id_missing:
            existing_position.voter_we_vote_id = fetch_voter_we_vote_id_from_voter_id(existing_position.voter_id)

        # Is there any organization data save with this position yet?
        organization_link_missing = not positive_value_exists(existing_position.organization_we_vote_id)
        if organization_link_missing:
            # If here, there isn't any organization information stored with this position. We need to see if
            #  an organization exists that is linked to this voter, and if so, heal the data
            voter_manager = VoterManager()
            # Look up the voter who owns this position
            if positive_value_exists(existing_position.voter_we_vote_id):
                voter_owner_results = voter_manager.retrieve_voter_by_we_vote_id(existing_position.voter_we_vote_id)
                if voter_owner_results['voter_found']:
                    voter_owner = voter_owner_results['voter']
                    organization_manager = OrganizationManager()
                    if positive_value_exists(voter_owner.linked_organization_we_vote_id):
                        # This voter is linked to an org, so we can bring that data over to save in this position
                        existing_position.organization_we_vote_id = voter_owner.linked_organization_we_vote_id
                        existing_position.organization_id = organization_manager.fetch_organization_id(
                            existing_position.organization_we_vote_id)
                    else:
                        # If here, we need to do some looking to see if an org exists that matches this voter
                        status += "POSITION_SWITCH_TO_PUBLIC_POSITION-LOOK_FOR_ORG"
                        pass
                else:
                    status += "POSITION_SWITCH_TO_PUBLIC_POSITION-VOTER_WE_VOTE_ID_NOT_FOUND"

        # Verify data: We may have in the position org and voter, but they don't match
        # ??? If in doubt, give position to the organization

        # Position could have been from voter friends-only, so we don't have *either* org_id or org_we_vote_id
        # Once they push them live, we need to make sure an organization exists for them
        # voter_manager = VoterManager()
        # ######################
        # CASE 1: It was a friend's only position, and we need to create an org to push it public with
        # if positive_value_exists(existing_position.voter_we_vote_id):
        #     organization_missing = not positive_value_exists(existing_position.organization_id) \
        #                            and not positive_value_exists(existing_position.organization_we_vote_id)
        #     if organization_missing:
        #       pass
        #         Check voter record for linked org
        #             If voter record has link to org, fill the position with the org ids
        #
        #         If no linked_org in voter, check to see if voter's twitter handle wasn't being used by existing org
        #
        #         If twitter handle not used by existing org, create new org
        #
        #
        #             Check that the org isn't already linked to another voter
        #             If not linked,

        # # Heal the data
        # results = voter_manager.retrieve_voter_by_we_vote_id(existing_position.voter_we_vote_id)
        # if results['voter_found']:
        #     voter = results['voter']
        #     # We found this voter from the existing position. Now we must make sure that the voter and
        #     # organization specified by the position all match
        #     if positive_value_exists(voter.linked_organization_we_vote_id) and
        # voter.linked_organization_we_vote_id == existing_position:
        #         if organization_id_missing:
        #             existing_position.organization_we_vote_id = voter.linked_organization_we_vote_id
        #             # Look up the organization_id
        #             existing_position.organization_id = organization_manager.fetch_organization_id(
        #                 voter.linked_organization_we_vote_id)

        # ######################
        # CASE 2: It is an org position, and we need to tie it to a voter

        # ######################
        # Note: We make sure a voter guide exists for this election and organization, in switch_position_visibility

        switch_to_public_position = True
        switch_position_visibility_results = self.switch_position_visibility(
            existing_position, switch_to_public_position)

        results = {
            'success':              switch_position_visibility_results['success'],
            'status':               status + switch_position_visibility_results['status'],
            'position_copied':      switch_position_visibility_results['position_copied'],
            'position_deleted':     switch_position_visibility_results['position_deleted'],
            'position':             switch_position_visibility_results['position'],
            'is_public_position':   switch_position_visibility_results['is_public_position'],
        }
        return results

    def transfer_to_friends_only_position(self, existing_position):
        # Check to make sure existing_position comes from PositionForFriends
        if not existing_position._meta.object_name == "PositionEntered":
            results = {
                'success':              False,
                'status':               "SWITCH_TO_FRIENDS_ONLY_POSITION_SUCCESS-NOT_PositionEntered",
                'position_copied':      False,
                'position_deleted':     False,
                'position':             PositionForFriends(),
                'is_public_position':   None,
            }
            return results

        switch_to_public_position = False
        return self.switch_position_visibility(existing_position, switch_to_public_position)

    def switch_position_visibility(self, existing_position, switch_to_public_position):

        # We assume one does NOT exist in the other table
        position_deleted = False
        if switch_to_public_position:
            new_position_starter = PositionEntered
            new_position = PositionEntered()  # For errors
        else:
            new_position_starter = PositionForFriends
            new_position = PositionForFriends()
        try:
            # Make sure a google_civic_election_id is stored
            if not positive_value_exists(existing_position.google_civic_election_id):
                # We want to retrieve the google_civic_election_id from the ballot item object
                if positive_value_exists(existing_position.candidate_campaign_we_vote_id):
                    candidate_campaign_manager = CandidateCampaignManager()
                    results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                        existing_position.candidate_campaign_we_vote_id)
                    if results['candidate_campaign_found']:
                        candidate_campaign = results['candidate_campaign']
                        existing_position.google_civic_election_id = \
                            candidate_campaign.google_civic_election_id
                        if positive_value_exists(candidate_campaign.state_code):
                            existing_position.state_code = candidate_campaign.state_code
                elif positive_value_exists(existing_position.contest_measure_we_vote_id):
                    contest_measure_manager = ContestMeasureManager()
                    results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                        existing_position.contest_measure_we_vote_id)
                    if results['contest_measure_found']:
                        contest_measure = results['contest_measure']
                        existing_position.google_civic_election_id = contest_measure.google_civic_election_id
                        if positive_value_exists(contest_measure.state_code):
                            existing_position.state_code = contest_measure.state_code
                elif positive_value_exists(existing_position.contest_office_we_vote_id):
                    contest_office_manager = ContestOfficeManager()
                    results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
                        existing_position.contest_office_we_vote_id)
                    if results['contest_office_found']:
                        contest_office = results['contest_office']
                        existing_position.google_civic_election_id = contest_office.google_civic_election_id
                        if positive_value_exists(contest_office.state_code):
                            existing_position.state_code = contest_office.state_code

            new_position = new_position_starter.objects.create(
                we_vote_id=existing_position.we_vote_id,
                date_entered=existing_position.date_entered,
                date_last_changed=existing_position.date_last_changed,
                organization_id=existing_position.organization_id,
                organization_we_vote_id=existing_position.organization_we_vote_id,
                voter_we_vote_id=existing_position.voter_we_vote_id,
                voter_id=existing_position.voter_id,
                google_civic_election_id=existing_position.google_civic_election_id,
                state_code=existing_position.state_code,
                google_civic_candidate_name=existing_position.google_civic_candidate_name,
                tweet_source_id=existing_position.tweet_source_id,
                ballot_item_display_name=existing_position.ballot_item_display_name,
                ballot_item_image_url_https=existing_position.ballot_item_image_url_https,
                ballot_item_twitter_handle=existing_position.ballot_item_twitter_handle,
                contest_office_we_vote_id=existing_position.contest_office_we_vote_id,
                contest_office_id=existing_position.contest_office_id,
                candidate_campaign_we_vote_id=existing_position.candidate_campaign_we_vote_id,
                candidate_campaign_id=existing_position.candidate_campaign_id,
                politician_we_vote_id=existing_position.politician_we_vote_id,
                politician_id=existing_position.politician_id,
                contest_measure_we_vote_id=existing_position.contest_measure_we_vote_id,
                contest_measure_id=existing_position.contest_measure_id,
                google_civic_measure_title=existing_position.google_civic_measure_title,
                stance=existing_position.stance,
                statement_text=existing_position.statement_text,
                statement_html=existing_position.statement_html,
                more_info_url=existing_position.more_info_url,
                from_scraper=existing_position.from_scraper,
                organization_certified=existing_position.organization_certified,
                volunteer_certified=existing_position.volunteer_certified,
                twitter_user_entered_position_id=existing_position.twitter_user_entered_position_id,
                voter_entering_position_id=existing_position.voter_entering_position_id,
                public_figure_we_vote_id=existing_position.public_figure_we_vote_id,
                vote_smart_time_span=existing_position.vote_smart_time_span,
                vote_smart_rating_id=existing_position.vote_smart_rating_id,
                vote_smart_rating=existing_position.vote_smart_rating,
                vote_smart_rating_name=existing_position.vote_smart_rating_name,
                speaker_display_name=existing_position.speaker_display_name,
                speaker_image_url_https=existing_position.speaker_image_url_https,
                speaker_twitter_handle=existing_position.speaker_twitter_handle,
            )
            status = 'SWITCH_POSITION_VISIBILITY_SUCCESS'
            position_copied = True
            success = True
            if switch_to_public_position:
                is_public_position = True

                if positive_value_exists(existing_position.organization_we_vote_id) \
                        and positive_value_exists(existing_position.google_civic_election_id):
                    voter_guide_manager = VoterGuideManager()
                    # Make sure we have a voter guide so others can find
                    if not voter_guide_manager.voter_guide_exists(existing_position.organization_we_vote_id,
                                                                  existing_position.google_civic_election_id):
                        voter_guide_we_vote_id = ''
                        voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                            voter_guide_we_vote_id,
                            existing_position.organization_we_vote_id, existing_position.google_civic_election_id,
                            existing_position.state_code)
            else:
                is_public_position = False
        except Exception as e:
            status = 'SWITCH_POSITION_VISIBILITY_FAILED'
            position_copied = False
            success = False
            if switch_to_public_position:
                is_public_position = False
            else:
                is_public_position = True

        if position_copied:
            # If here, we successfully copied the position and now we need to delete the old one
            try:
                existing_position.delete()
                position_deleted = True
            except Exception as e:
                status = 'SWITCH_POSITION_VISIBILITY_FAILED-UNABLE_TO_DELETE'
                position_deleted = False
                success = False

        results = {
            'success':                  success,
            'status':                   status,
            'position_copied':          position_copied,
            'position_deleted':         position_deleted,
            'position':                 new_position,
            'is_public_position':       is_public_position,
        }
        return results

    def merge_into_public_position(self, position_to_keep):
        status = "MERGE_INTO_PUBLIC_POSITION "
        # Check to see if there is an equivalent position in the PositionForFriends table
        position_we_vote_id = ""
        retrieve_position_for_friends = True
        ballot_item_identifier_found = positive_value_exists(position_to_keep.contest_office_id) \
            or positive_value_exists(position_to_keep.candidate_campaign_id) \
            or positive_value_exists(position_to_keep.contest_measure_id) \
            or positive_value_exists(position_to_keep.contest_office_we_vote_id) \
            or positive_value_exists(position_to_keep.candidate_campaign_we_vote_id) \
            or positive_value_exists(position_to_keep.contest_measure_we_vote_id)
        if ballot_item_identifier_found:
            google_civic_election_id = 0  # Not necessary if there is ballot_item
        else:
            google_civic_election_id = position_to_keep.google_civic_election_id
        results = self.retrieve_position(position_we_vote_id,
                                         position_to_keep.organization_id, position_to_keep.organization_we_vote_id,
                                         position_to_keep.voter_id,
                                         position_to_keep.contest_office_id, position_to_keep.candidate_campaign_id,
                                         position_to_keep.contest_measure_id,
                                         retrieve_position_for_friends,
                                         position_to_keep.voter_we_vote_id, position_to_keep.contest_office_we_vote_id,
                                         position_to_keep.candidate_campaign_we_vote_id,
                                         position_to_keep.contest_measure_we_vote_id,
                                         google_civic_election_id,
                                         position_to_keep.vote_smart_time_span)
        if results['position_found']:
            dead_position = results['position']
        else:
            results = {
                'success': True,
                'status': "MERGE_INTO_PUBLIC_POSITION-NO_NEED",
                'position_merged': False,
                'position_deleted': False,
                'is_public_position': True,
            }
            return results

        merge_position_visibility_results = self.merge_position_visibility(
            position_to_keep, dead_position)

        results = {
            'success': merge_position_visibility_results['success'],
            'status': status + merge_position_visibility_results['status'],
            'position_copied': merge_position_visibility_results['position_copied'],
            'position_deleted': merge_position_visibility_results['position_deleted'],
            'position': merge_position_visibility_results['position'],
            'is_public_position': merge_position_visibility_results['is_public_position'],
        }
        return results

    def merge_into_friends_only_position(self, position_to_keep):
        status = "MERGE_INTO_FRIENDS_ONLY_POSITION "
        # Check to see if there is an equivalent position in the PositionEntered table
        position_we_vote_id = ""
        retrieve_position_for_friends = False
        ballot_item_identifier_found = positive_value_exists(position_to_keep.contest_office_id) \
            or positive_value_exists(position_to_keep.candidate_campaign_id) \
            or positive_value_exists(position_to_keep.contest_measure_id) \
            or positive_value_exists(position_to_keep.contest_office_we_vote_id) \
            or positive_value_exists(position_to_keep.candidate_campaign_we_vote_id) \
            or positive_value_exists(position_to_keep.contest_measure_we_vote_id)
        if ballot_item_identifier_found:
            google_civic_election_id = 0  # Not necessary if there is ballot_item
        else:
            google_civic_election_id = position_to_keep.google_civic_election_id
        results = self.retrieve_position(position_we_vote_id,
                                         position_to_keep.organization_id, position_to_keep.organization_we_vote_id,
                                         position_to_keep.voter_id,
                                         position_to_keep.contest_office_id, position_to_keep.candidate_campaign_id,
                                         position_to_keep.contest_measure_id,
                                         retrieve_position_for_friends,
                                         position_to_keep.voter_we_vote_id, position_to_keep.contest_office_we_vote_id,
                                         position_to_keep.candidate_campaign_we_vote_id,
                                         position_to_keep.contest_measure_we_vote_id,
                                         google_civic_election_id,
                                         position_to_keep.vote_smart_time_span)
        if results['position_found']:
            dead_position = results['position']
        else:
            results = {
                'success': True,
                'status': "MERGE_INTO_FRIENDS_ONLY_POSITION-NO_NEED",
                'position_merged': False,
                'position_deleted': False,
                'is_public_position': True,
            }
            return results

        merge_position_visibility_results = self.merge_position_visibility(
            position_to_keep, dead_position)

        results = {
            'success': merge_position_visibility_results['success'],
            'status': status + merge_position_visibility_results['status'],
            'position_copied': merge_position_visibility_results['position_copied'],
            'position_deleted': merge_position_visibility_results['position_deleted'],
            'position': merge_position_visibility_results['position'],
            'is_public_position': merge_position_visibility_results['is_public_position'],
        }
        return results

    def merge_position_visibility(self, position_to_keep, dead_position):
        # We want to see if dead_position has any values to save before we delete it.
        data_transferred = False
        if not position_to_keep.stance == SUPPORT and not position_to_keep.stance == OPPOSE:
            if dead_position.stance == SUPPORT or dead_position.stance == OPPOSE:
                position_to_keep.stance = dead_position.stance
                data_transferred = True
        if not positive_value_exists(position_to_keep.more_info_url):
            if positive_value_exists(dead_position.more_info_url):
                position_to_keep.more_info_url = dead_position.more_info_url
                data_transferred = True
        if not positive_value_exists(position_to_keep.statement_text):
            if positive_value_exists(dead_position.statement_text):
                position_to_keep.statement_text = dead_position.statement_text
                data_transferred = True
        if not positive_value_exists(position_to_keep.statement_html):
            if positive_value_exists(dead_position.statement_html):
                position_to_keep.statement_html = dead_position.statement_html
                data_transferred = True

        if data_transferred:
            status = "MERGE_POSITION_VISIBILITY-DATA_TRANSFERRED"
        else:
            status = "MERGE_POSITION_VISIBILITY-DATA_NOT_TRANSFERRED"

        # Now delete the dead_position
        try:
            dead_position.delete()
            position_deleted = True
            success = True
        except Exception as e:
            status = 'SWITCH_POSITION_VISIBILITY_FAILED-UNABLE_TO_DELETE'
            position_deleted = False
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'position':                     position_to_keep,
            'position_deleted':             position_deleted,
            'position_data_transferred':    data_transferred,
        }
        return results

    def position_speaker_name_needs_repair(self, position, speaker_display_name):
        """
        See also organization_name_needs_repair
        :param position:
        :param speaker_display_name:
        :return:
        """
        if not hasattr(position, 'speaker_display_name'):
            return False
        if not positive_value_exists(speaker_display_name):
            # Repair not needed if there isn't a speaker_display_name to change to
            return False
        if speaker_display_name.startswith("Voter-") \
                or speaker_display_name.startswith("null") \
                or speaker_display_name is "" \
                or speaker_display_name.startswith("wv"):
            # Repair not needed if the speaker_display_name is a temporary name too
            return False
        if speaker_display_name != position.speaker_display_name:
            # If the position.speaker_display_name doesn't match the incoming speaker_display_name
            return True
        return False

    def toggle_on_voter_support_for_candidate_campaign(self, voter_id, candidate_campaign_id, user_agent_string,
                                                       user_agent_object):
        stance = SUPPORT
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, user_agent_string, user_agent_object)

    def toggle_off_voter_support_for_candidate_campaign(self, voter_id, candidate_campaign_id, user_agent_string,
                                                        user_agent_object):
        stance = NO_STANCE
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, user_agent_string, user_agent_object)

    def toggle_on_voter_oppose_for_candidate_campaign(self, voter_id, candidate_campaign_id, user_agent_string,
                                                      user_agent_object):
        stance = OPPOSE
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, user_agent_string, user_agent_object)

    def toggle_off_voter_oppose_for_candidate_campaign(self, voter_id, candidate_campaign_id, user_agent_string,
                                                       user_agent_object):
        stance = NO_STANCE
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_candidate_campaign(
            voter_id, candidate_campaign_id, stance, user_agent_string, user_agent_object)

    def toggle_on_voter_position_for_candidate_campaign(self, voter_id, candidate_campaign_id, stance,
                                                        user_agent_string, user_agent_object):
        # Does a position from this voter already exist?
        position_manager = PositionManager()
        duplicates_found = False
        status = ""
        results = position_manager.retrieve_voter_candidate_campaign_position(voter_id, candidate_campaign_id)
        is_public_position = results['is_public_position']

        if results['MultipleObjectsReturned']:
            duplicates_found = True
            status += results['status']
            status += 'MultipleObjectsReturned '

            retrieve_position_for_friends = not is_public_position
            merge_results = position_manager.merge_position_duplicates_voter_candidate_campaign_position(
                voter_id, candidate_campaign_id, retrieve_position_for_friends)
            status += merge_results['status']

            if merge_results['duplicates_repaired']:
                duplicates_found = False
                results = position_manager.retrieve_voter_candidate_campaign_position(voter_id, candidate_campaign_id)
                status += results['status']
                is_public_position = results['is_public_position']

                if results['MultipleObjectsReturned']:
                    duplicates_found = True
                    status += 'MultipleObjectsReturned-WORK_NEEDED2 '

        if duplicates_found:
            if is_public_position:
                voter_position_on_stage = PositionEntered()
            else:
                voter_position_on_stage = PositionForFriends()
            results = {
                'status':               status,
                'success':              False,
                'position_we_vote_id':  '',
                'position':             voter_position_on_stage,
            }
            return results

        voter_position_found = results['position_found']
        voter_position_on_stage = results['position']
        contest_measure_id = 0

        return position_manager.toggle_voter_position(voter_id, voter_position_found, voter_position_on_stage,
                                                      stance, candidate_campaign_id, contest_measure_id,
                                                      is_public_position, user_agent_string, user_agent_object)

    def toggle_voter_position(self, voter_id, voter_position_found, voter_position_on_stage, stance,
                              candidate_campaign_id, contest_measure_id, is_public_position, user_agent_string,
                              user_agent_object):
        status = ""
        voter_position_on_stage_found = False
        position_we_vote_id = ''
        voter_we_vote_id = ''
        is_signed_in = False
        google_civic_election_id = 0
        linked_organization_we_vote_id = ""
        candidate_campaign_we_vote_id = ""
        contest_measure_we_vote_id = ""
        voter_manager = VoterManager()
        if voter_position_found:
            # Update this position with new values
            try:
                voter_position_on_stage.stance = stance
                if voter_position_on_stage.candidate_campaign_id:
                    if not positive_value_exists(voter_position_on_stage.candidate_campaign_we_vote_id):
                        # Heal the data, and fill in the candidate_campaign_we_vote_id
                        candidate_campaign_manager = CandidateCampaignManager()
                        results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(
                            candidate_campaign_id)
                        if results['candidate_campaign_found']:
                            candidate_campaign = results['candidate_campaign']
                            candidate_campaign_we_vote_id = candidate_campaign.we_vote_id
                            google_civic_election_id = candidate_campaign.google_civic_election_id
                            voter_position_on_stage.candidate_campaign_we_vote_id = candidate_campaign.we_vote_id
                            voter_position_on_stage.google_civic_election_id = \
                                candidate_campaign.google_civic_election_id
                            voter_position_on_stage.state_code = candidate_campaign.state_code
                            voter_position_on_stage.ballot_item_display_name = candidate_campaign.candidate_name
                    else:
                        candidate_campaign_we_vote_id = voter_position_on_stage.candidate_campaign_we_vote_id
                        google_civic_election_id = voter_position_on_stage.google_civic_election_id

                if voter_position_on_stage.contest_measure_id:
                    if not positive_value_exists(voter_position_on_stage.contest_measure_we_vote_id):
                        # Heal the data, and fill in the contest_measure_we_vote_id
                        contest_measure_manager = ContestMeasureManager()
                        results = contest_measure_manager.retrieve_contest_measure_from_id(contest_measure_id)
                        if results['contest_measure_found']:
                            contest_measure = results['contest_measure']
                            contest_measure_we_vote_id = contest_measure.we_vote_id
                            google_civic_election_id = contest_measure.google_civic_election_id
                            voter_position_on_stage.contest_measure_we_vote_id = contest_measure.we_vote_id
                            voter_position_on_stage.google_civic_election_id = contest_measure.google_civic_election_id
                            voter_position_on_stage.state_code = contest_measure.state_code
                            voter_position_on_stage.ballot_item_display_name = contest_measure.measure_title
                    else:
                        contest_measure_we_vote_id = voter_position_on_stage.contest_measure_we_vote_id
                        google_civic_election_id = voter_position_on_stage.google_civic_election_id

                results = voter_manager.retrieve_voter_by_id(voter_id)
                if results['voter_found']:
                    voter = results['voter']
                    voter_we_vote_id = voter.we_vote_id
                    voter_manager.update_voter_by_object(voter, data_to_preserve=True)
                    is_signed_in = voter.is_signed_in()
                    linked_organization_we_vote_id = voter.linked_organization_we_vote_id
                    # Heal the data: Make sure we have a voter_we_vote_id
                    voter_position_on_stage.voter_we_vote_id = voter_we_vote_id
                    # Heal the data
                    if not positive_value_exists(linked_organization_we_vote_id):
                        organization_manager = OrganizationManager()
                        repair_results = organization_manager.repair_missing_linked_organization_we_vote_id(voter)
                        status += repair_results['status']
                        if repair_results['voter_repaired']:
                            voter = repair_results['voter']
                            linked_organization_we_vote_id = voter.linked_organization_we_vote_id
                    if positive_value_exists(linked_organization_we_vote_id):
                        voter_position_on_stage.organization_we_vote_id = linked_organization_we_vote_id
                        # Look up the organization_id
                        organization_manager = OrganizationManager()
                        organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                            linked_organization_we_vote_id)
                        if organization_results['organization_found']:
                            organization = organization_results['organization']
                            organization_id = organization.id
                            speaker_display_name = organization.organization_name

                            voter_position_on_stage.speaker_display_name = speaker_display_name
                            voter_position_on_stage.organization_id = organization_id

                voter_position_on_stage.save()
                position_we_vote_id = voter_position_on_stage.we_vote_id
                voter_position_on_stage_found = True
                status = 'STANCE_UPDATED'
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                status = 'STANCE_COULD_NOT_BE_UPDATED'
        else:
            try:
                # Create new
                candidate_campaign_we_vote_id = ""
                google_civic_election_id = 0
                state_code = ''
                ballot_item_display_name = ""
                if candidate_campaign_id:
                    candidate_campaign_manager = CandidateCampaignManager()
                    results = candidate_campaign_manager.retrieve_candidate_campaign_from_id(
                        candidate_campaign_id)
                    if results['candidate_campaign_found']:
                        candidate_campaign = results['candidate_campaign']
                        candidate_campaign_we_vote_id = candidate_campaign.we_vote_id
                        google_civic_election_id = candidate_campaign.google_civic_election_id
                        state_code = candidate_campaign.state_code
                        ballot_item_display_name = candidate_campaign.candidate_name

                contest_measure_we_vote_id = ""
                if contest_measure_id:
                    contest_measure_manager = ContestMeasureManager()
                    results = contest_measure_manager.retrieve_contest_measure_from_id(contest_measure_id)
                    if results['contest_measure_found']:
                        contest_measure = results['contest_measure']
                        contest_measure_we_vote_id = contest_measure.we_vote_id
                        google_civic_election_id = contest_measure.google_civic_election_id
                        state_code = contest_measure.state_code
                        ballot_item_display_name = contest_measure.measure_title

                # In order to show a position publicly we need to tie the position to either organization_we_vote_id,
                # public_figure_we_vote_id or candidate_we_vote_id. For now (2016-8-17) we assume organization
                results = voter_manager.retrieve_voter_by_id(voter_id)
                organization_id = 0
                linked_organization_we_vote_id = ""
                voter_we_vote_id = ""
                speaker_display_name = ""
                if results['voter_found']:
                    voter = results['voter']
                    voter_we_vote_id = voter.we_vote_id
                    voter_manager.update_voter_by_object(voter, data_to_preserve=True)
                    is_signed_in = voter.is_signed_in()
                    linked_organization_we_vote_id = voter.linked_organization_we_vote_id
                    # Heal the data
                    if not positive_value_exists(linked_organization_we_vote_id):
                        organization_manager = OrganizationManager()
                        repair_results = organization_manager.repair_missing_linked_organization_we_vote_id(voter)
                        status += repair_results['status']
                        if repair_results['voter_repaired']:
                            voter = repair_results['voter']
                            linked_organization_we_vote_id = voter.linked_organization_we_vote_id
                    if positive_value_exists(linked_organization_we_vote_id):
                        # Look up the organization_id
                        organization_manager = OrganizationManager()
                        organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                            voter.linked_organization_we_vote_id)
                        if organization_results['organization_found']:
                            organization = organization_results['organization']
                            organization_id = organization.id
                            speaker_display_name = organization.organization_name

                if is_public_position:
                    voter_position_on_stage = PositionEntered(
                        voter_id=voter_id,
                        voter_we_vote_id=voter_we_vote_id,
                        candidate_campaign_id=candidate_campaign_id,
                        candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                        contest_measure_id=contest_measure_id,
                        contest_measure_we_vote_id=contest_measure_we_vote_id,
                        stance=stance,
                        google_civic_election_id=google_civic_election_id,
                        state_code=state_code,
                        organization_id=organization_id,
                        organization_we_vote_id=linked_organization_we_vote_id,
                        ballot_item_display_name=ballot_item_display_name,
                        speaker_display_name=speaker_display_name,
                    )
                else:
                    voter_position_on_stage = PositionForFriends(
                        voter_id=voter_id,
                        voter_we_vote_id=voter_we_vote_id,
                        candidate_campaign_id=candidate_campaign_id,
                        candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                        contest_measure_id=contest_measure_id,
                        contest_measure_we_vote_id=contest_measure_we_vote_id,
                        stance=stance,
                        google_civic_election_id=google_civic_election_id,
                        state_code=state_code,
                        organization_id=organization_id,
                        organization_we_vote_id=linked_organization_we_vote_id,
                        ballot_item_display_name=ballot_item_display_name,
                        speaker_display_name=speaker_display_name,
                    )

                voter_position_on_stage.save()
                position_we_vote_id = voter_position_on_stage.we_vote_id
                voter_position_on_stage_found = True
                status = 'NEW_STANCE_SAVED'
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                status = 'NEW_STANCE_COULD_NOT_BE_SAVED'

        if voter_position_on_stage_found:
            # If here we need to make sure a voter guide exists
            if positive_value_exists(linked_organization_we_vote_id) \
                    and positive_value_exists(google_civic_election_id):
                voter_guide_manager = VoterGuideManager()
                if not voter_guide_manager.voter_guide_exists(linked_organization_we_vote_id, google_civic_election_id):
                    # Create voter guide
                    voter_guide_we_vote_id = ""
                    results = voter_guide_manager.update_or_create_organization_voter_guide_by_election_id(
                        voter_guide_we_vote_id, linked_organization_we_vote_id, google_civic_election_id)
            # If here, we are storing an analytics entry
            state_code = ''
            organization_id_temp = 0
            organization_we_vote_id_temp = ""  # Maybe we should record organization_we_vote_id?
            if positive_value_exists(candidate_campaign_we_vote_id):
                ballot_item_we_vote_id = candidate_campaign_we_vote_id
            elif positive_value_exists(contest_measure_we_vote_id):
                ballot_item_we_vote_id = contest_measure_we_vote_id
            else:
                ballot_item_we_vote_id = ""
            is_bot = user_agent_object.is_bot or robot_detection.is_robot(user_agent_string)
            analytics_manager = AnalyticsManager()
            analytics_results = analytics_manager.save_action(
                ACTION_POSITION_TAKEN, voter_we_vote_id, voter_id, is_signed_in, state_code,
                organization_we_vote_id_temp, organization_id_temp,
                google_civic_election_id, user_agent_string=user_agent_string, is_bot=is_bot,
                is_mobile=user_agent_object.is_mobile, is_desktop=user_agent_object.is_pc,
                is_tablet=user_agent_object.is_tablet, ballot_item_we_vote_id=ballot_item_we_vote_id)

        results = {
            'status':               status,
            'success':              True if voter_position_on_stage_found else False,
            'position_we_vote_id':  position_we_vote_id,
            'position':             voter_position_on_stage,
        }
        return results

    def toggle_on_voter_support_for_contest_measure(self, voter_id, contest_measure_id,
                                                    user_agent_string, user_agent_object):
        stance = SUPPORT
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, user_agent_string, user_agent_object)

    def toggle_off_voter_support_for_contest_measure(self, voter_id, contest_measure_id,
                                                     user_agent_string, user_agent_object):
        stance = NO_STANCE
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, user_agent_string, user_agent_object)

    def toggle_on_voter_oppose_for_contest_measure(self, voter_id, contest_measure_id,
                                                   user_agent_string, user_agent_object):
        stance = OPPOSE
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, user_agent_string, user_agent_object)

    def toggle_off_voter_oppose_for_contest_measure(self, voter_id, contest_measure_id,
                                                    user_agent_string, user_agent_object):
        stance = NO_STANCE
        position_manager = PositionManager()
        return position_manager.toggle_on_voter_position_for_contest_measure(
            voter_id, contest_measure_id, stance, user_agent_string, user_agent_object)

    def toggle_on_voter_position_for_contest_measure(self, voter_id, contest_measure_id, stance,
                                                     user_agent_string, user_agent_object):
        # Does a position from this voter already exist?
        position_manager = PositionManager()
        duplicates_found = False
        status = ""
        results = position_manager.retrieve_voter_contest_measure_position(voter_id, contest_measure_id)

        is_public_position = results['is_public_position']

        if results['MultipleObjectsReturned']:
            status += results['status']
            status += 'MultipleObjectsReturned-WORK_NEEDED '

            retrieve_position_for_friends = not is_public_position
            merge_results = position_manager.merge_position_duplicates_voter_contest_measure_position(
                voter_id, contest_measure_id, retrieve_position_for_friends)
            status += merge_results['status']

            if merge_results['duplicates_repaired']:
                duplicates_found = False
                results = position_manager.retrieve_voter_contest_measure_position(voter_id, contest_measure_id)
                status += results['status']
                is_public_position = results['is_public_position']

                if results['MultipleObjectsReturned']:
                    duplicates_found = True
                    status += 'MultipleObjectsReturned-WORK_NEEDED2 '

        if duplicates_found:
            if is_public_position:
                voter_position_on_stage = PositionEntered()
            else:
                voter_position_on_stage = PositionForFriends()
            results = {
                'status':               status,
                'success':              False,
                'position_we_vote_id':  '',
                'position':             voter_position_on_stage,
            }
            return results

        voter_position_found = results['position_found']
        voter_position_on_stage = results['position']
        candidate_campaign_id = 0

        return position_manager.toggle_voter_position(voter_id, voter_position_found, voter_position_on_stage,
                                                      stance, candidate_campaign_id, contest_measure_id,
                                                      is_public_position, user_agent_string, user_agent_object)

    def update_or_create_position_comment(self, position_we_vote_id, voter_id, voter_we_vote_id,
                                          office_we_vote_id, candidate_we_vote_id, measure_we_vote_id,
                                          statement_text, statement_html):
        voter_position_found = False
        is_public_position = False
        problem_with_duplicate_in_same_table = False
        status = ""

        # Set this in case of error
        voter_position_on_stage = PositionForFriends()
        if positive_value_exists(position_we_vote_id):
            # Retrieve the position this way
            pass
        else:
            if not positive_value_exists(voter_id):
                voter_id = fetch_voter_id_from_voter_we_vote_id(voter_we_vote_id)

            if positive_value_exists(candidate_we_vote_id):
                results = self.retrieve_voter_candidate_campaign_position_with_we_vote_id(
                    voter_id, candidate_we_vote_id)
                is_public_position = results['is_public_position']
                if results['position_found']:
                    voter_position_found = True
                    voter_position_on_stage = results['position']
                elif results['MultipleObjectsReturned']:
                    problem_with_duplicate_in_same_table = True
                    status += "UPDATE_OR_CREATE_POSITION_COMMENT-MultipleObjectsReturned-CANDIDATE "

                    retrieve_position_for_friends = not is_public_position
                    merge_results = self.merge_position_duplicates_voter_candidate_campaign_position_with_we_vote_id(
                        voter_id, candidate_we_vote_id, retrieve_position_for_friends)
                    status += merge_results['status']

                    if merge_results['duplicates_repaired']:
                        problem_with_duplicate_in_same_table = False
                        results = self.retrieve_voter_candidate_campaign_position_with_we_vote_id(
                            voter_id, candidate_we_vote_id)
                        status += results['status']
                        is_public_position = results['is_public_position']

                        if results['MultipleObjectsReturned']:
                            problem_with_duplicate_in_same_table = True
                            status += 'MultipleObjectsReturned-WORK_NEEDED2 '
            elif positive_value_exists(office_we_vote_id):
                # TODO
                pass
            elif positive_value_exists(measure_we_vote_id):
                results = self.retrieve_voter_contest_measure_position_with_we_vote_id(
                    voter_id, measure_we_vote_id)
                is_public_position = results['is_public_position']
                if results['position_found']:
                    voter_position_found = True
                    voter_position_on_stage = results['position']
                elif results['MultipleObjectsReturned']:
                    problem_with_duplicate_in_same_table = True
                    status += "UPDATE_OR_CREATE_POSITION_COMMENT-MultipleObjectsReturned-MEASURE "
                    # merge_position_duplicates_voter_contest_measure_position_with_we_vote_id

                    retrieve_position_for_friends = not is_public_position
                    merge_results = self.merge_position_duplicates_voter_contest_measure_position_with_we_vote_id(
                        voter_id, measure_we_vote_id, retrieve_position_for_friends)
                    status += merge_results['status']

                    if merge_results['duplicates_repaired']:
                        problem_with_duplicate_in_same_table = False
                        results = self.retrieve_voter_contest_measure_position_with_we_vote_id(
                            voter_id, measure_we_vote_id)
                        status += results['status']
                        is_public_position = results['is_public_position']

                        if results['MultipleObjectsReturned']:
                            problem_with_duplicate_in_same_table = True
                            status += 'MultipleObjectsReturned-WORK_NEEDED3 '

        voter_position_on_stage_found = False
        position_we_vote_id = ''
        if problem_with_duplicate_in_same_table:
            results = {
                'success':              False,
                'status':               status,
                'position_we_vote_id':  position_we_vote_id,
                'position':             voter_position_on_stage,
                'position_found':       voter_position_on_stage_found,
                'is_public_position':   is_public_position,
            }
            return results
        elif voter_position_found:
            problem_with_duplicate = False
            success = False
            status = "UPDATE_OR_CREATE_POSITION_COMMENT-CHECKING_FOR_DUPLICATE"
            try:
                # Check for duplicate in other table
                position_we_vote_id = ""
                organization_id = 0
                organization_we_vote_id = ""
                contest_office_id = 0
                candidate_campaign_id = 0
                contest_measure_id = 0
                retrieve_position_for_friends = True if is_public_position else False  # Get the opposite
                voter_we_vote_id = ""
                duplicate_results = self.retrieve_position(position_we_vote_id,
                                                           organization_id, organization_we_vote_id, voter_id,
                                                           contest_office_id, candidate_campaign_id, contest_measure_id,
                                                           retrieve_position_for_friends,
                                                           voter_we_vote_id,
                                                           office_we_vote_id, candidate_we_vote_id, measure_we_vote_id)
                if duplicate_results['position_found']:
                    problem_with_duplicate = True
                    success = False
                    status = 'UPDATE_OR_CREATE_POSITION_COMMENT-EXISTING_POSITION_CHECK_FAILED'

            except Exception as e:
                problem_with_duplicate = True
                success = False
                status = 'UPDATE_OR_CREATE_POSITION_COMMENT-EXISTING_POSITION_CHECK_FAILED-EXCEPTION'

            if problem_with_duplicate:
                results = {
                    'success': success,
                    'status': status,
                    'position_we_vote_id': position_we_vote_id,
                    'position': voter_position_on_stage,
                    'position_found': voter_position_found,
                    'is_public_position': is_public_position
                }
                return results

            # Update this position with new values
            try:
                voter_position_on_stage.statement_text = statement_text

                # Make sure a google_civic_election_id is stored
                if not positive_value_exists(voter_position_on_stage.google_civic_election_id):
                    # We want to retrieve the google_civic_election_id from the ballot item object
                    if positive_value_exists(voter_position_on_stage.candidate_campaign_we_vote_id):
                        candidate_campaign_manager = CandidateCampaignManager()
                        results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                            voter_position_on_stage.candidate_campaign_we_vote_id)
                        if results['candidate_campaign_found']:
                            candidate_campaign = results['candidate_campaign']
                            voter_position_on_stage.google_civic_election_id = \
                                candidate_campaign.google_civic_election_id
                            if positive_value_exists(candidate_campaign.state_code):
                                voter_position_on_stage.state_code = candidate_campaign.state_code

                    elif positive_value_exists(voter_position_on_stage.contest_measure_we_vote_id):
                        contest_measure_manager = ContestMeasureManager()
                        results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                            voter_position_on_stage.contest_measure_we_vote_id)
                        if results['contest_measure_found']:
                            contest_measure = results['contest_measure']
                            voter_position_on_stage.google_civic_election_id = contest_measure.google_civic_election_id
                            if positive_value_exists(contest_measure.state_code):
                                voter_position_on_stage.state_code = contest_measure.state_code
                    elif positive_value_exists(voter_position_on_stage.contest_office_we_vote_id):
                        contest_office_manager = ContestOfficeManager()
                        results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
                            voter_position_on_stage.contest_office_we_vote_id)
                        if results['contest_office_found']:
                            contest_office = results['contest_office']
                            voter_position_on_stage.google_civic_election_id = contest_office.google_civic_election_id
                            if positive_value_exists(contest_office.state_code):
                                voter_position_on_stage.state_code = contest_office.state_code

                if voter_position_on_stage.candidate_campaign_we_vote_id:
                    if not positive_value_exists(voter_position_on_stage.candidate_campaign_id):
                        # Heal the data, and fill in the candidate_campaign_id
                        candidate_campaign_manager = CandidateCampaignManager()
                        voter_position_on_stage.candidate_campaign_id = \
                            candidate_campaign_manager.fetch_candidate_campaign_id_from_we_vote_id(
                                voter_position_on_stage.candidate_campaign_we_vote_id)
                elif voter_position_on_stage.contest_measure_we_vote_id:
                    if not positive_value_exists(voter_position_on_stage.contest_measure_id):
                        # Heal the data, and fill in the contest_measure_id
                        contest_measure_manager = ContestMeasureManager()
                        voter_position_on_stage.contest_measure_id = \
                            contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(
                                voter_position_on_stage.contest_measure_we_vote_id)
                if not positive_value_exists(voter_position_on_stage.voter_we_vote_id):
                    # Heal the data: Make sure we have a voter_we_vote_id
                    voter_position_on_stage.voter_we_vote_id = fetch_voter_we_vote_id_from_voter_id(voter_id)

                voter_position_on_stage.save()
                position_we_vote_id = voter_position_on_stage.we_vote_id
                voter_position_on_stage_found = True
                status = 'POSITION_COMMENT_UPDATED'
            except Exception as e:
                status = 'POSITION_COMMENT_COULD_NOT_BE_UPDATED'
        else:
            try:
                # Create new
                candidate_campaign_id = None
                google_civic_election_id = 0
                state_code = ''
                ballot_item_display_name = ""
                speaker_display_name = ""
                if candidate_we_vote_id:
                    candidate_campaign_manager = CandidateCampaignManager()
                    results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                        candidate_we_vote_id)
                    if results['candidate_campaign_found']:
                        candidate_campaign = results['candidate_campaign']
                        candidate_campaign_id = candidate_campaign.id
                        google_civic_election_id = candidate_campaign.google_civic_election_id
                        state_code = candidate_campaign.state_code
                        ballot_item_display_name = candidate_campaign.candidate_name

                contest_measure_id = None
                if measure_we_vote_id:
                    contest_measure_manager = ContestMeasureManager()
                    results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)
                    if results['contest_measure_found']:
                        contest_measure = results['contest_measure']
                        contest_measure_id = contest_measure.id
                        google_civic_election_id = contest_measure.google_civic_election_id
                        state_code = contest_measure.state_code
                        ballot_item_display_name = contest_measure.measure_title

                # In order to show a position publicly we need to tie the position to either organization_we_vote_id,
                # public_figure_we_vote_id or candidate_we_vote_id. For now (2016-8-17) we assume organization
                voter_manager = VoterManager()
                results = voter_manager.retrieve_voter_by_id(voter_id)
                organization_id = 0
                organization_we_vote_id = ""
                voter_we_vote_id = ""
                if results['voter_found']:
                    voter = results['voter']
                    voter_we_vote_id = voter.we_vote_id
                    organization_we_vote_id = voter.linked_organization_we_vote_id
                    if positive_value_exists(organization_we_vote_id):
                        # Look up the organization_id
                        organization_manager = OrganizationManager()
                        organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                            voter.linked_organization_we_vote_id)
                        if organization_results['organization_found']:
                            organization = organization_results['organization']
                            organization_id = organization.id
                            speaker_display_name = organization.organization_name

                # Always default to Friends only
                voter_position_on_stage = PositionForFriends(
                    voter_id=voter_id,
                    voter_we_vote_id=voter_we_vote_id,
                    candidate_campaign_id=candidate_campaign_id,
                    candidate_campaign_we_vote_id=candidate_we_vote_id,
                    contest_measure_id=contest_measure_id,
                    contest_measure_we_vote_id=measure_we_vote_id,
                    stance=NO_STANCE,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    organization_id=organization_id,
                    organization_we_vote_id=organization_we_vote_id,
                    statement_text=statement_text,
                    ballot_item_display_name=ballot_item_display_name,
                    speaker_display_name=speaker_display_name,
                )

                voter_position_on_stage.save()
                position_we_vote_id = voter_position_on_stage.we_vote_id
                voter_position_on_stage_found = True
                is_public_position = False
                status = 'NEW_POSITION_COMMENT_SAVED'
            except Exception as e:
                status = 'NEW_POSITION_COMMENT_COULD_NOT_BE_SAVED'

        results = {
            'status':               status,
            'success':              True if voter_position_on_stage_found else False,
            'position_we_vote_id':  position_we_vote_id,
            'position':             voter_position_on_stage,
            'is_public_position':   is_public_position
        }
        return results

    def update_position_image_urls_from_candidate(self, position_object, candidate_campaign):
        """
        Update position_object with candidate image urls
        :param position_object:
        :param candidate_campaign:
        :return:
        """
        values_changed = False
        if positive_value_exists(candidate_campaign.candidate_photo_url()) and \
                position_object.ballot_item_image_url_https != candidate_campaign.candidate_photo_url():
            position_object.ballot_item_image_url_https = candidate_campaign.candidate_photo_url()
            values_changed = True
        if positive_value_exists(candidate_campaign.we_vote_hosted_profile_image_url_large) and \
                position_object.ballot_item_image_url_https_large != \
                candidate_campaign.we_vote_hosted_profile_image_url_large:
            position_object.ballot_item_image_url_https_large = \
                candidate_campaign.we_vote_hosted_profile_image_url_large
            values_changed = True
        if positive_value_exists(candidate_campaign.we_vote_hosted_profile_image_url_medium) and \
            position_object.ballot_item_image_url_https_medium != \
                candidate_campaign.we_vote_hosted_profile_image_url_medium:
            position_object.ballot_item_image_url_https_medium = \
                candidate_campaign.we_vote_hosted_profile_image_url_medium
            values_changed = True
        if positive_value_exists(candidate_campaign.we_vote_hosted_profile_image_url_tiny) and \
                position_object.ballot_item_image_url_https_tiny != \
                candidate_campaign.we_vote_hosted_profile_image_url_tiny:
            position_object.ballot_item_image_url_https_tiny = candidate_campaign.we_vote_hosted_profile_image_url_tiny
            values_changed = True
        if values_changed:
            try:
                position_object.save()
                success = True
                status = "POSITION_OBJECT_SAVED"
            except Exception as e:
                success = False
                status = 'POSITION_OBJECT_COULD_NOT_BE_SAVED'

        else:
            success = True
            status = "NO_CHANGES_SAVED_TO_POSITION_IMAGE_URLS"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    def update_position_image_urls_from_organization(self, position_object, organization):
        """
        Update position_object with organization image urls
        :param position_object:
        :param organization:
        :return:
        """
        values_changed = False
        if positive_value_exists(organization.organization_photo_url()) and \
                position_object.speaker_image_url_https != organization.organization_photo_url():
            position_object.speaker_image_url_https = organization.organization_photo_url()
            values_changed = True
        if positive_value_exists(organization.we_vote_hosted_profile_image_url_large) and \
                position_object.speaker_image_url_https_large != organization.we_vote_hosted_profile_image_url_large:
            position_object.speaker_image_url_https_large = organization.we_vote_hosted_profile_image_url_large
            values_changed = True
        if positive_value_exists(organization.we_vote_hosted_profile_image_url_medium) and \
                position_object.speaker_image_url_https_medium != organization.we_vote_hosted_profile_image_url_medium:
            position_object.speaker_image_url_https_medium = organization.we_vote_hosted_profile_image_url_medium
            values_changed = True
        if positive_value_exists(organization.we_vote_hosted_profile_image_url_tiny) and \
                position_object.speaker_image_url_https_tiny != organization.we_vote_hosted_profile_image_url_tiny:
            position_object.speaker_image_url_https_tiny = organization.we_vote_hosted_profile_image_url_tiny
            values_changed = True
        if values_changed:
            try:
                position_object.save()
                success = True
                status = "SAVED_POSITION_IMAGE_URLS_FROM_ORGANIZATION"
            except Exception as e:
                success = False
                status = 'NOT_SAVED_POSITION_IMAGE_URLS_FROM_ORGANIZATION'
        else:
            success = True
            status = "NO_CHANGES_SAVED_TO_POSITION_IMAGE_URLS"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    def update_position_image_urls_from_voter(self, position_object, voter):
        """
        Update position_object with voter image urls
        :param position_object:
        :param voter:
        :return:
        """
        values_changed = False
        if positive_value_exists(voter.voter_photo_url()) and \
                position_object.speaker_image_url_https != voter.voter_photo_url():
            position_object.speaker_image_url_https = voter.voter_photo_url()
            values_changed = True
        if positive_value_exists(voter.we_vote_hosted_profile_image_url_large) and \
                position_object.speaker_image_url_https_large != voter.we_vote_hosted_profile_image_url_large:
            position_object.speaker_image_url_https_large = voter.we_vote_hosted_profile_image_url_large
            values_changed = True
        if positive_value_exists(voter.we_vote_hosted_profile_image_url_medium) and \
                position_object.speaker_image_url_https_medium != voter.we_vote_hosted_profile_image_url_medium:
            position_object.speaker_image_url_https_medium = voter.we_vote_hosted_profile_image_url_medium
            values_changed = True
        if positive_value_exists(voter.we_vote_hosted_profile_image_url_tiny) and \
                position_object.speaker_image_url_https_tiny != voter.we_vote_hosted_profile_image_url_tiny:
            position_object.speaker_image_url_https_tiny = voter.we_vote_hosted_profile_image_url_tiny
            values_changed = True
        if values_changed:
            try:
                position_object.save()
                success = True
                status = "SAVED_POSITION_IMAGE_URLS_FROM_VOTER"
            except Exception as e:
                success = False
                status = 'NOT_SAVED_POSITION_IMAGE_URLS_FROM_VOTER'
        else:
            success = True
            status = "NO_CHANGES_SAVED_TO_POSITION_IMAGE_URLS"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    def reset_position_image_details(self, position_object, ballot_item_image_url_https=None,
                                     speaker_image_url_https=None):
        """
        Reset Position image details as per we vote image details
        :param position_object:
        :param ballot_item_image_url_https:
        :param speaker_image_url_https:
        :return:
        """
        position_change = False
        if positive_value_exists(ballot_item_image_url_https):
            position_object.ballot_item_image_url_https = ballot_item_image_url_https
            position_object.ballot_item_image_url_https_large = ''
            position_object.ballot_item_image_url_https_medium = ''
            position_object.ballot_item_image_url_https_tiny = ''
            position_change = True
        if positive_value_exists(speaker_image_url_https):
            position_object.speaker_image_url_https = speaker_image_url_https
            position_object.speaker_image_url_https_large = ''
            position_object.speaker_image_url_https_medium = ''
            position_object.speaker_image_url_https_tiny = ''
            position_change = True

        if position_change:
            position_object.save()
            success = True
            status = "RESET_POSITION_IMAGE_DETAILS"
        else:
            success = False
            status = "NO_CHANGES_RESET_TO_POSITION_IMAGE_DETAILS"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    def update_position_ballot_data_from_candidate(self, position_object, candidate_campaign):
        """
        Update position_object with candidate data.
        :param position_object:
        :param candidate_campaign:
        :return:
        """
        position_change = False
        if positive_value_exists(candidate_campaign.candidate_name) and \
                position_object.ballot_item_display_name != candidate_campaign.candidate_name:
            position_object.ballot_item_display_name = candidate_campaign.candidate_name
            position_change = True
        if positive_value_exists(candidate_campaign.candidate_twitter_handle) and \
                position_object.ballot_item_twitter_handle != candidate_campaign.candidate_twitter_handle:
            position_object.ballot_item_twitter_handle = candidate_campaign.candidate_twitter_handle
            position_change = True
        if position_change:
            try:
                position_object.save()
                success = True
                status = "SAVED_POSITION_BALLOT_DATA_FROM_CANDIDATE"
            except Exception as e:
                success = False
                status = 'NOT_SAVED_POSITION_BALLOT_DATA_FROM_CANDIDATE'
        else:
            success = True
            status = "NO_CHANGES_SAVED_TO_POSITION_BALLOT_DATA"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    def update_position_measure_data_from_contest_measure(self, position_object, contest_measure):
        """
        Update position_object with measure data.
        :param position_object:
        :param candidate_campaign:
        :return:
        """
        position_change = False
        if positive_value_exists(contest_measure.google_civic_measure_title) and \
                position_object.google_civic_measure_title != contest_measure.google_civic_measure_title:
            position_object.google_civic_measure_title = contest_measure.google_civic_measure_title
            position_change = True
        if positive_value_exists(contest_measure.we_vote_id) and \
                position_object.contest_measure_we_vote_id != contest_measure.we_vote_id:
            position_object.contest_measure_we_vote_id = contest_measure.we_vote_id
            position_change = True
        if positive_value_exists(contest_measure.id) and \
                position_object.contest_measure_id != contest_measure.id:
            position_object.contest_measure_id = contest_measure.id
            position_change = True
        if position_change:
            try:
                position_object.save()
                success = True
                status = "SAVED_POSITION_MEASURE_DATA_FROM_CONTEST_MEASURE"
            except Exception as e:
                success = False
                status = 'NOT_SAVED_POSITION_MEASURE_DATA_FROM_CONTEST_MEASURE'
        else:
            success = True
            status = "NO_CHANGES_SAVED_TO_POSITION_MEASURE_DATA"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    def update_position_office_data_from_contest_office(self, position_object, contest_office):
        """
        Update position_object with office data.
        :param position_object:
        :param candidate_campaign:
        :return:
        """
        position_change = False
        if positive_value_exists(contest_office.office_name) and \
                position_object.contest_office_name != contest_office.office_name:
            position_object.contest_office_name = contest_office.office_name
            position_change = True
        if positive_value_exists(contest_office.we_vote_id) and \
                position_object.contest_office_we_vote_id != contest_office.we_vote_id:
            position_object.contest_office_we_vote_id = contest_office.we_vote_id
            position_change = True
        if positive_value_exists(contest_office.id) and \
                position_object.contest_office_id != contest_office.id:
            position_object.contest_office_id = contest_office.id
            position_change = True
        if position_change:
            try:
                position_object.save()
                success = True
                status = "SAVED_POSITION_OFFICE_DATA_FROM_CONTEST_OFFICE"
            except Exception as e:
                success = False
                status = 'NOT_SAVED_POSITION_OFFICE_DATA_FROM_CONTEST_OFFICE'
        else:
            success = True
            status = "NO_CHANGES_SAVED_TO_POSITION_OFFICE_DATA"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    def update_position_speaker_data_from_organization(self, position_object, organization):
        """
        Update position_object with organization data.
        :param position_object:
        :param organization:
        :return:
        """
        position_change = False
        if positive_value_exists(organization.organization_name) and \
                position_object.speaker_display_name != organization.organization_name:
            position_object.speaker_display_name = organization.organization_name
            position_change = True
        if positive_value_exists(organization.organization_twitter_handle) and \
                position_object.speaker_twitter_handle != organization.organization_twitter_handle:
            position_object.speaker_twitter_handle = organization.organization_twitter_handle
            position_change = True
        if position_change:
            try:
                position_object.save()
                success = True
                status = "SAVED_POSITION_SPEAKER_DATA_FROM_ORGANIZATION"
            except Exception as e:
                success = False
                status = 'NOT_SAVED_POSITION_SPEAKER_DATA_FROM_ORGANIZATION'
        else:
            success = True
            status = "NO_CHANGES_SAVED_TO_POSITION_SPEAKER_DATA"
        results = {
            'success':  success,
            'status':   status,
            'position': position_object
        }
        return results

    # We rely on this unique identifier: position_we_vote_id
    # Pass in a value if we want it saved. Pass in "False" if we want to leave it the same.
    def update_or_create_position(
            self, position_we_vote_id,
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
            position_on_stage_starter = PositionEntered
            position_on_stage = PositionEntered()
        else:
            position_on_stage_starter = PositionForFriends
            position_on_stage = PositionForFriends()
        status = "ENTERING_UPDATE_OR_CREATE_POSITION "

        position_manager = PositionManager()

        # In order of authority
        # 1) position_id exists? Find it with position_id or fail (REMOVED)
        # 2) we_vote_id exists? Find it with we_vote_id or fail
        # 3-5) organization_we_vote_id related position?
        # 6-8) public_figure_we_vote_id related position?
        # 9-11) voter_we_vote_id related position?

        success = False
        if positive_value_exists(position_we_vote_id):
            # If here, we know we are updating
            # 1) position_id exists? Find it with position_id or fail REMOVED
            # 2) we_vote_id exists? Find it with we_vote_id or fail
            position_results = {
                'success': False,
            }
            found_with_we_vote_id = False
            if positive_value_exists(position_we_vote_id):
                position_results = position_manager.retrieve_position_from_we_vote_id(position_we_vote_id)
                found_with_we_vote_id = True

            if position_results['success']:
                position_on_stage = position_results['position']
                position_on_stage_found = True

                if organization_we_vote_id:
                    position_on_stage.organization_we_vote_id = organization_we_vote_id
                    # Lookup organization_id based on organization_we_vote_id and update
                    organization_manager = OrganizationManager()
                    position_on_stage.organization_id = \
                        organization_manager.fetch_organization_id(organization_we_vote_id)
                if google_civic_election_id:
                    position_on_stage.google_civic_election_id = google_civic_election_id
                if state_code:
                    position_on_stage.state_code = state_code
                if ballot_item_display_name:
                    position_on_stage.ballot_item_display_name = ballot_item_display_name
                if office_we_vote_id:
                    position_on_stage.contest_office_we_vote_id = office_we_vote_id
                    # Lookup contest_office_id based on office_we_vote_id and update
                    contest_office_manager = ContestOfficeManager()
                    position_on_stage.contest_office_id = \
                        contest_office_manager.fetch_contest_office_id_from_we_vote_id(office_we_vote_id)
                if candidate_we_vote_id:
                    position_on_stage.candidate_campaign_we_vote_id = candidate_we_vote_id
                    # Lookup candidate_campaign_id based on candidate_campaign_we_vote_id and update
                    candidate_campaign_manager = CandidateCampaignManager()
                    position_on_stage.candidate_campaign_id = \
                        candidate_campaign_manager.fetch_candidate_campaign_id_from_we_vote_id(candidate_we_vote_id)
                if measure_we_vote_id:
                    position_on_stage.contest_measure_we_vote_id = measure_we_vote_id
                    # Lookup contest_measure_id based on contest_measure_we_vote_id and update
                    contest_measure_manager = ContestMeasureManager()
                    position_on_stage.contest_measure_id = \
                        contest_measure_manager.fetch_contest_measure_id_from_we_vote_id(measure_we_vote_id)
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
                if organization_we_vote_id or google_civic_election_id or state_code or ballot_item_display_name or \
                        office_we_vote_id or candidate_we_vote_id or measure_we_vote_id or stance or statement_text \
                        or statement_html or more_info_url \
                        or vote_smart_time_span or vote_smart_rating_id or vote_smart_rating or vote_smart_rating_name:
                    position_on_stage.save()
                    success = True
                    if found_with_we_vote_id:
                        status = "POSITION_SAVED_WITH_POSITION_WE_VOTE_ID"
                    else:
                        status = "POSITION_CHANGES_SAVED"
                else:
                    success = True
                    if found_with_we_vote_id:
                        status = "NO_POSITION_CHANGES_SAVED_WITH_POSITION_WE_VOTE_ID"
                    else:
                        status = "NO_POSITION_CHANGES_SAVED"
            else:
                status = "POSITION_COULD_NOT_BE_FOUND_WITH_POSITION_ID_OR_WE_VOTE_ID"
        # else for this: if positive_value_exists(position_we_vote_id):
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
                status = "FAILED-TOO_MANY_UNIQUE_BALLOT_ITEM_VARIABLES "
                success = False
            elif number_of_unique_ballot_item_identifiers is 0:
                no_unique_ballot_item_variables_received = True
                status = "FAILED-NO_UNIQUE_BALLOT_ITEM_VARIABLES_RECEIVED "
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
                status = "FAILED-TOO_MANY_UNIQUE_ACTOR_VARIABLES "
                success = False
            elif number_of_unique_actor_identifiers is 0:
                no_unique_actor_variables_received = True
                status = "FAILED-NO_UNIQUE_ACTOR_VARIABLES_RECEIVED "
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
                        organization_id = 0
                        # organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        voter_we_vote_id = ""
                        office_we_vote_id = ""
                        candidate_id = 0
                        # candidate_we_vote_id = ""
                        measure_id = 0
                        measure_we_vote_id = ""
                        # google_civic_election_id = 0

                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id)
                        if results['position_found']:
                            position_on_stage = results['position']
                            position_on_stage_found = True
                            found_with_status = "FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID "
                    except MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        status = "FAILED-MULTIPLE_FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID "
                    except ObjectDoesNotExist as e:
                        # Not a problem -- a position matching this candidate_we_vote_id wasn't found
                        pass
                # If there wasn't a google_civic_election_id, look for vote_smart_time_span
                elif positive_value_exists(candidate_we_vote_id) and \
                        positive_value_exists(organization_we_vote_id) and \
                        positive_value_exists(vote_smart_time_span):
                    try:
                        organization_id = 0
                        # organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        voter_we_vote_id = ""
                        office_we_vote_id = ""
                        candidate_id = 0
                        # candidate_we_vote_id = ""
                        measure_id = 0
                        measure_we_vote_id = ""
                        google_civic_election_id = 0
                        # vote_smart_time_span = ""

                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id,
                            vote_smart_time_span,
                        )
                        if results['position_found']:
                            position_on_stage = results['position']
                            position_on_stage_found = True
                            found_with_status = "FOUND_WITH_CANDIDATE_AND_ORGANIZATION_WE_VOTE_ID_WITH_TIME_SPAN "
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
                        organization_id = 0
                        # organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        voter_we_vote_id = ""
                        office_we_vote_id = ""
                        candidate_id = 0
                        candidate_we_vote_id = ""
                        measure_id = 0
                        # measure_we_vote_id = ""
                        # google_civic_election_id = 0
                        vote_smart_time_span = ""

                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id,
                            vote_smart_time_span
                        )
                        if results['position_found']:
                            position_on_stage = results['position']
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
                        organization_id = 0
                        # organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        voter_we_vote_id = ""
                        # office_we_vote_id = ""
                        candidate_id = 0
                        candidate_we_vote_id = ""
                        measure_id = 0
                        measure_we_vote_id = ""
                        # google_civic_election_id = 0
                        vote_smart_time_span = ""

                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id,
                            vote_smart_time_span,
                        )
                        if results['position_found']:
                            position_on_stage = results['position']
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
                        organization_id = 0
                        organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        voter_we_vote_id = ""
                        office_we_vote_id = ""
                        candidate_id = 0
                        # candidate_we_vote_id = ""
                        measure_id = 0
                        measure_we_vote_id = ""
                        # google_civic_election_id = 0
                        vote_smart_time_span = ""

                        # TODO public_figure code needs to be added for this to work
                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id,
                            vote_smart_time_span,
                        )
                        if results['position_found']:
                            position_on_stage = results['position']
                            position_on_stage_found = False  # TODO Update when working
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
                        # TODO DALE replace with retrieve_position_table_unknown
                        position_on_stage = position_on_stage_starter.objects.get(
                            contest_measure_we_vote_id=measure_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id,
                            state_code=state_code,
                        )
                        position_on_stage_found = False  # TODO Update when working
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
                        # TODO DALE replace with retrieve_position_table_unknown
                        position_on_stage = position_on_stage_starter.objects.get(
                            contest_office_we_vote_id=office_we_vote_id,
                            public_figure_we_vote_id=public_figure_we_vote_id,
                            google_civic_election_id=google_civic_election_id,
                            state_code=state_code
                        )
                        position_on_stage_found = False  # TODO Update when public_figure working
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
                        organization_id = 0
                        organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        # voter_we_vote_id = ""
                        office_we_vote_id = ""
                        candidate_id = 0
                        # candidate_we_vote_id = ""
                        measure_id = 0
                        measure_we_vote_id = ""
                        vote_smart_time_span = ""

                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id,
                            vote_smart_time_span,
                        )
                        if results['position_found']:
                            position_on_stage = results['position']
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
                        organization_id = 0
                        organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        # voter_we_vote_id = ""
                        office_we_vote_id = ""
                        candidate_id = 0
                        candidate_we_vote_id = ""
                        measure_id = 0
                        # measure_we_vote_id = ""
                        # google_civic_election_id = 0
                        vote_smart_time_span = ""

                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id,
                            vote_smart_time_span,
                        )
                        if results['position_found']:
                            position_on_stage = results['position']
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
                        organization_id = 0
                        organization_we_vote_id = ""
                        voter_id = 0
                        office_id = 0
                        # voter_we_vote_id = ""
                        # office_we_vote_id = ""
                        candidate_id = 0
                        candidate_we_vote_id = ""
                        measure_id = 0
                        measure_we_vote_id = ""
                        vote_smart_time_span = ""

                        results = position_manager.retrieve_position_table_unknown(
                            position_we_vote_id, organization_id, organization_we_vote_id,
                            voter_id,
                            office_id, candidate_id,
                            measure_id,
                            voter_we_vote_id,
                            office_we_vote_id,
                            candidate_we_vote_id,
                            measure_we_vote_id,
                            google_civic_election_id,
                            vote_smart_time_span,
                        )
                        if results['position_found']:
                            position_on_stage = results['position']
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
                speaker_display_name = ""

                candidate_campaign_id = None
                if candidate_we_vote_id:
                    candidate_campaign_manager = CandidateCampaignManager()
                    results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                        candidate_we_vote_id)
                    if results['candidate_campaign_found']:
                        candidate_campaign = results['candidate_campaign']
                        candidate_campaign_id = candidate_campaign.id
                        google_civic_election_id = candidate_campaign.google_civic_election_id
                        state_code = candidate_campaign.state_code
                        ballot_item_display_name = candidate_campaign.candidate_name
                else:
                    # We don't need to ever look up the candidate_we_vote_id from the candidate_campaign_id
                    candidate_we_vote_id = None

                contest_measure_id = None
                if measure_we_vote_id:
                    contest_measure_manager = ContestMeasureManager()
                    results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)
                    if results['contest_measure_found']:
                        contest_measure = results['contest_measure']
                        contest_measure_id = contest_measure.id
                        google_civic_election_id = contest_measure.google_civic_election_id
                        state_code = contest_measure.state_code
                        ballot_item_display_name = contest_measure.measure_title
                else:
                    # We don't need to ever look up the measure_we_vote_id from the contest_measure_id
                    measure_we_vote_id = None

                contest_office_id = None
                if office_we_vote_id:
                    contest_office_manager = ContestOfficeManager()
                    results = contest_office_manager.retrieve_contest_office_from_we_vote_id(office_we_vote_id)
                    if results['contest_office_found']:
                        contest_office = results['contest_office']
                        contest_office_id = contest_office.id
                        google_civic_election_id = contest_office.google_civic_election_id
                        state_code = contest_office.state_code
                        ballot_item_display_name = contest_office.office_name
                else:
                    # We don't need to ever look up the office_we_vote_id from the contest_office_id
                    office_we_vote_id = None

                if google_civic_election_id is False:
                    google_civic_election_id = None

                if state_code is False:
                    state_code = None

                if ballot_item_display_name is False:
                    ballot_item_display_name = None

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

                # In order to show a position publicly we need to tie the position to either organization_we_vote_id,
                # public_figure_we_vote_id or candidate_we_vote_id. For now (2016-8-17) we assume organization
                voter_manager = VoterManager()
                results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id)
                voter_id = 0
                if results['voter_found']:
                    voter = results['voter']
                    voter_id = voter.id
                    organization_we_vote_id = voter.linked_organization_we_vote_id
                if positive_value_exists(organization_we_vote_id):
                    # Look up the organization_id
                    organization_manager = OrganizationManager()
                    organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                        organization_we_vote_id)
                    if organization_results['organization_found']:
                        organization = organization_results['organization']
                        organization_id = organization.id
                        speaker_display_name = organization.organization_name

                position_on_stage = position_on_stage_starter.objects.create(
                    organization_we_vote_id=organization_we_vote_id,
                    organization_id=organization_id,
                    voter_we_vote_id=voter_we_vote_id,
                    voter_id=voter_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    ballot_item_display_name=ballot_item_display_name,
                    speaker_display_name=speaker_display_name,
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
                    position_on_stage = PositionEntered()
                else:
                    position_on_stage = PositionForFriends()

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'position':                 position_on_stage,
            'new_position_created':     new_position_created,
        }
        return results

    def refresh_cached_position_info(self, position_object, force_update=False):
        """
        The position tables cache information from other tables. This function reaches out to the source tables
        and copies over the latest information to the position tables.
        :param position_object:
        :param force_update:
        :return:
        """
        position_change = False

        # Start with "speaker" information (Organization, Voter, or Public Figure)
        if positive_value_exists(position_object.organization_we_vote_id):
            if not positive_value_exists(position_object.speaker_display_name) \
                    or not positive_value_exists(position_object.speaker_image_url_https) \
                    or not positive_value_exists(position_object.speaker_twitter_handle) \
                    or force_update:
                try:
                    # We need to look in the organization table for speaker_display_name & speaker_image_url_https
                    organization_manager = OrganizationManager()
                    organization_id = 0
                    results = organization_manager.retrieve_organization(organization_id,
                                                                         position_object.organization_we_vote_id)
                    if results['organization_found']:
                        organization = results['organization']

                        # Make sure we have an organization name
                        if not positive_value_exists(organization.organization_name):
                            try:
                                linked_voter = Voter.objects.get(
                                    linked_organization_we_vote_id__iexact=organization.we_vote_id)
                                if linked_voter.get_full_name():
                                    try:
                                        organization.organization_name = linked_voter.get_full_name()
                                        organization.save()
                                    except Exception as e:
                                        pass
                            except Voter.DoesNotExist:
                                pass

                        if not positive_value_exists(position_object.speaker_display_name) or force_update:
                            # speaker_display_name is missing so look it up from source
                            position_object.speaker_display_name = organization.organization_name
                            position_change = True
                        if not positive_value_exists(position_object.speaker_image_url_https) or force_update:
                            # speaker_image_url_https is missing so look it up from source
                            position_object.speaker_image_url_https = organization.organization_photo_url()
                            position_change = True
                        if not positive_value_exists(position_object.speaker_twitter_handle) or force_update:
                            organization_twitter_handle = \
                                organization_manager.fetch_twitter_handle_from_organization_we_vote_id(
                                    organization.we_vote_id)
                            # speaker_twitter_handle is missing so look it up from source
                            position_object.speaker_twitter_handle = organization_twitter_handle
                            position_change = True
                except Exception as e:
                    pass
        elif positive_value_exists(position_object.voter_id):
            if not positive_value_exists(position_object.speaker_display_name) \
                    or not positive_value_exists(position_object.voter_we_vote_id) \
                    or not positive_value_exists(position_object.speaker_image_url_https) \
                    or not positive_value_exists(position_object.speaker_twitter_handle) \
                    or force_update:
                try:
                    # We need to look in the voter table for speaker_display_name
                    voter_manager = VoterManager()
                    results = voter_manager.retrieve_voter_by_id(position_object.voter_id)
                    if results['voter_found']:
                        voter = results['voter']
                        if not positive_value_exists(position_object.speaker_display_name) or force_update:
                            # speaker_display_name is missing so look it up from source
                            position_object.speaker_display_name = voter.get_full_name()
                            position_change = True
                        if not positive_value_exists(position_object.voter_we_vote_id) or force_update:
                            # speaker_we_vote_id is missing so look it up from source
                            position_object.voter_we_vote_id = voter.we_vote_id
                            position_change = True
                        if not positive_value_exists(position_object.speaker_image_url_https) or force_update:
                            # speaker_image_url_https is missing so look it up from source
                            position_object.speaker_image_url_https = voter.voter_photo_url()
                            position_change = True
                        if not positive_value_exists(position_object.speaker_twitter_handle) or force_update:
                            # speaker_twitter_handle is missing so look it up from source
                            voter_twitter_handle = voter_manager.fetch_twitter_handle_from_voter_we_vote_id(
                                voter.we_vote_id)
                            position_object.speaker_twitter_handle = voter_twitter_handle
                            position_change = True
                except Exception as e:
                    pass

        elif positive_value_exists(position_object.public_figure_we_vote_id):
            pass

        # Now move onto "ballot_item" information
        # Candidate
        check_for_missing_office_data = False
        candidate_campaign_manager = CandidateCampaignManager()
        contest_office_id = 0
        contest_office_we_vote_id = ""
        if positive_value_exists(position_object.candidate_campaign_id) or \
                positive_value_exists(position_object.candidate_campaign_we_vote_id):
            check_for_missing_office_data = True  # We check separately
            if not positive_value_exists(position_object.ballot_item_display_name) \
                    or not positive_value_exists(position_object.ballot_item_image_url_https) \
                    or not positive_value_exists(position_object.ballot_item_twitter_handle) \
                    or not positive_value_exists(position_object.state_code) \
                    or not positive_value_exists(position_object.political_party) \
                    or not positive_value_exists(position_object.politician_id) \
                    or not positive_value_exists(position_object.politician_we_vote_id) \
                    or force_update:
                try:
                    # We need to look in the voter table for speaker_display_name
                    results = candidate_campaign_manager.retrieve_candidate_campaign(
                        position_object.candidate_campaign_id, position_object.candidate_campaign_we_vote_id)
                    if results['candidate_campaign_found']:
                        candidate = results['candidate_campaign']
                        # Cache for further down
                        contest_office_id = candidate.contest_office_id
                        contest_office_we_vote_id = candidate.contest_office_we_vote_id
                        if not positive_value_exists(position_object.contest_office_id) or force_update:
                            position_object.contest_office_id = contest_office_id
                            position_change = True
                        if not positive_value_exists(position_object.contest_office_we_vote_id) or force_update:
                            position_object.contest_office_we_vote_id = contest_office_we_vote_id
                            position_change = True
                        if not positive_value_exists(position_object.ballot_item_display_name) or force_update:
                            # ballot_item_display_name is missing so look it up from source
                            position_object.ballot_item_display_name = candidate.display_candidate_name()
                            position_change = True
                        if not positive_value_exists(position_object.ballot_item_image_url_https) or force_update:
                            # ballot_item_image_url_https is missing so look it up from source
                            position_object.ballot_item_image_url_https = candidate.candidate_photo_url()
                            position_change = True
                        if not positive_value_exists(position_object.ballot_item_twitter_handle) or force_update:
                            # ballot_item_image_twitter_handle is missing so look it up from source
                            position_object.ballot_item_twitter_handle = candidate.candidate_twitter_handle
                            position_change = True
                        if not positive_value_exists(position_object.state_code) or force_update:
                            # state_code is missing so look it up from source
                            position_object.state_code = candidate.get_candidate_state()
                            position_change = True
                        if not positive_value_exists(position_object.political_party) or force_update:
                            # political_party is missing so look it up from source
                            position_object.political_party = candidate.political_party_display()
                            position_change = True
                        if not positive_value_exists(position_object.politician_id) or force_update:
                            # politician_id is missing so look it up from source
                            position_object.politician_id = candidate.politician_id
                            position_change = True
                        if not positive_value_exists(position_object.politician_we_vote_id) or force_update:
                            # politician_we_vote_id is missing so look it up from source
                            position_object.politician_we_vote_id = candidate.politician_we_vote_id
                            position_change = True
                except Exception as e:
                    pass
        # Measure
        elif positive_value_exists(position_object.contest_measure_id) or \
                positive_value_exists(position_object.contest_measure_we_vote_id):
            if not positive_value_exists(position_object.ballot_item_display_name) \
                    or position_object.ballot_item_display_name == "None" \
                    or positive_value_exists(position_object.ballot_item_image_url_https) \
                    or positive_value_exists(position_object.ballot_item_twitter_handle) \
                    or not positive_value_exists(position_object.state_code) \
                    or force_update:
                try:
                    # We need to look in the voter table for speaker_display_name
                    contest_measure_manager = ContestMeasureManager()
                    results = contest_measure_manager.retrieve_contest_measure(
                        position_object.contest_measure_id, position_object.contest_measure_we_vote_id)
                    if results['contest_measure_found']:
                        contest_measure = results['contest_measure']
                        if not positive_value_exists(position_object.ballot_item_display_name) \
                                or position_object.ballot_item_display_name == "None" \
                                or force_update:
                            # ballot_item_display_name is missing so look it up from source
                            position_object.ballot_item_display_name = contest_measure.measure_title
                            position_change = True
                        if positive_value_exists(position_object.ballot_item_image_url_https) or force_update:
                            # ballot_item_image_url_https should not exist for measures
                            position_object.ballot_item_image_url_https = ""
                            position_change = True
                        if positive_value_exists(position_object.ballot_item_twitter_handle) or force_update:
                            # ballot_item_image_twitter_handle should not exist for measures
                            position_object.ballot_item_twitter_handle = ""
                            position_change = True
                        if not positive_value_exists(position_object.state_code) or force_update:
                            # state_code is missing so look it up from source
                            position_object.state_code = contest_measure.state_code
                            position_change = True
                except Exception as e:
                    pass
        # Office - We are only here if NOT a candidate and NOT a measure
        elif positive_value_exists(position_object.contest_office_id) or \
                positive_value_exists(position_object.contest_office_we_vote_id):
            check_for_missing_office_data = True

        if check_for_missing_office_data:
            if not positive_value_exists(position_object.contest_office_id) \
                    or not positive_value_exists(position_object.contest_office_we_vote_id) \
                    or not positive_value_exists(position_object.contest_office_name) \
                    or force_update:
                if not positive_value_exists(position_object.contest_office_id) \
                        and not positive_value_exists(position_object.contest_office_we_vote_id):
                    if not contest_office_id or not contest_office_we_vote_id:
                        # If here we need to get the contest_office identifier from the candidate
                        candidate_results = candidate_campaign_manager.retrieve_candidate_campaign_from_we_vote_id(
                            position_object.candidate_campaign_we_vote_id)
                        if candidate_results['candidate_campaign_found']:
                            candidate = candidate_results['candidate_campaign']
                            position_object.contest_office_id = candidate.contest_office_id
                            position_object.contest_office_we_vote_id = candidate.contest_office_we_vote_id
                            position_change = True
                    else:
                        position_object.contest_office_id = contest_office_id
                        position_object.contest_office_we_vote_id = contest_office_we_vote_id
                        position_change = True
                office_found = False
                contest_office_manager = ContestOfficeManager()
                if positive_value_exists(position_object.contest_office_id):
                    results = contest_office_manager.retrieve_contest_office_from_id(position_object.contest_office_id)
                    office_found = results['contest_office_found']
                elif positive_value_exists(position_object.contest_office_we_vote_id):
                    results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
                        position_object.contest_office_we_vote_id)
                    office_found = results['contest_office_found']

                if office_found:
                    office_object = results['contest_office']
                    if not positive_value_exists(position_object.contest_office_id) or force_update:
                        position_object.contest_office_id = office_object.id
                        position_change = True
                    if not positive_value_exists(position_object.contest_office_we_vote_id) or force_update:
                        position_object.contest_office_we_vote_id = office_object.we_vote_id
                        position_change = True
                    if not positive_value_exists(position_object.contest_office_name) or force_update:
                        position_object.contest_office_name = office_object.office_name
                        position_change = True

        if position_change:
            position_object.save()

        return position_object

    def count_positions_for_election(self, google_civic_election_id, retrieve_public_positions=True):
        """
        Return count of positions for a given election
        :param google_civic_election_id: 
        :param retrieve_public_positions:
        :return:
        """

        if positive_value_exists(retrieve_public_positions):
            position_item_queryset = PositionEntered.objects.all()
        else:
            position_item_queryset = PositionForFriends.objects.all()

        positions_count = 0
        success = False
        if positive_value_exists(google_civic_election_id):
            # get count of positions
            try:
                position_item_queryset = position_item_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
                positions_count = position_item_queryset.count()

                status = 'POSITION_ITEMS_FOUND '
                success = True
            except PositionEntered.DoesNotExist:
                # No position items found. Not a problem.
                status = 'NO_POSITION_ITEMS_FOUND '
                success = True
            except Exception as e:
                handle_exception(e, logger=logger)
                status = 'FAILED retrieve_position_items_for_election ' \
                         '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
        else:
            status = 'INVALID_GOOGLE_CIVIC_ELECTION_ID'

        results = {
            'success':          success,
            'status':           status,
            'positions_count':  positions_count
        }
        return results


class PositionMetricsManager(models.Model):

    def __unicode__(self):
        return "PositionMetricsManager"

    def fetch_positions_public(self, google_civic_election_id=0, positions_taken_by_these_voter_we_vote_ids=False):
        count_result = None
        try:
            count_query = PositionEntered.objects.using('readonly').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positions_taken_by_these_voter_we_vote_ids is not False:
                count_query = count_query.filter(voter_we_vote_id__in=positions_taken_by_these_voter_we_vote_ids)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_positions_public_with_comments(self, google_civic_election_id=0,
                                             positions_taken_by_these_voter_we_vote_ids=False):
        count_result = None
        try:
            count_query = PositionEntered.objects.using('readonly').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.exclude(
                (Q(statement_text__isnull=True) | Q(statement_text__exact='')) &
                (Q(statement_html__isnull=True) | Q(statement_html__exact=''))
            )
            if positions_taken_by_these_voter_we_vote_ids is not False:
                count_query = count_query.filter(voter_we_vote_id__in=positions_taken_by_these_voter_we_vote_ids)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_positions_friends_only(self, google_civic_election_id=0,
                                     positions_taken_by_these_voter_we_vote_ids=False):
        count_result = None
        try:
            count_query = PositionForFriends.objects.using('readonly').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positions_taken_by_these_voter_we_vote_ids is not False:
                count_query = count_query.filter(voter_we_vote_id__in=positions_taken_by_these_voter_we_vote_ids)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_positions_friends_only_with_comments(self, google_civic_election_id=0,
                                                   positions_taken_by_these_voter_we_vote_ids=False):
        count_result = None
        try:
            count_query = PositionForFriends.objects.using('readonly').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.exclude(
                (Q(statement_text__isnull=True) | Q(statement_text__exact='')) &
                (Q(statement_html__isnull=True) | Q(statement_html__exact=''))
            )
            if positions_taken_by_these_voter_we_vote_ids is not False:
                count_query = count_query.filter(voter_we_vote_id__in=positions_taken_by_these_voter_we_vote_ids)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_comments_entered_friends_only(self, voter_we_vote_id):
        count_result = None
        try:
            count_query = PositionForFriends.objects.using('readonly').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.exclude(
                (Q(statement_text__isnull=True) | Q(statement_text__exact='')) &
                (Q(statement_html__isnull=True) | Q(statement_html__exact=''))
            )
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_comments_entered_public(self, voter_we_vote_id):
        count_result = None
        try:
            count_query = PositionEntered.objects.using('readonly').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.exclude(
                (Q(statement_text__isnull=True) | Q(statement_text__exact='')) &
                (Q(statement_html__isnull=True) | Q(statement_html__exact=''))
            )
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_positions_entered_friends_only(self, voter_we_vote_id):
        count_result = None
        try:
            count_query = PositionForFriends.objects.using('readonly').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_voter_positions_entered_public(self, voter_we_vote_id):
        count_result = None
        try:
            count_query = PositionEntered.objects.using('readonly').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_positions_count_for_this_voter(self, voter):

        position_filters = []
        final_position_filters = []
        if positive_value_exists(voter.we_vote_id):
            new_position_filter = Q(voter_we_vote_id__iexact=voter.we_vote_id)
            position_filters.append(new_position_filter)
        if positive_value_exists(voter.id):
            new_position_filter = Q(voter_id=voter.id)
            position_filters.append(new_position_filter)
        if positive_value_exists(voter.linked_organization_we_vote_id):
            new_position_filter = Q(organization_we_vote_id=voter.linked_organization_we_vote_id)
            position_filters.append(new_position_filter)

        if len(position_filters):
            final_position_filters = position_filters.pop()

            # ...and "OR" the remaining items in the list
            for item in position_filters:
                final_position_filters |= item

        # PositionEntered
        position_list_query = PositionEntered.objects.using('readonly').all()
        position_list_query = position_list_query.filter(final_position_filters)

        position_entered_count = position_list_query.count()

        # PositionForFriends
        position_list_query = PositionForFriends.objects.using('readonly').all()
        position_list_query = position_list_query.filter(final_position_filters)

        position_for_friends_count = position_list_query.count()

        total_positions_count = position_entered_count + position_for_friends_count

        return total_positions_count
