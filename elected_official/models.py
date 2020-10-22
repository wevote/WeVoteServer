# elected_official/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from elected_office.models import ElectedOffice, ElectedOfficeManager
import re
from wevote_settings.models import fetch_next_we_vote_id_elected_official_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, display_full_name_with_correct_capitalization, \
    extract_title_from_full_name, extract_first_name_from_full_name, extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_suffix_from_full_name, extract_nickname_from_full_name, \
    extract_state_from_ocd_division_id, extract_twitter_handle_from_text_string, \
    positive_value_exists
from image.models import ORGANIZATION_ENDORSEMENTS_IMAGE_NAME

logger = wevote_functions.admin.get_logger(__name__)

# When merging elected_officials, these are the fields we check for figure_out_elected_official_conflict_values
ELECTED_OFFICIAL_UNIQUE_IDENTIFIERS = [
    'ballot_guide_official_statement',
    'ballotpedia_elected_official_id',
    'ballotpedia_elected_official_name',
    'ballotpedia_elected_official_url',
    'ballotpedia_page_title',
    'ballotpedia_photo_url',
    'elected_official_email',
    'elected_official_name',
    'elected_official_phone',
    'elected_official_twitter_handle',
    'elected_official_url',
    'elected_office_id',
    'elected_office_name',
    'elected_office_we_vote_id',
    'ctcl_uuid',
    'facebook_profile_image_url_https',
    'facebook_url',
    'google_civic_elected_official_name',
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


class ElectedOfficialListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Elected Officials
    Note: Extending models.Models creates a useless empty table, we probably want to extend models.Manager here
    """

    def retrieve_all_elected_officials_for_office(self, office_id, office_we_vote_id):
        elected_official_list = []
        elected_official_list_found = False

        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
            results = {
                'success':              True if elected_official_list_found else False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'elected_official_list_found': elected_official_list_found,
                'elected_official_list':       elected_official_list,
            }
            return results

        try:
            elected_official_queryset = ElectedOfficial.objects.all()
            if positive_value_exists(office_id):
                elected_official_queryset = elected_official_queryset.filter(elected_office_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                elected_official_queryset = elected_official_queryset.filter(
                    elected_office_we_vote_id=office_we_vote_id)
            elected_official_queryset = elected_official_queryset.order_by('-twitter_followers_count')
            elected_official_list = elected_official_queryset

            if len(elected_official_list):
                elected_official_list_found = True
                status = 'ELECTED_OFFICIALS_RETRIEVED'
            else:
                status = 'NO_ELECTED_OFFICIALS_RETRIEVED'
        except ElectedOfficial.DoesNotExist:
            # No elected_officials found. Not a problem.
            status = 'NO_ELECTED_OFFICIALS_FOUND_DoesNotExist'
            elected_official_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_elected_officials_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if elected_official_list_found else False,
            'status':                       status,
            'office_id':                    office_id,
            'office_we_vote_id':            office_we_vote_id,
            'elected_official_list_found':  elected_official_list_found,
            'elected_official_list':        elected_official_list,
        }
        return results

    def retrieve_all_elected_officials_for_upcoming_election(self, google_civic_election_id=0, state_code='',
                                                             return_list_of_objects=False):
        elected_official_list_objects = []
        elected_official_list_light = []
        elected_official_list_found = False

        try:
            elected_official_queryset = ElectedOfficial.objects.all()
            if positive_value_exists(google_civic_election_id):
                elected_official_queryset = elected_official_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(state_code):
                elected_official_queryset = elected_official_queryset.filter(state_code__iexact=state_code)
            elected_official_queryset = elected_official_queryset.order_by("elected_official_name")
            if positive_value_exists(google_civic_election_id):
                elected_official_list_objects = elected_official_queryset
            else:
                elected_official_list_objects = elected_official_queryset[:300]

            if len(elected_official_list_objects):
                elected_official_list_found = True
                status = 'ELECTED_OFFICIALS_RETRIEVED'
                success = True
            else:
                status = 'NO_ELECTED_OFFICIALS_RETRIEVED'
                success = True
        except ElectedOfficial.DoesNotExist:
            # No elected_officials found. Not a problem.
            status = 'NO_ELECTED_OFFICIALS_FOUND_DoesNotExist'
            elected_official_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_elected_officials_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        if elected_official_list_found:
            for elected_official in elected_official_list_objects:
                one_elected_official = {
                    'ballot_item_display_name': elected_official.display_elected_official_name(),
                    'elected_official_we_vote_id':     elected_official.we_vote_id,
                    'office_we_vote_id':        elected_official.elected_office_we_vote_id,
                    'measure_we_vote_id':       '',
                }
                elected_official_list_light.append(one_elected_official.copy())

        results = {
            'success':                          success,
            'status':                           status,
            'google_civic_election_id':         google_civic_election_id,
            'elected_official_list_found':      elected_official_list_found,
            'elected_official_list_objects':    elected_official_list_objects if return_list_of_objects else [],
            'elected_official_list_light':      elected_official_list_light,
        }
        return results

    def retrieve_elected_official_count_for_office(self, office_id, office_we_vote_id):
        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status = 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING'
            results = {
                'success':              False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'elected_official_count':      0,
            }
            return results

        try:
            elected_official_queryset = ElectedOfficial.objects.using('readonly').all()
            if positive_value_exists(office_id):
                elected_official_queryset = elected_official_queryset.filter(elected_office_id=office_id)
            elif positive_value_exists(office_we_vote_id):
                elected_official_queryset = elected_official_queryset.filter(
                    elected_office_we_vote_id=office_we_vote_id)
            elected_official_list = elected_official_queryset

            elected_official_count = elected_official_list.count()
            success = True
            status = "ELECTED_OFFICIAL_COUNT_FOUND"
        except ElectedOfficial.DoesNotExist:
            # No elected_officials found. Not a problem.
            status = 'NO_ELECTED_OFFICIALS_FOUND_DoesNotExist'
            elected_official_count = 0
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_elected_officials_for_office ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False
            elected_official_count = 0

        results = {
            'success':              success,
            'status':               status,
            'office_id':            office_id,
            'office_we_vote_id':    office_we_vote_id,
            'elected_official_count':      elected_official_count,
        }
        return results

    def is_automatic_merge_ok(self, elected_official_option1, elected_official_option2):
        automatic_merge_ok = True
        status = ""
        if elected_official_option1.elected_official_name != elected_official_option2.elected_official_name:
            automatic_merge_ok = False
            status += " elected_official_name:"
        elected_official1_twitter_handle = str(elected_official_option1.elected_official_twitter_handle)
        elected_official2_twitter_handle = str(elected_official_option2.elected_official_twitter_handle)
        if elected_official1_twitter_handle.lower() != elected_official2_twitter_handle.lower():
            automatic_merge_ok = False
            status += " elected_official_twitter_handle:"
        if elected_official_option1.elected_official_url != elected_official_option2.elected_official_url:
            automatic_merge_ok = False
            status += " elected_official_url:"

        if not automatic_merge_ok:
            status = "Different: " + status

        results = {
            "status":               status,
            "automatic_merge_ok":   automatic_merge_ok,
        }
        return results

    def do_automatic_merge(self, elected_official_option1, elected_official_option2):
        success = False
        status = "do_automatic_merge NOT IMPLEMENTED YET"

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def find_and_merge_duplicate_elected_officials(self, google_civic_election_id, merge=False, remove=False):
        success = False
        status = "find_and_merge_duplicate_elected_officials NOT IMPLEMENTED YET"

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
        }
        return results

    def retrieve_elected_officials_from_all_elections_list(self):
        """
        This is used by the admin tools to show ElectedOfficials in a drop-down for example
        """
        elected_officials_list_temp = ElectedOfficial.objects.all()
        # Order by elected_official_name.
        # To order by last name we will need to make some guesses in some case about what the last name is.
        elected_officials_list_temp = elected_officials_list_temp.order_by('elected_official_name')[:300]
        return elected_officials_list_temp

    def remove_duplicate_elected_official(self, elected_official_id, google_civic_election_id):
        # TODO DALE We need to delete the positions associated with this elected_official, and convert them to belong
        # to elected official we leave in place.

        success = False
        status = "COULD_NOT_DELETE_DUPLICATE_ELECTED_OFFICIAL"

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def retrieve_possible_duplicate_elected_officials(self, elected_official_name, google_civic_elected_official_name,
                                                      google_civic_election_id, office_we_vote_id,
                                                      politician_we_vote_id,
                                                      elected_official_twitter_handle,
                                                      ballotpedia_elected_official_id, vote_smart_id, maplight_id,
                                                      we_vote_id_from_master=''):
        elected_official_list_objects = []
        filters = []
        elected_official_list_found = False
        ballotpedia_elected_official_id = convert_to_int(ballotpedia_elected_official_id)

        try:
            elected_official_queryset = ElectedOfficial.objects.all()
            elected_official_queryset = elected_official_queryset.filter(
                google_civic_election_id=google_civic_election_id)
            # We don't look for office_we_vote_id because of the chance that locally we are using a
            # different we_vote_id
            # elected_official_queryset = elected_official_queryset.filter(
            # elected_office_we_vote_id__iexact=office_we_vote_id)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                elected_official_queryset = elected_official_queryset.filter(
                    ~Q(we_vote_id__iexact=we_vote_id_from_master))

            # We want to find elected_officials with *any* of these values
            if positive_value_exists(google_civic_elected_official_name):
                # We intentionally use case sensitive matching here
                new_filter = Q(google_civic_elected_official_name__exact=google_civic_elected_official_name)
                filters.append(new_filter)
            elif positive_value_exists(elected_official_name):
                new_filter = Q(elected_official_name__iexact=elected_official_name)
                filters.append(new_filter)

            if positive_value_exists(politician_we_vote_id):
                new_filter = Q(politician_we_vote_id__iexact=politician_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(elected_official_twitter_handle):
                new_filter = Q(elected_official_twitter_handle__iexact=elected_official_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(ballotpedia_elected_official_id):
                new_filter = Q(ballotpedia_elected_official_id=ballotpedia_elected_official_id)
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

                elected_official_queryset = elected_official_queryset.filter(final_filters)

            elected_official_list_objects = elected_official_queryset

            if len(elected_official_list_objects):
                elected_official_list_found = True
                status = 'DUPLICATE_ELECTED_OFFICIALS_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_ELECTED_OFFICIALS_RETRIEVED'
                success = True
        except ElectedOfficial.DoesNotExist:
            # No elected_officials found. Not a problem.
            status = 'NO_DUPLICATE_ELECTED_OFFICIALS_FOUND_DoesNotExist'
            elected_official_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_elected_officials ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'elected_official_list_found':     elected_official_list_found,
            'elected_official_list':           elected_official_list_objects,
        }
        return results

    def retrieve_elected_officials_from_non_unique_identifiers(self, google_civic_election_id, state_code,
                                                               elected_official_twitter_handle, elected_official_name,
                                                               ignore_elected_official_id_list=[]):
        keep_looking_for_duplicates = True
        elected_official = ElectedOfficial()
        elected_official_found = False
        elected_official_list = []
        elected_official_list_found = False
        multiple_entries_found = False
        elected_official_twitter_handle = extract_twitter_handle_from_text_string(elected_official_twitter_handle)
        success = True
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(elected_official_twitter_handle):
            try:
                elected_official_query = ElectedOfficial.objects.all()
                elected_official_query = elected_official_query.filter(
                    elected_official_twitter_handle__iexact=elected_official_twitter_handle,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    elected_official_query = elected_official_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_elected_official_id_list):
                    elected_official_query = elected_official_query.exclude(
                        we_vote_id__in=ignore_elected_official_id_list)

                elected_official_list = list(elected_official_query)
                if len(elected_official_list):
                    # At least one entry exists
                    status += 'BATCH_ROW_ACTION_ELECTED_OFFICIAL_LIST_RETRIEVED '
                    # if a single entry matches, update that entry
                    if len(elected_official_list) == 1:
                        multiple_entries_found = False
                        elected_official = elected_official_list[0]
                        elected_official_found = True
                        keep_looking_for_duplicates = False
                        success = True
                        status += "ELECTED_OFFICIAL_FOUND_BY_TWITTER "
                    else:
                        # more than one entry found
                        elected_official_list_found = True
                        multiple_entries_found = True
                        keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
                        status += "MULTIPLE_TWITTER_MATCHES "
            except ElectedOfficial.DoesNotExist:
                success = True
                status += "BATCH_ROW_ACTION_EXISTING_ELECTED_OFFICIAL_NOT_FOUND "
            except Exception as e:
                status += "BATCH_ROW_ACTION_ELECTED_OFFICIAL_QUERY_FAILED1 "
                keep_looking_for_duplicates = False
        # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(elected_official_name):
            # Search by Elected Official name exact match
            try:
                elected_official_query = ElectedOfficial.objects.all()
                elected_official_query = elected_official_query.filter(
                    elected_official_name__iexact=elected_official_name,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    elected_official_query = elected_official_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_elected_official_id_list):
                    elected_official_query = elected_official_query.exclude(
                        we_vote_id__in=ignore_elected_official_id_list)

                elected_official_list = list(elected_official_query)
                if len(elected_official_list):
                    # entry exists
                    status += 'ELECTED_OFFICIAL_ENTRY_EXISTS '
                    success = True
                    # if a single entry matches, update that entry
                    if len(elected_official_list) == 1:
                        elected_official = elected_official_list[0]
                        elected_official_found = True
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in ElectedOfficial
                        elected_official_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    success = True
                    status += 'ELECTED_OFFICIAL_ENTRY_NOT_FOUND-EXACT '

            except ElectedOfficial.DoesNotExist:
                success = True
                status += "BATCH_ROW_ACTION_ELECTED_OFFICIAL_NOT_FOUND-EXACT_MATCH "
            except Exception as e:
                status += "BATCH_ROW_ACTION_ELECTED_OFFICIAL_QUERY_FAILED2 "

        if keep_looking_for_duplicates and positive_value_exists(elected_official_name):
            # Search for Elected Official(s) that contains the same first and last names
            try:
                elected_official_query = ElectedOfficial.objects.all()
                elected_official_query = elected_official_query.filter(
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    elected_official_query = elected_official_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(elected_official_name)
                elected_official_query = elected_official_query.filter(elected_official_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(elected_official_name)
                elected_official_query = elected_official_query.filter(elected_official_name__icontains=last_name)

                if positive_value_exists(ignore_elected_official_id_list):
                    elected_official_query = elected_official_query.exclude(
                        we_vote_id__in=ignore_elected_official_id_list)

                elected_official_list = list(elected_official_query)
                if len(elected_official_list):
                    # entry exists
                    status += 'ELECTED_OFFICIAL_ENTRY_EXISTS '
                    success = True
                    # if a single entry matches, update that entry
                    if len(elected_official_list) == 1:
                        elected_official = elected_official_list[0]
                        elected_official_found = True
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in ElectedOfficial
                        elected_official_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    status += 'ELECTED_OFFICIAL_ENTRY_NOT_FOUND-FIRST_OR_LAST '
                    success = True
            except ElectedOfficial.DoesNotExist:
                status += "BATCH_ROW_ACTION_ELECTED_OFFICIAL_NOT_FOUND-FIRST_OR_LAST_NAME "
                success = True
            except Exception as e:
                status += "BATCH_ROW_ACTION_ELECTED_OFFICIAL_QUERY_FAILED3 "

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'elected_official_found':          elected_official_found,
            'elected_official':                elected_official,
            'elected_official_list_found':     elected_official_list_found,
            'elected_official_list':           elected_official_list,
            'multiple_entries_found':   multiple_entries_found,
        }
        return results

    def fetch_elected_officials_from_non_unique_identifiers_count(
            self, google_civic_election_id, state_code, elected_official_twitter_handle, elected_official_name,
            ignore_elected_official_id_list=[]):
        keep_looking_for_duplicates = True
        elected_official_twitter_handle = extract_twitter_handle_from_text_string(elected_official_twitter_handle)
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(elected_official_twitter_handle):
            try:
                elected_official_query = ElectedOfficial.objects.all()
                elected_official_query = elected_official_query.filter(
                    elected_official_twitter_handle__iexact=elected_official_twitter_handle,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    elected_official_query = elected_official_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_elected_official_id_list):
                    elected_official_query = elected_official_query.exclude(
                        we_vote_id__in=ignore_elected_official_id_list)

                elected_official_count = elected_official_query.count()
                if positive_value_exists(elected_official_count):
                    return elected_official_count
            except ElectedOfficial.DoesNotExist:
                pass
            except Exception as e:
                keep_looking_for_duplicates = False
                pass
        # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(elected_official_name):
            # Search by Elected Official name exact match
            try:
                elected_official_query = ElectedOfficial.objects.all()
                elected_official_query = elected_official_query.filter(
                    elected_official_name__iexact=elected_official_name,
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    elected_official_query = elected_official_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_elected_official_id_list):
                    elected_official_query = elected_official_query.exclude(
                        we_vote_id__in=ignore_elected_official_id_list)

                elected_official_count = elected_official_query.count()
                if positive_value_exists(elected_official_count):
                    return elected_official_count
            except ElectedOfficial.DoesNotExist:
                status += "BATCH_ROW_ACTION_ELECTED_OFFICIAL_NOT_FOUND "

        if keep_looking_for_duplicates and positive_value_exists(elected_official_name):
            # Search for Elected Official(s) that contains the same first and last names
            try:
                elected_official_query = ElectedOfficial.objects.all()
                elected_official_query = elected_official_query.filter(
                    google_civic_election_id=google_civic_election_id)
                if positive_value_exists(state_code):
                    elected_official_query = elected_official_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(elected_official_name)
                elected_official_query = elected_official_query.filter(elected_official_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(elected_official_name)
                elected_official_query = elected_official_query.filter(elected_official_name__icontains=last_name)

                if positive_value_exists(ignore_elected_official_id_list):
                    elected_official_query = elected_official_query.exclude(
                        we_vote_id__in=ignore_elected_official_id_list)

                elected_official_count = elected_official_query.count()
                if positive_value_exists(elected_official_count):
                    return elected_official_count
            except ElectedOfficial.DoesNotExist:
                status += "BATCH_ROW_ACTION_ELECTED_OFFICIAL_NOT_FOUND "
                success = True

        return 0


class ElectedOfficial(models.Model):
    # This entry is for a person elected into an office. Not the same as a Politician entry, which is the person
    #  whether they are in office or not.
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "electedofficial", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_elected_official_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this person in this position",
        max_length=255, default=None, null=True,
        blank=True, unique=True)
    # The internal We Vote id for the ElectedOffice that this elected official is competing for.
    # During setup we need to allow
    # this to be null.
    elected_office_id = models.CharField(
        verbose_name="elected_office_id id", max_length=255, null=True, blank=True)
    # We want to link the elected official to the elected office with permanent ids so we can export and import
    elected_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the office this elected official is running for", max_length=255,
        default=None, null=True, blank=True, unique=False)
    elected_office_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)
    # politician (internal) link to local We Vote Politician entry. During setup we need to allow this to be null.
    politician_id = models.BigIntegerField(verbose_name="politician unique identifier", null=True, blank=True)
    # The persistent We Vote unique ID of the Politician, so we can export and import into other databases.
    politician_we_vote_id = models.CharField(
        verbose_name="we vote politician id", max_length=255, null=True, blank=True)
    # The elected_official's name.
    elected_official_name = models.CharField(verbose_name="elected official name", max_length=255, null=False,
                                             blank=False)
    # The elected_official's name as passed over by Google Civic.
    # We save this so we can match to this elected official even
    # if we edit the elected_official's name locally.
    google_civic_elected_official_name = models.CharField(
        verbose_name="elected official name exactly as received from google civic",
        max_length=255, null=False, blank=False)
    # The full name of the party the elected_official is a member of.
    political_party = models.CharField(verbose_name="political_party", max_length=255, null=True, blank=True)
    # A URL for a photo of the elected_official.
    photo_url = models.CharField(verbose_name="photoUrl", max_length=255, null=True, blank=True)
    photo_url_from_maplight = models.URLField(
        verbose_name='elected official portrait url of elected official from maplight', blank=True, null=True)
    photo_url_from_vote_smart = models.URLField(
        verbose_name='elected official portrait url of elected official from vote smart', blank=True, null=True)
    # The order the elected official appears on the ballot relative to other elected_officials for this contest.
    order_on_ballot = models.CharField(verbose_name="order on ballot", max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="state this elected official serves", max_length=2, null=True,
                                  blank=True)
    # The URL for the elected_official's campaign web site.
    elected_official_url = models.URLField(
        verbose_name='website url of elected official', max_length=255, blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of elected official', blank=True, null=True)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of profile image from facebook',
                                                       blank=True, null=True)

    twitter_url = models.URLField(verbose_name='twitter url of elected official', blank=True, null=True)
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    elected_official_twitter_handle = models.CharField(
        verbose_name='elected official twitter screen_name', max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="elected official plain text name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="elected official location from twitter", max_length=255, null=True, blank=True)
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

    google_plus_url = models.URLField(verbose_name='google plus url of elected official', blank=True, null=True)
    vote_smart_id = models.CharField(verbose_name="votesmart unique identifier",
                                     max_length=200, null=True, unique=False)
    maplight_id = models.CharField(verbose_name="maplight unique identifier",
                                   max_length=200, null=True, unique=True, blank=True)
    youtube_url = models.URLField(verbose_name='youtube url of elected official', blank=True, null=True)
    # The email address for the elected_official's campaign.
    elected_official_email = models.CharField(verbose_name="elected official email", max_length=255, null=True,
                                              blank=True)
    # The voice phone number for the elected officials office.
    elected_official_phone = models.CharField(verbose_name="elected official phone", max_length=255, null=True,
                                              blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', max_length=255, blank=True, null=True)
    linkedin_url = models.CharField(
        verbose_name="linkedin url of elected_official", max_length=255, null=True, blank=True)
    linkedin_photo_url = models.URLField(verbose_name='url of linkedin logo', max_length=255, blank=True, null=True)

    # other_source_url is the location (ex/ http://mywebsite.com/elected_official1.html) where we find
    # the other_source_photo_url OR the original url of the photo before we store it locally
    other_source_url = models.CharField(
        verbose_name="other source url of elected_official", max_length=255, null=True, blank=True)
    other_source_photo_url = models.URLField(
        verbose_name='url of other source image', max_length=255, blank=True, null=True)

    ballotpedia_elected_official_id = models.PositiveIntegerField(
        verbose_name="ballotpedia integer id", null=True, blank=True)
    # The elected_official's name as passed over by Ballotpedia
    ballotpedia_elected_official_name = models.CharField(
        verbose_name="elected official name exactly as received from ballotpedia", max_length=255, null=True,
        blank=True)
    ballotpedia_elected_official_url = models.URLField(
        verbose_name='url of elected official on ballotpedia', max_length=255, blank=True, null=True)
    # This is just the characters in the Ballotpedia URL
    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(
        verbose_name='url of ballotpedia logo', max_length=255, blank=True, null=True)

    # CTCL elected official data fields
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)

    def elected_office(self):
        try:
            elected_office = ElectedOffice.objects.get(id=self.elected_office_id)
        except ElectedOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            return
        except ElectedOffice.DoesNotExist:
            return
        return elected_office

    def elected_official_photo_url(self):
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
        if positive_value_exists(self.elected_official_twitter_handle):
            return self.elected_official_twitter_handle
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
        if self.elected_official_twitter_handle:
            return "https://twitter.com/{twitter_handle}".format(twitter_handle=self.elected_official_twitter_handle)
        else:
            return ''

    def get_elected_official_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            # Pull this from ocdDivisionId
            if positive_value_exists(self.ocd_division_id):
                ocd_division_id = self.ocd_division_id
                return extract_state_from_ocd_division_id(ocd_division_id)
            else:
                return ''

    def display_elected_official_name(self):
        full_name = self.elected_official_name
        if full_name.isupper():
            full_name_corrected_capitalization = display_full_name_with_correct_capitalization(full_name)
            return full_name_corrected_capitalization
        return full_name

    def extract_title(self):
        full_name = self.display_elected_official_name()
        return extract_title_from_full_name(full_name)

    def extract_first_name(self):
        full_name = self.display_elected_official_name()
        return extract_first_name_from_full_name(full_name)

    def extract_middle_name(self):
        full_name = self.display_elected_official_name()
        return extract_middle_name_from_full_name(full_name)

    def extract_last_name(self):
        full_name = self.display_elected_official_name()
        return extract_last_name_from_full_name(full_name)

    def extract_suffix(self):
        full_name = self.display_elected_official_name()
        return extract_suffix_from_full_name(full_name)

    def extract_nickname(self):
        full_name = self.display_elected_official_name()
        return extract_nickname_from_full_name(full_name)

    def political_party_display(self):
        return elected_official_party_display(self.political_party)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_elected_official_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "electedofficial" = tells us this is a unique id for a ElectedOfficial
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}electedofficial{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        if self.maplight_id == "":  # We want this to be unique IF there is a value, and otherwise "None"
            self.maplight_id = None
        super(ElectedOfficial, self).save(*args, **kwargs)


def fetch_elected_official_count_for_elected_office(elected_office_id=0, elected_office_we_vote_id=''):
    elected_official_list = ElectedOfficialListManager()
    results = elected_official_list.retrieve_elected_official_count_for_office(elected_office_id,
                                                                               elected_office_we_vote_id)
    return results['elected_official_count']


# See also 'convert_to_political_party_constant' in we_vote_functions/functions.py
def elected_official_party_display(raw_political_party):
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


class ElectedOfficialManager(models.Model):
    # Extending models.Models creates a useless empty table, we probably want to extend models.Manager here

    def __unicode__(self):
        return "ElectedOfficialManager"

    def retrieve_elected_official_from_id(self, elected_official_id):
        elected_official_manager = ElectedOfficialManager()
        return elected_official_manager.retrieve_elected_official(elected_official_id)

    def retrieve_elected_official_from_we_vote_id(self, we_vote_id):
        elected_official_id = 0
        elected_official_manager = ElectedOfficialManager()
        return elected_official_manager.retrieve_elected_official(elected_official_id, we_vote_id)

    def fetch_elected_official_id_from_we_vote_id(self, we_vote_id):
        elected_official_id = 0
        elected_official_manager = ElectedOfficialManager()
        results = elected_official_manager.retrieve_elected_official(elected_official_id, we_vote_id)
        if results['success']:
            return results['elected_official_id']
        return 0

    def fetch_elected_official_we_vote_id_from_id(self, elected_official_id):
        we_vote_id = ''
        elected_official_manager = ElectedOfficialManager()
        results = elected_official_manager.retrieve_elected_official(elected_official_id, we_vote_id)
        if results['success']:
            return results['elected_official_we_vote_id']
        return ''

    def fetch_google_civic_elected_official_name_from_we_vote_id(self, we_vote_id):
        elected_official_id = 0
        elected_official_manager = ElectedOfficialManager()
        results = elected_official_manager.retrieve_elected_official(elected_official_id, we_vote_id)
        if results['success']:
            elected_official = results['elected_official']
            return elected_official.google_civic_elected_official_name
        return 0

    def retrieve_elected_official_from_maplight_id(self, elected_official_maplight_id):
        elected_official_id = 0
        we_vote_id = ''
        elected_official_manager = ElectedOfficialManager()
        return elected_official_manager.retrieve_elected_official(
            elected_official_id, we_vote_id, elected_official_maplight_id)

    def retrieve_elected_official_from_vote_smart_id(self, elected_official_vote_smart_id):
        elected_official_id = 0
        we_vote_id = ''
        elected_official_maplight_id = ''
        elected_official_name = ''
        elected_official_manager = ElectedOfficialManager()
        return elected_official_manager.retrieve_elected_official(
            elected_official_id, we_vote_id, elected_official_maplight_id, elected_official_name,
            elected_official_vote_smart_id)

    def retrieve_elected_official_from_ballotpedia_elected_official_id(self, ballotpedia_elected_official_id):
        elected_official_id = 0
        we_vote_id = ''
        elected_official_maplight_id = ''
        elected_official_name = ''
        elected_official_vote_smart_id = 0
        return self.retrieve_elected_official(
            elected_official_id, we_vote_id, elected_official_maplight_id, elected_official_name,
            elected_official_vote_smart_id, ballotpedia_elected_official_id)

    def retrieve_elected_official_from_elected_official_name(self, elected_official_name):
        elected_official_id = 0
        we_vote_id = ''
        elected_official_maplight_id = ''
        elected_official_manager = ElectedOfficialManager()

        results = elected_official_manager.retrieve_elected_official(
            elected_official_id, we_vote_id, elected_official_maplight_id, elected_official_name)
        if results['success']:
            return results

        # Try to modify the elected official name, and search again
        # MapLight for example will pass in "Ronald  Gold" for example
        elected_official_name_try2 = elected_official_name.replace('  ', ' ')
        results = elected_official_manager.retrieve_elected_official(
            elected_official_id, we_vote_id, elected_official_maplight_id, elected_official_name_try2)
        if results['success']:
            return results

        # MapLight also passes in "Kamela D Harris" for example, and Google Civic uses "Kamela D. Harris"
        elected_official_name_try3 = mimic_google_civic_initials(elected_official_name)
        if elected_official_name_try3 != elected_official_name:
            results = elected_official_manager.retrieve_elected_official(
                elected_official_id, we_vote_id, elected_official_maplight_id, elected_official_name_try3)
            if results['success']:
                return results

        # Otherwise return failed results
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_elected_official(
            self, elected_official_id, elected_official_we_vote_id=None, elected_official_maplight_id=None,
            elected_official_name=None, elected_official_vote_smart_id=None, ballotpedia_elected_official_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        elected_official_on_stage = ElectedOfficial()

        try:
            if positive_value_exists(elected_official_id):
                elected_official_on_stage = ElectedOfficial.objects.get(id=elected_official_id)
                elected_official_id = elected_official_on_stage.id
                elected_official_we_vote_id = elected_official_on_stage.we_vote_id
                elected_official_found = True
                status = "RETRIEVE_ELECTED_OFFICIAL_FOUND_BY_ID"
            elif positive_value_exists(elected_official_we_vote_id):
                elected_official_on_stage = ElectedOfficial.objects.get(we_vote_id=elected_official_we_vote_id)
                elected_official_id = elected_official_on_stage.id
                elected_official_we_vote_id = elected_official_on_stage.we_vote_id
                elected_official_found = True
                status = "RETRIEVE_ELECTED_OFFICIAL_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(elected_official_maplight_id):
                elected_official_on_stage = ElectedOfficial.objects.get(maplight_id=elected_official_maplight_id)
                elected_official_id = elected_official_on_stage.id
                elected_official_we_vote_id = elected_official_on_stage.we_vote_id
                elected_official_found = True
                status = "RETRIEVE_ELECTED_OFFICIAL_FOUND_BY_MAPLIGHT_ID"
            elif positive_value_exists(elected_official_vote_smart_id):
                elected_official_on_stage = ElectedOfficial.objects.get(vote_smart_id=elected_official_vote_smart_id)
                elected_official_id = elected_official_on_stage.id
                elected_official_we_vote_id = elected_official_on_stage.we_vote_id
                elected_official_found = True
                status = "RETRIEVE_ELECTED_OFFICIAL_FOUND_BY_VOTE_SMART_ID"
            elif positive_value_exists(elected_official_name):
                elected_official_on_stage = ElectedOfficial.objects.get(elected_official_name=elected_official_name)
                elected_official_id = elected_official_on_stage.id
                elected_official_we_vote_id = elected_official_on_stage.we_vote_id
                elected_official_found = True
                status = "RETRIEVE_ELECTED_OFFICIAL_FOUND_BY_NAME"
            elif positive_value_exists(ballotpedia_elected_official_id):
                ballotpedia_elected_official_id_integer = convert_to_int(ballotpedia_elected_official_id)
                elected_official_on_stage = ElectedOfficial.objects.get(
                    ballotpedia_elected_official_id=ballotpedia_elected_official_id_integer)
                elected_official_id = elected_official_on_stage.id
                elected_official_we_vote_id = elected_official_on_stage.we_vote_id
                elected_official_found = True
                status = "RETRIEVE_ELECTED_OFFICIAL_FOUND_BY_BALLOTPEDIA_ELECTED_OFFICIAL_ID"
            else:
                elected_official_found = False
                status = "RETRIEVE_ELECTED_OFFICIAL_SEARCH_INDEX_MISSING"
        except ElectedOfficial.MultipleObjectsReturned as e:
            elected_official_found = False
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_ELECTED_OFFICIAL_MULTIPLE_OBJECTS_RETURNED"
        except ElectedOfficial.DoesNotExist:
            elected_official_found = False
            exception_does_not_exist = True
            status = "RETRIEVE_ELECTED_OFFICIAL_NOT_FOUND"
        except Exception as e:
            elected_official_found = False
            status = "RETRIEVE_ELECTED_OFFICIAL_NOT_FOUND_EXCEPTION"

        results = {
            'success':                      True if convert_to_int(elected_official_id) > 0 else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'elected_official_found':       elected_official_found,
            'elected_official_id':          convert_to_int(elected_official_id),
            'elected_official_we_vote_id':  elected_official_we_vote_id,
            'elected_official':             elected_official_on_stage,
        }
        return results

    def retrieve_elected_officials_are_not_duplicates(self, elected_official1_we_vote_id, elected_official2_we_vote_id,
                                                      read_only=True):
        elected_officials_are_not_duplicates = ElectedOfficialsAreNotDuplicates()
        # Note that the direction of the friendship does not matter
        try:
            if positive_value_exists(read_only):
                elected_officials_are_not_duplicates = ElectedOfficialsAreNotDuplicates.objects.using('readonly').get(
                    elected_official1_we_vote_id__iexact=elected_official1_we_vote_id,
                    elected_official2_we_vote_id__iexact=elected_official2_we_vote_id,
                )
            else:
                elected_officials_are_not_duplicates = ElectedOfficialsAreNotDuplicates.objects.get(
                    elected_official1_we_vote_id__iexact=elected_official1_we_vote_id,
                    elected_official2_we_vote_id__iexact=elected_official2_we_vote_id,
                )
            elected_officials_are_not_duplicates_found = True
            success = True
            status = "ELECTED_OFFICIALS_NOT_DUPLICATES_UPDATED_OR_CREATED1 "
        except ElectedOfficialsAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            elected_officials_are_not_duplicates_found = False
            status = 'NO_ELECTED_OFFICIALS_NOT_DUPLICATES_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            elected_officials_are_not_duplicates_found = False
            elected_officials_are_not_duplicates = ElectedOfficialsAreNotDuplicates()
            success = False
            status = "ELECTED_OFFICIALS_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED1 "

        if not elected_officials_are_not_duplicates_found and success:
            try:
                if positive_value_exists(read_only):
                    elected_officials_are_not_duplicates = \
                        ElectedOfficialsAreNotDuplicates.objects.using('readonly').get(
                            elected_official1_we_vote_id__iexact=elected_official2_we_vote_id,
                            elected_official2_we_vote_id__iexact=elected_official1_we_vote_id,
                        )
                else:
                    elected_officials_are_not_duplicates = \
                        ElectedOfficialsAreNotDuplicates.objects.get(
                            elected_official1_we_vote_id__iexact=elected_official2_we_vote_id,
                            elected_official2_we_vote_id__iexact=elected_official1_we_vote_id
                        )
                elected_officials_are_not_duplicates_found = True
                success = True
                status = "ELECTED_OFFICIALS_NOT_DUPLICATES_UPDATED_OR_CREATED2 "
            except ElectedOfficialsAreNotDuplicates.DoesNotExist:
                # No data found. Try again below
                success = True
                elected_officials_are_not_duplicates_found = False
                status = 'NO_ELECTED_OFFICIALS_NOT_DUPLICATES_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                elected_officials_are_not_duplicates_found = False
                elected_officials_are_not_duplicates = ElectedOfficialsAreNotDuplicates()
                success = False
                status = "ELECTED_OFFICIALS_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED2 "

        results = {
            'success':                                      success,
            'status':                                       status,
            'elected_officials_are_not_duplicates_found':   elected_officials_are_not_duplicates_found,
            'elected_officials_are_not_duplicates':         elected_officials_are_not_duplicates,
        }
        return results

    def retrieve_elected_officials_are_not_duplicates_list(self, elected_official_we_vote_id, read_only=True):
        """
        Get a list of other elected_official_we_vote_id's that are not duplicates
        :param elected_official_we_vote_id:
        :param read_only:
        :return:
        """
        # Note that the direction of the linkage does not matter
        elected_officials_are_not_duplicates_list1 = []
        elected_officials_are_not_duplicates_list2 = []
        try:
            if positive_value_exists(read_only):
                elected_officials_are_not_duplicates_list_query = \
                    ElectedOfficialsAreNotDuplicates.objects.using('readonly').filter(
                        elected_official1_we_vote_id__iexact=elected_official_we_vote_id,
                    )
            else:
                elected_officials_are_not_duplicates_list_query = \
                    ElectedOfficialsAreNotDuplicates.objects.filter(
                        elected_official1_we_vote_id__iexact=elected_official_we_vote_id)
            elected_officials_are_not_duplicates_list1 = list(elected_officials_are_not_duplicates_list_query)
            success = True
            status = "ELECTED_OFFICIALS_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except ElectedOfficialsAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status = 'NO_ELECTED_OFFICIALS_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status = "ELECTED_OFFICIALS_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1 "

        if success:
            try:
                if positive_value_exists(read_only):
                    elected_officials_are_not_duplicates_list_query = \
                        ElectedOfficialsAreNotDuplicates.objects.using('readonly').filter(
                            elected_official2_we_vote_id__iexact=elected_official_we_vote_id,
                        )
                else:
                    elected_officials_are_not_duplicates_list_query = \
                        ElectedOfficialsAreNotDuplicates.objects.filter(
                            elected_official2_we_vote_id__iexact=elected_official_we_vote_id)
                elected_officials_are_not_duplicates_list2 = list(elected_officials_are_not_duplicates_list_query)
                success = True
                status = "ELECTED_OFFICIALS_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except ElectedOfficialsAreNotDuplicates.DoesNotExist:
                success = True
                status = 'NO_ELECTED_OFFICIALS_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status = "ELECTED_OFFICIALS_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2 "

        elected_officials_are_not_duplicates_list = elected_officials_are_not_duplicates_list1 + \
            elected_officials_are_not_duplicates_list2
        elected_officials_are_not_duplicates_list_found = positive_value_exists(len(
            elected_officials_are_not_duplicates_list))
        elected_officials_are_not_duplicates_list_we_vote_ids = []
        for one_entry in elected_officials_are_not_duplicates_list:
            if one_entry.elected_official1_we_vote_id != elected_official_we_vote_id:
                elected_officials_are_not_duplicates_list_we_vote_ids.append(one_entry.elected_official1_we_vote_id)
            elif one_entry.elected_official2_we_vote_id != elected_official_we_vote_id:
                elected_officials_are_not_duplicates_list_we_vote_ids.append(one_entry.elected_official2_we_vote_id)
        results = {
            'success':                                          success,
            'status':                                           status,
            'elected_officials_are_not_duplicates_list_found':  elected_officials_are_not_duplicates_list_found,
            'elected_officials_are_not_duplicates_list':        elected_officials_are_not_duplicates_list,
            'elected_officials_are_not_duplicates_list_we_vote_ids':
                elected_officials_are_not_duplicates_list_we_vote_ids,
        }
        return results

    def fetch_elected_officials_are_not_duplicates_list_we_vote_ids(self, elected_official_we_vote_id):
        results = self.retrieve_elected_officials_are_not_duplicates_list(elected_official_we_vote_id)
        return results['elected_officials_are_not_duplicates_list_we_vote_ids']

    def update_or_create_elected_official(self,  elected_office_name, elected_official_name,
                                          google_civic_elected_official_name, political_party, photo_url,
                                          ocd_division_id, state_code, elected_official_url,
                                          facebook_url, twitter_url, google_plus_url, youtube_url,
                                          elected_official_phone ):

        """
        Either update or create a elected_official entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_elected_official_created = False
        elected_official_on_stage = ElectedOfficial()
        status = ""

        if not positive_value_exists(ocd_division_id):
            success = False
            status += 'MISSING_OCD_DIVISION_ID '
        elif not positive_value_exists(google_civic_elected_official_name):
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTED_OFFICIAL_NAME '
        else:
            try:
                # If here we are using permanent public identifier elected_office_we_vote_id
                elected_official_on_stage, new_elected_official_created = \
                    ElectedOfficial.objects.update_or_create(
                        elected_office_name=elected_office_name,
                        elected_official_name=elected_official_name,
                        google_civic_elected_official_name=google_civic_elected_official_name,
                        ocd_division_id=ocd_division_id,
                        state_code=state_code,
                        political_party=political_party,
                        photo_url=photo_url,
                        elected_official_url=elected_official_url,
                        facebook_url=facebook_url,
                        twitter_url=twitter_url,
                        google_plus_url=google_plus_url,
                        youtube_url=youtube_url,
                        elected_official_phone=elected_official_phone)
                success = True
                status += "ELECTED_OFFICIAL_CAMPAIGN_UPDATED_OR_CREATED "
            except ElectedOfficial.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_ELECTED_OFFICIAL_CAMPAIGNS_FOUND_BY_GOOGLE_CIVIC_ELECTED_OFFICIAL_NAME '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_ELECTED_OFFICIAL_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        # else:
        #     # Given we might have the office listed by google_civic_office_name
        #     # OR office_name, we need to check both before we try to create a new entry
        #     elected_official_found = False
        #     try:
        #         elected_official_on_stage = ElectedOfficial.objects.get(
        #             google_civic_election_id__exact=google_civic_election_id,
        #             google_civic_elected_official_name__iexact=google_civic_elected_official_name
        #         )
        #         elected_official_found = True
        #         success = True
        #         status += 'CONTEST_OFFICE_SAVED '
        #     except ElectedOfficial.MultipleObjectsReturned as e:
        #         success = False
        #         status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_GOOGLE_CIVIC_OFFICE_NAME '
        #         exception_multiple_object_returned = True
        #     except ElectedOfficial.DoesNotExist:
        #         exception_does_not_exist = True
        #         status += "RETRIEVE_OFFICE_NOT_FOUND_BY_GOOGLE_CIVIC_ELECTED_OFFICIAL_NAME "
        #     except Exception as e:
        #         status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME ' \
        #                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #
        #     if not elected_official_found and not exception_multiple_object_returned:
        #         # Try to find record based on office_name (instead of google_civic_office_name)
        #         try:
        #             elected_official_on_stage = ElectedOfficial.objects.get(
        #                 google_civic_election_id__exact=google_civic_election_id,
        #                 elected_official_name__iexact=google_civic_elected_official_name
        #             )
        #             elected_official_found = True
        #             success = True
        #             status += 'ELECTED_OFFICIAL_RETRIEVED_FROM_ELECTED_OFFICIAL_NAME '
        #         except ElectedOfficial.MultipleObjectsReturned as e:
        #             success = False
        #             status += 'MULTIPLE_MATCHING_ELECTED_OFFICIALS_FOUND_BY_ELECTED_OFFICIAL_NAME '
        #             exception_multiple_object_returned = True
        #         except ElectedOfficial.DoesNotExist:
        #             exception_does_not_exist = True
        #             status += "RETRIEVE_ELECTED_OFFICIAL_NOT_FOUND_BY_ELECTED_OFFICIAL_NAME "
        #         except Exception as e:
        #             status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
        #                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #             success = False
        #
        #     if exception_multiple_object_returned:
        #         # We can't proceed because there is an error with the data
        #         success = False
        #     elif elected_official_found:
        #         # Update record
        #         # Note: When we decide to start updating elected_official_name elsewhere within We Vote, we should stop
        #         #  updating elected_official_name via subsequent Google Civic imports
        #         try:
        #             new_elected_official_created = False
        #             elected_official_updated = False
        #             elected_official_has_changes = False
        #             for key, value in updated_elected_official_values.items():
        #                 if hasattr(elected_official_on_stage, key):
        #                     elected_official_has_changes = True
        #                     setattr(elected_official_on_stage, key, value)
        #             if elected_official_has_changes and positive_value_exists(elected_official_on_stage.we_vote_id):
        #                 elected_official_on_stage.save()
        #                 elected_official_updated = True
        #             if elected_official_updated:
        #                 success = True
        #                 status += "ELECTED_OFFICIAL_UPDATED "
        #             else:
        #                 success = False
        #                 status += "ELECTED_OFFICIAL_NOT_UPDATED "
        #         except Exception as e:
        #             status += 'FAILED_TO_UPDATE_ELECTED_OFFICIAL ' \
        #                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #             success = False
        #     else:
        #         # Create record
        #         try:
        #             new_elected_official_created = False
        #             elected_official_on_stage = ElectedOfficial.objects.create(
        #                 google_civic_election_id=google_civic_election_id,
        #                 ocd_division_id=ocd_division_id,
        #                 elected_office_id=elected_office_id,
        #                 elected_office_we_vote_id=elected_office_we_vote_id,
        #                 google_civic_elected_official_name=google_civic_elected_official_name)
        #             if positive_value_exists(elected_official_on_stage.id):
        #                 for key, value in updated_elected_official_values.items():
        #                     if hasattr(elected_official_on_stage, key):
        #                         setattr(elected_official_on_stage, key, value)
        #                 elected_official_on_stage.save()
        #                 new_elected_official_created = True
        #             if positive_value_exists(new_elected_official_created):
        #                 status += "ELECTED_OFFICIAL_CREATED "
        #                 success = True
        #             else:
        #                 status += "ELECTED_OFFICIAL_NOT_CREATED "
        #                 success = False
        #
        #         except Exception as e:
        #             status += 'FAILED_TO_CREATE_ELECTED_OFFICIAL ' \
        #                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        #             success = False

        results = {
            'success':                      success,
            'status':                       status,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'new_elected_official_created': new_elected_official_created,
            'elected_official':             elected_official_on_stage,
        }
        return results

    def update_or_create_elected_officials_are_not_duplicates(self, elected_official1_we_vote_id,
                                                              elected_official2_we_vote_id):
        """
        Either update or create a elected_official entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_elected_officials_are_not_duplicates_created = False
        elected_officials_are_not_duplicates = ElectedOfficialsAreNotDuplicates()
        status = ""

        if positive_value_exists(elected_official1_we_vote_id) and positive_value_exists(elected_official2_we_vote_id):
            try:
                updated_values = {
                    'elected_official1_we_vote_id':    elected_official1_we_vote_id,
                    'elected_official2_we_vote_id':    elected_official2_we_vote_id,
                }
                elected_officials_are_not_duplicates, new_elected_officials_are_not_duplicates_created = \
                    ElectedOfficialsAreNotDuplicates.objects.update_or_create(
                        elected_official1_we_vote_id__exact=elected_official1_we_vote_id,
                        elected_official2_we_vote_id__iexact=elected_official2_we_vote_id,
                        defaults=updated_values)
                success = True
                status += "ELECTED_OFFICIALS_ARE_NOT_DUPLICATES_UPDATED_OR_CREATED "
            except ElectedOfficialsAreNotDuplicates.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_ELECTED_OFFICIALS_ARE_NOT_DUPLICATES_FOUND_BY_ELECTED_OFFICIAL_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'EXCEPTION_UPDATE_OR_CREATE_ELECTED_OFFICIALS_ARE_NOT_DUPLICATES ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                                      success,
            'status':                                       status,
            'MultipleObjectsReturned':                      exception_multiple_object_returned,
            'new_elected_officials_are_not_duplicates_created':    new_elected_officials_are_not_duplicates_created,
            'elected_officials_are_not_duplicates':                elected_officials_are_not_duplicates,
        }
        return results

    def update_elected_official_social_media(self, elected_official, elected_official_twitter_handle=False,
                                      elected_official_facebook=False):
        """
        Update a elected official entry with general social media data. If a value is passed in False
        it means "Do not update"
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        success = False
        status = "ENTERING_UPDATE_ELECTED_OFFICIAL_SOCIAL_MEDIA"
        values_changed = False

        elected_official_twitter_handle = elected_official_twitter_handle.strip() if elected_official_twitter_handle \
            else False
        elected_official_facebook = elected_official_facebook.strip() if elected_official_facebook else False
        # elected_official_image = elected_official_image.strip() if elected_official_image else False

        if elected_official:
            if elected_official_twitter_handle:
                if elected_official_twitter_handle != elected_official.elected_official_twitter_handle:
                    elected_official.elected_official_twitter_handle = elected_official_twitter_handle
                    values_changed = True
            if elected_official_facebook:
                if elected_official_facebook != elected_official.facebook_url:
                    elected_official.facebook_url = elected_official_facebook
                    values_changed = True

            if values_changed:
                elected_official.save()
                success = True
                status = "SAVED_ELECTED_OFFICIAL_SOCIAL_MEDIA"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_ELECTED_OFFICIAL_SOCIAL_MEDIA"

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'elected_official':         elected_official,
        }
        return results

    def update_elected_official_twitter_details(self, elected_official, twitter_json,
                                                cached_twitter_profile_image_url_https,
                                                cached_twitter_profile_background_image_url_https,
                                                cached_twitter_profile_banner_url_https,
                                                we_vote_hosted_profile_image_url_large,
                                                we_vote_hosted_profile_image_url_medium,
                                                we_vote_hosted_profile_image_url_tiny):
        """
        Update a elected official entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_ELECTED_OFFICIAL_TWITTER_DETAILS"
        values_changed = False

        if elected_official:
            if 'id' in twitter_json and positive_value_exists(twitter_json['id']):
                if convert_to_int(twitter_json['id']) != elected_official.twitter_user_id:
                    elected_official.twitter_user_id = convert_to_int(twitter_json['id'])
                    values_changed = True
            if 'screen_name' in twitter_json and positive_value_exists(twitter_json['screen_name']):
                if twitter_json['screen_name'] != elected_official.elected_official_twitter_handle:
                    elected_official.elected_official_twitter_handle = twitter_json['screen_name']
                    values_changed = True
            if 'name' in twitter_json and positive_value_exists(twitter_json['name']):
                if twitter_json['name'] != elected_official.twitter_name:
                    elected_official.twitter_name = twitter_json['name']
                    values_changed = True
            if 'followers_count' in twitter_json and positive_value_exists(twitter_json['followers_count']):
                if convert_to_int(twitter_json['followers_count']) != elected_official.twitter_followers_count:
                    elected_official.twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                elected_official.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_image_url_https']):
                if twitter_json['profile_image_url_https'] != elected_official.twitter_profile_image_url_https:
                    elected_official.twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                elected_official.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            elif ('profile_banner_url' in twitter_json) and positive_value_exists(twitter_json['profile_banner_url']):
                if twitter_json['profile_banner_url'] != elected_official.twitter_profile_banner_url_https:
                    elected_official.twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                elected_official.twitter_profile_background_image_url_https = \
                    cached_twitter_profile_background_image_url_https
                values_changed = True
            elif 'profile_background_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_background_image_url_https']):
                if twitter_json['profile_background_image_url_https'] != \
                        elected_official.twitter_profile_background_image_url_https:
                    elected_official.twitter_profile_background_image_url_https = \
                        twitter_json['profile_background_image_url_https']
                    values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                elected_official.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                elected_official.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                elected_official.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_json:  # No value required to update description (so we can clear out)
                if twitter_json['description'] != elected_official.twitter_description:
                    elected_official.twitter_description = twitter_json['description']
                    values_changed = True
            if 'location' in twitter_json:  # No value required to update location (so we can clear out)
                if twitter_json['location'] != elected_official.twitter_location:
                    elected_official.twitter_location = twitter_json['location']
                    values_changed = True

            if values_changed:
                elected_official.save()
                success = True
                status = "SAVED_ELECTED_OFFICIAL_TWITTER_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_ELECTED_OFFICIAL_TWITTER_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'elected_official':    elected_official,
        }
        return results

    def reset_elected_official_image_details(self, elected_official, twitter_profile_image_url_https,
                                             twitter_profile_background_image_url_https,
                                             twitter_profile_banner_url_https):
        """
        Reset an elected official entry with original image details from we vote image.
        """
        success = False
        status = "ENTERING_RESET_ELECTED_OFFICIAL_IMAGE_DETAILS"

        if elected_official:
            if positive_value_exists(twitter_profile_image_url_https):
                elected_official.twitter_profile_image_url_https = twitter_profile_image_url_https
            if positive_value_exists(twitter_profile_background_image_url_https):
                elected_official.twitter_profile_background_image_url_https = twitter_profile_background_image_url_https
            if positive_value_exists(twitter_profile_banner_url_https):
                elected_official.twitter_profile_banner_url_https = twitter_profile_banner_url_https
            elected_official.we_vote_hosted_profile_image_url_large = ''
            elected_official.we_vote_hosted_profile_image_url_medium = ''
            elected_official.we_vote_hosted_profile_image_url_tiny = ''
            elected_official.save()
            success = True
            status = "RESET_ELECTED_OFFICIAL_IMAGE_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'elected_official':    elected_official,
        }
        return results

    def clear_elected_official_twitter_details(self, elected_official):
        """
        Update an elected official entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_ELECTED_OFFICIAL_TWITTER_DETAILS"

        if elected_official:
            elected_official.twitter_user_id = 0
            # We leave the handle in place
            # elected_official.elected_official_twitter_handle = ""
            elected_official.twitter_name = ''
            elected_official.twitter_followers_count = 0
            elected_official.twitter_profile_image_url_https = ''
            elected_official.we_vote_hosted_profile_image_url_large = ''
            elected_official.we_vote_hosted_profile_image_url_medium = ''
            elected_official.we_vote_hosted_profile_image_url_tiny = ''
            elected_official.twitter_description = ''
            elected_official.twitter_location = ''
            elected_official.save()
            success = True
            status = "CLEARED_ELECTED_OFFICIAL_TWITTER_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'elected_official':    elected_official,
        }
        return results

    def refresh_cached_elected_official_office_info(self, elected_official_object):
        """
        The elected official tables cache information from other tables. This function reaches out to the source tables
        and copies over the latest information to the elected official table.
        :param elected_official_object:
        :return:
        """
        values_changed = False
        office_found = False
        elected_office_manager = ElectedOfficeManager()
        results = {}
        if positive_value_exists(elected_official_object.elected_office_id):
            results = elected_office_manager.retrieve_elected_office_from_id(elected_official_object.elected_office_id)
            office_found = results['elected_office_found']
        elif positive_value_exists(elected_official_object.elected_office_we_vote_id):
            results = elected_office_manager.retrieve_elected_office_from_we_vote_id(
                elected_official_object.elected_office_we_vote_id)
            office_found = results['elected_office_found']

        if office_found:
            office_object = results['elected_office']
            elected_official_object.elected_office_id = office_object.id
            elected_official_object.elected_office_we_vote_id = office_object.we_vote_id
            elected_official_object.elected_office_name = office_object.office_name
            values_changed = True

        if values_changed:
            elected_official_object.save()

        return elected_official_object

    def create_elected_official_row_entry(self, update_values):
        """
        Create ElectedOfficial table entry with ElectedOfficial details
        :param update_values:
        :return:
        """
        success = False
        status = ""
        elected_official_updated = False
        new_elected_official_created = False
        new_elected_official = ''

        # Variables we accept
        elected_official_name = update_values['elected_official_name'] if 'elected_official_name' in update_values else ''
        elected_office_we_vote_id = update_values['elected_office_we_vote_id'] \
            if 'elected_office_we_vote_id' in update_values else False
        elected_office_id = update_values['elected_office_id'] \
            if 'elected_office_id' in update_values else False
        elected_office_name = update_values['elected_office_name'] \
            if 'elected_office_name' in update_values else False
        elected_official_party_name = update_values['political_party'] if 'political_party' in update_values else ''
        ctcl_uuid = update_values['ctcl_uuid'] if 'ctcl_uuid' in update_values else ''
        google_civic_election_id = update_values['google_civic_election_id'] \
            if 'google_civic_election_id' in update_values else ''
        state_code = update_values['state_code'] if 'state_code' in update_values else ''
        elected_official_twitter_handle = update_values['elected_official_twitter_handle'] \
            if 'elected_official_twitter_handle' in update_values else ''
        elected_official_url = update_values['elected_official_url'] \
            if 'elected_official_url' in update_values else ''
        facebook_url = update_values['facebook_url'] \
            if 'facebook_url' in update_values else ''
        photo_url = update_values['photo_url'] \
            if 'photo_url' in update_values else ''

        if not positive_value_exists(elected_official_name) or not positive_value_exists(elected_office_we_vote_id) \
                or not positive_value_exists(elected_office_id) \
                or not positive_value_exists(google_civic_election_id) or not positive_value_exists(state_code):
            # If we don't have the minimum values required to create a elected_official, then don't proceed
            status += "CREATE_ELECTED_OFFICIAL_ROW "
            results = {
                    'success':                  success,
                    'status':                   status,
                    'new_elected_official_created':    new_elected_official_created,
                    'elected_official_updated':        elected_official_updated,
                    'new_elected_official':            new_elected_official,
                }
            return results

        try:
            new_elected_official = ElectedOfficial.objects.create(
                elected_official_name=elected_official_name,
                elected_office_we_vote_id=elected_office_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                state_code=state_code)
            if new_elected_official:
                success = True
                status += "ELECTED_OFFICIAL_CREATED "
                new_elected_official_created = True
            else:
                success = False
                status += "ELECTED_OFFICIAL_CREATE_FAILED "
        except Exception as e:
            success = False
            new_elected_official_created = False
            status += "ELECTED_OFFICIAL_CREATE_ERROR "
            handle_exception(e, logger=logger, exception_message=status)

        if new_elected_official_created:
            try:
                new_elected_official.elected_office_id = elected_office_id
                new_elected_official.elected_office_name = elected_office_name
                new_elected_official.political_party = elected_official_party_name
                new_elected_official.ctcl_uuid = ctcl_uuid
                new_elected_official.elected_official_twitter_handle = elected_official_twitter_handle
                new_elected_official.elected_official_url = elected_official_url
                new_elected_official.facebook_url = facebook_url
                new_elected_official.photo_url = photo_url
                if new_elected_official.photo_url:
                    elected_official_results = \
                        self.modify_elected_official_with_organization_endorsements_image(new_elected_official,
                                                                                   photo_url, True)
                    if elected_official_results['success']:
                        elected_official = elected_official_results['elected_official']
                        new_elected_official.we_vote_hosted_profile_image_url_large = \
                            elected_official.we_vote_hosted_profile_image_url_large
                        new_elected_official.we_vote_hosted_profile_image_url_medium = \
                            elected_official.we_vote_hosted_profile_image_url_medium
                        new_elected_official.we_vote_hosted_profile_image_url_tiny = \
                            elected_official.we_vote_hosted_profile_image_url_tiny
                new_elected_official.save()

                status += "ELECTED_OFFICIAL_CREATE_THEN_UPDATE_SUCCESS "
            except Exception as e:
                success = False
                new_elected_official_created = False
                status += "ELECTED_OFFICIAL_CREATE_THEN_UPDATE_ERROR "
                handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':                  success,
                'status':                   status,
                'new_elected_official_created':    new_elected_official_created,
                'elected_official_updated':        elected_official_updated,
                'new_elected_official':            new_elected_official,
            }
        return results

    def update_elected_official_row_entry(self, elected_official_we_vote_id, update_values):
        """
        Update ElectedOfficial table entry with matching we_vote_id
        :param elected_official_we_vote_id:
        :param update_values:
        :return:
        """

        success = False
        status = ""
        elected_official_updated = False
        existing_elected_official_entry = ''

        try:
            existing_elected_official_entry = ElectedOfficial.objects.get(we_vote_id__iexact=
                                                                          elected_official_we_vote_id)
            values_changed = False

            if existing_elected_official_entry:
                # found the existing entry, update the values
                if 'ballotpedia_elected_official_id' in update_values:
                    existing_elected_official_entry.ballotpedia_elected_official_id = \
                        convert_to_int(update_values['ballotpedia_elected_official_id'])
                    values_changed = True
                if 'ballotpedia_elected_official_name' in update_values:
                    existing_elected_official_entry.ballotpedia_elected_official_name = \
                        update_values['ballotpedia_elected_official_name']
                    values_changed = True
                if 'ballotpedia_elected_official_url' in update_values:
                    existing_elected_official_entry.ballotpedia_elected_official_url = \
                        update_values['ballotpedia_elected_official_url']
                    values_changed = True
                if 'elected_official_name' in update_values:
                    existing_elected_official_entry.elected_official_name = update_values['elected_official_name']
                    values_changed = True
                if 'elected_official_twitter_handle' in update_values:
                    existing_elected_official_entry.elected_official_twitter_handle = \
                        update_values['elected_official_twitter_handle']
                    values_changed = True
                if 'elected_official_url' in update_values:
                    existing_elected_official_entry.elected_official_url = update_values['elected_official_url']
                    values_changed = True
                if 'elected_office_we_vote_id' in update_values:
                    existing_elected_official_entry.elected_office_we_vote_id = \
                        update_values['elected_office_we_vote_id']
                    values_changed = True
                if 'elected_office_id' in update_values:
                    existing_elected_official_entry.elected_office_id = update_values['elected_office_id']
                    values_changed = True
                if 'elected_office_name' in update_values:
                    existing_elected_official_entry.elected_office_name = update_values['elected_office_name']
                    values_changed = True
                if 'ctcl_uuid' in update_values:
                    existing_elected_official_entry.ctcl_uuid = update_values['ctcl_uuid']
                    values_changed = True
                if 'facebook_url' in update_values:
                    existing_elected_official_entry.facebook_url = update_values['facebook_url']
                    values_changed = True
                if 'google_civic_election_id' in update_values:
                    existing_elected_official_entry.google_civic_election_id = update_values['google_civic_election_id']
                    values_changed = True
                if 'political_party' in update_values:
                    existing_elected_official_entry.political_party = update_values['political_party']
                    values_changed = True
                if 'politician_id' in update_values:
                    existing_elected_official_entry.politician_id = update_values['politician_id']
                    values_changed = True
                if 'state_code' in update_values:
                    existing_elected_official_entry.state_code = update_values['state_code']
                    values_changed = True
                if 'photo_url' in update_values:
                    # check if elected official has an existing photo in the ElectedOfficial table
                    if positive_value_exists(existing_elected_official_entry.we_vote_hosted_profile_image_url_large) \
                            and positive_value_exists(
                                existing_elected_official_entry.we_vote_hosted_profile_image_url_medium) \
                            and positive_value_exists(
                                existing_elected_official_entry.we_vote_hosted_profile_image_url_tiny):
                        save_to_elected_official_object = False
                    else:
                        save_to_elected_official_object = True

                    elected_official_results = self.modify_elected_official_with_organization_endorsements_image(
                        existing_elected_official_entry, update_values['photo_url'], save_to_elected_official_object)
                    if elected_official_results['success']:
                        values_changed = True
                        elected_official = elected_official_results['elected_official']
                        existing_elected_official_entry.we_vote_hosted_profile_image_url_large = \
                            elected_official.we_vote_hosted_profile_image_url_large
                        existing_elected_official_entry.we_vote_hosted_profile_image_url_medium = \
                            elected_official.we_vote_hosted_profile_image_url_medium
                        existing_elected_official_entry.we_vote_hosted_profile_image_url_tiny = \
                            elected_official.we_vote_hosted_profile_image_url_tiny

                # now go ahead and save this entry (update)
                if values_changed:
                    existing_elected_official_entry.save()
                    elected_official_updated = True
                    success = True
                    status = "ELECTED_OFFICIAL_UPDATED"
                else:
                    elected_official_updated = False
                    success = True
                    status = "ELECTED_OFFICIAL_NOT_UPDATED-NO_CHANGES "
        except Exception as e:
            success = False
            elected_official_updated = False
            status = "ELECTED_OFFICIAL_RETRIEVE_ERROR"
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':              success,
                'status':               status,
                'elected_official_updated':    elected_official_updated,
                'updated_elected_official':    existing_elected_official_entry,
            }
        return results

    def modify_elected_official_with_organization_endorsements_image(self, elected_official, elected_official_photo_url,
                                                                     save_to_elected_official_object):
        """
        Save profile image url for elected official in image table
        This function could be updated to save images from other sources beyond ORGANIZATION_ENDORSEMENTS_IMAGE_NAME
        :param elected_official:
        :param elected_official_photo_url:
        :param save_to_elected_official_object:
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
        modified_url_string = elected_official_photo_url
        temp_url_string = elected_official_photo_url.lower()
        temp_url_string = temp_url_string.replace("\\", "")
        if "http" not in temp_url_string:
            modified_url_string = "https:{0}".format(temp_url_string)
        # image_source=OTHER_SOURCE is not currently used
        cache_results = cache_master_and_resized_image(elected_official_id=elected_official.id,
                                                       elected_official_we_vote_id=elected_official.we_vote_id,
                                                       other_source_image_url=modified_url_string,
                                                       other_source=ORGANIZATION_ENDORSEMENTS_IMAGE_NAME,
                                                       image_source=OTHER_SOURCE)
        cached_other_source_image_url_https = cache_results['cached_other_source_image_url_https']
        # We store the original source of the elected official photo, even though we don't use this url
        # to display the image
        elected_official.other_source_url = elected_official_photo_url
        # Store locally cached link to this image
        elected_official.other_source_photo_url = cached_other_source_image_url_https

        # save this in elected official table only if no image exists for the elected_official.
        # Do not overwrite existing image
        if positive_value_exists(save_to_elected_official_object):
            we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
            we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

            try:
                elected_official.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                elected_official.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                elected_official.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                success = True
                status += "MODIFY_ELECTED_OFFICIAL_WITH_ORGANIZATION_ENDORSEMENTS_IMAGE-IMAGE_SAVED"
            except Exception as e:
                status += "MODIFY_ELECTED_OFFICIAL_WITH_ORGANIZATION_ENDORSEMENTS_IMAGE-IMAGE_SAVE_FAILED"
                pass
        results = {
            'success': success,
            'status': status,
            'elected_official': elected_official,
        }

        return results

    def count_elected_officials_for_election(self, google_civic_election_id):
        """
        Return count of elected_officials found for a given election
        :param google_civic_election_id:
        :return:
        """
        elected_officials_count = 0
        success = False
        if positive_value_exists(google_civic_election_id):
            try:
                elected_official_item_queryset = ElectedOfficial.objects.all()
                elected_official_item_queryset = elected_official_item_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
                elected_officials_count = elected_official_item_queryset.count()

                status = 'ELECTED_OFFICIALS_ITEMS_FOUND '
                success = True
            except ElectedOfficial.DoesNotExist:
                # No elected official items found. Not a problem.
                status = 'NO_ELECTED_OFFICIAL_ITEMS_FOUND '
                success = True
            except Exception as e:
                handle_exception(e, logger=logger)
                status = 'FAILED retrieve_elected_official_items_for_election ' \
                         '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
        else:
            status = 'INVALID_GOOGLE_CIVIC_ELECTION_ID'
        results = {
            'success':          success,
            'status':           status,
            'elected_officials_count': elected_officials_count
        }
        return results


class ElectedOfficialsAreNotDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two elected_officials as NOT duplicates
    """
    elected_official1_we_vote_id = models.CharField(
        verbose_name="first elected official we are tracking", max_length=255, null=True, unique=False)
    elected_official2_we_vote_id = models.CharField(
        verbose_name="second elected official we are tracking", max_length=255, null=True, unique=False)

    def fetch_other_elected_official_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.elected_official1_we_vote_id:
            return self.elected_official2_we_vote_id
        elif one_we_vote_id == self.elected_official2_we_vote_id:
            return self.elected_official1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""

