# politician/controllers_generate_seo_friendly_path.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.utils.text import slugify
from politician.models import Politician, PoliticianSEOFriendlyPath
import string
import wevote_functions.admin
from wevote_functions.functions import convert_state_code_to_state_text, \
    display_full_name_with_correct_capitalization, generate_random_string, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def generate_campaign_title_from_politician(
        politician_name='', state_code=''):
    # If politician_name is all caps, convert it to Title Case
    if politician_name.isupper():
        politician_name = display_full_name_with_correct_capitalization(politician_name)
    if positive_value_exists(state_code):
        state_suffix = ", Politician from {state_text}" \
                       "".format(state_text=convert_state_code_to_state_text(state_code))
    else:
        state_suffix = ", Politician"
    campaign_title = politician_name + state_suffix
    return campaign_title


def generate_seo_friendly_path_generic(
        base_pathname_string=None,
        campaignx_title='',
        campaignx_we_vote_id='',
        for_campaign=False,
        for_politician=False,
        politician_name=None,
        politician_we_vote_id='',
        state_code=None):
    """
    Generate SEO friendly path for this campaignx or politician. Ensure that the SEO friendly path is unique.

    """
    final_pathname_string = ''
    for_campaign = positive_value_exists(for_campaign)
    for_politician = positive_value_exists(for_politician)
    pathname_modifier = None
    seo_friendly_path_created = False
    seo_friendly_path_found = False
    status = ""
    success = True

    required_variable_missing = False
    if for_campaign:
        if not positive_value_exists(campaignx_we_vote_id):
            required_variable_missing = True
            status += "MISSING_CAMPAIGNX_WE_VOTE_ID "

        if not campaignx_title:
            required_variable_missing = True
            status += "MISSING_CAMPAIGN_TITLE "
    elif for_politician:
        if not positive_value_exists(politician_we_vote_id):
            required_variable_missing = True
            status += "MISSING_POLITICIAN_WE_VOTE_ID "

        if not politician_name:
            required_variable_missing = True
            status += "MISSING_POLITICIAN_NAME "
    else:
        required_variable_missing = True
        status += "MISSING_CAMPAIGN_OR_POLITICIAN "

    if required_variable_missing:
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    False,
            'seo_friendly_path_found':      False,
            'status':                       status,
            'success':                      False,
        }
        return results

    pathname_modifier_length = 3
    length_to_allow_for_pathname_modifier = pathname_modifier_length + 1  # + 1 for "-" or "c"
    base_pathname_string_max_length = 255 - length_to_allow_for_pathname_modifier
    try:
        if positive_value_exists(base_pathname_string):
            base_pathname_string = slugify(base_pathname_string)
            if len(base_pathname_string) > base_pathname_string_max_length:
                base_pathname_string = base_pathname_string[:base_pathname_string_max_length]
        elif positive_value_exists(campaignx_title):
            base_pathname_string = slugify(campaignx_title)
        elif positive_value_exists(politician_name):
            # If one wasn't passed in, generate the ideal path given politician_name
            if positive_value_exists(state_code):
                state_suffix = "politician-from-{state_text}" \
                               "".format(state_text=convert_state_code_to_state_text(state_code))
                state_suffix = "-" + slugify(state_suffix)
            else:
                state_suffix = "-politician"

            state_suffix_length = len(state_suffix)
            # # If politician_name is all caps, convert it to Title Case
            # if politician_name.isupper():
            #     politician_name = display_full_name_with_correct_capitalization(politician_name)
            base_pathname_string = slugify(politician_name)
            if state_suffix_length > 0 and \
                    len(base_pathname_string) > (base_pathname_string_max_length - state_suffix_length):
                # Make sure there is enough room for the state_suffix
                base_pathname_string = base_pathname_string[:base_pathname_string_max_length - state_suffix_length]
            base_pathname_string += state_suffix
    except Exception as e:
        status += 'PROBLEM_WITH_SLUGIFY: ' + str(e) + ' '
        success = False

    if not base_pathname_string or not positive_value_exists(len(base_pathname_string)):
        status += "MISSING_BASE_PATHNAME_STRING "
        success = False

    if not positive_value_exists(success):
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    False,
            'seo_friendly_path_found':      False,
            'status':                       status,
            'success':                      False,
        }
        return results

    from campaign.models import CampaignX, CampaignXSEOFriendlyPath
    try:
        match_count = 0
        if for_campaign:
            # Is that path already stored for this campaign?
            path_query = CampaignXSEOFriendlyPath.objects.using('readonly').all()
            path_query = path_query.filter(campaignx_we_vote_id=campaignx_we_vote_id)
            path_query = path_query.filter(final_pathname_string__iexact=base_pathname_string)
            match_count = path_query.count()
        elif for_politician:
            # Is that path already stored for this politician?
            path_query = PoliticianSEOFriendlyPath.objects.using('readonly').all()
            path_query = path_query.filter(politician_we_vote_id=politician_we_vote_id)
            path_query = path_query.filter(final_pathname_string__iexact=base_pathname_string)
            match_count = path_query.count()
        if positive_value_exists(match_count):
            if for_campaign:
                status += "PATHNAME_FOUND-OWNED_BY_THIS_CAMPAIGNX "
            elif for_politician:
                status += "PATHNAME_FOUND-OWNED_BY_THIS_POLITICIAN "
            results = {
                'seo_friendly_path':            base_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      True,
                'status':                       status,
                'success':                      True,
            }
            return results
    except Exception as e:
        status += 'PROBLEM_QUERYING_SEO_FRIENDLY_PATH_TABLE1 {error} [type: {error_type}] ' \
                  ''.format(error=str(e), error_type=type(e))
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    False,
            'seo_friendly_path_found':      False,
            'status':                       status,
            'success':                      False,
        }
        return results

    owned_by_another = False
    try:
        match_count = 0
        if for_campaign:
            # Is it being used by any campaign?
            path_query = CampaignXSEOFriendlyPath.objects.using('readonly').all()
            path_query = path_query.filter(final_pathname_string__iexact=base_pathname_string)
            match_count = path_query.count()
        elif for_politician:
            # Is it being used by any politician?
            path_query = PoliticianSEOFriendlyPath.objects.using('readonly').all()
            path_query = path_query.filter(final_pathname_string__iexact=base_pathname_string)
            match_count = path_query.count()
        if positive_value_exists(match_count):
            owned_by_another = True
            if for_campaign:
                status += "PATHNAME_FOUND-OWNED_BY_ANOTHER_CAMPAIGNX "
            elif for_politician:
                status += "PATHNAME_FOUND-OWNED_BY_ANOTHER_POLITICIAN "
    except Exception as e:
        status += 'PROBLEM_QUERYING_SEO_FRIENDLY_PATH_TABLE2 {error} [type: {error_type}] ' \
                  ''.format(error=str(e), error_type=type(e))
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    False,
            'seo_friendly_path_found':      False,
            'status':                       status,
            'success':                      False,
        }
        return results

    if not owned_by_another:
        # Double-check that we don't have a reserved entry already in the CampaignX or Politician tables
        match_count = 0
        try:
            if for_campaign:
                path_query = CampaignX.objects.using('readonly').all()
                path_query = path_query.filter(seo_friendly_path__iexact=base_pathname_string)
                match_count = path_query.count()
            elif for_politician:
                path_query = Politician.objects.using('readonly').all()
                path_query = path_query.filter(seo_friendly_path__iexact=base_pathname_string)
                match_count = path_query.count()
            if positive_value_exists(match_count):
                owned_by_another = True
                if for_campaign:
                    status += "PATHNAME_FOUND_IN_ANOTHER_CAMPAIGNX "
                elif for_politician:
                    status += "PATHNAME_FOUND_IN_ANOTHER_POLITICIAN "
        except Exception as e:
            status += 'PROBLEM_QUERYING_SEO_FRIENDLY_PATH_TABLE3 {error} [type: {error_type}] ' \
                      ''.format(error=str(e), error_type=type(e))
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

    if not owned_by_another:
        final_pathname_string = base_pathname_string
    else:
        # If already being used, add a random string on the end, verify not in use, and save
        continue_retrieving = True
        pathname_modifiers_already_reviewed_list = []  # Reset
        safety_valve_count = 0
        while continue_retrieving and safety_valve_count < 100:
            safety_valve_count += 1
            modifier_safety_valve_count = 0
            pathname_modifier = generate_random_string(
                string_length=pathname_modifier_length,
                chars=string.ascii_lowercase + string.digits,
                remove_confusing_digits=True,
            )
            if pathname_modifier in pathname_modifiers_already_reviewed_list:
                # Already owned by another politician. Restart the while loop and try a different random string.
                pass
            else:
                if modifier_safety_valve_count > 50:
                    status += 'MODIFIER_SAFETY_VALVE_EXCEEDED '
                    results = {
                        'seo_friendly_path':            final_pathname_string,
                        'seo_friendly_path_created':    False,
                        'seo_friendly_path_found':      False,
                        'status':                       status,
                        'success':                      False,
                    }
                    return results
                modifier_safety_valve_count += 1
                try:
                    match_count = 0
                    pathname_modifiers_already_reviewed_list.append(pathname_modifier)
                    final_pathname_string_to_test = "{base_pathname_string}-{pathname_modifier}".format(
                        base_pathname_string=base_pathname_string,
                        pathname_modifier=pathname_modifier)
                    if for_campaign:
                        path_query = CampaignXSEOFriendlyPath.objects.using('readonly').all()
                        path_query = path_query.filter(final_pathname_string__iexact=final_pathname_string_to_test)
                        match_count = path_query.count()
                    elif for_politician:
                        path_query = PoliticianSEOFriendlyPath.objects.using('readonly').all()
                        path_query = path_query.filter(final_pathname_string__iexact=final_pathname_string_to_test)
                        match_count = path_query.count()
                    if not positive_value_exists(match_count):
                        try:
                            if for_campaign:
                                path_query = CampaignX.objects.using('readonly').all()
                                path_query = path_query.filter(seo_friendly_path__iexact=final_pathname_string_to_test)
                                match_count = path_query.count()
                            elif for_politician:
                                path_query = Politician.objects.using('readonly').all()
                                path_query = path_query.filter(seo_friendly_path__iexact=final_pathname_string_to_test)
                                match_count = path_query.count()
                            if positive_value_exists(match_count):
                                status += "FOUND_IN_ANOTHER2 "
                            else:
                                continue_retrieving = False
                                final_pathname_string = final_pathname_string_to_test
                                owned_by_another = False
                                status += "NO_PATHNAME_COLLISION "
                        except Exception as e:
                            status += 'PROBLEM_QUERYING_CAMPAIGNX_OR_POLITICIAN_TABLE {error} [type: {error_type}] ' \
                                      ''.format(error=str(e), error_type=type(e))
                            results = {
                                'seo_friendly_path':            final_pathname_string,
                                'seo_friendly_path_created':    False,
                                'seo_friendly_path_found':      False,
                                'status':                       status,
                                'success':                      False,
                            }
                            return results
                except Exception as e:
                    status += 'PROBLEM_QUERYING_POLITICIAN_SEO_FRIENDLY_PATH_TABLE4 {error} [type: {error_type}] ' \
                              ''.format(error=str(e), error_type=type(e))
                    results = {
                        'seo_friendly_path':            final_pathname_string,
                        'seo_friendly_path_created':    False,
                        'seo_friendly_path_found':      False,
                        'status':                       status,
                        'success':                      False,
                    }
                    return results

    if owned_by_another:
        # We have failed to find a unique URL
        status += 'FAILED_TO_FIND_UNIQUE_URL '
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    False,
            'seo_friendly_path_found':      False,
            'status':                       status,
            'success':                      False,
        }
        return results

    if not positive_value_exists(final_pathname_string):
        # We have failed to generate a unique URL
        status += 'MISSING_REQUIRED_VARIABLE '
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    False,
            'seo_friendly_path_found':      False,
            'status':                       status,
            'success':                      False,
        }
        return results

    # Create a new entry
    try:
        if for_campaign:
            campaignx_seo_friendly_path = CampaignXSEOFriendlyPath.objects.create(
                base_pathname_string=base_pathname_string,
                campaign_title=campaignx_title,
                campaignx_we_vote_id=campaignx_we_vote_id,
                final_pathname_string=final_pathname_string,
                pathname_modifier=pathname_modifier,
            )
            seo_friendly_path_created = True
            seo_friendly_path_found = True
            success = True
            status += "CAMPAIGNX_SEO_FRIENDLY_PATH_CREATED "
        elif for_politician:
            politician_seo_friendly_path = PoliticianSEOFriendlyPath.objects.create(
                base_pathname_string=base_pathname_string,
                politician_name=politician_name,
                politician_we_vote_id=politician_we_vote_id,
                final_pathname_string=final_pathname_string,
                pathname_modifier=pathname_modifier,
            )
            seo_friendly_path_created = True
            seo_friendly_path_found = True
            success = True
            status += "POLITICIAN_SEO_FRIENDLY_PATH_CREATED "
        else:
            status += "SEO_FRIENDLY_PATH_NOT_STORED_IN_CAMPAIGN_OR_POLITICIAN_SEO_TABLE "
            success = False
    except Exception as e:
        status += "SEO_FRIENDLY_PATH_NOT_CREATED: " + str(e) + " "
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    False,
            'seo_friendly_path_found':      False,
            'status':                       status,
            'success':                      False,
        }
        return results

    status += "FINAL_PATHNAME_STRING_GENERATED "
    results = {
        'seo_friendly_path':            final_pathname_string,
        'seo_friendly_path_created':    seo_friendly_path_created,
        'seo_friendly_path_found':      seo_friendly_path_found,
        'status':                       status,
        'success':                      success,
    }
    return results

