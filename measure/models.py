# measure/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_we_vote_id_last_contest_measure_integer, \
    fetch_next_we_vote_id_last_measure_campaign_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.models import extract_state_from_ocd_division_id, positive_value_exists


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
                                   max_length=255, null=True, blank=True, unique=True)
    # The title of the measure (e.g. 'Proposition 42').
    measure_title = models.CharField(verbose_name="measure title", max_length=255, null=False, blank=False)
    # A brief description of the referendum. This field is only populated for contests of type 'Referendum'.
    measure_subtitle = models.CharField(verbose_name="google civic referendum subtitle",
                                        max_length=255, null=False, blank=False)
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

    def update_or_create_contest_measure(self, we_vote_id, google_civic_election_id, district_id, district_name,
                                         measure_title, state_code,
                                         update_contest_measure_values):  # , create_contest_measure_values
        """
        Either update or create an office entry.
        """
        exception_multiple_object_returned = False
        new_measure_created = False
        contest_measure_on_stage = ContestMeasure()

        if not google_civic_election_id:
            success = False
            status = 'MISSING_GOOGLE_CIVIC_ELECTION_ID'
        elif not (district_id or district_name):
            success = False
            status = 'MISSING_DISTRICT_ID'
        elif not state_code:
            success = False
            status = 'MISSING_STATE_CODE'
        elif not measure_title:
            success = False
            status = 'MISSING_MEASURE_TITLE'
        else:
            # We need to use one set of values when we are creating an entry, and another set of values when we
            #  are updating an entry
            try:
                # Use get_or_create with create_contest_measure_values. It will be more elegent and less prone
                #  to problems.

                # if a contest_measure_on_stage is found, *then* update it with update_contest_measure_values

                if positive_value_exists(we_vote_id):
                    contest_measure_on_stage, new_measure_created = ContestMeasure.objects.update_or_create(
                        google_civic_election_id__exact=google_civic_election_id,
                        we_vote_id__exact=we_vote_id,
                        defaults=update_contest_measure_values)
                else:
                    contest_measure_on_stage, new_measure_created = ContestMeasure.objects.update_or_create(
                        google_civic_election_id__exact=google_civic_election_id,
                        district_id__exact=district_id,
                        district_name__iexact=district_name,  # Case doesn't matter
                        measure_title__iexact=measure_title,  # Case doesn't matter
                        state_code__iexact=state_code,  # Case doesn't matter
                        defaults=update_contest_measure_values)
                success = True
                status = 'CONTEST_MEASURE_SAVED'
            except ContestMeasure.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_CONTEST_MEASURES_FOUND'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_measure_created':      new_measure_created,
            'contest_measure':          contest_measure_on_stage,
            'saved':                    new_measure_created,
            'updated':                  True if success and not new_measure_created else False,
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
            elif positive_value_exists(contest_measure_we_vote_id):
                contest_measure_on_stage = ContestMeasure.objects.get(we_vote_id=contest_measure_we_vote_id)
                contest_measure_id = contest_measure_on_stage.id
            elif positive_value_exists(maplight_id):
                contest_measure_on_stage = ContestMeasure.objects.get(maplight_id=maplight_id)
                contest_measure_id = contest_measure_on_stage.id
        except ContestMeasure.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
        except ContestMeasure.DoesNotExist:
            exception_does_not_exist = True

        results = {
            'success':                      True if contest_measure_id > 0 else False,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'contest_measure_found':         True if contest_measure_id > 0 else False,
            'contest_measure_id':            contest_measure_id,
            'contest_measure_we_vote_id':    contest_measure_we_vote_id,
            'contest_measure':               contest_measure_on_stage,
        }
        return results

    def fetch_contest_measure_id_from_contest_measure_we_vote_id(self, contest_measure_we_vote_id):
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
            # else:
            #     logger.warn("fetch_contest_measure_id_from_contest_measure_we_vote_id no contest_measure_we_vote_id")

        except ContestMeasure.MultipleObjectsReturned as e:
            # logger.warn("fetch_contest_measure_id_from_we_vote_id ContestMeasure.MultipleObjectsReturned")
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ContestMeasure.DoesNotExist:
            contest_measure_id = 0
            # logger.warn("fetch_contest_measure_id_from_contest_measure_we_vote_id ContestMeasure.DoesNotExist")

        return contest_measure_id


class ContestMeasureList(models.Model):
    """
    This is a class to make it easy to retrieve lists of Measures
    """

    def __unicode__(self):
        return "ContestMeasureList"

    def retrieve_all_measures_for_upcoming_election(self, google_civic_election_id=0,
                                                    return_list_of_objects=False):
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
            measure_list_objects = measure_queryset

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
                    'ballot_item_label':    measure.measure_title,
                    'measure_we_vote_id':   measure.we_vote_id,
                    'office_we_vote_id':    '',
                    'candidate_we_vote_id': '',
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
