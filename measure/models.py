# measure/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_we_vote_id_contest_measure_integer, \
    fetch_next_we_vote_id_measure_campaign_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


# The measure that is on the ballot (equivalent to ContestOffice)
class ContestMeasure(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "meas", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_measure_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)
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
    # A brief description of the referendum. This field is only populated for contests of type 'Referendum'.
    measure_subtitle = models.TextField(verbose_name="google civic referendum subtitle",
                                        null=True, blank=True, default="")
    # The text of the measure. This field is only populated for contests of type 'Referendum'.
    measure_text = models.TextField(verbose_name="measure text", null=True, blank=False)
    # A link to the referendum. This field is only populated for contests of type 'Referendum'.
    measure_url = models.CharField(verbose_name="measure details url", max_length=255, null=True, blank=False)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=255, null=True, blank=True)
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
    state_code = models.CharField(verbose_name="state this measure affects", max_length=2, null=True, blank=True)
    # Day of the election in YYYY-MM-DD format.
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', blank=True, null=True)

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
    ballotpedia_measure_url = models.URLField(verbose_name='ballotpedia url of measure', blank=True, null=True)
    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(verbose_name='url of ballotpedia logo', blank=True, null=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)

    def get_measure_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        # Pull this from ocdDivisionId
        ocd_division_id = self.ocd_division_id
        return extract_state_from_ocd_division_id(ocd_division_id)

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
    url = models.URLField(verbose_name='website url of campaign', blank=True, null=True)
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

    def retrieve_contest_measure_from_id(self, contest_measure_id):
        contest_measure_manager = ContestMeasureManager()
        return contest_measure_manager.retrieve_contest_measure(contest_measure_id)

    def retrieve_contest_measure_from_we_vote_id(self, contest_measure_we_vote_id):
        contest_measure_id = 0
        contest_measure_manager = ContestMeasureManager()
        return contest_measure_manager.retrieve_contest_measure(contest_measure_id, contest_measure_we_vote_id)

    def retrieve_contest_measure_from_maplight_id(self, maplight_id):
        contest_measure_id = 0
        contest_measure_we_vote_id = ''
        contest_measure_manager = ContestMeasureManager()
        return contest_measure_manager.retrieve_contest_measure(contest_measure_id, contest_measure_we_vote_id,
                                                                maplight_id)

    def fetch_contest_measure_id_from_maplight_id(self, maplight_id):
        contest_measure_id = 0
        contest_measure_we_vote_id = ''
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure(
            contest_measure_id, contest_measure_we_vote_id, maplight_id)
        if results['success']:
            return results['contest_measure_id']
        return 0

    def fetch_contest_measure_we_vote_id_from_id(self, contest_measure_id):
        contest_measure_we_vote_id = ''
        maplight_id = ''
        contest_measure_manager = ContestMeasureManager()
        results = contest_measure_manager.retrieve_contest_measure(
            contest_measure_id, contest_measure_we_vote_id, maplight_id)
        if results['success']:
            return results['contest_measure_we_vote_id']
        return 0

    def update_or_create_contest_measure(self, we_vote_id, google_civic_election_id, measure_title,
                                         district_id, district_name, state_code,
                                         updated_contest_measure_values):
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
        else:
            # If here, we are dealing with a measure that is new to We Vote
            if not (district_id or district_name):
                success = False
                status = 'MISSING_DISTRICT_ID-MEASURE_UPDATE_OR_CREATE'
                proceed_to_update_or_save = False
            elif not state_code:
                success = False
                status = 'MISSING_STATE_CODE-MEASURE_UPDATE_OR_CREATE'
                proceed_to_update_or_save = False
            elif not measure_title:
                success = False
                status = 'MISSING_MEASURE_TITLE-MEASURE_UPDATE_OR_CREATE'
                proceed_to_update_or_save = False

        if not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID-MEASURE_UPDATE_OR_CREATE'
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
                    status = 'MULTIPLE_MATCHING_CONTEST_MEASURES_FOUND'
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
                        for key, value in updated_contest_measure_values.items():
                            if hasattr(contest_measure_on_stage, key):
                                setattr(contest_measure_on_stage, key, value)
                        contest_measure_on_stage.save()
                        measure_updated = True
                        new_measure_created = False
                        success = True
                        status += "CONTEST_MEASURE_UPDATED "
                    except Exception as e:
                        status += 'FAILED_TO_UPDATE_CONTEST_MEASURE ' \
                                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                        success = False
                else:
                    # Create record
                    try:
                        contest_measure_on_stage = ContestMeasure.objects.create()
                        for key, value in updated_contest_measure_values.items():
                            if hasattr(contest_measure_on_stage, key):
                                setattr(contest_measure_on_stage, key, value)
                        contest_measure_on_stage.save()
                        measure_updated = False
                        new_measure_created = True
                        success = True
                        status += "CONTEST_MEASURE_CREATED "
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
    def retrieve_contest_measure(self, contest_measure_id, contest_measure_we_vote_id='', maplight_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        contest_measure_on_stage = ContestMeasure()

        try:
            if positive_value_exists(contest_measure_id):
                contest_measure_on_stage = ContestMeasure.objects.get(id=contest_measure_id)
                contest_measure_id = contest_measure_on_stage.id
                contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
                status = "RETRIEVE_MEASURE_FOUND_BY_ID"
            elif positive_value_exists(contest_measure_we_vote_id):
                contest_measure_on_stage = ContestMeasure.objects.get(we_vote_id=contest_measure_we_vote_id)
                contest_measure_id = contest_measure_on_stage.id
                contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
                status = "RETRIEVE_MEASURE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(maplight_id):
                contest_measure_on_stage = ContestMeasure.objects.get(maplight_id=maplight_id)
                contest_measure_id = contest_measure_on_stage.id
                contest_measure_we_vote_id = contest_measure_on_stage.we_vote_id
                status = "RETRIEVE_MEASURE_FOUND_BY_MAPLIGHT_ID"
            else:
                status = "RETRIEVE_MEASURE_SEARCH_INDEX_MISSING"
        except ContestMeasure.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_MEASURE_MULTIPLE_OBJECTS_RETURNED"
        except ContestMeasure.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_MEASURE_NOT_FOUND"

        results = {
            'success':                      True if convert_to_int(contest_measure_id) > 0 else False,
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
                state_code=state_code,ctcl_uuid=ctcl_uuid, google_civic_election_id=google_civic_election_id)
            if new_measure:
                success = True
                status = "CREATE_MEASURE_ROW_ENTRY-MEASURE_CREATED "
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
                if 'state_code' in defaults:
                    new_measure.state_code = defaults['state_code']
                new_measure.save()
            else:
                success = False
                status = "CREATE_MEASURE_ROW_ENTRY-MEASURE_CREATE_FAILED "
        except Exception as e:
            success = False
            new_measure_created = False
            status = "CREATE_MEASURE_ROW_ENTRY-MEASURE_CREATE_ERROR "
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
                if 'state_code' in defaults:
                    existing_measure_entry.state_code = defaults['state_code']
                # now go ahead and save this entry (update)
                existing_measure_entry.save()
                measure_updated = True
                success = True
                status = "UPDATE_MEASURE_ROW_ENTRY-MEASURE_UPDATED"
        except Exception as e:
            success = False
            measure_updated = False
            status = "UPDATE_MEASURE_ROW_ENTRY-MEASURE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':          success,
                'status':           status,
                'measure_updated':  measure_updated,
                'updated_measure':  existing_measure_entry,
            }
        return results


class ContestMeasureList(models.Model):
    """
    This is a class to make it easy to retrieve lists of Measures
    """

    def __unicode__(self):
        return "ContestMeasureList"

    def retrieve_measures(self, google_civic_election_id=0, ballotpedia_district_id=0, state_code="", limit=0):
        measure_list_objects = []
        measure_list_light = []
        measure_list_found = False

        try:
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

    def retrieve_all_measures_for_upcoming_election(self, google_civic_election_id=0, state_code='',
                                                    return_list_of_objects=False, limit=300):
        measure_list_objects = []
        measure_list_light = []
        measure_list_found = False

        try:
            measure_queryset = ContestMeasure.objects.all()
            if positive_value_exists(google_civic_election_id):
                measure_queryset = measure_queryset.filter(google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(state_code):
                measure_queryset = measure_queryset.filter(state_code__iexact=state_code)
            measure_queryset = measure_queryset.order_by("measure_title")
            # We never expect more than 300 measures for one election
            if positive_value_exists(limit):
                measure_list_objects = measure_queryset[:limit]

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
            status = 'FAILED retrieve_all_measures_for_upcoming_election ' \
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
            'measure_list_objects':     measure_list_objects if return_list_of_objects else [],
            'measure_list_light':       measure_list_light,
        }
        return results

    def retrieve_measures_from_non_unique_identifiers(self, google_civic_election_id, state_code,
                                                      contest_measure_title):
        keep_looking_for_duplicates = True
        measure = ContestMeasure()
        measure_found = False
        measure_list = []
        measure_list_found = False
        multiple_entries_found = False
        success = False
        status = ""

        if keep_looking_for_duplicates:
            # Search by Candidate name exact match
            try:
                measure_query = ContestMeasure.objects.all()
                measure_query = measure_query.filter(measure_title__iexact=contest_measure_title,
                                                     state_code__iexact=state_code,
                                                     google_civic_election_id=google_civic_election_id)

                measure_list = list(measure_query)
                if len(measure_list):
                    # entry exists
                    status += 'MEASURE_ENTRY_EXISTS '
                    success = True
                    # if a single entry matches, update that entry
                    if len(measure_list) == 1:
                        measure = measure_list[0]
                        measure_found = True
                        keep_looking_for_duplicates = False
                    else:
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                        # more than one entry found with a match in CandidateCampaign
            except ContestMeasure.DoesNotExist:
                status += "BATCH_ROW_ACTION_MEASURE_NOT_FOUND "

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'measure_found':            measure_found,
            'measure':                  measure,
            'measure_list_found':       measure_list_found,
            'measure_list':             measure_list,
            'multiple_entries_found':   multiple_entries_found,
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
            # We don't look for office_we_vote_id because of the chance that locally we are using a
            # different we_vote_id
            # measure_queryset = measure_queryset.filter(contest_office_we_vote_id__iexact=office_we_vote_id)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                measure_queryset = measure_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            # We want to find candidates with *any* of these values
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
            # No candidates found. Not a problem.
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
