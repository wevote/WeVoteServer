# candidate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from election.models import Election
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from office.models import ContestOffice, ContestOfficeManager
import re
from wevote_settings.models import fetch_next_we_vote_id_candidate_campaign_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, display_full_name_with_correct_capitalization, \
    extract_title_from_full_name, extract_first_name_from_full_name, extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_suffix_from_full_name, extract_nickname_from_full_name, \
    extract_state_from_ocd_division_id, extract_twitter_handle_from_text_string, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


class CandidateCampaignListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Candidates
    """

    def retrieve_all_candidates_for_office(self, office_id, office_we_vote_id):
        candidate_list = []
        candidate_list_found = False

        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
            results = {
                'success':              True if candidate_list_found else False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'candidate_list_found': candidate_list_found,
                'candidate_list':       candidate_list,
            }
            return results

        try:
            candidate_queryset = CandidateCampaign.objects.all()
            if positive_value_exists(office_id):
                candidate_queryset = candidate_queryset.filter(contest_office_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                candidate_queryset = candidate_queryset.filter(contest_office_we_vote_id=office_we_vote_id)
            candidate_queryset = candidate_queryset.order_by('-twitter_followers_count')
            candidate_list = candidate_queryset

            if len(candidate_list):
                candidate_list_found = True
                status = 'CANDIDATES_RETRIEVED'
            else:
                status = 'NO_CANDIDATES_RETRIEVED'
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status = 'NO_CANDIDATES_FOUND_DoesNotExist'
            candidate_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_candidates_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':              True if candidate_list_found else False,
            'status':               status,
            'office_id':            office_id,
            'office_we_vote_id':    office_we_vote_id,
            'candidate_list_found': candidate_list_found,
            'candidate_list':       candidate_list,
        }
        return results

    def retrieve_all_candidates_for_upcoming_election(self, google_civic_election_id=0, state_code='',
                                                      return_list_of_objects=False):
        candidate_list_objects = []
        candidate_list_light = []
        candidate_list_found = False

        try:
            candidate_queryset = CandidateCampaign.objects.all()
            if positive_value_exists(google_civic_election_id):
                candidate_queryset = candidate_queryset.filter(google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(state_code):
                candidate_queryset = candidate_queryset.filter(state_code__iexact=state_code)
            candidate_queryset = candidate_queryset.order_by("candidate_name")
            if positive_value_exists(google_civic_election_id):
                candidate_list_objects = candidate_queryset
            else:
                candidate_list_objects = candidate_queryset[:300]

            if len(candidate_list_objects):
                candidate_list_found = True
                status = 'CANDIDATES_RETRIEVED'
                success = True
            else:
                status = 'NO_CANDIDATES_RETRIEVED'
                success = True
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status = 'NO_CANDIDATES_FOUND_DoesNotExist'
            candidate_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_candidates_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        if candidate_list_found:
            for candidate in candidate_list_objects:
                one_candidate = {
                    'ballot_item_display_name': candidate.display_candidate_name(),
                    'candidate_we_vote_id':     candidate.we_vote_id,
                    'office_we_vote_id':        candidate.contest_office_we_vote_id,
                    'measure_we_vote_id':       '',
                }
                candidate_list_light.append(one_candidate.copy())

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'candidate_list_found':     candidate_list_found,
            'candidate_list_objects':   candidate_list_objects if return_list_of_objects else [],
            'candidate_list_light':     candidate_list_light,
        }
        return results

    def retrieve_candidate_count_for_office(self, office_id, office_we_vote_id):
        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
            results = {
                'success':              False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'candidate_count':      0,
            }
            return results

        try:
            candidate_queryset = CandidateCampaign.objects.all()
            if positive_value_exists(office_id):
                candidate_queryset = candidate_queryset.filter(contest_office_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                candidate_queryset = candidate_queryset.filter(contest_office_we_vote_id=office_we_vote_id)
            candidate_list = candidate_queryset

            candidate_count = candidate_list.count()
            success = True
            status = "CANDIDATE_COUNT_FOUND"
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status = 'NO_CANDIDATES_FOUND_DoesNotExist'
            candidate_count = 0
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_candidates_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False
            candidate_count = 0

        results = {
            'success':              success,
            'status':               status,
            'office_id':            office_id,
            'office_we_vote_id':    office_we_vote_id,
            'candidate_count':      candidate_count,
        }
        return results

    def is_automatic_merge_ok(self, candidate_option1, candidate_option2):
        automatic_merge_ok = True
        status = ""
        if candidate_option1.candidate_name != candidate_option2.candidate_name:
            automatic_merge_ok = False
            status += " candidate_name:"
        candidate1_twitter_handle = str(candidate_option1.candidate_twitter_handle)
        candidate2_twitter_handle = str(candidate_option2.candidate_twitter_handle)
        if candidate1_twitter_handle.lower() != candidate2_twitter_handle.lower():
            automatic_merge_ok = False
            status += " candidate_twitter_handle:"
        if candidate_option1.candidate_url != candidate_option2.candidate_url:
            automatic_merge_ok = False
            status += " candidate_url:"

        if not automatic_merge_ok:
            status = "Different: " + status

        results = {
            "status":               status,
            "automatic_merge_ok":   automatic_merge_ok,
        }
        return results

    def do_automatic_merge(self, candidate_option1, candidate_option2):
        success = False
        status = "do_automatic_merge NOT IMPLEMENTED YET"

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def find_and_remove_duplicate_candidates(self, google_civic_election_id, merge=False, remove=False):
        success = False
        status = "find_and_remove_duplicate_candidates NOT IMPLEMENTED YET"

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
        }
        return results

    def retrieve_candidate_campaigns_from_all_elections_list(self):
        """
        This is used by the admin tools to show CandidateCampaigns in a drop-down for example
        """
        candidates_list_temp = CandidateCampaign.objects.all()
        # Order by candidate_name.
        # To order by last name we will need to make some guesses in some case about what the last name is.
        candidates_list_temp = candidates_list_temp.order_by('candidate_name')[:300]
        return candidates_list_temp

    def remove_duplicate_candidate(self, candidate_id, google_civic_election_id):
        # TODO DALE We need to delete the positions associated with this candidate, and convert them to belong
        # to candidate we leave in place.

        success = False
        status = "COULD_NOT_DELETE_DUPLICATE_CANDIDATE"

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def retrieve_possible_duplicate_candidates(self, candidate_name, google_civic_candidate_name,
                                               google_civic_election_id, office_we_vote_id,
                                               politician_we_vote_id,
                                               candidate_twitter_handle, vote_smart_id, maplight_id,
                                               we_vote_id_from_master=''):
        candidate_list_objects = []
        filters = []
        candidate_list_found = False

        try:
            candidate_queryset = CandidateCampaign.objects.all()
            candidate_queryset = candidate_queryset.filter(google_civic_election_id=google_civic_election_id)
            # We don't look for office_we_vote_id because of the chance that locally we are using a
            # different we_vote_id
            # candidate_queryset = candidate_queryset.filter(contest_office_we_vote_id__iexact=office_we_vote_id)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                candidate_queryset = candidate_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            # We want to find candidates with *any* of these values
            if positive_value_exists(google_civic_candidate_name):
                # We intentionally use case sensitive matching here
                new_filter = Q(google_civic_candidate_name__exact=google_civic_candidate_name)
                filters.append(new_filter)
            elif positive_value_exists(candidate_name):
                new_filter = Q(candidate_name__iexact=candidate_name)
                filters.append(new_filter)

            if positive_value_exists(politician_we_vote_id):
                new_filter = Q(politician_we_vote_id__iexact=politician_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(candidate_twitter_handle):
                new_filter = Q(candidate_twitter_handle__iexact=candidate_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(vote_smart_id):
                new_filter = Q(vote_smart_id=vote_smart_id)
                filters.append(new_filter)

            if positive_value_exists(maplight_id):
                new_filter = Q(maplight_id=maplight_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                candidate_queryset = candidate_queryset.filter(final_filters)

            candidate_list_objects = candidate_queryset

            if len(candidate_list_objects):
                candidate_list_found = True
                status = 'DUPLICATE_CANDIDATES_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_CANDIDATES_RETRIEVED'
                success = True
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status = 'NO_DUPLICATE_CANDIDATES_FOUND_DoesNotExist'
            candidate_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_candidates ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'candidate_list_found':     candidate_list_found,
            'candidate_list':           candidate_list_objects,
        }
        return results

    def retrieve_candidates_from_non_unique_identifiers(self, google_civic_election_id, state_code,
                                                        candidate_twitter_handle, candidate_name):
        keep_looking_for_duplicates = True
        candidate = CandidateCampaign()
        candidate_found = False
        candidate_list_objects = []
        candidate_list_found = False
        multiple_entries_found = False
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
        success = False
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(candidate_twitter_handle):
            try:
                candidate_query = CandidateCampaign.objects.all()
                candidate_query = candidate_query.filter(candidate_twitter_handle__iexact=candidate_twitter_handle,
                                                         google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)

                candidate_list = list(candidate_query)
                if len(candidate_list):
                    # At least one entry exists
                    status += 'BATCH_ROW_ACTION_CANDIDATE_LIST_RETRIEVED '
                    # if a single entry matches, update that entry
                    if len(candidate_list) == 1:
                        multiple_entries_found = False
                        candidate = candidate_list[0]
                        candidate_found = True
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found
                        multiple_entries_found = True
                        keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
            except CandidateCampaign.DoesNotExist:
                # success = True
                status += "BATCH_ROW_ACTION_EXISTING_CANDIDATE_NOT_FOUND "
            except Exception as e:
                keep_looking_for_duplicates = False
                pass
        # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(candidate_name):
            # Search by Candidate name exact match
            try:
                candidate_query = CandidateCampaign.objects.all()
                candidate_query = candidate_query.filter(candidate_name__iexact=candidate_name,
                                                         google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)

                candidate_list = list(candidate_query)
                if len(candidate_list):
                    # entry exists
                    status += 'CANDIDATE_ENTRY_EXISTS '
                    success = True
                    # if a single entry matches, update that entry
                    if len(candidate_list) == 1:
                        candidate = candidate_list[0]
                        candidate_found = True
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in CandidateCampaign
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
            except CandidateCampaign.DoesNotExist:
                status += "BATCH_ROW_ACTION_CANDIDATE_NOT_FOUND "

        if keep_looking_for_duplicates and positive_value_exists(candidate_name):
            # Search for Candidate(s) that contains the same first and last names
            try:
                candidate_query = CandidateCampaign.objects.all()
                candidate_query = candidate_query.filter(google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(candidate_name)
                candidate_query = candidate_query.filter(candidate_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(candidate_name)
                candidate_query = candidate_query.filter(candidate_name__icontains=last_name)

                candidate_list = list(candidate_query)
                if len(candidate_list):
                    # entry exists
                    status += 'CANDIDATE_ENTRY_EXISTS '
                    success = True
                    # if a single entry matches, update that entry
                    if len(candidate_list) == 1:
                        candidate = candidate_list[0]
                        candidate_found = True
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in CandidateCampaign
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    success = True
            except CandidateCampaign.DoesNotExist:
                status += "BATCH_ROW_ACTION_CANDIDATE_NOT_FOUND "
                success = True

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'candidate_found':          candidate_found,
            'candidate':                candidate,
            'candidate_list_found':     candidate_list_found,
            'candidate_list':           candidate_list_objects,
            'multiple_entries_found':   multiple_entries_found,
        }
        return results


class CandidateCampaign(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "cand", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_candidate_campaign_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this candidate campaign", max_length=255, default=None, null=True,
        blank=True, unique=True)
    maplight_id = models.CharField(
        verbose_name="maplight candidate id", max_length=255, default=None, null=True, blank=True, unique=True)
    vote_smart_id = models.CharField(
        verbose_name="vote smart candidate id", max_length=15, default=None, null=True, blank=True, unique=False)
    # The internal We Vote id for the ContestOffice that this candidate is competing for. During setup we need to allow
    # this to be null.
    contest_office_id = models.CharField(
        verbose_name="contest_office_id id", max_length=255, null=True, blank=True)
    # We want to link the candidate to the contest with permanent ids so we can export and import
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the office this candidate is running for", max_length=255, default=None,
        null=True, blank=True, unique=False)
    contest_office_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)
    # politician (internal) link to local We Vote Politician entry. During setup we need to allow this to be null.
    politician_id = models.BigIntegerField(verbose_name="politician unique identifier", null=True, blank=True)
    # The persistent We Vote unique ID of the Politician, so we can export and import into other databases.
    politician_we_vote_id = models.CharField(
        verbose_name="we vote politician id", max_length=255, null=True, blank=True)
    # The candidate's name.
    candidate_name = models.CharField(verbose_name="candidate name", max_length=255, null=False, blank=False)
    # The candidate's name as passed over by Google Civic. We save this so we can match to this candidate even
    # if we edit the candidate's name locally.
    google_civic_candidate_name = models.CharField(verbose_name="candidate name exactly as received from google civic",
                                                   max_length=255, null=False, blank=False)
    # The full name of the party the candidate is a member of.
    party = models.CharField(verbose_name="party", max_length=255, null=True, blank=True)
    # A URL for a photo of the candidate.
    photo_url = models.CharField(verbose_name="photoUrl", max_length=255, null=True, blank=True)
    photo_url_from_maplight = models.URLField(
        verbose_name='candidate portrait url of candidate from maplight', blank=True, null=True)
    photo_url_from_vote_smart = models.URLField(
        verbose_name='candidate portrait url of candidate from vote smart', blank=True, null=True)
    # The order the candidate appears on the ballot relative to other candidates for this contest.
    order_on_ballot = models.CharField(verbose_name="order on ballot", max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=255, null=True, blank=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="state this candidate serves", max_length=2, null=True, blank=True)
    # The URL for the candidate's campaign web site.
    candidate_url = models.URLField(verbose_name='website url of candidate campaign', blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of candidate campaign', blank=True, null=True)

    twitter_url = models.URLField(verbose_name='twitter url of candidate campaign', blank=True, null=True)
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    candidate_twitter_handle = models.CharField(
        verbose_name='candidate twitter screen_name', max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="candidate plain text name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="candidate location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of logo from twitter', blank=True, null=True)
    twitter_profile_background_image_url_https = models.URLField(verbose_name='tile-able background from twitter',
                                                                 blank=True, null=True)
    twitter_profile_banner_url_https = models.URLField(verbose_name='profile banner image from twitter',
                                                       blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)
    we_vote_hosted_profile_image_url_large = models.URLField(verbose_name='we vote hosted large image url',
                                                             blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.URLField(verbose_name='we vote hosted medium image url',
                                                              blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.URLField(verbose_name='we vote hosted tiny image url',
                                                            blank=True, null=True)

    google_plus_url = models.URLField(verbose_name='google plus url of candidate campaign', blank=True, null=True)
    youtube_url = models.URLField(verbose_name='youtube url of candidate campaign', blank=True, null=True)
    # The email address for the candidate's campaign.
    candidate_email = models.CharField(verbose_name="candidate campaign email", max_length=255, null=True, blank=True)
    # The voice phone number for the candidate's campaign office.
    candidate_phone = models.CharField(verbose_name="candidate campaign phone", max_length=255, null=True, blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', blank=True, null=True)

    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(verbose_name='url of ballotpedia logo', blank=True, null=True)

    # Official Statement from Candidate in Ballot Guide
    ballot_guide_official_statement = models.TextField(verbose_name="official candidate statement from ballot guide",
                                                       null=True, blank=True, default="")
    # CTCL candidate data fields
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    candidate_is_top_ticket = models.BooleanField(verbose_name="candidate is top ticket", default=False)
    candidate_is_incumbent = models.BooleanField(verbose_name="candidate is the current incumbent", default=False)

    def election(self):
        try:
            election = Election.objects.get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("candidate.election Found multiple")
            return
        except Election.DoesNotExist:
            logger.error("candidate.election did not find")
            return
        return election

    def office(self):
        try:
            office = ContestOffice.objects.get(id=self.contest_office_id)
        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("candidate.election Found multiple")
            return
        except ContestOffice.DoesNotExist:
            logger.error("candidate.election did not find")
            return
        return office

    def candidate_photo_url(self):
        if self.photo_url_from_vote_smart:
            return self.photo_url_from_vote_smart_large()
        if self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https_original()
        if self.photo_url_from_maplight:
            return self.photo_url_from_maplight
        if self.photo_url:
            return self.photo_url
        else:
            return ""
            # "http://votersedge.org/sites/all/modules/map/modules/map_proposition/images/politicians/2662.jpg"
        # else:
        #     politician_manager = PoliticianManager()
        #     return politician_manager.politician_photo_url(self.politician_id)

    def photo_url_from_vote_smart_large(self):
        if positive_value_exists(self.photo_url_from_vote_smart):
            # Use regex to replace '.jpg' with '_lg.jpg'
            # Vote smart returns the link to the small photo, but we want to use the large photo
            photo_url_from_vote_smart_large = re.sub(r'.jpg', r'_lg.jpg', self.photo_url_from_vote_smart)
            return photo_url_from_vote_smart_large
        else:
            return ""

    def fetch_twitter_handle(self):
        if positive_value_exists(self.candidate_twitter_handle):
            return self.candidate_twitter_handle
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
        if self.candidate_twitter_handle:
            return "https://twitter.com/{twitter_handle}".format(twitter_handle=self.candidate_twitter_handle)
        else:
            return ''

    def get_candidate_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            # Pull this from ocdDivisionId
            if positive_value_exists(self.ocd_division_id):
                ocd_division_id = self.ocd_division_id
                return extract_state_from_ocd_division_id(ocd_division_id)
            else:
                return ''

    def display_candidate_name(self):
        full_name = self.candidate_name
        if full_name.isupper():
            full_name_corrected_capitalization = display_full_name_with_correct_capitalization(full_name)
            return full_name_corrected_capitalization
        return full_name

    def extract_title(self):
        full_name = self.display_candidate_name()
        return extract_title_from_full_name(full_name)

    def extract_first_name(self):
        full_name = self.display_candidate_name()
        return extract_first_name_from_full_name(full_name)

    def extract_middle_name(self):
        full_name = self.display_candidate_name()
        return extract_middle_name_from_full_name(full_name)

    def extract_last_name(self):
        full_name = self.display_candidate_name()
        return extract_last_name_from_full_name(full_name)

    def extract_suffix(self):
        full_name = self.display_candidate_name()
        return extract_suffix_from_full_name(full_name)

    def extract_nickname(self):
        full_name = self.display_candidate_name()
        return extract_nickname_from_full_name(full_name)

    def political_party_display(self):
        return candidate_party_display(self.party)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_candidate_campaign_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "cand" = tells us this is a unique id for a CandidateCampaign
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}cand{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        if self.maplight_id == "":  # We want this to be unique IF there is a value, and otherwise "None"
            self.maplight_id = None
        super(CandidateCampaign, self).save(*args, **kwargs)


def fetch_candidate_count_for_office(office_id=0, office_we_vote_id=''):
    candidate_campaign_list = CandidateCampaignListManager()
    results = candidate_campaign_list.retrieve_candidate_count_for_office(office_id, office_we_vote_id)
    return results['candidate_count']


# See also 'convert_to_political_party_constant' in we_vote_functions/functions.py
def candidate_party_display(raw_party):
    if raw_party is None:
        return ''
    if raw_party == '':
        return ''
    if raw_party == 'Amer. Ind.':
        return 'American Independent'
    if raw_party == 'DEM':
        return 'Democrat'
    if raw_party == 'Democratic':
        return 'Democrat'
    if raw_party == 'Party Preference: Democratic':
        return 'Democrat'
    if raw_party == 'GRN':
        return 'Green'
    if raw_party == 'LIB':
        return 'Libertarian'
    if raw_party == 'NPP':
        return 'No Party Preference'
    if raw_party == 'Party Preference: None':
        return 'No Party Preference'
    if raw_party == 'PF':
        return 'Peace and Freedom'
    if raw_party == 'REP':
        return 'Republican'
    if raw_party == 'Party Preference: Republican':
        return 'Republican'
    if raw_party.lower() == 'none':
        return ''
    else:
        return raw_party


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


class CandidateCampaignManager(models.Model):

    def __unicode__(self):
        return "CandidateCampaignManager"

    def retrieve_candidate_campaign_from_id(self, candidate_campaign_id):
        candidate_campaign_manager = CandidateCampaignManager()
        return candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id)

    def retrieve_candidate_campaign_from_we_vote_id(self, we_vote_id):
        candidate_campaign_id = 0
        candidate_campaign_manager = CandidateCampaignManager()
        return candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id, we_vote_id)

    def fetch_candidate_campaign_id_from_we_vote_id(self, we_vote_id):
        candidate_campaign_id = 0
        candidate_campaign_manager = CandidateCampaignManager()
        results = candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id, we_vote_id)
        if results['success']:
            return results['candidate_campaign_id']
        return 0

    def fetch_candidate_campaign_we_vote_id_from_id(self, candidate_campaign_id):
        we_vote_id = ''
        candidate_campaign_manager = CandidateCampaignManager()
        results = candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id, we_vote_id)
        if results['success']:
            return results['candidate_campaign_we_vote_id']
        return ''

    def fetch_google_civic_candidate_name_from_we_vote_id(self, we_vote_id):
        candidate_campaign_id = 0
        candidate_campaign_manager = CandidateCampaignManager()
        results = candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id, we_vote_id)
        if results['success']:
            candidate_campaign = results['candidate_campaign']
            return candidate_campaign.google_civic_candidate_name
        return 0

    def retrieve_candidate_campaign_from_maplight_id(self, candidate_maplight_id):
        candidate_campaign_id = 0
        we_vote_id = ''
        candidate_campaign_manager = CandidateCampaignManager()
        return candidate_campaign_manager.retrieve_candidate_campaign(
            candidate_campaign_id, we_vote_id, candidate_maplight_id)

    def retrieve_candidate_campaign_from_vote_smart_id(self, candidate_vote_smart_id):
        candidate_campaign_id = 0
        we_vote_id = ''
        candidate_maplight_id = ''
        candidate_name = ''
        candidate_campaign_manager = CandidateCampaignManager()
        return candidate_campaign_manager.retrieve_candidate_campaign(
            candidate_campaign_id, we_vote_id, candidate_maplight_id, candidate_name, candidate_vote_smart_id)

    def retrieve_candidate_campaign_from_candidate_name(self, candidate_name):
        candidate_campaign_id = 0
        we_vote_id = ''
        candidate_maplight_id = ''
        candidate_campaign_manager = CandidateCampaignManager()

        results = candidate_campaign_manager.retrieve_candidate_campaign(
            candidate_campaign_id, we_vote_id, candidate_maplight_id, candidate_name)
        if results['success']:
            return results

        # Try to modify the candidate name, and search again
        # MapLight for example will pass in "Ronald  Gold" for example
        candidate_name_try2 = candidate_name.replace('  ', ' ')
        results = candidate_campaign_manager.retrieve_candidate_campaign(
            candidate_campaign_id, we_vote_id, candidate_maplight_id, candidate_name_try2)
        if results['success']:
            return results

        # MapLight also passes in "Kamela D Harris" for example, and Google Civic uses "Kamela D. Harris"
        candidate_name_try3 = mimic_google_civic_initials(candidate_name)
        if candidate_name_try3 != candidate_name:
            results = candidate_campaign_manager.retrieve_candidate_campaign(
                candidate_campaign_id, we_vote_id, candidate_maplight_id, candidate_name_try3)
            if results['success']:
                return results

        # Otherwise return failed results
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_candidate_campaign(
            self, candidate_campaign_id, candidate_campaign_we_vote_id=None, candidate_maplight_id=None,
            candidate_name=None, candidate_vote_smart_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        candidate_campaign_on_stage = CandidateCampaign()

        try:
            if positive_value_exists(candidate_campaign_id):
                candidate_campaign_on_stage = CandidateCampaign.objects.get(id=candidate_campaign_id)
                candidate_campaign_id = candidate_campaign_on_stage.id
                candidate_campaign_we_vote_id = candidate_campaign_on_stage.we_vote_id
                candidate_campaign_found = True
                status = "RETRIEVE_CANDIDATE_FOUND_BY_ID"
            elif positive_value_exists(candidate_campaign_we_vote_id):
                candidate_campaign_on_stage = CandidateCampaign.objects.get(we_vote_id=candidate_campaign_we_vote_id)
                candidate_campaign_id = candidate_campaign_on_stage.id
                candidate_campaign_we_vote_id = candidate_campaign_on_stage.we_vote_id
                candidate_campaign_found = True
                status = "RETRIEVE_CANDIDATE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(candidate_maplight_id):
                candidate_campaign_on_stage = CandidateCampaign.objects.get(maplight_id=candidate_maplight_id)
                candidate_campaign_id = candidate_campaign_on_stage.id
                candidate_campaign_we_vote_id = candidate_campaign_on_stage.we_vote_id
                candidate_campaign_found = True
                status = "RETRIEVE_CANDIDATE_FOUND_BY_MAPLIGHT_ID"
            elif positive_value_exists(candidate_vote_smart_id):
                candidate_campaign_on_stage = CandidateCampaign.objects.get(vote_smart_id=candidate_vote_smart_id)
                candidate_campaign_id = candidate_campaign_on_stage.id
                candidate_campaign_we_vote_id = candidate_campaign_on_stage.we_vote_id
                candidate_campaign_found = True
                status = "RETRIEVE_CANDIDATE_FOUND_BY_VOTE_SMART_ID"
            elif positive_value_exists(candidate_name):
                candidate_campaign_on_stage = CandidateCampaign.objects.get(candidate_name=candidate_name)
                candidate_campaign_id = candidate_campaign_on_stage.id
                candidate_campaign_we_vote_id = candidate_campaign_on_stage.we_vote_id
                candidate_campaign_found = True
                status = "RETRIEVE_CANDIDATE_FOUND_BY_NAME"
            else:
                candidate_campaign_found = False
                status = "RETRIEVE_CANDIDATE_SEARCH_INDEX_MISSING"
        except CandidateCampaign.MultipleObjectsReturned as e:
            candidate_campaign_found = False
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_CANDIDATE_MULTIPLE_OBJECTS_RETURNED"
        except CandidateCampaign.DoesNotExist:
            candidate_campaign_found = False
            exception_does_not_exist = True
            status = "RETRIEVE_CANDIDATE_NOT_FOUND"
        except Exception as e:
            candidate_campaign_found = False
            status = "RETRIEVE_CANDIDATE_NOT_FOUND_EXCEPTION"

        results = {
            'success':                  True if convert_to_int(candidate_campaign_id) > 0 else False,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'candidate_campaign_found': candidate_campaign_found,
            'candidate_campaign_id':    convert_to_int(candidate_campaign_id),
            'candidate_campaign_we_vote_id':    candidate_campaign_we_vote_id,
            'candidate_campaign':       candidate_campaign_on_stage,
        }
        return results

    def update_or_create_candidate_campaign(self, candidate_we_vote_id, google_civic_election_id, ocd_division_id,
                                            contest_office_id, contest_office_we_vote_id, google_civic_candidate_name,
                                            updated_candidate_campaign_values):
        """
        Either update or create a candidate_campaign entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_candidate_created = False
        candidate_campaign_on_stage = CandidateCampaign()
        status = ""

        if not positive_value_exists(google_civic_election_id):
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID '
        # We are avoiding requiring ocd_division_id
        # elif not positive_value_exists(ocd_division_id):
        #     success = False
        #     status = 'MISSING_OCD_DIVISION_ID'
        # DALE 2016-02-20 We are not requiring contest_office_id or contest_office_we_vote_id to match a candidate
        # elif not positive_value_exists(contest_office_we_vote_id): # and not positive_value_exists(contest_office_id):
        #     success = False
        #     status = 'MISSING_CONTEST_OFFICE_ID'
        elif not positive_value_exists(google_civic_candidate_name):
            success = False
            status += 'MISSING_GOOGLE_CIVIC_CANDIDATE_NAME '
        elif positive_value_exists(candidate_we_vote_id) and positive_value_exists(contest_office_we_vote_id):
            try:
                # If here we are using permanent public identifier contest_office_we_vote_id
                candidate_campaign_on_stage, new_candidate_created = \
                    CandidateCampaign.objects.update_or_create(
                        google_civic_election_id__exact=google_civic_election_id,
                        we_vote_id__iexact=candidate_we_vote_id,
                        contest_office_we_vote_id__iexact=contest_office_we_vote_id,
                        defaults=updated_candidate_campaign_values)
                success = True
                status += "CANDIDATE_CAMPAIGN_UPDATED_OR_CREATED "
            except CandidateCampaign.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CANDIDATE_CAMPAIGNS_FOUND_BY_CANDIDATE_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False  # If coming (most likely) from a Google Civic import, or internal bulk update
        else:
            # Given we might have the office listed by google_civic_office_name
            # OR office_name, we need to check both before we try to create a new entry
            candidate_found = False
            try:
                candidate_campaign_on_stage = CandidateCampaign.objects.get(
                    google_civic_election_id__exact=google_civic_election_id,
                    google_civic_candidate_name__iexact=google_civic_candidate_name
                )
                candidate_found = True
                success = True
                status += 'CONTEST_OFFICE_SAVED '
            except CandidateCampaign.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_GOOGLE_CIVIC_OFFICE_NAME '
                exception_multiple_object_returned = True
            except CandidateCampaign.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND_BY_GOOGLE_CIVIC_CANDIDATE_NAME "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

            if not candidate_found and not exception_multiple_object_returned:
                # Try to find record based on office_name (instead of google_civic_office_name)
                try:
                    candidate_campaign_on_stage = CandidateCampaign.objects.get(
                        google_civic_election_id__exact=google_civic_election_id,
                        candidate_name__iexact=google_civic_candidate_name
                    )
                    candidate_found = True
                    success = True
                    status += 'CANDIDATE_RETRIEVED_FROM_CANDIDATE_NAME '
                except CandidateCampaign.MultipleObjectsReturned as e:
                    success = False
                    status += 'MULTIPLE_MATCHING_CANDIDATES_FOUND_BY_CANDIDATE_NAME '
                    exception_multiple_object_returned = True
                except CandidateCampaign.DoesNotExist:
                    exception_does_not_exist = True
                    status += "RETRIEVE_CANDIDATE_NOT_FOUND_BY_CANDIDATE_NAME "
                except Exception as e:
                    status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

            if exception_multiple_object_returned:
                # We can't proceed because there is an error with the data
                success = False
            elif candidate_found:
                # Update record
                # Note: When we decide to start updating candidate_name elsewhere within We Vote, we should stop
                #  updating candidate_name via subsequent Google Civic imports
                try:
                    for key, value in updated_candidate_campaign_values.items():
                        if hasattr(candidate_campaign_on_stage, key):
                            setattr(candidate_campaign_on_stage, key, value)
                    candidate_campaign_on_stage.save()
                    new_candidate_created = False
                    success = True
                    status += "CANDIDATE_UPDATED "
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_CANDIDATE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    candidate_campaign_on_stage = CandidateCampaign.objects.create()
                    for key, value in updated_candidate_campaign_values.items():
                        if hasattr(candidate_campaign_on_stage, key):
                            setattr(candidate_campaign_on_stage, key, value)
                    candidate_campaign_on_stage.save()
                    new_candidate_created = True
                    success = True
                    status += "CANDIDATE_CREATED "
                except Exception as e:
                    status += 'FAILED_TO_CREATE_CANDIDATE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

        results = {
            'success':                          success,
            'status':                           status,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'new_candidate_created':            new_candidate_created,
            'candidate_campaign':               candidate_campaign_on_stage,
        }
        return results

    def update_candidate_social_media(self, candidate, candidate_twitter_handle=False, candidate_facebook=False):
        """
        Update a candidate entry with general social media data. If a value is passed in False
        it means "Do not update"
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        success = False
        status = "ENTERING_UPDATE_CANDIDATE_SOCIAL_MEDIA"
        values_changed = False

        candidate_twitter_handle = candidate_twitter_handle.strip() if candidate_twitter_handle else False
        candidate_facebook = candidate_facebook.strip() if candidate_facebook else False
        # candidate_image = candidate_image.strip() if candidate_image else False

        if candidate:
            if candidate_twitter_handle:
                if candidate_twitter_handle != candidate.candidate_twitter_handle:
                    candidate.candidate_twitter_handle = candidate_twitter_handle
                    values_changed = True
            if candidate_facebook:
                if candidate_facebook != candidate.facebook_url:
                    candidate.facebook_url = candidate_facebook
                    values_changed = True

            if values_changed:
                candidate.save()
                success = True
                status = "SAVED_CANDIDATE_SOCIAL_MEDIA"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_CANDIDATE_SOCIAL_MEDIA"

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'candidate':                candidate,
        }
        return results

    def update_candidate_twitter_details(self, candidate, twitter_json, cached_twitter_profile_image_url_https,
                                         cached_twitter_profile_background_image_url_https,
                                         cached_twitter_profile_banner_url_https,
                                         we_vote_hosted_profile_image_url_large,
                                         we_vote_hosted_profile_image_url_medium,
                                         we_vote_hosted_profile_image_url_tiny):
        """
        Update a candidate entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_CANDIDATE_TWITTER_DETAILS"
        values_changed = False

        if candidate:
            if 'id' in twitter_json and positive_value_exists(twitter_json['id']):
                if convert_to_int(twitter_json['id']) != candidate.twitter_user_id:
                    candidate.twitter_user_id = convert_to_int(twitter_json['id'])
                    values_changed = True
            if 'screen_name' in twitter_json and positive_value_exists(twitter_json['screen_name']):
                if twitter_json['screen_name'] != candidate.candidate_twitter_handle:
                    candidate.candidate_twitter_handle = twitter_json['screen_name']
                    values_changed = True
            if 'name' in twitter_json and positive_value_exists(twitter_json['name']):
                if twitter_json['name'] != candidate.twitter_name:
                    candidate.twitter_name = twitter_json['name']
                    values_changed = True
            if 'followers_count' in twitter_json and positive_value_exists(twitter_json['followers_count']):
                if convert_to_int(twitter_json['followers_count']) != candidate.twitter_followers_count:
                    candidate.twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                candidate.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_image_url_https']):
                if twitter_json['profile_image_url_https'] != candidate.twitter_profile_image_url_https:
                    candidate.twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                candidate.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            elif ('profile_banner_url' in twitter_json) and positive_value_exists(twitter_json['profile_banner_url']):
                if twitter_json['profile_banner_url'] != candidate.twitter_profile_banner_url_https:
                    candidate.twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                candidate.twitter_profile_background_image_url_https = cached_twitter_profile_background_image_url_https
                values_changed = True
            elif 'profile_background_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_background_image_url_https']):
                if twitter_json['profile_background_image_url_https'] != \
                        candidate.twitter_profile_background_image_url_https:
                    candidate.twitter_profile_background_image_url_https = \
                        twitter_json['profile_background_image_url_https']
                    values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                candidate.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                candidate.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                candidate.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_json and positive_value_exists(twitter_json['description']):
                if twitter_json['description'] != candidate.twitter_description:
                    candidate.twitter_description = twitter_json['description']
                    values_changed = True
            if 'location' in twitter_json and positive_value_exists(twitter_json['location']):
                if twitter_json['location'] != candidate.twitter_location:
                    candidate.twitter_location = twitter_json['location']
                    values_changed = True

            if values_changed:
                candidate.save()
                success = True
                status = "SAVED_CANDIDATE_TWITTER_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_CANDIDATE_TWITTER_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'candidate':    candidate,
        }
        return results

    def reset_candidate_image_details(self, candidate, twitter_profile_image_url_https,
                                      twitter_profile_background_image_url_https,
                                      twitter_profile_banner_url_https):
        """
        Reset an candidate entry with original image details from we vote image.
        """
        success = False
        status = "ENTERING_RESET_CANDIDATE_IMAGE_DETAILS"

        if candidate:
            if positive_value_exists(twitter_profile_image_url_https):
                candidate.twitter_profile_image_url_https = twitter_profile_image_url_https
            if positive_value_exists(twitter_profile_background_image_url_https):
                candidate.twitter_profile_background_image_url_https = twitter_profile_background_image_url_https
            if positive_value_exists(twitter_profile_banner_url_https):
                candidate.twitter_profile_banner_url_https = twitter_profile_banner_url_https
            candidate.we_vote_hosted_profile_image_url_large = ''
            candidate.we_vote_hosted_profile_image_url_medium = ''
            candidate.we_vote_hosted_profile_image_url_tiny = ''
            candidate.save()
            success = True
            status = "RESET_CANDIDATE_IMAGE_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'candidate':    candidate,
        }
        return results

    def clear_candidate_twitter_details(self, candidate):
        """
        Update an candidate entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_CANDIDATE_TWITTER_DETAILS"

        if candidate:
            candidate.twitter_user_id = 0
            # We leave the handle in place
            # candidate.candidate_twitter_handle = ""
            candidate.twitter_name = ''
            candidate.twitter_followers_count = 0
            candidate.twitter_profile_image_url_https = ''
            candidate.we_vote_hosted_profile_image_url_large = ''
            candidate.we_vote_hosted_profile_image_url_medium = ''
            candidate.we_vote_hosted_profile_image_url_tiny = ''
            candidate.twitter_description = ''
            candidate.twitter_location = ''
            candidate.save()
            success = True
            status = "CLEARED_CANDIDATE_TWITTER_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'candidate':    candidate,
        }
        return results

    def refresh_cached_candidate_info(self, candidate_object):
        """
        The candidate tables cache information from other tables. This function reaches out to the source tables
        and copies over the latest information to the candidate table.
        :param candidate_object:
        :return:
        """
        values_changed = False

        if not positive_value_exists(candidate_object.contest_office_id) \
                or not positive_value_exists(candidate_object.contest_office_we_vote_id) \
                or not positive_value_exists(candidate_object.contest_office_name):
            office_found = False
            contest_office_manager = ContestOfficeManager()
            if positive_value_exists(candidate_object.contest_office_id):
                results = contest_office_manager.retrieve_contest_office_from_id(candidate_object.contest_office_id)
                office_found = results['contest_office_found']
            elif positive_value_exists(candidate_object.contest_office_we_vote_id):
                results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
                    candidate_object.contest_office_we_vote_id)
                office_found = results['contest_office_found']

            if office_found:
                office_object = results['contest_office']
                if not positive_value_exists(candidate_object.contest_office_id):
                    candidate_object.contest_office_id = office_object.id
                    values_changed = True
                if not positive_value_exists(candidate_object.contest_office_we_vote_id):
                    candidate_object.contest_office_we_vote_id = office_object.we_vote_id
                    values_changed = True
                if not positive_value_exists(candidate_object.contest_office_name):
                    candidate_object.contest_office_name = office_object.office_name
                    values_changed = True

        if values_changed:
            candidate_object.save()

        return candidate_object

    def create_candidate_row_entry(self, update_values):
        """
        Create CandidateCampaign table entry with CandidateCampaign details 
        :param update_values:
        :return:
        """
        success = False
        status = ""
        candidate_updated = False
        new_candidate_created = False
        new_candidate = ''

        # Variables we accept
        candidate_name = update_values['candidate_name'] if 'candidate_name' in update_values else ''
        contest_office_we_vote_id = update_values['contest_office_we_vote_id'] \
            if 'contest_office_we_vote_id' in update_values else False
        contest_office_id = update_values['contest_office_id'] \
            if 'contest_office_id' in update_values else False
        contest_office_name = update_values['contest_office_name'] \
            if 'contest_office_name' in update_values else False
        candidate_party_name = update_values['party'] if 'party' in update_values else ''
        candidate_is_incumbent = update_values['candidate_is_incumbent'] \
            if 'candidate_is_incumbent' in update_values else False
        candidate_is_top_ticket = update_values['candidate_is_top_ticket'] \
            if 'candidate_is_top_ticket' in update_values else False
        ctcl_uuid = update_values['ctcl_uuid'] if 'ctcl_uuid' in update_values else ''
        google_civic_election_id = update_values['google_civic_election_id'] \
            if 'google_civic_election_id' in update_values else ''
        state_code = update_values['state_code'] if 'state_code' in update_values else ''
        candidate_twitter_handle = update_values['candidate_twitter_handle'] \
            if 'candidate_twitter_handle' in update_values else ''
        candidate_url = update_values['candidate_url'] \
            if 'candidate_url' in update_values else ''
        facebook_url = update_values['facebook_url'] \
            if 'facebook_url' in update_values else ''

        if not positive_value_exists(candidate_name) or not positive_value_exists(contest_office_we_vote_id) \
                or not positive_value_exists(contest_office_id) \
                or not positive_value_exists(google_civic_election_id) or not positive_value_exists(state_code):
            # If we don't have the minimum values required to create a candidate, then don't proceed
            status += "CREATE_CANDIDATE_ROW "
            results = {
                    'success':                  success,
                    'status':                   status,
                    'new_candidate_created':    new_candidate_created,
                    'candidate_updated':        candidate_updated,
                    'new_candidate':            new_candidate,
                }
            return results

        try:
            new_candidate = CandidateCampaign.objects.create(candidate_name=candidate_name,
                                                             contest_office_we_vote_id=contest_office_we_vote_id,
                                                             google_civic_election_id=google_civic_election_id,
                                                             state_code=state_code)
            if new_candidate:
                success = True
                status += "CANDIDATE_CREATED "
                new_candidate_created = True
            else:
                success = False
                status += "CANDIDATE_CREATE_FAILED "
        except Exception as e:
            success = False
            new_candidate_created = False
            status += "CANDIDATE_CREATE_ERROR "
            handle_exception(e, logger=logger, exception_message=status)

        if new_candidate_created:
            try:
                new_candidate.contest_office_id = contest_office_id
                new_candidate.contest_office_name = contest_office_name
                new_candidate.party = candidate_party_name
                new_candidate.ctcl_uuid = ctcl_uuid
                new_candidate.candidate_is_incumbent = candidate_is_incumbent
                new_candidate.candidate_is_top_ticket = candidate_is_top_ticket
                new_candidate.candidate_twitter_handle = candidate_twitter_handle
                new_candidate.candidate_url = candidate_url
                new_candidate.facebook_url = facebook_url
                new_candidate.save()

                status += "CANDIDATE_CREATE_THEN_UPDATE_SUCCESS "
            except Exception as e:
                success = False
                new_candidate_created = False
                status += "CANDIDATE_CREATE_THEN_UPDATE_ERROR "
                handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'new_candidate_created':    new_candidate_created,
                'candidate_updated':        candidate_updated,
                'new_candidate':            new_candidate,
            }
        return results

    def update_candidate_row_entry(self, candidate_we_vote_id, update_values):
        """
        Update CandidateCampaign table entry with matching we_vote_id
        :param candidate_we_vote_id:
        :param update_values:
        :return:
        """

        success = False
        status = ""
        candidate_updated = False
        existing_candidate_entry = ''

        try:
            existing_candidate_entry = CandidateCampaign.objects.get(we_vote_id__iexact=candidate_we_vote_id)
            values_changed = False

            if existing_candidate_entry:
                # found the existing entry, update the values
                if 'candidate_name' in update_values:
                    existing_candidate_entry.candidate_name = update_values['candidate_name']
                    values_changed = True
                if 'party' in update_values:
                    existing_candidate_entry.party = update_values['party']
                    values_changed = True
                if 'contest_office_we_vote_id' in update_values:
                    existing_candidate_entry.contest_office_we_vote_id = update_values['contest_office_we_vote_id']
                    values_changed = True
                if 'contest_office_id' in update_values:
                    existing_candidate_entry.contest_office_id = update_values['contest_office_id']
                    values_changed = True
                if 'contest_office_name' in update_values:
                    existing_candidate_entry.contest_office_name = update_values['contest_office_name']
                    values_changed = True
                if 'google_civic_election_id' in update_values:
                    existing_candidate_entry.google_civic_election_id = update_values['google_civic_election_id']
                    values_changed = True
                if 'candidate_is_incumbent' in update_values:
                    existing_candidate_entry.candidate_is_incumbent = update_values['candidate_is_incumbent']
                    values_changed = True
                if 'candidate_is_top_ticket' in update_values:
                    existing_candidate_entry.is_top_ticket = update_values['candidate_is_top_ticket']
                    values_changed = True
                if 'ctcl_uuid' in update_values:
                    existing_candidate_entry.ctcl_uuid = update_values['ctcl_uuid']
                    values_changed = True
                if 'state_code' in update_values:
                    existing_candidate_entry.state_code = update_values['state_code']
                    values_changed = True
                if 'candidate_twitter_handle' in update_values:
                    existing_candidate_entry.candidate_twitter_handle = update_values['candidate_twitter_handle']
                    values_changed = True
                if 'candidate_url' in update_values:
                    existing_candidate_entry.candidate_url = update_values['candidate_url']
                    values_changed = True
                if 'facebook_url' in update_values:
                    existing_candidate_entry.facebook_url = update_values['facebook_url']
                    values_changed = True
                # now go ahead and save this entry (update)
                if values_changed:
                    existing_candidate_entry.save()
                    candidate_updated = True
                    success = True
                    status = "CANDIDATE_UPDATED"
                else:
                    candidate_updated = False
                    success = True
                    status = "CANDIDATE_NOT_UPDATED-NO_CHANGES "
        except Exception as e:
            success = False
            candidate_updated = False
            status = "CANDIDATE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':              success,
                'status':               status,
                'candidate_updated':    candidate_updated,
                'updated_candidate':    existing_candidate_entry,
            }
        return results
