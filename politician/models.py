# politician/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# Politician-related Models
from django.db import models
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from tag.models import Tag
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, convert_to_political_party_constant, \
    display_full_name_with_correct_capitalization, \
    extract_first_name_from_full_name, extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_state_from_ocd_division_id, extract_twitter_handle_from_text_string, \
    positive_value_exists, \
    AMERICAN_INDEPENDENT, DEMOCRAT, D_R, ECONOMIC_GROWTH, GREEN, INDEPENDENT,  INDEPENDENT_GREEN, LIBERTARIAN, \
    NO_PARTY_PREFERENCE, NON_PARTISAN, PEACE_AND_FREEDOM, REFORM, REPUBLICAN


from wevote_settings.models import fetch_next_we_vote_id_politician_integer, fetch_site_unique_id_prefix


FEMALE = 'F'
GENDER_NEUTRAL = 'N'
MALE = 'M'
UNKNOWN = 'U'
GENDER_CHOICES = (
    (FEMALE, 'Female'),
    (GENDER_NEUTRAL, 'Gender Neutral'),
    (MALE, 'Male'),
    (UNKNOWN, 'Unknown'),
)

logger = wevote_functions.admin.get_logger(__name__)


class Politician(models.Model):
    # We are relying on built-in Python id field
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "pol", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_politician_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this politician", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # See this url for properties: https://docs.python.org/2/library/functions.html#property
    first_name = models.CharField(verbose_name="first name",
                                  max_length=255, default=None, null=True, blank=True)
    middle_name = models.CharField(verbose_name="middle name",
                                   max_length=255, default=None, null=True, blank=True)
    last_name = models.CharField(verbose_name="last name",
                                 max_length=255, default=None, null=True, blank=True)
    politician_name = models.CharField(verbose_name="official full name",
                                       max_length=255, default=None, null=True, blank=True)
    # This is the politician's name from GoogleCivicCandidateCampaign
    google_civic_candidate_name = models.CharField(verbose_name="full name from google civic",
                                                   max_length=255, default=None, null=True, blank=True)
    # This is the politician's name assembled from TheUnitedStatesIo first_name + last_name for quick search
    full_name_assembled = models.CharField(verbose_name="full name assembled from first_name + last_name",
                                           max_length=255, default=None, null=True, blank=True)
    gender = models.CharField("gender", max_length=1, choices=GENDER_CHOICES, default=UNKNOWN)

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
    wikipedia_id = models.CharField(verbose_name="wikipedia url",
                                    max_length=500, default=None, null=True, blank=True)
    ballotpedia_id = models.CharField(verbose_name="ballotpedia url",
                                      max_length=500, default=None, null=True, blank=True)
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
    state_code = models.CharField(verbose_name="politician home state", max_length=2, null=True)
    politician_url = models.URLField(verbose_name='latest website url of politician', blank=True, null=True)

    politician_twitter_handle = models.CharField(
        verbose_name='politician twitter screen_name', max_length=255, null=True, unique=False)
    we_vote_hosted_profile_image_url_large = models.URLField(verbose_name='we vote hosted large image url',
                                                             blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.URLField(verbose_name='we vote hosted medium image url',
                                                              blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.URLField(verbose_name='we vote hosted tiny image url',
                                                            blank=True, null=True)
    # ctcl politician fields
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    politician_facebook_id = models.CharField(verbose_name='politician facebook user name', max_length=255, null=True,
                                              unique=False)
    politician_phone_number = models.CharField(verbose_name='politician phone number', max_length=255, null=True,
                                               unique=False)
    politician_googleplus_id = models.CharField(verbose_name='politician googleplus profile name', max_length=255,
                                                null=True, unique=False)
    politician_youtube_id = models.CharField(verbose_name='politician youtube profile name', max_length=255, null=True,
                                             unique=False)
    politician_email_address = models.CharField(verbose_name='politician email address', max_length=80, null=True,
                                                unique=False)

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
        return self.gender in self.FEMALE

    def is_gender_neutral(self):
        return self.gender in self.GENDER_NEUTRAL

    def is_male(self):
        return self.gender in self.MALE

    def is_gender_specified(self):
        return self.gender in (self.FEMALE, self.GENDER_NEUTRAL, self.MALE)


class PoliticianManager(models.Model):
    def __init__(self):
        # TODO Recommend by Hy Carrel
        pass

    def politician_photo_url(self, politician_id):
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(politician_id)

        if results['success']:
            politician = results['politician']
            return politician.politician_photo_url()
        return ""

    def retrieve_politician(self, politician_id, we_vote_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        politician_on_stage = Politician()
        politician_on_stage_id = 0
        politician_we_vote_id = ""
        try:
            if positive_value_exists(politician_id):
                politician_on_stage = Politician.objects.get(id=politician_id)
                politician_on_stage_id = politician_on_stage.id
                politician_we_vote_id = politician_on_stage.we_vote_id
            elif positive_value_exists(we_vote_id):
                politician_on_stage = Politician.objects.get(we_vote_id__iexact=we_vote_id)
                politician_on_stage_id = politician_on_stage.id
                politician_we_vote_id = politician_on_stage.we_vote_id
        except Politician.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
        except Politician.DoesNotExist:
            error_result = True
            exception_does_not_exist = True

        # politician_on_stage_found2 = politician_on_stage_id > 0  # TODO Why not this simpler case?
        politician_on_stage_found = True if politician_on_stage_id > 0 else False
        results = {
            'success':                      True if politician_on_stage_found else False,
            'politician_found':             politician_on_stage_found,
            'politician_id':                politician_on_stage_id,
            'politician_we_vote_id':        politician_we_vote_id,
            'politician':                   politician_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def retrieve_all_politicians_that_might_match_candidate(self, vote_smart_id, maplight_id, candidate_twitter_handle,
                                                            candidate_name='', state_code=''):
        politician_list = []
        politician_list_found = False
        politician = Politician()
        politician_found = False

        # if not positive_value_exists(politician_id) and not positive_value_exists(politician_we_vote_id):
        #     status = 'VALID_POLITICIAN_ID_AND_POLITICIAN_WE_VOTE_ID_MISSING'
        #     results = {
        #         'success':                  True if politician_list_found else False,
        #         'status':                   status,
        #         'politician_id':            politician_id,
        #         'politician_we_vote_id':    politician_we_vote_id,
        #         'politician_list_found':    politician_list_found,
        #         'politician_list':          politician_list,
        #     }
        #     return results

        try:
            filter_set = False
            politician_queryset = Politician.objects.all()
            if positive_value_exists(vote_smart_id):
                filter_set = True
                politician_queryset = politician_queryset.filter(vote_smart_id=vote_smart_id)
            elif positive_value_exists(maplight_id):
                filter_set = True
                politician_queryset = politician_queryset.filter(maplight_id=maplight_id)
            elif positive_value_exists(candidate_twitter_handle):
                filter_set = True
                politician_queryset = politician_queryset.filter(
                    politician_twitter_handle__iexact=candidate_twitter_handle)
            elif positive_value_exists(candidate_name) and positive_value_exists(state_code):
                filter_set = True
                # Note, this won't catch Presidential candidates
                politician_queryset = politician_queryset.filter(politician_name__iexact=candidate_name)
                politician_queryset = politician_queryset.filter(state_code__iexact=state_code)

            if filter_set:
                politician_list = politician_queryset
            else:
                politician_list = []

            if len(politician_list) is 1:
                politician_found = True
                politician_list_found = False
                politician = politician_list[0]
                status = 'ONE_POLITICIAN_RETRIEVED'
            elif len(politician_list):
                politician_found = False
                politician_list_found = True
                status = 'POLITICIAN_LIST_RETRIEVED'
            else:
                status = 'NO_POLITICIANS_RETRIEVED'
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
        politician_details = self.retrieve_politician(0, candidate.politician_we_vote_id)
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

    def update_politician_details_from_candidate(self, candidate):
        """
        Update a politician entry with details retrieved from candidate
        :param candidate:
        :return:
        """
        values_changed = False
        politician_details = self.retrieve_politician(0, candidate.politician_we_vote_id)
        politician = politician_details['politician']
        if politician_details['success']:
            # Politician found so update politicina details with candidate details
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
            if positive_value_exists(candidate.candidate_twitter_handle) and \
                    candidate.candidate_twitter_handle != politician.politician_twitter_handle:
                politician.politician_twitter_handle = candidate.candidate_twitter_handle
                values_changed = True
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
                success = True
                status = "SAVED_POLITICIAN_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_POLITICIAN_DETAILS"
        else:
            success = False
            status = "POLITICIAN_NOT_FOUND"
        results = {
            'success':      success,
            'status':       status,
            'politician':   politician
        }
        return results

    def update_or_create_politician_from_candidate(self, candidate):
        """
        Take a We Vote candidate_campaign object, and map it to update_or_create_politician
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
            'maplight_id':                              candidate.maplight_id,
            'politician_name':                          candidate.candidate_name,
            'google_civic_candidate_name':              candidate.google_civic_candidate_name,
            'state_code':                               candidate.state_code,
            'politician_twitter_handle':                candidate.candidate_twitter_handle,
            'we_vote_hosted_profile_image_url_large':   candidate.we_vote_hosted_profile_image_url_large,
            'we_vote_hosted_profile_image_url_medium':  candidate.we_vote_hosted_profile_image_url_medium,
            'we_vote_hosted_profile_image_url_tiny':    candidate.we_vote_hosted_profile_image_url_tiny,
            'first_name':                               first_name,
            'middle_name':                              middle_name,
            'last_name':                                last_name,
            'political_party':                          political_party,
        }

        return self.update_or_create_politician(updated_politician_values, candidate.politician_we_vote_id)

    def update_or_create_politician(self, updated_politician_values, politician_we_vote_id,
                                    vote_smart_id=0, maplight_id="",
                                    candidate_twitter_handle="", candidate_name="", state_code="",
                                    first_name="", middle_name="", last_name=""):
        """
        Either update or create a politician entry. The individual variables passed in are for the purpose of finding
        a politician to update, and the updated_politician_values variable contains the values we want to update to.
        """
        politician_found = False
        new_politician_created = False
        politician = Politician()

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
            elif positive_value_exists(candidate_twitter_handle):
                politician, new_politician_created = \
                    Politician.objects.update_or_create(
                        politician_twitter_handle=candidate_twitter_handle,
                        defaults=updated_politician_values)
                politician_found = True
            elif positive_value_exists(first_name) and positive_value_exists(last_name) \
                    and positive_value_exists(state_code):
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
                status = 'POLITICIAN_SAVED'
            else:
                status = 'POLITICIAN_NOT_SAVED'
        except Exception as e:
            success = False
            status = 'UNABLE_TO_UPDATE_OR_CREATE_POLITICIAN'

        results = {
            'success':              success,
            'status':               status,
            'politician_created':   new_politician_created,
            'politician_found':     politician_found,
            'politician':           politician,
        }
        return results

    def fetch_politician_id_from_we_vote_id(self, we_vote_id):
        politician_id = 0
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(politician_id, we_vote_id)
        if results['success']:
            return results['politician_id']
        return 0

    def fetch_politician_we_vote_id_from_id(self, politician_id):
        we_vote_id = ''
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(politician_id, we_vote_id)
        if results['success']:
            return results['politician_we_vote_id']
        return ''


    def create_politician_row_entry(self, politician_name, politician_first_name, politician_middle_name,
                                    politician_last_name, ctcl_uuid, political_party, politician_email_address,
                                    politician_phone_number, politician_twitter_handle, politician_facebook_id,
                                    politician_googleplus_id, politician_youtube_id, politician_website_url):
        """
        Create Politician table entry with Politician details
        :param politician_name: 
        :param politician_first_name: 
        :param politician_middle_name: 
        :param politician_last_name: 
        :param ctcl_uuid: 
        :param political_party: 
        :param politician_email_address: 
        :param politician_phone_number: 
        :param politician_twitter_handle:
        :param politician_facebook_id: 
        :param politician_googleplus_id: 
        :param politician_youtube_id: 
        :param politician_website_url: 
        :return: 
        """
        success = False
        status = ""
        politician_updated = False
        new_politician_created = False
        new_politician = ''

        try:
            new_politician = Politician.objects.create(politician_name=politician_name, first_name=politician_first_name,
                                                       middle_name=politician_middle_name,
                                                       last_name=politician_last_name, political_party=political_party,
                                                       politician_email_address=politician_email_address,
                                                       politician_phone_number=politician_phone_number,
                                                       politician_twitter_handle=politician_twitter_handle,
                                                       politician_facebook_id=politician_facebook_id,
                                                       politician_googleplus_id=politician_googleplus_id,
                                                       politician_youtube_id=politician_youtube_id,
                                                       politician_url=politician_website_url,ctcl_uuid=ctcl_uuid)
            if new_politician:
                success = True
                status = "POLITICIAN_CREATED"
                new_politician_created = True
            else:
                success = False
                status = "POLITICIAN_CREATE_FAILED"
        except Exception as e:
            success = False
            new_politician_created = False
            status = "POLITICIAN_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'new_politician_created':   new_politician_created,
                'politician_updated':       politician_updated,
                'new_politician':           new_politician,
            }
        return results

    def update_politician_row_entry(self, politician_name, politician_first_name, politician_middle_name,
                                    politician_last_name, ctcl_uuid,political_party, politician_email_address,
                                    politician_twitter_handle, politician_phone_number, politician_facebook_id,
                                    politician_googleplus_id, politician_youtube_id, politician_website_url,
                                    politician_we_vote_id):
        """
        Update Politician table entry with matching we_vote_id
        :param politician_name: 
        :param politician_first_name: 
        :param politician_middle_name: 
        :param politician_last_name: 
        :param ctcl_uuid: 
        :param political_party: 
        :param politician_email_address: 
        :param politician_twitter_handle: 
        :param politician_phone_number: 
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
                existing_politician_entry.politician_phone_number = politician_phone_number
                existing_politician_entry.twitter_handle = politician_twitter_handle
                existing_politician_entry.politician_facebook_id = politician_facebook_id
                existing_politician_entry.politician_googleplus_id = politician_googleplus_id
                existing_politician_entry.politician_youtube_id = politician_youtube_id
                existing_politician_entry.politician_url = politician_website_url
                existing_politician_entry.politician_email_address = politician_email_address
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


class PoliticianTagLink(models.Model):
    """
    A confirmed (undisputed) link between tag & item of interest.
    """
    tag = models.ForeignKey(Tag, null=False, blank=False, verbose_name='tag unique identifier')
    politician = models.ForeignKey(Politician, null=False, blank=False, verbose_name='politician unique identifier')
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
    tag = models.ForeignKey(Tag, null=False, blank=False, verbose_name='tag unique identifier')
    politician = models.ForeignKey(Politician, null=False, blank=False, verbose_name='politician unique identifier')
    # measure_id
    # office_id
    # issue_id
