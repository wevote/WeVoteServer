# candidate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from election.models import Election, ElectionManager
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from office.models import ContestOffice, ContestOfficeManager
import re
from wevote_settings.models import fetch_next_we_vote_id_candidate_campaign_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import add_period_to_middle_name_initial, add_period_to_name_prefix_and_suffix, \
    convert_to_int, \
    display_full_name_with_correct_capitalization, \
    extract_title_from_full_name, extract_first_name_from_full_name, extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, extract_suffix_from_full_name, extract_nickname_from_full_name, \
    extract_state_from_ocd_division_id, extract_twitter_handle_from_text_string, \
    positive_value_exists, remove_period_from_middle_name_initial, remove_period_from_name_prefix_and_suffix
from image.models import ORGANIZATION_ENDORSEMENTS_IMAGE_NAME

logger = wevote_functions.admin.get_logger(__name__)

# When merging candidates, these are the fields we check for figure_out_candidate_conflict_values
CANDIDATE_UNIQUE_IDENTIFIERS = [
    'ballot_guide_official_statement',
    'ballotpedia_candidate_id',
    'ballotpedia_candidate_name',
    'ballotpedia_candidate_summary',
    'ballotpedia_candidate_url',
    'ballotpedia_election_id',
    'ballotpedia_image_id',
    'ballotpedia_office_id',
    'ballotpedia_person_id',
    'ballotpedia_page_title',
    'ballotpedia_photo_url',
    'ballotpedia_race_id',
    'birth_day_text',
    'candidate_email',
    'candidate_gender',
    'candidate_is_incumbent',
    'candidate_is_top_ticket',
    'candidate_participation_status',
    'candidate_name',
    'candidate_phone',
    'candidate_twitter_handle',
    'candidate_url',
    'candidate_contact_form_url',
    'contest_office_id',
    'contest_office_we_vote_id',
    'crowdpac_candidate_id',
    'ctcl_uuid',
    'facebook_profile_image_url_https',
    'facebook_url',
    'google_civic_election_id',
    'google_plus_url',
    'linkedin_url',
    'linkedin_photo_url',
    'maplight_id',
    'ocd_division_id',
    'order_on_ballot',
    'other_source_photo_url',
    'other_source_url',
    'party',
    'photo_url',
    'photo_url_from_ctcl',
    'photo_url_from_maplight',
    'photo_url_from_vote_smart',
    'photo_url_from_vote_usa',
    'politician_id',
    'politician_we_vote_id',
    'profile_image_type_currently_active',
    'state_code',
    'twitter_location',
    'twitter_name',
    'twitter_profile_background_image_url_https',
    'twitter_profile_banner_url_https',
    'twitter_profile_image_url_https',
    'twitter_url',
    'twitter_user_id',
    'vote_smart_id',
    'vote_usa_office_id',
    'vote_usa_politician_id',
    'vote_usa_profile_image_url_https',
    'we_vote_hosted_profile_facebook_image_url_large',
    'we_vote_hosted_profile_facebook_image_url_medium',
    'we_vote_hosted_profile_facebook_image_url_tiny',
    'we_vote_hosted_profile_image_url_large',
    'we_vote_hosted_profile_image_url_medium',
    'we_vote_hosted_profile_image_url_tiny',
    'we_vote_hosted_profile_twitter_image_url_large',
    'we_vote_hosted_profile_twitter_image_url_medium',
    'we_vote_hosted_profile_twitter_image_url_tiny',
    'we_vote_hosted_profile_uploaded_image_url_large',
    'we_vote_hosted_profile_uploaded_image_url_medium',
    'we_vote_hosted_profile_uploaded_image_url_tiny',
    'we_vote_hosted_profile_vote_usa_image_url_large',
    'we_vote_hosted_profile_vote_usa_image_url_medium',
    'we_vote_hosted_profile_vote_usa_image_url_tiny',
    'wikipedia_page_title',
    'wikipedia_photo_url',
    'youtube_url',
]

PROFILE_IMAGE_TYPE_FACEBOOK = 'FACEBOOK'
PROFILE_IMAGE_TYPE_TWITTER = 'TWITTER'
PROFILE_IMAGE_TYPE_UNKNOWN = 'UNKNOWN'
PROFILE_IMAGE_TYPE_UPLOADED = 'UPLOADED'
PROFILE_IMAGE_TYPE_VOTE_USA = 'VOTE_USA'
PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES = (
    (PROFILE_IMAGE_TYPE_FACEBOOK, 'Facebook'),
    (PROFILE_IMAGE_TYPE_TWITTER, 'Twitter'),
    (PROFILE_IMAGE_TYPE_UNKNOWN, 'Unknown'),
    (PROFILE_IMAGE_TYPE_UPLOADED, 'Uploaded'),
    (PROFILE_IMAGE_TYPE_VOTE_USA, 'Vote-USA'),
)


class CandidateListManager(models.Manager):
    """
    This is a class to make it easy to retrieve lists of Candidates
    """

    def retrieve_all_candidates_for_office(self, office_id=0, office_we_vote_id='', read_only=False):
        candidate_list = []
        candidate_list_found = False
        candidate_we_vote_id_list = []
        status = ""
        success = True

        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status += 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING '
            results = {
                'success':              False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'candidate_list_found': candidate_list_found,
                'candidate_list':       candidate_list,
                'candidate_we_vote_id_list': candidate_we_vote_id_list,
            }
            return results

        candidate_manager = CandidateManager()
        contest_manager = ContestOfficeManager()
        if positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            office_we_vote_id = contest_manager.fetch_contest_office_we_vote_id_from_id(office_id)

        link_results = \
            candidate_manager.retrieve_candidate_to_office_link(contest_office_we_vote_id=office_we_vote_id)
        if not positive_value_exists(link_results['success']):
            status += link_results['status']
            success = False
            results = {
                'success': success,
                'status': status,
                'office_id': office_id,
                'office_we_vote_id': office_we_vote_id,
                'candidate_list_found': candidate_list_found,
                'candidate_list': candidate_list,
                'candidate_we_vote_id_list': candidate_we_vote_id_list,
            }
            return results
        candidate_to_office_link_list = link_results['candidate_to_office_link_list']
        candidate_we_vote_id_list = []
        for one_link in candidate_to_office_link_list:
            if positive_value_exists(one_link.candidate_we_vote_id):
                candidate_we_vote_id_list.append(one_link.candidate_we_vote_id)
        try:
            if read_only:
                candidate_query = CandidateCampaign.objects.using('readonly').all()
            else:
                candidate_query = CandidateCampaign.objects.all()
            candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            candidate_query = candidate_query.exclude(do_not_display_on_ballot=True)
            candidate_query = candidate_query.order_by('-twitter_followers_count')
            candidate_list = candidate_query

            if len(candidate_list):
                candidate_list_found = True
                status += 'RETRIEVE_ALL_CANDIDATES_FOR_OFFICE-CANDIDATES_RETRIEVED '
            else:
                status += 'RETRIEVE_ALL_CANDIDATES_FOR_OFFICE-NO_CANDIDATES_RETRIEVED '
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'RETRIEVE_ALL_CANDIDATES_FOR_OFFICE-NO_CANDIDATES_FOUND_DoesNotExist '
            candidate_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_candidates_for_office ' + str(e) + ' '
            success = False

        for one_candidate in candidate_list:
            candidate_we_vote_id_list.append(one_candidate.we_vote_id)

        results = {
            'success':              success,
            'status':               status,
            'office_id':            office_id,
            'office_we_vote_id':    office_we_vote_id,
            'candidate_list_found': candidate_list_found,
            'candidate_list':       candidate_list,
            'candidate_we_vote_id_list': candidate_we_vote_id_list,
        }
        return results

    def retrieve_all_candidates_for_upcoming_election(
            self,
            google_civic_election_id_list=[],
            state_code='',
            search_string=False,
            return_list_of_objects=False):
        candidate_list_objects = []
        candidate_list_light = []
        candidate_list_found = False
        status = ""
        if positive_value_exists(search_string):
            try:
                search_words = search_string.split()
            except Exception as e:
                status += "SEARCH_STRING_INVALID "
                search_words = []
        else:
            search_words = []

        results = self.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list,
            limit_to_this_state_code=state_code)
        if not positive_value_exists(results['success']):
            status += results['status']
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']
        office_we_vote_id_list_by_candidate_we_vote_id = results['office_we_vote_id_list_by_candidate_we_vote_id']

        try:
            candidate_query = CandidateCampaign.objects.all()
            if positive_value_exists(google_civic_election_id_list) and len(google_civic_election_id_list):
                candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            if positive_value_exists(state_code):
                candidate_query = candidate_query.filter(state_code__iexact=state_code)
            if positive_value_exists(search_string):
                # This is an "OR" search for each term, but an "AND" search across all search_words
                for search_word in search_words:
                    filters = []

                    # We want to find candidates with *any* of these values
                    new_filter = Q(ballotpedia_candidate_name__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(candidate_name__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(candidate_twitter_handle__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(contest_office_name__icontains=search_word)
                    filters.append(new_filter)
                    new_filter = Q(twitter_name__icontains=search_word)
                    filters.append(new_filter)

                    # Add the first query
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    # Add as new filter for "AND"
                    candidate_query = candidate_query.filter(final_filters)
            candidate_query = candidate_query.order_by("candidate_name")
            if positive_value_exists(google_civic_election_id_list) and len(google_civic_election_id_list):
                candidate_list_objects = list(candidate_query)
            else:
                candidate_list_objects = candidate_query[:300]

            if len(candidate_list_objects):
                candidate_list_found = True
                status += 'CANDIDATES_RETRIEVED '
                success = True
            else:
                status += 'NO_CANDIDATES_RETRIEVED '
                success = True
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_CANDIDATES_FOUND_DoesNotExist '
            candidate_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_candidates_for_upcoming_election ' + str(e) + ' '
            success = False

        if candidate_list_found:
            for candidate in candidate_list_objects:
                one_candidate = {
                    'ballot_item_display_name': candidate.display_candidate_name(),
                    'candidate_we_vote_id':     candidate.we_vote_id,
                    'office_we_vote_id':
                        office_we_vote_id_list_by_candidate_we_vote_id[candidate.we_vote_id],
                    'measure_we_vote_id':       '',
                }
                candidate_list_light.append(one_candidate.copy())

        results = {
            'success':                          success,
            'status':                           status,
            'google_civic_election_id_list':    google_civic_election_id_list,
            'candidate_list_found':             candidate_list_found,
            'candidate_list_objects':           candidate_list_objects if return_list_of_objects else [],
            'candidate_list_light':             candidate_list_light,
        }
        return results

    def retrieve_all_offices_for_candidate(self, candidate_id=0, candidate_we_vote_id='', read_only=False):
        office_list = []
        office_list_found = False
        office_we_vote_id_list = []
        status = ""
        success = True

        if not positive_value_exists(candidate_id) and not positive_value_exists(candidate_we_vote_id):
            status += 'VALID_CANDIDATE_ID_AND_CANDIDATE_WE_VOTE_ID_MISSING '
            results = {
                'success':                  False,
                'status':                   status,
                'candidate_id':             candidate_id,
                'candidate_we_vote_id':     candidate_we_vote_id,
                'office_list_found':        office_list_found,
                'office_list':              office_list,
                'office_we_vote_id_list':   office_we_vote_id_list,
            }
            return results

        candidate_manager = CandidateManager()
        if positive_value_exists(candidate_id) and not positive_value_exists(candidate_we_vote_id):
            candidate_we_vote_id = candidate_manager.fetch_candidate_we_vote_id_from_id(candidate_id)

        link_results = \
            candidate_manager.retrieve_candidate_to_office_link(candidate_we_vote_id=candidate_we_vote_id)
        if not positive_value_exists(link_results['success']):
            status += link_results['status']
            success = False
            results = {
                'success':                  success,
                'status':                   status,
                'candidate_id':             candidate_id,
                'candidate_we_vote_id':     candidate_we_vote_id,
                'office_list_found':        office_list_found,
                'office_list':              office_list,
                'office_we_vote_id_list':   office_we_vote_id_list,
            }
            return results
        candidate_to_office_link_list = link_results['candidate_to_office_link_list']
        for one_link in candidate_to_office_link_list:
            if positive_value_exists(one_link.contest_office_we_vote_id):
                office_we_vote_id_list.append(one_link.contest_office_we_vote_id)
        try:
            if read_only:
                office_query = ContestOffice.objects.using('readonly').all()
            else:
                office_query = ContestOffice.objects.all()
            office_query = office_query.filter(we_vote_id__in=office_we_vote_id_list)
            office_list = list(office_query)

            if len(office_list):
                office_list_found = True
                status += 'RETRIEVE_ALL_OFFICES_FOR_CANDIDATE-OFFICES_RETRIEVED '
            else:
                status += 'RETRIEVE_ALL_OFFICES_FOR_CANDIDATE-NO_OFFICES_RETRIEVED '
        except ContestOffice.DoesNotExist:
            # No offices found. Not a problem.
            status += 'RETRIEVE_ALL_OFFICES_FOR_CANDIDATE-NO_OFFICES_FOUND_DoesNotExist '
            office_list = []
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_offices_for_candidate ' + str(e) + ' '
            success = False

        for one_office in office_list:
            office_we_vote_id_list.append(one_office.we_vote_id)

        results = {
            'success':                  success,
            'status':                   status,
            'candidate_id':             candidate_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'office_list_found':        office_list_found,
            'office_list':              office_list,
            'office_we_vote_id_list':   office_we_vote_id_list,
        }
        return results

    def retrieve_candidates_for_specific_elections(self, google_civic_election_id_list=[],
                                                   limit_to_this_state_code="",
                                                   return_list_of_objects=False,
                                                   super_light_candidate_list=False):
        """
        This function is needed for our scraping tools.
        :param google_civic_election_id_list:
        :param limit_to_this_state_code:
        :param return_list_of_objects:
        :param super_light_candidate_list:
        :return:
        """
        status = ""
        candidate_list_objects = []
        candidate_list_light = []
        candidate_list_found = False

        if not positive_value_exists(google_civic_election_id_list) or not len(google_civic_election_id_list):
            success = False
            status += "LIST_OF_ELECTIONS_MISSING "
            results = {
                'success': success,
                'status': status,
                'candidate_list_found': candidate_list_found,
                'candidate_list_objects': [],
                'candidate_list_light': [],
            }
            return results

        try:
            results = self.retrieve_candidate_we_vote_id_list_from_election_list(
                google_civic_election_id_list=google_civic_election_id_list,
                limit_to_this_state_code=limit_to_this_state_code)
            if not positive_value_exists(results['success']):
                status += results['status']
                success = False
            else:
                candidate_we_vote_id_list = results['candidate_we_vote_id_list']

                candidate_query = CandidateCampaign.objects.using('readonly').all()
                candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
                if positive_value_exists(limit_to_this_state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=limit_to_this_state_code)
                candidate_list_objects = list(candidate_query)

                if len(candidate_list_objects):
                    candidate_list_found = True
                    status += 'CANDIDATES_RETRIEVED '
                    success = True
                else:
                    status += 'NO_CANDIDATES_RETRIEVED '
                    success = True
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_CANDIDATES_FOUND_DoesNotExist '
            candidate_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED-retrieve_candidates_for_specific_elections: ' + str(e) + ' '
            success = False

        if candidate_list_found:
            for candidate in candidate_list_objects:
                if positive_value_exists(super_light_candidate_list):
                    one_candidate = {
                        'name':         candidate.display_candidate_name(),
                        'we_vote_id':   candidate.we_vote_id,
                    }
                    alternate_names = candidate.display_alternate_names_list()
                    if len(alternate_names):
                        one_candidate['alternate_names'] = alternate_names
                else:
                    one_candidate = {
                        'ballot_item_display_name':     candidate.display_candidate_name(),
                        'alternate_names':              candidate.display_alternate_names_list(),
                        'ballot_item_website':          candidate.candidate_url,
                        'candidate_contact_form_url':   candidate.candidate_contact_form_url,
                        'candidate_we_vote_id':         candidate.we_vote_id,
                        'measure_we_vote_id':           '',
                        'more_info_url':                '',
                    }
                candidate_list_light.append(one_candidate)

        results = {
            'success':                  success,
            'status':                   status,
            'candidate_list_found':     candidate_list_found,
            'candidate_list_objects':   candidate_list_objects if return_list_of_objects else [],
            'candidate_list_light':     candidate_list_light,
        }
        return results

    def retrieve_candidate_count_for_office(self, office_id=0, office_we_vote_id=''):
        status = ""
        if not positive_value_exists(office_id) and not positive_value_exists(office_we_vote_id):
            status += 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING '
            results = {
                'success':              False,
                'status':               status,
                'candidate_count':      0,
            }
            return results

        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_all_candidates_for_office(
            office_id=office_id, office_we_vote_id=office_we_vote_id)
        if not positive_value_exists(results['success']):
            status += 'RETRIEVE_CANDIDATE_COUNT_FOR_OFFICE_FAILED '
            status += results['status']
            results = {
                'success':              False,
                'status':               status,
                'office_id':            office_id,
                'office_we_vote_id':    office_we_vote_id,
                'candidate_count':      0,
            }
            return results
        candidate_we_vote_id_list = []
        candidate_list = results['candidate_list']
        for one_candidate in candidate_list:
            candidate_we_vote_id_list.append(one_candidate.we_vote_id)
        try:
            candidate_query = CandidateCampaign.objects.using('readonly').all()
            candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            candidate_count = candidate_query.count()
            success = True
            status += "CANDIDATE_COUNT_FOUND "
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_CANDIDATES_FOUND_DoesNotExist '
            candidate_count = 0
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED retrieve_all_candidates_for_office ' + str(e) + ' '
            success = False
            candidate_count = 0

        results = {
            'success':              success,
            'status':               status,
            'candidate_count':      candidate_count,
        }
        return results

    def retrieve_candidate_count_for_election_and_state(self, google_civic_election_id_list=[], state_code=''):
        status = ''
        if not positive_value_exists(google_civic_election_id_list) and not positive_value_exists(state_code):
            status += 'VALID_ELECTION_ID_AND_STATE_CODE_MISSING '
            results = {
                'success':                          False,
                'status':                           status,
                'google_civic_election_id_list':    google_civic_election_id_list,
                'state_code':                       state_code,
                'candidate_count':                  0,
            }
            return results

        try:
            results = self.retrieve_candidate_we_vote_id_list_from_election_list(
                google_civic_election_id_list=google_civic_election_id_list,
                limit_to_this_state_code=state_code)
            if not positive_value_exists(results['success']):
                candidate_count = 0
                status += results['status']
                success = False
            else:
                candidate_we_vote_id_list = results['candidate_we_vote_id_list']

                candidate_query = CandidateCampaign.objects.using('readonly').all()
                candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)
    
                candidate_count = candidate_query.count()
                success = True
                status += "CANDIDATE_COUNT_FOUND "
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_CANDIDATES_FOUND_DoesNotExist '
            candidate_count = 0
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED RETRIEVE_CANDIDATE_COUNT ' + str(e) + ' '
            success = False
            candidate_count = 0

        results = {
            'success':                          success,
            'status':                           status,
            'google_civic_election_id_list':    google_civic_election_id_list,
            'state_code':                       state_code,
            'candidate_count':                  candidate_count,
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
        if candidate_option1.candidate_contact_form_url != candidate_option2.candidate_contact_form_url:
            automatic_merge_ok = False
            status += " candidate_contact_form_url:"

        if not automatic_merge_ok:
            status += "Different: " + status

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

    def retrieve_candidates_from_all_elections_list(self):
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
                                               google_civic_candidate_name2, google_civic_candidate_name3,
                                               google_civic_election_id, office_we_vote_id,
                                               politician_we_vote_id,
                                               candidate_twitter_handle,
                                               ballotpedia_candidate_id, vote_smart_id, maplight_id,
                                               we_vote_id_from_master=''):
        """
        retrieve_possible_duplicate_candidates is used primarily to avoid duplicate candidate imports.
        :param candidate_name:
        :param google_civic_candidate_name:
        :param google_civic_candidate_name2:
        :param google_civic_candidate_name3:
        :param google_civic_election_id:
        :param office_we_vote_id:
        :param politician_we_vote_id:
        :param candidate_twitter_handle:
        :param ballotpedia_candidate_id:
        :param vote_smart_id:
        :param maplight_id:
        :param we_vote_id_from_master:
        :return:
        """
        candidate_list_objects = []
        filters = []
        candidate_list_found = False
        ballotpedia_candidate_id = convert_to_int(ballotpedia_candidate_id)
        status = ""
        office_manager = ContestOfficeManager()

        try:
            candidate_query = CandidateCampaign.objects.all()
            google_civic_election_id_list = [convert_to_int(google_civic_election_id)]

            results = self.retrieve_candidate_we_vote_id_list_from_election_list(
                google_civic_election_id_list=google_civic_election_id_list)
            if not positive_value_exists(results['success']):
                status += results['status']
            candidate_we_vote_id_list = results['candidate_we_vote_id_list']

            candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                candidate_query = candidate_query.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            # We want to find candidates with *any* of these values
            if positive_value_exists(google_civic_candidate_name):
                # We intentionally use case sensitive matching here
                new_filter = Q(google_civic_candidate_name__exact=google_civic_candidate_name)
                filters.append(new_filter)
                new_filter = Q(google_civic_candidate_name2__exact=google_civic_candidate_name)
                filters.append(new_filter)
                new_filter = Q(google_civic_candidate_name3__exact=google_civic_candidate_name)
                filters.append(new_filter)

                # Since Google Civic doesn't provide a unique identifier, and sometimes returns initials with
                # a period and sometimes without, we may need to try again
                name_changed = False
                google_civic_candidate_name_modified = ""
                # If an initial exists in the name (ex/ " A "), then search for the name
                # with a period added (ex/ " A. ")
                add_results = add_period_to_middle_name_initial(google_civic_candidate_name)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_middle_name_initial(google_civic_candidate_name)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name_modified = add_results['modified_name']
                if name_changed and positive_value_exists(google_civic_candidate_name_modified):
                    new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name_modified)
                    filters.append(new_filter)

                # Deal with prefix and suffix
                name_changed = False
                google_civic_candidate_name_modified = ""
                # If an prefix or suffix exists in the name (ex/ " JR"), then search for the name
                # with a period added (ex/ " JR.")
                add_results = add_period_to_name_prefix_and_suffix(google_civic_candidate_name)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_name_prefix_and_suffix(google_civic_candidate_name)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name_modified = add_results['modified_name']
                if name_changed and positive_value_exists(google_civic_candidate_name_modified):
                    new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name_modified)
                    filters.append(new_filter)

            if positive_value_exists(google_civic_candidate_name2):
                new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name2)
                filters.append(new_filter)
                new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name2)
                filters.append(new_filter)
                new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name2)
                filters.append(new_filter)

                # Since Google Civic doesn't provide a unique identifier, and sometimes returns initials with
                # a period and sometimes without, we may need to try again
                name_changed = False
                google_civic_candidate_name2_modified = ""
                # If an initial exists in the name (ex/ " A "), then search for the name
                # with a period added (ex/ " A. ")
                add_results = add_period_to_middle_name_initial(google_civic_candidate_name2)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name2_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_middle_name_initial(google_civic_candidate_name2)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name2_modified = add_results['modified_name']
                if name_changed and positive_value_exists(google_civic_candidate_name2_modified):
                    new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name2_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name2_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name2_modified)
                    filters.append(new_filter)

                # Deal with prefix and suffix
                name_changed = False
                google_civic_candidate_name2_modified = ""
                # If an prefix or suffix exists in the name (ex/ " JR"), then search for the name
                # with a period added (ex/ " JR.")
                add_results = add_period_to_name_prefix_and_suffix(google_civic_candidate_name2)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name2_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_name_prefix_and_suffix(google_civic_candidate_name2)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name2_modified = add_results['modified_name']
                if name_changed and positive_value_exists(google_civic_candidate_name2_modified):
                    # We intentionally use case sensitive matching here
                    new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name2_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name2_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name2_modified)
                    filters.append(new_filter)

            if positive_value_exists(google_civic_candidate_name3):
                # We intentionally use case sensitive matching here
                new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name3)
                filters.append(new_filter)
                new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name3)
                filters.append(new_filter)
                new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name3)
                filters.append(new_filter)

                # Since Google Civic doesn't provide a unique identifier, and sometimes returns initials with
                # a period and sometimes without, we may need to try again
                name_changed = False
                google_civic_candidate_name3_modified = ""
                # If an initial exists in the name (ex/ " A "), then search for the name
                # with a period added (ex/ " A. ")
                add_results = add_period_to_middle_name_initial(google_civic_candidate_name3)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name3_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_middle_name_initial(google_civic_candidate_name3)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name3_modified = add_results['modified_name']
                if name_changed and positive_value_exists(google_civic_candidate_name3_modified):
                    # We intentionally use case sensitive matching here
                    new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name3_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name3_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name3_modified)
                    filters.append(new_filter)

                # Deal with prefix and suffix
                name_changed = False
                google_civic_candidate_name3_modified = ""
                # If an prefix or suffix exists in the name (ex/ " JR"), then search for the name
                # with a period added (ex/ " JR.")
                add_results = add_period_to_name_prefix_and_suffix(google_civic_candidate_name3)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name3_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_name_prefix_and_suffix(google_civic_candidate_name3)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name3_modified = add_results['modified_name']
                if name_changed and positive_value_exists(google_civic_candidate_name3_modified):
                    # We intentionally use case sensitive matching here
                    new_filter = Q(google_civic_candidate_name__iexact=google_civic_candidate_name3_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name2__iexact=google_civic_candidate_name3_modified)
                    filters.append(new_filter)
                    new_filter = Q(google_civic_candidate_name3__iexact=google_civic_candidate_name3_modified)
                    filters.append(new_filter)

            if positive_value_exists(candidate_name):
                new_filter = Q(candidate_name__iexact=candidate_name)
                filters.append(new_filter)

                # Since Google Civic doesn't provide a unique identifier, and sometimes returns initials with
                # a period and sometimes without, we may need to try again
                name_changed = False
                candidate_name_modified = ""
                # If an initial exists in the name (ex/ " A "), then search for the name
                # with a period added (ex/ " A. ")
                add_results = add_period_to_middle_name_initial(candidate_name)
                if add_results['name_changed']:
                    name_changed = True
                    candidate_name_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_middle_name_initial(candidate_name)
                    if add_results['name_changed']:
                        name_changed = True
                        candidate_name_modified = add_results['modified_name']

                if name_changed and positive_value_exists(candidate_name_modified):
                    # We intentionally use case sensitive matching here
                    new_filter = Q(candidate_name__exact=candidate_name_modified)
                    filters.append(new_filter)

            if positive_value_exists(politician_we_vote_id):
                new_filter = Q(politician_we_vote_id__iexact=politician_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(candidate_twitter_handle):
                new_filter = Q(candidate_twitter_handle__iexact=candidate_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(ballotpedia_candidate_id):
                new_filter = Q(ballotpedia_candidate_id=ballotpedia_candidate_id)
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

                candidate_query = candidate_query.filter(final_filters)

            candidate_list_objects = list(candidate_query)

            if len(candidate_list_objects):
                candidate_list_found = True
                status += 'DUPLICATE_CANDIDATES_RETRIEVED '
                success = True
            else:
                status += 'NO_DUPLICATE_CANDIDATES_RETRIEVED '
                success = True
        except CandidateCampaign.DoesNotExist:
            # No candidates found. Not a problem.
            status += 'NO_DUPLICATE_CANDIDATES_FOUND_DoesNotExist '
            candidate_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED-retrieve_possible_duplicate_candidates ' + str(e) + ' '
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'candidate_list_found':     candidate_list_found,
            'candidate_list':           candidate_list_objects,
        }
        return results

    def retrieve_candidates_from_non_unique_identifiers(
            self,
            google_civic_election_id_list=[],
            state_code='',
            candidate_twitter_handle='',
            candidate_name='',
            ignore_candidate_id_list=[],
            read_only=False):
        """
        This function, retrieve_candidates_from_non_unique_identifiers, is built to find possible duplicate candidates
        with stricter parameters.
        This is a different approach from search_candidates_in_specific_elections, which casts a wider net.
        Another related function, retrieve_possible_duplicate_candidates, is used to avoid duplicate candidate imports.
        :param google_civic_election_id_list:
        :param state_code:
        :param candidate_twitter_handle:
        :param candidate_name:
        :param ignore_candidate_id_list:
        :param read_only:
        :return:
        """
        keep_looking_for_duplicates = True
        candidate = CandidateCampaign()
        candidate_found = False
        candidate_list = []
        candidate_list_found = False
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
        multiple_entries_found = False
        success = True
        status = ""

        results = self.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list,
            limit_to_this_state_code=state_code)
        if not positive_value_exists(results['success']):
            status += results['status']
            success = False
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

        election_manager = ElectionManager()
        year_list = []
        results = election_manager.retrieve_year_list_by_election_list(
            google_civic_election_id_list=google_civic_election_id_list)
        if results['success']:
            year_list = results['year_list']

        if keep_looking_for_duplicates and positive_value_exists(candidate_twitter_handle):
            try:
                if positive_value_exists(read_only):
                    candidate_query = CandidateCampaign.objects.using('readonly').all()
                else:
                    candidate_query = CandidateCampaign.objects.all()

                # Only look for matches in candidates in the specified elections, or in the year(s) the elections are in
                candidate_query = candidate_query.filter(
                    Q(we_vote_id__in=candidate_we_vote_id_list) |
                    Q(candidate_year__in=year_list)
                )

                candidate_query = candidate_query.filter(candidate_twitter_handle__iexact=candidate_twitter_handle)
                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_candidate_id_list):
                    candidate_query = candidate_query.exclude(we_vote_id__in=ignore_candidate_id_list)

                candidate_list = list(candidate_query)
                if len(candidate_list):
                    # At least one entry exists
                    status += 'RETRIEVE_CANDIDATES_FROM_NON_UNIQUE-CANDIDATE_LIST_RETRIEVED '
                    # if a single entry matches, update that entry
                    if len(candidate_list) == 1:
                        multiple_entries_found = False
                        candidate = candidate_list[0]
                        candidate_found = True
                        keep_looking_for_duplicates = False
                        success = True
                        status += "CANDIDATE_FOUND_BY_TWITTER "
                    else:
                        # more than one entry found
                        candidate_list_found = True
                        multiple_entries_found = True
                        keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
                        status += "MULTIPLE_TWITTER_MATCHES "
            except CandidateCampaign.DoesNotExist:
                success = True
                status += "RETRIEVE_CANDIDATES_FROM_NON_UNIQUE-CANDIDATE_NOT_FOUND "
            except Exception as e:
                status += "RETRIEVE_CANDIDATES_FROM_NON_UNIQUE-CANDIDATE_QUERY_FAILED1 " + str(e) + " "
                success = False
                keep_looking_for_duplicates = False

        # twitter handle does not exist, next look up against other data that might match
        if keep_looking_for_duplicates and positive_value_exists(candidate_name):
            # Search by Candidate name exact match
            try:
                if positive_value_exists(read_only):
                    candidate_query = CandidateCampaign.objects.using('readonly').all()
                else:
                    candidate_query = CandidateCampaign.objects.all()

                # Only look for matches in candidates in the specified elections, or in the year(s) the elections are in
                candidate_query = candidate_query.filter(
                    Q(we_vote_id__in=candidate_we_vote_id_list) |
                    Q(candidate_year__in=year_list)
                )

                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)

                candidate_query = candidate_query.filter(
                    Q(candidate_name__iexact=candidate_name) |
                    Q(google_civic_candidate_name__iexact=candidate_name) |
                    Q(google_civic_candidate_name2__iexact=candidate_name) |
                    Q(google_civic_candidate_name3__iexact=candidate_name)
                )

                if positive_value_exists(ignore_candidate_id_list):
                    candidate_query = candidate_query.exclude(we_vote_id__in=ignore_candidate_id_list)

                candidate_list = list(candidate_query)
                if len(candidate_list):
                    # entry exists
                    status += 'CANDIDATE_ENTRY_EXISTS1 '
                    success = True
                    # if a single entry matches, update that entry
                    if len(candidate_list) == 1:
                        candidate = candidate_list[0]
                        candidate_found = True
                        status += candidate.we_vote_id + " "
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in CandidateCampaign
                        candidate_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    success = True
                    status += 'CANDIDATE_ENTRY_NOT_FOUND-EXACT '

            except CandidateCampaign.DoesNotExist:
                success = True
                status += "RETRIEVE_CANDIDATES_FROM_NON_UNIQUE-CANDIDATE_NOT_FOUND-EXACT_MATCH "
            except Exception as e:
                status += "RETRIEVE_CANDIDATES_FROM_NON_UNIQUE-CANDIDATE_QUERY_FAILED2: " + str(e) + " "
                success = False

        if keep_looking_for_duplicates and positive_value_exists(candidate_name):
            # Search for Candidate(s) that contains the same first and last names
            try:
                if positive_value_exists(read_only):
                    candidate_query = CandidateCampaign.objects.using('readonly').all()
                else:
                    candidate_query = CandidateCampaign.objects.all()

                # We *could* convert to be an "or" -- or election_year matches, but may not want to
                #  Given we might turn up more false positives. Worth trying.
                # candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)

                # Only look for matches in candidates in the specified elections, or in the year(s) the elections are in
                candidate_query = candidate_query.filter(
                    Q(we_vote_id__in=candidate_we_vote_id_list) |
                    Q(candidate_year__in=year_list)
                )

                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(candidate_name)
                candidate_query = candidate_query.filter(
                    Q(candidate_name__icontains=first_name) |
                    Q(google_civic_candidate_name__icontains=first_name) |
                    Q(google_civic_candidate_name2__icontains=first_name) |
                    Q(google_civic_candidate_name3__icontains=first_name)
                )
                last_name = extract_last_name_from_full_name(candidate_name)
                candidate_query = candidate_query.filter(candidate_name__icontains=last_name)

                if positive_value_exists(ignore_candidate_id_list):
                    candidate_query = candidate_query.exclude(we_vote_id__in=ignore_candidate_id_list)

                candidate_list = list(candidate_query)
                if len(candidate_list):
                    # entry exists
                    status += 'CANDIDATE_ENTRY_EXISTS2 '
                    success = True
                    # if a single entry matches, update that entry
                    if len(candidate_list) == 1:
                        candidate = candidate_list[0]
                        candidate_found = True
                        status += candidate.we_vote_id + " "
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match in CandidateCampaign
                        candidate_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    status += 'CANDIDATE_ENTRY_NOT_FOUND-FIRST_OR_LAST '
                    success = True
            except CandidateCampaign.DoesNotExist:
                status += "RETRIEVE_CANDIDATES_FROM_NON_UNIQUE-CANDIDATE_NOT_FOUND-FIRST_OR_LAST_NAME "
                success = True
            except Exception as e:
                status += "RETRIEVE_CANDIDATES_FROM_NON_UNIQUE-CANDIDATE_QUERY_FAILED3: " + str(e) + " "
                success = False

        results = {
            'success':                          success,
            'status':                           status,
            'google_civic_election_id_list':    google_civic_election_id_list,
            'candidate_found':                  candidate_found,
            'candidate':                        candidate,
            'candidate_list_found':             candidate_list_found,
            'candidate_list':                   candidate_list,
            'multiple_entries_found':           multiple_entries_found,
        }
        return results

    @staticmethod
    def fetch_candidate_count_for_politician(
            politician_id=0,
            politician_we_vote_id=''):

        if not positive_value_exists(politician_id) and not \
                positive_value_exists(politician_we_vote_id):
            return 0

        candidate_query = CandidateCampaign.objects.using('readonly').all()

        # Retrieve the support positions for this politician_id
        position_count = 0
        try:
            if positive_value_exists(politician_id) and positive_value_exists(politician_we_vote_id):
                candidate_query = candidate_query.filter(
                    Q(politician_we_vote_id__iexact=politician_we_vote_id) |
                    Q(politician_id=politician_id)
                )
            elif positive_value_exists(politician_id):
                candidate_query = candidate_query.filter(politician_id=politician_id)
            else:
                candidate_query = candidate_query.filter(
                    politician_we_vote_id__iexact=politician_we_vote_id)

            position_count = candidate_query.count()
        except Exception as e:
            pass

        return position_count

    def fetch_candidates_from_non_unique_identifiers_count(
            self,
            google_civic_election_id_list=[],
            state_code='',
            candidate_twitter_handle='',
            candidate_name='',
            ignore_candidate_id_list=[]):
        keep_looking_for_duplicates = True
        candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle)
        status = ""

        results = self.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list)
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

        election_manager = ElectionManager()
        year_list = []
        results = election_manager.retrieve_year_list_by_election_list(
            google_civic_election_id_list=google_civic_election_id_list)
        if results['success']:
            year_list = results['year_list']

        if keep_looking_for_duplicates and positive_value_exists(candidate_twitter_handle):
            try:
                candidate_query = CandidateCampaign.objects.all()
                candidate_query = candidate_query.filter(candidate_twitter_handle__iexact=candidate_twitter_handle)

                # Only look for matches in candidates in the specified elections, or in the year(s) the elections are in
                candidate_query = candidate_query.filter(
                    Q(we_vote_id__in=candidate_we_vote_id_list) |
                    Q(candidate_year__in=year_list)
                )

                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_candidate_id_list):
                    candidate_query = candidate_query.exclude(we_vote_id__in=ignore_candidate_id_list)

                candidate_count = candidate_query.count()
                if positive_value_exists(candidate_count):
                    return candidate_count
            except CandidateCampaign.DoesNotExist:
                status += "FETCH_CANDIDATES_FROM_NON_UNIQUE_IDENTIFIERS_COUNT1 "
                # twitter handle does not exist, next look up against other data that might match

        if keep_looking_for_duplicates and positive_value_exists(candidate_name):
            # Search by Candidate name exact match
            try:
                candidate_query = CandidateCampaign.objects.all()
                candidate_query = candidate_query.filter(candidate_name__iexact=candidate_name)

                # Only look for matches in candidates in the specified elections, or in the year(s) the elections are in
                candidate_query = candidate_query.filter(
                    Q(we_vote_id__in=candidate_we_vote_id_list) |
                    Q(candidate_year__in=year_list)
                )

                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)

                if positive_value_exists(ignore_candidate_id_list):
                    candidate_query = candidate_query.exclude(we_vote_id__in=ignore_candidate_id_list)

                candidate_count = candidate_query.count()
                if positive_value_exists(candidate_count):
                    return candidate_count
            except CandidateCampaign.DoesNotExist:
                status += "FETCH_CANDIDATES_FROM_NON_UNIQUE_IDENTIFIERS_COUNT2 "

        if keep_looking_for_duplicates and positive_value_exists(candidate_name):
            # Search for Candidate(s) that contains the same first and last names
            try:
                candidate_query = CandidateCampaign.objects.all()

                # Only look for matches in candidates in the specified elections, or in the year(s) the elections are in
                candidate_query = candidate_query.filter(
                    Q(we_vote_id__in=candidate_we_vote_id_list) |
                    Q(candidate_year__in=year_list)
                )

                if positive_value_exists(state_code):
                    candidate_query = candidate_query.filter(state_code__iexact=state_code)
                first_name = extract_first_name_from_full_name(candidate_name)
                candidate_query = candidate_query.filter(candidate_name__icontains=first_name)
                last_name = extract_last_name_from_full_name(candidate_name)
                candidate_query = candidate_query.filter(candidate_name__icontains=last_name)

                if positive_value_exists(ignore_candidate_id_list):
                    candidate_query = candidate_query.exclude(we_vote_id__in=ignore_candidate_id_list)

                candidate_count = candidate_query.count()
                if positive_value_exists(candidate_count):
                    return candidate_count
            except CandidateCampaign.DoesNotExist:
                status += "FETCH_CANDIDATES_FROM_NON_UNIQUE_IDENTIFIERS_COUNT3 "

        return 0

    def retrieve_candidate_to_office_link_list(
            self,
            candidate_we_vote_id_list=[],
            contest_office_we_vote_id_list=[],
            google_civic_election_id_list=[],
            state_code='',
            read_only=True):
        link_list = []
        status = ""
        success = True
        google_civic_election_id_integer_list = []
        for google_civic_election_id in google_civic_election_id_list:
            google_civic_election_id_integer_list.append(convert_to_int(google_civic_election_id))

        try:
            if positive_value_exists(read_only):
                query = CandidateToOfficeLink.objects.using('readonly').all()
            else:
                query = CandidateToOfficeLink.objects.all()
            if positive_value_exists(len(candidate_we_vote_id_list)):
                query = query.filter(candidate_we_vote_id__in=candidate_we_vote_id_list)
            if positive_value_exists(len(contest_office_we_vote_id_list)):
                query = query.filter(contest_office_we_vote_id__in=contest_office_we_vote_id_list)
            if positive_value_exists(len(google_civic_election_id_list)):
                query = query.filter(google_civic_election_id__in=google_civic_election_id_integer_list)
            if positive_value_exists(state_code):
                query = query.filter(state_code__iexact=state_code)

            link_list = list(query)
        except Exception as e:
            status += "RETRIEVE_CANDIDATE_TO_OFFICE_LINK_LIST-ERROR: " + str(e) + " "
            success = False

        results = {
            'success':                          success,
            'status':                           status,
            'candidate_to_office_link_list':    link_list,
        }
        return results

    def retrieve_candidate_we_vote_id_list_from_election_list(
            self,
            google_civic_election_id_list=[],
            limit_to_this_state_code=''):
        candidate_we_vote_id_list = []
        office_we_vote_id_list_by_candidate_we_vote_id = {}
        status = ''
        success = True
        results = self.retrieve_candidate_to_office_link_list(
            google_civic_election_id_list=google_civic_election_id_list,
            state_code=limit_to_this_state_code)
        if not positive_value_exists(results['success']):
            status += results['status']
            success = False
        else:
            candidate_to_office_link_list = results['candidate_to_office_link_list']
            for candidate_to_office_link in candidate_to_office_link_list:
                candidate_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)
                office_we_vote_id_list_by_candidate_we_vote_id[candidate_to_office_link.candidate_we_vote_id]\
                    = candidate_to_office_link.contest_office_we_vote_id
        results = {
            'status':                       status,
            'success':                      success,
            'candidate_we_vote_id_list':    candidate_we_vote_id_list,
            'office_we_vote_id_list_by_candidate_we_vote_id':   office_we_vote_id_list_by_candidate_we_vote_id,
        }
        return results

    def retrieve_candidate_we_vote_id_list_from_office_list(
            self,
            contest_office_we_vote_id_list=[],
            limit_to_this_state_code=''):
        candidate_we_vote_id_list = []
        office_we_vote_id_list_by_candidate_we_vote_id = {}
        status = ''
        success = True
        results = self.retrieve_candidate_to_office_link_list(
            contest_office_we_vote_id_list=contest_office_we_vote_id_list,
            state_code=limit_to_this_state_code)
        if not positive_value_exists(results['success']):
            status += results['status']
            success = False
        else:
            candidate_to_office_link_list = results['candidate_to_office_link_list']
            for candidate_to_office_link in candidate_to_office_link_list:
                candidate_we_vote_id_list.append(candidate_to_office_link.candidate_we_vote_id)
                office_we_vote_id_list_by_candidate_we_vote_id[candidate_to_office_link.candidate_we_vote_id]\
                    = candidate_to_office_link.contest_office_we_vote_id
        results = {
            'status':                       status,
            'success':                      success,
            'candidate_we_vote_id_list':    candidate_we_vote_id_list,
            'office_we_vote_id_list_by_candidate_we_vote_id':   office_we_vote_id_list_by_candidate_we_vote_id,
        }
        return results

    def fetch_candidate_we_vote_id_list_from_office_we_vote_id(self, office_we_vote_id):
        results = self.retrieve_all_candidates_for_office(office_we_vote_id=office_we_vote_id)
        if not positive_value_exists(results['candidate_list_found']):
            return []
        candidate_list = results['candidate_list']
        candidate_we_vote_id_list = []
        for one_candidate in candidate_list:
            candidate_we_vote_id_list.append(one_candidate.we_vote_id)
        return candidate_we_vote_id_list

    def fetch_candidate_we_vote_id_list_from_election_list(
            self,
            google_civic_election_id_list=[],
            limit_to_this_state_code=''):
        results = self.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list,
            limit_to_this_state_code=limit_to_this_state_code)
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']
        return candidate_we_vote_id_list

    def fetch_office_we_vote_id_list_from_candidate_we_vote_id(self, candidate_we_vote_id):
        results = self.retrieve_all_offices_for_candidate(candidate_we_vote_id=candidate_we_vote_id)
        if not positive_value_exists(results['office_list_found']):
            return []
        office_list = results['office_list']
        office_we_vote_id_list = []
        for one_office in office_list:
            office_we_vote_id_list.append(one_office.we_vote_id)
        return office_we_vote_id_list

    def retrieve_google_civic_election_id_list_from_candidate_we_vote_id_list(
            self,
            candidate_we_vote_id_list=[],
            limit_to_this_state_code=''):
        google_civic_election_id_list = []
        office_we_vote_id_list_by_google_civic_election_id = {}
        status = ''
        success = True
        results = self.retrieve_candidate_to_office_link_list(
            candidate_we_vote_id_list=candidate_we_vote_id_list,
            state_code=limit_to_this_state_code)
        if not positive_value_exists(results['success']):
            status += results['status']
            success = False
        else:
            candidate_to_office_link_list = results['candidate_to_office_link_list']
            for candidate_to_office_link in candidate_to_office_link_list:
                google_civic_election_id_list.append(candidate_to_office_link.google_civic_election_id)
                office_we_vote_id_list_by_google_civic_election_id[candidate_to_office_link.google_civic_election_id]\
                    = candidate_to_office_link.candidate_we_vote_id
        results = {
            'status':                           status,
            'success':                          success,
            'google_civic_election_id_list':    google_civic_election_id_list,
            'office_we_vote_id_list_by_google_civic_election_id':   office_we_vote_id_list_by_google_civic_election_id,
        }
        return results

    def search_candidates_in_specific_elections(self, google_civic_election_id_list, search_string='', state_code='',
                                                candidate_name='', candidate_twitter_handle='',
                                                candidate_website='', candidate_email='',
                                                candidate_facebook='', twitter_handle_list='', facebook_page_list='',
                                                exact_match=False):
        """
        This function, search_candidates_in_specific_elections, is meant to cast a wider net for any
        possible candidates that might match.
        It has some parallels with organization.models: organization_search_find_any_possibilities
        This is different than retrieve_candidates_from_non_unique_identifiers, which is built to find
        possible duplicate candidates with stricter parameters.
        Another related function, retrieve_possible_duplicate_candidates, is used to avoid duplicate candidate imports.
        :param google_civic_election_id_list:
        :param search_string:
        :param state_code:
        :param candidate_name:
        :param candidate_twitter_handle:
        :param candidate_website:
        :param candidate_email:
        :param candidate_facebook:
        :param twitter_handle_list:
        :param facebook_page_list:
        :param exact_match:
        :return:
        """
        status = ""
        candidate_list_objects = []
        candidate_list_json = []
        candidate_list_found = False

        try:
            search_words = search_string.split()
        except Exception as e:
            status += "SEARCH_STRING_COULD_NOT_BE_SPLIT "
            search_words = []

        # candidate_website = voter_guide_website,
        # facebook_page_list = facebook_page_list_modified,
        # twitter_handle_list = twitter_handle_list_modified
        try:
            results = self.retrieve_candidate_we_vote_id_list_from_election_list(
                google_civic_election_id_list=google_civic_election_id_list,
                limit_to_this_state_code=state_code)
            if not positive_value_exists(results['success']):
                status += results['status']
                success = False
            candidate_we_vote_id_list = results['candidate_we_vote_id_list']

            candidate_query = CandidateCampaign.objects.all()
            candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            if positive_value_exists(state_code):
                candidate_query = candidate_query.filter(state_code__iexact=state_code)
            candidate_query = candidate_query.order_by("candidate_name")

            # This is an "OR" search for each term, but an "AND" search across all search_words
            for search_word in search_words:
                filters = []

                # We want to find candidates with *any* of these values
                new_filter = Q(ballotpedia_candidate_name__icontains=search_word)
                filters.append(new_filter)
                new_filter = Q(google_civic_candidate_name__icontains=search_word)
                filters.append(new_filter)
                new_filter = Q(candidate_name__icontains=search_word)
                filters.append(new_filter)
                new_filter = Q(candidate_twitter_handle__icontains=search_word)
                filters.append(new_filter)
                new_filter = Q(contest_office_name__icontains=search_word)
                filters.append(new_filter)
                new_filter = Q(twitter_name__icontains=search_word)
                filters.append(new_filter)

                # Add the first query
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                # Add as new filter for "AND"
                candidate_query = candidate_query.filter(final_filters)

            # Reset filters for next batch of "OR"
            filters = []

            if positive_value_exists(twitter_handle_list):
                for one_twitter_handle in twitter_handle_list:
                    one_twitter_handle2 = extract_twitter_handle_from_text_string(one_twitter_handle)
                    if positive_value_exists(exact_match):
                        new_filter = Q(candidate_twitter_handle__iexact=one_twitter_handle2)
                    else:
                        new_filter = Q(candidate_twitter_handle__icontains=one_twitter_handle2)
                    filters.append(new_filter)

            if positive_value_exists(facebook_page_list):
                for one_facebook_page in facebook_page_list:
                    one_facebook_page2 = extract_twitter_handle_from_text_string(one_facebook_page)
                    if positive_value_exists(exact_match):
                        new_filter = Q(facebook_url__iexact=one_facebook_page2)
                    else:
                        new_filter = Q(facebook_url__icontains=one_facebook_page2)
                    filters.append(new_filter)

            if positive_value_exists(candidate_website):
                if positive_value_exists(exact_match):
                    new_filter = Q(candidate_url__iexact=candidate_website)
                else:
                    new_filter = Q(candidate_url__icontains=candidate_website)
                filters.append(new_filter)

            if positive_value_exists(candidate_email):
                if positive_value_exists(exact_match):
                    new_filter = Q(candidate_email__iexact=candidate_email)
                else:
                    new_filter = Q(candidate_email__icontains=candidate_email)
                filters.append(new_filter)

            if positive_value_exists(len(filters)):
                final_filters = filters.pop()
                for item in filters:
                    final_filters |= item

                # Add as new filter for "AND"
                candidate_query = candidate_query.filter(final_filters)

            candidate_list_objects = candidate_query[:25]

            if len(candidate_list_objects):
                candidate_list_found = True
                status += 'SEARCH_CANDIDATES_FOR_UPCOMING_ELECTION_FOUND '
                success = True
            else:
                status += 'SEARCH_CANDIDATES_FOR_UPCOMING_ELECTION_NOT_FOUND '
                success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'FAILED_SEARCH_CANDIDATES_FOR_UPCOMING_ELECTION: ' + str(e) + ' '
            success = False

        if candidate_list_found:
            for candidate in candidate_list_objects:
                one_candidate = {
                    'ballot_item_display_name':     candidate.display_candidate_name(),
                    'ballotpedia_candidate_id':     candidate.ballotpedia_candidate_id,
                    'ballotpedia_candidate_url':    candidate.ballotpedia_candidate_url,
                    'ballotpedia_office_id':        candidate.ballotpedia_office_id,
                    'ballotpedia_person_id':        candidate.ballotpedia_person_id,
                    'ballotpedia_race_id':          candidate.ballotpedia_race_id,
                    'candidate_contact_form_url':   candidate.candidate_contact_form_url,
                    'candidate_email':              candidate.candidate_email,
                    'candidate_name':               candidate.candidate_name,  # For Voter Guide Possibility System
                    'candidate_phone':              candidate.candidate_phone,
                    'candidate_photo_url_large':    candidate.we_vote_hosted_profile_image_url_large
                    if positive_value_exists(candidate.we_vote_hosted_profile_image_url_large)
                    else candidate.candidate_photo_url(),
                    'candidate_photo_url_medium':   candidate.we_vote_hosted_profile_image_url_medium,
                    'candidate_photo_url_tiny':     candidate.we_vote_hosted_profile_image_url_tiny,
                    'candidate_url':                candidate.candidate_url,
                    'candidate_we_vote_id':         candidate.we_vote_id,
                    'candidate_website':            candidate.candidate_url,  # For Voter Guide Possibility System
                    'candidate_twitter_handle':     candidate.candidate_twitter_handle,  # For Voter Guide Possibility
                    'candidate_facebook':           candidate.facebook_url,  # For Voter Guide Possibility System
                    'contest_office_id':            candidate.contest_office_id,
                    'contest_office_we_vote_id':    candidate.contest_office_we_vote_id,
                    'contest_office_name':          candidate.contest_office_name,
                    'facebook_url':                 candidate.facebook_url,
                    'google_civic_election_id':     candidate.google_civic_election_id,
                    'id':                           candidate.id,
                    'kind_of_ballot_item':          "CANDIDATE",
                    'maplight_id':                  candidate.maplight_id,
                    'ocd_division_id':              candidate.ocd_division_id,
                    'office_we_vote_id':            candidate.contest_office_we_vote_id,
                    'order_on_ballot':              candidate.order_on_ballot,
                    'politician_id':                candidate.politician_id,
                    'politician_we_vote_id':        candidate.politician_we_vote_id,
                    'party':                        candidate.political_party_display(),
                    'state_code':                   candidate.state_code,
                    'twitter_url':                  candidate.twitter_url,
                    'twitter_handle':               candidate.fetch_twitter_handle(),
                    'twitter_description':          candidate.twitter_description,
                    'twitter_followers_count':      candidate.twitter_followers_count,
                    'youtube_url':                  candidate.youtube_url,
                    'we_vote_id': candidate.we_vote_id,
                }
                candidate_list_json.append(one_candidate.copy())

        results = {
            'success': success,
            'status': status,
            'candidate_list': candidate_list_objects,
            'candidate_list_found': candidate_list_found,
            'candidate_list_json': candidate_list_json,
        }
        return results

    def retrieve_candidates_with_misformatted_names(self, start=0, count=15):
        """
        Get the first 15 records that have 3 capitalized letters in a row, as long as those letters
        are not 'III' i.e. King Henry III.  Also exclude the names where the word "WITHDRAWN" has been appended when
        the candidate withdrew from the race
        SELECT * FROM public.politician_politician WHERE politician_name ~ '.*?[A-Z][A-Z][A-Z].*?' and politician_name !~ '.*?III.*?'

        :param start:
        :return:
        """
        candidate_query = CandidateCampaign.objects.all()
        # Get all candidates that have three capital letters in a row in their name, but exclude III (King Henry III)
        candidate_query = candidate_query.filter(candidate_name__regex=r'.*?[A-Z][A-Z][A-Z].*?(?<!III)').\
            order_by('candidate_name')
        number_of_rows = candidate_query.count()
        candidate_query = candidate_query[start:(start+count)]
        candidate_list_objects = list(candidate_query)
        results_list = []
        out = ''
        # out = 'KING HENRY III => ' + display_full_name_with_correct_capitalization('KING HENRY III') + ", "
        for x in candidate_list_objects:
            name = x.candidate_name
            if name.endswith('WITHDRAWN') and not bool(re.match('^[A-Z]+$', name)):
                continue
            x.person_name_normalized = display_full_name_with_correct_capitalization(name)
            results_list.append(x)
            # out += name + ' = > ' + x.person_name_normalized + ', '

        return results_list, number_of_rows

    def retrieve_candidates_from_politician(self, politician_id=0, politician_we_vote_id=''):
        success = True
        status = ""
        candidate_list = []
        candidate_list_found = False

        if not positive_value_exists(politician_we_vote_id) and not positive_value_exists(politician_id):
            success = False
            status += "POLITICIAN_ID_AND_WE_VOTE_ID_MISSING "
            results = {
                'success':              success,
                'status':               status,
                'candidate_list':       candidate_list,
                'candidate_list_found': candidate_list_found,
            }
            return results

        try:
            candidate_query = CandidateCampaign.objects.all()
            if positive_value_exists(politician_id) and positive_value_exists(politician_we_vote_id):
                candidate_query = candidate_query.filter(
                    Q(politician_id=politician_id) |
                    Q(politician_we_vote_id=politician_we_vote_id)
                )
            elif positive_value_exists(politician_id):
                candidate_query = candidate_query.filter(politician_id=politician_id)
            else:
                candidate_query = candidate_query.filter(politician_we_vote_id__iexact=politician_we_vote_id)
            candidate_list = list(candidate_query)
            candidate_list_found = len(candidate_list) > 0
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_CANDIDATE_LIST_FROM_POLITICIAN_WE_VOTE_ID: " + str(e) + ' '
        results = {
            'success':              success,
            'status':               status,
            'candidate_list':       candidate_list,
            'candidate_list_found': candidate_list_found,
        }
        return results

    def retrieve_politician_we_vote_id_list_from_candidate_we_vote_id_list(
            self,
            candidate_we_vote_id_list=[]):
        success = True
        status = ""
        politician_we_vote_id_list = []
        politician_we_vote_id_list_found = False
        try:
            candidate_query = CandidateCampaign.objects.all()
            candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            candidate_query = candidate_query.exclude(
                Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id="")
            )
            candidate_query = candidate_query.values_list('politician_we_vote_id', flat=True).distinct()
            politician_we_vote_id_list = list(candidate_query)
            politician_we_vote_id_list_found = len(politician_we_vote_id_list) > 0
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_POLITICIAN_LIST: " + str(e) + ' '
        results = {
            'success':                          success,
            'status':                           status,
            'politician_we_vote_id_list':       politician_we_vote_id_list,
            'politician_we_vote_id_list_found': politician_we_vote_id_list_found,
        }
        return results

    def update_politician_we_vote_id_in_all_candidates(
            self,
            candidate_we_vote_id='',
            politician_id=0,
            politician_we_vote_id='',
            new_politician_id=None,
            new_politician_we_vote_id=None):
        success = True
        status = ''
        number_changed = 0

        if positive_value_exists(candidate_we_vote_id):
            number_changed += CandidateCampaign.objects.all().filter(
                candidate_campaign_we_vote_id=candidate_we_vote_id,
            ).update(
                politician_id=new_politician_id,
                politician_we_vote_id=new_politician_we_vote_id,
            )

        if positive_value_exists(politician_id):
            number_changed += CandidateCampaign.objects.all().filter(
                politician_id=politician_id,
            ).update(
                politician_id=new_politician_id,
                politician_we_vote_id=new_politician_we_vote_id,
            )

        if positive_value_exists(politician_we_vote_id):
            number_changed += CandidateCampaign.objects.all().filter(
                politician_we_vote_id=politician_we_vote_id,
            ).update(
                politician_id=new_politician_id,
                politician_we_vote_id=new_politician_we_vote_id,
            )

        results = {
            'success':          success,
            'status':           status,
            'number_changed':   number_changed,
        }
        return results


class CandidateCampaign(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # Endorsers
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "cand", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_candidate_campaign_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this candidate", max_length=255, default=None, null=True,
        blank=True, unique=True, db_index=True)
    maplight_id = models.CharField(
        verbose_name="maplight candidate id", max_length=255, default=None, null=True, blank=True, unique=True)
    vote_smart_id = models.CharField(
        verbose_name="vote smart candidate id", max_length=15, default=None, null=True, blank=True, unique=False)
    # The internal We Vote id for the ContestOffice that this candidate is competing for. During setup we need to allow
    # this to be null.
    contest_office_id = models.CharField(
        verbose_name="contest_office_id id", max_length=255, null=True, blank=True, db_index=True)
    # We want to link the candidate to the contest with permanent ids so we can export and import
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the office this candidate is running for", max_length=255, default=None,
        null=True, blank=True, unique=False, db_index=True)
    contest_office_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)
    # politician (internal) link to local We Vote Politician entry. During setup we need to allow this to be null.
    politician_id = models.BigIntegerField(verbose_name="politician unique identifier", null=True, blank=True)
    # The persistent We Vote unique ID of the Politician, so we can export and import into other databases.
    politician_we_vote_id = models.CharField(
        verbose_name="we vote politician id", max_length=255, null=True, blank=True)
    # The candidate's name.
    candidate_name = models.CharField(verbose_name="candidate name", max_length=255, null=False, blank=False)
    # The candidate's name as passed over by Google Civic. We save this so we can match to this candidate even
    # if we edit the candidate's name locally.  Sometimes Google isn't consistent with office names.
    google_civic_candidate_name = models.CharField(verbose_name="candidate name exactly as received from google civic",
                                                   max_length=255, null=True)
    google_civic_candidate_name2 = models.CharField(verbose_name="candidate name exactly as received from google civic",
                                                    max_length=255, null=True)
    google_civic_candidate_name3 = models.CharField(verbose_name="candidate name exactly as received from google civic",
                                                    max_length=255, null=True)
    candidate_gender = models.CharField(verbose_name="candidate gender", max_length=255, null=True, blank=True)
    # Birthday in YYYY-MM-DD format.
    birth_day_text = models.CharField(verbose_name="birth day", max_length=10, null=True, blank=True)
    # The full name of the party the candidate is a member of.
    party = models.CharField(verbose_name="party", max_length=255, null=True, blank=True)
    # A URL for a photo of the candidate.
    photo_url = models.TextField(verbose_name="photoUrl", null=True, blank=True)
    photo_url_from_ctcl = models.TextField(null=True, blank=True)
    photo_url_from_maplight = models.TextField(
        verbose_name='candidate portrait url of candidate from maplight', blank=True, null=True)
    photo_url_from_vote_smart = models.TextField(
        verbose_name='candidate portrait url of candidate from vote smart', blank=True, null=True)
    # Image URL on Vote USA's servers. See vote_usa_profile_image_url_https, the master image cached on We Vote servers.
    photo_url_from_vote_usa = models.TextField(null=True, blank=True)
    # The order the candidate appears on the ballot relative to other candidates for this contest.
    order_on_ballot = models.CharField(verbose_name="order on ballot", max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=255, null=True, blank=True, db_index=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    candidate_instagram_url = models.TextField(blank=True, null=True)
    # The date of the last election this candidate relates to, converted to integer, ex/ 20201103
    candidate_ultimate_election_date = models.PositiveIntegerField(default=None, null=True)
    # The year this candidate is running for office
    candidate_year = models.PositiveIntegerField(default=None, null=True)
    # State code
    state_code = models.CharField(verbose_name="state this candidate serves",
                                  max_length=2, null=True, blank=True, db_index=True)
    date_last_updated = models.DateTimeField(null=True, auto_now=True)
    # The URL for the candidate's campaign web site.
    candidate_url = models.URLField(
        verbose_name='website url of candidate', max_length=255, blank=True, null=True)
    candidate_contact_form_url = models.URLField(
        verbose_name='website url of candidate contact form', max_length=255, blank=True, null=True)
    facebook_url = models.TextField(verbose_name='facebook url of candidate', blank=True, null=True)
    facebook_url_is_broken = models.BooleanField(verbose_name="facebook url is broken", default=False)
    # Some ambiguity to be resolved. In some places this variable is used for photo url on Facebook servers.
    # Should be the master image url cached on We Vote servers.
    facebook_profile_image_url_https = models.TextField(
        verbose_name='url of profile image from facebook', blank=True, null=True)

    twitter_url = models.URLField(verbose_name='twitter url of candidate', blank=True, null=True)
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    candidate_twitter_handle = models.CharField(
        verbose_name='candidate twitter screen_name', max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="candidate plain text name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="candidate location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    # This is the master image cached on We Vote servers. Note that we do not keep the original image URL from Twitter.
    twitter_profile_image_url_https = models.TextField(
        verbose_name='locally cached url of candidate profile image from twitter', blank=True, null=True)
    twitter_profile_background_image_url_https = models.TextField(verbose_name='tile-able background from twitter',
                                                                  blank=True, null=True)
    twitter_profile_banner_url_https = models.TextField(verbose_name='profile banner image from twitter',
                                                        blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)
    vote_usa_office_id = models.CharField(
        verbose_name="Vote USA permanent id for the office", max_length=64, default=None, null=True, blank=True)
    vote_usa_politician_id = models.CharField(
        verbose_name="Vote USA permanent id for this candidate", max_length=64, default=None, null=True, blank=True)
    # This is the master image url cached on We Vote servers. See photo_url_from_vote_usa for Vote USA URL.
    vote_usa_profile_image_url_https = models.TextField(null=True, blank=True, default=None)

    # Which voter image is currently active?
    profile_image_type_currently_active = models.CharField(
        max_length=10, choices=PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES, default=PROFILE_IMAGE_TYPE_UNKNOWN)
    # Image for candidate from Facebook, cached on We Vote's servers. See also facebook_profile_image_url_https.
    we_vote_hosted_profile_facebook_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for candidate from Twitter, cached on We Vote's servers. See local master twitter_profile_image_url_https.
    we_vote_hosted_profile_twitter_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for candidate uploaded to We Vote's servers.
    we_vote_hosted_profile_uploaded_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for candidate from Vote USA, cached on We Vote's servers. See local master vote_usa_profile_image_url_https.
    we_vote_hosted_profile_vote_usa_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_tiny = models.TextField(blank=True, null=True)
    # Image we are using as the profile photo (could be sourced from Twitter, Facebook, etc.)
    we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)

    google_plus_url = models.URLField(verbose_name='google plus url of candidate', blank=True, null=True)
    youtube_url = models.URLField(verbose_name='youtube url of candidate', blank=True, null=True)
    # The email address for the candidate's campaign.
    candidate_email = models.CharField(verbose_name="candidate email", max_length=255, null=True, blank=True)
    # The voice phone number for the candidate's campaign office.
    candidate_phone = models.CharField(verbose_name="candidate phone", max_length=255, null=True, blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.TextField(
        verbose_name='url of wikipedia logo', blank=True, null=True)
    linkedin_url = models.CharField(
        verbose_name="linkedin url of candidate", max_length=255, null=True, blank=True)
    linkedin_photo_url = models.TextField(verbose_name='url of linkedin logo', blank=True, null=True)

    # other_source_url is the location (ex/ http://mywebsite.com/candidate1.html) where we find
    # the other_source_photo_url OR the original url of the photo before we store it locally
    other_source_url = models.CharField(
        verbose_name="other source url of candidate", max_length=255, null=True, blank=True)
    other_source_photo_url = models.TextField(verbose_name='url of other source image', blank=True, null=True)

    ballotpedia_candidate_id = models.PositiveIntegerField(verbose_name="ballotpedia integer id", null=True, blank=True)
    # The candidate's name as passed over by Ballotpedia
    ballotpedia_candidate_name = models.CharField(verbose_name="candidate name exactly as received from ballotpedia",
                                                  max_length=255, null=True, blank=True)
    ballotpedia_candidate_summary = models.TextField(verbose_name="candidate summary from ballotpedia",
                                                     null=True, blank=True, default=None)
    ballotpedia_candidate_url = models.TextField(
        verbose_name='url of candidate on ballotpedia', blank=True, null=True)
    ballotpedia_election_id = models.PositiveIntegerField(verbose_name="ballotpedia election id", null=True, blank=True)
    # The id of the image for retrieval from Ballotpedia API
    ballotpedia_image_id = models.PositiveIntegerField(verbose_name="ballotpedia image id", null=True, blank=True)
    ballotpedia_profile_image_url_https = models.TextField(
        verbose_name='locally cached candidate profile image from ballotpedia', blank=True, null=True)
    # Equivalent to Elected Office
    ballotpedia_office_id = models.PositiveIntegerField(
        verbose_name="ballotpedia elected office integer id", null=True, blank=True)
    # This is just the characters in the Ballotpedia URL
    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    # Equivalent to Politician
    ballotpedia_person_id = models.PositiveIntegerField(verbose_name="ballotpedia integer id", null=True, blank=True)
    ballotpedia_photo_url = models.TextField(
        verbose_name='url of ballotpedia logo', blank=True, null=True)
    # Equivalent to Contest Office
    ballotpedia_race_id = models.PositiveIntegerField(verbose_name="ballotpedia race integer id", null=True, blank=True)

    # Official Statement from Candidate in Ballot Guide
    ballot_guide_official_statement = models.TextField(verbose_name="official candidate statement from ballot guide",
                                                       null=True, blank=True, default="")
    crowdpac_candidate_id = models.PositiveIntegerField(
        verbose_name="crowdpac integer id", null=True, blank=True)
    # CTCL candidate data fields
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=36, null=True, blank=True)

    candidate_is_top_ticket = models.BooleanField(verbose_name="candidate is top ticket", default=False)
    candidate_is_incumbent = models.BooleanField(verbose_name="candidate is the current incumbent", default=False)
    # Candidacy Declared, (and others for withdrawing, etc.)
    candidate_participation_status = models.CharField(verbose_name="candidate participation status",
                                                      max_length=255, null=True, blank=True)
    withdrawn_from_election = models.BooleanField(verbose_name='Candidate has withdrawn from election', default=False)
    withdrawal_date = models.DateField(verbose_name='Withdrawal date from election', null=True, auto_now=False)
    # Set to true if we don't want to display this candidate for some reason
    do_not_display_on_ballot = models.BooleanField(default=False)
    # Set this for existing candidates once we have created CandidateToOfficeLink (is temporary variable)
    migrated_to_link = models.BooleanField(default=False)

    def election(self):
        try:
            election = Election.objects.get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("candidate.election Found multiple")
            return
        except Election.DoesNotExist:
            logger.error("CandidateCampaign.election not attached to object, id: " + str(self.google_civic_election_id))
            return
        return election

    def office(self):
        try:
            office = ContestOffice.objects.get(we_vote_id=self.contest_office_we_vote_id)
        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("candidate.office Found multiple")
            return
        except ContestOffice.DoesNotExist:
            logger.error("CandidateCampaign.office not attached to object, we_vote_id: " +
                         str(self.contest_office_we_vote_id))
            return
        return office

    def candidate_photo_url(self):
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

    def display_alternate_names_list(self):
        alternate_names = []
        if self.ballotpedia_candidate_name and (self.ballotpedia_candidate_name != self.display_candidate_name()):
            alternate_names.append(self.ballotpedia_candidate_name)
        if self.google_civic_candidate_name and (self.google_civic_candidate_name != self.display_candidate_name()):
            alternate_names.append(self.google_civic_candidate_name)
        if self.google_civic_candidate_name2 and (self.google_civic_candidate_name2 != self.display_candidate_name()):
            alternate_names.append(self.google_civic_candidate_name2)
        if self.google_civic_candidate_name3 and (self.google_civic_candidate_name3 != self.display_candidate_name()):
            alternate_names.append(self.google_civic_candidate_name3)
        return alternate_names

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
    candidate_list = CandidateListManager()
    results = candidate_list.retrieve_candidate_count_for_office(office_id, office_we_vote_id)
    return results['candidate_count']


def fetch_candidate_count_for_election_and_state(google_civic_election_id, state_code):
    candidate_list = CandidateListManager()
    results = candidate_list.retrieve_candidate_count_for_office(google_civic_election_id, state_code)
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


class CandidateManager(models.Manager):

    def __unicode__(self):
        return "CandidateManager"

    def retrieve_candidate_from_id(self, candidate_id, read_only=False):
        candidate_manager = CandidateManager()
        return candidate_manager.retrieve_candidate(candidate_id, read_only=read_only)

    def retrieve_candidate_from_we_vote_id(self, we_vote_id):
        candidate_id = 0
        candidate_manager = CandidateManager()
        return candidate_manager.retrieve_candidate(candidate_id, we_vote_id)

    def fetch_candidate_id_from_we_vote_id(self, we_vote_id):
        candidate_id = 0
        candidate_manager = CandidateManager()
        results = candidate_manager.retrieve_candidate(candidate_id, we_vote_id)
        if results['success']:
            return results['candidate_id']
        return 0

    def fetch_candidate_we_vote_id_from_id(self, candidate_id):
        we_vote_id = ''
        candidate_manager = CandidateManager()
        results = candidate_manager.retrieve_candidate(candidate_id, we_vote_id)
        if results['success']:
            return results['candidate_we_vote_id']
        return ''

    def fetch_google_civic_candidate_name_from_we_vote_id(self, we_vote_id):
        candidate_id = 0
        candidate_manager = CandidateManager()
        results = candidate_manager.retrieve_candidate(candidate_id, we_vote_id)
        if results['success']:
            candidate = results['candidate']
            return candidate.google_civic_candidate_name
        return 0

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_candidate(
            self,
            candidate_id=0,
            candidate_we_vote_id=None,
            candidate_maplight_id=None,
            candidate_name=None,
            candidate_vote_smart_id=None,
            ballotpedia_candidate_id=None,
            google_civic_election_id=None,
            candidate_year=None,
            read_only=False):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        candidate_on_stage = CandidateCampaign()
        status = ""
        success = True

        try:
            if positive_value_exists(candidate_id):
                if positive_value_exists(read_only):
                    candidate_on_stage = CandidateCampaign.objects.using('readonly').get(
                        id=candidate_id)
                else:
                    candidate_on_stage = CandidateCampaign.objects.get(id=candidate_id)
                candidate_id = candidate_on_stage.id
                candidate_we_vote_id = candidate_on_stage.we_vote_id
                candidate_found = True
                status += "RETRIEVE_CANDIDATE_FOUND_BY_ID "
            elif positive_value_exists(candidate_we_vote_id):
                if positive_value_exists(read_only):
                    candidate_on_stage = CandidateCampaign.objects.using('readonly').get(
                        we_vote_id=candidate_we_vote_id)
                else:
                    candidate_on_stage = CandidateCampaign.objects.get(
                        we_vote_id=candidate_we_vote_id)
                candidate_id = candidate_on_stage.id
                candidate_we_vote_id = candidate_on_stage.we_vote_id
                candidate_found = True
                status += "RETRIEVE_CANDIDATE_FOUND_BY_WE_VOTE_ID "
            elif positive_value_exists(candidate_maplight_id):
                if positive_value_exists(read_only):
                    candidate_on_stage = CandidateCampaign.objects.using('readonly').get(
                        maplight_id=candidate_maplight_id)
                else:
                    candidate_on_stage = CandidateCampaign.objects.get(maplight_id=candidate_maplight_id)
                candidate_id = candidate_on_stage.id
                candidate_we_vote_id = candidate_on_stage.we_vote_id
                candidate_found = True
                status += "RETRIEVE_CANDIDATE_FOUND_BY_MAPLIGHT_ID "
            elif positive_value_exists(candidate_vote_smart_id):
                if positive_value_exists(read_only):
                    candidate_on_stage = CandidateCampaign.objects.using('readonly').get(
                        vote_smart_id=candidate_vote_smart_id)
                else:
                    candidate_on_stage = CandidateCampaign.objects.get(vote_smart_id=candidate_vote_smart_id)
                candidate_id = candidate_on_stage.id
                candidate_we_vote_id = candidate_on_stage.we_vote_id
                candidate_found = True
                status += "RETRIEVE_CANDIDATE_FOUND_BY_VOTE_SMART_ID "
            elif positive_value_exists(candidate_name):
                if positive_value_exists(read_only):
                    if positive_value_exists(candidate_year):
                        candidate_on_stage = CandidateCampaign.objects.using('readonly').get(
                            candidate_name=candidate_name,
                            candidate_year=candidate_year)
                    else:
                        candidate_on_stage = CandidateCampaign.objects.using('readonly').get(
                            candidate_name=candidate_name)
                else:
                    if positive_value_exists(candidate_year):
                        candidate_on_stage = CandidateCampaign.objects.get(candidate_name=candidate_name,
                                                                           candidate_year=candidate_year)
                    else:
                        candidate_on_stage = CandidateCampaign.objects.get(candidate_name=candidate_name)
                candidate_id = candidate_on_stage.id
                candidate_we_vote_id = candidate_on_stage.we_vote_id
                candidate_found = True
                status += "RETRIEVE_CANDIDATE_FOUND_BY_NAME "
            elif positive_value_exists(ballotpedia_candidate_id):
                ballotpedia_candidate_id_integer = convert_to_int(ballotpedia_candidate_id)
                if positive_value_exists(read_only):
                    candidate_on_stage = CandidateCampaign.objects.using('readonly').get(
                        ballotpedia_candidate_id=ballotpedia_candidate_id_integer)
                else:
                    candidate_on_stage = CandidateCampaign.objects.get(
                        ballotpedia_candidate_id=ballotpedia_candidate_id_integer)
                candidate_id = candidate_on_stage.id
                candidate_we_vote_id = candidate_on_stage.we_vote_id
                candidate_found = True
                status += "RETRIEVE_CANDIDATE_FOUND_BY_BALLOTPEDIA_CANDIDATE_ID "
            else:
                candidate_found = False
                status += "RETRIEVE_CANDIDATE_SEARCH_INDEX_MISSING "
                success = False
        except CandidateCampaign.MultipleObjectsReturned as e:
            candidate_found = False
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status += "RETRIEVE_CANDIDATE_MULTIPLE_OBJECTS_RETURNED "
            success = False
        except CandidateCampaign.DoesNotExist:
            candidate_found = False
            exception_does_not_exist = True
            status += "RETRIEVE_CANDIDATE_NOT_FOUND "
        except Exception as e:
            candidate_found = False
            status += "RETRIEVE_CANDIDATE_NOT_FOUND_EXCEPTION " + str(e) + " "
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'candidate_found':          candidate_found,
            'candidate_id':             convert_to_int(candidate_id),
            'candidate_we_vote_id':     candidate_we_vote_id,
            'candidate':                candidate_on_stage,
        }
        return results

    def retrieve_candidate_from_ballotpedia_candidate_id(
            self, ballotpedia_candidate_id, read_only=False):
        candidate_id = 0
        we_vote_id = ''
        candidate_maplight_id = ''
        candidate_name = ''
        candidate_vote_smart_id = 0
        return self.retrieve_candidate(
            candidate_id, we_vote_id, candidate_maplight_id, candidate_name, candidate_vote_smart_id,
            ballotpedia_candidate_id, read_only=read_only)

    def retrieve_candidate_from_candidate_name(self, candidate_name):
        candidate_id = 0
        we_vote_id = ''
        candidate_maplight_id = ''
        candidate_manager = CandidateManager()

        results = candidate_manager.retrieve_candidate(
            candidate_id, we_vote_id, candidate_maplight_id, candidate_name)
        if results['success']:
            return results

        # Try to modify the candidate name, and search again
        # MapLight for example will pass in "Ronald  Gold" for example
        candidate_name_try2 = candidate_name.replace('  ', ' ')
        results = candidate_manager.retrieve_candidate(
            candidate_id, we_vote_id, candidate_maplight_id, candidate_name_try2)
        if results['success']:
            return results

        # MapLight also passes in "Kamela D Harris" for example, and Google Civic uses "Kamela D. Harris"
        candidate_name_try3 = mimic_google_civic_initials(candidate_name)
        if candidate_name_try3 != candidate_name:
            results = candidate_manager.retrieve_candidate(
                candidate_id, we_vote_id, candidate_maplight_id, candidate_name_try3)
            if results['success']:
                return results

        # Otherwise return failed results
        return results

    def retrieve_candidate_from_maplight_id(self, candidate_maplight_id):
        candidate_id = 0
        we_vote_id = ''
        candidate_manager = CandidateManager()
        return candidate_manager.retrieve_candidate(
            candidate_id, we_vote_id, candidate_maplight_id)

    def retrieve_candidate_from_vote_smart_id(self, candidate_vote_smart_id):
        candidate_id = 0
        we_vote_id = ''
        candidate_maplight_id = ''
        candidate_name = ''
        candidate_manager = CandidateManager()
        return candidate_manager.retrieve_candidate(
            candidate_id, we_vote_id, candidate_maplight_id, candidate_name, candidate_vote_smart_id)

    def retrieve_candidate_from_vote_usa_variables(
            self,
            vote_usa_politician_id='',
            vote_usa_office_id='',
            google_civic_election_id=0,
            read_only=True):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        candidate_found = False
        candidate_id = 0
        candidate_on_stage = None
        candidate_options_found = False
        candidate_we_vote_id = ''
        candidate_we_vote_id_list = []
        status = ""
        success = True

        try:
            if positive_value_exists(read_only):
                candidate_query = CandidateCampaign.objects.using('readonly').all()
            else:
                candidate_query = CandidateCampaign.objects.all()
            candidate_query = candidate_query.filter(
                vote_usa_politician_id=vote_usa_politician_id,
                vote_usa_office_id=vote_usa_office_id,
            )
            candidate_we_vote_id_list = candidate_query.values_list('we_vote_id', flat=True)
            if len(candidate_we_vote_id_list) > 0:
                candidate_options_found = True
                status += "CANDIDATE_LIST_FROM_VOTE_USA_POLITICIAN_RETRIEVED "
            else:
                exception_does_not_exist = True
                status += "CANDIDATE_LIST_FROM_VOTE_USA_POLITICIAN_NOT_FOUND "
        except Exception as e:
            candidate_found = False
            status += "CANDIDATE_LIST_FROM_VOTE_USA_POLITICIAN_EXCEPTION: " + str(e) + " "
            success = False

        if candidate_options_found:
            candidate_list_manager = CandidateListManager()
            results = candidate_list_manager.retrieve_candidate_to_office_link_list(
                candidate_we_vote_id_list=candidate_we_vote_id_list,
                google_civic_election_id_list=[google_civic_election_id],
                read_only=True,
            )
            if results['success']:
                candidate_to_office_link_list = results['candidate_to_office_link_list']
                if len(candidate_to_office_link_list) > 1:
                    candidate_found = False
                    exception_multiple_object_returned = True
                elif len(candidate_to_office_link_list) == 1:
                    candidate_found = True
                    candidate_to_office_link = candidate_to_office_link_list[0]
                    if positive_value_exists(candidate_to_office_link.candidate_we_vote_id):
                        candidate_manager = CandidateManager()
                        return candidate_manager.retrieve_candidate_from_we_vote_id(
                            candidate_to_office_link.candidate_we_vote_id)
                else:
                    candidate_found = False

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'candidate_found':          candidate_found,
            'candidate_id':             candidate_id,
            'candidate_we_vote_id':     candidate_we_vote_id,
            'candidate':                candidate_on_stage,
        }
        return results

    def retrieve_candidates_are_not_duplicates(self, candidate1_we_vote_id, candidate2_we_vote_id, read_only=True):
        candidates_are_not_duplicates = CandidatesAreNotDuplicates()
        status = ""
        # Note that the direction of the friendship does not matter
        try:
            if positive_value_exists(read_only):
                candidates_are_not_duplicates = CandidatesAreNotDuplicates.objects.using('readonly').get(
                    candidate1_we_vote_id__iexact=candidate1_we_vote_id,
                    candidate2_we_vote_id__iexact=candidate2_we_vote_id,
                )
            else:
                candidates_are_not_duplicates = CandidatesAreNotDuplicates.objects.get(
                    candidate1_we_vote_id__iexact=candidate1_we_vote_id,
                    candidate2_we_vote_id__iexact=candidate2_we_vote_id,
                )
            candidates_are_not_duplicates_found = True
            success = True
            status += "CANDIDATES_NOT_DUPLICATES_UPDATED_OR_CREATED1 "
        except CandidatesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            candidates_are_not_duplicates_found = False
            status += 'NO_CANDIDATES_NOT_DUPLICATES_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            candidates_are_not_duplicates_found = False
            candidates_are_not_duplicates = CandidatesAreNotDuplicates()
            success = False
            status += "CANDIDATES_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED1 " + str(e) + ' '

        if not candidates_are_not_duplicates_found and success:
            try:
                if positive_value_exists(read_only):
                    candidates_are_not_duplicates = CandidatesAreNotDuplicates.objects.using('readonly').get(
                        candidate1_we_vote_id__iexact=candidate2_we_vote_id,
                        candidate2_we_vote_id__iexact=candidate1_we_vote_id,
                    )
                else:
                    candidates_are_not_duplicates = CandidatesAreNotDuplicates.objects.get(
                        candidate1_we_vote_id__iexact=candidate2_we_vote_id,
                        candidate2_we_vote_id__iexact=candidate1_we_vote_id,
                    )
                candidates_are_not_duplicates_found = True
                success = True
                status += "CANDIDATES_NOT_DUPLICATES_UPDATED_OR_CREATED2 "
            except CandidatesAreNotDuplicates.DoesNotExist:
                # No data found. Try again below
                success = True
                candidates_are_not_duplicates_found = False
                status += 'NO_CANDIDATES_NOT_DUPLICATES_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                candidates_are_not_duplicates_found = False
                candidates_are_not_duplicates = CandidatesAreNotDuplicates()
                success = False
                status += "CANDIDATES_NOT_DUPLICATES_NOT_UPDATED_OR_CREATED2 " + str(e) + ' '

        results = {
            'success':                              success,
            'status':                               status,
            'candidates_are_not_duplicates_found':  candidates_are_not_duplicates_found,
            'candidates_are_not_duplicates':        candidates_are_not_duplicates,
        }
        return results

    def retrieve_candidates_are_not_duplicates_list(self, candidate_we_vote_id, read_only=True):
        """
        Get a list of other candidate_we_vote_id's that are not duplicates
        :param candidate_we_vote_id:
        :param read_only:
        :return:
        """
        # Note that the direction of the linkage does not matter
        candidates_are_not_duplicates_list1 = []
        candidates_are_not_duplicates_list2 = []
        status = ""
        try:
            if positive_value_exists(read_only):
                candidates_are_not_duplicates_list_query = CandidatesAreNotDuplicates.objects.using('readonly').filter(
                    candidate1_we_vote_id__iexact=candidate_we_vote_id,
                )
            else:
                candidates_are_not_duplicates_list_query = CandidatesAreNotDuplicates.objects.filter(
                    candidate1_we_vote_id__iexact=candidate_we_vote_id,
                )
            candidates_are_not_duplicates_list1 = list(candidates_are_not_duplicates_list_query)
            success = True
            status += "CANDIDATES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except CandidatesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status += 'NO_CANDIDATES_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status += "CANDIDATES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1 " + str(e) + ' '

        if success:
            try:
                if positive_value_exists(read_only):
                    candidates_are_not_duplicates_list_query = \
                        CandidatesAreNotDuplicates.objects.using('readonly').filter(
                            candidate2_we_vote_id__iexact=candidate_we_vote_id,
                        )
                else:
                    candidates_are_not_duplicates_list_query = \
                        CandidatesAreNotDuplicates.objects.filter(
                            candidate2_we_vote_id__iexact=candidate_we_vote_id,
                        )
                candidates_are_not_duplicates_list2 = list(candidates_are_not_duplicates_list_query)
                success = True
                status += "CANDIDATES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except CandidatesAreNotDuplicates.DoesNotExist:
                success = True
                status += 'NO_CANDIDATES_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status += "CANDIDATES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2 " + str(e) + ' '

        candidates_are_not_duplicates_list = candidates_are_not_duplicates_list1 + candidates_are_not_duplicates_list2
        candidates_are_not_duplicates_list_found = positive_value_exists(len(candidates_are_not_duplicates_list))
        candidates_are_not_duplicates_list_we_vote_ids = []
        for one_entry in candidates_are_not_duplicates_list:
            if one_entry.candidate1_we_vote_id != candidate_we_vote_id:
                candidates_are_not_duplicates_list_we_vote_ids.append(one_entry.candidate1_we_vote_id)
            elif one_entry.candidate2_we_vote_id != candidate_we_vote_id:
                candidates_are_not_duplicates_list_we_vote_ids.append(one_entry.candidate2_we_vote_id)
        results = {
            'success':                                  success,
            'status':                                   status,
            'candidates_are_not_duplicates_list_found': candidates_are_not_duplicates_list_found,
            'candidates_are_not_duplicates_list':       candidates_are_not_duplicates_list,
            'candidates_are_not_duplicates_list_we_vote_ids': candidates_are_not_duplicates_list_we_vote_ids,
        }
        return results

    def retrieve_candidate_to_office_link(
            self,
            candidate_we_vote_id='',
            contest_office_we_vote_id='',
            google_civic_election_id=0,
            state_code='',
            read_only=True):
        """
        See also retrieve_candidate_to_office_link_list
        :param candidate_we_vote_id:
        :param contest_office_we_vote_id:
        :param google_civic_election_id:
        :param state_code:
        :param read_only:
        :return:
        """
        candidate_to_office_link = None
        link_list = []
        status = ""
        success = True
        google_civic_election_id = convert_to_int(google_civic_election_id)

        try:
            if positive_value_exists(read_only):
                query = CandidateToOfficeLink.objects.using('readonly').all()
            else:
                query = CandidateToOfficeLink.objects.all()
            if positive_value_exists(candidate_we_vote_id):
                query = query.filter(candidate_we_vote_id=candidate_we_vote_id)
            if positive_value_exists(contest_office_we_vote_id):
                query = query.filter(contest_office_we_vote_id=contest_office_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                query = query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(state_code):
                query = query.filter(state_code=state_code)

            link_list = list(query)
            if len(link_list) == 1:
                list_found = True
                only_one_found = True
                candidate_to_office_link = link_list[0]
            elif len(link_list) > 1:
                list_found = True
                only_one_found = False
            else:
                list_found = False
                only_one_found = False
        except Exception as e:
            list_found = False
            only_one_found = False
            status += "RETRIEVE_CANDIDATE_TO_OFFICE_LINK-ERROR: " + str(e) + " "
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'candidate_to_office_link': candidate_to_office_link,
            'list_found':               list_found,
            'only_one_found':           only_one_found,
            'candidate_to_office_link_list':    link_list,
        }
        return results

    def fetch_next_upcoming_election_id_for_candidate(self, candidate_we_vote_id):
        results = self.retrieve_candidate_to_office_link(candidate_we_vote_id=candidate_we_vote_id)
        if not positive_value_exists(results['success']):
            return 0
        if results['only_one_found']:
            candidate_to_office_link = results['candidate_to_office_link']
            return candidate_to_office_link.google_civic_election_id
        if results['list_found']:
            candidate_to_office_link_list = results['candidate_to_office_link_list']
            google_civic_election_id_list = []
            for candidate_to_office_link in candidate_to_office_link_list:
                if positive_value_exists(candidate_to_office_link.google_civic_election_id):
                    google_civic_election_id_list.append(candidate_to_office_link.google_civic_election_id)
            election_manager = ElectionManager()
            return election_manager.fetch_google_civic_election_id_from_list(google_civic_election_id_list)
        return 0

    def fetch_candidates_are_not_duplicates_list_we_vote_ids(self, candidate_we_vote_id):
        results = self.retrieve_candidates_are_not_duplicates_list(candidate_we_vote_id)
        return results['candidates_are_not_duplicates_list_we_vote_ids']

    def update_or_create_candidate(
            self,
            candidate_we_vote_id='',
            google_civic_election_id='',
            ocd_division_id='',
            contest_office_id=0,
            contest_office_we_vote_id='',
            google_civic_candidate_name='',
            updated_candidate_values={}):
        """
        Either update or create a candidate entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_candidate_created = False
        candidate_on_stage = CandidateCampaign()
        candidate_found = False
        status = ""
        google_civic_candidate_name2 = updated_candidate_values['google_civic_candidate_name2'] \
            if 'google_civic_candidate_name2' in updated_candidate_values else ""
        google_civic_candidate_name3 = updated_candidate_values['google_civic_candidate_name3'] \
            if 'google_civic_candidate_name3' in updated_candidate_values else ""

        if not positive_value_exists(google_civic_election_id):
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID '
        # We are avoiding requiring ocd_division_id
        # elif not positive_value_exists(ocd_division_id):
        #     success = False
        #     status += 'MISSING_OCD_DIVISION_ID '
        # DALE 2016-02-20 We are not requiring contest_office_id or contest_office_we_vote_id to match a candidate
        # elif not positive_value_exists(contest_office_we_vote_id): # and not positive_value_exists(contest_office_id):
        #     success = False
        #     status += 'MISSING_CONTEST_OFFICE_ID '
        elif not positive_value_exists(google_civic_candidate_name):
            success = False
            status += 'MISSING_GOOGLE_CIVIC_CANDIDATE_NAME '
        elif positive_value_exists(candidate_we_vote_id) and positive_value_exists(contest_office_we_vote_id):
            try:
                candidate_on_stage, new_candidate_created = \
                    CandidateCampaign.objects.update_or_create(
                        # google_civic_election_id__exact=google_civic_election_id,
                        we_vote_id__iexact=candidate_we_vote_id,
                        # contest_office_we_vote_id__iexact=contest_office_we_vote_id,
                        defaults=updated_candidate_values)
                candidate_found = True
                success = True
                status += "CANDIDATE_CAMPAIGN_UPDATED_OR_CREATED_BY_CANDIDATE_WE_VOTE_ID "
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
            try:
                if not positive_value_exists(google_civic_candidate_name):
                    google_civic_candidate_name = "NO_NAME_IGNORE"
                if not positive_value_exists(google_civic_candidate_name2):
                    google_civic_candidate_name2 = "NO_NAME_IGNORE"
                if not positive_value_exists(google_civic_candidate_name3):
                    google_civic_candidate_name3 = "NO_NAME_IGNORE"
                candidate_on_stage = CandidateCampaign.objects.get(
                    Q(google_civic_candidate_name__iexact=google_civic_candidate_name) |
                    Q(google_civic_candidate_name2__iexact=google_civic_candidate_name) |
                    Q(google_civic_candidate_name3__iexact=google_civic_candidate_name) |
                    Q(google_civic_candidate_name__iexact=google_civic_candidate_name2) |
                    Q(google_civic_candidate_name2__iexact=google_civic_candidate_name2) |
                    Q(google_civic_candidate_name3__iexact=google_civic_candidate_name2) |
                    Q(google_civic_candidate_name__iexact=google_civic_candidate_name3) |
                    Q(google_civic_candidate_name2__iexact=google_civic_candidate_name3) |
                    Q(google_civic_candidate_name3__iexact=google_civic_candidate_name3),
                    google_civic_election_id__exact=google_civic_election_id,
                )
                candidate_found = True
                success = True
                status += "CANDIDATE_CAMPAIGN_UPDATED_OR_CREATED_BY_GOOGLE_CIVIC_CANDIDATE_NAME "
            except CandidateCampaign.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_GOOGLE_CIVIC_CANDIDATE_NAME '
                exception_multiple_object_returned = True
            except CandidateCampaign.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND_BY_GOOGLE_CIVIC_CANDIDATE_NAME1 "

                # Since Google Civic doesn't provide a unique identifier, and sometimes returns initials with
                # a period and sometimes without, we may need to try again
                name_changed = False
                google_civic_candidate_name_modified = "NO_NAME_IGNORE"
                google_civic_candidate_name2_modified = "NO_NAME_IGNORE"
                google_civic_candidate_name3_modified = "NO_NAME_IGNORE"
                google_civic_candidate_name_new_start = google_civic_candidate_name
                google_civic_candidate_name2_new_start = google_civic_candidate_name2
                google_civic_candidate_name3_new_start = google_civic_candidate_name3

                # If an initial exists in the name (ex/ " A "), then search for the name
                # with a period added (ex/ " A. ")
                # google_civic_candidate_name
                add_results = add_period_to_middle_name_initial(google_civic_candidate_name)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name_modified = add_results['modified_name']
                    google_civic_candidate_name_new_start = google_civic_candidate_name_modified
                else:
                    add_results = remove_period_from_middle_name_initial(google_civic_candidate_name)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name_modified = add_results['modified_name']
                        google_civic_candidate_name_new_start = google_civic_candidate_name_modified
                # google_civic_candidate_name2
                add_results = add_period_to_middle_name_initial(google_civic_candidate_name2)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name2_modified = add_results['modified_name']
                    google_civic_candidate_name2_new_start = google_civic_candidate_name2_modified
                else:
                    add_results = remove_period_from_middle_name_initial(google_civic_candidate_name2)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name2_modified = add_results['modified_name']
                        google_civic_candidate_name2_new_start = google_civic_candidate_name2_modified
                # google_civic_candidate_name3
                add_results = add_period_to_middle_name_initial(google_civic_candidate_name3)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name3_modified = add_results['modified_name']
                    google_civic_candidate_name3_new_start = google_civic_candidate_name3_modified
                else:
                    add_results = remove_period_from_middle_name_initial(google_civic_candidate_name3)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name3_modified = add_results['modified_name']
                        google_civic_candidate_name3_new_start = google_civic_candidate_name3_modified

                # Deal with prefix and suffix
                # If an prefix or suffix exists in the name (ex/ " JR"), then search for the name
                # with a period added (ex/ " JR.")
                # google_civic_candidate_name
                add_results = add_period_to_name_prefix_and_suffix(google_civic_candidate_name_new_start)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_name_prefix_and_suffix(google_civic_candidate_name_new_start)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name_modified = add_results['modified_name']
                # google_civic_candidate_name2
                add_results = add_period_to_name_prefix_and_suffix(google_civic_candidate_name2_new_start)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name2_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_name_prefix_and_suffix(google_civic_candidate_name2_new_start)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name2_modified = add_results['modified_name']
                # google_civic_candidate_name3
                add_results = add_period_to_name_prefix_and_suffix(google_civic_candidate_name3_new_start)
                if add_results['name_changed']:
                    name_changed = True
                    google_civic_candidate_name3_modified = add_results['modified_name']
                else:
                    add_results = remove_period_from_name_prefix_and_suffix(google_civic_candidate_name3_new_start)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name3_modified = add_results['modified_name']

                if name_changed:
                    try:
                        candidate_on_stage = CandidateCampaign.objects.get(
                            Q(google_civic_candidate_name__iexact=google_civic_candidate_name_modified) |
                            Q(google_civic_candidate_name2__iexact=google_civic_candidate_name_modified) |
                            Q(google_civic_candidate_name3__iexact=google_civic_candidate_name_modified) |
                            Q(google_civic_candidate_name__iexact=google_civic_candidate_name2_modified) |
                            Q(google_civic_candidate_name2__iexact=google_civic_candidate_name2_modified) |
                            Q(google_civic_candidate_name3__iexact=google_civic_candidate_name2_modified) |
                            Q(google_civic_candidate_name__iexact=google_civic_candidate_name3_modified) |
                            Q(google_civic_candidate_name2__iexact=google_civic_candidate_name3_modified) |
                            Q(google_civic_candidate_name3__iexact=google_civic_candidate_name3_modified),
                            google_civic_election_id__exact=google_civic_election_id,
                        )
                        candidate_found = True
                        success = True
                        status += "CANDIDATE_CAMPAIGN_UPDATED_OR_CREATED_BY_GOOGLE_CIVIC_CANDIDATE_NAME_MODIFIED "
                    except CandidateCampaign.MultipleObjectsReturned as e:
                        success = False
                        status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_GOOGLE_CIVIC_CANDIDATE_NAME_MODIFIED '
                        exception_multiple_object_returned = True
                    except CandidateCampaign.DoesNotExist:
                        exception_does_not_exist = True
                        status += "RETRIEVE_OFFICE_NOT_FOUND_BY_GOOGLE_CIVIC_CANDIDATE_NAME_MODIFIED "
                    except Exception as e:
                        status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME_MODIFIED ' \
                                  '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_CANDIDATE_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

            if not candidate_found and not exception_multiple_object_returned:
                # Try to find record based on candidate_name (instead of google_civic_office_name)
                try:
                    candidate_on_stage = CandidateCampaign.objects.get(
                        Q(candidate_name__iexact=google_civic_candidate_name) |
                        Q(candidate_name__iexact=google_civic_candidate_name2) |
                        Q(candidate_name__iexact=google_civic_candidate_name3),
                        google_civic_election_id__exact=google_civic_election_id,
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

                    # Since Google Civic doesn't provide a unique identifier, and sometimes returns initials with
                    # a period and sometimes without, we may need to try again
                    name_changed = False
                    google_civic_candidate_name_modified = "NO_NAME_IGNORE"
                    google_civic_candidate_name2_modified = "NO_NAME_IGNORE"
                    google_civic_candidate_name3_modified = "NO_NAME_IGNORE"
                    # If an initial exists in the name (ex/ " A "), then search for the name
                    # with a period added (ex/ " A. ")
                    # google_civic_candidate_name
                    add_results = add_period_to_middle_name_initial(google_civic_candidate_name)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name_modified = add_results['modified_name']
                    else:
                        add_results = remove_period_from_middle_name_initial(google_civic_candidate_name)
                        if add_results['name_changed']:
                            name_changed = True
                            google_civic_candidate_name_modified = add_results['modified_name']
                    # google_civic_candidate_name2
                    add_results = add_period_to_middle_name_initial(google_civic_candidate_name2)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name2_modified = add_results['modified_name']
                    else:
                        add_results = remove_period_from_middle_name_initial(google_civic_candidate_name2)
                        if add_results['name_changed']:
                            name_changed = True
                            google_civic_candidate_name2_modified = add_results['modified_name']
                    # google_civic_candidate_name3
                    add_results = add_period_to_middle_name_initial(google_civic_candidate_name3)
                    if add_results['name_changed']:
                        name_changed = True
                        google_civic_candidate_name3_modified = add_results['modified_name']
                    else:
                        add_results = remove_period_from_middle_name_initial(google_civic_candidate_name3)
                        if add_results['name_changed']:
                            name_changed = True
                            google_civic_candidate_name3_modified = add_results['modified_name']

                    if name_changed and positive_value_exists(google_civic_candidate_name_modified):
                        try:
                            candidate_on_stage = CandidateCampaign.objects.get(
                                Q(candidate_name__iexact=google_civic_candidate_name_modified) |
                                Q(candidate_name__iexact=google_civic_candidate_name2_modified) |
                                Q(candidate_name__iexact=google_civic_candidate_name3_modified),
                                google_civic_election_id__exact=google_civic_election_id
                            )
                            candidate_found = True
                            success = True
                            status += "CANDIDATE_CAMPAIGN_UPDATED_OR_CREATED_BY_CANDIDATE_NAME_MODIFIED "
                        except CandidateCampaign.MultipleObjectsReturned as e:
                            success = False
                            status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_CANDIDATE_NAME_MODIFIED '
                            exception_multiple_object_returned = True
                        except CandidateCampaign.DoesNotExist:
                            exception_does_not_exist = True
                            status += "RETRIEVE_OFFICE_NOT_FOUND_BY_CANDIDATE_NAME_MODIFIED "
                        except Exception as e:
                            status += 'FAILED_TO_RETRIEVE_OFFICE_BY_CANDIDATE_NAME_MODIFIED ' \
                                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                except Exception as e:
                    status += 'FAILED_TO_RETRIEVE_OFFICE_BY_CANDIDATE_NAME ' \
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
                    new_candidate_created = False
                    candidate_updated = False
                    candidate_changes_found = False
                    for key, value in updated_candidate_values.items():
                        if hasattr(candidate_on_stage, key):
                            candidate_changes_found = True
                            setattr(candidate_on_stage, key, value)
                    if candidate_changes_found and positive_value_exists(candidate_on_stage.we_vote_id):
                        candidate_on_stage.save()
                        candidate_updated = True
                    if candidate_updated:
                        success = True
                        status += "CANDIDATE_UPDATED "
                    else:
                        success = False
                        status += "CANDIDATE_NOT_UPDATED "
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_CANDIDATE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    new_candidate_created = False
                    candidate_on_stage = CandidateCampaign.objects.create(
                        google_civic_election_id=google_civic_election_id,
                        ocd_division_id=ocd_division_id,
                        contest_office_id=contest_office_id,
                        contest_office_we_vote_id=contest_office_we_vote_id,
                        google_civic_candidate_name=google_civic_candidate_name)
                    candidate_found = True
                    if positive_value_exists(candidate_on_stage.id):
                        for key, value in updated_candidate_values.items():
                            if hasattr(candidate_on_stage, key):
                                setattr(candidate_on_stage, key, value)
                        candidate_on_stage.save()
                        new_candidate_created = True
                    if new_candidate_created:
                        success = True
                        status += "CANDIDATE_CREATED "
                    else:
                        success = False
                        status += "CANDIDATE_NOT_CREATED "

                except Exception as e:
                    status += 'FAILED_TO_CREATE_CANDIDATE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_candidate_created':    new_candidate_created,
            'candidate':                candidate_on_stage,
            'candidate_found':          candidate_found,
        }
        return results

    def update_or_create_candidates_are_not_duplicates(self, candidate1_we_vote_id, candidate2_we_vote_id):
        """
        Either update or create a candidate entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_candidates_are_not_duplicates_created = False
        candidates_are_not_duplicates = CandidatesAreNotDuplicates()
        status = ""

        if positive_value_exists(candidate1_we_vote_id) and positive_value_exists(candidate2_we_vote_id):
            try:
                updated_values = {
                    'candidate1_we_vote_id':    candidate1_we_vote_id,
                    'candidate2_we_vote_id':    candidate2_we_vote_id,
                }
                candidates_are_not_duplicates, new_candidates_are_not_duplicates_created = \
                    CandidatesAreNotDuplicates.objects.update_or_create(
                        candidate1_we_vote_id__exact=candidate1_we_vote_id,
                        candidate2_we_vote_id__iexact=candidate2_we_vote_id,
                        defaults=updated_values)
                success = True
                status += "CANDIDATES_ARE_NOT_DUPLICATES_UPDATED_OR_CREATED "
            except CandidatesAreNotDuplicates.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CANDIDATES_ARE_NOT_DUPLICATES_FOUND_BY_CANDIDATE_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'EXCEPTION_UPDATE_OR_CREATE_CANDIDATES_ARE_NOT_DUPLICATES ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                                      success,
            'status':                                       status,
            'MultipleObjectsReturned':                      exception_multiple_object_returned,
            'new_candidates_are_not_duplicates_created':    new_candidates_are_not_duplicates_created,
            'candidates_are_not_duplicates':                candidates_are_not_duplicates,
        }
        return results

    def add_candidate_position_sorting_dates_if_needed(self, position_object=None, candidate=None):
        generate_sorting_dates = False
        position_object_updated = False
        candidate_year_changed = False
        candidate_ultimate_election_date_changed = False
        status = ""
        success = True

        if positive_value_exists(candidate.candidate_year):
            position_object.position_year = candidate.candidate_year
            position_object_updated = True
        else:
            generate_sorting_dates = True
        if positive_value_exists(candidate.candidate_ultimate_election_date):
            position_object.position_ultimate_election_date = candidate.candidate_ultimate_election_date
            position_object_updated = True
        else:
            generate_sorting_dates = True

        if generate_sorting_dates:
            largest_year_integer = None
            largest_election_date_integer = None
            candidate_manager = CandidateManager()
            date_results = candidate_manager.generate_candidate_position_sorting_dates(
                candidate_we_vote_id=candidate.we_vote_id)
            if positive_value_exists(date_results['largest_year_integer']):
                if candidate.candidate_year != date_results['largest_year_integer']:
                    candidate_year_changed = True
                if not position_object.position_year:
                    position_object.position_year = date_results['largest_year_integer']
                    position_object_updated = True
                elif date_results['largest_year_integer'] > position_object.position_year:
                    position_object.position_year = date_results['largest_year_integer']
                    position_object_updated = True
            if positive_value_exists(date_results['largest_election_date_integer']):
                if candidate.candidate_ultimate_election_date != date_results['largest_election_date_integer']:
                    candidate_ultimate_election_date_changed = True
                if not position_object.position_ultimate_election_date:
                    position_object.position_ultimate_election_date = date_results['largest_election_date_integer']
                    position_object_updated = True
                elif date_results['largest_election_date_integer'] > position_object.position_ultimate_election_date:
                    position_object.position_ultimate_election_date = date_results['largest_election_date_integer']
                    position_object_updated = True
            if candidate_year_changed or candidate_ultimate_election_date_changed:
                # Retrieve an editable copy of the candidate so we can update the date caches
                results = \
                    candidate_manager.retrieve_candidate_from_we_vote_id(candidate.we_vote_id)
                if results['candidate_found']:
                    editable_candidate = results['candidate']
                    try:
                        if candidate_year_changed:
                            editable_candidate.candidate_year = largest_year_integer
                        if candidate_ultimate_election_date_changed:
                            editable_candidate.candidate_ultimate_election_date = largest_election_date_integer
                        editable_candidate.save()
                        status += "SAVED_EDITABLE_CAMPAIGN "
                    except Exception as e:
                        status += "FAILED_TO_SAVE_EDITABLE_CAMPAIGN: " + str(e) + " "

        return {
            'position_object_updated':  position_object_updated,
            'position_object':          position_object,
            'status':                   status,
            'success':                  success,
        }

    def generate_candidate_position_sorting_dates(self, candidate_we_vote_id=''):
        largest_year_integer = 0
        largest_election_date_integer = 0
        results = self.retrieve_candidate_to_office_link(
            candidate_we_vote_id=candidate_we_vote_id,
            read_only=True)
        candidate_to_office_link_list = results['candidate_to_office_link_list']
        election_manager = ElectionManager()
        google_civic_election_id_reviewed_list = []
        for one_link in candidate_to_office_link_list:
            if positive_value_exists(one_link.google_civic_election_id) and \
                    one_link.google_civic_election_id not in google_civic_election_id_reviewed_list:
                results = election_manager.retrieve_election(google_civic_election_id=one_link.google_civic_election_id)
                if results['election_found']:
                    election = results['election']
                    if positive_value_exists(election.election_day_text):
                        year_string = election.election_day_text[:4]
                        year_integer = convert_to_int(year_string)
                        if year_integer > largest_year_integer:
                            largest_year_integer = year_integer
                        election_day_text = election.election_day_text.replace('-', '')
                        election_date_integer = convert_to_int(election_day_text)
                        if election_date_integer > largest_election_date_integer:
                            largest_election_date_integer = election_date_integer
                google_civic_election_id_reviewed_list.append(one_link.google_civic_election_id)
        return {
            'largest_year_integer': largest_year_integer,
            'largest_election_date_integer':  largest_election_date_integer,
        }

    def get_or_create_candidate_to_office_link(
            self,
            candidate_we_vote_id='',
            contest_office_we_vote_id='',
            google_civic_election_id=0,
            state_code=''):
        exception_multiple_object_returned = False
        success = True
        new_candidate_to_office_link_created = False
        candidate_to_office_link = None
        status = ""

        candidate_we_vote_id = str(candidate_we_vote_id).strip()
        contest_office_we_vote_id = str(contest_office_we_vote_id).strip()
        google_civic_election_id = str(google_civic_election_id).strip()
        google_civic_election_id = convert_to_int(google_civic_election_id)
        try:
            state_code = state_code.upper()
        except Exception as e:
            pass

        try:
            candidate_to_office_link, new_candidate_to_office_link_created = \
                CandidateToOfficeLink.objects.get_or_create(
                    candidate_we_vote_id=candidate_we_vote_id,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code)
            status += "CANDIDATE_TO_OFFICE_LINK_GET_OR_CREATE-SUCCESS "
        except CandidateToOfficeLink.MultipleObjectsReturned as e:
            success = False
            status += 'ERROR-MULTIPLE_MATCHING_CANDIDATE_TO_OFFICE_LINK_FOUND: ' + str(e) + ' '
            status += '[candidate_we_vote_id: ' + str(candidate_we_vote_id) + ' '
            status += 'contest_office_we_vote_id: ' + str(contest_office_we_vote_id) + ' '
            status += 'google_civic_election_id: ' + str(google_civic_election_id) + ' '
            status += 'state_code: ' + str(state_code) + '] '
            exception_multiple_object_returned = True
            handle_exception(e, logger=logger, exception_message=status)
        except Exception as e:
            status += 'EXCEPTION_UPDATE_OR_CREATE_CANDIDATE_TO_OFFICE_LINK ' + str(e) + ' '
            success = False

        if new_candidate_to_office_link_created:
            election_manager = ElectionManager()
            results = election_manager.retrieve_election(google_civic_election_id=google_civic_election_id)
            position_year = None
            position_ultimate_election_date = None
            if results['election_found']:
                election = results['election']
                if positive_value_exists(election.election_day_text):
                    year_string = election.election_day_text[:4]
                    position_year = convert_to_int(year_string)
                    election_day_text = election.election_day_text.replace('-', '')
                    position_ultimate_election_date = convert_to_int(election_day_text)
            if positive_value_exists(position_year) and positive_value_exists(position_ultimate_election_date):
                from position.controllers import update_positions_and_candidate_position_year
                results = update_positions_and_candidate_position_year(
                    position_year=position_year, candidate_we_vote_id_list=[candidate_we_vote_id])
                if results['success']:
                    candidate_year_update_count = results['candidate_year_update_count']
                    friends_position_year_candidate_update_count = \
                        results['friends_position_year_candidate_update_count']
                    public_position_year_candidate_update_count = \
                        results['public_position_year_candidate_update_count']
                    status += "[candidate_year_updates: " + str(candidate_year_update_count) + \
                              ", friends_year_updates: " + str(friends_position_year_candidate_update_count) + \
                              ", public_year_updates: " + str(public_position_year_candidate_update_count) + "] "

                from position.controllers import update_positions_and_candidate_position_ultimate_election_date
                results = update_positions_and_candidate_position_ultimate_election_date(
                    position_ultimate_election_date=position_ultimate_election_date,
                    candidate_we_vote_id_list=[candidate_we_vote_id])
                if results['success']:
                    candidate_ultimate_update_count = results['candidate_ultimate_update_count']
                    friends_ultimate_candidate_update_count = results['friends_ultimate_candidate_update_count']
                    public_ultimate_candidate_update_count = results['public_ultimate_candidate_update_count']
                    status += \
                        "[candidate_ultimate_updates: " + str(candidate_ultimate_update_count) + \
                        ", friends_ultimate_updates: " + str(friends_ultimate_candidate_update_count) + \
                        ", public_ultimate_updates: " + str(public_ultimate_candidate_update_count) + "] "

        results = {
            'success':                              success,
            'status':                               status,
            'MultipleObjectsReturned':              exception_multiple_object_returned,
            'new_candidate_to_office_link_created': new_candidate_to_office_link_created,
            'candidate_to_office_link':             candidate_to_office_link,
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
                    if len(str(candidate_twitter_handle)) > 255:
                        candidate_twitter_handle = str(candidate_twitter_handle)
                        candidate_twitter_handle = candidate_twitter_handle[:255]
                        pass
                    candidate.candidate_twitter_handle = candidate_twitter_handle
                    values_changed = True
            if candidate_facebook:
                if candidate_facebook != candidate.facebook_url:
                    if len(str(candidate_facebook)) > 200:
                        candidate_facebook = str(candidate_facebook)
                        candidate_facebook = candidate_facebook[:200]
                    candidate.facebook_url = candidate_facebook
                    values_changed = True

            if values_changed:
                candidate.save()
                success = True
                status += "SAVED_CANDIDATE_SOCIAL_MEDIA "
            else:
                success = True
                status += "NO_CHANGES_SAVED_TO_CANDIDATE_SOCIAL_MEDIA "

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'candidate':                candidate,
        }
        return results

    def update_candidate_ballotpedia_image_details(
            self, candidate,
            cached_ballotpedia_profile_image_url_https,
            we_vote_hosted_profile_image_url_large,
            we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny):
        """
        Update a candidate entry with the latest image details.
        """
        success = False
        status = "ENTERING_UPDATE_CANDIDATE_BALLOTPEDIA_IMAGE_DETAILS"
        values_changed = False

        if candidate:
            if positive_value_exists(cached_ballotpedia_profile_image_url_https):
                candidate.ballotpedia_profile_image_url_https = cached_ballotpedia_profile_image_url_https
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

            if values_changed:
                candidate.save()
                success = True
                status += "SAVED_BALLOTPEDIA_IMAGES "
            else:
                success = True
                status += "NO_CHANGES_SAVED_TO_BALLOTPEDIA_IMAGES "

        results = {
            'success':      success,
            'status':       status,
            'candidate':    candidate,
        }
        return results

    def update_candidate_twitter_details(
            self,
            candidate,
            twitter_json,
            cached_twitter_profile_image_url_https,
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

            candidate.we_vote_hosted_profile_twitter_image_url_large = we_vote_hosted_profile_image_url_large
            candidate.we_vote_hosted_profile_twitter_image_url_medium = we_vote_hosted_profile_image_url_medium
            candidate.we_vote_hosted_profile_twitter_image_url_tiny = we_vote_hosted_profile_image_url_tiny

            if candidate.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                candidate.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
                values_changed = True
            if candidate.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                candidate.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                candidate.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                candidate.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_json:  # No value required to update description (so we can clear out)
                if twitter_json['description'] != candidate.twitter_description:
                    candidate.twitter_description = twitter_json['description']
                    values_changed = True
            if 'location' in twitter_json:  # No value required to update location (so we can clear out)
                if twitter_json['location'] != candidate.twitter_location:
                    candidate.twitter_location = twitter_json['location']
                    values_changed = True
            if not positive_value_exists(candidate.candidate_url):
                # Only use the URL from Twitter if a candidate_url doesn't already exist
                if 'entities' in twitter_json and \
                        'url' in twitter_json['entities'] and \
                        'urls' in twitter_json['entities']['url'] and \
                        len(twitter_json['entities']['url']['urls']) > 0:
                    # scan and pick the first encountered
                    for url_data in twitter_json['entities']['url']['urls']:
                        if 'expanded_url' in url_data and positive_value_exists(url_data['expanded_url']):
                            if url_data['expanded_url'] != candidate.candidate_url:
                                candidate.candidate_url = url_data['expanded_url']
                                values_changed = True
                                break

            try:
                candidate.save()
                success = True
                status += "SAVED_CANDIDATE_TWITTER_DETAILS "
            except Exception as e:
                success = False
                status += "NO_CHANGES_SAVED_TO_CANDIDATE_TWITTER_DETAILS: " + str(e) + " "

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
            status += "RESET_CANDIDATE_IMAGE_DETAILS "

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
            status += "CLEARED_CANDIDATE_TWITTER_DETAILS "

        results = {
            'success':      success,
            'status':       status,
            'candidate':    candidate,
        }
        return results

    def refresh_cached_candidate_office_info(self, candidate_object, office_object=None):
        """
        The candidate tables cache information from other tables. This function reaches out to the source tables
        and copies over the latest information to the candidate table.
        :param candidate_object:
        :param office_object: Save the time retrieving office by using existing object
        :return:
        """
        values_changed = False
        office_found = False
        contest_office_manager = ContestOfficeManager()
        if office_object and hasattr(office_object, 'office_name'):
            office_found = True
        elif positive_value_exists(candidate_object.contest_office_id):
            results = contest_office_manager.retrieve_contest_office_from_id(candidate_object.contest_office_id)
            office_found = results['contest_office_found']
            office_object = results['contest_office']
        elif positive_value_exists(candidate_object.contest_office_we_vote_id):
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
                candidate_object.contest_office_we_vote_id)
            office_found = results['contest_office_found']
            office_object = results['contest_office']

        if office_found:
            candidate_object.contest_office_id = office_object.id
            candidate_object.contest_office_we_vote_id = office_object.we_vote_id
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
        ballotpedia_candidate_id = update_values['ballotpedia_candidate_id'] \
            if 'ballotpedia_candidate_id' in update_values else 0
        ballotpedia_candidate_name = update_values['ballotpedia_candidate_name'] \
            if 'ballotpedia_candidate_name' in update_values else ''
        ballotpedia_candidate_summary = update_values['ballotpedia_candidate_summary'] \
            if 'ballotpedia_candidate_summary' in update_values else ''
        ballotpedia_candidate_url = update_values['ballotpedia_candidate_url'] \
            if 'ballotpedia_candidate_url' in update_values else ''
        ballotpedia_election_id = update_values['ballotpedia_election_id'] \
            if 'ballotpedia_election_id' in update_values else 0
        ballotpedia_image_id = update_values['ballotpedia_image_id'] \
            if 'ballotpedia_image_id' in update_values else 0
        ballotpedia_office_id = update_values['ballotpedia_office_id'] \
            if 'ballotpedia_office_id' in update_values else 0
        ballotpedia_person_id = update_values['ballotpedia_person_id'] \
            if 'ballotpedia_person_id' in update_values else 0
        ballotpedia_race_id = update_values['ballotpedia_race_id'] \
            if 'ballotpedia_race_id' in update_values else 0
        birth_day_text = update_values['birth_day_text'] if 'birth_day_text' in update_values else ''
        candidate_email = update_values['candidate_email'] if 'candidate_email' in update_values else ''
        candidate_gender = update_values['candidate_gender'] if 'candidate_gender' in update_values else ''
        if 'candidate_is_incumbent' in update_values:
            candidate_is_incumbent = positive_value_exists(update_values['candidate_is_incumbent'])
        else:
            candidate_is_incumbent = False
        if 'candidate_is_top_ticket' in update_values:
            candidate_is_top_ticket = positive_value_exists(update_values['candidate_is_top_ticket'])
        else:
            candidate_is_top_ticket = False
        candidate_name = update_values['candidate_name'] if 'candidate_name' in update_values else ''
        candidate_participation_status = update_values['candidate_participation_status'] \
            if 'candidate_participation_status' in update_values else ''
        candidate_party_name = update_values['party'] if 'party' in update_values else ''
        candidate_phone = update_values['candidate_phone'] if 'candidate_phone' in update_values else ''
        candidate_twitter_handle = update_values['candidate_twitter_handle'] \
            if 'candidate_twitter_handle' in update_values else ''
        candidate_url = update_values['candidate_url'] \
            if 'candidate_url' in update_values else ''
        candidate_contact_form_url = update_values['candidate_contact_form_url'] \
            if 'candidate_contact_form_url' in update_values else ''
        candidate_instagram_url = update_values['candidate_instagram_url'] \
            if 'candidate_instagram_url' in update_values else ''
        contest_office_we_vote_id = update_values['contest_office_we_vote_id'] \
            if 'contest_office_we_vote_id' in update_values else ''
        contest_office_id = update_values['contest_office_id'] \
            if 'contest_office_id' in update_values else 0
        contest_office_name = update_values['contest_office_name'] \
            if 'contest_office_name' in update_values else ''
        crowdpac_candidate_id = update_values['crowdpac_candidate_id'] \
            if 'crowdpac_candidate_id' in update_values else 0
        ctcl_uuid = update_values['ctcl_uuid'] if 'ctcl_uuid' in update_values else ''
        facebook_url = update_values['facebook_url'] \
            if 'facebook_url' in update_values else ''
        google_civic_candidate_name = update_values['google_civic_candidate_name'] \
            if 'google_civic_candidate_name' in update_values else ''
        google_civic_election_id = update_values['google_civic_election_id'] \
            if 'google_civic_election_id' in update_values else ''
        photo_url = update_values['photo_url'] if 'photo_url' in update_values else ''
        photo_url_from_ctcl = update_values['photo_url_from_ctcl'] if 'photo_url_from_ctcl' in update_values else ''
        photo_url_from_vote_usa = update_values['photo_url_from_vote_usa'] \
            if 'photo_url_from_vote_usa' in update_values else ''
        state_code = update_values['state_code'] if 'state_code' in update_values else ''
        if positive_value_exists(state_code):
            state_code = state_code.lower()
        vote_usa_office_id = update_values['vote_usa_office_id'] \
            if 'vote_usa_office_id' in update_values else None
        vote_usa_politician_id = update_values['vote_usa_politician_id'] \
            if 'vote_usa_politician_id' in update_values else None
        vote_usa_profile_image_url_https = update_values['vote_usa_profile_image_url_https'] \
            if 'vote_usa_profile_image_url_https' in update_values else None

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
                new_candidate.ballotpedia_candidate_id = convert_to_int(ballotpedia_candidate_id)
                new_candidate.ballotpedia_candidate_name = ballotpedia_candidate_name
                new_candidate.ballotpedia_candidate_summary = ballotpedia_candidate_summary
                new_candidate.ballotpedia_candidate_url = ballotpedia_candidate_url
                new_candidate.ballotpedia_election_id = convert_to_int(ballotpedia_election_id)
                new_candidate.ballotpedia_image_id = convert_to_int(ballotpedia_image_id)
                new_candidate.ballotpedia_office_id = convert_to_int(ballotpedia_office_id)
                new_candidate.ballotpedia_person_id = convert_to_int(ballotpedia_person_id)
                new_candidate.ballotpedia_race_id = convert_to_int(ballotpedia_race_id)
                new_candidate.birth_day_text = birth_day_text
                new_candidate.candidate_email = candidate_email
                new_candidate.candidate_gender = candidate_gender
                new_candidate.candidate_instagram_url = candidate_instagram_url
                new_candidate.candidate_is_incumbent = candidate_is_incumbent
                new_candidate.candidate_is_top_ticket = candidate_is_top_ticket
                new_candidate.candidate_participation_status = candidate_participation_status
                new_candidate.candidate_phone = candidate_phone
                new_candidate.candidate_twitter_handle = candidate_twitter_handle
                new_candidate.candidate_url = candidate_url
                new_candidate.candidate_contact_form_url = candidate_contact_form_url
                new_candidate.contest_office_id = convert_to_int(contest_office_id)
                new_candidate.contest_office_name = contest_office_name
                new_candidate.crowdpac_candidate_id = convert_to_int(crowdpac_candidate_id)
                new_candidate.ctcl_uuid = ctcl_uuid
                new_candidate.facebook_url = facebook_url
                new_candidate.google_civic_candidate_name = google_civic_candidate_name
                new_candidate.party = candidate_party_name
                new_candidate.photo_url = photo_url
                new_candidate.photo_url_from_ctcl = photo_url_from_ctcl
                new_candidate.photo_url_from_vote_usa = photo_url_from_vote_usa
                new_candidate.vote_usa_office_id = vote_usa_office_id
                new_candidate.vote_usa_politician_id = vote_usa_politician_id
                new_candidate.vote_usa_profile_image_url_https = vote_usa_profile_image_url_https
                new_candidate.save()

                status += "CANDIDATE_CREATE_THEN_UPDATE_SUCCESS "
            except Exception as e:
                success = False
                new_candidate_created = False
                status += "CANDIDATE_CREATE_THEN_UPDATE_ERROR: " + str(e) + " "
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
                if 'ballotpedia_candidate_id' in update_values:
                    existing_candidate_entry.ballotpedia_candidate_id = \
                        convert_to_int(update_values['ballotpedia_candidate_id'])
                    values_changed = True
                if 'ballotpedia_candidate_name' in update_values:
                    existing_candidate_entry.ballotpedia_candidate_name = update_values['ballotpedia_candidate_name']
                    values_changed = True
                if 'ballotpedia_candidate_summary' in update_values:
                    existing_candidate_entry.ballotpedia_candidate_summary = \
                        update_values['ballotpedia_candidate_summary']
                    values_changed = True
                if 'ballotpedia_candidate_url' in update_values:
                    existing_candidate_entry.ballotpedia_candidate_url = update_values['ballotpedia_candidate_url']
                    values_changed = True
                if 'ballotpedia_election_id' in update_values:
                    existing_candidate_entry.ballotpedia_election_id = \
                        convert_to_int(update_values['ballotpedia_election_id'])
                    values_changed = True
                if 'ballotpedia_image_id' in update_values:
                    existing_candidate_entry.ballotpedia_image_id = \
                        convert_to_int(update_values['ballotpedia_image_id'])
                    values_changed = True
                if 'ballotpedia_office_id' in update_values:
                    existing_candidate_entry.ballotpedia_office_id = \
                        convert_to_int(update_values['ballotpedia_office_id'])
                    values_changed = True
                if 'ballotpedia_person_id' in update_values:
                    existing_candidate_entry.ballotpedia_person_id = \
                        convert_to_int(update_values['ballotpedia_person_id'])
                    values_changed = True
                if 'ballotpedia_race_id' in update_values:
                    existing_candidate_entry.ballotpedia_race_id = \
                        convert_to_int(update_values['ballotpedia_race_id'])
                    values_changed = True
                if 'birth_day_text' in update_values:
                    existing_candidate_entry.birth_day_text = update_values['birth_day_text']
                    values_changed = True
                if 'candidate_contact_form_url' in update_values:
                    existing_candidate_entry.candidate_contact_form_url = update_values['candidate_contact_form_url']
                    values_changed = True
                if 'candidate_instagram_url' in update_values:
                    existing_candidate_entry.candidate_instagram_url = update_values['candidate_instagram_url']
                    values_changed = True
                if 'candidate_email' in update_values:
                    existing_candidate_entry.candidate_email = update_values['candidate_email']
                    values_changed = True
                if 'candidate_gender' in update_values:
                    existing_candidate_entry.candidate_gender = update_values['candidate_gender']
                    values_changed = True
                if 'candidate_is_incumbent' in update_values:
                    existing_candidate_entry.candidate_is_incumbent = \
                        positive_value_exists(update_values['candidate_is_incumbent'])
                    values_changed = True
                if 'candidate_is_top_ticket' in update_values:
                    existing_candidate_entry.is_top_ticket = \
                        positive_value_exists(update_values['candidate_is_top_ticket'])
                    values_changed = True
                if 'candidate_name' in update_values:
                    existing_candidate_entry.candidate_name = update_values['candidate_name']
                    values_changed = True
                if 'candidate_participation_status' in update_values:
                    existing_candidate_entry.candidate_participation_status = \
                        update_values['candidate_participation_status']
                    values_changed = True
                if 'candidate_phone' in update_values:
                    existing_candidate_entry.candidate_phone = update_values['candidate_phone']
                    values_changed = True
                if 'candidate_twitter_handle' in update_values:
                    existing_candidate_entry.candidate_twitter_handle = update_values['candidate_twitter_handle']
                    values_changed = True
                if 'candidate_url' in update_values:
                    existing_candidate_entry.candidate_url = update_values['candidate_url']
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
                if 'crowdpac_candidate_id' in update_values:
                    existing_candidate_entry.crowdpac_candidate_id = update_values['crowdpac_candidate_id']
                    values_changed = True
                if 'ctcl_uuid' in update_values:
                    existing_candidate_entry.ctcl_uuid = update_values['ctcl_uuid']
                    values_changed = True
                if 'facebook_url' in update_values:
                    existing_candidate_entry.facebook_url = update_values['facebook_url']
                    values_changed = True
                if 'google_civic_election_id' in update_values:
                    existing_candidate_entry.google_civic_election_id = update_values['google_civic_election_id']
                    values_changed = True
                if 'party' in update_values:
                    existing_candidate_entry.party = update_values['party']
                    values_changed = True
                if 'politician_id' in update_values:
                    existing_candidate_entry.politician_id = update_values['politician_id']
                    values_changed = True
                if 'photo_url' in update_values:
                    # check if candidate has an existing photo in the CandidateCampaign table
                    if positive_value_exists(existing_candidate_entry.we_vote_hosted_profile_image_url_large) and \
                            positive_value_exists(existing_candidate_entry.we_vote_hosted_profile_image_url_medium) \
                            and positive_value_exists(existing_candidate_entry.we_vote_hosted_profile_image_url_tiny):
                        save_to_candidate_object = False
                    else:
                        save_to_candidate_object = True

                    candidate_results = self.modify_candidate_with_organization_endorsements_image(
                        existing_candidate_entry, update_values['photo_url'], save_to_candidate_object)
                    if candidate_results['success']:
                        values_changed = True
                        candidate = candidate_results['candidate']
                        existing_candidate_entry.we_vote_hosted_profile_image_url_large = \
                            candidate.we_vote_hosted_profile_image_url_large
                        existing_candidate_entry.we_vote_hosted_profile_image_url_medium = \
                            candidate.we_vote_hosted_profile_image_url_medium
                        existing_candidate_entry.we_vote_hosted_profile_image_url_tiny = \
                            candidate.we_vote_hosted_profile_image_url_tiny
                if 'photo_url_from_ctcl' in update_values:
                    existing_candidate_entry.photo_url_from_ctcl = update_values['photo_url_from_ctcl']
                    values_changed = True
                if 'photo_url_from_vote_usa' in update_values:
                    existing_candidate_entry.photo_url_from_vote_usa = update_values['photo_url_from_vote_usa']
                    values_changed = True
                if 'state_code' in update_values:
                    state_code = update_values['state_code']
                    if positive_value_exists(state_code):
                        state_code = state_code.lower()
                    existing_candidate_entry.state_code = state_code
                    values_changed = True
                if 'vote_usa_office_id' in update_values:
                    existing_candidate_entry.vote_usa_office_id = update_values['vote_usa_office_id']
                    values_changed = True
                if 'vote_usa_politician_id' in update_values:
                    existing_candidate_entry.vote_usa_politician_id = update_values['vote_usa_politician_id']
                    values_changed = True
                if 'vote_usa_profile_image_url_https' in update_values:
                    existing_candidate_entry.vote_usa_profile_image_url_https = update_values['vote_usa_profile_image_url_https']
                    values_changed = True

                # now go ahead and save this entry (update)
                if values_changed:
                    existing_candidate_entry.save()
                    candidate_updated = True
                    success = True
                    status += "CANDIDATE_UPDATED "
                else:
                    candidate_updated = False
                    success = True
                    status += "CANDIDATE_NOT_UPDATED-NO_CHANGES "
        except Exception as e:
            success = False
            candidate_updated = False
            status += "UPDATE_CANDIDATE_ROW_ENTRY: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

        results = {
                'success':              success,
                'status':               status,
                'candidate_updated':    candidate_updated,
                'updated_candidate':    existing_candidate_entry,
            }
        return results

    def modify_candidate_with_organization_endorsements_image(self, candidate, candidate_photo_url,
                                                              save_to_candidate_object):
        """
        Save profile image url for candidate in image table
        This function could be updated to save images from other sources beyond ORGANIZATION_ENDORSEMENTS_IMAGE_NAME
        :param candidate: 
        :param candidate_photo_url: 
        :param save_to_candidate_object: 
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
        modified_url_string = candidate_photo_url
        temp_url_string = candidate_photo_url.lower()
        temp_url_string = temp_url_string.replace("\\", "")
        if "http" not in temp_url_string:
            modified_url_string = "https:{0}".format(temp_url_string)
        # image_source=OTHER_SOURCE is not currently used
        cache_results = cache_master_and_resized_image(
            candidate_id=candidate.id,
            candidate_we_vote_id=candidate.we_vote_id,
            other_source_image_url=modified_url_string,
            other_source=ORGANIZATION_ENDORSEMENTS_IMAGE_NAME,
            image_source=OTHER_SOURCE)
        cached_other_source_image_url_https = cache_results['cached_other_source_image_url_https']
        # We store the original source of the candidate photo, even though we don't use this url to display the image
        candidate.other_source_url = candidate_photo_url
        # Store locally cached link to this image
        candidate.other_source_photo_url = cached_other_source_image_url_https

        # save this in candidate table only if no image exists for the candidate. Do not overwrite existing image
        if positive_value_exists(save_to_candidate_object):
            we_vote_hosted_profile_image_url_large = cache_results['we_vote_hosted_profile_image_url_large']
            we_vote_hosted_profile_image_url_medium = cache_results['we_vote_hosted_profile_image_url_medium']
            we_vote_hosted_profile_image_url_tiny = cache_results['we_vote_hosted_profile_image_url_tiny']

            try:
                candidate.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                candidate.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                candidate.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                success = True
                status += "MODIFY_CANDIDATE_WITH_ORGANIZATION_ENDORSEMENTS_IMAGE-IMAGE_SAVED "
            except Exception as e:
                status += "MODIFY_CANDIDATE_WITH_ORGANIZATION_ENDORSEMENTS_IMAGE-IMAGE_SAVE_FAILED: " + str(e) + " "
        results = {
            'success': success,
            'status': status,
            'candidate': candidate,
        }

        return results

    def count_candidates_for_election(self, google_civic_election_id):
        """
        Return count of candidates found for a given election        
        :param google_civic_election_id: 
        :return: 
        """
        candidates_count = 0
        success = False
        status = ""
        if positive_value_exists(google_civic_election_id):
            try:
                candidate_item_queryset = CandidateCampaign.objects.all()
                candidate_item_queryset = candidate_item_queryset.filter(
                    google_civic_election_id=google_civic_election_id)
                candidates_count = candidate_item_queryset.count()

                status += 'CANDIDATES_ITEMS_FOUND '
                success = True
            except CandidateCampaign.DoesNotExist:
                # No candidate items found. Not a problem.
                status += 'NO_CANDIDATE_ITEMS_FOUND '
                success = True
            except Exception as e:
                handle_exception(e, logger=logger)
                status += 'FAILED retrieve_candidate_items_for_election ' \
                          '{error} [type: {error_type}] '.format(error=e.message, error_type=type(e))
        else:
            status += 'INVALID_GOOGLE_CIVIC_ELECTION_ID '
        results = {
            'success':          success,
            'status':           status,
            'candidates_count': candidates_count
        }
        return results


class CandidatesAreNotDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two candidates as NOT duplicates
    """
    candidate1_we_vote_id = models.CharField(
        verbose_name="first candidate we are tracking", max_length=255, null=True, unique=False)
    candidate2_we_vote_id = models.CharField(
        verbose_name="second candidate we are tracking", max_length=255, null=True, unique=False)

    def fetch_other_candidate_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.candidate1_we_vote_id:
            return self.candidate2_we_vote_id
        elif one_we_vote_id == self.candidate2_we_vote_id:
            return self.candidate1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class CandidateToOfficeLink(models.Model):
    """
    Some candidates, like Presidential candidates, are the same across many different states or elections.
    We also see the same candidates from primaries move into the next election. We make sure
    to create a unique ContestOffice per election, but we let the Candidate be used in both the primary and
    General election.
    With this table, we can allow candidates to be linked to multiple elections
    This replaces ContestOfficeVisitingOtherElection
    """
    candidate_we_vote_id = models.CharField(db_index=True, max_length=255, null=False, unique=False)
    contest_office_we_vote_id = models.CharField(db_index=True, max_length=255, null=False, unique=False)
    google_civic_election_id = models.PositiveIntegerField(db_index=True, default=0, null=False, blank=False)
    state_code = models.CharField(db_index=True, max_length=2, null=True)
    position_dates_set = models.BooleanField(default=False)  # Have we finished data update process?

    def election(self):
        try:
            election = Election.objects.get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("CandidateToOfficeLink.election Found multiple")
            return
        except Election.DoesNotExist:
            logger.error("CandidateToOfficeLink.election not attached to object, id: "
                         "" + str(self.google_civic_election_id))
            return
        return election

    def office(self):
        try:
            office = ContestOffice.objects.get(we_vote_id=self.contest_office_we_vote_id)
        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("CandidateToOfficeLink.office Found multiple")
            return
        except ContestOffice.DoesNotExist:
            logger.error("CandidateToOfficeLink.office not attached to object, id: "
                         "" + str(self.contest_office_we_vote_id))
            return
        return office
