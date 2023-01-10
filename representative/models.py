# representative/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from office_held.models import OfficeHeld, OfficeHeldManager
import re
from wevote_settings.models import fetch_next_we_vote_id_representative_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, display_full_name_with_correct_capitalization, \
    extract_title_from_full_name, extract_first_name_from_full_name, extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_suffix_from_full_name, extract_nickname_from_full_name, \
    extract_state_from_ocd_division_id, extract_twitter_handle_from_text_string, \
    positive_value_exists
from image.models import ORGANIZATION_ENDORSEMENTS_IMAGE_NAME

logger = wevote_functions.admin.get_logger(__name__)

# When merging representatives, these are the fields we check for figure_out_representative_conflict_values
REPRESENTATIVE_UNIQUE_IDENTIFIERS = [
    'ballot_guide_official_statement',
    'ballotpedia_representative_id',
    'ballotpedia_representative_name',
    'ballotpedia_representative_url',
    'ballotpedia_page_title',
    'ballotpedia_photo_url',
    'representative_email',
    'representative_name',
    'representative_phone',
    'representative_twitter_handle',
    'representative_url',
    'office_held_id',
    'office_held_name',
    'office_held_we_vote_id',
    'ctcl_uuid',
    'facebook_profile_image_url_https',
    'facebook_url',
    'google_civic_representative_name',
    'google_civic_election_id',
    'google_plus_url',
    'linkedin_url',
    'linkedin_photo_url',
    'maplight_id',
    'ocd_division_id',
    'order_on_ballot',
    'other_source_photo_url',
    'other_source_url',
    'political_party',
    'photo_url',
    'photo_url_from_maplight',
    'photo_url_from_vote_smart',
    'politician_id',
    'politician_we_vote_id',
    'state_code',
    'twitter_location',
    'twitter_name',
    'twitter_profile_background_image_url_https',
    'twitter_profile_banner_url_https',
    'twitter_profile_image_url_https',
    'twitter_url',
    'twitter_user_id',
    'vote_smart_id',
    'we_vote_hosted_profile_image_url_large',
    'we_vote_hosted_profile_image_url_medium',
    'we_vote_hosted_profile_image_url_tiny',
    'wikipedia_page_title',
    'wikipedia_photo_url',
    'youtube_url',
]


class RepresentativeListManager(models.Manager):
    """
    This is a class to make it easy to retrieve lists of Representatives
    """

    def retrieve_all_representatives_for_office(self, office_id, office_we_vote_id):
        representative_list = []
        representative_list_found = False

        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
            results = {
                'success':              True if representative_list_found else False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'representative_list_found': representative_list_found,
                'representative_list':       representative_list,
            }
            return results

        try:
            representative_queryset = Representative.objects.all()
            if positive_value_exists(office_id):
                representative_queryset = representative_queryset.filter(office_held_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                representative_queryset = representative_queryset.filter(
                    office_held_we_vote_id=office_we_vote_id)
            representative_queryset = representative_queryset.order_by('-twitter_followers_count')
            representative_list = representative_queryset

            if len(representative_list):
                representative_list_found = True
                status = 'REPRESENTATIVES_RETRIEVED'
            else:
                status = 'NO_REPRESENTATIVES_RETRIEVED'
        except Representative.DoesNotExist:
            # No representatives found. Not a problem.
            status = 'NO_REPRESENTATIVES_FOUND_DoesNotExist'
            representative_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_representatives_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if representative_list_found else False,
            'status':                       status,
            'office_id':                    office_id,
            'office_we_vote_id':            office_we_vote_id,
            'representative_list_found':  representative_list_found,
            'representative_list':        representative_list,
        }
        return results

    def retrieve_all_representatives_for_upcoming_election(self, google_civic_election_id=0, state_code='',
                                                             return_list_of_objects=False):
        representative_list_objects = []
        representative_list_light = []
        representative_list_found = False

        try:
            representative_queryset = Representative.objects.all()
            if positive_value_exists(google_civic_election_id):
                representative_queryset = representative_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(state_code):
                representative_queryset = representative_queryset.filter(state_code__iexact=state_code)
            representative_queryset = representative_queryset.order_by("representative_name")
            if positive_value_exists(google_civic_election_id):
                representative_list_objects = representative_queryset
            else:
                representative_list_objects = representative_queryset[:300]

            if len(representative_list_objects):
                representative_list_found = True
                status = 'REPRESENTATIVES_RETRIEVED'
                success = True
            else:
                status = 'NO_REPRESENTATIVES_RETRIEVED'
                success = True
        except Representative.DoesNotExist:
            # No representatives found. Not a problem.
            status = 'NO_REPRESENTATIVES_FOUND_DoesNotExist'
            representative_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_representatives_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        if representative_list_found:
            for representative in representative_list_objects:
                one_representative = {
                    'ballot_item_display_name': representative.display_representative_name(),
                    'representative_we_vote_id':     representative.we_vote_id,
                    'office_we_vote_id':        representative.office_held_we_vote_id,
                    'measure_we_vote_id':       '',
                }
                representative_list_light.append(one_representative.copy())

        results = {
            'success':                          success,
            'status':                           status,
            'google_civic_election_id':         google_civic_election_id,
            'representative_list_found':      representative_list_found,
            'representative_list_objects':    representative_list_objects if return_list_of_objects else [],
            'representative_list_light':      representative_list_light,
        }
        return results

    def retrieve_representative_count_for_office(self, office_id, office_we_vote_id):
        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
            results = {
                'success':              False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'representative_count':      0,
            }
            return results

        try:
            representative_queryset = Representative.objects.using('readonly').all()
            if positive_value_exists(office_id):
                representative_queryset = representative_queryset.filter(office_held_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                representative_queryset = representative_queryset.filter(
                    office_held_we_vote_id=office_we_vote_id)
            representative_list = representative_queryset

            representative_count = representative_list.count()
            success = True
            status = "REPRESENTATIVE_COUNT_FOUND"
        except Representative.DoesNotExist:
            # No representatives found. Not a problem.
            status = 'NO_REPRESENTATIVES_FOUND_DoesNotExist'
            representative_count = 0
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_representatives_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False
            representative_count = 0

        results = {
            'success':              success,
            'status':               status,
            'office_id':            office_id,
            'office_we_vote_id':    office_we_vote_id,
            'representative_count':      representative_count,
        }
        return results

    def is_automatic_merge_ok(self, representative_option1, representative_option2):
        automatic_merge_ok = True
        status = ""
        if representative_option1.representative_name != representative_option2.representative_name:
            automatic_merge_ok = False
            status += " representative_name:"
        representative1_twitter_handle = str(representative_option1.representative_twitter_handle)
        representative2_twitter_handle = str(representative_option2.representative_twitter_handle)
        if representative1_twitter_handle.lower() != representative2_twitter_handle.lower():
            automatic_merge_ok = False
            status += " representative_twitter_handle:"
        if representative_option1.representative_url != representative_option2.representative_url:
            automatic_merge_ok = False
            status += " representative_url:"

        if not automatic_merge_ok:
            status = "Different: " + status

        results = {
            "status":               status,
            "automatic_merge_ok":   automatic_merge_ok,
        }
        return results

    def do_automatic_merge(self, representative_option1, representative_option2):
        success = False
        status = "do_automatic_merge NOT IMPLEMENTED YET"

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def find_and_merge_duplicate_representatives(self, google_civic_election_id, merge=False, remove=False):
        success = False
        status = "find_and_merge_duplicate_representatives NOT IMPLEMENTED YET"

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
        }
        return results

    def retrieve_representatives_from_all_elections_list(self):
        """
        This is used by the admin tools to show Representatives in a drop-down for example
        """
        representatives_list_temp = Representative.objects.all()
        # Order by representative_name.
        # To order by last name we will need to make some guesses in some case about what the last name is.
        representatives_list_temp = representatives_list_temp.order_by('representative_name')[:300]
        return representatives_list_temp

    def remove_duplicate_representative(self, representative_id, google_civic_election_id):
        # TODO DALE We need to delete the positions associated with this representative, and convert them to belong
        # to representative we leave in place.

        success = False
        status = "COULD_NOT_DELETE_DUPLICATE_REPRESENTATIVE"

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def retrieve_possible_duplicate_representatives(self, representative_name, google_civic_representative_name,
                                                      google_civic_election_id, office_we_vote_id,
                                                      politician_we_vote_id,
                                                      representative_twitter_handle,
                                                      ballotpedia_representative_id, vote_smart_id, maplight_id,
                                                      we_vote_id_from_master=''):
        representative_list_objects = []
        filters = []
        representative_list_found = False
        ballotpedia_representative_id = convert_to_int(ballotpedia_representative_id)

        try:
            representative_queryset = Representative.objects.all()
            representative_queryset = representative_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            # We don't look for office_we_vote_id because of the chance that locally we are using a
            # different we_vote_id
            # representative_queryset = representative_queryset.filter(
            # office_held_we_vote_id__iexact=office_we_vote_id)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                representative_queryset = representative_queryset.filter(
                    ~Q(we_vote_id__iexact=we_vote_id_from_master))

            # We want to find representatives with *any* of these values
            if positive_value_exists(google_civic_representative_name):
                # We intentionally use case sensitive matching here
                new_filter = Q(google_civic_representative_name__exact=google_civic_representative_name)
                filters.append(new_filter)
            elif positive_value_exists(representative_name):
                new_filter = Q(representative_name__iexact=representative_name)
                filters.append(new_filter)

            if positive_value_exists(politician_we_vote_id):
                new_filter = Q(politician_we_vote_id__iexact=politician_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(representative_twitter_handle):
                new_filter = Q(representative_twitter_handle__iexact=representative_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(ballotpedia_representative_id):
                new_filter = Q(ballotpedia_representative_id=ballotpedia_representative_id)
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

                representative_queryset = representative_queryset.filter(final_filters)

            representative_list_objects = representative_queryset

            if len(representative_list_objects):
                representative_list_found = True
                status = 'DUPLICATE_REPRESENTATIVES_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_REPRESENTATIVES_RETRIEVED'
                success = True
        except Representative.DoesNotExist:
            # No representatives found. Not a problem.
            status = 'NO_DUPLICATE_REPRESENTATIVES_FOUND_DoesNotExist'
            representative_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_representatives ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'representative_list_found':     representative_list_found,
            'representative_list':           representative_list_objects,
        }
        return results

    def retrieve_representatives_from_non_unique_identifiers(self, google_civic_election_id, state_code,
                                                               representative_twitter_handle, representative_name,
                                                               ignore_representative_id_list=[]):
        keep_looking_for_duplicates = True
        representative = Representative()
        representative_found = False
        representative_list = []
        representative_list_found = False
        multiple_entries_found = False
        representative_twitter_handle = extract_twitter_handle_from_text_string(representative_twitter_handle)
        success = True
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(representative_twitter_handle):
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    representative_twitter_handle__iexact=representative_twitter_handle,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_representative_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_id_list)

                representative_list = list(representative_query)
                if len(representative_list):
                    # At least one entry exists
                    status += 'BATCH_ROW_ACTION_REPRESENTATIVE_LIST_RETRIEVED '
                    # if a single entry matches, update that entry
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
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_QUERY_FAILED1 "
                keep_looking_for_duplicates = False
        # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search by Representative name exact match
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    representative_name__iexact=representative_name,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_representative_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_id_list)

                representative_list = list(representative_query)
                if len(representative_list):
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
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_QUERY_FAILED2 "

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search for Representative(s) that contains the same first and last names
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=last_name)

                if positive_value_exists(ignore_representative_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_id_list)

                representative_list = list(representative_query)
                if len(representative_list):
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
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_QUERY_FAILED3 "

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'representative_found':          representative_found,
            'representative':                representative,
            'representative_list_found':     representative_list_found,
            'representative_list':           representative_list,
            'multiple_entries_found':   multiple_entries_found,
        }
        return results

    def fetch_representatives_from_non_unique_identifiers_count(
            self, google_civic_election_id, state_code, representative_twitter_handle, representative_name,
            ignore_representative_id_list=[]):
        keep_looking_for_duplicates = True
        representative_twitter_handle = extract_twitter_handle_from_text_string(representative_twitter_handle)
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(representative_twitter_handle):
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    representative_twitter_handle__iexact=representative_twitter_handle,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_representative_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_id_list)

                representative_count = representative_query.count()
                if positive_value_exists(representative_count):
                    return representative_count
            except Representative.DoesNotExist:
                pass
            except Exception as e:
                keep_looking_for_duplicates = False
                pass
        # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search by Representative name exact match
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    representative_name__iexact=representative_name,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_representative_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_id_list)

                representative_count = representative_query.count()
                if positive_value_exists(representative_count):
                    return representative_count
            except Representative.DoesNotExist:
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_NOT_FOUND "

        if keep_looking_for_duplicates and positive_value_exists(representative_name):
            # Search for Representative(s) that contains the same first and last names
            try:
                representative_query = Representative.objects.all()
                representative_query = representative_query.filter(
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    representative_query = representative_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(representative_name)
                representative_query = representative_query.filter(representative_name__icontains=last_name)

                if positive_value_exists(ignore_representative_id_list):
                    representative_query = representative_query.exclude(
                        we_vote_id__in=ignore_representative_id_list)

                representative_count = representative_query.count()
                if positive_value_exists(representative_count):
                    return representative_count
            except Representative.DoesNotExist:
                status += "BATCH_ROW_ACTION_REPRESENTATIVE_NOT_FOUND "
                success = True

        return 0


class Representative(models.Model):
    # This entry is for a person elected into an office. Not the same as a Politician entry, which is the person
    #  whether they are in office or not.
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "rep", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_representative_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this person in this position",
        max_length=255, default=None, null=True,
        blank=True, unique=True)
    # The internal We Vote id for the OfficeHeld that this representative is competing for.
    # During setup we need to allow
    # this to be null.
    office_held_id = models.CharField(
        verbose_name="office_held_id id", max_length=255, null=True, blank=True)
    # We want to link the representative to the office held with permanent ids, so we can export and import
    office_held_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the office this representative is running for", max_length=255,
        default=None, null=True, blank=True, unique=False)
    office_held_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)
    # politician (internal) link to local We Vote Politician entry. During setup we need to allow this to be null.
    politician_id = models.BigIntegerField(verbose_name="politician unique identifier", null=True, blank=True)
    # The persistent We Vote unique ID of the Politician, so we can export and import into other databases.
    politician_we_vote_id = models.CharField(
        verbose_name="we vote politician id", max_length=255, null=True, blank=True)
    # The representative's name.
    representative_name = models.CharField(verbose_name="representative name", max_length=255, null=False,
                                             blank=False)
    # The representative's name as passed over by Google Civic.
    # We save this so we can match to this representative even
    # if we edit the representative's name locally.
    google_civic_representative_name = models.CharField(
        verbose_name="representative name exactly as received from google civic",
        max_length=255, null=False, blank=False)
    # The full name of the party the representative is a member of.
    political_party = models.CharField(verbose_name="political_party", max_length=255, null=True, blank=True)
    # A URL for a photo of the representative.
    photo_url = models.CharField(verbose_name="photoUrl", max_length=255, null=True, blank=True)
    photo_url_from_maplight = models.URLField(
        verbose_name='representative portrait url of representative from maplight', blank=True, null=True)
    photo_url_from_vote_smart = models.URLField(
        verbose_name='representative portrait url of representative from vote smart', blank=True, null=True)
    # The order the representative appears on the ballot relative to other representatives for this contest.
    order_on_ballot = models.CharField(verbose_name="order on ballot", max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="state this representative serves", max_length=2, null=True,
                                  blank=True)
    # The URL for the representative's campaign web site.
    representative_url = models.URLField(
        verbose_name='website url of representative', max_length=255, blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of representative', blank=True, null=True)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of profile image from facebook',
                                                       blank=True, null=True)

    twitter_url = models.URLField(verbose_name='twitter url of representative', blank=True, null=True)
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    representative_twitter_handle = models.CharField(
        verbose_name='representative twitter screen_name', max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="representative plain text name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="representative location from twitter", max_length=255, null=True, blank=True)
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

    google_plus_url = models.URLField(verbose_name='google plus url of representative', blank=True, null=True)
    vote_smart_id = models.CharField(verbose_name="votesmart unique identifier",
                                     max_length=200, null=True, unique=False)
    maplight_id = models.CharField(verbose_name="maplight unique identifier",
                                   max_length=200, null=True, unique=True, blank=True)
    youtube_url = models.URLField(verbose_name='youtube url of representative', blank=True, null=True)
    # The email address for the representative's campaign.
    representative_email = models.CharField(verbose_name="representative email", max_length=255, null=True,
                                              blank=True)
    # The voice phone number for the representatives office.
    representative_phone = models.CharField(verbose_name="representative phone", max_length=255, null=True,
                                              blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', max_length=255, blank=True, null=True)
    linkedin_url = models.CharField(
        verbose_name="linkedin url of representative", max_length=255, null=True, blank=True)
    linkedin_photo_url = models.URLField(verbose_name='url of linkedin logo', max_length=255, blank=True, null=True)

    # other_source_url is the location (ex/ http://mywebsite.com/representative1.html) where we find
    # the other_source_photo_url OR the original url of the photo before we store it locally
    other_source_url = models.CharField(
        verbose_name="other source url of representative", max_length=255, null=True, blank=True)
    other_source_photo_url = models.URLField(
        verbose_name='url of other source image', max_length=255, blank=True, null=True)

    ballotpedia_representative_id = models.PositiveIntegerField(
        verbose_name="ballotpedia integer id", null=True, blank=True)
    # The representative's name as passed over by Ballotpedia
    ballotpedia_representative_name = models.CharField(
        verbose_name="representative name exactly as received from ballotpedia", max_length=255, null=True,
        blank=True)
    ballotpedia_representative_url = models.URLField(
        verbose_name='url of representative on ballotpedia', max_length=255, blank=True, null=True)
    # This is just the characters in the Ballotpedia URL
    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(
        verbose_name='url of ballotpedia logo', max_length=255, blank=True, null=True)

    # CTCL representative data fields
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=36, null=True, blank=True)

    def office_held(self):
        try:
            office_held = OfficeHeld.objects.get(id=self.office_held_id)
        except OfficeHeld.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            return
        except OfficeHeld.DoesNotExist:
            return
        return office_held

    def representative_photo_url(self):
        if self.we_vote_hosted_profile_image_url_tiny:
            return self.we_vote_hosted_profile_image_url_tiny
        if self.photo_url_from_vote_smart:
            return self.photo_url_from_vote_smart_large()
        if self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https_original()
        if self.facebook_profile_image_url_https:
            return self.facebook_profile_image_url_https
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
        return representative_party_display(self.political_party)

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
        if self.maplight_id == "":  # We want this to be unique IF there is a value, and otherwise "None"
            self.maplight_id = None
        super(Representative, self).save(*args, **kwargs)


def fetch_representative_count_for_office_held(office_held_id=0, office_held_we_vote_id=''):
    representative_list = RepresentativeListManager()
    results = representative_list.retrieve_representative_count_for_office(office_held_id,
                                                                               office_held_we_vote_id)
    return results['representative_count']


# See also 'convert_to_political_party_constant' in we_vote_functions/functions.py
def representative_party_display(raw_political_party):
    if raw_political_party is None:
        return ''
    if raw_political_party == '':
        return ''
    if raw_political_party == 'Amer. Ind.':
        return 'American Independent'
    if raw_political_party == 'DEM':
        return 'Democrat'
    if raw_political_party == 'Democratic':
        return 'Democrat'
    if raw_political_party == 'Party Preference: Democratic':
        return 'Democrat'
    if raw_political_party == 'GRN':
        return 'Green'
    if raw_political_party == 'LIB':
        return 'Libertarian'
    if raw_political_party == 'NPP':
        return 'No Party Preference'
    if raw_political_party == 'Party Preference: None':
        return 'No Party Preference'
    if raw_political_party == 'PF':
        return 'Peace and Freedom'
    if raw_political_party == 'REP':
        return 'Republican'
    if raw_political_party == 'Party Preference: Republican':
        return 'Republican'
    if raw_political_party.lower() == 'none':
        return ''
    else:
        return raw_political_party


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

    def retrieve_representative_from_id(self, representative_id):
        representative_manager = RepresentativeManager()
        return representative_manager.retrieve_representative(representative_id)

    def retrieve_representative_from_we_vote_id(self, we_vote_id):
        representative_id = 0
        representative_manager = RepresentativeManager()
        return representative_manager.retrieve_representative(representative_id, we_vote_id)

    def fetch_representative_id_from_we_vote_id(self, we_vote_id):
        representative_id = 0
        representative_manager = RepresentativeManager()
        results = representative_manager.retrieve_representative(representative_id, we_vote_id)
        if results['success']:
            return results['representative_id']
        return 0

    def fetch_representative_we_vote_id_from_id(self, representative_id):
        we_vote_id = ''
        representative_manager = RepresentativeManager()
        results = representative_manager.retrieve_representative(representative_id, we_vote_id)
        if results['success']:
            return results['representative_we_vote_id']
        return ''

    def fetch_google_civic_representative_name_from_we_vote_id(self, we_vote_id):
        representative_id = 0
        representative_manager = RepresentativeManager()
        results = representative_manager.retrieve_representative(representative_id, we_vote_id)
        if results['success']:
            representative = results['representative']
            return representative.google_civic_representative_name
        return 0

    def retrieve_representative_from_maplight_id(self, representative_maplight_id):
        representative_id = 0
        we_vote_id = ''
        representative_manager = RepresentativeManager()
        return representative_manager.retrieve_representative(
            representative_id, we_vote_id, representative_maplight_id)

    def retrieve_representative_from_vote_smart_id(self, representative_vote_smart_id):
        representative_id = 0
        we_vote_id = ''
        representative_maplight_id = ''
        representative_name = ''
        representative_manager = RepresentativeManager()
        return representative_manager.retrieve_representative(
            representative_id, we_vote_id, representative_maplight_id, representative_name,
            representative_vote_smart_id)

    def retrieve_representative_from_ballotpedia_representative_id(self, ballotpedia_representative_id):
        representative_id = 0
        we_vote_id = ''
        representative_maplight_id = ''
        representative_name = ''
        representative_vote_smart_id = 0
        return self.retrieve_representative(
            representative_id, we_vote_id, representative_maplight_id, representative_name,
            representative_vote_smart_id, ballotpedia_representative_id)

    def retrieve_representative_from_representative_name(self, representative_name):
        representative_id = 0
        we_vote_id = ''
        representative_maplight_id = ''
        representative_manager = RepresentativeManager()

        results = representative_manager.retrieve_representative(
            representative_id, we_vote_id, representative_maplight_id, representative_name)
        if results['success']:
            return results

        # Try to modify the representative name, and search again
        # MapLight for example will pass in "Ronald  Gold" for example
        representative_name_try2 = representative_name.replace('  ', ' ')
        results = representative_manager.retrieve_representative(
            representative_id, we_vote_id, representative_maplight_id, representative_name_try2)
        if results['success']:
            return results

        # MapLight also passes in "Kamela D Harris" for example, and Google Civic uses "Kamela D. Harris"
        representative_name_try3 = mimic_google_civic_initials(representative_name)
        if representative_name_try3 != representative_name:
            results = representative_manager.retrieve_representative(
                representative_id, we_vote_id, representative_maplight_id, representative_name_try3)
            if results['success']:
                return results

        # Otherwise return failed results
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_representative(
            self, representative_id, representative_we_vote_id=None, representative_maplight_id=None,
            representative_name=None, representative_vote_smart_id=None, ballotpedia_representative_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        representative_on_stage = Representative()

        try:
            if positive_value_exists(representative_id):
                representative_on_stage = Representative.objects.get(id=representative_id)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status = "RETRIEVE_REPRESENTATIVE_FOUND_BY_ID"
            elif positive_value_exists(representative_we_vote_id):
                representative_on_stage = Representative.objects.get(we_vote_id=representative_we_vote_id)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status = "RETRIEVE_REPRESENTATIVE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(representative_maplight_id):
                representative_on_stage = Representative.objects.get(maplight_id=representative_maplight_id)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status = "RETRIEVE_REPRESENTATIVE_FOUND_BY_MAPLIGHT_ID"
            elif positive_value_exists(representative_vote_smart_id):
                representative_on_stage = Representative.objects.get(vote_smart_id=representative_vote_smart_id)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status = "RETRIEVE_REPRESENTATIVE_FOUND_BY_VOTE_SMART_ID"
            elif positive_value_exists(representative_name):
                representative_on_stage = Representative.objects.get(representative_name=representative_name)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status = "RETRIEVE_REPRESENTATIVE_FOUND_BY_NAME"
            elif positive_value_exists(ballotpedia_representative_id):
                ballotpedia_representative_id_integer = convert_to_int(ballotpedia_representative_id)
                representative_on_stage = Representative.objects.get(
                    ballotpedia_representative_id=ballotpedia_representative_id_integer)
                representative_id = representative_on_stage.id
                representative_we_vote_id = representative_on_stage.we_vote_id
                representative_found = True
                status = "RETRIEVE_REPRESENTATIVE_FOUND_BY_BALLOTPEDIA_REPRESENTATIVE_ID"
            else:
                representative_found = False
                status = "RETRIEVE_REPRESENTATIVE_SEARCH_INDEX_MISSING"
        except Representative.MultipleObjectsReturned as e:
            representative_found = False
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_REPRESENTATIVE_MULTIPLE_OBJECTS_RETURNED"
        except Representative.DoesNotExist:
            representative_found = False
            exception_does_not_exist = True
            status = "RETRIEVE_REPRESENTATIVE_NOT_FOUND"
        except Exception as e:
            representative_found = False
            status = "RETRIEVE_REPRESENTATIVE_NOT_FOUND_EXCEPTION"

        results = {
            'success':                      True if convert_to_int(representative_id) > 0 else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'representative_found':       representative_found,
            'representative_id':          convert_to_int(representative_id),
            'representative_we_vote_id':  representative_we_vote_id,
            'representative':             representative_on_stage,
        }
        return results

    def retrieve_representatives_are_not_duplicates(self, representative1_we_vote_id, representative2_we_vote_id,
                                                      read_only=True):
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
            status = "REPRESENTATIVES_NOT_DUPLICATES_UPDATED_OR_CREATED1 "
        except RepresentativesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            representatives_are_not_duplicates_found = False
            status = 'NO_REPRESENTATIVES_NOT_DUPLICATES_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            representatives_are_not_duplicates_found = False
            representatives_are_not_duplicates = RepresentativesAreNotDuplicates()
            success = False
            status = "REPRESENTATIVES_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED1 "

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
                status = "REPRESENTATIVES_NOT_DUPLICATES_UPDATED_OR_CREATED2 "
            except RepresentativesAreNotDuplicates.DoesNotExist:
                # No data found. Try again below
                success = True
                representatives_are_not_duplicates_found = False
                status = 'NO_REPRESENTATIVES_NOT_DUPLICATES_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                representatives_are_not_duplicates_found = False
                representatives_are_not_duplicates = RepresentativesAreNotDuplicates()
                success = False
                status = "REPRESENTATIVES_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED2 "

        results = {
            'success':                                      success,
            'status':                                       status,
            'representatives_are_not_duplicates_found':   representatives_are_not_duplicates_found,
            'representatives_are_not_duplicates':         representatives_are_not_duplicates,
        }
        return results

    def retrieve_representatives_are_not_duplicates_list(self, representative_we_vote_id, read_only=True):
        """
        Get a list of other representative_we_vote_id's that are not duplicates
        :param representative_we_vote_id:
        :param read_only:
        :return:
        """
        # Note that the direction of the linkage does not matter
        representatives_are_not_duplicates_list1 = []
        representatives_are_not_duplicates_list2 = []
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
            status = "REPRESENTATIVES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except RepresentativesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status = 'NO_REPRESENTATIVES_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status = "REPRESENTATIVES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1 "

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
                status = "REPRESENTATIVES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except RepresentativesAreNotDuplicates.DoesNotExist:
                success = True
                status = 'NO_REPRESENTATIVES_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status = "REPRESENTATIVES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2 "

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
            'representatives_are_not_duplicates_list_found':  representatives_are_not_duplicates_list_found,
            'representatives_are_not_duplicates_list':        representatives_are_not_duplicates_list,
            'representatives_are_not_duplicates_list_we_vote_ids':
                representatives_are_not_duplicates_list_we_vote_ids,
        }
        return results

    def fetch_representatives_are_not_duplicates_list_we_vote_ids(self, representative_we_vote_id):
        results = self.retrieve_representatives_are_not_duplicates_list(representative_we_vote_id)
        return results['representatives_are_not_duplicates_list_we_vote_ids']

    def update_or_create_representative(self,  office_held_name, representative_name,
                                          google_civic_representative_name, political_party, photo_url,
                                          ocd_division_id, state_code, representative_url,
                                          facebook_url, twitter_url, google_plus_url, youtube_url,
                                          representative_phone ):

        """
        Either update or create a representative entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_representative_created = False
        representative_on_stage = Representative()
        status = ""

        if not positive_value_exists(ocd_division_id):
            success = False
            status += 'MISSING_OCD_DIVISION_ID '
        elif not positive_value_exists(google_civic_representative_name):
            success = False
            status += 'MISSING_GOOGLE_CIVIC_REPRESENTATIVE_NAME '
        else:
            try:
                # If here we are using permanent public identifier office_held_we_vote_id
                representative_on_stage, new_representative_created = \
                    Representative.objects.update_or_create(
                        office_held_name=office_held_name,
                        representative_name=representative_name,
                        google_civic_representative_name=google_civic_representative_name,
                        ocd_division_id=ocd_division_id,
                        state_code=state_code,
                        political_party=political_party,
                        photo_url=photo_url,
                        representative_url=representative_url,
                        facebook_url=facebook_url,
                        twitter_url=twitter_url,
                        google_plus_url=google_plus_url,
                        youtube_url=youtube_url,
                        representative_phone=representative_phone)
                success = True
                status += "REPRESENTATIVE_CAMPAIGN_UPDATED_OR_CREATED "
            except Representative.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_REPRESENTATIVE_CAMPAIGNS_FOUND_BY_GOOGLE_CIVIC_REPRESENTATIVE_NAME '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_REPRESENTATIVE_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        # else:
        #     # Given we might have the office listed by google_civic_office_name
        #     # OR office_name, we need to check both before we try to create a new entry
        #     representative_found = False
        #     try:
        #         representative_on_stage = Representative.objects.get(
        #             google_civic_election_id__exact=google_civic_election_id,
        #             google_civic_representative_name__iexact=google_civic_representative_name
        #         )
        #         representative_found = True
        #         success = True
        #         status += 'CONTEST_OFFICE_SAVED '
        #     except Representative.MultipleObjectsReturned as e:
        #         success = False
        #         status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_GOOGLE_CIVIC_OFFICE_NAME '
        #         exception_multiple_object_returned = True
        #     except Representative.DoesNotExist:
        #         exception_does_not_exist = True
        #         status += "RETRIEVE_OFFICE_NOT_FOUND_BY_GOOGLE_CIVIC_REPRESENTATIVE_NAME "
        #     except Exception as e:
        #         status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME ' \
        #                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #
        #     if not representative_found and not exception_multiple_object_returned:
        #         # Try to find record based on office_name (instead of google_civic_office_name)
        #         try:
        #             representative_on_stage = Representative.objects.get(
        #                 google_civic_election_id__exact=google_civic_election_id,
        #                 representative_name__iexact=google_civic_representative_name
        #             )
        #             representative_found = True
        #             success = True
        #             status += 'REPRESENTATIVE_RETRIEVED_FROM_REPRESENTATIVE_NAME '
        #         except Representative.MultipleObjectsReturned as e:
        #             success = False
        #             status += 'MULTIPLE_MATCHING_REPRESENTATIVES_FOUND_BY_REPRESENTATIVE_NAME '
        #             exception_multiple_object_returned = True
        #         except Representative.DoesNotExist:
        #             exception_does_not_exist = True
        #             status += "RETRIEVE_REPRESENTATIVE_NOT_FOUND_BY_REPRESENTATIVE_NAME "
        #         except Exception as e:
        #             status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
        #                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #             success = False
        #
        #     if exception_multiple_object_returned:
        #         # We can't proceed because there is an error with the data
        #         success = False
        #     elif representative_found:
        #         # Update record
        #         # Note: When we decide to start updating representative_name elsewhere within We Vote, we should stop
        #         #  updating representative_name via subsequent Google Civic imports
        #         try:
        #             new_representative_created = False
        #             representative_updated = False
        #             representative_has_changes = False
        #             for key, value in updated_representative_values.items():
        #                 if hasattr(representative_on_stage, key):
        #                     representative_has_changes = True
        #                     setattr(representative_on_stage, key, value)
        #             if representative_has_changes and positive_value_exists(representative_on_stage.we_vote_id):
        #                 representative_on_stage.save()
        #                 representative_updated = True
        #             if representative_updated:
        #                 success = True
        #                 status += "REPRESENTATIVE_UPDATED "
        #             else:
        #                 success = False
        #                 status += "REPRESENTATIVE_NOT_UPDATED "
        #         except Exception as e:
        #             status += 'FAILED_TO_UPDATE_REPRESENTATIVE ' \
        #                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #             success = False
        #     else:
        #         # Create record
        #         try:
        #             new_representative_created = False
        #             representative_on_stage = Representative.objects.create(
        #                 google_civic_election_id=google_civic_election_id,
        #                 ocd_division_id=ocd_division_id,
        #                 office_held_id=office_held_id,
        #                 office_held_we_vote_id=office_held_we_vote_id,
        #                 google_civic_representative_name=google_civic_representative_name)
        #             if positive_value_exists(representative_on_stage.id):
        #                 for key, value in updated_representative_values.items():
        #                     if hasattr(representative_on_stage, key):
        #                         setattr(representative_on_stage, key, value)
        #                 representative_on_stage.save()
        #                 new_representative_created = True
        #             if positive_value_exists(new_representative_created):
        #                 status += "REPRESENTATIVE_CREATED "
        #                 success = True
        #             else:
        #                 status += "REPRESENTATIVE_NOT_CREATED "
        #                 success = False
        #
        #         except Exception as e:
        #             status += 'FAILED_TO_CREATE_REPRESENTATIVE ' \
        #                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #             success = False

        results = {
            'success':                      success,
            'status':                       status,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'new_representative_created': new_representative_created,
            'representative':             representative_on_stage,
        }
        return results

    def update_or_create_representatives_are_not_duplicates(self, representative1_we_vote_id,
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
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                                      success,
            'status':                                       status,
            'MultipleObjectsReturned':                      exception_multiple_object_returned,
            'new_representatives_are_not_duplicates_created':    new_representatives_are_not_duplicates_created,
            'representatives_are_not_duplicates':                representatives_are_not_duplicates,
        }
        return results

    def update_representative_social_media(self, representative, representative_twitter_handle=False,
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
                status = "SAVED_REPRESENTATIVE_SOCIAL_MEDIA"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_REPRESENTATIVE_SOCIAL_MEDIA"

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'representative':         representative,
        }
        return results

    def update_representative_twitter_details(self, representative, twitter_json,
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
            if 'id' in twitter_json and positive_value_exists(twitter_json['id']):
                if convert_to_int(twitter_json['id']) != representative.twitter_user_id:
                    representative.twitter_user_id = convert_to_int(twitter_json['id'])
                    values_changed = True
            if 'screen_name' in twitter_json and positive_value_exists(twitter_json['screen_name']):
                if twitter_json['screen_name'] != representative.representative_twitter_handle:
                    representative.representative_twitter_handle = twitter_json['screen_name']
                    values_changed = True
            if 'name' in twitter_json and positive_value_exists(twitter_json['name']):
                if twitter_json['name'] != representative.twitter_name:
                    representative.twitter_name = twitter_json['name']
                    values_changed = True
            if 'followers_count' in twitter_json and positive_value_exists(twitter_json['followers_count']):
                if convert_to_int(twitter_json['followers_count']) != representative.twitter_followers_count:
                    representative.twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                representative.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_image_url_https']):
                if twitter_json['profile_image_url_https'] != representative.twitter_profile_image_url_https:
                    representative.twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                representative.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            elif ('profile_banner_url' in twitter_json) and positive_value_exists(twitter_json['profile_banner_url']):
                if twitter_json['profile_banner_url'] != representative.twitter_profile_banner_url_https:
                    representative.twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                representative.twitter_profile_background_image_url_https = \
                    cached_twitter_profile_background_image_url_https
                values_changed = True
            elif 'profile_background_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_background_image_url_https']):
                if twitter_json['profile_background_image_url_https'] != \
                        representative.twitter_profile_background_image_url_https:
                    representative.twitter_profile_background_image_url_https = \
                        twitter_json['profile_background_image_url_https']
                    values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                representative.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                representative.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                representative.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_json:  # No value required to update description (so we can clear out)
                if twitter_json['description'] != representative.twitter_description:
                    representative.twitter_description = twitter_json['description']
                    values_changed = True
            if 'location' in twitter_json:  # No value required to update location (so we can clear out)
                if twitter_json['location'] != representative.twitter_location:
                    representative.twitter_location = twitter_json['location']
                    values_changed = True

            if values_changed:
                representative.save()
                success = True
                status = "SAVED_REPRESENTATIVE_TWITTER_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_REPRESENTATIVE_TWITTER_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'representative':    representative,
        }
        return results

    def reset_representative_image_details(self, representative, twitter_profile_image_url_https,
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
            status = "RESET_REPRESENTATIVE_IMAGE_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'representative':    representative,
        }
        return results

    def clear_representative_twitter_details(self, representative):
        """
        Update an representative entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_REPRESENTATIVE_TWITTER_DETAILS"

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
            status = "CLEARED_REPRESENTATIVE_TWITTER_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'representative':    representative,
        }
        return results

    def refresh_cached_representative_office_info(self, representative_object):
        """
        The representative tables cache information from other tables. This function reaches out to the source tables
        and copies over the latest information to the representative table.
        :param representative_object:
        :return:
        """
        values_changed = False
        office_found = False
        office_held_manager = OfficeHeldManager()
        results = {}
        if positive_value_exists(representative_object.office_held_id):
            results = office_held_manager.retrieve_office_held_from_id(representative_object.office_held_id)
            office_found = results['office_held_found']
        elif positive_value_exists(representative_object.office_held_we_vote_id):
            results = office_held_manager.retrieve_office_held_from_we_vote_id(
                representative_object.office_held_we_vote_id)
            office_found = results['office_held_found']

        if office_found:
            office_object = results['office_held']
            representative_object.office_held_id = office_object.id
            representative_object.office_held_we_vote_id = office_object.we_vote_id
            representative_object.office_held_name = office_object.office_name
            values_changed = True

        if values_changed:
            representative_object.save()

        return representative_object

    def create_representative_row_entry(self, update_values):
        """
        Create Representative table entry with Representative details
        :param update_values:
        :return:
        """
        success = False
        status = ""
        representative_updated = False
        new_representative_created = False
        new_representative = ''

        # Variables we accept
        representative_name = update_values['representative_name'] if 'representative_name' in update_values else ''
        office_held_we_vote_id = update_values['office_held_we_vote_id'] \
            if 'office_held_we_vote_id' in update_values else False
        office_held_id = update_values['office_held_id'] \
            if 'office_held_id' in update_values else False
        office_held_name = update_values['office_held_name'] \
            if 'office_held_name' in update_values else False
        representative_party_name = update_values['political_party'] if 'political_party' in update_values else ''
        ctcl_uuid = update_values['ctcl_uuid'] if 'ctcl_uuid' in update_values else ''
        google_civic_election_id = update_values['google_civic_election_id'] \
            if 'google_civic_election_id' in update_values else ''
        state_code = update_values['state_code'] if 'state_code' in update_values else ''
        representative_twitter_handle = update_values['representative_twitter_handle'] \
            if 'representative_twitter_handle' in update_values else ''
        representative_url = update_values['representative_url'] \
            if 'representative_url' in update_values else ''
        facebook_url = update_values['facebook_url'] \
            if 'facebook_url' in update_values else ''
        photo_url = update_values['photo_url'] \
            if 'photo_url' in update_values else ''

        if not positive_value_exists(representative_name) or not positive_value_exists(office_held_we_vote_id) \
                or not positive_value_exists(office_held_id) \
                or not positive_value_exists(google_civic_election_id) or not positive_value_exists(state_code):
            # If we don't have the minimum values required to create a representative, then don't proceed
            status += "CREATE_REPRESENTATIVE_ROW "
            results = {
                    'success':                  success,
                    'status':                   status,
                    'new_representative_created':    new_representative_created,
                    'representative_updated':        representative_updated,
                    'new_representative':            new_representative,
                }
            return results

        try:
            new_representative = Representative.objects.create(
                representative_name=representative_name,
                office_held_we_vote_id=office_held_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code)
            if new_representative:
                success = True
                status += "REPRESENTATIVE_CREATED "
                new_representative_created = True
            else:
                success = False
                status += "REPRESENTATIVE_CREATE_FAILED "
        except Exception as e:
            success = False
            new_representative_created = False
            status += "REPRESENTATIVE_CREATE_ERROR "
            handle_exception(e, logger=logger, exception_message=status)

        if new_representative_created:
            try:
                new_representative.office_held_id = office_held_id
                new_representative.office_held_name = office_held_name
                new_representative.political_party = representative_party_name
                new_representative.ctcl_uuid = ctcl_uuid
                new_representative.representative_twitter_handle = representative_twitter_handle
                new_representative.representative_url = representative_url
                new_representative.facebook_url = facebook_url
                new_representative.photo_url = photo_url
                if new_representative.photo_url:
                    representative_results = \
                        self.modify_representative_with_organization_endorsements_image(new_representative,
                                                                                   photo_url, True)
                    if representative_results['success']:
                        representative = representative_results['representative']
                        new_representative.we_vote_hosted_profile_image_url_large = \
                            representative.we_vote_hosted_profile_image_url_large
                        new_representative.we_vote_hosted_profile_image_url_medium = \
                            representative.we_vote_hosted_profile_image_url_medium
                        new_representative.we_vote_hosted_profile_image_url_tiny = \
                            representative.we_vote_hosted_profile_image_url_tiny
                new_representative.save()

                status += "REPRESENTATIVE_CREATE_THEN_UPDATE_SUCCESS "
            except Exception as e:
                success = False
                new_representative_created = False
                status += "REPRESENTATIVE_CREATE_THEN_UPDATE_ERROR "
                handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'new_representative_created':    new_representative_created,
                'representative_updated':        representative_updated,
                'new_representative':            new_representative,
            }
        return results

    def update_representative_row_entry(self, representative_we_vote_id, update_values):
        """
        Update Representative table entry with matching we_vote_id
        :param representative_we_vote_id:
        :param update_values:
        :return:
        """

        success = False
        status = ""
        representative_updated = False
        existing_representative_entry = ''

        try:
            existing_representative_entry = Representative.objects.get(we_vote_id__iexact=
                                                                          representative_we_vote_id)
            values_changed = False

            if existing_representative_entry:
                # found the existing entry, update the values
                if 'ballotpedia_representative_id' in update_values:
                    existing_representative_entry.ballotpedia_representative_id = \
                        convert_to_int(update_values['ballotpedia_representative_id'])
                    values_changed = True
                if 'ballotpedia_representative_name' in update_values:
                    existing_representative_entry.ballotpedia_representative_name = \
                        update_values['ballotpedia_representative_name']
                    values_changed = True
                if 'ballotpedia_representative_url' in update_values:
                    existing_representative_entry.ballotpedia_representative_url = \
                        update_values['ballotpedia_representative_url']
                    values_changed = True
                if 'representative_name' in update_values:
                    existing_representative_entry.representative_name = update_values['representative_name']
                    values_changed = True
                if 'representative_twitter_handle' in update_values:
                    existing_representative_entry.representative_twitter_handle = \
                        update_values['representative_twitter_handle']
                    values_changed = True
                if 'representative_url' in update_values:
                    existing_representative_entry.representative_url = update_values['representative_url']
                    values_changed = True
                if 'office_held_we_vote_id' in update_values:
                    existing_representative_entry.office_held_we_vote_id = \
                        update_values['office_held_we_vote_id']
                    values_changed = True
                if 'office_held_id' in update_values:
                    existing_representative_entry.office_held_id = update_values['office_held_id']
                    values_changed = True
                if 'office_held_name' in update_values:
                    existing_representative_entry.office_held_name = update_values['office_held_name']
                    values_changed = True
                if 'ctcl_uuid' in update_values:
                    existing_representative_entry.ctcl_uuid = update_values['ctcl_uuid']
                    values_changed = True
                if 'facebook_url' in update_values:
                    existing_representative_entry.facebook_url = update_values['facebook_url']
                    values_changed = True
                if 'google_civic_election_id' in update_values:
                    existing_representative_entry.google_civic_election_id = update_values['google_civic_election_id']
                    values_changed = True
                if 'political_party' in update_values:
                    existing_representative_entry.political_party = update_values['political_party']
                    values_changed = True
                if 'politician_id' in update_values:
                    existing_representative_entry.politician_id = update_values['politician_id']
                    values_changed = True
                if 'state_code' in update_values:
                    existing_representative_entry.state_code = update_values['state_code']
                    values_changed = True
                if 'photo_url' in update_values:
                    # check if representative has an existing photo in the Representative table
                    if positive_value_exists(existing_representative_entry.we_vote_hosted_profile_image_url_large) \
                            and positive_value_exists(
                                existing_representative_entry.we_vote_hosted_profile_image_url_medium) \
                            and positive_value_exists(
                                existing_representative_entry.we_vote_hosted_profile_image_url_tiny):
                        save_to_representative_object = False
                    else:
                        save_to_representative_object = True

                    representative_results = self.modify_representative_with_organization_endorsements_image(
                        existing_representative_entry, update_values['photo_url'], save_to_representative_object)
                    if representative_results['success']:
                        values_changed = True
                        representative = representative_results['representative']
                        existing_representative_entry.we_vote_hosted_profile_image_url_large = \
                            representative.we_vote_hosted_profile_image_url_large
                        existing_representative_entry.we_vote_hosted_profile_image_url_medium = \
                            representative.we_vote_hosted_profile_image_url_medium
                        existing_representative_entry.we_vote_hosted_profile_image_url_tiny = \
                            representative.we_vote_hosted_profile_image_url_tiny

                # now go ahead and save this entry (update)
                if values_changed:
                    existing_representative_entry.save()
                    representative_updated = True
                    success = True
                    status = "REPRESENTATIVE_UPDATED"
                else:
                    representative_updated = False
                    success = True
                    status = "REPRESENTATIVE_NOT_UPDATED-NO_CHANGES "
        except Exception as e:
            success = False
            representative_updated = False
            status = "REPRESENTATIVE_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':              success,
                'status':               status,
                'representative_updated':    representative_updated,
                'updated_representative':    existing_representative_entry,
            }
        return results

    def modify_representative_with_organization_endorsements_image(self, representative, representative_photo_url,
                                                                     save_to_representative_object):
        """
        Save profile image url for representative in image table
        This function could be updated to save images from other sources beyond ORGANIZATION_ENDORSEMENTS_IMAGE_NAME
        :param representative:
        :param representative_photo_url:
        :param save_to_representative_object:
        :return:
        """
        status = ''
        success = False
        cache_results = {
            'we_vote_hosted_profile_image_url_large':   None,
            'we_vote_hosted_profile_image_url_medium':  None,
            'we_vote_hosted_profile_image_url_tiny':    None
        }

        from image.controllers import OTHER_SOURCE, cache_master_and_resized_image

        # add https to the url and replace “\/” with “/”
        modified_url_string = representative_photo_url
        temp_url_string = representative_photo_url.lower()
        temp_url_string = temp_url_string.replace("\\", "")
        if "http" not in temp_url_string:
            modified_url_string = "https:{0}".format(temp_url_string)
        # image_source=OTHER_SOURCE is not currently used
        cache_results = cache_master_and_resized_image(representative_id=representative.id,
                                                       representative_we_vote_id=representative.we_vote_id,
                                                       other_source_image_url=modified_url_string,
                                                       other_source=ORGANIZATION_ENDORSEMENTS_IMAGE_NAME,
                                                       image_source=OTHER_SOURCE)
        cached_other_source_image_url_https = cache_results['cached_other_source_image_url_https']
        # We store the original source of the representative photo, even though we don't use this url
        # to display the image
        representative.other_source_url = representative_photo_url
        # Store locally cached link to this image
        representative.other_source_photo_url = cached_other_source_image_url_https

        # save this in representative table only if no image exists for the representative.
        # Do not overwrite existing image
        if positive_value_exists(save_to_representative_object):
            we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
            we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

            try:
                representative.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                representative.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                representative.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                success = True
                status += "MODIFY_REPRESENTATIVE_WITH_ORGANIZATION_ENDORSEMENTS_IMAGE-IMAGE_SAVED"
            except Exception as e:
                status += "MODIFY_REPRESENTATIVE_WITH_ORGANIZATION_ENDORSEMENTS_IMAGE-IMAGE_SAVE_FAILED"
                pass
        results = {
            'success': success,
            'status': status,
            'representative': representative,
        }

        return results

    def count_representatives_for_election(self, google_civic_election_id):
        """
        Return count of representatives found for a given election
        :param google_civic_election_id:
        :return:
        """
        representatives_count = 0
        success = False
        if positive_value_exists(google_civic_election_id):
            try:
                representative_item_queryset = Representative.objects.using('readonly').all()
                representative_item_queryset = representative_item_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
                representatives_count = representative_item_queryset.count()

                status = 'REPRESENTATIVES_ITEMS_FOUND '
                success = True
            except Representative.DoesNotExist:
                # No representative items found. Not a problem.
                status = 'NO_REPRESENTATIVE_ITEMS_FOUND '
                success = True
            except Exception as e:
                handle_exception(e, logger=logger)
                status = 'FAILED retrieve_representative_items_for_election ' \
                         '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
        else:
            status = 'INVALID_GOOGLE_CIVIC_ELECTION_ID'
        results = {
            'success':          success,
            'status':           status,
            'representatives_count': representatives_count
        }
        return results


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

