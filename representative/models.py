# representative/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime
from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from candidate.models import PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_VOTE_USA, PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES
from office_held.models import OfficeHeld, OfficeHeldManager
from wevote_settings.constants import IS_BATTLEGROUND_YEARS_AVAILABLE, OFFICE_HELD_YEARS_AVAILABLE
from wevote_settings.models import fetch_next_we_vote_id_representative_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import candidate_party_display, convert_to_int, \
    display_full_name_with_correct_capitalization, \
    extract_title_from_full_name, extract_first_name_from_full_name, extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_suffix_from_full_name, extract_nickname_from_full_name, \
    extract_state_from_ocd_division_id, extract_twitter_handle_from_text_string, \
    positive_value_exists
from image.models import ORGANIZATION_ENDORSEMENTS_IMAGE_NAME

logger = wevote_functions.admin.get_logger(__name__)

# When merging representatives, these are the fields we check for figure_out_representative_conflict_values
REPRESENTATIVE_UNIQUE_IDENTIFIERS = [
    'ballotpedia_representative_url',
    'ctcl_uuid',
    'facebook_url',
    'google_civic_profile_image_url_https',
    # 'google_civic_representative_name',
    # 'google_civic_representative_name2',
    # 'google_civic_representative_name3',
    'instagram_handle',
    'is_battleground_race_2019',
    'is_battleground_race_2020',
    'is_battleground_race_2021',
    'is_battleground_race_2022',
    'is_battleground_race_2023',
    'is_battleground_race_2024',
    'is_battleground_race_2025',
    'is_battleground_race_2026',
    'linkedin_url',
    'ocd_division_id',
    'office_held_id',
    'office_held_name',
    'office_held_we_vote_id',
    'photo_url_from_google_civic',
    'political_party',
    'politician_id',
    'politician_we_vote_id',
    'representative_contact_form_url',
    # 'representative_email',
    # 'representative_email2',
    # 'representative_email3',
    'representative_name',
    # 'representative_phone',
    # 'representative_phone2',
    # 'representative_phone3',
    # 'representative_twitter_handle',
    # 'representative_twitter_handle2',
    # 'representative_twitter_handle3',
    # 'representative_url',
    # 'representative_url2',
    # 'representative_url3',
    'state_code',
    'twitter_description',
    'twitter_handle_updates_failing',
    'twitter_handle2_updates_failing',
    'twitter_location',
    'twitter_name',
    'twitter_profile_background_image_url_https',
    'twitter_profile_banner_url_https',
    'twitter_profile_image_url_https',
    'twitter_url',
    'twitter_user_id',
    'vote_usa_politician_id',
    'we_vote_hosted_profile_image_url_large',
    'we_vote_hosted_profile_image_url_medium',
    'we_vote_hosted_profile_image_url_tiny',
    'wikipedia_url',
    'year_in_office_2023',
    'year_in_office_2024',
    'year_in_office_2025',
    'year_in_office_2026',
    'youtube_url',
]


def attach_defaults_values_to_representative_object(representative, defaults):
    if 'ballotpedia_representative_url' in defaults:
        representative.ballotpedia_representative_url = defaults['ballotpedia_representative_url']
    if 'ctcl_uuid' in defaults:
        representative.ctcl_uuid = defaults['ctcl_uuid']
    if 'facebook_url' in defaults:
        representative.facebook_url = defaults['facebook_url']
    if 'google_civic_representative_name' in defaults:
        representative.google_civic_representative_name = defaults['google_civic_representative_name']
    if 'google_civic_representative_name2' in defaults:
        representative.google_civic_representative_name2 = defaults['google_civic_representative_name2']
    if 'google_civic_representative_name3' in defaults:
        representative.google_civic_representative_name3 = defaults['google_civic_representative_name3']
    if 'instagram_handle' in defaults:
        representative.instagram_handle = defaults['instagram_handle']
    if 'linkedin_url' in defaults:
        representative.linkedin_url = defaults['linkedin_url']
    if 'ocd_division_id' in defaults:
        representative.ocd_division_id = defaults['ocd_division_id']
    if 'office_held_id' in defaults:
        representative.office_held_id = defaults['office_held_id']
    if 'office_held_name' in defaults:
        representative.office_held_name = defaults['office_held_name']
    if 'office_held_we_vote_id' in defaults:
        representative.office_held_we_vote_id = defaults['office_held_we_vote_id']
    if 'political_party' in defaults:
        representative.political_party = defaults['political_party']
    if 'politician_id' in defaults:
        representative.politician_id = defaults['politician_id']
    if 'politician_we_vote_id' in defaults:
        representative.politician_we_vote_id = defaults['politician_we_vote_id']
    if 'profile_image_type_currently_active' in defaults:
        representative.profile_image_type_currently_active = defaults['profile_image_type_currently_active']
    if 'representative_contact_form_url' in defaults:
        representative.representative_contact_form_url = defaults['representative_contact_form_url']
    if 'representative_email' in defaults:
        representative.representative_email = defaults['representative_email']
    if 'representative_email2' in defaults:
        representative.representative_email2 = defaults['representative_email2']
    if 'representative_email3' in defaults:
        representative.representative_email3 = defaults['representative_email3']
    if 'representative_name' in defaults:
        representative.representative_name = defaults['representative_name']
    if 'representative_phone' in defaults:
        representative.representative_phone = defaults['representative_phone']
    if 'representative_phone2' in defaults:
        representative.representative_phone2 = defaults['representative_phone2']
    if 'representative_phone3' in defaults:
        representative.representative_phone3 = defaults['representative_phone3']
    if 'representative_twitter_handle' in defaults:
        representative.representative_twitter_handle = defaults['representative_twitter_handle']
    if 'representative_twitter_handle2' in defaults:
        representative.representative_twitter_handle2 = defaults['representative_twitter_handle2']
    if 'representative_twitter_handle3' in defaults:
        representative.representative_twitter_handle3 = defaults['representative_twitter_handle3']
    if 'representative_url' in defaults:
        representative.representative_url = defaults['representative_url']
    if 'representative_url2' in defaults:
        representative.representative_url2 = defaults['representative_url2']
    if 'representative_url3' in defaults:
        representative.representative_url3 = defaults['representative_url3']
    if 'seo_friendly_path' in defaults:
        representative.seo_friendly_path = defaults['seo_friendly_path']
    if 'state_code' in defaults:
        representative.state_code = defaults['state_code']
    if 'twitter_description' in defaults:
        representative.twitter_description = defaults['twitter_description']
    if 'twitter_followers_count' in defaults:
        representative.twitter_followers_count = defaults['twitter_followers_count']
    if 'twitter_handle_updates_failing' in defaults:
        representative.twitter_handle_updates_failing = defaults['twitter_handle_updates_failing']
    if 'twitter_handle2_updates_failing' in defaults:
        representative.twitter_handle2_updates_failing = defaults['twitter_handle2_updates_failing']
    if 'twitter_location' in defaults:
        representative.twitter_location = defaults['twitter_location']
    if 'twitter_name' in defaults:
        representative.twitter_name = defaults['twitter_name']
    if 'twitter_profile_background_image_url_https' in defaults:
        representative.twitter_profile_background_image_url_https = \
            defaults['twitter_profile_background_image_url_https']
    if 'twitter_profile_banner_url_https' in defaults:
        representative.twitter_profile_banner_url_https = defaults['twitter_profile_banner_url_https']
    if 'twitter_profile_image_url_https' in defaults:
        representative.twitter_profile_image_url_https = defaults['twitter_profile_image_url_https']
    if 'twitter_url' in defaults:
        representative.twitter_url = defaults['twitter_url']
    if 'twitter_user_id' in defaults:
        representative.twitter_user_id = defaults['twitter_user_id']
    if 'vote_usa_politician_id' in defaults:
        representative.vote_usa_politician_id = defaults['vote_usa_politician_id']
    if 'we_vote_hosted_profile_image_url_large' in defaults:
        representative.we_vote_hosted_profile_image_url_large = defaults['we_vote_hosted_profile_image_url_large']
    if 'we_vote_hosted_profile_image_url_medium' in defaults:
        representative.we_vote_hosted_profile_image_url_medium = defaults['we_vote_hosted_profile_image_url_medium']
    if 'we_vote_hosted_profile_image_url_tiny' in defaults:
        representative.we_vote_hosted_profile_image_url_tiny = defaults['we_vote_hosted_profile_image_url_tiny']
    if 'wikipedia_url' in defaults:
        representative.wikipedia_url = defaults['wikipedia_url']
    # if 'years_in_office_flags' in defaults:
    #     representative.years_in_office_flags = defaults['years_in_office_flags']
    year_in_office_list = OFFICE_HELD_YEARS_AVAILABLE
    for year in year_in_office_list:
        year_in_office_key = 'year_in_office_' + str(year)
        if year_in_office_key in defaults:
            setattr(representative, year_in_office_key, defaults[year_in_office_key])
    if 'youtube_url' in defaults:
        representative.youtube_url = defaults['youtube_url']
    return representative


class Representative(models.Model):
    # This entry is for a person elected into an office. Not the same as a Politician entry, which is the person
    #  whether they are in office or not.
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "rep", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_representative_integer
    objects = None
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this person in this position",
        max_length=255, default=None, null=True,
        blank=True, unique=True)
    ballotpedia_representative_url = models.TextField(
        verbose_name='url of representative on ballotpedia', max_length=255, blank=True, null=True)
    # CTCL representative data fields
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=36, null=True, blank=True)
    date_last_updated = models.DateTimeField(null=True, auto_now=True)
    date_last_updated_from_politician = models.DateTimeField(null=True, default=None)
    facebook_url = models.TextField(null=True, blank=True, default=None)
    facebook_url_is_broken = models.BooleanField(default=False)
    # This is the master image url cached on We Vote servers. See photo_url_from_google_civic for Original URL.
    google_civic_profile_image_url_https = models.TextField(null=True, blank=True, default=None)
    # The representative's name as passed over by Google Civic.
    # We save this, so we can match to this representative even
    # if we edit the representative's name locally.
    google_civic_representative_name = models.CharField(max_length=255, null=True)
    google_civic_representative_name2 = models.CharField(max_length=255, null=True)
    google_civic_representative_name3 = models.CharField(max_length=255, null=True)
    instagram_followers_count = models.IntegerField(null=False, blank=True, default=0)
    instagram_handle = models.CharField(max_length=255, null=True, unique=False)
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
    linked_campaignx_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    linked_campaignx_we_vote_id_date_last_updated = models.DateTimeField(null=True)
    linkedin_url = models.CharField(max_length=255, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    ocd_id_state_mismatch_checked = models.BooleanField(default=False, null=False)
    ocd_id_state_mismatch_found = models.BooleanField(default=False, null=False)
    office_held_district_name = models.CharField(max_length=255, null=True, blank=True)
    office_held_id = models.CharField(
        verbose_name="office_held_id id", max_length=255, null=True, blank=True)
    office_held_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)
    # We want to link the representative to the office held with permanent ids, so we can export and import
    office_held_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the office this representative is running for", max_length=255,
        default=None, null=True, blank=True, unique=False)
    # Image URL on Google Civic's servers.
    # See google_civic_profile_image_url_https, the master image cached on We Vote servers.
    photo_url_from_google_civic = models.TextField(null=True, blank=True)
    # The full name of the party the representative is a member of.
    political_party = models.CharField(verbose_name="political_party", max_length=255, null=True, blank=True)
    politician_deduplication_attempted = models.BooleanField(default=False)
    # politician (internal) link to local We Vote Politician entry. During setup, we need to allow this to be null.
    politician_id = models.BigIntegerField(verbose_name="politician unique identifier", null=True, blank=True)
    politician_match_attempted = models.BooleanField(default=False)
    # The persistent We Vote unique ID of the Politician, so we can export and import into other databases.
    politician_we_vote_id = models.CharField(max_length=255, null=True, blank=True)
    representative_contact_form_url = models.TextField(max_length=255, blank=True, null=True)
    # The email address for the representative
    representative_email = models.CharField(max_length=255, null=True, blank=True)
    representative_email2 = models.CharField(max_length=255, null=True, blank=True)
    representative_email3 = models.CharField(max_length=255, null=True, blank=True)
    representative_name = models.CharField(max_length=255, null=False, blank=False)
    # The voice phone number for the representative's office.
    representative_phone = models.CharField(max_length=255, null=True, blank=True)
    representative_phone2 = models.CharField(max_length=255, null=True, blank=True)
    representative_phone3 = models.CharField(max_length=255, null=True, blank=True)
    # The URL for the representative's website.
    representative_url = models.TextField(max_length=255, blank=True, null=True)
    representative_url2 = models.TextField(max_length=255, blank=True, null=True)
    representative_url3 = models.TextField(max_length=255, blank=True, null=True)
    # seo_friendly_path data is copied from the Politician object, and isn't edited directly on this object
    seo_friendly_path = models.CharField(max_length=255, null=True, unique=False, db_index=True)
    seo_friendly_path_date_last_updated = models.DateTimeField(null=True)
    state_code = models.CharField(verbose_name="state this representative serves", max_length=2, null=True)
    supporters_count = models.PositiveIntegerField(default=0)  # From linked_campaignx_we_vote_id CampaignX entry
    twitter_handle_updates_failing = models.BooleanField(default=False)
    twitter_handle2_updates_failing = models.BooleanField(default=False)
    twitter_url = models.TextField(verbose_name='twitter url of representative', blank=True, null=True)
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    representative_twitter_handle = models.CharField(max_length=255, null=True, unique=False)
    representative_twitter_handle2 = models.CharField(max_length=255, null=True, unique=False)
    representative_twitter_handle3 = models.CharField(max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="representative plain text name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="representative location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(null=False, blank=True, default=0)
    twitter_profile_image_url_https = models.TextField(verbose_name='url of logo from twitter', blank=True, null=True)
    twitter_profile_background_image_url_https = models.TextField(verbose_name='tile-able background from twitter',
                                                                  blank=True, null=True)
    twitter_profile_banner_url_https = models.TextField(verbose_name='profile banner image from twitter',
                                                        blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)
    vote_usa_politician_id = models.CharField(max_length=255, null=True, unique=False)

    # Which representative image is currently active?
    profile_image_type_currently_active = models.CharField(
        max_length=11, choices=PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES, default=PROFILE_IMAGE_TYPE_UNKNOWN)
    profile_image_background_color = models.CharField(blank=True, null=True, max_length=7)
    # Image for representative from Facebook, cached on We Vote's servers. See also facebook_profile_image_url_https.
    we_vote_hosted_profile_facebook_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for representative from Twitter, cached on We Vote's servers. See master twitter_profile_image_url_https.
    we_vote_hosted_profile_twitter_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for representative uploaded to We Vote's servers.
    we_vote_hosted_profile_uploaded_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for representative from Vote USA, cached on We Vote's servers. See master vote_usa_profile_image_url_https.
    we_vote_hosted_profile_vote_usa_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_tiny = models.TextField(blank=True, null=True)
    # Image we are using as the profile photo (could be sourced from Twitter, Facebook, etc.)
    we_vote_hosted_profile_image_url_large = models.TextField(null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(null=True)

    wikipedia_url = models.TextField(null=True)
    # Which years did this representative serve. This is master data we also cache in RepresentativeToOfficeHeldLink
    # years_in_office_flags = models.PositiveIntegerField(default=0)
    # As we add more years here, update /wevote_settings/constants.py OFFICE_HELD_YEARS_AVAILABLE
    # and attach_defaults_values_to_representative_object
    year_in_office_2023 = models.BooleanField(default=None, null=True)
    year_in_office_2024 = models.BooleanField(default=None, null=True)
    year_in_office_2025 = models.BooleanField(default=None, null=True)
    year_in_office_2026 = models.BooleanField(default=None, null=True)
    youtube_url = models.TextField(blank=True, null=True)


    def office_held(self):
        try:
            office_held = OfficeHeld.objects.get(id=self.office_held_id)
        except OfficeHeld.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            return
        except OfficeHeld.DoesNotExist:
            return
        return office_held

    def fetch_twitter_handle(self):
        if positive_value_exists(self.representative_twitter_handle):
            return self.representative_twitter_handle
        elif self.twitter_url:
            # Extract the twitter handle from twitter_url if we don't have it stored as a handle yet
            return extract_twitter_handle_from_text_string(self.twitter_url)
        return self.twitter_url

    def twitter_profile_image_url_https_bigger(self):
        if self.we_vote_hosted_profile_image_url_large:
            return self.we_vote_hosted_profile_image_url_large
        elif self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https.replace("_normal", "_bigger")
        else:
            return ''

    def twitter_profile_image_url_https_original(self):
        if self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https.replace("_normal", "")
        else:
            return ''

    def generate_twitter_link(self):
        if self.representative_twitter_handle:
            return "https://twitter.com/{twitter_handle}".format(twitter_handle=self.representative_twitter_handle)
        else:
            return ''

    def get_representative_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            # Pull this from ocdDivisionId
            if positive_value_exists(self.ocd_division_id):
                ocd_division_id = self.ocd_division_id
                return extract_state_from_ocd_division_id(ocd_division_id)
            else:
                return ''

    def display_representative_name(self):
        full_name = self.representative_name
        if full_name.isupper():
            full_name_corrected_capitalization = display_full_name_with_correct_capitalization(full_name)
            return full_name_corrected_capitalization
        return full_name

    def extract_title(self):
        full_name = self.display_representative_name()
        return extract_title_from_full_name(full_name)

    def extract_first_name(self):
        full_name = self.display_representative_name()
        return extract_first_name_from_full_name(full_name)

    def extract_middle_name(self):
        full_name = self.display_representative_name()
        return extract_middle_name_from_full_name(full_name)

    def extract_last_name(self):
        full_name = self.display_representative_name()
        return extract_last_name_from_full_name(full_name)

    def extract_suffix(self):
        full_name = self.display_representative_name()
        return extract_suffix_from_full_name(full_name)

    def extract_nickname(self):
        full_name = self.display_representative_name()
        return extract_nickname_from_full_name(full_name)

    def political_party_display(self):
        return candidate_party_display(self.political_party)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_representative_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "rep" = tells us this is a unique id for a Representative
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}rep{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(Representative, self).save(*args, **kwargs)


def mimic_google_civic_initials(name):
    modified_name = name.replace(' A ', ' A. ')
    modified_name = modified_name.replace(' B ', ' B. ')
    modified_name = modified_name.replace(' C ', ' C. ')
    modified_name = modified_name.replace(' D ', ' D. ')
    modified_name = modified_name.replace(' E ', ' E. ')
    modified_name = modified_name.replace(' F ', ' F. ')
    modified_name = modified_name.replace(' G ', ' G. ')
    modified_name = modified_name.replace(' H ', ' H. ')
    modified_name = modified_name.replace(' I ', ' I. ')
    modified_name = modified_name.replace(' J ', ' J. ')
    modified_name = modified_name.replace(' K ', ' K. ')
    modified_name = modified_name.replace(' L ', ' L. ')
    modified_name = modified_name.replace(' M ', ' M. ')
    modified_name = modified_name.replace(' N ', ' N. ')
    modified_name = modified_name.replace(' O ', ' O. ')
    modified_name = modified_name.replace(' P ', ' P. ')
    modified_name = modified_name.replace(' Q ', ' Q. ')
    modified_name = modified_name.replace(' R ', ' R. ')
    modified_name = modified_name.replace(' S ', ' S. ')
    modified_name = modified_name.replace(' T ', ' T. ')
    modified_name = modified_name.replace(' U ', ' U. ')
    modified_name = modified_name.replace(' V ', ' V. ')
    modified_name = modified_name.replace(' W ', ' W. ')
    modified_name = modified_name.replace(' X ', ' X. ')
    modified_name = modified_name.replace(' Y ', ' Y. ')
    modified_name = modified_name.replace(' Z ', ' Z. ')
    return modified_name


class RepresentativeManager(models.Manager):

    def __unicode__(self):
        return "RepresentativeManager"

    @staticmethod
    def retrieve_polling_location_we_vote_id_list_from_representatives_are_missing(
            batch_process_date_started=None,
            is_from_google_civic=False,
            state_code=''):
        polling_location_we_vote_id_list = []
        status = ''
        success = True

        try:
            query = RepresentativesMissingFromPollingLocation.objects.using('readonly')\
                .order_by('-date_last_updated')\
                .filter(issue_resolved=False)\
                .exclude(Q(polling_location_we_vote_id__isnull=True) | Q(polling_location_we_vote_id=""))
            if batch_process_date_started:
                query = query.filter(date_last_updated__gt=batch_process_date_started)
            if positive_value_exists(is_from_google_civic):
                query = query.filter(is_from_google_civic=True)
            if positive_value_exists(state_code):
                query = query.filter(state_code__iexact=state_code)
            query = query.values_list('polling_location_we_vote_id', flat=True).distinct()
            polling_location_we_vote_id_list = list(query)
        except Exception as e:
            status += "COULD_NOT_RETRIEVE_POLLING_LOCATION_LIST-EMPTY: " + str(e) + " "
        # status += "PL_LIST: " + str(polling_location_we_vote_id_list) + " "
        polling_location_we_vote_id_list_found = positive_value_exists(len(polling_location_we_vote_id_list))
        results = {
            'success':                                  success,
            'status':                                   status,
            'polling_location_we_vote_id_list_found':   polling_location_we_vote_id_list_found,
            'polling_location_we_vote_id_list':         polling_location_we_vote_id_list,
        }
        return results

    @staticmethod
    def retrieve_representative_from_id(representative_id, read_only=False):
        representative_manager = RepresentativeManager()
        return representative_manager.retrieve_representative(
            representative_id=representative_id,
            read_only=read_only)

    @staticmethod
    def retrieve_representative_from_we_vote_id(we_vote_id, read_only=False):
        representative_manager = RepresentativeManager()
        return representative_manager.retrieve_representative(
            representative_we_vote_id=we_vote_id,
            read_only=read_only)

    @staticmethod
    def fetch_representative_id_from_we_vote_id(we_vote_id):
        representative_manager = RepresentativeManager()
        results = representative_manager.retrieve_representative(
            representative_we_vote_id=we_vote_id)
        if results['success']:
            return results['representative_id']
        return 0

    @staticmethod
    def fetch_representative_we_vote_id_from_id(representative_id):
        representative_manager = RepresentativeManager()
        results = representative_manager.retrieve_representative(
            representative_id=representative_id)
        if results['success']:
            return results['representative_we_vote_id']
        return ''

    @staticmethod
    def fetch_google_civic_representative_name_from_we_vote_id(we_vote_id):
        representative_manager = RepresentativeManager()
        results = representative_manager.retrieve_representative(
            representative_we_vote_id=we_vote_id)
        if results['success']:
            representative = results['representative']
            return representative.google_civic_representative_name
        return 0

    @staticmethod
    def retrieve_representative_from_representative_name(representative_name):
        representative_manager = RepresentativeManager()

        results = representative_manager.retrieve_representative(
            representative_name=representative_name)
        if results['success']:
            return results

        # Try to modify the representative name, and search again
        # MapLight for example will pass in "Ronald  Gold" for example
        representative_name_try2 = representative_name.replace('  ', ' ')
        results = representative_manager.retrieve_representative(
            representative_name=representative_name_try2)
        if results['success']:
            return results

        # MapLight also passes in "Kamela D Harris" for example, and Google Civic uses "Kamela D. Harris"
        representative_name_try3 = mimic_google_civic_initials(representative_name)
        if representative_name_try3 != representative_name:
            results = representative_manager.retrieve_representative(
                representative_name=representative_name_try3)
            if results['success']:
                return results

        # Otherwise, return failed results
        return results

    @staticmethod
    def retrieve_representative(
            google_civic_representative_name='',
            ocd_division_id='',
            office_held_we_vote_id='',
            politician_we_vote_id='',
            read_only=False,
            representative_id=0,
            representative_we_vote_id=None,
            representative_name=None):
        representative_found = False
        representative_list = []
        representative_list_found = False
        representative_on_stage = None
        status = ''
        success = True

        try:
            if positive_value_exists(representative_id):
                if read_only:
                    representative_on_stage = Representative.objects.using('readonly').get(id=representative_id)
                else:
                    representative_on_stage = Representative.objects.get(id=representative_id)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status += "RETRIEVE_REPRESENTATIVE_FOUND_BY_ID "
            elif positive_value_exists(representative_we_vote_id):
                if read_only:
                    representative_on_stage = \
                        Representative.objects.using('readonly').get(we_vote_id=representative_we_vote_id)
                else:
                    representative_on_stage = Representative.objects.get(we_vote_id=representative_we_vote_id)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status += "RETRIEVE_REPRESENTATIVE_FOUND_BY_WE_VOTE_ID "
            elif positive_value_exists(office_held_we_vote_id) and (
                    positive_value_exists(google_civic_representative_name) or
                    positive_value_exists(representative_name)):
                if read_only:
                    queryset = Representative.objects.using('readonly').all()
                else:
                    queryset = Representative.objects.all()
                queryset = queryset.filter(office_held_we_vote_id=office_held_we_vote_id)
                if positive_value_exists(representative_name):
                    queryset = queryset.filter(
                        Q(representative_name=representative_name) |
                        Q(google_civic_representative_name=representative_name) |
                        Q(google_civic_representative_name2=representative_name) |
                        Q(google_civic_representative_name3=representative_name)
                    )
                if positive_value_exists(google_civic_representative_name):
                    queryset = queryset.filter(
                        Q(google_civic_representative_name=google_civic_representative_name) |
                        Q(google_civic_representative_name2=google_civic_representative_name) |
                        Q(google_civic_representative_name3=google_civic_representative_name)
                    )
                representative_list = list(queryset)
                if len(representative_list) > 0:
                    # At least one entry exists
                    if len(representative_list) == 1:
                        representative_on_stage = representative_list[0]
                        representative_id = representative_on_stage.id
                        representative_found = True
                        representative_list_found = False
                        representative_we_vote_id = representative_on_stage.we_vote_id
                        status += "REPRESENTATIVE_FOUND "
                    else:
                        # more than one entry found
                        representative_found = False
                        representative_list_found = True
                        status += "MULTIPLE_REPRESENTATIVE_MATCHES "
                else:
                    representative_found = False
                    representative_list_found = False
                    status += "REPRESENTATIVE_NOT_FOUND "
            elif positive_value_exists(politician_we_vote_id):
                if read_only:
                    queryset = Representative.objects.using('readonly').all()
                else:
                    queryset = Representative.objects.all()
                queryset = queryset.filter(politician_we_vote_id=politician_we_vote_id)
                today = datetime.now().date()
                year = today.year
                year_filters = []
                years_list = [year]
                year_integer_list = []
                for year in years_list:
                    year_integer = convert_to_int(year)
                    if year_integer in OFFICE_HELD_YEARS_AVAILABLE:
                        year_integer_list.append(year_integer)
                for year_integer in year_integer_list:
                    if positive_value_exists(year_integer):
                        year_in_office_key = 'year_in_office_' + str(year_integer)
                        one_year_filter = Q(**{year_in_office_key: True})
                        year_filters.append(one_year_filter)
                if len(year_filters) > 0:
                    # Add the first query
                    final_filters = year_filters.pop()
                    # ...and "OR" the remaining items in the list
                    for item in year_filters:
                        final_filters |= item
                    queryset = queryset.filter(final_filters)
                representative_list = list(queryset)
                if len(representative_list) > 0:
                    representative_on_stage = representative_list[0]
                    representative_id = representative_on_stage.id
                    representative_found = True
                    representative_list_found = False
                    representative_we_vote_id = representative_on_stage.we_vote_id
                    status += "REPRESENTATIVE_FOUND "
            else:
                representative_found = False
                status += "RETRIEVE_REPRESENTATIVE_SEARCH_INDEX_MISSING "
        except Representative.DoesNotExist:
            representative_found = False
            representative_list_found = False
            status += "RETRIEVE_REPRESENTATIVE_NOT_FOUND "
        except Exception as e:
            representative_found = False
            representative_list_found = False
            status += "RETRIEVE_REPRESENTATIVE_NOT_FOUND_EXCEPTION: " + str(e) + " "
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'representative_found':         representative_found,
            'representative_id':            convert_to_int(representative_id),
            'representative_list':          representative_list,
            'representative_list_found':    representative_list_found,
            'representative_we_vote_id':    representative_we_vote_id,
            'representative':               representative_on_stage,
        }
        return results

    @staticmethod
    def retrieve_representatives_are_not_duplicates(
            representative1_we_vote_id,
            representative2_we_vote_id,
            read_only=True):
        status = ''
        representatives_are_not_duplicates = RepresentativesAreNotDuplicates()
        # Note that the direction of the friendship does not matter
        try:
            if positive_value_exists(read_only):
                representatives_are_not_duplicates = RepresentativesAreNotDuplicates.objects.using('readonly').get(
                    representative1_we_vote_id__iexact=representative1_we_vote_id,
                    representative2_we_vote_id__iexact=representative2_we_vote_id,
                )
            else:
                representatives_are_not_duplicates = RepresentativesAreNotDuplicates.objects.get(
                    representative1_we_vote_id__iexact=representative1_we_vote_id,
                    representative2_we_vote_id__iexact=representative2_we_vote_id,
                )
            representatives_are_not_duplicates_found = True
            success = True
            status += "REPRESENTATIVES_NOT_DUPLICATES_UPDATED_OR_CREATED1 "
        except RepresentativesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            representatives_are_not_duplicates_found = False
            status += 'NO_REPRESENTATIVES_NOT_DUPLICATES_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            representatives_are_not_duplicates_found = False
            representatives_are_not_duplicates = RepresentativesAreNotDuplicates()
            success = False
            status += "REPRESENTATIVES_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED1: " + str(e) + " "

        if not representatives_are_not_duplicates_found and success:
            try:
                if positive_value_exists(read_only):
                    representatives_are_not_duplicates = \
                        RepresentativesAreNotDuplicates.objects.using('readonly').get(
                            representative1_we_vote_id__iexact=representative2_we_vote_id,
                            representative2_we_vote_id__iexact=representative1_we_vote_id,
                        )
                else:
                    representatives_are_not_duplicates = \
                        RepresentativesAreNotDuplicates.objects.get(
                            representative1_we_vote_id__iexact=representative2_we_vote_id,
                            representative2_we_vote_id__iexact=representative1_we_vote_id
                        )
                representatives_are_not_duplicates_found = True
                success = True
                status += "REPRESENTATIVES_NOT_DUPLICATES_UPDATED_OR_CREATED2 "
            except RepresentativesAreNotDuplicates.DoesNotExist:
                # No data found. Try again below
                success = True
                representatives_are_not_duplicates_found = False
                status += 'NO_REPRESENTATIVES_NOT_DUPLICATES_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                representatives_are_not_duplicates_found = False
                representatives_are_not_duplicates = RepresentativesAreNotDuplicates()
                success = False
                status += "REPRESENTATIVES_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED2: " + str(e) + " "

        results = {
            'success':                                      success,
            'status':                                       status,
            'representatives_are_not_duplicates_found':   representatives_are_not_duplicates_found,
            'representatives_are_not_duplicates':         representatives_are_not_duplicates,
        }
        return results

    @staticmethod
    def retrieve_representatives_are_not_duplicates_list(representative_we_vote_id, read_only=True):
        """
        Get a list of other representative_we_vote_id's that are not duplicates
        :param representative_we_vote_id:
        :param read_only:
        :return:
        """
        # Note that the direction of the linkage does not matter
        representatives_are_not_duplicates_list1 = []
        representatives_are_not_duplicates_list2 = []
        status = ''
        try:
            if positive_value_exists(read_only):
                representatives_are_not_duplicates_list_query = \
                    RepresentativesAreNotDuplicates.objects.using('readonly').filter(
                        representative1_we_vote_id__iexact=representative_we_vote_id,
                    )
            else:
                representatives_are_not_duplicates_list_query = \
                    RepresentativesAreNotDuplicates.objects.filter(
                        representative1_we_vote_id__iexact=representative_we_vote_id)
            representatives_are_not_duplicates_list1 = list(representatives_are_not_duplicates_list_query)
            success = True
            status += "REPRESENTATIVES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except RepresentativesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status += 'NO_REPRESENTATIVES_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status += "REPRESENTATIVES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1: " + str(e) + " "

        if success:
            try:
                if positive_value_exists(read_only):
                    representatives_are_not_duplicates_list_query = \
                        RepresentativesAreNotDuplicates.objects.using('readonly').filter(
                            representative2_we_vote_id__iexact=representative_we_vote_id,
                        )
                else:
                    representatives_are_not_duplicates_list_query = \
                        RepresentativesAreNotDuplicates.objects.filter(
                            representative2_we_vote_id__iexact=representative_we_vote_id)
                representatives_are_not_duplicates_list2 = list(representatives_are_not_duplicates_list_query)
                success = True
                status += "REPRESENTATIVES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except RepresentativesAreNotDuplicates.DoesNotExist:
                success = True
                status += 'NO_REPRESENTATIVES_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status += "REPRESENTATIVES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2: " + str(e) + " "

        representatives_are_not_duplicates_list = representatives_are_not_duplicates_list1 + \
            representatives_are_not_duplicates_list2
        representatives_are_not_duplicates_list_found = positive_value_exists(len(
            representatives_are_not_duplicates_list))
        representatives_are_not_duplicates_list_we_vote_ids = []
        for one_entry in representatives_are_not_duplicates_list:
            if one_entry.representative1_we_vote_id != representative_we_vote_id:
                representatives_are_not_duplicates_list_we_vote_ids.append(one_entry.representative1_we_vote_id)
            elif one_entry.representative2_we_vote_id != representative_we_vote_id:
                representatives_are_not_duplicates_list_we_vote_ids.append(one_entry.representative2_we_vote_id)
        results = {
            'success':                                          success,
            'status':                                           status,
            'representatives_are_not_duplicates_list_found':    representatives_are_not_duplicates_list_found,
            'representatives_are_not_duplicates_list':          representatives_are_not_duplicates_list,
            'representatives_are_not_duplicates_list_we_vote_ids':
                representatives_are_not_duplicates_list_we_vote_ids,
        }
        return results

    def fetch_representatives_are_not_duplicates_list_we_vote_ids(self, representative_we_vote_id):
        results = self.retrieve_representatives_are_not_duplicates_list(representative_we_vote_id)
        return results['representatives_are_not_duplicates_list_we_vote_ids']

    @staticmethod
    def retrieve_representative_list(
            index_start=0,
            is_missing_politician_we_vote_id=False,
            limit_to_this_state_code='',
            office_held_we_vote_id_list=[],
            politician_we_vote_id_list=[],
            read_only=False,
            representatives_limit=300,
            search_string='',
            years_list=[]):
        """

        :param index_start:
        :param is_missing_politician_we_vote_id:
        :param limit_to_this_state_code:
        :param office_held_we_vote_id_list:
        :param politician_we_vote_id_list:
        :param read_only:
        :param representatives_limit:
        :param search_string:
        :param years_list:
        :return:
        """
        index_start = convert_to_int(index_start)
        representative_list = []
        representative_list_found = False
        representatives_limit = convert_to_int(representatives_limit)
        sort_by_is_battleground = False
        if not positive_value_exists(len(years_list)):
            today = datetime.now().date()
            year = today.year
            years_list = [year]
        year_integer_list = []
        year_furthest_in_future = 0
        for year in years_list:
            year_integer = convert_to_int(year)
            if year_integer in OFFICE_HELD_YEARS_AVAILABLE:
                year_integer_list.append(year_integer)
            if year_integer in IS_BATTLEGROUND_YEARS_AVAILABLE:
                sort_by_is_battleground = True
                if year_integer > year_furthest_in_future:
                    year_furthest_in_future = year_integer
        returned_count = 0
        total_count = 0
        status = ""
        success = True

        if positive_value_exists(search_string):
            try:
                search_words = search_string.split()
            except Exception as e:
                status += "SEARCH_STRING_INVALID: " + str(e) + ' '
                search_words = []
        else:
            search_words = []

        if len(year_integer_list) == 0:
            status += "VALID_YEAR_NOT_PROVIDED-EARLIEST_REPRESENTATIVE_DATA_IS_2022 "
            results = {
                'success':                      success,
                'status':                       status,
                'representative_list_found':    representative_list_found,
                'representative_list':          representative_list,
                'returned_count':               returned_count,
                'total_count':                  total_count,
            }
            return results

        try:
            if positive_value_exists(read_only):
                queryset = Representative.objects.using('readonly').all()
            else:
                queryset = Representative.objects.all()
            year_filters = []
            if len(office_held_we_vote_id_list) > 0:
                queryset = queryset.filter(office_held_we_vote_id__in=office_held_we_vote_id_list)
            if len(politician_we_vote_id_list) > 0:
                queryset = queryset.filter(politician_we_vote_id__in=politician_we_vote_id_list)
            if positive_value_exists(is_missing_politician_we_vote_id):
                queryset = queryset.filter(
                    Q(politician_we_vote_id__isnull=True) |
                    Q(politician_we_vote_id='')
                )
            for year_integer in year_integer_list:
                if positive_value_exists(year_integer):
                    year_in_office_key = 'year_in_office_' + str(year_integer)
                    one_year_filter = Q(**{year_in_office_key: True})
                    year_filters.append(one_year_filter)
            if len(year_filters) > 0:
                # Add the first query
                final_filters = year_filters.pop()
                # ...and "OR" the remaining items in the list
                for item in year_filters:
                    final_filters |= item
                queryset = queryset.filter(final_filters)
            if positive_value_exists(limit_to_this_state_code):
                queryset = queryset.filter(state_code__iexact=limit_to_this_state_code)
            if positive_value_exists(search_string):
                # This is an "OR" search for each term, but an "AND" search across all search_words
                for search_word in search_words:
                    filters = []

                    # We want to find representatives with *any* of these values
                    new_filter = Q(google_civic_representative_name__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_representative_name2__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_representative_name3__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(representative_email__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(representative_email2__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(representative_email3__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(representative_name__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(representative_twitter_handle__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(representative_twitter_handle2__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(representative_twitter_handle3__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(office_held_name__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(twitter_name__icontains=search_word)
                    filters.append(new_filter)

                    # Add the first query
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    # Add as new filter for "AND"
                    queryset = queryset.filter(final_filters)
            if sort_by_is_battleground and positive_value_exists(year_furthest_in_future):
                is_battleground_race_desc = "-is_battleground_race_{year}".format(year=year_furthest_in_future)
                queryset = queryset.order_by(is_battleground_race_desc, '-twitter_followers_count')
            else:
                queryset = queryset.order_by('-twitter_followers_count')
            total_count = queryset.count()
            if representatives_limit > 0:
                if index_start > 0:
                    representative_list = queryset[index_start:representatives_limit]
                else:
                    representative_list = queryset[:representatives_limit]
            else:
                representative_list = list(queryset)

            if len(representative_list):
                representative_list_found = True
                status += 'REPRESENTATIVES_RETRIEVED '
            else:
                status += 'NO_REPRESENTATIVES_RETRIEVED '
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_representative_list: ' + str(e) + ' '
            success = False

        returned_count = len(representative_list)

        results = {
            'success':                      success,
            'status':                       status,
            'representative_list_found':    representative_list_found,
            'representative_list':          representative_list,
            'returned_count':               returned_count,
            'total_count':                  total_count,
        }
        return results

    def save_fresh_twitter_details_to_representative(
            self,
            representative=None,
            representative_we_vote_id='',
            twitter_user=None):
        """
        Update a representative entry with details retrieved from the Twitter API.
        """
        representative_updated = False
        success = True
        status = ""
        values_changed = False

        if not hasattr(twitter_user, 'twitter_id'):
            success = False
            status += "VALID_TWITTER_USER_NOT_PROVIDED "

        if success:
            if not hasattr(representative, 'representative_twitter_handle') \
                    and positive_value_exists(representative_we_vote_id):
                # Retrieve representative to update
                pass

        if not hasattr(representative, 'representative_twitter_handle'):
            status += "VALID_REPRESENTATIVE_NOT_PROVIDED_TO_UPDATE_TWITTER_DETAILS "
            success = False

        if not positive_value_exists(representative.representative_twitter_handle) \
                and not positive_value_exists(twitter_user.twitter_handle):
            status += "REPRESENTATIVE_TWITTER_HANDLE_MISSING "
            success = False

        # I don't think this is a problem
        # if success:
        #     if representative.representative_twitter_handle.lower() != twitter_user.twitter_handle.lower():
        #         status += "REPRESENTATIVE_TWITTER_HANDLE_MISMATCH "
        #         success = False

        if not success:
            results = {
                'success':              success,
                'status':               status,
                'representative':           representative,
                'representative_updated':   representative_updated,
            }
            return results

        if positive_value_exists(twitter_user.twitter_description):
            if twitter_user.twitter_description != representative.twitter_description:
                representative.twitter_description = twitter_user.twitter_description
                values_changed = True
        if positive_value_exists(twitter_user.twitter_followers_count):
            if twitter_user.twitter_followers_count != representative.twitter_followers_count:
                representative.twitter_followers_count = twitter_user.twitter_followers_count
                values_changed = True
        if positive_value_exists(twitter_user.twitter_handle):
            # In case the capitalization of the name changes
            if twitter_user.twitter_handle != representative.representative_twitter_handle:
                representative.representative_twitter_handle = twitter_user.twitter_handle
                values_changed = True
        if positive_value_exists(twitter_user.twitter_handle_updates_failing):
            if twitter_user.twitter_handle_updates_failing != representative.twitter_handle_updates_failing:
                representative.twitter_handle_updates_failing = twitter_user.twitter_handle_updates_failing
                values_changed = True
        if positive_value_exists(twitter_user.twitter_id):
            if twitter_user.twitter_id != representative.twitter_user_id:
                representative.twitter_user_id = twitter_user.twitter_id
                values_changed = True
        if positive_value_exists(twitter_user.twitter_location):
            if twitter_user.twitter_location != representative.twitter_location:
                representative.twitter_location = twitter_user.twitter_location
                values_changed = True
        if positive_value_exists(twitter_user.twitter_name):
            if twitter_user.twitter_name != representative.twitter_name:
                representative.twitter_name = twitter_user.twitter_name
                values_changed = True
            if not positive_value_exists(representative.representative_name):
                representative.representative_name = twitter_user.twitter_name
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_image_url_https):
            if twitter_user.twitter_profile_image_url_https != representative.twitter_profile_image_url_https:
                representative.twitter_profile_image_url_https = twitter_user.twitter_profile_image_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_background_image_url_https):
            if twitter_user.twitter_profile_background_image_url_https != \
                    representative.twitter_profile_background_image_url_https:
                representative.twitter_profile_background_image_url_https = \
                    twitter_user.twitter_profile_background_image_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_banner_url_https):
            if twitter_user.twitter_profile_banner_url_https != representative.twitter_profile_banner_url_https:
                representative.twitter_profile_banner_url_https = twitter_user.twitter_profile_banner_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_url):
            from representative.controllers import add_value_to_next_representative_spot
            results = add_value_to_next_representative_spot(
                field_name_base='representative_url',
                new_value_to_add=twitter_user.twitter_url,
                representative=representative,
            )
            if results['success'] and results['values_changed']:
                representative = results['representative']
                values_changed = True
            if not results['success']:
                status += results['status']
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_large):
            if twitter_user.we_vote_hosted_profile_image_url_large != \
                    representative.we_vote_hosted_profile_twitter_image_url_large:
                representative.we_vote_hosted_profile_twitter_image_url_large = \
                    twitter_user.we_vote_hosted_profile_image_url_large
                values_changed = True
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_medium):
            if twitter_user.we_vote_hosted_profile_image_url_medium != \
                    representative.we_vote_hosted_profile_twitter_image_url_medium:
                representative.we_vote_hosted_profile_twitter_image_url_medium = \
                    twitter_user.we_vote_hosted_profile_image_url_medium
                values_changed = True
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_tiny):
            if twitter_user.we_vote_hosted_profile_image_url_tiny != \
                    representative.we_vote_hosted_profile_twitter_image_url_tiny:
                representative.we_vote_hosted_profile_twitter_image_url_tiny = \
                    twitter_user.we_vote_hosted_profile_image_url_tiny
                values_changed = True

        if representative.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN and \
                positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_large):
            representative.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
            values_changed = True
        if representative.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
            if twitter_user.we_vote_hosted_profile_image_url_large != \
                    representative.we_vote_hosted_profile_image_url_large:
                representative.we_vote_hosted_profile_image_url_large = \
                    twitter_user.we_vote_hosted_profile_image_url_large
                values_changed = True
            if twitter_user.we_vote_hosted_profile_image_url_medium != \
                    representative.we_vote_hosted_profile_image_url_medium:
                representative.we_vote_hosted_profile_image_url_medium = \
                    twitter_user.we_vote_hosted_profile_image_url_medium
                values_changed = True
            if twitter_user.we_vote_hosted_profile_image_url_tiny != \
                    representative.we_vote_hosted_profile_image_url_tiny:
                representative.we_vote_hosted_profile_image_url_tiny = \
                    twitter_user.we_vote_hosted_profile_image_url_tiny
                values_changed = True

        if values_changed:
            try:
                representative.save()
                representative_updated = True
                success = True
                status += "SAVED_REPRESENTATIVE_TWITTER_DETAILS "
            except Exception as e:
                success = False
                status += "NO_CHANGES_SAVED_TO_REPRESENTATIVE_TWITTER_DETAILS: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'representative':           representative,
            'representative_updated':   representative_updated,
        }
        return results

    @staticmethod
    def update_or_create_representative(
            representative_we_vote_id,
            updated_values={}):
        """
        Either update or create a representative entry.
        """
        exception_multiple_object_returned = False
        new_representative_created = False
        representative = None
        status = ""
        representative_updated = False

        if not representative_we_vote_id:
            success = False
            status += 'MISSING_REPRESENTATIVE_WE_VOTE_ID '
        else:
            try:
                representative, new_representative_created = Representative.objects.update_or_create(
                    we_vote_id=representative_we_vote_id,
                    defaults=updated_values)
                representative_updated = not new_representative_created
                success = True
                status += 'REPRESENTATIVE_SAVED '
            except Representative.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_OFFICES_HELD_FOUND: ' + str() + ' '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_REPRESENTATIVE_BY_WE_VOTE_ID ' \
                        '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                      success,
            'status':                       status,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'new_representative_created':   new_representative_created,
            'representative':               representative,
            'saved':                        new_representative_created or representative_updated,
            'updated':                      representative_updated,
            'not_processed':                True if not success else False,
        }
        return results

    @staticmethod
    def update_or_create_representatives_are_not_duplicates(
            representative1_we_vote_id,
            representative2_we_vote_id):
        """
        Either update or create a representative entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_representatives_are_not_duplicates_created = False
        representatives_are_not_duplicates = RepresentativesAreNotDuplicates()
        status = ""

        if positive_value_exists(representative1_we_vote_id) and positive_value_exists(representative2_we_vote_id):
            try:
                updated_values = {
                    'representative1_we_vote_id':    representative1_we_vote_id,
                    'representative2_we_vote_id':    representative2_we_vote_id,
                }
                representatives_are_not_duplicates, new_representatives_are_not_duplicates_created = \
                    RepresentativesAreNotDuplicates.objects.update_or_create(
                        representative1_we_vote_id__exact=representative1_we_vote_id,
                        representative2_we_vote_id__iexact=representative2_we_vote_id,
                        defaults=updated_values)
                success = True
                status += "REPRESENTATIVES_ARE_NOT_DUPLICATES_UPDATED_OR_CREATED "
            except RepresentativesAreNotDuplicates.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_REPRESENTATIVES_ARE_NOT_DUPLICATES_FOUND_BY_REPRESENTATIVE_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'EXCEPTION_UPDATE_OR_CREATE_REPRESENTATIVES_ARE_NOT_DUPLICATES ' \
                        '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                                      success,
            'status':                                       status,
            'MultipleObjectsReturned':                      exception_multiple_object_returned,
            'new_representatives_are_not_duplicates_created':    new_representatives_are_not_duplicates_created,
            'representatives_are_not_duplicates':                representatives_are_not_duplicates,
        }
        return results

    @staticmethod
    def update_representative_social_media(
            representative,
            representative_twitter_handle=False,
            representative_facebook=False):
        """
        Update a representative entry with general social media data. If a value is passed in False
        it means "Do not update"
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        success = False
        status = "ENTERING_UPDATE_REPRESENTATIVE_SOCIAL_MEDIA"
        values_changed = False

        representative_twitter_handle = representative_twitter_handle.strip() if representative_twitter_handle \
            else False
        representative_facebook = representative_facebook.strip() if representative_facebook else False
        # representative_image = representative_image.strip() if representative_image else False

        if representative:
            if representative_twitter_handle:
                if representative_twitter_handle != representative.representative_twitter_handle:
                    representative.representative_twitter_handle = representative_twitter_handle
                    values_changed = True
            if representative_facebook:
                if representative_facebook != representative.facebook_url:
                    representative.facebook_url = representative_facebook
                    values_changed = True

            if values_changed:
                representative.save()
                success = True
                status += "SAVED_REPRESENTATIVE_SOCIAL_MEDIA "
            else:
                success = True
                status += "NO_CHANGES_SAVED_TO_REPRESENTATIVE_SOCIAL_MEDIA "

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'representative':         representative,
        }
        return results

    @staticmethod
    def update_representative_twitter_details(
            representative, twitter_dict,
            cached_twitter_profile_image_url_https,
            cached_twitter_profile_background_image_url_https,
            cached_twitter_profile_banner_url_https,
            we_vote_hosted_profile_image_url_large,
            we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny):
        """
        Update a representative entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_REPRESENTATIVE_TWITTER_DETAILS"
        values_changed = False

        if representative:
            if 'id' in twitter_dict and positive_value_exists(twitter_dict['id']):
                if convert_to_int(twitter_dict['id']) != representative.twitter_user_id:
                    representative.twitter_user_id = convert_to_int(twitter_dict['id'])
                    values_changed = True
            if 'username' in twitter_dict and positive_value_exists(twitter_dict['username']):
                if twitter_dict['username'] != representative.representative_twitter_handle:
                    representative.representative_twitter_handle = twitter_dict['username']
                    values_changed = True
            if 'name' in twitter_dict and positive_value_exists(twitter_dict['name']):
                if twitter_dict['name'] != representative.twitter_name:
                    representative.twitter_name = twitter_dict['name']
                    values_changed = True
            if 'followers_count' in twitter_dict and positive_value_exists(twitter_dict['followers_count']):
                if convert_to_int(twitter_dict['followers_count']) != representative.twitter_followers_count:
                    representative.twitter_followers_count = convert_to_int(twitter_dict['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                representative.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url' in twitter_dict and positive_value_exists(
                    twitter_dict['profile_image_url']):
                if twitter_dict['profile_image_url'] != representative.twitter_profile_image_url_https:
                    representative.twitter_profile_image_url_https = twitter_dict['profile_image_url']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                representative.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            # 2024-01-27 Twitter API v2 doesn't return profile_banner_url anymore
            # elif ('profile_banner_url' in twitter_dict) and positive_value_exists(twitter_dict['profile_banner_url']):
            #     if twitter_dict['profile_banner_url'] != representative.twitter_profile_banner_url_https:
            #         representative.twitter_profile_banner_url_https = twitter_dict['profile_banner_url']
            #         values_changed = True

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                representative.twitter_profile_background_image_url_https = \
                    cached_twitter_profile_background_image_url_https
                values_changed = True
            # 2024-01-27 Twitter API v2 doesn't return profile_background_image_url_https anymore
            # elif 'profile_background_image_url_https' in twitter_dict and positive_value_exists(
            #         twitter_dict['profile_background_image_url_https']):
            #     if twitter_dict['profile_background_image_url_https'] != \
            #             representative.twitter_profile_background_image_url_https:
            #         representative.twitter_profile_background_image_url_https = \
            #             twitter_dict['profile_background_image_url_https']
            #         values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                representative.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                representative.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                representative.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_dict:  # No value required to update description (so we can clear out)
                if twitter_dict['description'] != representative.twitter_description:
                    representative.twitter_description = twitter_dict['description']
                    values_changed = True
            if 'location' in twitter_dict:  # No value required to update location (so we can clear out)
                if twitter_dict['location'] != representative.twitter_location:
                    representative.twitter_location = twitter_dict['location']
                    values_changed = True

            if values_changed:
                representative.save()
                success = True
                status += "SAVED_REPRESENTATIVE_TWITTER_DETAILS "
            else:
                success = True
                status += "NO_CHANGES_SAVED_TO_REPRESENTATIVE_TWITTER_DETAILS "

        results = {
            'success':      success,
            'status':       status,
            'representative':    representative,
        }
        return results

    @staticmethod
    def reset_representative_image_details(
            representative,
            twitter_profile_image_url_https,
            twitter_profile_background_image_url_https,
            twitter_profile_banner_url_https):
        """
        Reset an representative entry with original image details from we vote image.
        """
        success = False
        status = "ENTERING_RESET_REPRESENTATIVE_IMAGE_DETAILS"

        if representative:
            if positive_value_exists(twitter_profile_image_url_https):
                representative.twitter_profile_image_url_https = twitter_profile_image_url_https
            if positive_value_exists(twitter_profile_background_image_url_https):
                representative.twitter_profile_background_image_url_https = twitter_profile_background_image_url_https
            if positive_value_exists(twitter_profile_banner_url_https):
                representative.twitter_profile_banner_url_https = twitter_profile_banner_url_https
            representative.we_vote_hosted_profile_image_url_large = ''
            representative.we_vote_hosted_profile_image_url_medium = ''
            representative.we_vote_hosted_profile_image_url_tiny = ''
            representative.save()
            success = True
            status += "RESET_REPRESENTATIVE_IMAGE_DETAILS "

        results = {
            'success':      success,
            'status':       status,
            'representative':    representative,
        }
        return results

    @staticmethod
    def clear_representative_twitter_details(representative):
        """
        Update representative entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_REPRESENTATIVE_TWITTER_DETAILS "

        if representative:
            representative.twitter_user_id = 0
            # We leave the handle in place
            # representative.representative_twitter_handle = ""
            representative.twitter_name = ''
            representative.twitter_followers_count = 0
            representative.twitter_profile_image_url_https = ''
            representative.we_vote_hosted_profile_image_url_large = ''
            representative.we_vote_hosted_profile_image_url_medium = ''
            representative.we_vote_hosted_profile_image_url_tiny = ''
            representative.twitter_description = ''
            representative.twitter_location = ''
            representative.save()
            success = True
            status += "CLEARED_REPRESENTATIVE_TWITTER_DETAILS "

        results = {
            'success':      success,
            'status':       status,
            'representative':    representative,
        }
        return results

    @staticmethod
    def create_representative_row_entry(update_values):
        """
        Create Representative table entry with Representative details
        :param update_values:
        :return:
        """
        success = False
        status = ""
        representative_created = False
        representative_found = False
        representative_updated = False
        representative = ''

        # Variables we accept
        representative_name = update_values.get('representative_name', '')
        office_held_we_vote_id = update_values.get('office_held_we_vote_id', '')
        office_held_id = update_values.get('office_held_id', 0)

        if not positive_value_exists(representative_name) \
                or not positive_value_exists(office_held_we_vote_id) \
                or not positive_value_exists(office_held_id):
            # If we don't have the minimum values required to create a representative, then don't proceed
            status += "CREATE_REPRESENTATIVE_ROW-MISSING_REQUIRED_FIELDS "
            results = {
                    'success':                  success,
                    'status':                   status,
                    'representative':           representative,
                    'representative_created':   representative_created,
                    'representative_found':     representative_found,
                    'representative_updated':   representative_updated,
                }
            return results

        try:
            representative = Representative.objects.create(
                google_civic_representative_name=representative_name,
                representative_name=representative_name,
                office_held_we_vote_id=office_held_we_vote_id)
            if representative:
                success = True
                status += "REPRESENTATIVE_CREATED "
                representative_created = True
                representative_found = True
            else:
                success = False
                status += "REPRESENTATIVE_CREATE_FAILED "
        except Exception as e:
            success = False
            status += "REPRESENTATIVE_CREATE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        if representative_created:
            try:
                representative = attach_defaults_values_to_representative_object(
                    representative=representative, defaults=update_values)
                representative.save()
                representative_updated = True

                status += "REPRESENTATIVE_CREATE_THEN_UPDATE_SUCCESS "
            except Exception as e:
                success = False
                representative_updated = False
                status += "REPRESENTATIVE_CREATE_THEN_UPDATE_ERROR "
                handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'representative':           representative,
                'representative_created':   representative_created,
                'representative_found':     representative_found,
                'representative_updated':   representative_updated,
            }
        return results

    @staticmethod
    def create_representatives_missing(
            is_from_google_civic=False,
            polling_location_we_vote_id='',
            state_code=None,
            defaults={}):
        entry_created = False
        representatives_missing = None
        representatives_missing_found = False
        status = ''
        success = True

        try:
            representatives_missing, entry_created = RepresentativesMissingFromPollingLocation.objects.update_or_create(
                is_from_google_civic=is_from_google_civic,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                defaults=defaults)
            representatives_missing_found = True
            status += "REPRESENTATIVES_MISSING_CREATED "
        except Exception as e:
            status += "REPRESENTATIVES_MISSING_NOT_CREATED: " + str(e) + " "
            success = False

        results = {
            'status':                           status,
            'success':                          success,
            'representatives_missing':          representatives_missing,
            'representatives_missing_created':  entry_created,
            'representatives_missing_found':    representatives_missing_found,
        }
        return results

    @staticmethod
    def update_representative_row_entry(representative_we_vote_id, update_values):
        """
        Update Representative table entry with matching we_vote_id
        :param representative_we_vote_id:
        :param update_values:
        :return:
        """

        success = True
        status = ""
        representative = None
        representative_found = False
        representative_updated = False

        try:
            representative = Representative.objects.get(we_vote_id__iexact=representative_we_vote_id)
            representative_found = True
        except Representative.DoesNotExist:
            status += "REPRESENTATIVE_NOT_FOUND "
        except Exception as e:
            success = False
            status += "REPRESENTATIVE_RETRIEVE_ERROR " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        try:
            if representative_found:
                representative = attach_defaults_values_to_representative_object(
                    representative=representative, defaults=update_values)
                representative.save()
                representative_updated = True
                success = True
                status += "REPRESENTATIVE_UPDATED "
        except Exception as e:
            success = False
            representative_updated = False
            status += "REPRESENTATIVE_RETRIEVE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'representative':           representative,
                'representative_found':     representative_found,
                'representative_updated':   representative_updated,
            }
        return results

    @staticmethod
    def retrieve_representatives_from_non_unique_identifiers(
            ignore_representative_we_vote_id_list=[],
            ocd_division_id='',
            read_only=True,
            twitter_handle_list=[],
            representative_name='',
            state_code=''):
        keep_looking_for_duplicates = True
        representative = None
        representative_found = False
        representative_list = []
        representative_list_found = False
        multiple_entries_found = False
        success = True
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(len(twitter_handle_list)):
            try:
                if positive_value_exists(read_only):
                    representative_query = Representative.objects.using('readonly').all()
                else:
                    representative_query = Representative.objects.all()
                if positive_value_exists(ocd_division_id):
                    representative_query = representative_query.filter(ocd_division_id=ocd_division_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                twitter_filters = []
                for one_twitter_handle in twitter_handle_list:
                    one_twitter_handle_cleaned = extract_twitter_handle_from_text_string(one_twitter_handle)
                    new_filter = (
                        Q(representative_twitter_handle__iexact=one_twitter_handle_cleaned) |
                        Q(representative_twitter_handle2__iexact=one_twitter_handle_cleaned) |
                        Q(representative_twitter_handle3__iexact=one_twitter_handle_cleaned)
                    )
                    twitter_filters.append(new_filter)

                # Add the first query
                final_filters = twitter_filters.pop()
                # ...and "OR" the remaining items in the list
                for item in twitter_filters:
                    final_filters |= item

                representative_query = representative_query.filter(final_filters)

                if positive_value_exists(ignore_representative_we_vote_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_we_vote_id_list)

                representative_list = list(representative_query)
                if len(representative_list) > 0:
                    # At least one entry exists
                    status += 'BATCH_ROW_ACTION_REPRESENTATIVE_LIST_RETRIEVED '
                    if len(representative_list) == 1:
                        multiple_entries_found = False
                        representative = representative_list[0]
                        representative_found = True
                        keep_looking_for_duplicates = False
                        success = True
                        status += "REPRESENTATIVE_FOUND_BY_TWITTER "
                    else:
                        # more than one entry found
                        representative_list_found = True
                        multiple_entries_found = True
                        keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
                        status += "MULTIPLE_TWITTER_MATCHES "
            except Representative.DoesNotExist:
                success = True
                status += "BATCH_ROW_ACTION_EXISTING_REPRESENTATIVE_NOT_FOUND "
            except Exception as e:
                keep_looking_for_duplicates = False
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_QUERY_FAILED1: " + str(e) + " "
                success = False
        # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search by Representative name exact match
            try:
                if positive_value_exists(read_only):
                    representative_query = Representative.objects.using('readonly').all()
                else:
                    representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    representative_name__iexact=representative_name,
                    ocd_division_id=ocd_division_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_representative_we_vote_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_we_vote_id_list)

                representative_list = list(representative_query)
                if len(representative_list) > 0:
                    # entry exists
                    status += 'REPRESENTATIVE_ENTRY_EXISTS '
                    success = True
                    # if a single entry matches, update that entry
                    if len(representative_list) == 1:
                        representative = representative_list[0]
                        representative_found = True
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in Representative
                        representative_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    success = True
                    status += 'REPRESENTATIVE_ENTRY_NOT_FOUND-EXACT '

            except Representative.DoesNotExist:
                success = True
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_NOT_FOUND-EXACT_MATCH "
            except Exception as e:
                keep_looking_for_duplicates = False
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_QUERY_FAILED2: " + str(e) + " "
                success = False

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search for Representative(s) that contains the same first and last names
            try:
                if positive_value_exists(read_only):
                    representative_query = Representative.objects.using('readonly').all()
                else:
                    representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    ocd_division_id=ocd_division_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=last_name)

                if positive_value_exists(ignore_representative_we_vote_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_we_vote_id_list)

                representative_list = list(representative_query)
                if len(representative_list) > 0:
                    # entry exists
                    status += 'REPRESENTATIVE_ENTRY_EXISTS '
                    success = True
                    # if a single entry matches, update that entry
                    if len(representative_list) == 1:
                        representative = representative_list[0]
                        representative_found = True
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in Representative
                        representative_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    status += 'REPRESENTATIVE_ENTRY_NOT_FOUND-FIRST_OR_LAST '
                    success = True
            except Representative.DoesNotExist:
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_NOT_FOUND-FIRST_OR_LAST_NAME "
                success = True
            except Exception as e:
                keep_looking_for_duplicates = False
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_QUERY_FAILED3: " + str(e) + " "
                success = False

        results = {
            'success':                      success,
            'status':                       status,
            'ocd_division_id':              ocd_division_id,
            'representative_found':         representative_found,
            'representative':               representative,
            'representative_list_found':    representative_list_found,
            'representative_list':          representative_list,
            'multiple_entries_found':       multiple_entries_found,
        }
        return results

    @staticmethod
    def fetch_representatives_from_non_unique_identifiers_count(
            ocd_division_id='',
            state_code='',
            representative_twitter_handle='',
            representative_twitter_handle2='',
            representative_twitter_handle3='',
            representative_name='',
            ignore_representative_we_vote_id_list=[]):
        keep_looking_for_duplicates = True
        representative_twitter_handle = extract_twitter_handle_from_text_string(representative_twitter_handle)
        representative_twitter_handle2 = extract_twitter_handle_from_text_string(representative_twitter_handle2)
        representative_twitter_handle3 = extract_twitter_handle_from_text_string(representative_twitter_handle3)
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(representative_twitter_handle):
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    representative_twitter_handle__iexact=representative_twitter_handle,
                    ocd_division_id_iexact=ocd_division_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_representative_we_vote_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_we_vote_id_list)

                representative_count = representative_query.count()
                if positive_value_exists(representative_count):
                    return representative_count
            except Representative.DoesNotExist:
                pass
            except Exception as e:
                keep_looking_for_duplicates = False
                status += ""
        # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search by Representative name exact match
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    representative_name__iexact=representative_name,
                    ocd_division_id_iexact=ocd_division_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_representative_we_vote_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_we_vote_id_list)

                representative_count = representative_query.count()
                if positive_value_exists(representative_count):
                    return representative_count
            except Representative.DoesNotExist:
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_NOT_FOUND "

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search for Representative(s) that contains the same first and last names
            try:
                representative_query = Representative.objects.all()
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=last_name)

                if positive_value_exists(ignore_representative_we_vote_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_we_vote_id_list)

                representative_count = representative_query.count()
                if positive_value_exists(representative_count):
                    return representative_count
            except Representative.DoesNotExist:
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_NOT_FOUND "
                success = True

        return 0


class RepresentativesAreNotDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two representatives as NOT duplicates
    """
    representative1_we_vote_id = models.CharField(
        verbose_name="first representative we are tracking", max_length=255, null=True, unique=False)
    representative2_we_vote_id = models.CharField(
        verbose_name="second representative we are tracking", max_length=255, null=True, unique=False)

    def fetch_other_representative_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.representative1_we_vote_id:
            return self.representative2_we_vote_id
        elif one_we_vote_id == self.representative2_we_vote_id:
            return self.representative1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class RepresentativesMissingFromPollingLocation(models.Model):
    """
    We asked for representatives from this Polling Location, but none came back
    """
    date_last_updated = models.DateTimeField(
        verbose_name='date representatives last requested', auto_now=True, db_index=True)
    error_message = models.TextField(default=None, null=True)
    is_from_google_civic = models.BooleanField(default=False)
    issue_resolved = models.BooleanField(default=False)
    # The map point for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the map point", max_length=255, default=None, null=True,
        blank=True, unique=False)
    state_code = models.CharField(max_length=2, null=True, db_index=True)


# Instead of using this model currently, we simply store the office_held_we_vote_id in the Representative table.
# class RepresentativeToOfficeHeldLink(models.Model):
#     """
#     With this table, we can store which OfficeHeld a Representative is connected to.
#     """
#     representative_we_vote_id = models.CharField(db_index=True, max_length=255, null=False, unique=False)
#     office_held_we_vote_id = models.CharField(db_index=True, max_length=255, null=False, unique=False)
#     politician_we_vote_id = models.CharField(db_index=True, max_length=255, null=True, unique=False)
#     state_code = models.CharField(db_index=True, max_length=2, null=True)
#     # Which years did this representative serve. This is cached data -- the master data is in the Representative table
#     years_in_office_flags = models.PositiveIntegerField(default=0)
#
#     def office_held(self):
#         try:
#             office = OfficeHeld.objects.get(we_vote_id=self.office_held_we_vote_id)
#         except OfficeHeld.MultipleObjectsReturned as e:
#             handle_record_found_more_than_one_exception(e, logger=logger)
#             logger.error("RepresentativeToOfficeHeldLink.office_held Found multiple")
#             return
#         except OfficeHeld.DoesNotExist:
#             logger.error("RepresentativeToOfficeHeldLink.office_held not attached to object, id: "
#                          "" + str(self.office_held_we_vote_id))
#             return
#         return office
#
#     def set_years_in_office_flags(self, years_in_office_flag_integer_to_set):
#         self.years_in_office_flags |= years_in_office_flag_integer_to_set
#
#     def unset_years_in_office_flags(self, years_in_office_flag_integer_to_unset):
#         self.years_in_office_flags = ~years_in_office_flag_integer_to_unset & self.years_in_office_flags
