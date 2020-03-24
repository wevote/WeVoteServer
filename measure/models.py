# measure/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_we_vote_id_contest_measure_integer, \
    fetch_next_we_vote_id_measure_campaign_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, \
    MEASURE_TITLE_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES, MEASURE_TITLE_SYNONYMS, positive_value_exists, STATE_CODE_MAP


logger = wevote_functions.admin.get_logger(__name__)

CONTEST_MEASURE_UNIQUE_IDENTIFIERS = [
    'ballotpedia_district_id',
    'ballotpedia_election_id',
    'ballotpedia_measure_id',
    'ballotpedia_measure_name',
    'ballotpedia_measure_status',
    'ballotpedia_measure_summary',
    'ballotpedia_measure_text',
    'ballotpedia_measure_url',
    'ballotpedia_no_vote_description',
    'ballotpedia_page_title',
    'ballotpedia_yes_vote_description',
    'cctl_uuid',
    'district_id',
    'district_name',
    'district_scope',
    'election_day_text',
    'google_ballot_placement',
    'google_civic_election_id',
    'google_civic_measure_title',
    # 'google_civic_measure_title2',
    # 'google_civic_measure_title3',
    # 'google_civic_measure_title4',
    # 'google_civic_measure_title5',
    'maplight_id',
    'measure_subtitle',
    'measure_text',
    'measure_title',
    'measure_url',
    'ocd_division_id',
    'primary_party',
    'state_code',
    'vote_smart_id',
    'we_vote_id',
    'wikipedia_page_id',
    'wikipedia_page_title',
    'wikipedia_photo_url',
]


# The measure that is on the ballot (equivalent to ContestOffice)
class ContestMeasure(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "meas", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_measure_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id",
        max_length=255, default=None, null=True, blank=True, unique=True, db_index=True)
    maplight_id = models.CharField(verbose_name="maplight unique identifier",
                                   max_length=255, null=True, blank=True, unique=False)
    vote_smart_id = models.CharField(verbose_name="votesmart unique identifier",
                                     max_length=200, null=True, blank=True, unique=False)
    # The title of the measure (e.g. 'Proposition 42').
    measure_title = models.CharField(verbose_name="measure title", max_length=255, null=False, blank=False)
    # The measure's title as passed over by Google Civic. We save this so we can match to this measure even
    # if we edit the measure's name locally.
    google_civic_measure_title = models.CharField(verbose_name="measure name exactly as received from google civic",
                                                  max_length=255, null=True, blank=True)
    google_civic_measure_title2 = models.CharField(verbose_name="measure name from google civic alternative",
                                                   max_length=255, null=True, blank=True)
    google_civic_measure_title3 = models.CharField(verbose_name="measure name from google civic alternative",
                                                   max_length=255, null=True, blank=True)
    google_civic_measure_title4 = models.CharField(verbose_name="measure name from google civic alternative",
                                                   max_length=255, null=True, blank=True)
    google_civic_measure_title5 = models.CharField(verbose_name="measure name from google civic alternative",
                                                   max_length=255, null=True, blank=True)
    # A brief description of the referendum. This field is only populated for contests of type 'Referendum'.
    measure_subtitle = models.TextField(verbose_name="google civic referendum subtitle",
                                        null=True, blank=True, default="")
    # The text of the measure. This field is only populated for contests of type 'Referendum'.
    measure_text = models.TextField(verbose_name="measure text", null=True, blank=False)
    # A link to the referendum. This field is only populated for contests of type 'Referendum'.
    measure_url = models.CharField(verbose_name="measure details url", max_length=255, null=True, blank=False)
    google_ballot_placement = models.BigIntegerField(
        verbose_name="the order this item should appear on the ballot", null=True, blank=True, unique=False)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=255, null=True, blank=True, db_index=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id new", default=0, null=False, blank=False)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    # ballot_placement: We store ballot_placement in the BallotItem table instead because it is different for each voter
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="primary party", max_length=255, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="district name", max_length=255, null=False, blank=False)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="district scope", max_length=255, null=False, blank=False)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_id = models.CharField(verbose_name="google civic district id", max_length=255, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="state this measure affects",
                                  max_length=2, null=True, blank=True, db_index=True)
    # Day of the election in YYYY-MM-DD format.
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.URLField(
        verbose_name='url of wikipedia logo', max_length=255, blank=True, null=True)

    ballotpedia_district_id = models.PositiveIntegerField(
        verbose_name="ballotpedia district id", default=0, null=False, blank=False)
    ballotpedia_election_id = models.PositiveIntegerField(
        verbose_name="ballotpedia election id", default=0, null=False, blank=False)
    ballotpedia_measure_id = models.PositiveIntegerField(
        verbose_name="ballotpedia measure id", default=0, null=False, blank=False)
    ballotpedia_measure_name = models.CharField(
        verbose_name="ballotpedia measure name", max_length=255, null=True, blank=True)
    ballotpedia_measure_status = models.CharField(
        verbose_name="ballotpedia measure status", max_length=255, null=True, blank=True)
    ballotpedia_measure_summary = models.TextField(
        verbose_name="ballotpedia measure summary", null=True, blank=True, default="")
    ballotpedia_measure_text = models.TextField(
        verbose_name="ballotpedia measure text", null=True, blank=True, default="")
    ballotpedia_measure_url = models.URLField(
        verbose_name='ballotpedia url of measure', max_length=255, blank=True, null=True)
    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(
        verbose_name='url of ballotpedia logo', max_length=255, blank=True, null=True)
    ballotpedia_yes_vote_description = models.TextField(
        verbose_name="what a yes vote means", null=True, blank=True, default=None)
    ballotpedia_no_vote_description = models.TextField(
        verbose_name="what a no vote means", null=True, blank=True, default=None)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)

    def get_measure_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        # Pull this from ocdDivisionId
        ocd_division_id = self.ocd_division_id
        return extract_state_from_ocd_division_id(ocd_division_id)

    def get_measure_text(self):
        if positive_value_exists(self.measure_text):
            return self.measure_text
        if positive_value_exists(self.ballotpedia_measure_text):
            return self.ballotpedia_measure_text
        return ""

    def get_measure_url(self):
        if positive_value_exists(self.measure_url):
            return self.measure_url
        if positive_value_exists(self.ballotpedia_measure_url):
            return self.ballotpedia_measure_url
        return ""

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_contest_measure_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "meas" = tells us this is a unique id for a ContestMeasure
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}meas{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ContestMeasure, self).save(*args, **kwargs)


# The campaign that is supporting this Measure. Equivalent to CandidateCampaign
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
                                          max_length=255, null=False, blank=False)
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
    candidate_name = models.CharField(verbose_name="candidate name", max_length=255, null=False, blank=False)
    # The full name of the party the candidate is a member of.
    party = models.CharField(verbose_name="party", max_length=255, null=True, blank=True)
    # A URL for a photo of the candidate.
    photo_url = models.CharField(verbose_name="photoUrl", max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google election id",
                                                max_length=255, null=False, blank=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google election id", default=0, null=False, blank=False)
    # The URL for the candidate's campaign web site.
    url = models.URLField(
        verbose_name='website url of campaign', max_length=255, blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of campaign', blank=True, null=True)
    twitter_url = models.URLField(verbose_name='twitter url of campaign', blank=True, null=True)
    google_plus_url = models.URLField(verbose_name='google plus url of campaign', blank=True, null=True)
    youtube_url = models.URLField(verbose_name='youtube url of campaign', blank=True, null=True)
    # The email address for the candidate's campaign.
    measure_email = models.CharField(verbose_name="measure email", max_length=255, null=True, blank=True)
    # The voice phone number for the campaign office for this measure.
    measure_phone = models.CharField(verbose_name="measure phone", max_length=255, null=True, blank=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_measure_campaign_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "meascam" = tells us this is a unique id for a MeasureCampaign
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}meascam{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(MeasureCampaign, self).save(*args, **kwargs)


class ContestMeasureManager(models.Model):

    def __unicode__(self):
        return "ContestMeasureManager"

    def retrieve_contest_measure_from_id(self, contest_measure_id, read_only=False):
        contest_measure_manager = ContestMeasureManager()
        return contest_measure_manager.retrieve_contest_measure(contest_measure_id, read_only=read_only)

    def retrieve_contest_measure_from_we_vote_id(self, contest_measure_we_vote_id, read_only=False):
        contest_measure_id = 0
        contest_measure_manager = ContestMeasureManager()
        return contest_measure_manager.retrieve_contest_measure(contest_measure_id, contest_measure_we_vote_id,
                                                                read_only=read_only)

    def retrieve_contest_measure_from_maplight_id(self, maplight_id, read_only=False):
        contest_measure_id = 0
        contest_measure_we_vote_id = ''
        contest_measure_manager = ContestMeasureManager()
        return contest_measure_manager.retrieve_contest_measure(contest_measure_id, contest_measure_we_vote_id,
                                                                maplight_id, read_only=read_only)

    def retrieve_contest_measure_from_ballotpedia_measure_id(self, ballotpedia_measure_id, read_only=False):
        contest_measure_manager = ContestMeasureManager()
        return contest_measure_manager.retrieve_contest_measure(ballotpedia_measure_id=ballotpedia_measure_id,
                                                                read_only=read_only)

    def fetch_contest_measure_id_from_maplight_id(self, maplight_id):
        contest_measure_id = 0
        contest_measure_we_vote_id = ''
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure(
            contest_measure_id, contest_measure_we_vote_id, maplight_id, read_only=True)
        if results['success']:
            return results['contest_measure_id']
        return 0

    def fetch_contest_measure_we_vote_id_from_id(self, contest_measure_id):
        contest_measure_we_vote_id = ''
        maplight_id = ''
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure(
            contest_measure_id, contest_measure_we_vote_id, maplight_id, read_only=True)
        if results['success']:
            return results['contest_measure_we_vote_id']
        return 0

    def fetch_google_civic_election_id_from_measure_we_vote_id(self, contest_measure_we_vote_id):
        """
        Take in contest_measure_we_vote_id and return google_civic_election_id
        :param contest_measure_we_vote_id:
        :return:
        """
        google_civic_election_id = '0'
        try:
            if positive_value_exists(contest_measure_we_vote_id):
                contest_measure_on_stage = ContestMeasure.objects.using('readonly').get(
                    we_vote_id=contest_measure_we_vote_id)
                google_civic_election_id = contest_measure_on_stage.google_civic_election_id

        except ContestMeasure.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ContestMeasure.DoesNotExist:
            pass

        return google_civic_election_id

    def update_or_create_contest_measure(
            self, we_vote_id='', google_civic_election_id='', measure_title='',
            district_id='', district_name='', state_code='', ballotpedia_measure_id='',
            updated_contest_measure_values={}):
        """
        Either update or create an measure entry.
        """
        exception_multiple_object_returned = False
        new_measure_created = False
        measure_updated = False
        proceed_to_update_or_save = True
        success = False
        status = 'ENTERING update_or_create_contest_measure '

        contest_measure_on_stage = ContestMeasure()
        if positive_value_exists(we_vote_id):
            # If here we are dealing with an existing measure
            pass
        elif positive_value_exists(ballotpedia_measure_id):
            # We need to find or create a new ballotpedia_measure_id
            pass
        else:
            # If here, we are dealing with a measure that is new to We Vote
            if not (district_id or district_name):
                success = False
                status += 'MISSING_DISTRICT_ID-MEASURE_UPDATE_OR_CREATE'
                proceed_to_update_or_save = False
            elif not state_code:
                success = False
                status += 'MISSING_STATE_CODE-MEASURE_UPDATE_OR_CREATE'
                proceed_to_update_or_save = False
            elif not measure_title:
                success = False
                status += 'MISSING_MEASURE_TITLE-MEASURE_UPDATE_OR_CREATE'
                proceed_to_update_or_save = False

        if not google_civic_election_id:
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID-MEASURE_UPDATE_OR_CREATE'
            proceed_to_update_or_save = False

        if proceed_to_update_or_save:
            # if a contest_measure_on_stage is found, *then* update it with updated_contest_measure_values

            if positive_value_exists(we_vote_id):
                try:
                    contest_measure_on_stage, new_measure_created = ContestMeasure.objects.update_or_create(
                        google_civic_election_id__exact=google_civic_election_id,
                        we_vote_id__iexact=we_vote_id,
                        defaults=updated_contest_measure_values)
                    success = True
                    status += 'CONTEST_UPDATE_OR_CREATE_SUCCEEDED '
                    measure_updated = not new_measure_created
                except ContestMeasure.MultipleObjectsReturned as e:
                    handle_record_found_more_than_one_exception(e, logger=logger)
                    success = False
                    status += 'MULTIPLE_MATCHING_CONTEST_MEASURES_FOUND'
                    exception_multiple_object_returned = True
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_OR_CREATE ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            elif positive_value_exists(ballotpedia_measure_id):
                try:
                    contest_measure_on_stage, new_measure_created = ContestMeasure.objects.update_or_create(
                        google_civic_election_id=google_civic_election_id,
                        ballotpedia_measure_id=ballotpedia_measure_id,
                        defaults=updated_contest_measure_values)
                    success = True
                    status += 'CONTEST_UPDATE_OR_CREATE_SUCCEEDED_BY_BALLOTPEDIA_MEASURE_ID '
                    measure_updated = not new_measure_created
                except ContestMeasure.MultipleObjectsReturned as e:
                    handle_record_found_more_than_one_exception(e, logger=logger)
                    success = False
                    status += 'MULTIPLE_MATCHING_CONTEST_MEASURES_FOUND ' + str(e) + ' '
                    exception_multiple_object_returned = True
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_OR_CREATE ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Given we might have the measure listed by google_civic_measure_title
                # OR measure_title, we need to check both before we try to create a new entry
                contest_measure_found = False
                try:
                    contest_measure_on_stage = ContestMeasure.objects.get(
                        google_civic_election_id__exact=google_civic_election_id,
                        google_civic_measure_title__iexact=measure_title,
                        state_code__iexact=state_code
                    )
                    contest_measure_found = True
                    success = True
                    status += 'CONTEST_MEASURE_SAVED '
                except ContestMeasure.MultipleObjectsReturned as e:
                    success = False
                    status += 'MULTIPLE_MATCHING_CONTEST_MEASURES_FOUND_BY_GOOGLE_CIVIC_MEASURE_TITLE '
                    exception_multiple_object_returned = True
                except ContestMeasure.DoesNotExist:
                    exception_does_not_exist = True
                    status += "RETRIEVE_MEASURE_NOT_FOUND "
                except Exception as e:
                    status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_MEASURE_TITLE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

                if not contest_measure_found and not exception_multiple_object_returned:
                    # Try to find record based on measure_title (instead of google_civic_measure_title)
                    try:
                        contest_measure_on_stage = ContestMeasure.objects.get(
                            google_civic_election_id__exact=google_civic_election_id,
                            measure_title__iexact=measure_title,
                            state_code__iexact=state_code
                        )
                        contest_measure_found = True
                        success = True
                        status += 'CONTEST_MEASURE_SAVED '
                    except ContestMeasure.MultipleObjectsReturned as e:
                        success = False
                        status += 'MULTIPLE_MATCHING_CONTEST_MEASURES_FOUND_BY_MEASURE_NAME '
                        exception_multiple_object_returned = True
                    except ContestMeasure.DoesNotExist:
                        exception_does_not_exist = True
                        status += "RETRIEVE_MEASURE_NOT_FOUND "
                    except Exception as e:
                        status += 'FAILED_TO_RETRIEVE_MEASURE_BY_MEASURE_TITLE ' \
                                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                        success = False

                if exception_multiple_object_returned:
                    # We can't proceed because there is an error with the data
                    success = False
                elif contest_measure_found:
                    # Update record
                    try:
                        new_measure_created = False
                        measure_updated = False
                        measure_changes_found = False
                        for key, value in updated_contest_measure_values.items():
                            if hasattr(contest_measure_on_stage, key):
                                measure_changes_found = True
                                setattr(contest_measure_on_stage, key, value)
                        if measure_changes_found and positive_value_exists(contest_measure_on_stage.we_vote_id):
                            contest_measure_on_stage.save()
                            measure_updated = True
                        if measure_updated:
                            success = True
                            status += "CONTEST_MEASURE_UPDATED "
                        else:
                            success = False
                            status += "CONTEST_MEASURE_NOT_UPDATED "
                    except Exception as e:
                        status += 'FAILED_TO_UPDATE_CONTEST_MEASURE ' \
                                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                        success = False
                else:
                    # Create record
                    try:
                        measure_updated = False
                        new_measure_created = False
                        contest_measure_on_stage = ContestMeasure.objects.create(
                            google_civic_election_id=google_civic_election_id,
                            measure_title=measure_title,
                            district_id=district_id,
                            district_name=district_name,
                            state_code=district_name,
                        )
                        if positive_value_exists(contest_measure_on_stage.id):
                            for key, value in updated_contest_measure_values.items():
                                if hasattr(contest_measure_on_stage, key):
                                    setattr(contest_measure_on_stage, key, value)
                            contest_measure_on_stage.save()
                            new_measure_created = True
                        if new_measure_created:
                            success = True
                            status += "CONTEST_MEASURE_CREATED "
                        else:
                            success = False
                            status += "CONTEST_MEASURE_NOT_CREATED "
                    except Exception as e:
                        status += 'FAILED_TO_CREATE_CONTEST_MEASURE ' \
                                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                        success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_measure_created':      new_measure_created,
            'contest_measure':          contest_measure_on_stage,
            'saved':                    new_measure_created,
            'updated':                  measure_updated,
            'not_processed':            True if not success else False,
        }
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_contest_measure(self, contest_measure_id=0, contest_measure_we_vote_id='', maplight_id=None,
                                 ballotpedia_measure_id=0, read_only=False):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        contest_measure_on_stage = ContestMeasure()
        status = ""
        success = True

        try:
            if positive_value_exists(contest_measure_id):
                if positive_value_exists(read_only):
                    contest_measure_on_stage = ContestMeasure.objects.using('readonly').get(id=contest_measure_id)
                else:
                    contest_measure_on_stage = ContestMeasure.objects.get(id=contest_measure_id)
                contest_measure_id = contest_measure_on_stage.id
                contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
                status += "RETRIEVE_MEASURE_FOUND_BY_ID "
            elif positive_value_exists(contest_measure_we_vote_id):
                if positive_value_exists(read_only):
                    contest_measure_on_stage = ContestMeasure.objects.using('readonly').get(
                        we_vote_id=contest_measure_we_vote_id)
                else:
                    contest_measure_on_stage = ContestMeasure.objects.get(we_vote_id=contest_measure_we_vote_id)
                contest_measure_id = contest_measure_on_stage.id
                contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
                status += "RETRIEVE_MEASURE_FOUND_BY_WE_VOTE_ID "
            elif positive_value_exists(maplight_id):
                if positive_value_exists(read_only):
                    contest_measure_on_stage = ContestMeasure.objects.using('readonly').get(maplight_id=maplight_id)
                else:
                    contest_measure_on_stage = ContestMeasure.objects.get(maplight_id=maplight_id)
                contest_measure_id = contest_measure_on_stage.id
                contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
                status += "RETRIEVE_MEASURE_FOUND_BY_MAPLIGHT_ID "
            elif positive_value_exists(ballotpedia_measure_id):
                if positive_value_exists(read_only):
                    contest_measure_on_stage = ContestMeasure.objects.using('readonly').get(
                        ballotpedia_measure_id=ballotpedia_measure_id)
                else:
                    contest_measure_on_stage = ContestMeasure.objects.get(ballotpedia_measure_id=ballotpedia_measure_id)
                contest_measure_id = contest_measure_on_stage.id
                contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
                status += "RETRIEVE_MEASURE_FOUND_BY_BALLOTPEDIA_MEASURE_ID "
            else:
                status += "RETRIEVE_MEASURE_SEARCH_INDEX_MISSING "
                success = False
        except ContestMeasure.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status += "RETRIEVE_MEASURE_MULTIPLE_OBJECTS_RETURNED "
            success = False
        except ContestMeasure.DoesNotExist:
            exception_does_not_exist = True
            status += "RETRIEVE_MEASURE_NOT_FOUND "
        except Exception as e:
            status += "RETRIEVE_MEASURE_EXCEPTION " + str(e) + " "
            success = False


        results = {
            'success':                      success,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'contest_measure_found':        True if convert_to_int(contest_measure_id) > 0 else False,
            'contest_measure_id':           convert_to_int(contest_measure_id),
            'contest_measure_we_vote_id':   contest_measure_we_vote_id,
            'contest_measure':              contest_measure_on_stage,
        }
        return results

    def fetch_contest_measure_id_from_we_vote_id(self, contest_measure_we_vote_id):
        """
        Take in contest_measure_we_vote_id and return internal/local-to-this-database contest_measure_id
        :param contest_measure_we_vote_id:
        :return:
        """
        contest_measure_id = 0
        try:
            if positive_value_exists(contest_measure_we_vote_id):
                contest_measure_on_stage = ContestMeasure.objects.get(we_vote_id=contest_measure_we_vote_id)
                contest_measure_id = contest_measure_on_stage.id

        except ContestMeasure.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ContestMeasure.DoesNotExist:
            contest_measure_id = 0

        return contest_measure_id

    def fetch_state_code_from_we_vote_id(self, contest_measure_we_vote_id):
        """
        Take in contest_measure_we_vote_id and return return the state_code
        :param contest_measure_we_vote_id:
        :return:
        """
        state_code = ""
        try:
            if positive_value_exists(contest_measure_we_vote_id):
                contest_measure_on_stage = ContestMeasure.objects.get(we_vote_id=contest_measure_we_vote_id)
                state_code = contest_measure_on_stage.state_code

        except ContestMeasure.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ContestMeasure.DoesNotExist:
            pass

        return state_code

    def retrieve_measures_are_not_duplicates_list(self, contest_measure_we_vote_id, read_only=True):
        """
        Get a list of other measure_we_vote_id's that are not duplicates
        :param contest_measure_we_vote_id:
        :param read_only:
        :return:
        """
        # Note that the direction of the linkage does not matter
        contest_measures_are_not_duplicates_list1 = []
        contest_measures_are_not_duplicates_list2 = []
        try:
            if positive_value_exists(read_only):
                contest_measures_are_not_duplicates_list_query = \
                    ContestMeasuresAreNotDuplicates.objects.using('readonly').filter(
                        contest_measure1_we_vote_id__iexact=contest_measure_we_vote_id,
                    )
            else:
                contest_measures_are_not_duplicates_list_query = \
                    ContestMeasuresAreNotDuplicates.objects.using('readonly').filter(
                        contest_measure1_we_vote_id__iexact=contest_measure_we_vote_id,
                    )
            contest_measures_are_not_duplicates_list1 = list(contest_measures_are_not_duplicates_list_query)
            success = True
            status = "CONTEST_MEASURES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except ContestMeasuresAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status = 'NO_CONTEST_MEASURES_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status = "CONTEST_MEASURES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1 " + str(e) + ' '

        if success:
            try:
                if positive_value_exists(read_only):
                    contest_measures_are_not_duplicates_list_query = \
                        ContestMeasuresAreNotDuplicates.objects.using('readonly').filter(
                            contest_measure2_we_vote_id__iexact=contest_measure_we_vote_id,
                        )
                else:
                    contest_measures_are_not_duplicates_list_query = \
                        ContestMeasuresAreNotDuplicates.objects.filter(
                            contest_measure2_we_vote_id__iexact=contest_measure_we_vote_id,
                        )
                contest_measures_are_not_duplicates_list2 = list(contest_measures_are_not_duplicates_list_query)
                success = True
                status = "CONTEST_MEASURES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except ContestMeasuresAreNotDuplicates.DoesNotExist:
                success = True
                status = 'NO_CONTEST_MEASURES_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status = "CONTEST_MEASURES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2 " + str(e) + ' '

        contest_measures_are_not_duplicates_list = \
            contest_measures_are_not_duplicates_list1 + contest_measures_are_not_duplicates_list2
        contest_measures_are_not_duplicates_list_found = positive_value_exists(len(
            contest_measures_are_not_duplicates_list))
        contest_measures_are_not_duplicates_list_we_vote_ids = []
        for one_entry in contest_measures_are_not_duplicates_list:
            if one_entry.contest_measure1_we_vote_id != contest_measure_we_vote_id:
                contest_measures_are_not_duplicates_list_we_vote_ids.append(one_entry.contest_measure1_we_vote_id)
            elif one_entry.contest_measure2_we_vote_id != contest_measure_we_vote_id:
                contest_measures_are_not_duplicates_list_we_vote_ids.append(one_entry.contest_measure2_we_vote_id)
        results = {
            'success':                                              success,
            'status':                                               status,
            'contest_measures_are_not_duplicates_list_found':       contest_measures_are_not_duplicates_list_found,
            'contest_measures_are_not_duplicates_list':             contest_measures_are_not_duplicates_list,
            'contest_measures_are_not_duplicates_list_we_vote_ids':
                contest_measures_are_not_duplicates_list_we_vote_ids,
        }
        return results

    def fetch_measures_are_not_duplicates_list_we_vote_ids(self, measure_we_vote_id):
        results = self.retrieve_measures_are_not_duplicates_list(measure_we_vote_id)
        return results['contest_measures_are_not_duplicates_list_we_vote_ids']

    def create_measure_row_entry(self, measure_title, measure_subtitle, measure_text, state_code, ctcl_uuid,
                                 google_civic_election_id, defaults):
        """
        Create ContestMeasure table entry with Measure details from CTCL data
        :param measure_title: 
        :param measure_subtitle: 
        :param measure_text: 
        :param state_code: 
        :param ctcl_uuid: 
        :param google_civic_election_id: 
        :param defaults:
        :return:
        """
        success = False
        status = ""
        measure_updated = False
        new_measure_created = False
        new_measure = ''

        try:
            new_measure = ContestMeasure.objects.create(
                measure_title=measure_title, measure_subtitle=measure_subtitle, measure_text=measure_text,
                state_code=state_code, ctcl_uuid=ctcl_uuid, google_civic_election_id=google_civic_election_id)
            if new_measure:
                success = True
                status += "CREATE_MEASURE_ROW_ENTRY-MEASURE_CREATED "
                new_measure_created = True
                if 'election_day_text' in defaults:
                    new_measure.election_day_text = defaults['election_day_text']
                if 'ballotpedia_district_id' in defaults:
                    new_measure.ballotpedia_district_id = defaults['ballotpedia_district_id']
                if 'ballotpedia_election_id' in defaults:
                    new_measure.ballotpedia_election_id = defaults['ballotpedia_election_id']
                if 'ballotpedia_measure_id' in defaults:
                    new_measure.ballotpedia_measure_id = defaults['ballotpedia_measure_id']
                if 'ballotpedia_measure_name' in defaults:
                    new_measure.ballotpedia_measure_name = defaults['ballotpedia_measure_name']
                if 'ballotpedia_measure_status' in defaults:
                    new_measure.ballotpedia_measure_status = defaults['ballotpedia_measure_status']
                if 'ballotpedia_measure_summary' in defaults:
                    new_measure.ballotpedia_measure_summary = defaults['ballotpedia_measure_summary']
                if 'ballotpedia_measure_text' in defaults:
                    new_measure.ballotpedia_measure_text = defaults['ballotpedia_measure_text']
                if 'ballotpedia_measure_url' in defaults:
                    new_measure.ballotpedia_measure_url = defaults['ballotpedia_measure_url']
                if 'ballotpedia_yes_vote_description' in defaults:
                    new_measure.ballotpedia_yes_vote_description = defaults['ballotpedia_yes_vote_description']
                if 'ballotpedia_no_vote_description' in defaults:
                    new_measure.ballotpedia_no_vote_description = defaults['ballotpedia_no_vote_description']
                if 'measure_url' in defaults:
                    new_measure.measure_url = defaults['measure_url']
                if 'state_code' in defaults:
                    new_measure.state_code = defaults['state_code']
                if positive_value_exists(new_measure.we_vote_id):
                    new_measure.save()
                else:
                    status += "COULD_NOT_SAVE-NO_WE_VOTE_ID "
            else:
                success = False
                status += "CREATE_MEASURE_ROW_ENTRY-MEASURE_CREATE_FAILED "
        except Exception as e:
            success = False
            new_measure_created = False
            status += "CREATE_MEASURE_ROW_ENTRY-MEASURE_CREATE_ERROR "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':               success,
                'status':                status,
                'new_measure_created':   new_measure_created,
                'measure_updated':       measure_updated,
                'new_measure':           new_measure,
            }
        return results

    def update_measure_row_entry(self, measure_title, measure_subtitle, measure_text, state_code, ctcl_uuid,
                                 google_civic_election_id, measure_we_vote_id, defaults):
        """
            Update ContestMeasure table entry with matching we_vote_id 
        :param measure_title: 
        :param measure_subtitle: 
        :param measure_text: 
        :param state_code: 
        :param ctcl_uuid: 
        :param google_civic_election_id: 
        :param measure_we_vote_id:  
        :param defaults:
        :return:
        """
        success = False
        status = ""
        measure_updated = False
        existing_measure_entry = ''

        try:
            existing_measure_entry = ContestMeasure.objects.get(we_vote_id__iexact=measure_we_vote_id)
            if existing_measure_entry:
                # found the existing entry, update the values
                existing_measure_entry.measure_title = measure_title
                existing_measure_entry.measure_subtitle = measure_subtitle
                existing_measure_entry.measure_text = measure_text
                existing_measure_entry.state_code = state_code
                existing_measure_entry.ctcl_uuid = ctcl_uuid
                existing_measure_entry.google_civic_election_id = google_civic_election_id
                if 'election_day_text' in defaults:
                    existing_measure_entry.election_day_text = defaults['election_day_text']
                if 'ballotpedia_district_id' in defaults:
                    existing_measure_entry.ballotpedia_district_id = defaults['ballotpedia_district_id']
                if 'ballotpedia_election_id' in defaults:
                    existing_measure_entry.ballotpedia_election_id = defaults['ballotpedia_election_id']
                if 'ballotpedia_measure_id' in defaults:
                    existing_measure_entry.ballotpedia_measure_id = defaults['ballotpedia_measure_id']
                if 'ballotpedia_measure_name' in defaults:
                    existing_measure_entry.ballotpedia_measure_name = defaults['ballotpedia_measure_name']
                if 'ballotpedia_measure_status' in defaults:
                    existing_measure_entry.ballotpedia_measure_status = defaults['ballotpedia_measure_status']
                if 'ballotpedia_measure_summary' in defaults:
                    existing_measure_entry.ballotpedia_measure_summary = defaults['ballotpedia_measure_summary']
                if 'ballotpedia_measure_text' in defaults:
                    existing_measure_entry.ballotpedia_measure_text = defaults['ballotpedia_measure_text']
                if 'ballotpedia_measure_url' in defaults:
                    existing_measure_entry.ballotpedia_measure_url = defaults['ballotpedia_measure_url']
                if 'ballotpedia_yes_vote_description' in defaults:
                    existing_measure_entry.ballotpedia_yes_vote_description = \
                        defaults['ballotpedia_yes_vote_description']
                if 'ballotpedia_no_vote_description' in defaults:
                    existing_measure_entry.ballotpedia_no_vote_description = defaults['ballotpedia_no_vote_description']
                if 'measure_url' in defaults:
                    existing_measure_entry.measure_url = defaults['measure_url']
                if 'state_code' in defaults:
                    existing_measure_entry.state_code = defaults['state_code']
                measure_updated = False
                # now go ahead and save this entry (update)
                if positive_value_exists(existing_measure_entry.we_vote_id):
                    existing_measure_entry.save()
                    measure_updated = True
                    success = True
                    status += "UPDATE_MEASURE_ROW_ENTRY-MEASURE_UPDATED "
                else:
                    success = False
                    status += "UPDATE_MEASURE_ROW_ENTRY-MISSING_WE_VOTE_ID "
        except Exception as e:
            success = False
            measure_updated = False
            status += "UPDATE_MEASURE_ROW_ENTRY-MEASURE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':          success,
                'status':           status,
                'measure_updated':  measure_updated,
                'updated_measure':  existing_measure_entry,
            }
        return results


class ContestMeasureListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Measures
    """

    def __unicode__(self):
        return "ContestMeasureListManager"

    def fetch_measures_from_non_unique_identifiers_count(
            self, google_civic_election_id, state_code, measure_title, ignore_measure_we_vote_id_list=[]):
        keep_looking_for_duplicates = True
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(measure_title):
            # Search by ContestMeasure name exact match
            try:
                contest_measure_query = ContestMeasure.objects.all()
                contest_measure_query = contest_measure_query.filter(measure_title__iexact=measure_title,
                                                                     google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    contest_measure_query = contest_measure_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_measure_we_vote_id_list):
                    contest_measure_query = contest_measure_query.exclude(we_vote_id__in=ignore_measure_we_vote_id_list)

                contest_measure_count = contest_measure_query.count()
                if positive_value_exists(contest_measure_count):
                    return contest_measure_count
            except ContestMeasure.DoesNotExist:
                status += "CONTEST_MEASURES_COUNT_NOT_FOUND "
            except Exception as e:
                keep_looking_for_duplicates = False

        return 0

    def retrieve_measures(self, google_civic_election_id=0, ballotpedia_district_id=0, state_code="", limit=0,
                          read_only=False):
        measure_list_objects = []
        measure_list_light = []
        measure_list_found = False

        try:
            if positive_value_exists(read_only):
                measure_queryset = ContestMeasure.objects.using('readonly').all()
            else:
                measure_queryset = ContestMeasure.objects.all()
            if positive_value_exists(google_civic_election_id):
                measure_queryset = measure_queryset.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(ballotpedia_district_id):
                measure_queryset = measure_queryset.filter(ballotpedia_district_id=ballotpedia_district_id)
            if positive_value_exists(state_code):
                measure_queryset = measure_queryset.filter(state_code__iexact=state_code)
            if positive_value_exists(limit):
                measure_list_objects = measure_queryset[:limit]
            else:
                measure_list_objects = list(measure_queryset)

            if len(measure_list_objects):
                measure_list_found = True
                status = 'MEASURES_RETRIEVED'
                success = True
            else:
                status = 'NO_MEASURES_RETRIEVED'
                success = True
        except ContestMeasure.DoesNotExist:
            # No measures found. Not a problem.
            status = 'NO_MEASURES_FOUND_DoesNotExist'
            measure_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_measures ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if measure_list_found:
            for measure in measure_list_objects:
                one_measure = {
                    'ballot_item_display_name': measure.measure_title,
                    'measure_we_vote_id':       measure.we_vote_id,
                    'office_we_vote_id':        '',
                    'candidate_we_vote_id':     '',
                }
                measure_list_light.append(one_measure.copy())

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'measure_list_found':       measure_list_found,
            'measure_list_objects':     measure_list_objects,
            'measure_list_light':       measure_list_light,
        }
        return results

    def retrieve_all_measures_for_upcoming_election(self, google_civic_election_id_list=[], state_code='',
                                                    return_list_of_objects=False, limit=300, read_only=False):
        measure_list_objects = []
        measure_list_light = []
        measure_list_found = False
        status = ""

        try:
            if positive_value_exists(read_only):
                measure_queryset = ContestMeasure.objects.using('readonly').all()
            else:
                measure_queryset = ContestMeasure.objects.all()
            if positive_value_exists(google_civic_election_id_list) and len(google_civic_election_id_list):
                measure_queryset = measure_queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
            else:
                success = False
                status += "RETRIEVE_ALL_MEASURES_FOR_UPCOMING_ELECTION-MISSING_ELECTION_ID "
                results = {
                    'success': success,
                    'status': status,
                    'google_civic_election_id_list':    google_civic_election_id_list,
                    'measure_list_found': measure_list_found,
                    'measure_list_objects': measure_list_objects if return_list_of_objects else [],
                    'measure_list_light': measure_list_light,
                }
                return results
            if positive_value_exists(state_code):
                measure_queryset = measure_queryset.filter(state_code__iexact=state_code)
            measure_queryset = measure_queryset.order_by("measure_title")
            # We never expect more than 300 measures for one election
            if positive_value_exists(limit):
                measure_list_objects = measure_queryset[:limit]
            else:
                measure_list_objects = list(measure_queryset)

            if len(measure_list_objects):
                measure_list_found = True
                status += 'MEASURES_RETRIEVED '
                success = True
            else:
                status += 'NO_MEASURES_RETRIEVED '
                success = True
        except ContestMeasure.DoesNotExist:
            # No measures found. Not a problem.
            status += 'NO_MEASURES_FOUND_DoesNotExist '
            measure_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_measures_for_upcoming_election ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            success = False

        if measure_list_found:
            for measure in measure_list_objects:
                one_measure = {
                    'ballot_item_display_name': measure.measure_title,
                    'measure_we_vote_id':       measure.we_vote_id,
                    'office_we_vote_id':        '',
                    'candidate_we_vote_id':     '',
                }
                measure_list_light.append(one_measure.copy())

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id_list':    google_civic_election_id_list,
            'measure_list_found':       measure_list_found,
            'measure_list_objects':     measure_list_objects if return_list_of_objects else [],
            'measure_list_light':       measure_list_light,
        }
        return results

    def retrieve_contest_measures_from_non_unique_identifiers(
            self, google_civic_election_id_list, incoming_state_code, contest_measure_title,
            district_id='', district_name='',
            ignore_measure_we_vote_id_list=[],
            read_only=False):
        keep_looking_for_duplicates = True
        success = False
        contest_measure = ContestMeasure()
        contest_measure_found = False
        contest_measure_list_filtered = []
        contest_measure_list_found = False
        multiple_entries_found = False
        status = ""

        try:
            if positive_value_exists(read_only):
                contest_measure_query = ContestMeasure.objects.using('readonly').all()
            else:
                contest_measure_query = ContestMeasure.objects.all()
            # TODO Is there a way to filter with "dash" insensitivity? - vs --
            contest_measure_query = contest_measure_query.filter(
                measure_title__iexact=contest_measure_title,
                state_code__iexact=incoming_state_code,
                google_civic_election_id__in=google_civic_election_id_list)
            if positive_value_exists(district_id):
                contest_measure_query = contest_measure_query.filter(district_id=district_id)
            elif positive_value_exists(district_name):
                contest_measure_query = contest_measure_query.filter(district_name__iexact=district_name)

            if positive_value_exists(ignore_measure_we_vote_id_list):
                contest_measure_query = contest_measure_query.exclude(we_vote_id__in=ignore_measure_we_vote_id_list)

            contest_measure_list_filtered = list(contest_measure_query)
            if len(contest_measure_list_filtered):
                keep_looking_for_duplicates = False
                # if a single entry matches, update that entry
                if len(contest_measure_list_filtered) == 1:
                    status += 'RETRIEVE_CONTEST_MEASURES_FROM_NON_UNIQUE-SINGLE_ROW_RETRIEVED '
                    contest_measure = contest_measure_list_filtered[0]
                    contest_measure_found = True
                    contest_measure_list_found = True
                    success = True
                else:
                    # more than one entry found with a match in ContestMeasure
                    contest_measure_list_found = True
                    multiple_entries_found = True
                    status += 'RETRIEVE_CONTEST_MEASURES_FROM_NON_UNIQUE-MULTIPLE_ROWS_RETRIEVED '
                    success = True
            else:
                # Existing entry couldn't be found in the contest office table. We should keep looking for
                #  close matches
                success = True
        except ContestMeasure.DoesNotExist:
            # Existing entry couldn't be found in the contest office table. We should keep looking for
            #  close matches
            success = True

        # Strip away common words and look for direct matches
        if keep_looking_for_duplicates:
            try:
                if positive_value_exists(read_only):
                    contest_measure_query = ContestMeasure.objects.using('readonly').all()
                else:
                    contest_measure_query = ContestMeasure.objects.all()
                contest_measure_query = contest_measure_query.filter(
                    google_civic_election_id__in=google_civic_election_id_list)
                if positive_value_exists(incoming_state_code):
                    contest_measure_query = contest_measure_query.filter(state_code__iexact=incoming_state_code)

                if positive_value_exists(ignore_measure_we_vote_id_list):
                    contest_measure_query = contest_measure_query.exclude(we_vote_id__in=ignore_measure_we_vote_id_list)

                # Start with the contest_measure_title and remove MEASURE_TITLE_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES
                stripped_down_contest_measure_title = contest_measure_title.lower()
                for remove_this in MEASURE_TITLE_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES:
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove "of State", ex/ "of California"
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " of " + state_name.lower()
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove leading state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = state_name.lower() + " "
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove trailing state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " " + state_name.lower()
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove leading and trailing spaces
                stripped_down_contest_measure_title = stripped_down_contest_measure_title.strip()

                contest_measure_query = contest_measure_query.filter(
                    measure_title__icontains=stripped_down_contest_measure_title)

                contest_measure_list = list(contest_measure_query)

                if len(contest_measure_list):
                    keep_looking_for_duplicates = False
                    # if a single entry matches, update that entry
                    if len(contest_measure_list_filtered) == 1:
                        status += 'RETRIEVE_CONTEST_MEASURES_FROM_NON_UNIQUE-SINGLE_ROW_RETRIEVED2 '
                        contest_measure = contest_measure_list_filtered[0]
                        contest_measure_found = True
                        contest_measure_list_found = True
                        success = True
                    else:
                        # more than one entry found with a match in ContestMeasure
                        contest_measure_list_found = True
                        multiple_entries_found = True
                        status += 'RETRIEVE_CONTEST_MEASURES_FROM_NON_UNIQUE-MULTIPLE_ROWS_RETRIEVED2 '
                        success = True
                else:
                    # Existing entry couldn't be found in the contest office table. We should keep looking for
                    #  close matches
                    success = True
            except ContestMeasure.DoesNotExist:
                # Existing entry couldn't be found in the contest office table. We should keep looking for
                #  close matches
                success = True

        if keep_looking_for_duplicates:
            try:
                if positive_value_exists(read_only):
                    contest_measure_query = ContestMeasure.objects.using('readonly').all()
                else:
                    contest_measure_query = ContestMeasure.objects.all()
                contest_measure_query = contest_measure_query.filter(
                    google_civic_election_id__in=google_civic_election_id_list)
                if positive_value_exists(incoming_state_code):
                    contest_measure_query = contest_measure_query.filter(state_code__iexact=incoming_state_code)

                if positive_value_exists(ignore_measure_we_vote_id_list):
                    contest_measure_query = contest_measure_query.exclude(we_vote_id__in=ignore_measure_we_vote_id_list)

                # Start with the contest_measure_title and remove MEASURE_TITLE_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES
                stripped_down_contest_measure_title = contest_measure_title.lower()
                for remove_this in MEASURE_TITLE_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES:
                    # Currently MEASURE_TITLE_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES is empty
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove "of State", ex/ "of California"
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " of " + state_name.lower()
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove leading state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = state_name.lower() + " "
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove trailing state, ex/ "California "
                for state_code, state_name in STATE_CODE_MAP.items():
                    remove_this = " " + state_name.lower()
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.replace(remove_this, "")

                # Remove leading and trailing spaces
                stripped_down_contest_measure_title = stripped_down_contest_measure_title.strip()

                filters = []
                synonyms_found = False

                class BreakException(Exception):  # Also called LocalBreak elsewhere
                    pass

                break_exception = BreakException()  # Also called LocalBreak elsewhere

                one_synonym_list = []
                one_synonym_list_found = False
                try:
                    for one_synonym_list in MEASURE_TITLE_SYNONYMS:
                        for one_synonym in one_synonym_list:
                            if one_synonym in stripped_down_contest_measure_title:
                                one_synonym_list_found = True
                                raise break_exception
                except BreakException:
                    pass

                if one_synonym_list_found:
                    synonym_filters = []
                    for one_synonym in one_synonym_list:
                        new_filter = Q(measure_title__icontains=one_synonym)
                        synonym_filters.append(new_filter)

                    # Add the first query
                    if len(synonym_filters):
                        final_synonym_filters = synonym_filters.pop()

                        # ...and "OR" the remaining items in the list
                        for item in synonym_filters:
                            final_synonym_filters |= item

                        filters.append(final_synonym_filters)
                        synonyms_found = True

                if not synonyms_found:
                    # Remove leading and trailing spaces
                    stripped_down_contest_measure_title = stripped_down_contest_measure_title.strip()
                    if positive_value_exists(stripped_down_contest_measure_title):
                        new_filter = Q(measure_title__icontains=stripped_down_contest_measure_title)
                        filters.append(new_filter)

                if len(filters):
                    # Add the first query
                    final_filters = filters.pop()

                    # ...and "AND" the remaining items in the list
                    for item in filters:
                        final_filters &= item

                    contest_measure_query = contest_measure_query.filter(final_filters)

                    contest_measure_list = list(contest_measure_query)

                    if len(contest_measure_list):
                        keep_looking_for_duplicates = False
                        # if a single entry matches, update that entry
                        if len(contest_measure_list_filtered) == 1:
                            status += 'RETRIEVE_CONTEST_MEASURES_FROM_NON_UNIQUE-SINGLE_ROW_RETRIEVED3 '
                            contest_measure = contest_measure_list_filtered[0]
                            contest_measure_found = True
                            contest_measure_list_found = True
                            success = True
                        else:
                            # more than one entry found with a match in ContestMeasure
                            contest_measure_list_found = True
                            multiple_entries_found = True
                            status += 'RETRIEVE_CONTEST_MEASURES_FROM_NON_UNIQUE-MULTIPLE_ROWS_RETRIEVED3 '
                            success = True
                    else:
                        # Existing entry couldn't be found in the contest office table. We should keep looking for
                        #  close matches
                        success = True
            except ContestMeasure.DoesNotExist:
                # Existing entry couldn't be found in the ContestMeasure table. We should keep looking for
                #  close matches
                success = True

        results = {
            'success':                      success,
            'status':                       status,
            'contest_measure_found':        contest_measure_found,
            'contest_measure':              contest_measure,
            'contest_measure_list_found':   contest_measure_list_found,
            'contest_measure_list':         contest_measure_list_filtered,
            'google_civic_election_id_list': google_civic_election_id_list,
            'multiple_entries_found':       multiple_entries_found,
            'state_code':                   incoming_state_code,
        }
        return results

    def retrieve_measures_for_specific_elections(self, google_civic_election_id_list=[],
                                                 limit_to_this_state_code="",
                                                 return_list_of_objects=False):
        status = ""
        measure_list_objects = []
        measure_list_light = []
        measure_list_found = False

        if not positive_value_exists(google_civic_election_id_list) or not len(google_civic_election_id_list):
            success = False
            status += "LIST_OF_ELECTIONS_MISSING-FOR_MEASURES "
            results = {
                'success': success,
                'status': status,
                'measure_list_found': measure_list_found,
                'measure_list_objects': [],
                'measure_list_light': [],
            }
            return results

        try:
            measure_queryset = ContestMeasure.objects.all()
            measure_queryset = measure_queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
            if positive_value_exists(limit_to_this_state_code):
                measure_queryset = measure_queryset.filter(state_code__iexact=limit_to_this_state_code)
            measure_list_objects = list(measure_queryset)

            if len(measure_list_objects):
                measure_list_found = True
                status += 'MEASURES_RETRIEVED '
                success = True
            else:
                status += 'NO_MEASURES_RETRIEVED '
                success = True
        except ContestMeasure.DoesNotExist:
            # No measures found. Not a problem.
            status = 'NO_MEASURES_FOUND_DoesNotExist '
            measure_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_measures_for_specific_elections ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if measure_list_found:
            for measure in measure_list_objects:
                one_measure = {
                    'ballot_item_display_name': measure.measure_title,
                    'alternate_names': [],  # List of alternate names
                    'candidate_we_vote_id':     '',
                    'google_civic_election_id': measure.google_civic_election_id,
                    'office_we_vote_id':        '',
                    'more_info_url':            '',
                    'measure_we_vote_id':       measure.we_vote_id,
                }
                measure_list_light.append(one_measure)

        results = {
            'success':              success,
            'status':               status,
            'measure_list_found':   measure_list_found,
            'measure_list_objects': measure_list_objects if return_list_of_objects else [],
            'measure_list_light':   measure_list_light,
        }
        return results

    def retrieve_measure_count_for_election_and_state(self, google_civic_election_id=0, state_code=''):
        status = ''
        if not positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code):
            status += 'VALID_ELECTION_ID_AND_STATE_CODE_MISSING '
            results = {
                'success':                  False,
                'status':                   status,
                'google_civic_election_id': google_civic_election_id,
                'state_code':               state_code,
                'measure_count':            0,
            }
            return results

        try:
            measure_queryset = ContestMeasure.objects.using('readonly').all()
            if positive_value_exists(google_civic_election_id):
                google_civic_election_id_list = [convert_to_int(google_civic_election_id)]
                measure_queryset = measure_queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
            if positive_value_exists(state_code):
                measure_queryset = measure_queryset.filter(state_code__iexact=state_code)
            measure_count = measure_queryset.count()
            success = True
            status += "MEASURE_COUNT_FOUND "
        except ContestMeasure.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_MEASURES_FOUND_DoesNotExist '
            measure_count = 0
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED RETRIEVE_MEASURE_COUNT ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            success = False
            measure_count = 0

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'state_code':               state_code,
            'measure_count':            measure_count,
        }
        return results

    def retrieve_possible_duplicate_measures(self, measure_title, google_civic_election_id, measure_url, maplight_id,
                                             vote_smart_id,
                                             we_vote_id_from_master=''):
        measure_list_objects = []
        filters = []
        measure_list_found = False

        try:
            measure_queryset = ContestMeasure.objects.all()
            measure_queryset = measure_queryset.filter(google_civic_election_id=google_civic_election_id)
            # We don't look for contest_measure_we_vote_id because of the chance that locally we are using a
            # different we_vote_id
            # measure_queryset = measure_queryset.filter(contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                measure_queryset = measure_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            # We want to find measures with *any* of these values
            if positive_value_exists(measure_title):
                new_filter = Q(measure_title__iexact=measure_title)
                filters.append(new_filter)

            if positive_value_exists(measure_url):
                new_filter = Q(measure_url__iexact=measure_url)
                filters.append(new_filter)

            if positive_value_exists(maplight_id):
                new_filter = Q(maplight_id=maplight_id)
                filters.append(new_filter)

            if positive_value_exists(vote_smart_id):
                new_filter = Q(vote_smart_id=vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                measure_queryset = measure_queryset.filter(final_filters)

            measure_list_objects = measure_queryset

            if len(measure_list_objects):
                measure_list_found = True
                status = 'DUPLICATE_MEASURES_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_MEASURES_RETRIEVED'
                success = True
        except ContestMeasure.DoesNotExist:
            # No measures found. Not a problem.
            status = 'NO_DUPLICATE_MEASURES_FOUND_DoesNotExist'
            measure_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_measures ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'measure_list_found':       measure_list_found,
            'measure_list':             measure_list_objects,
        }
        return results

    def update_or_create_contest_measures_are_not_duplicates(self, contest_measure1_we_vote_id,
                                                             contest_measure2_we_vote_id):
        """
        Either update or create a contest_measure entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_contest_measures_are_not_duplicates_created = False
        contest_measures_are_not_duplicates = ContestMeasuresAreNotDuplicates()
        status = ""

        if positive_value_exists(contest_measure1_we_vote_id) and positive_value_exists(contest_measure2_we_vote_id):
            try:
                updated_values = {
                    'contest_measure1_we_vote_id': contest_measure1_we_vote_id,
                    'contest_measure2_we_vote_id': contest_measure2_we_vote_id,
                }
                contest_measures_are_not_duplicates, new_contest_measures_are_not_duplicates_created = \
                    ContestMeasuresAreNotDuplicates.objects.update_or_create(
                        contest_measure1_we_vote_id__exact=contest_measure1_we_vote_id,
                        contest_measure2_we_vote_id__iexact=contest_measure2_we_vote_id,
                        defaults=updated_values)
                success = True
                status += "CONTEST_MEASURES_ARE_NOT_DUPLICATES_UPDATED_OR_CREATED "
            except ContestMeasuresAreNotDuplicates.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_MEASURES_ARE_NOT_DUPLICATES_FOUND_BY_CONTEST_MEASURE_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'EXCEPTION_UPDATE_OR_CREATE_CONTEST_MEASURES_ARE_NOT_DUPLICATES ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success': success,
            'status': status,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'new_contest_measures_are_not_duplicates_created': new_contest_measures_are_not_duplicates_created,
            'contest_measures_are_not_duplicates': contest_measures_are_not_duplicates,
        }
        return results


class ContestMeasuresAreNotDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two contest measures as NOT duplicates
    """
    contest_measure1_we_vote_id = models.CharField(
        verbose_name="first contest measure we are tracking", max_length=255, null=True, unique=False)
    contest_measure2_we_vote_id = models.CharField(
        verbose_name="second contest measure we are tracking", max_length=255, null=True, unique=False)

    def fetch_other_office_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.contest_measure1_we_vote_id:
            return self.contest_measure2_we_vote_id
        elif one_we_vote_id == self.contest_measure2_we_vote_id:
            return self.contest_measure1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""
