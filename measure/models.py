# measure/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from wevote_settings.models import fetch_next_we_vote_id_last_contest_measure_integer, \
    fetch_next_we_vote_id_last_measure_campaign_integer, fetch_site_unique_id_prefix
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class ContestMeasure(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "meas", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_measure_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)
    maplight_id = models.CharField(verbose_name="maplight unique identifier",
                                   max_length=254, null=True, blank=True, unique=True)
    # The title of the measure (e.g. 'Proposition 42').
    measure_title = models.CharField(verbose_name="measure title", max_length=254, null=False, blank=False)
    # A brief description of the referendum. This field is only populated for contests of type 'Referendum'.
    measure_subtitle = models.CharField(verbose_name="google civic referendum subtitle",
                                        max_length=254, null=False, blank=False)
    # A link to the referendum. This field is only populated for contests of type 'Referendum'.
    measure_url = models.CharField(verbose_name="measure details url", max_length=254, null=True, blank=False)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=254, null=True, blank=True)
    # ballot_placement: We store ballot_placement in the BallotItem table instead because it is different for each voter
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

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_contest_measure_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "meas" = tells us this is a unique id for a ContestMeasure
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}meas{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ContestMeasure, self).save(*args, **kwargs)


class MeasureCampaign(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "meascam", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_measure_campaign_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)
    # contest_measure link
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_measure_id = models.CharField(verbose_name="contest_measure unique id",
                                          max_length=254, null=False, blank=False)
    # Is the campaign attempting to pass the measure, or stop it from passing?
    SUPPORT = 'S'
    NEUTRAL = 'N'
    OPPOSE = 'O'
    STANCE_CHOICES = (
        (SUPPORT, 'Support'),
        (NEUTRAL, 'Neutral'),
        (OPPOSE, 'Oppose'),
    )
    stance = models.CharField("stance", max_length=1, choices=STANCE_CHOICES, default=NEUTRAL)

    # The candidate's name.
    candidate_name = models.CharField(verbose_name="candidate name", max_length=254, null=False, blank=False)
    # The full name of the party the candidate is a member of.
    party = models.CharField(verbose_name="party", max_length=254, null=True, blank=True)
    # A URL for a photo of the candidate.
    photo_url = models.CharField(verbose_name="photoUrl", max_length=254, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google election id",
                                                max_length=254, null=False, blank=False)
    # The URL for the candidate's campaign web site.
    url = models.URLField(verbose_name='website url of campaign', blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of campaign', blank=True, null=True)
    twitter_url = models.URLField(verbose_name='twitter url of campaign', blank=True, null=True)
    google_plus_url = models.URLField(verbose_name='google plus url of campaign', blank=True, null=True)
    youtube_url = models.URLField(verbose_name='youtube url of campaign', blank=True, null=True)
    # The email address for the candidate's campaign.
    email = models.CharField(verbose_name="campaign email", max_length=254, null=True, blank=True)
    # The voice phone number for the campaign office.
    phone = models.CharField(verbose_name="campaign email", max_length=254, null=True, blank=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_measure_campaign_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "meascam" = tells us this is a unique id for a MeasureCampaign
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}meascam{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(MeasureCampaign, self).save(*args, **kwargs)
