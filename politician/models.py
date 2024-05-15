# politician/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import re
from datetime import datetime

import gender_guesser.detector as gender
from django.db import models
from django.db.models import Q

import wevote_functions.admin
from candidate.models import PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from tag.models import Tag
from wevote_functions.functions import candidate_party_display, convert_to_int, convert_to_political_party_constant, \
    display_full_name_with_correct_capitalization, extract_first_name_from_full_name, \
    extract_middle_name_from_full_name, extract_last_name_from_full_name, \
    extract_twitter_handle_from_text_string, positive_value_exists
from wevote_functions.functions_date import convert_date_to_date_as_integer
from wevote_settings.models import fetch_next_we_vote_id_politician_integer, fetch_site_unique_id_prefix

FEMALE = 'F'
GENDER_NEUTRAL = 'N'
MALE = 'M'
UNKNOWN = 'U'
GENDER_CHOICES = (
    (MALE, 'Male'),
    (FEMALE, 'Female'),
    (GENDER_NEUTRAL, 'Nonbinary'),
    (UNKNOWN, 'Unknown'),
)

DISPLAYABLE_GUESS = {
    'male': 'Male',
    'mostly_male': 'Likely Male',
    'female': 'Female',
    'mostly_female': 'Likely Female',
    'unknown': '...?...',
}


POLITICAL_DATA_MANAGER =         'PolDataMgr'
PROVIDED_BY_POLITICIAN =         'Politician'
GENDER_GUESSER_HIGH_LIKELIHOOD = 'GuessHigh'
GENDER_GUESSER_LOW_LIKELIHOOOD = 'GuessLow'
NOT_ANALYZED =                   ''
GENDER_LIKELIHOOD = (
    (POLITICAL_DATA_MANAGER, 'Political Data Mgr'),
    (PROVIDED_BY_POLITICIAN, 'Politician Provided'),
    (GENDER_GUESSER_HIGH_LIKELIHOOD, 'Gender Guesser High Likelihood'),
    (GENDER_GUESSER_LOW_LIKELIHOOOD, 'Gender Guesser Low Likelihood'),
    (NOT_ANALYZED, ''),
)
logger = wevote_functions.admin.get_logger(__name__)
detector = gender.Detector()

# When merging candidates, these are the fields we check for figure_out_politician_conflict_values
POLITICIAN_UNIQUE_IDENTIFIERS = [
    'ballotpedia_id',
    'ballotpedia_politician_name',
    'ballotpedia_politician_url',
    'bioguide_id',
    'birth_date',
    'cspan_id',
    'ctcl_uuid',
    # 'facebook_url',  # We now have 3 options and merge them automatically
    # 'facebook_url_is_broken',
    'fec_id',
    'first_name',
    'gender',
    'govtrack_id',
    'house_history_id',
    'icpsr_id',
    'instagram_followers_count',
    'instagram_handle',
    'is_battleground_race_2019',
    'is_battleground_race_2020',
    'is_battleground_race_2021',
    'is_battleground_race_2022',
    'is_battleground_race_2023',
    'is_battleground_race_2024',
    'is_battleground_race_2025',
    'is_battleground_race_2026',
    'last_name',
    'linked_campaignx_we_vote_id',
    'lis_id',
    'maplight_id',
    'middle_name',
    'ocd_id_state_mismatch_found',
    'opensecrets_id',
    'political_party',
    'politician_contact_form_url',
    # 'politician_email',  # We now have 3 options and merge them automatically
    'politician_facebook_id',
    'politician_googleplus_id',
    'politician_name',
    # 'politician_phone_number',  # We now have 3 options and merge them automatically
    # 'politician_url',  # We have 5 options now and merge them automatically
    'politician_youtube_id',
    'seo_friendly_path',
    'state_code',
    'thomas_id',
    'twitter_handle_updates_failing',
    'twitter_handle2_updates_failing',
    'vote_smart_id',
    'vote_usa_politician_id',
    'washington_post_id',
    'we_vote_hosted_profile_image_url_large',
    'we_vote_hosted_profile_image_url_medium',
    'we_vote_hosted_profile_image_url_tiny',
    'wikipedia_id',
]
POLITICIAN_UNIQUE_ATTRIBUTES_TO_BE_CLEARED = [
    'bioguide_id',
    'fec_id',
    'govtrack_id',
    'linked_campaignx_we_vote_id',
    'maplight_id',
    'seo_friendly_path',
    'thomas_id',
]


class Politician(models.Model):
    # We are relying on built-in Python id field
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "pol", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_politician_integer
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this politician", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # Official Statement from Candidate in Ballot Guide
    ballot_guide_official_statement = models.TextField(verbose_name="official candidate statement from ballot guide",
                                                       null=True, blank=True, default=None)
    # See this url for properties: https://docs.python.org/2/library/functions.html#property
    first_name = models.CharField(verbose_name="first name",
                                  max_length=255, default=None, null=True, blank=True)
    middle_name = models.CharField(verbose_name="middle name",
                                   max_length=255, default=None, null=True, blank=True)
    last_name = models.CharField(verbose_name="last name",
                                 max_length=255, default=None, null=True, blank=True)
    politician_name = models.CharField(verbose_name="official full name",
                                       max_length=255, default=None, null=True, blank=True)
    facebook_url = models.TextField(verbose_name='facebook url of candidate', blank=True, null=True)
    facebook_url2 = models.TextField(blank=True, null=True)
    facebook_url3 = models.TextField(blank=True, null=True)
    facebook_url_is_broken = models.BooleanField(verbose_name="facebook url is broken", default=False)
    facebook_url2_is_broken = models.BooleanField(default=False)
    facebook_url3_is_broken = models.BooleanField(default=False)
    # This is the politician's name from GoogleCivicCandidateCampaign
    google_civic_name_alternates_generated = models.BooleanField(default=False)
    google_civic_candidate_name = models.CharField(
        verbose_name="full name from google civic", max_length=255, default=None, null=True, blank=True)
    google_civic_candidate_name2 = models.CharField(max_length=255, null=True)
    google_civic_candidate_name3 = models.CharField(max_length=255, null=True)
    # This is the politician's name assembled from TheUnitedStatesIo first_name + last_name for quick search
    full_name_assembled = models.CharField(verbose_name="full name assembled from first_name + last_name",
                                           max_length=255, default=None, null=True, blank=True)
    gender = models.CharField("gender", max_length=1, choices=GENDER_CHOICES, default=UNKNOWN)
    gender_likelihood = models.CharField("gender guess likelihood", max_length=11, choices=GENDER_LIKELIHOOD,
                                         default='')

    birth_date = models.DateField("birth date", default=None, null=True, blank=True)
    # race = enum?
    # official_image_id = ??

    bioguide_id = models.CharField(verbose_name="bioguide unique identifier",
                                   max_length=200, null=True, unique=True)
    thomas_id = models.CharField(verbose_name="thomas unique identifier",
                                 max_length=200, null=True, unique=True)
    lis_id = models.CharField(verbose_name="lis unique identifier",
                              max_length=200, null=True, blank=True, unique=False)
    govtrack_id = models.CharField(verbose_name="govtrack unique identifier",
                                   max_length=200, null=True, unique=True)
    opensecrets_id = models.CharField(verbose_name="opensecrets unique identifier",
                                      max_length=200, null=True, unique=False)
    vote_smart_id = models.CharField(verbose_name="votesmart unique identifier",
                                     max_length=200, null=True, unique=False)
    fec_id = models.CharField(verbose_name="fec unique identifier",
                              max_length=200, null=True, unique=True, blank=True)
    cspan_id = models.CharField(verbose_name="cspan unique identifier",
                                max_length=200, null=True, blank=True, unique=False)
    # DEPRECATE wikipedia_id
    wikipedia_id = models.CharField(verbose_name="wikipedia url",
                                    max_length=500, default=None, null=True, blank=True)
    wikipedia_url = models.TextField(null=True)
    wikipedia_photo_url = models.TextField(
        verbose_name='url of remote wikipedia profile photo', blank=True, null=True)
    wikipedia_profile_image_url_https = models.TextField(
        verbose_name='locally cached candidate profile image from wikipedia', blank=True, null=True)
    ballotpedia_photo_url = models.TextField(
        verbose_name='url of remote ballotpedia profile photo', blank=True, null=True)
    ballotpedia_photo_url_is_broken = models.BooleanField(default=False)
    ballotpedia_photo_url_is_placeholder = models.BooleanField(default=False)
    ballotpedia_profile_image_url_https = models.TextField(
        verbose_name='locally cached profile image from ballotpedia', blank=True, null=True)
    # The candidate's name as passed over by Ballotpedia
    ballotpedia_politician_name = models.CharField(
        verbose_name="name exactly as received from ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_politician_url = models.TextField(
        verbose_name='url of politician on ballotpedia', blank=True, null=True)
    # We might need to deprecate ballotpedia_id
    ballotpedia_id = models.CharField(
        verbose_name="ballotpedia url", max_length=500, default=None, null=True, blank=True)
    house_history_id = models.CharField(verbose_name="house history unique identifier",
                                        max_length=200, null=True, blank=True)
    maplight_id = models.CharField(verbose_name="maplight unique identifier",
                                   max_length=200, null=True, unique=True, blank=True)
    washington_post_id = models.CharField(verbose_name="washington post unique identifier",
                                          max_length=200, null=True, unique=False)
    icpsr_id = models.CharField(verbose_name="icpsr unique identifier",
                                max_length=200, null=True, unique=False)
    tag_link = models.ManyToManyField(Tag, through='PoliticianTagLink')
    # The full name of the party the official belongs to.
    political_party = models.CharField(verbose_name="politician political party", max_length=255, null=True)
    politician_analysis_done = models.BooleanField(default=False)
    politician_url = models.TextField(blank=True, null=True)
    politician_url2 = models.TextField(blank=True, null=True)
    politician_url3 = models.TextField(blank=True, null=True)
    politician_url4 = models.TextField(blank=True, null=True)
    politician_url5 = models.TextField(blank=True, null=True)
    politician_contact_form_url = models.URLField(
        verbose_name='website url of contact form', max_length=255, blank=True, null=True)

    politician_twitter_handle = models.CharField(max_length=255, null=True, unique=False)
    politician_twitter_handle2 = models.CharField(max_length=255, null=True, unique=False)
    politician_twitter_handle3 = models.CharField(max_length=255, null=True, unique=False)
    politician_twitter_handle4 = models.CharField(max_length=255, null=True, unique=False)
    politician_twitter_handle5 = models.CharField(max_length=255, null=True, unique=False)
    seo_friendly_path = models.CharField(max_length=255, null=True, unique=True, db_index=True)
    seo_friendly_path_date_last_updated = models.DateTimeField(null=True)
    seo_friendly_path_needs_regeneration = models.BooleanField(default=False)
    state_code = models.CharField(verbose_name="politician home state", max_length=2, null=True)
    supporters_count = models.PositiveIntegerField(default=0)  # From linked_campaignx_we_vote_id CampaignX entry
    twitter_handle_updates_failing = models.BooleanField(default=False)
    twitter_handle2_updates_failing = models.BooleanField(default=False)
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    vote_usa_politician_id = models.CharField(
        verbose_name="Vote USA permanent id for this politician", max_length=64, default=None, null=True, blank=True)
    # Image URL on Vote USA's servers. See vote_usa_profile_image_url_https, the master image cached on We Vote servers.
    photo_url_from_vote_usa = models.TextField(null=True, blank=True)
    # This is the master image url cached on We Vote servers. See photo_url_from_vote_usa for Vote USA URL.
    vote_usa_profile_image_url_https = models.TextField(null=True, blank=True, default=None)

    # Which politician image is currently active?
    profile_image_type_currently_active = models.CharField(
        max_length=11, choices=PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES, default=PROFILE_IMAGE_TYPE_UNKNOWN)
    we_vote_hosted_politician_photo_original_url = models.TextField(blank=True, null=True)
    # Image for candidate from Ballotpedia, cached on We Vote's servers. See also ballotpedia_profile_image_url_https.
    we_vote_hosted_profile_ballotpedia_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_ballotpedia_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_ballotpedia_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for politician from Facebook, cached on We Vote's servers. See also facebook_profile_image_url_https.
    we_vote_hosted_profile_facebook_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for candidate from LinkedIn, cached on We Vote's servers. See also linkedin_profile_image_url_https.
    we_vote_hosted_profile_linkedin_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_linkedin_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_linkedin_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for politician from Twitter, cached on We Vote's servers. See local master twitter_profile_image_url_https.
    we_vote_hosted_profile_twitter_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for politician uploaded to We Vote's servers.
    we_vote_hosted_profile_uploaded_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for politician from Vote USA, cached on We Vote's servers. See local master vote_usa_profile_image_url_https
    we_vote_hosted_profile_vote_usa_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for candidate from Wikipedia, cached on We Vote's servers. See also wikipedia_profile_image_url_https.
    we_vote_hosted_profile_wikipedia_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_wikipedia_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_wikipedia_image_url_tiny = models.TextField(blank=True, null=True)
    # Image we are using as the profile photo (could be sourced from Twitter, Facebook, etc.)
    we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    # ctcl politician fields
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=36, null=True, blank=True)
    instagram_handle = models.TextField(verbose_name="politician's instagram handle", blank=True, null=True)
    instagram_followers_count = models.IntegerField(
        verbose_name="count of politician's instagram followers", null=True, blank=True)
    # As we add more years here, update /wevote_settings/constants.py IS_BATTLEGROUND_YEARS_AVAILABLE
    is_battleground_race_2019 = models.BooleanField(default=False, null=False)
    is_battleground_race_2020 = models.BooleanField(default=False, null=False)
    is_battleground_race_2021 = models.BooleanField(default=False, null=False)
    is_battleground_race_2022 = models.BooleanField(default=False, null=False)
    is_battleground_race_2023 = models.BooleanField(default=False, null=False)
    is_battleground_race_2024 = models.BooleanField(default=False, null=False)
    is_battleground_race_2025 = models.BooleanField(default=False, null=False)
    is_battleground_race_2026 = models.BooleanField(default=False, null=False)
    # Every politician has one default CampaignX entry that follows them over time. Campaigns with
    #  a linked_politician_we_vote_id are auto-generated by We Vote.
    # This is not the same as saying that a CampaignX is supporting or opposing this politician -- we use
    #  the CampaignXPolitician table to store links to politicians.
    linked_campaignx_we_vote_id = models.CharField(max_length=255, null=True, unique=True, db_index=True)
    linked_campaignx_we_vote_id_date_last_updated = models.DateTimeField(null=True)
    linkedin_url = models.TextField(null=True, blank=True)
    linkedin_photo_url = models.TextField(verbose_name='url of remote linkedin profile photo', blank=True, null=True)
    linkedin_profile_image_url_https = models.TextField(
        verbose_name='locally cached candidate profile image from linkedin', blank=True, null=True)
    ocd_id_state_mismatch_found = models.BooleanField(default=False, null=False)
    politician_facebook_id = models.CharField(
        verbose_name='politician facebook user name', max_length=255, null=True, unique=False)
    politician_phone_number = models.CharField(max_length=255, null=True, unique=False)
    politician_phone_number2 = models.CharField(max_length=255, null=True, unique=False)
    politician_phone_number3 = models.CharField(max_length=255, null=True, unique=False)
    politician_googleplus_id = models.CharField(
        verbose_name='politician googleplus profile name', max_length=255, null=True, unique=False)
    politician_youtube_id = models.CharField(
        verbose_name='politician youtube profile name', max_length=255, null=True, unique=False)
    # DEPRECATE after transferring all data to politician_email
    politician_email_address = models.CharField(max_length=255, null=True, unique=False)
    politician_email = models.CharField(max_length=255, null=True, unique=False)
    politician_email2 = models.CharField(max_length=255, null=True, unique=False)
    politician_email3 = models.CharField(max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="politician plain text name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="politician location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(
        verbose_name="number of twitter followers", null=False, blank=True, default=0)
    # This is the master image cached on We Vote servers. Note that we do not keep the original image URL from Twitter.
    twitter_profile_image_url_https = models.TextField(
        verbose_name='locally cached url of politician profile image from twitter', blank=True, null=True)
    twitter_profile_background_image_url_https = models.TextField(
        verbose_name='tile-able background from twitter', blank=True, null=True)
    twitter_profile_banner_url_https = models.TextField(
        verbose_name='profile banner image from twitter', blank=True, null=True)
    twitter_description = models.CharField(
        verbose_name="Text description of this organization from twitter.", max_length=255, null=True, blank=True)
    youtube_url = models.TextField(blank=True, null=True)
    date_last_updated = models.DateTimeField(null=True, auto_now=True)
    date_last_updated_from_candidate = models.DateTimeField(null=True, default=None)
    profile_image_background_color = models.CharField(blank=True, null=True, max_length=7)
    profile_image_background_color_needed = models.BooleanField(null=True)
    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_politician_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "pol" = tells us this is a unique id for a Politician
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}pol{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        if self.maplight_id == "":  # We want this to be unique IF there is a value, and otherwise "None"
            self.maplight_id = None
        super(Politician, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.last_name

    def get_recommendation(self) -> list[str]:

        """
            Get a list of recommended politicians for the current politician.
            Returns:
                list[str]: A list of We Vote IDs of recommended politicians.
                If no recommendations are found, the list will be empty.
        """
        politician_manager = PoliticianManager()
        results = politician_manager.fetch_recommend_list_by_we_vote_id(self.we_vote_id)
        return results

    class Meta:
        ordering = ('last_name',)

    def display_full_name(self):
        if self.politician_name:
            return self.politician_name
        elif self.first_name and self.last_name:
            return self.first_name + " " + self.last_name
        elif self.google_civic_candidate_name:
            return self.google_civic_candidate_name
        else:
            return self.first_name + " " + self.last_name

    def display_personal_statement(self):
        if self.twitter_description:
            return self.twitter_description
        else:
            return ""

    def politician_photo_url(self):
        """
        fetch URL of politician's photo from TheUnitedStatesIo repo
        """
        if self.bioguide_id:
            url_str = 'https://theunitedstates.io/images/congress/225x275/{bioguide_id}.jpg'.format(
                bioguide_id=self.bioguide_id)
            return url_str
        else:
            return ""

    def is_female(self):
        return self.gender in [FEMALE]

    def is_gender_neutral(self):
        return self.gender in [GENDER_NEUTRAL]

    def is_male(self):
        return self.gender in [MALE]

    def is_gender_specified(self):
        return self.gender in [FEMALE, GENDER_NEUTRAL, MALE]


class RecommendedPoliticianLinkByPolitician(models.Model):
    """
       Model to store links between a politician and recommended politicians.
       Attributes:
           from_politician_we_vote_id (str): We Vote ID of the politician accessed by User.
           recommended_politician_we_vote_id (str):  We Vote ID of the recommended politician.
       Note:
           This model is configured to store up to five associated recommended politicians per one politician.
           For instance,
           from_politician_we_vote_id,   recommended_politician_we_vote_id
           ww1,                          ww2
           ww1,                          ww5
           ww1,                          ww6
           ww1,                          ww4
           ww1,                          ww9
           ww2,                          ww4
              ,
              ,
              ,
       Example:
           A record in this model signifies that 'from_politician_we_vote_id' recommends 'recommended_politician_we_vote_id'.
       """

    from_politician_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    recommended_politician_we_vote_id = models.CharField(max_length=255, null=True, unique=False)

    def __str__(self):
        return f"RecommendedPoliticianLinkByPolitician(id={self.from_politician_we_vote_id}, from_politician_we_vote_id={self.from_politician_we_vote_id}, recommended_politician_we_vote_id={self.recommended_politician_we_vote_id})"


class PoliticiansAreNotDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two politicians as NOT duplicates
    """
    MultipleObjectsReturned = None
    DoesNotExist = None
    objects = None
    politician1_we_vote_id = models.CharField(
        verbose_name="first politician we are tracking", max_length=255, null=True, unique=False)
    politician2_we_vote_id = models.CharField(
        verbose_name="second politician we are tracking", max_length=255, null=True, unique=False)

    def fetch_other_politician_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.politician1_we_vote_id:
            return self.politician2_we_vote_id
        elif one_we_vote_id == self.politician2_we_vote_id:
            return self.politician1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class PoliticiansArePossibleDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two politicians as possible duplicates
    """
    politician1_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    politician2_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    state_code = models.CharField(max_length=2, null=True)

    def fetch_other_politician_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.politician1_we_vote_id:
            return self.politician2_we_vote_id
        elif one_we_vote_id == self.politician2_we_vote_id:
            return self.politician1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class PoliticianChangeLog(models.Model):
    batch_process_id = models.PositiveIntegerField(db_index=True, null=True, unique=False)
    politician_we_vote_id = models.CharField(max_length=255, null=False, unique=False)
    changed_by_name = models.CharField(max_length=255, default=None, null=True)
    changed_by_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    change_description = models.TextField(null=True, blank=True)
    log_datetime = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    # We keep track of which volunteer adds links to social accounts. We run reports seeing when any of these fields
    # are set, so we can show the changed_by_voter_we_vote_id who collected the data.
    is_ballotpedia_added = models.BooleanField(db_index=True, default=None, null=True)  # New Ballotpedia link
    is_ballotpedia_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_facebook_added = models.BooleanField(db_index=True, default=None, null=True)  # New Facebook account added
    is_facebook_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_from_twitter = models.BooleanField(db_index=True, default=None, null=True)  # Error retrieving from Twitter
    is_linkedin_added = models.BooleanField(db_index=True, default=None, null=True)  # New LinkedIn link added
    is_linkedin_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_official_statement_added = models.BooleanField(db_index=True, default=None, null=True)  # New Official Statement
    is_official_statement_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_photo_added = models.BooleanField(db_index=True, default=None, null=True)  # New Photo added
    is_photo_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_politician_analysis_done = models.BooleanField(db_index=True, default=None, null=True)  # Analysis complete
    is_politician_url_added = models.BooleanField(db_index=True, default=None, null=True)  # New Ballotpedia link
    is_politician_url_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_twitter_handle_added = models.BooleanField(db_index=True, default=None, null=True)  # New Twitter handle saved
    is_twitter_handle_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_website_added = models.BooleanField(db_index=True, default=None, null=True)  # New Website link added
    is_website_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_wikipedia_added = models.BooleanField(db_index=True, default=None, null=True)  # New Wikipedia link added
    is_wikipedia_removed = models.BooleanField(db_index=True, default=None, null=True)
    is_withdrawal_date_added = models.BooleanField(db_index=True, default=None, null=True)  # New Withdrawal Date
    is_withdrawal_date_removed = models.BooleanField(db_index=True, default=None, null=True)
    kind_of_log_entry = models.CharField(db_index=True, max_length=50, default=None, null=True)
    state_code = models.CharField(db_index=True, max_length=2, null=True)

    def change_description_augmented(self):
        # See issue.models, function of same name for full example of how this should be used
        if self.change_description:
            change_description_augmented = self.change_description
            return change_description_augmented
        else:
            return ''


class PoliticianManager(models.Manager):

    def __init__(self):
        pass

    @staticmethod
    def retrieve_recommend_list_by_we_vote_id(we_vote_id: str) -> list[RecommendedPoliticianLinkByPolitician]:

        """
        retrieve a list of recommended politicians for a given politician's we vote ID.
        Args:
            we_vote_id (str): We Vote ID of the politician.
        Returns:
            list[RecommendedPoliticianLinkByPolitician]: A list of recommended politicians linked to the given We Vote ID.
            either empty_list if it does not find anyone associated with we_vote_id
        """

        recommend_found = False
        empty_list = []
        try:
            suggested_politicians = RecommendedPoliticianLinkByPolitician.objects.using('readonly').filter(
                from_politician_we_vote_id__iexact=we_vote_id)
            suggested_politicians = list(suggested_politicians)
            if len(suggested_politicians):
                recommend_found = True

        except Exception as e:
            pass

        if recommend_found:
            return suggested_politicians

        else:
            return empty_list

    def fetch_recommend_list_by_we_vote_id(self, we_vote_id: str) -> list[str]:

        """
        Fetch a list of We Vote IDs of recommended politicians for a given politician's We Vote ID.
        Args:
            we_vote_id (str): We Vote ID of the politician.
        Returns:
            list[str]: A list of We Vote IDs of recommended politicians.
        """

        suggestion_list = []
        retrieved_recommend_list = self.retrieve_recommend_list_by_we_vote_id(we_vote_id)
        for recommended_politician in retrieved_recommend_list:
            suggestion_list.append(recommended_politician.recommended_politician_we_vote_id)
        return suggestion_list

    @staticmethod
    def add_politician_position_sorting_dates_if_needed(position_object=None, politician_we_vote_id=''):
        """
        Search for any CandidateCampaign objects for this politician in the future
         Then find the latest election that candidate is running for, so we can get
         candidate_year and candidate_ultimate_election_date.
        If no future candidate entries for this politician, set position_ultimate_election_not_linked to True
        :param position_object:
        :param politician_we_vote_id:
        :return:
        """
        candidate_list = []
        candidate_list_found = False
        position_object_updated = False
        status = ""
        success = True
        from candidate.models import CandidateManager
        candidate_manager = CandidateManager()

        if positive_value_exists(politician_we_vote_id):
            from candidate.models import CandidateListManager
            candidate_list_manager = CandidateListManager()
            results = candidate_list_manager.retrieve_candidates_from_politician(
                politician_we_vote_id=politician_we_vote_id,
                read_only=True)
            if results['candidate_list_found']:
                candidate_list = results['candidate_list']
                candidate_list_found = True
            elif not results['success']:
                status += results['status']
                success = False

        candidate_we_vote_id_list = []
        if candidate_list_found:
            for candidate in candidate_list:
                if candidate.we_vote_id not in candidate_we_vote_id_list:
                    candidate_we_vote_id_list.append(candidate.we_vote_id)

        ultimate_election_date_found = False
        if candidate_list_found and len(candidate_we_vote_id_list) > 0:
            today = datetime.now().date()
            this_year = 0
            if today and today.year:
                this_year = convert_to_int(today.year)
            date_now_as_integer = convert_date_to_date_as_integer(today)
            date_results = candidate_manager.generate_candidate_position_sorting_dates(
                candidate_we_vote_id_list=candidate_we_vote_id_list)
            if not positive_value_exists(date_results['success']):
                success = False
            if success:
                largest_year_integer = date_results['largest_year_integer']
                if largest_year_integer < this_year:
                    largest_year_integer = 0
                if positive_value_exists(largest_year_integer):
                    if not position_object.position_year:
                        position_object.position_year = largest_year_integer
                        position_object_updated = True
                    elif largest_year_integer > position_object.position_year:
                        position_object.position_year = largest_year_integer
                        position_object_updated = True

                largest_election_date_integer = date_results['largest_election_date_integer']
                if largest_election_date_integer < date_now_as_integer:
                    largest_election_date_integer = 0
                if positive_value_exists(largest_election_date_integer):
                    if not position_object.position_ultimate_election_date:
                        position_object.position_ultimate_election_date = largest_election_date_integer
                        position_object_updated = True
                        ultimate_election_date_found = True
                    elif largest_election_date_integer > position_object.position_ultimate_election_date:
                        position_object.position_ultimate_election_date = largest_election_date_integer
                        position_object_updated = True
                        ultimate_election_date_found = True
        if success and not ultimate_election_date_found:
            # If here, mark position_ultimate_election_not_linked as True and then exit
            status += "ULTIMATE_ELECTION_DATE_NOT_FOUND "
            position_object.position_ultimate_election_not_linked = True
            position_object_updated = True

        return {
            'position_object_updated':  position_object_updated,
            'position_object':          position_object,
            'status':                   status,
            'success':                  success,
        }

    @staticmethod
    def get_politician_from_politicianseofriendlypath_table(path):
        try:
            path_query = PoliticianSEOFriendlyPath.objects.all()
            path_query = path_query.filter(final_pathname_string=path)
            path_count = path_query.count()
            path_list = list(path_query)
            if path_count == 0:
                path_query = path_query.filter(Q(base_pathname_string=path))
                path_count = path_query.count()
                path_list = list(path_query)
            if path_count == 0:
                return 0, '', None, 'NO_PATH_MATCH_IN_POLITICIANSEOFRIENDLYPATH_TABLE '

            politician = Politician.objects.get(we_vote_id=path_list[0].politician_we_vote_id)

            return path_list[0].id, path_list[0].politician_we_vote_id, politician, ''
        except Exception as e:
            return 0, '', None, \
                "FAILED_TO_GET_POLITICIAN_VIA_FALLBACK_TO_POLITICIANSEOFRIENDLYPATH_TABLE: " + str(e) + ' '

    def create_politician_from_similar_object(self, similar_object):
        """
        Take We Vote candidate, organization or representative object, and create a new politician entry
        :param similar_object:
        :return:
        """
        status = ''
        success = True
        politician = None
        politician_created = False
        politician_found = False
        politician_id = 0
        politician_we_vote_id = ''

        birth_date = None
        facebook_url = None
        first_name = None
        gender = UNKNOWN
        instagram_handle = None
        last_name = None
        linkedin_url = None
        middle_name = None
        object_is_candidate = False
        object_is_organization = False
        object_is_representative = False
        political_party = None
        state_code = None
        vote_usa_politician_id = None
        if 'cand' in similar_object.we_vote_id:
            object_is_candidate = True
            facebook_url = similar_object.facebook_url
            first_name = extract_first_name_from_full_name(similar_object.candidate_name)
            instagram_handle = similar_object.instagram_handle
            middle_name = extract_middle_name_from_full_name(similar_object.candidate_name)
            last_name = extract_last_name_from_full_name(similar_object.candidate_name)
            linkedin_url = similar_object.linkedin_url
            political_party_constant = convert_to_political_party_constant(similar_object.party)
            political_party = candidate_party_display(political_party_constant)
            if positive_value_exists(similar_object.birth_day_text):
                try:
                    birth_date = datetime.strptime(similar_object.birth_day_text, '%Y-%m-%d')
                except Exception as e:
                    birth_date = None
                    status += "FAILED_CONVERTING_BIRTH_DAY_TEXT: " + str(e) + " " + \
                              str(similar_object.birth_day_text) + " "
            else:
                birth_date = None
            if positive_value_exists(similar_object.candidate_gender):
                if similar_object.candidate_gender.lower() == 'female':
                    gender = FEMALE
                elif similar_object.candidate_gender.lower() == 'male':
                    gender = MALE
                elif similar_object.candidate_gender.lower() in ['nonbinary', 'non-binary', 'non binary']:
                    gender = GENDER_NEUTRAL
                else:
                    gender = UNKNOWN
            else:
                gender = UNKNOWN
            state_code = similar_object.state_code
            vote_usa_politician_id = similar_object.vote_usa_politician_id
        elif 'org' in similar_object.we_vote_id:
            object_is_organization = True
            facebook_url = similar_object.organization_facebook

            first_name = extract_first_name_from_full_name(similar_object.organization_name)
            instagram_handle = similar_object.organization_instagram_handle
            middle_name = extract_middle_name_from_full_name(similar_object.organization_name)
            last_name = extract_last_name_from_full_name(similar_object.organization_name)
            gender = UNKNOWN
            state_code = similar_object.state_served_code
        elif 'rep' in similar_object.we_vote_id:
            # If here we are looking at representative object
            object_is_representative = True
            facebook_url = similar_object.facebook_url
            first_name = extract_first_name_from_full_name(similar_object.representative_name)
            instagram_handle = similar_object.instagram_handle
            middle_name = extract_middle_name_from_full_name(similar_object.representative_name)
            last_name = extract_last_name_from_full_name(similar_object.representative_name)
            linkedin_url = similar_object.linkedin_url
            political_party_constant = convert_to_political_party_constant(similar_object.political_party)
            political_party = candidate_party_display(political_party_constant)
            state_code = similar_object.state_code
            vote_usa_politician_id = similar_object.vote_usa_politician_id
        if object_is_candidate or object_is_organization or object_is_representative:
            try:
                politician = Politician.objects.create(
                    birth_date=birth_date,
                    facebook_url=facebook_url,
                    facebook_url_is_broken=similar_object.facebook_url_is_broken,
                    first_name=first_name,
                    gender=gender,
                    instagram_followers_count=similar_object.instagram_followers_count,
                    instagram_handle=instagram_handle,
                    last_name=last_name,
                    linkedin_url=linkedin_url,
                    middle_name=middle_name,
                    political_party=political_party,
                    profile_image_type_currently_active=similar_object.profile_image_type_currently_active,
                    state_code=state_code,
                    twitter_description=similar_object.twitter_description,
                    twitter_followers_count=similar_object.twitter_followers_count,
                    twitter_name=similar_object.twitter_name,
                    twitter_location=similar_object.twitter_location,
                    twitter_profile_background_image_url_https=similar_object.twitter_profile_background_image_url_https,
                    twitter_profile_banner_url_https=similar_object.twitter_profile_banner_url_https,
                    twitter_profile_image_url_https=similar_object.twitter_profile_image_url_https,
                    twitter_handle_updates_failing=similar_object.twitter_handle_updates_failing,
                    twitter_handle2_updates_failing=similar_object.twitter_handle2_updates_failing,
                    vote_usa_politician_id=vote_usa_politician_id,
                    we_vote_hosted_profile_facebook_image_url_large=similar_object.we_vote_hosted_profile_facebook_image_url_large,
                    we_vote_hosted_profile_facebook_image_url_medium=similar_object.we_vote_hosted_profile_facebook_image_url_medium,
                    we_vote_hosted_profile_facebook_image_url_tiny=similar_object.we_vote_hosted_profile_facebook_image_url_tiny,
                    we_vote_hosted_profile_twitter_image_url_large=similar_object.we_vote_hosted_profile_twitter_image_url_large,
                    we_vote_hosted_profile_twitter_image_url_medium=similar_object.we_vote_hosted_profile_twitter_image_url_medium,
                    we_vote_hosted_profile_twitter_image_url_tiny=similar_object.we_vote_hosted_profile_twitter_image_url_tiny,
                    we_vote_hosted_profile_uploaded_image_url_large=similar_object.we_vote_hosted_profile_uploaded_image_url_large,
                    we_vote_hosted_profile_uploaded_image_url_medium=similar_object.we_vote_hosted_profile_uploaded_image_url_medium,
                    we_vote_hosted_profile_uploaded_image_url_tiny=similar_object.we_vote_hosted_profile_uploaded_image_url_tiny,
                    we_vote_hosted_profile_vote_usa_image_url_large=similar_object.we_vote_hosted_profile_vote_usa_image_url_large,
                    we_vote_hosted_profile_vote_usa_image_url_medium=similar_object.we_vote_hosted_profile_vote_usa_image_url_medium,
                    we_vote_hosted_profile_vote_usa_image_url_tiny=similar_object.we_vote_hosted_profile_vote_usa_image_url_tiny,
                    we_vote_hosted_profile_image_url_large=similar_object.we_vote_hosted_profile_image_url_large,
                    we_vote_hosted_profile_image_url_medium=similar_object.we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=similar_object.we_vote_hosted_profile_image_url_tiny,
                    wikipedia_url=similar_object.wikipedia_url,
                    youtube_url=similar_object.youtube_url,
                )
                status += "POLITICIAN_CREATED "
                politician_created = True
                politician_found = True
                politician_id = politician.id
                politician_we_vote_id = politician.we_vote_id
            except Exception as e:
                status += "FAILED_TO_CREATE_POLITICIAN: " + str(e) + " "
                success = False

        if politician_found:
            from politician.controllers import add_twitter_handle_to_next_politician_spot
            from representative.controllers import add_value_to_next_representative_spot
            twitter_handles = []
            try:
                if object_is_candidate:
                    politician.ballotpedia_politician_url = similar_object.ballotpedia_candidate_url
                    politician.ballotpedia_politician_name = similar_object.ballotpedia_candidate_name
                    politician.politician_contact_form_url = similar_object.candidate_contact_form_url
                    politician.politician_url = similar_object.candidate_url
                    politician.google_civic_candidate_name = similar_object.google_civic_candidate_name
                    politician.google_civic_candidate_name2 = similar_object.google_civic_candidate_name2
                    politician.google_civic_candidate_name3 = similar_object.google_civic_candidate_name3
                    politician.maplight_id = similar_object.maplight_id
                    politician.politician_email = similar_object.candidate_email
                    politician.politician_name = similar_object.candidate_name
                    politician.politician_phone_number = similar_object.candidate_phone
                    politician.vote_smart_id = similar_object.vote_smart_id
                    politician.vote_usa_politician_id = similar_object.vote_usa_politician_id
                    politician.vote_usa_profile_image_url_https = similar_object.vote_usa_profile_image_url_https

                    if positive_value_exists(similar_object.candidate_twitter_handle):
                        twitter_handles.append(similar_object.candidate_twitter_handle)
                    if positive_value_exists(similar_object.candidate_twitter_handle2):
                        twitter_handles.append(similar_object.candidate_twitter_handle2)
                    if positive_value_exists(similar_object.candidate_twitter_handle3):
                        twitter_handles.append(similar_object.candidate_twitter_handle3)
                elif object_is_organization:
                    politician.politician_name = similar_object.organization_name
                    if positive_value_exists(similar_object.organization_phone1):
                        politician.politician_phone_number = similar_object.organization_phone1
                    email_list = []
                    if positive_value_exists(similar_object.organization_email):
                        email_list.append(similar_object.organization_email)
                    if positive_value_exists(similar_object.facebook_email):
                        email_list.append(similar_object.facebook_email)
                    if 0 in email_list and positive_value_exists(email_list[0]):
                        politician.politician_email = email_list[0]
                    if 1 in email_list and positive_value_exists(email_list[1]):
                        politician.politician_email2 = email_list[1]
                    if positive_value_exists(similar_object.organization_twitter_handle):
                        twitter_handles.append(similar_object.organization_twitter_handle)
                    politician.vote_smart_id = similar_object.vote_smart_id
                elif object_is_representative:
                    politician.ballotpedia_politician_url = similar_object.ballotpedia_representative_url
                    politician.google_civic_candidate_name = similar_object.google_civic_representative_name
                    politician.google_civic_candidate_name2 = similar_object.google_civic_representative_name2
                    politician.google_civic_candidate_name3 = similar_object.google_civic_representative_name3
                    if positive_value_exists(similar_object.representative_twitter_handle):
                        twitter_handles.append(similar_object.representative_twitter_handle)
                    politician.politician_contact_form_url = similar_object.representative_contact_form_url
                    politician.politician_email = similar_object.representative_email
                    politician.politician_email2 = similar_object.representative_email2
                    politician.politician_email3 = similar_object.representative_email3
                    politician.politician_name = similar_object.representative_name
                    politician.politician_phone_number = similar_object.representative_phone
                    if positive_value_exists(similar_object.representative_url):
                        results = add_value_to_next_representative_spot(
                            field_name_base='politician_url',
                            new_value_to_add=similar_object.representative_url,
                            representative=politician,
                        )
                        if results['success'] and results['values_changed']:
                            politician = results['representative']
                        if not results['success']:
                            status += results['status']
                    if positive_value_exists(similar_object.representative_url2):
                        results = add_value_to_next_representative_spot(
                            field_name_base='politician_url',
                            new_value_to_add=similar_object.representative_url2,
                            representative=politician,
                        )
                        if results['success'] and results['values_changed']:
                            politician = results['representative']
                        if not results['success']:
                            status += results['status']
                    if positive_value_exists(similar_object.representative_url3):
                        results = add_value_to_next_representative_spot(
                            field_name_base='politician_url',
                            new_value_to_add=similar_object.representative_url3,
                            representative=politician,
                        )
                        if results['success'] and results['values_changed']:
                            politician = results['representative']
                        if not results['success']:
                            status += results['status']

                    if positive_value_exists(similar_object.representative_twitter_handle):
                        twitter_handles.append(similar_object.representative_twitter_handle)
                    if positive_value_exists(similar_object.representative_twitter_handle2):
                        twitter_handles.append(similar_object.representative_twitter_handle2)
                    if positive_value_exists(similar_object.representative_twitter_handle3):
                        twitter_handles.append(similar_object.representative_twitter_handle3)

                for one_twitter_handle in twitter_handles:
                    twitter_results = add_twitter_handle_to_next_politician_spot(
                        politician, one_twitter_handle)
                    if twitter_results['success']:
                        if twitter_results['values_changed']:
                            politician = twitter_results['politician']
                    else:
                        status += twitter_results['status']
                        success = False
                politician.save()
            except Exception as e:
                status += "FAILED_TO_ADD_OTHER_FIELDS: " + str(e) + " "
                success = False

        if politician_found:
            # Generate seo_friendly_path
            try:
                results = self.generate_seo_friendly_path(
                    politician_name=politician.politician_name,
                    politician_we_vote_id=politician.we_vote_id,
                    state_code=politician.state_code,
                )
                if results['seo_friendly_path_found']:
                    politician.seo_friendly_path = results['seo_friendly_path']
                    try:
                        politician.save()
                    except Exception as e:
                        status += "FAILED_TO_SAVE_SEO_FRIENDLY_PATH: " + str(e) + " "
                        success = False
            except Exception as e:
                status += "FAILED_TO_GENERATE_SEO_FRIENDLY_PATH: " + str(e) + " "
                success = False
        results = {
            'success':                      success,
            'status':                       status,
            'politician':                   politician,
            'politician_created':           politician_created,
            'politician_found':             politician_found,
            'politician_id':                politician_id,
            'politician_we_vote_id':        politician_we_vote_id,
        }
        return results

    @staticmethod
    def politician_photo_url(politician_id):
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(politician_id=politician_id, read_only=True)

        if results['success']:
            politician = results['politician']
            return politician.politician_photo_url()
        return ""

    def retrieve_politician(
            self,
            politician_id=0,
            politician_we_vote_id='',
            read_only=False,
            seo_friendly_path='',
            voter_we_vote_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        politician = None
        politician_found = False
        success = True
        status = ''
        try:
            if positive_value_exists(politician_id):
                if positive_value_exists(read_only):
                    politician = Politician.objects.using('readonly').get(id=politician_id)
                else:
                    politician = Politician.objects.get(id=politician_id)
                politician_id = politician.id
                politician_we_vote_id = politician.we_vote_id
                politician_found = True
            elif positive_value_exists(politician_we_vote_id):
                if positive_value_exists(read_only):
                    politician = Politician.objects.using('readonly').get(we_vote_id__iexact=politician_we_vote_id)
                else:
                    politician = Politician.objects.get(we_vote_id__iexact=politician_we_vote_id)
                politician_id = politician.id
                politician_we_vote_id = politician.we_vote_id
                politician_found = True
            elif positive_value_exists(seo_friendly_path):
                if positive_value_exists(read_only):
                    politician = Politician.objects.using('readonly').get(seo_friendly_path__iexact=seo_friendly_path)
                else:
                    politician = Politician.objects.get(seo_friendly_path__iexact=seo_friendly_path)
                politician_id = politician.id
                politician_we_vote_id = politician.we_vote_id
                politician_found = True
        except Politician.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status += "MULTIPLE_POLITICIANS_FOUND "
        except Politician.DoesNotExist:
            politician_id, politician_we_vote_id, politician, status2 = \
                self.get_politician_from_politicianseofriendlypath_table(seo_friendly_path)
            status += status2
            if politician_id == 0:
                error_result = True
                exception_does_not_exist = True
                status += "NO_POLITICIAN_FOUND "
            else:
                politician_found = True
        except Exception as e:
            success = False
            status += "PROBLEM_WITH_RETRIEVE_POLITICIAN: " + str(e) + ' '

        # TODO: Implement this for Politicians
        # if positive_value_exists(campaignx_found):
        #     if positive_value_exists(campaignx_we_vote_id) and positive_value_exists(voter_we_vote_id):
        #         viewer_is_owner = campaignx_manager.is_voter_campaignx_owner(
        #             campaignx_we_vote_id=campaignx_we_vote_id, voter_we_vote_id=voter_we_vote_id)
        #
        #     campaignx_owner_object_list = campaignx_manager.retrieve_campaignx_owner_list(
        #         campaignx_we_vote_id_list=[campaignx_we_vote_id], viewer_is_owner=False)
        #     for campaignx_owner in campaignx_owner_object_list:
        #         campaign_owner_dict = {
        #             'organization_name':                        campaignx_owner.organization_name,
        #             'organization_we_vote_id':                  campaignx_owner.organization_we_vote_id,
        #             'feature_this_profile_image':               campaignx_owner.feature_this_profile_image,
        #             'visible_to_public':                        campaignx_owner.visible_to_public,
        #             'we_vote_hosted_profile_image_url_medium':campaignx_owner.we_vote_hosted_profile_image_url_medium,
        #             'we_vote_hosted_profile_image_url_tiny':    campaignx_owner.we_vote_hosted_profile_image_url_tiny,
        #         }
        #         campaignx_owner_list.append(campaign_owner_dict)
        politician_owner_list = []

        results = {
            'success':                      success,
            'status':                       status,
            'politician':                   politician,
            'politician_found':             politician_found,
            'politician_id':                politician_id,
            'politician_owner_list':        politician_owner_list,
            'politician_we_vote_id':        politician_we_vote_id,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def retrieve_politician_from_we_vote_id(self, politician_we_vote_id):
        return self.retrieve_politician(politician_we_vote_id=politician_we_vote_id)

    @staticmethod
    def create_politician_name_filter(
            filters=[],
            politician_name='',
            queryset=None,
            return_close_matches=False,
            state_code=''):
        filter_set = False
        if politician_name:
            if positive_value_exists(return_close_matches):
                if positive_value_exists(state_code):
                    new_filter = Q(politician_name__icontains=politician_name,
                                   state_code__iexact=state_code)
                else:
                    new_filter = Q(politician_name__icontains=politician_name)
            else:
                if positive_value_exists(state_code):
                    new_filter = Q(politician_name__iexact=politician_name,
                                   state_code__iexact=state_code)
                else:
                    new_filter = Q(politician_name__iexact=politician_name)
            filter_set = True
            filters.append(new_filter)

            search_words = politician_name.split()
            if len(search_words) > 0:
                search_filters = []
                for one_word in search_words:
                    if positive_value_exists(state_code):
                        search_filter = Q(
                            politician_name__icontains=one_word,
                            state_code__iexact=state_code)
                    else:
                        search_filter = Q(politician_name__icontains=one_word)
                    search_filters.append(search_filter)
                # Add the first query
                if len(search_filters) > 0:
                    final_search_filters = search_filters.pop()
                    if positive_value_exists(return_close_matches):
                        # ..."OR" the remaining items in the list
                        for item in search_filters:
                            final_search_filters |= item
                    else:
                        # ..."AND" the remaining items in the list
                        for item in search_filters:
                            final_search_filters &= item
                    queryset = queryset.filter(final_search_filters)

        results = {
            'filters':      filters,
            'filter_set':   filter_set,
            'queryset':     queryset,
        }
        return results

    def retrieve_all_politicians_that_might_match_similar_object(
            self,
            facebook_url_list=[],
            full_name_list=[],
            instagram_handle='',
            maplight_id='',
            return_close_matches=True,
            state_code='',
            twitter_handle_list=[],
            vote_smart_id='',
            vote_usa_politician_id='',
            read_only=True,
    ):
        politician_list = []
        politician_list_found = False
        politician = None
        politician_found = False
        status = ''

        try:
            filter_set = False
            if positive_value_exists(read_only):
                politician_queryset = Politician.objects.using('readonly').all()
            else:
                politician_queryset = Politician.objects.all()

            filters = []
            for facebook_url in facebook_url_list:
                filter_set = True
                if positive_value_exists(facebook_url):
                    new_filter = (
                        Q(facebook_url__iexact=facebook_url) |
                        Q(facebook_url2__iexact=facebook_url) |
                        Q(facebook_url3__iexact=facebook_url)
                    )
                    filters.append(new_filter)

            if positive_value_exists(instagram_handle):
                new_filter = Q(instagram_handle__iexact=instagram_handle)
                filter_set = True
                filters.append(new_filter)

            if positive_value_exists(maplight_id):
                new_filter = Q(maplight_id__iexact=maplight_id)
                filter_set = True
                filters.append(new_filter)

            for twitter_handle in twitter_handle_list:
                if positive_value_exists(twitter_handle):
                    filter_set = True
                    new_filter = (
                        Q(politician_twitter_handle__iexact=twitter_handle) |
                        Q(politician_twitter_handle2__iexact=twitter_handle) |
                        Q(politician_twitter_handle3__iexact=twitter_handle) |
                        Q(politician_twitter_handle4__iexact=twitter_handle) |
                        Q(politician_twitter_handle5__iexact=twitter_handle)
                    )
                    filters.append(new_filter)

            for full_name in full_name_list:
                if positive_value_exists(full_name):
                    filter_results = self.create_politician_name_filter(
                        filters=filters,
                        politician_name=full_name,
                        queryset=politician_queryset,
                        return_close_matches=return_close_matches,
                        state_code=state_code,
                    )
                    if filter_results['filter_set']:
                        filter_set = True
                        filters = filter_results['filters']
                    politician_queryset = filter_results['queryset']

            if positive_value_exists(vote_smart_id):
                new_filter = Q(vote_smart_id__iexact=vote_smart_id)
                filter_set = True
                filters.append(new_filter)

            if positive_value_exists(vote_usa_politician_id):
                new_filter = Q(vote_usa_politician_id__iexact=vote_usa_politician_id)
                filter_set = True
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                politician_queryset = politician_queryset.filter(final_filters)

            if filter_set:
                politician_list = list(politician_queryset)
            else:
                politician_list = []

            if len(politician_list) == 1:
                politician_found = True
                politician_list_found = False
                politician = politician_list[0]
                status += 'ONE_POLITICIAN_RETRIEVED '
            elif len(politician_list) > 1:
                politician_found = False
                politician_list_found = True
                status += 'POLITICIAN_LIST_RETRIEVED '
            else:
                status += 'NO_POLITICIANS_RETRIEVED '
            success = True
        except Exception as e:
            status = 'FAILED retrieve_all_politicians_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        # TODO DALE If nothing found, look for a national entry for this candidate -- i.e. Presidential candidates
        if not politician_found and not politician_list_found:
            pass

        results = {
            'success':                  success,
            'status':                   status,
            'politician_list_found':    politician_list_found,
            'politician_list':          politician_list,
            'politician_found':         politician_found,
            'politician':               politician,
        }
        return results

    def reset_politician_image_details_from_candidate(self, candidate, twitter_profile_image_url_https,
                                                      twitter_profile_background_image_url_https,
                                                      twitter_profile_banner_url_https):
        """
        Reset an Politician entry with original image details from we vote image.
        :param candidate:
        :param twitter_profile_image_url_https:
        :param twitter_profile_background_image_url_https:
        :param twitter_profile_banner_url_https:
        :return:
        """
        politician_details = self.retrieve_politician(
            politician_we_vote_id=candidate.politician_we_vote_id,
            read_only=False)
        politician = politician_details['politician']
        if politician_details['success']:
            politician.we_vote_hosted_profile_image_url_medium = ''
            politician.we_vote_hosted_profile_image_url_large = ''
            politician.we_vote_hosted_profile_image_url_tiny = ''

            politician.save()
            success = True
            status = "RESET_POLITICIAN_IMAGE_DETAILS"
        else:
            success = False
            status = "POLITICIAN_NOT_FOUND_IN_RESET_IMAGE_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'politician':   politician
        }
        return results

    @staticmethod
    def search_politicians(name_search_terms=None):
        status = ""
        success = True
        politician_search_results_list = []

        try:
            queryset = Politician.objects.all()
            if name_search_terms is not None:
                name_search_words = name_search_terms.split()
            else:
                name_search_words = []
            for one_word in name_search_words:
                filters = []  # Reset for each search word
                new_filter = Q(politician_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_twitter_handle__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_twitter_handle2__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_twitter_handle3__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_twitter_handle4__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(politician_twitter_handle5__icontains=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    queryset = queryset.filter(final_filters)

            politician_search_results_list = list(queryset)
        except Exception as e:
            success = False
            status += "ERROR_SEARCHING_POLITICIANS: " + str(e) + " "

        results = {
            'status':                           status,
            'success':                          success,
            'politician_search_results_list':   politician_search_results_list,
        }
        return results

    # TODO: Get rid of this function and replace with update_politician_details_from_candidate in politician/controllers.py
    def update_politician_details_from_candidate(self, candidate):
        """
        Update a politician entry with details retrieved from candidate
        :param candidate:
        :return:
        """
        status = ''
        success = True
        values_changed = False
        politician_details = self.retrieve_politician(
            politician_we_vote_id=candidate.politician_we_vote_id,
            read_only=False)
        politician = politician_details['politician']
        from politician.controllers import add_twitter_handle_to_next_politician_spot
        if politician_details['success'] and politician:
            # Politician found so update politician details with candidate details
            first_name = extract_first_name_from_full_name(candidate.candidate_name)
            middle_name = extract_middle_name_from_full_name(candidate.candidate_name)
            last_name = extract_last_name_from_full_name(candidate.candidate_name)
            if positive_value_exists(first_name) and first_name != politician.first_name:
                politician.first_name = first_name
                values_changed = True
            if positive_value_exists(last_name) and last_name != politician.last_name:
                politician.last_name = last_name
                values_changed = True
            if positive_value_exists(middle_name) and middle_name != politician.middle_name:
                politician.middle_name = middle_name
                values_changed = True
            if positive_value_exists(candidate.party):
                if convert_to_political_party_constant(candidate.party) != politician.political_party:
                    politician.political_party = convert_to_political_party_constant(candidate.party)
                    values_changed = True
            if positive_value_exists(candidate.vote_smart_id) and candidate.vote_smart_id != politician.vote_smart_id:
                politician.vote_smart_id = candidate.vote_smart_id
                values_changed = True
            if positive_value_exists(candidate.maplight_id) and candidate.maplight_id != politician.maplight_id:
                politician.maplight_id = candidate.maplight_id
                values_changed = True
            if positive_value_exists(candidate.candidate_name) and \
                    candidate.candidate_name != politician.politician_name:
                politician.politician_name = candidate.candidate_name
                values_changed = True
            if positive_value_exists(candidate.google_civic_candidate_name) and \
                    candidate.google_civic_candidate_name != politician.google_civic_candidate_name:
                politician.google_civic_candidate_name = candidate.google_civic_candidate_name
                values_changed = True
            if positive_value_exists(candidate.state_code) and candidate.state_code != politician.state_code:
                politician.state_code = candidate.state_code
                values_changed = True
            if positive_value_exists(candidate.candidate_twitter_handle):
                add_results = add_twitter_handle_to_next_politician_spot(politician, candidate.candidate_twitter_handle)
                if add_results['success']:
                    politician = add_results['politician']
                    values_changed = add_results['values_changed']
                else:
                    status += 'FAILED_TO_ADD_ONE_TWITTER_HANDLE '
                    success = False
            if positive_value_exists(candidate.we_vote_hosted_profile_image_url_large) and \
                    candidate.we_vote_hosted_profile_image_url_large != \
                    politician.we_vote_hosted_profile_image_url_large:
                politician.we_vote_hosted_profile_image_url_large = candidate.we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(candidate.we_vote_hosted_profile_image_url_medium) and \
                    candidate.we_vote_hosted_profile_image_url_medium != \
                    politician.we_vote_hosted_profile_image_url_medium:
                politician.we_vote_hosted_profile_image_url_medium = candidate.we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(candidate.we_vote_hosted_profile_image_url_tiny) and \
                    candidate.we_vote_hosted_profile_image_url_tiny != politician.we_vote_hosted_profile_image_url_tiny:
                politician.we_vote_hosted_profile_image_url_tiny = candidate.we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if values_changed:
                politician.save()
                status += "SAVED_POLITICIAN_DETAILS"
            else:
                status += "NO_CHANGES_SAVED_TO_POLITICIAN_DETAILS"
        else:
            success = False
            status += "POLITICIAN_NOT_FOUND"
        results = {
            'success':      success,
            'status':       status,
            'politician':   politician
        }
        return results

    def update_or_create_politician_from_candidate(self, candidate):
        """
        Take We Vote candidate object, and map it to update_or_create_politician
        :param candidate:
        :return:
        """

        first_name = extract_first_name_from_full_name(candidate.candidate_name)
        middle_name = extract_middle_name_from_full_name(candidate.candidate_name)
        last_name = extract_last_name_from_full_name(candidate.candidate_name)
        political_party = convert_to_political_party_constant(candidate.party)
        # TODO Add all other identifiers from other systems
        updated_politician_values = {
            'vote_smart_id':                            candidate.vote_smart_id,
            'vote_usa_politician_id':                   candidate.vote_usa_politician_id,
            'maplight_id':                              candidate.maplight_id,
            'politician_name':                          candidate.candidate_name,
            'google_civic_candidate_name':              candidate.google_civic_candidate_name,
            'state_code':                               candidate.state_code,
            # See below
            # 'politician_twitter_handle':                candidate.candidate_twitter_handle,
            'we_vote_hosted_profile_image_url_large':   candidate.we_vote_hosted_profile_image_url_large,
            'we_vote_hosted_profile_image_url_medium':  candidate.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_image_url_tiny':    candidate.we_vote_hosted_profile_image_url_tiny,
            'first_name':                               first_name,
            'middle_name':                              middle_name,
            'last_name':                                last_name,
            'political_party':                          political_party,
        }

        results = self.update_or_create_politician(
            updated_politician_values=updated_politician_values,
            politician_we_vote_id=candidate.politician_we_vote_id,
            vote_usa_politician_id=candidate.vote_usa_politician_id,
            candidate_twitter_handle=candidate.candidate_twitter_handle,
            candidate_name=candidate.candidate_name,
            state_code=candidate.state_code)
        from politician.controllers import add_twitter_handle_to_next_politician_spot
        if results['success']:
            politician = results['politician']
            twitter_results = add_twitter_handle_to_next_politician_spot(politician, candidate.candidate_twitter_handle)
            if twitter_results['success']:
                if twitter_results['values_changed']:
                    politician = twitter_results['politician']
                    politician.save()
            else:
                results['status'] += twitter_results['status']
                results['success'] = False
        return results

    @staticmethod
    def update_or_create_politician(
            updated_politician_values={},
            politician_we_vote_id='',
            vote_smart_id=0,
            vote_usa_politician_id='',
            maplight_id="",
            candidate_twitter_handle="",
            candidate_name="",
            state_code="",
            first_name="",
            middle_name="",
            last_name=""):
        """
        Either update or create a politician entry. The individual variables passed in are for the purpose of finding
        a politician to update, and the updated_politician_values variable contains the values we want to update to.
        """
        new_politician_created = False
        politician_found = False
        politician = Politician()
        status = ''

        try:
            # Note: When we decide to start updating candidate_name elsewhere within We Vote, we should stop
            #  updating candidate_name via subsequent Google Civic imports

            # If coming from a record that has already been in We Vote
            if positive_value_exists(politician_we_vote_id):
                politician, new_politician_created = \
                    Politician.objects.update_or_create(
                        we_vote_id__iexact=politician_we_vote_id,
                        defaults=updated_politician_values)
                politician_found = True
            elif positive_value_exists(vote_smart_id):
                politician, new_politician_created = \
                    Politician.objects.update_or_create(
                        vote_smart_id=vote_smart_id,
                        defaults=updated_politician_values)
                politician_found = True
            elif positive_value_exists(vote_usa_politician_id):
                politician, new_politician_created = \
                    Politician.objects.update_or_create(
                        vote_usa_politician_id=vote_usa_politician_id,
                        defaults=updated_politician_values)
                politician_found = True
            elif positive_value_exists(candidate_twitter_handle):
                # For incoming twitter_handle we need to approach this differently
                query = Politician.objects.all.filter(
                    Q(politician_twitter_handle__iexact=candidate_twitter_handle) |
                    Q(politician_twitter_handle2__iexact=candidate_twitter_handle) |
                    Q(politician_twitter_handle3__iexact=candidate_twitter_handle) |
                    Q(politician_twitter_handle4__iexact=candidate_twitter_handle) |
                    Q(politician_twitter_handle5__iexact=candidate_twitter_handle)
                )
                results_list = list(query)
                if len(results_list) > 0:
                    politician = results_list[0]
                    politician_found = True
                else:
                    # Create politician
                    politician = Politician.objects.create(defaults=updated_politician_values)
                    new_politician_created = True
                    politician_found = True
            elif positive_value_exists(candidate_name) and positive_value_exists(state_code):
                state_code = state_code.lower()
                politician, new_politician_created = \
                    Politician.objects.update_or_create(
                        politician_name=candidate_name,
                        state_code=state_code,
                        defaults=updated_politician_values)
                politician_found = True
            elif positive_value_exists(first_name) and positive_value_exists(last_name) \
                    and positive_value_exists(state_code):
                state_code = state_code.lower()
                politician, new_politician_created = \
                    Politician.objects.update_or_create(
                        first_name=first_name,
                        last_name=last_name,
                        state_code=state_code,
                        defaults=updated_politician_values)
                politician_found = True
            else:
                # If here we have exhausted our set of unique identifiers
                politician_found = False
                pass

            success = True
            if politician_found:
                status += 'POLITICIAN_SAVED '
            else:
                status += 'POLITICIAN_NOT_SAVED '
        except Exception as e:
            success = False
            status = 'UNABLE_TO_UPDATE_OR_CREATE_POLITICIAN: ' + str(e) + ' '

        results = {
            'success':              success,
            'status':               status,
            'politician_created':   new_politician_created,
            'politician_found':     politician_found,
            'politician':           politician,
        }
        return results

    @staticmethod
    def fetch_politician_id_from_we_vote_id(we_vote_id):
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(politician_we_vote_id=we_vote_id, read_only=True)
        if results['success']:
            return results['politician_id']
        return 0

    @staticmethod
    def fetch_politician_we_vote_id_from_id(politician_id):
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(politician_id=politician_id, read_only=True)
        if results['success']:
            return results['politician_we_vote_id']
        return ''

    def fetch_politicians_are_not_duplicates_list_we_vote_ids(self, politician_we_vote_id):
        results = self.retrieve_politicians_are_not_duplicates_list(politician_we_vote_id)
        return results['politicians_are_not_duplicates_list_we_vote_ids']

    @staticmethod
    def create_politician_log_entry(
            batch_process_id=None,
            change_description=None,
            changes_found_dict=None,
            changed_by_name=None,
            changed_by_voter_we_vote_id=None,
            politician_we_vote_id=None,
            kind_of_log_entry=None,
            state_code=None,
    ):
        """
        Create PoliticianChangeLog data
        """
        success = True
        status = ""
        politician_log_entry_saved = False
        politician_log_entry = None
        missing_required_variable = False

        if not politician_we_vote_id:
            missing_required_variable = True
            status += 'MISSING_POLITICIAN_WE_VOTE_ID '

        if missing_required_variable:
            results = {
                'success':                      success,
                'status':                       status,
                'politician_log_entry_saved':   politician_log_entry_saved,
                'politician_log_entry':         politician_log_entry,
            }
            return results

        try:
            politician_log_entry = PoliticianChangeLog.objects.using('analytics').create(
                batch_process_id=batch_process_id,
                change_description=change_description,
                changed_by_name=changed_by_name,
                changed_by_voter_we_vote_id=changed_by_voter_we_vote_id,
                politician_we_vote_id=politician_we_vote_id,
                kind_of_log_entry=kind_of_log_entry,
                state_code=state_code,
            )
            status += 'POLITICIAN_LOG_ENTRY_SAVED '
            update_found = False
            for change_found_key, change_found_value in changes_found_dict.items():
                if hasattr(politician_log_entry, change_found_key):
                    setattr(politician_log_entry, change_found_key, change_found_value)
                    update_found = True
                else:
                    status += "** MISSING_FROM_MODEL:" + change_found_key + ' '
            if update_found:
                politician_log_entry.save()
                politician_log_entry_saved = True
                status += 'POLITICIAN_LOG_ENTRY_UPDATED '
            success = True
            politician_log_entry_saved = True
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_POLITICIAN_LOG_ENTRY: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'politician_log_entry_saved':    politician_log_entry_saved,
            'politician_log_entry':          politician_log_entry,
        }
        return results

    @staticmethod
    def create_politician_row_entry(
            politician_name='',
            politician_first_name='',
            politician_middle_name='',
            politician_last_name='',
            ctcl_uuid='',
            political_party='',
            politician_email='',
            politician_email2='',
            politician_email3='',
            politician_phone_number='',
            politician_phone_number2='',
            politician_phone_number3='',
            politician_twitter_handle='',
            politician_twitter_handle2='',
            politician_twitter_handle3='',
            politician_twitter_handle4='',
            politician_twitter_handle5='',
            politician_facebook_id='',
            politician_googleplus_id='',
            politician_youtube_id='',
            politician_website_url='',
            state_code=None,
        ):
        """

        :param politician_name:
        :param politician_first_name:
        :param politician_middle_name:
        :param politician_last_name:
        :param ctcl_uuid:
        :param political_party:
        :param politician_email:
        :param politician_email2:
        :param politician_email3:
        :param politician_phone_number:
        :param politician_phone_number2:
        :param politician_phone_number3:
        :param politician_twitter_handle:
        :param politician_twitter_handle2:
        :param politician_twitter_handle3:
        :param politician_twitter_handle4:
        :param politician_twitter_handle5:
        :param politician_facebook_id:
        :param politician_googleplus_id:
        :param politician_youtube_id:
        :param politician_website_url:
        :param state_code:
        :return:
        """
        success = False
        status = ""
        politician_updated = False
        new_politician_created = False
        new_politician = ''

        try:
            new_politician = Politician.objects.create(
                politician_name=politician_name,
                first_name=politician_first_name,
                middle_name=politician_middle_name,
                last_name=politician_last_name,
                political_party=political_party,
                politician_email=politician_email,
                politician_email2=politician_email2,
                politician_email3=politician_email3,
                politician_phone_number=politician_phone_number,
                politician_phone_number2=politician_phone_number2,
                politician_phone_number3=politician_phone_number3,
                politician_twitter_handle=politician_twitter_handle,
                politician_twitter_handle2=politician_twitter_handle2,
                politician_twitter_handle3=politician_twitter_handle3,
                politician_twitter_handle4=politician_twitter_handle4,
                politician_twitter_handle5=politician_twitter_handle5,
                politician_facebook_id=politician_facebook_id,
                politician_googleplus_id=politician_googleplus_id,
                politician_youtube_id=politician_youtube_id,
                politician_url=politician_website_url,
                state_code=state_code,
                ctcl_uuid=ctcl_uuid)
            if new_politician:
                success = True
                status += "POLITICIAN_CREATED "
                new_politician_created = True
            else:
                success = False
                status += "POLITICIAN_CREATE_FAILED "
        except Exception as e:
            success = False
            new_politician_created = False
            status += "POLITICIAN_RETRIEVE_ERROR "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'new_politician_created':   new_politician_created,
                'politician_updated':       politician_updated,
                'new_politician':           new_politician,
            }
        return results

    @staticmethod
    def update_politician_row_entry(
            politician_name='',
            politician_first_name='',
            politician_middle_name='',
            politician_last_name='',
            ctcl_uuid='',
            political_party='',
            politician_email='',
            politician_email2='',
            politician_email3='',
            politician_twitter_handle='',
            politician_twitter_handle2='',
            politician_twitter_handle3='',
            politician_twitter_handle4='',
            politician_twitter_handle5='',
            politician_phone_number='',
            politician_phone_number2='',
            politician_phone_number3='',
            politician_facebook_id='',
            politician_googleplus_id='',
            politician_youtube_id='',
            politician_website_url='',
            politician_we_vote_id=''):
        """

        :param politician_name:
        :param politician_first_name:
        :param politician_middle_name:
        :param politician_last_name:
        :param ctcl_uuid:
        :param political_party:
        :param politician_email:
        :param politician_email2:
        :param politician_email3:
        :param politician_twitter_handle:
        :param politician_twitter_handle2:
        :param politician_twitter_handle3:
        :param politician_twitter_handle4:
        :param politician_twitter_handle5:
        :param politician_phone_number:
        :param politician_phone_number2:
        :param politician_phone_number3:
        :param politician_facebook_id:
        :param politician_googleplus_id:
        :param politician_youtube_id:
        :param politician_website_url:
        :param politician_we_vote_id:
        :return:
        """
        success = False
        status = ""
        politician_updated = False
        # new_politician_created = False
        # new_politician = ''
        existing_politician_entry = ''

        try:
            existing_politician_entry = Politician.objects.get(we_vote_id__iexact=politician_we_vote_id)
            if existing_politician_entry:
                # found the existing entry, update the values
                existing_politician_entry.politician_name = politician_name
                existing_politician_entry.first_name = politician_first_name
                existing_politician_entry.middle_name = politician_middle_name
                existing_politician_entry.last_name = politician_last_name
                existing_politician_entry.party_name = political_party
                existing_politician_entry.ctcl_uuid = ctcl_uuid
                existing_politician_entry.politician_email = politician_email
                existing_politician_entry.politician_email2 = politician_email2
                existing_politician_entry.politician_email3 = politician_email3
                existing_politician_entry.politician_phone_number = politician_phone_number
                existing_politician_entry.politician_phone_number2 = politician_phone_number2
                existing_politician_entry.politician_phone_number3 = politician_phone_number3
                existing_politician_entry.politician_twitter_handle = politician_twitter_handle
                existing_politician_entry.politician_twitter_handle2 = politician_twitter_handle2
                existing_politician_entry.politician_twitter_handle3 = politician_twitter_handle3
                existing_politician_entry.politician_twitter_handle4 = politician_twitter_handle4
                existing_politician_entry.politician_twitter_handle5 = politician_twitter_handle5
                existing_politician_entry.politician_facebook_id = politician_facebook_id
                existing_politician_entry.politician_googleplus_id = politician_googleplus_id
                existing_politician_entry.politician_youtube_id = politician_youtube_id
                existing_politician_entry.politician_url = politician_website_url
                # now go ahead and save this entry (update)
                existing_politician_entry.save()
                politician_updated = True
                success = True
                status = "POLITICIAN_UPDATED"
        except Exception as e:
            success = False
            politician_updated = False
            status = "POLITICIAN_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':              success,
                'status':               status,
                'politician_updated':   politician_updated,
                'updated_politician':   existing_politician_entry,
            }
        return results

# def delete_all_politician_data():
#     with open(LEGISLATORS_CURRENT_FILE, 'rU') as politicians_current_data:
#         politicians_current_data.readline()             # Skip the header
#         reader = csv.reader(politicians_current_data)   # Create a regular tuple reader
#         for index, politician_row in enumerate(reader):
#             if index > 3:
#                 break
#             politician_entry = Politician.objects.order_by('last_name')[0]
#             politician_entry.delete()

    @staticmethod
    def retrieve_politician_list(
            limit_to_this_state_code="",
            politician_we_vote_id_list=[],
            read_only=False,
    ):
        """

        :param limit_to_this_state_code:
        :param politician_we_vote_id_list:
        :param read_only:
        :return:
        """
        status = ""
        politician_list = []
        politician_list_found = False

        try:
            if positive_value_exists(read_only):
                politician_query = Politician.objects.using('readonly').all()
            else:
                politician_query = Politician.objects.all()
            if len(politician_we_vote_id_list):
                politician_query = politician_query.filter(we_vote_id__in=politician_we_vote_id_list)
            if positive_value_exists(limit_to_this_state_code):
                politician_query = politician_query.filter(state_code__iexact=limit_to_this_state_code)
            politician_list = list(politician_query)

            if len(politician_list):
                politician_list_found = True
                status += 'POLITICIANS_RETRIEVED '
                success = True
            else:
                status += 'NO_POLITICIANS_RETRIEVED '
                success = True
        except Politician.DoesNotExist:
            # No politicians found. Not a problem.
            status += 'NO_POLITICIANS_FOUND_DoesNotExist '
            politician_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED-retrieve_politicians_for_specific_elections: ' + str(e) + ' '
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'politician_list_found':    politician_list_found,
            'politician_list':          politician_list,
        }
        return results

    @staticmethod
    def retrieve_politicians_from_non_unique_identifiers(
            state_code='',
            twitter_handle_list=[],
            politician_name='',
            ignore_politician_id_list=[],
            read_only=False):
        """

        :param state_code:
        :param twitter_handle_list:
        :param politician_name:
        :param ignore_politician_id_list:
        :param read_only:
        :return:
        """
        keep_looking_for_duplicates = True
        politician = None
        politician_found = False
        politician_list = []
        politician_list_found = False
        multiple_entries_found = False
        success = True
        status = ""

        if keep_looking_for_duplicates and len(twitter_handle_list) > 0:
            try:
                if positive_value_exists(read_only):
                    politician_query = Politician.objects.using('readonly').all()
                else:
                    politician_query = Politician.objects.all()

                twitter_filters = []
                for one_twitter_handle in twitter_handle_list:
                    one_twitter_handle_cleaned = extract_twitter_handle_from_text_string(one_twitter_handle)
                    new_filter = (
                        Q(politician_twitter_handle__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle2__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle3__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle4__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle5__iexact=one_twitter_handle_cleaned)
                    )
                    twitter_filters.append(new_filter)

                # Add the first query
                final_filters = twitter_filters.pop()
                # ...and "OR" the remaining items in the list
                for item in twitter_filters:
                    final_filters |= item

                politician_query = politician_query.filter(final_filters)

                if positive_value_exists(state_code):
                    politician_query = politician_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_politician_id_list):
                    politician_query = politician_query.exclude(we_vote_id__in=ignore_politician_id_list)

                politician_list = list(politician_query)
                if len(politician_list):
                    # At least one entry exists
                    status += 'RETRIEVE_POLITICIANS_FROM_NON_UNIQUE-POLITICIAN_LIST_RETRIEVED '
                    # if a single entry matches, update that entry
                    if len(politician_list) == 1:
                        multiple_entries_found = False
                        politician = politician_list[0]
                        politician_found = True
                        keep_looking_for_duplicates = False
                        success = True
                        status += "POLITICIAN_FOUND_BY_TWITTER "
                    else:
                        # more than one entry found
                        politician_list_found = True
                        multiple_entries_found = True
                        keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
                        status += "MULTIPLE_TWITTER_MATCHES "
            except Politician.DoesNotExist:
                success = True
                status += "RETRIEVE_POLITICIANS_FROM_NON_UNIQUE-POLITICIAN_NOT_FOUND "
            except Exception as e:
                status += "RETRIEVE_POLITICIANS_FROM_NON_UNIQUE-POLITICIAN_QUERY_FAILED1 " + str(e) + " "
                success = False
                keep_looking_for_duplicates = False

        # twitter handle does not exist, next look up against other data that might match
        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search by Candidate name exact match
            try:
                if positive_value_exists(read_only):
                    politician_query = Politician.objects.using('readonly').all()
                else:
                    politician_query = Politician.objects.all()

                politician_query = politician_query.filter(
                    Q(politician_name__iexact=politician_name) |
                    Q(google_civic_candidate_name__iexact=politician_name) |
                    Q(google_civic_candidate_name2__iexact=politician_name) |
                    Q(google_civic_candidate_name3__iexact=politician_name)
                )

                if positive_value_exists(state_code):
                    politician_query = politician_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_politician_id_list):
                    politician_query = politician_query.exclude(we_vote_id__in=ignore_politician_id_list)

                politician_list = list(politician_query)
                if len(politician_list):
                    # entry exists
                    status += 'POLITICIAN_ENTRY_EXISTS1 '
                    success = True
                    # if a single entry matches, update that entry
                    if len(politician_list) == 1:
                        politician = politician_list[0]
                        politician_found = True
                        status += politician.we_vote_id + " "
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in Politician
                        politician_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    success = True
                    status += 'POLITICIAN_ENTRY_NOT_FOUND-EXACT '

            except Politician.DoesNotExist:
                success = True
                status += "RETRIEVE_POLITICIANS_FROM_NON_UNIQUE-POLITICIAN_NOT_FOUND-EXACT_MATCH "
            except Exception as e:
                status += "RETRIEVE_POLITICIANS_FROM_NON_UNIQUE-POLITICIAN_QUERY_FAILED2: " + str(e) + " "
                success = False

        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search for Candidate(s) that contains the same first and last names
            first_name = extract_first_name_from_full_name(politician_name)
            last_name = extract_last_name_from_full_name(politician_name)
            if positive_value_exists(first_name) and positive_value_exists(last_name):
                try:
                    if positive_value_exists(read_only):
                        politician_query = Politician.objects.using('readonly').all()
                    else:
                        politician_query = Politician.objects.all()

                    politician_query = politician_query.filter(
                        (Q(politician_name__icontains=first_name) & Q(politician_name__icontains=last_name)) |
                        (Q(google_civic_candidate_name__icontains=first_name) &
                         Q(google_civic_candidate_name__icontains=last_name)) |
                        (Q(google_civic_candidate_name2__icontains=first_name) &
                         Q(google_civic_candidate_name2__icontains=last_name)) |
                        (Q(google_civic_candidate_name3__icontains=first_name) &
                         Q(google_civic_candidate_name3__icontains=last_name))
                    )

                    if positive_value_exists(state_code):
                        politician_query = politician_query.filter(state_code__iexact=state_code)

                    if positive_value_exists(ignore_politician_id_list):
                        politician_query = politician_query.exclude(we_vote_id__in=ignore_politician_id_list)

                    politician_list = list(politician_query)
                    if len(politician_list):
                        # entry exists
                        status += 'POLITICIAN_ENTRY_EXISTS2 '
                        success = True
                        # if a single entry matches, update that entry
                        if len(politician_list) == 1:
                            politician = politician_list[0]
                            politician_found = True
                            status += politician.we_vote_id + " "
                            keep_looking_for_duplicates = False
                        else:
                            # more than one entry found with a match in Politician
                            politician_list_found = True
                            keep_looking_for_duplicates = False
                            multiple_entries_found = True
                    else:
                        status += 'POLITICIAN_ENTRY_NOT_FOUND-FIRST_OR_LAST '
                        success = True
                except Politician.DoesNotExist:
                    status += "RETRIEVE_POLITICIANS_FROM_NON_UNIQUE-POLITICIAN_NOT_FOUND-FIRST_OR_LAST_NAME "
                    success = True
                except Exception as e:
                    status += "RETRIEVE_POLITICIANS_FROM_NON_UNIQUE-POLITICIAN_QUERY_FAILED3: " + str(e) + " "
                    success = False

        results = {
            'success':                  success,
            'status':                   status,
            'politician_found':         politician_found,
            'politician':               politician,
            'politician_list_found':    politician_list_found,
            'politician_list':          politician_list,
            'multiple_entries_found':   multiple_entries_found,
        }
        return results

    @staticmethod
    def fetch_politicians_from_non_unique_identifiers_count(
            state_code='',
            twitter_handle_list=[],
            politician_name='',
            ignore_politician_id_list=[]):
        keep_looking_for_duplicates = True
        status = ""

        if keep_looking_for_duplicates and len(twitter_handle_list) > 0:
            try:
                politician_query = Politician.objects.using('readonly').all()
                twitter_filters = []
                for one_twitter_handle in twitter_handle_list:
                    one_twitter_handle_cleaned = extract_twitter_handle_from_text_string(one_twitter_handle)
                    new_filter = (
                        Q(politician_twitter_handle__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle2__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle3__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle4__iexact=one_twitter_handle_cleaned) |
                        Q(politician_twitter_handle5__iexact=one_twitter_handle_cleaned)
                    )
                    twitter_filters.append(new_filter)

                # Add the first query
                final_filters = twitter_filters.pop()
                # ...and "OR" the remaining items in the list
                for item in twitter_filters:
                    final_filters |= item

                politician_query = politician_query.filter(final_filters)

                if positive_value_exists(state_code):
                    politician_query = politician_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_politician_id_list):
                    politician_query = politician_query.exclude(we_vote_id__in=ignore_politician_id_list)

                politician_count = politician_query.count()
                if positive_value_exists(politician_count):
                    return politician_count
            except Politician.DoesNotExist:
                status += "FETCH_POLITICIANS_FROM_NON_UNIQUE_IDENTIFIERS_COUNT1 "
                # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search by Candidate name exact match
            try:
                politician_query = Politician.objects.using('readonly').all()
                politician_query = politician_query.filter(
                    Q(politician_name__iexact=politician_name) |
                    Q(google_civic_candidate_name__iexact=politician_name) |
                    Q(google_civic_candidate_name2__iexact=politician_name) |
                    Q(google_civic_candidate_name3__iexact=politician_name)
                )

                if positive_value_exists(state_code):
                    politician_query = politician_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_politician_id_list):
                    politician_query = politician_query.exclude(we_vote_id__in=ignore_politician_id_list)

                politician_count = politician_query.count()
                if positive_value_exists(politician_count):
                    return politician_count
            except Politician.DoesNotExist:
                status += "FETCH_POLITICIANS_FROM_NON_UNIQUE_IDENTIFIERS_COUNT2 "

        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search for Candidate(s) that contains the same first and last names
            first_name = extract_first_name_from_full_name(politician_name)
            last_name = extract_last_name_from_full_name(politician_name)
            if positive_value_exists(first_name) and positive_value_exists(last_name):
                try:
                    politician_query = Politician.objects.using('readonly').all()

                    politician_query = politician_query.filter(
                        (Q(politician_name__icontains=first_name) & Q(politician_name__icontains=last_name)) |
                        (Q(google_civic_candidate_name__icontains=first_name) &
                         Q(google_civic_candidate_name__icontains=last_name)) |
                        (Q(google_civic_candidate_name2__icontains=first_name) &
                         Q(google_civic_candidate_name2__icontains=last_name)) |
                        (Q(google_civic_candidate_name3__icontains=first_name) &
                         Q(google_civic_candidate_name3__icontains=last_name))
                    )

                    if positive_value_exists(state_code):
                        politician_query = politician_query.filter(state_code__iexact=state_code)

                    if positive_value_exists(ignore_politician_id_list):
                        politician_query = politician_query.exclude(we_vote_id__in=ignore_politician_id_list)

                    politician_count = politician_query.count()
                    if positive_value_exists(politician_count):
                        return politician_count
                except Politician.DoesNotExist:
                    status += "FETCH_POLITICIANS_FROM_NON_UNIQUE_IDENTIFIERS_COUNT3 "

        return 0

    @staticmethod
    def generate_seo_friendly_path(
            base_pathname_string=None,
            politician_name=None,
            politician_we_vote_id='',
            state_code=None):
        """
        Generate SEO friendly path for this politician. Ensure that the SEO friendly path is unique.

        :param base_pathname_string: Pass this in if we want a custom SEO friendly path
        :param politician_name:
        :param politician_we_vote_id:
        :param state_code:
        :return:
        """
        from politician.controllers_generate_seo_friendly_path import generate_seo_friendly_path_generic
        return generate_seo_friendly_path_generic(
            base_pathname_string=base_pathname_string,
            for_campaign=False,
            for_politician=True,
            politician_name=politician_name,
            politician_we_vote_id=politician_we_vote_id,
            state_code=state_code,
        )

    @staticmethod
    def retrieve_politicians_are_not_duplicates_list(politician_we_vote_id, read_only=True):
        """
        Get a list of other politician_we_vote_id's that are not duplicates
        :param politician_we_vote_id:
        :param read_only:
        :return:
        """
        # Note that the direction of the linkage does not matter
        politicians_are_not_duplicates_list1 = []
        politicians_are_not_duplicates_list2 = []
        status = ""
        try:
            if positive_value_exists(read_only):
                politicians_are_not_duplicates_list_query = \
                    PoliticiansAreNotDuplicates.objects.using('readonly').filter(
                        politician1_we_vote_id__iexact=politician_we_vote_id,
                    )
            else:
                politicians_are_not_duplicates_list_query = PoliticiansAreNotDuplicates.objects.filter(
                    politician1_we_vote_id__iexact=politician_we_vote_id,
                )
            politicians_are_not_duplicates_list1 = list(politicians_are_not_duplicates_list_query)
            success = True
            status += "POLITICIANS_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except PoliticiansAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status += 'NO_POLITICIANS_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status += "POLITICIANS_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1: " + str(e) + ' '

        if success:
            try:
                if positive_value_exists(read_only):
                    politicians_are_not_duplicates_list_query = \
                        PoliticiansAreNotDuplicates.objects.using('readonly').filter(
                            politician2_we_vote_id__iexact=politician_we_vote_id,
                        )
                else:
                    politicians_are_not_duplicates_list_query = \
                        PoliticiansAreNotDuplicates.objects.filter(
                            politician2_we_vote_id__iexact=politician_we_vote_id,
                        )
                politicians_are_not_duplicates_list2 = list(politicians_are_not_duplicates_list_query)
                success = True
                status += "POLITICIANS_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except PoliticiansAreNotDuplicates.DoesNotExist:
                success = True
                status += 'NO_POLITICIANS_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status += "POLITICIANS_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2: " + str(e) + ' '

        politicians_are_not_duplicates_list = \
            politicians_are_not_duplicates_list1 + politicians_are_not_duplicates_list2
        politicians_are_not_duplicates_list_found = positive_value_exists(len(politicians_are_not_duplicates_list))
        politicians_are_not_duplicates_list_we_vote_ids = []
        for one_entry in politicians_are_not_duplicates_list:
            if one_entry.politician1_we_vote_id != politician_we_vote_id:
                politicians_are_not_duplicates_list_we_vote_ids.append(one_entry.politician1_we_vote_id)
            elif one_entry.politician2_we_vote_id != politician_we_vote_id:
                politicians_are_not_duplicates_list_we_vote_ids.append(one_entry.politician2_we_vote_id)
        results = {
            'success':                                          success,
            'status':                                           status,
            'politicians_are_not_duplicates_list_found':        politicians_are_not_duplicates_list_found,
            'politicians_are_not_duplicates_list':              politicians_are_not_duplicates_list,
            'politicians_are_not_duplicates_list_we_vote_ids':  politicians_are_not_duplicates_list_we_vote_ids,
        }
        return results

    def retrieve_politicians_with_no_gender_id(self, start=0, count=15, show_unknowns=True):
        """
        Get the first 15 records that have gender 'U' undefined
          use gender_guesser to set the gender if male or female or androgynous (can't guess other human gender states)
          set gender_likelihood to gender
        :param start:
        :param count:
        :param show_unknowns: show "unknowns", candidates for whom the gender guesser couldn't determine their gender
        :return:
        """
        logger.error('On Entry start = ' + str(start) + '  show_unknowns = ' + str(show_unknowns))
        politician_query = Politician.objects.using('readonly').all()
        # Get all politicians who do not have gender specified
        politician_query = politician_query.filter(gender=UNKNOWN)
        number_of_rows = politician_query.count()
        politician_query = politician_query.order_by('politician_name')
        politician_query = politician_query[start:(start + count)]
        politician_list_objects = list(politician_query)
        results_list = []
        for pol in politician_list_objects:
            first = pol.first_name.lower().capitalize()

            if len(first) == 1 or (len(first) == 2 and pol.first_name[1] == '.'):
                # G. Burt Lancaster
                first = pol.middle_name.lower().capitalize()
            pol.guess = detector.get_gender(first)
            try:
                pol.displayable_guess = DISPLAYABLE_GUESS[pol.guess]
            except KeyError:
                pol.displayable_guess = DISPLAYABLE_GUESS['unknown']
                pol.guess = 'unknown'
            if pol.guess != 'unknown' or positive_value_exists(show_unknowns):
                results_list.append(pol)

        if len(results_list) == 0 and start + count < number_of_rows:
            logger.error('recursive call with new start = ' + str(start + count))
            # Make a recursive call if all the results are 'unknown's
            results_list, number_of_rows = self.retrieve_politicians_with_no_gender_id(start + count, count, show_unknowns)

        return results_list, number_of_rows

    @staticmethod
    def retrieve_politicians_with_misformatted_names(start=0, count=15, read_only=False):
        """
        Get the first 15 records that have 3 capitalized letters in a row, as long as those letters
        are not 'III' i.e. King Henry III.  Also exclude the names where the word "WITHDRAWN" has been appended when
        the politician withdrew from the race
        SELECT * FROM public.politician_politician WHERE politician_name ~ '.*?[A-Z][A-Z][A-Z].*?' and
           politician_name !~ '.*?III.*?'

        :param start:
        :param count:
        :param read_only:
        :return:
        """
        if positive_value_exists(read_only):
            politician_query = Politician.objects.using('readonly').all()
        else:
            politician_query = Politician.objects.all()
        # Get all politicians that have three capital letters in a row in their name, but exclude III (King Henry III)
        politician_query = politician_query.filter(politician_name__regex=r'.*?[A-Z][A-Z][A-Z].*?(?<!III)').\
            order_by('politician_name')
        number_of_rows = politician_query.count()
        politician_query = politician_query[start:(start + count)]
        politician_list_objects = list(politician_query)
        results_list = []
        # out = ''
        # out = 'KING HENRY III => ' + display_full_name_with_correct_capitalization('KING HENRY III') + ", "
        for x in politician_list_objects:
            name = x.politician_name
            if name.endswith('WITHDRAWN') and not bool(re.match('^[A-Z]+$', name)):
                continue
            x.person_name_normalized = display_full_name_with_correct_capitalization(name)
            x.party = x.political_party
            results_list.append(x)

        return results_list, number_of_rows

    @staticmethod
    def save_fresh_twitter_details_to_politician(
            politician=None,
            politician_we_vote_id='',
            twitter_user=None):
        """
        Update a politician entry with details retrieved from the Twitter API.
        """
        politician_updated = False
        success = True
        status = ""
        values_changed = False

        if not hasattr(twitter_user, 'twitter_id'):
            success = False
            status += "VALID_TWITTER_USER_NOT_PROVIDED "

        if success:
            if not hasattr(politician, 'politician_twitter_handle') and positive_value_exists(politician_we_vote_id):
                # Retrieve politician to update
                pass

        if not hasattr(politician, 'politician_twitter_handle'):
            status += "VALID_POLITICIAN_NOT_PROVIDED_TO_UPDATE_TWITTER_DETAILS "
            success = False

        if not positive_value_exists(politician.politician_twitter_handle) \
                and not positive_value_exists(twitter_user.twitter_handle):
            status += "POLITICIAN_TWITTER_HANDLE_MISSING "
            success = False

        # I don't think this is a problem
        # if success:
        #     if politician.politician_twitter_handle.lower() != twitter_user.twitter_handle.lower():
        #         status += "POLITICIAN_TWITTER_HANDLE_MISMATCH "
        #         success = False

        if not success:
            results = {
                'success':              success,
                'status':               status,
                'politician':           politician,
                'politician_updated':   politician_updated,
            }
            return results

        if positive_value_exists(twitter_user.twitter_description):
            if twitter_user.twitter_description != politician.twitter_description:
                politician.twitter_description = twitter_user.twitter_description
                values_changed = True
        if positive_value_exists(twitter_user.twitter_followers_count):
            if twitter_user.twitter_followers_count != politician.twitter_followers_count:
                politician.twitter_followers_count = twitter_user.twitter_followers_count
                values_changed = True
        if positive_value_exists(twitter_user.twitter_handle):
            # In case the capitalization of the name changes
            if twitter_user.twitter_handle != politician.politician_twitter_handle:
                politician.politician_twitter_handle = twitter_user.twitter_handle
                values_changed = True
        if positive_value_exists(twitter_user.twitter_handle_updates_failing):
            if twitter_user.twitter_handle_updates_failing != politician.twitter_handle_updates_failing:
                politician.twitter_handle_updates_failing = twitter_user.twitter_handle_updates_failing
                values_changed = True
        if positive_value_exists(twitter_user.twitter_id):
            if twitter_user.twitter_id != politician.twitter_user_id:
                politician.twitter_user_id = twitter_user.twitter_id
                values_changed = True
        if positive_value_exists(twitter_user.twitter_location):
            if twitter_user.twitter_location != politician.twitter_location:
                politician.twitter_location = twitter_user.twitter_location
                values_changed = True
        if positive_value_exists(twitter_user.twitter_name):
            if twitter_user.twitter_name != politician.twitter_name:
                politician.twitter_name = twitter_user.twitter_name
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_image_url_https):
            if twitter_user.twitter_profile_image_url_https != politician.twitter_profile_image_url_https:
                politician.twitter_profile_image_url_https = twitter_user.twitter_profile_image_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_background_image_url_https):
            if twitter_user.twitter_profile_background_image_url_https != \
                    politician.twitter_profile_background_image_url_https:
                politician.twitter_profile_background_image_url_https = \
                    twitter_user.twitter_profile_background_image_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_banner_url_https):
            if twitter_user.twitter_profile_banner_url_https != politician.twitter_profile_banner_url_https:
                politician.twitter_profile_banner_url_https = twitter_user.twitter_profile_banner_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_url):
            from representative.controllers import add_value_to_next_representative_spot
            results = add_value_to_next_representative_spot(
                field_name_base='politician_url',
                new_value_to_add=twitter_user.twitter_url,
                representative=politician,
            )
            if results['success'] and results['values_changed']:
                politician = results['representative']
                values_changed = True
            if not results['success']:
                status += results['status']
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_large):
            if twitter_user.we_vote_hosted_profile_image_url_large != \
                    politician.we_vote_hosted_profile_twitter_image_url_large:
                politician.we_vote_hosted_profile_twitter_image_url_large = \
                    twitter_user.we_vote_hosted_profile_image_url_large
                values_changed = True
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_medium):
            if twitter_user.we_vote_hosted_profile_image_url_medium != \
                    politician.we_vote_hosted_profile_twitter_image_url_medium:
                politician.we_vote_hosted_profile_twitter_image_url_medium = \
                    twitter_user.we_vote_hosted_profile_image_url_medium
                values_changed = True
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_tiny):
            if twitter_user.we_vote_hosted_profile_image_url_tiny != \
                    politician.we_vote_hosted_profile_twitter_image_url_tiny:
                politician.we_vote_hosted_profile_twitter_image_url_tiny = \
                    twitter_user.we_vote_hosted_profile_image_url_tiny
                values_changed = True

        if politician.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN and \
                positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_large):
            politician.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
            values_changed = True
        if politician.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
            if twitter_user.we_vote_hosted_profile_image_url_large != politician.we_vote_hosted_profile_image_url_large:
                politician.we_vote_hosted_profile_image_url_large = twitter_user.we_vote_hosted_profile_image_url_large
                values_changed = True
            if twitter_user.we_vote_hosted_profile_image_url_medium != \
                    politician.we_vote_hosted_profile_image_url_medium:
                politician.we_vote_hosted_profile_image_url_medium = \
                    twitter_user.we_vote_hosted_profile_image_url_medium
                values_changed = True
            if twitter_user.we_vote_hosted_profile_image_url_tiny != politician.we_vote_hosted_profile_image_url_tiny:
                politician.we_vote_hosted_profile_image_url_tiny = twitter_user.we_vote_hosted_profile_image_url_tiny
                values_changed = True

        if values_changed:
            try:
                politician.save()
                politician_updated = True
                success = True
                status += "SAVED_POLITICIAN_TWITTER_DETAILS "
            except Exception as e:
                success = False
                status += "NO_CHANGES_SAVED_TO_POLITICIAN_TWITTER_DETAILS: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'politician':           politician,
            'politician_updated':   politician_updated,
        }
        return results

    @staticmethod
    def update_or_create_politicians_are_not_duplicates(politician1_we_vote_id, politician2_we_vote_id):
        """
        Either update or create a politician entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_politicians_are_not_duplicates_created = False
        politicians_are_not_duplicates = None
        status = ""

        if positive_value_exists(politician1_we_vote_id) and positive_value_exists(politician2_we_vote_id):
            try:
                updated_values = {
                    'politician1_we_vote_id':    politician1_we_vote_id,
                    'politician2_we_vote_id':    politician2_we_vote_id,
                }
                politicians_are_not_duplicates, new_politicians_are_not_duplicates_created = \
                    PoliticiansAreNotDuplicates.objects.update_or_create(
                        politician1_we_vote_id__exact=politician1_we_vote_id,
                        politician2_we_vote_id__iexact=politician2_we_vote_id,
                        defaults=updated_values)
                success = True
                status += "POLITICIANS_ARE_NOT_DUPLICATES_UPDATED_OR_CREATED "
            except PoliticiansAreNotDuplicates.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_POLITICIANS_ARE_NOT_DUPLICATES_FOUND_BY_POLITICIAN_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'EXCEPTION_UPDATE_OR_CREATE_POLITICIANS_ARE_NOT_DUPLICATES ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                                      success,
            'status':                                       status,
            'MultipleObjectsReturned':                      exception_multiple_object_returned,
            'new_politicians_are_not_duplicates_created':   new_politicians_are_not_duplicates_created,
            'politicians_are_not_duplicates':               politicians_are_not_duplicates,
        }
        return results


class PoliticianSEOFriendlyPath(models.Model):
    objects = None

    @staticmethod
    def __unicode__():
        return "PoliticianSEOFriendlyPath"

    politician_we_vote_id = models.CharField(max_length=255, null=True)
    politician_name = models.CharField(max_length=255, null=False)
    base_pathname_string = models.CharField(max_length=255, null=True)
    pathname_modifier = models.CharField(max_length=10, null=True)
    final_pathname_string = models.CharField(max_length=255, null=True, unique=True, db_index=True)


class PoliticianTagLink(models.Model):
    """
    A confirmed (undisputed) link between tag & item of interest.
    """
    tag = models.ForeignKey(Tag, null=False, blank=False, verbose_name='tag unique identifier',
                            on_delete=models.deletion.DO_NOTHING)
    politician = models.ForeignKey(Politician, null=False, blank=False, verbose_name='politician unique identifier',
                                   on_delete=models.deletion.DO_NOTHING)
    # measure_id
    # office_id
    # issue_id


class PoliticianTagLinkDisputed(models.Model):
    """
    This is a highly disputed link between tag & item of interest. Generated from 'tag_added', and tag results
    are only shown to people within the cloud of the voter who posted

    We split off how things are tagged to avoid conflict wars between liberals & conservatives
    (Deal with some tags visible in some networks, and not in others - ex/ #ObamaSucks)
    """
    tag = models.ForeignKey(Tag, null=False, blank=False, verbose_name='tag unique identifier',
                            on_delete=models.deletion.DO_NOTHING)
    politician = models.ForeignKey(Politician, null=False, blank=False, verbose_name='politician unique identifier',
                                   on_delete=models.deletion.DO_NOTHING)
    # measure_id
    # office_id
    # issue_id
