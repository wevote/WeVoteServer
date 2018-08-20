# voter_guide/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from django.db import models
from django.db.models import Q
from election.models import ElectionManager, TIME_SPAN_LIST
from exception.models import handle_exception, handle_record_not_found_exception, \
    handle_record_found_more_than_one_exception
import operator
from organization.models import Organization, OrganizationManager, \
    CORPORATION, GROUP, INDIVIDUAL, NEWS_ORGANIZATION, NONPROFIT, NONPROFIT_501C3, NONPROFIT_501C4, \
    POLITICAL_ACTION_COMMITTEE, PUBLIC_FIGURE, UNKNOWN, ORGANIZATION_TYPE_CHOICES
from pledge_to_vote.models import PledgeToVoteManager
import pytz
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, convert_to_str, positive_value_exists
from wevote_settings.models import fetch_site_unique_id_prefix, fetch_next_we_vote_id_voter_guide_integer

logger = wevote_functions.admin.get_logger(__name__)

ORGANIZATION = 'O'  # Deprecated
ORGANIZATION_WORD = 'ORGANIZATION'
VOTER = 'V'  # Deprecated

SUPPORT = 'SUPPORT'
NO_STANCE = 'NO_STANCE'
OPPOSE = 'OPPOSE'
POSITION_CHOICES = (
    (SUPPORT,           'Supports'),
    (NO_STANCE,         'No stance'),
    (OPPOSE,            'Opposes'),
)
CANDIDATE_NUMBER_LIST = ["001", "002", "003", "004", "005", "006", "007", "008", "009", "010",
                         "011", "012", "013", "014", "015", "016", "017", "018", "019", "020",
                         "021", "022", "023", "024", "025", "026", "027", "028", "029", "030",
                         "031", "032", "033", "034", "035", "036", "037", "038", "039", "040",
                         "041", "042", "043", "044", "045", "046", "047", "048", "049", "050",
                         "051", "052", "053", "054", "055", "056", "057", "058", "059", "060",
                         "061", "062", "063", "064", "065", "066", "067", "068", "069", "070",
                         "071", "072", "073", "074", "075", "076", "077", "078", "079", "080",
                         "081", "082", "083", "084", "085", "086", "087", "088", "089", "090",
                         "091", "092", "093", "094", "095", "096", "097", "098", "099", "100",
                         "101", "102", "103", "104", "105", "106", "107", "108", "109", "110",
                         "111", "112", "113", "114", "115", "116", "117", "118", "119", "120",
                         "121", "122", "123", "124", "125", "126", "127", "128", "129", "130",
                         "131", "132", "133", "134", "135", "136", "137", "138", "139", "140",
                         "141", "142", "143", "144", "145", "146", "147", "148", "149", "150",
                         "151", "152", "153", "154", "155", "156", "157", "158", "159", "160",
                         "161", "162", "163", "164", "165", "166", "167", "168", "169", "170",
                         "171", "172", "173", "174", "175", "176", "177", "178", "179", "180",
                         "181", "182", "183", "184", "185", "186", "187", "188", "189", "190",
                         "191", "192", "193", "194", "195", "196", "197", "198", "199", "200"]
                         # "201", "202", "203", "204", "205", "206", "207", "208", "209", "210",
                         # "211", "212", "213", "214", "215", "216", "217", "218", "219", "220",
                         # "221", "222", "223", "224", "225", "226", "227", "228", "229", "230",
                         # "231", "232", "233", "234", "235", "236", "237", "238", "239", "240",
                         # "241", "242", "243", "244", "245", "246", "247", "248", "249", "250",
                         # "251", "252", "253", "254", "255", "256", "257", "258", "259", "260",
                         # "261", "262", "263", "264", "265", "266", "267", "268", "269", "270",
                         # "271", "272", "273", "274", "275", "276", "277", "278", "279", "280",
                         # "281", "282", "283", "284", "285", "286", "287", "288", "289", "290",
                         # "291", "292", "293", "294", "295", "296", "297", "298", "299", "300"]


class VoterGuideManager(models.Manager):
    """
    A class for working with the VoterGuide model
    """
    def update_or_create_organization_voter_guide_by_election_id(self, voter_guide_we_vote_id,
                                                                 organization_we_vote_id,
                                                                 google_civic_election_id,
                                                                 state_code='',
                                                                 pledge_goal=0,
                                                                 we_vote_hosted_profile_image_url_large='',
                                                                 we_vote_hosted_profile_image_url_medium='',
                                                                 we_vote_hosted_profile_image_url_tiny='',
                                                                 vote_smart_ratings_only=False
                                                                 ):
        """
        This creates voter_guides, and also refreshes voter guides with updated organization data
        """
        google_civic_election_id = convert_to_int(google_civic_election_id)
        exception_multiple_object_returned = False
        voter_guide_on_stage = None
        organization = Organization()
        organization_found = False
        new_voter_guide_created = False
        status = ''
        if not google_civic_election_id or not organization_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_ORGANIZATION_VOTER_GUIDE'
            success = False
            new_voter_guide_created = False
        else:
            # Retrieve the organization object so we can bring over values
            # NOTE: If we don't have this organization in the local database, we won't create a voter guide
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization(0, organization_we_vote_id)
            if results['organization_found']:
                organization_found = True
                organization = results['organization']

            # Now update voter_guide
            try:
                if organization_found:
                    pledge_to_vote_manager = PledgeToVoteManager()
                    pledge_results = pledge_to_vote_manager.retrieve_pledge_count_from_organization_we_vote_id(
                            organization_we_vote_id)
                    if pledge_results['pledge_count_found']:
                        pledge_count = pledge_results['pledge_count']
                    else:
                        pledge_count = 0

                    if positive_value_exists(state_code):
                        state_code = state_code.lower()
                    updated_values = {
                        'google_civic_election_id': google_civic_election_id,
                        'organization_we_vote_id':  organization_we_vote_id,
                        'image_url':                organization.organization_photo_url(),
                        'twitter_handle':           organization.organization_twitter_handle,
                        'twitter_description':      organization.twitter_description,
                        'twitter_followers_count':  organization.twitter_followers_count,
                        'display_name':             organization.organization_name,
                        'voter_guide_owner_type':   organization.organization_type,
                        'vote_smart_ratings_only':  vote_smart_ratings_only,
                        'state_code':               state_code,
                        'we_vote_hosted_profile_image_url_large':  organization.we_vote_hosted_profile_image_url_large,
                        'we_vote_hosted_profile_image_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                        'we_vote_hosted_profile_image_url_tiny':   organization.we_vote_hosted_profile_image_url_tiny,
                        'pledge_count':             pledge_count,
                    }
                    if positive_value_exists(voter_guide_we_vote_id):
                        updated_values['we_vote_id'] = voter_guide_we_vote_id
                    if positive_value_exists(pledge_goal):
                        updated_values['pledge_goal'] = pledge_goal
                    if positive_value_exists(we_vote_hosted_profile_image_url_large):
                        updated_values['we_vote_hosted_profile_image_url_large'] = \
                            we_vote_hosted_profile_image_url_large
                    if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                        updated_values['we_vote_hosted_profile_image_url_medium'] = \
                            we_vote_hosted_profile_image_url_medium
                    if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                        updated_values['we_vote_hosted_profile_image_url_tiny'] = we_vote_hosted_profile_image_url_tiny
                    if positive_value_exists(google_civic_election_id):
                        election_manager = ElectionManager()
                        election_results = election_manager.retrieve_election(google_civic_election_id)
                        if election_results['election_found']:
                            election = election_results['election']
                            updated_values['election_day_text'] = election.election_day_text

                    voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                        google_civic_election_id__exact=google_civic_election_id,
                        organization_we_vote_id__iexact=organization_we_vote_id,
                        defaults=updated_values)
                    success = True
                    if new_voter_guide_created:
                        status += 'VOTER_GUIDE_CREATED_FOR_ORGANIZATION '
                    else:
                        status += 'VOTER_GUIDE_UPDATED_FOR_ORGANIZATION '
                else:
                    success = False
                    status += 'VOTER_GUIDE_NOT_CREATED_BECAUSE_ORGANIZATION_NOT_FOUND_LOCALLY'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status += 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_ORGANIZATION'
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'voter_guide':              voter_guide_on_stage,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_organization_voter_guide_by_time_span(self, voter_guide_we_vote_id,
                                                               organization_we_vote_id, vote_smart_time_span,
                                                               pledge_goal='',
                                                               we_vote_hosted_profile_image_url_large='',
                                                               we_vote_hosted_profile_image_url_medium='',
                                                               we_vote_hosted_profile_image_url_tiny=''
                                                               ):
        organization_found = False
        voter_guide_owner_type = ORGANIZATION
        exception_multiple_object_returned = False
        new_voter_guide_created = False
        if not vote_smart_time_span or not organization_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_ORGANIZATION_VOTER_GUIDE_BY_TIME_SPAN'
            success = False
            new_voter_guide_created = False
        else:
            # Retrieve the organization object so we can bring over values
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization(0, organization_we_vote_id)
            if results['organization_found']:
                organization_found = True
                organization = results['organization']

            # Now update voter_guide  # TODO DALE Get from TwitterLinkToOrganization, not organization_twitter_handle
            try:
                if organization_found:
                    if organization.twitter_followers_count is None:
                        twitter_followers_count = 0
                    else:
                        twitter_followers_count = convert_to_int(organization.twitter_followers_count)
                    pledge_to_vote_manager = PledgeToVoteManager()
                    pledge_results = pledge_to_vote_manager.retrieve_pledge_count_from_organization_we_vote_id(
                            organization_we_vote_id)
                    if pledge_results['pledge_count_found']:
                        pledge_count = pledge_results['pledge_count']
                    else:
                        pledge_count = 0
                    updated_values = {
                        # Values we search against below
                        'vote_smart_time_span':     vote_smart_time_span,
                        'organization_we_vote_id':  organization_we_vote_id,
                        # The rest of the values
                        'voter_guide_owner_type':   voter_guide_owner_type,
                        'twitter_handle':           organization.organization_twitter_handle,
                        'display_name':             organization.organization_name,
                        'image_url':                organization.organization_photo_url(),
                        'twitter_description':      organization.twitter_description,
                        'twitter_followers_count':  twitter_followers_count,
                        'pledge_count':             pledge_count,
                    }
                    if positive_value_exists(voter_guide_we_vote_id):
                        updated_values['we_vote_id'] = voter_guide_we_vote_id
                    if positive_value_exists(pledge_goal):
                        updated_values['pledge_goal'] = pledge_goal
                    if positive_value_exists(we_vote_hosted_profile_image_url_large):
                        updated_values['we_vote_hosted_profile_image_url_large'] = \
                            we_vote_hosted_profile_image_url_large
                    if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                        updated_values['we_vote_hosted_profile_image_url_medium'] = \
                            we_vote_hosted_profile_image_url_medium
                    if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                        updated_values['we_vote_hosted_profile_image_url_tiny'] = we_vote_hosted_profile_image_url_tiny
                    voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                        vote_smart_time_span__exact=vote_smart_time_span,
                        organization_we_vote_id__iexact=organization_we_vote_id,
                        defaults=updated_values)
                    success = True
                    if new_voter_guide_created:
                        status = 'VOTER_GUIDE_CREATED_FOR_ORGANIZATION_BY_TIME_SPAN'
                    else:
                        status = 'VOTER_GUIDE_UPDATED_FOR_ORGANIZATION_BY_TIME_SPAN'
                else:
                    success = False
                    status = 'VOTER_GUIDE_NOT_CREATED_BECAUSE_ORGANIZATION_NOT_FOUND_LOCALLY'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_ORGANIZATION_BY_TIME_SPAN'
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_public_figure_voter_guide(self, voter_guide_we_vote_id,
                                                   google_civic_election_id, public_figure_we_vote_id,
                                                   pledge_goal,
                                                   we_vote_hosted_profile_image_url_large='',
                                                   we_vote_hosted_profile_image_url_medium='',
                                                   we_vote_hosted_profile_image_url_tiny=''
                                                   ):
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.PUBLIC_FIGURE
        exception_multiple_object_returned = False
        if not google_civic_election_id or not public_figure_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_PUBLIC_FIGURE_VOTER_GUIDE'
            new_voter_guide_created = False
            success = False
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'public_figure_we_vote_id': public_figure_we_vote_id,
                    # The rest of the values
                }
                if positive_value_exists(voter_guide_we_vote_id):
                    updated_values['we_vote_id'] = voter_guide_we_vote_id
                if positive_value_exists(pledge_goal):
                    updated_values['pledge_goal'] = pledge_goal
                if positive_value_exists(we_vote_hosted_profile_image_url_large):
                    updated_values['we_vote_hosted_profile_image_url_large'] = \
                        we_vote_hosted_profile_image_url_large
                if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                    updated_values['we_vote_hosted_profile_image_url_medium'] = \
                        we_vote_hosted_profile_image_url_medium
                if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                    updated_values['we_vote_hosted_profile_image_url_tiny'] = we_vote_hosted_profile_image_url_tiny
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_guide_owner_type__iexact=voter_guide_owner_type,
                    public_figure_we_vote_id__iexact=public_figure_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_PUBLIC_FIGURE'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_PUBLIC_FIGURE'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_PUBLIC_FIGURE'
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_voter_voter_guide(self, google_civic_election_id, voter):
        """

        :param google_civic_election_id:
        :param voter:
        :param organization:
        :return:
        """
        google_civic_election_id = convert_to_int(google_civic_election_id)
        success = False
        status = ""
        exception_multiple_object_returned = False
        new_voter_guide_created = False
        linked_organization_we_vote_id = ""
        organization_manager = OrganizationManager()
        voter_guide = VoterGuide()

        try:
            voter
        except NameError:
            voter_exists = False
        else:
            voter_exists = True

        if voter_exists and positive_value_exists(voter.linked_organization_we_vote_id):
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(voter.linked_organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                linked_organization_we_vote_id = organization.we_vote_id

        try:
            organization
        except NameError:
            organization_exists = False
        else:
            organization_exists = True

        if positive_value_exists(linked_organization_we_vote_id) and voter_exists and organization_exists \
                and positive_value_exists(google_civic_election_id):
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'organization_we_vote_id': linked_organization_we_vote_id,
                    # The rest of the values
                    'voter_guide_owner_type': organization.organization_type,
                    'owner_voter_id': voter.id,
                    'owner_we_vote_id': voter.we_vote_id,
                }
                voter_guide, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    organization_we_vote_id__iexact=linked_organization_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status += 'VOTER_GUIDE_CREATED_FOR_VOTER '
                else:
                    status += 'VOTER_GUIDE_UPDATED_FOR_VOTER '
            except VoterGuide.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_VOTER '
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide':              voter_guide,
            'voter_guide_saved':        success,
            'voter_guide_created':      new_voter_guide_created,
        }
        return results

    def voter_guide_exists(self, organization_we_vote_id, google_civic_election_id):
        voter_guide_found = False
        google_civic_election_id = int(google_civic_election_id)

        if not positive_value_exists(organization_we_vote_id) or not positive_value_exists(google_civic_election_id):
            return False

        try:
            if positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                voter_guide_query = VoterGuide.objects.filter(google_civic_election_id=google_civic_election_id,
                                                              organization_we_vote_id__iexact=organization_we_vote_id)
                voter_guide_found = True if voter_guide_query.count() > 0 else False
        except VoterGuide.MultipleObjectsReturned as e:
            voter_guide_found = True
        except VoterGuide.DoesNotExist:
            voter_guide_found = False
        return voter_guide_found

    def retrieve_voter_guide(self, voter_guide_id=0, voter_guide_we_vote_id="", google_civic_election_id=0,
                             vote_smart_time_span=None,
                             organization_we_vote_id=None, public_figure_we_vote_id=None, owner_we_vote_id=None):
        voter_guide_id = convert_to_int(voter_guide_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        organization_we_vote_id = convert_to_str(organization_we_vote_id)
        public_figure_we_vote_id = convert_to_str(public_figure_we_vote_id)
        owner_we_vote_id = convert_to_str(owner_we_vote_id)

        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_guide_on_stage = VoterGuide()
        voter_guide_on_stage_id = 0
        status = ""
        try:
            if positive_value_exists(voter_guide_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ID "  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(id=voter_guide_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_ID "
            elif positive_value_exists(voter_guide_we_vote_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_WE_VOTE_ID "  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(we_vote_id=voter_guide_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_WE_VOTE_ID "
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ORGANIZATION_WE_VOTE_ID"  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              organization_we_vote_id__iexact=organization_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_ORGANIZATION_WE_VOTE_ID "
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(vote_smart_time_span):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ORGANIZATION_WE_VOTE_ID_AND_TIME_SPAN "
                voter_guide_on_stage = VoterGuide.objects.get(vote_smart_time_span=vote_smart_time_span,
                                                              organization_we_vote_id__iexact=organization_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_ORGANIZATION_WE_VOTE_ID_AND_TIME_SPAN "
            elif positive_value_exists(public_figure_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_PUBLIC_FIGURE_WE_VOTE_ID"  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              public_figure_we_vote_id__iexact=public_figure_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_PUBLIC_FIGURE_WE_VOTE_ID "
            elif positive_value_exists(owner_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_VOTER_WE_VOTE_ID "  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              owner_we_vote_id__iexact=owner_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_VOTER_WE_VOTE_ID "
            else:
                status = "Insufficient variables included to retrieve one voter guide."
        except VoterGuide.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status += ", ERROR_MORE_THAN_ONE_VOTER_GUIDE_FOUND "
        except VoterGuide.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status += ", VOTER_GUIDE_DOES_NOT_EXIST "

        voter_guide_on_stage_found = True if voter_guide_on_stage_id > 0 else False
        results = {
            'success':                      True if voter_guide_on_stage_found else False,
            'status':                       status,
            'voter_guide_found':            voter_guide_on_stage_found,
            'voter_guide_id':               voter_guide_on_stage_id,
            'organization_we_vote_id':      voter_guide_on_stage.organization_we_vote_id,
            'public_figure_we_vote_id':     voter_guide_on_stage.public_figure_we_vote_id,
            'owner_we_vote_id':             voter_guide_on_stage.owner_we_vote_id,
            'voter_guide':                  voter_guide_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def retrieve_most_recent_voter_guide_for_org(self, organization_we_vote_id):
        status = 'ENTERING_RETRIEVE_MOST_RECENT_VOTER_GUIDE_FOR_ORG'
        voter_guide_found = False
        voter_guide = VoterGuide()
        voter_guide_manager = VoterGuideManager()
        for time_span in TIME_SPAN_LIST:
            voter_guide_by_time_span_results = voter_guide_manager.retrieve_voter_guide(
                vote_smart_time_span=time_span,
                organization_we_vote_id=organization_we_vote_id)
            if voter_guide_by_time_span_results['voter_guide_found']:
                voter_guide_found = True
                voter_guide = voter_guide_by_time_span_results['voter_guide']
                status = 'MOST_RECENT_VOTER_GUIDE_FOUND_FOR_ORG_BY_TIME_SPAN'
                results = {
                    'success':              voter_guide_found,
                    'status':               status,
                    'voter_guide_found':    voter_guide_found,
                    'voter_guide':          voter_guide,
                }
                return results

        election_manager = ElectionManager()
        results = election_manager.retrieve_elections_by_date()
        if results['success']:
            election_list = results['election_list']
            for one_election in election_list:
                voter_guide_results = voter_guide_manager.retrieve_voter_guide(
                    google_civic_election_id=one_election.google_civic_election_id,
                    organization_we_vote_id=organization_we_vote_id)
                if voter_guide_results['voter_guide_found']:
                    voter_guide_found = True
                    voter_guide = voter_guide_results['voter_guide']
                    status = 'MOST_RECENT_VOTER_GUIDE_FOUND_FOR_ORG_BY_ELECTION_ID'
                    results = {
                        'success':              voter_guide_found,
                        'status':               status,
                        'voter_guide_found':    voter_guide_found,
                        'voter_guide':          voter_guide,
                    }
                    return results

        results = {
            'success':              False,
            'status':               status,
            'voter_guide_found':    voter_guide_found,
            'voter_guide':          voter_guide,
        }
        return results

    def reset_voter_guide_image_details(self, organization, twitter_profile_image_url_https=None,
                                        facebook_profile_image_url_https=None):
        """
        Reset Voter guide entry with original we vote image details
        :param organization:
        :param twitter_profile_image_url_https:
        :param facebook_profile_image_url_https:
        :return:
        """
        image_url = None
        success = False
        status = ""
        voter_guide = VoterGuide()

        if positive_value_exists(twitter_profile_image_url_https):
            image_url = twitter_profile_image_url_https
        elif positive_value_exists(facebook_profile_image_url_https):
            image_url = facebook_profile_image_url_https
        if organization:
            voter_guide_list_manager = VoterGuideListManager()
            results = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
                organization.we_vote_id)
            voter_guide_list = results['voter_guide_list']
            if positive_value_exists(results['voter_guide_list_found']):
                for voter_guide in voter_guide_list:
                    voter_guide.image_url = image_url
                    voter_guide.we_vote_hosted_profile_image_url_large = ''
                    voter_guide.we_vote_hosted_profile_image_url_medium = ''
                    voter_guide.we_vote_hosted_profile_image_url_tiny = ''

                    voter_guide.save()
                    success = True
                    status += " RESET_ORG_IMAGE_DETAILS-EARLIER VERSION"
            else:
                success = True
                status += "NO_VOTER_GUIDES_FOUND_FOR_RESET_IMAGE_DETAILS"

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
            'voter_guide':              voter_guide,
        }
        return results

    def update_organization_voter_guides_with_organization_data(self, organization):
        """
        Update voter_guide entry with the latest information from an organization
        """
        success = False
        status = ""
        voter_guides_updated = 0

        if organization:
            voter_guide_list_manager = VoterGuideListManager()
            results = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
                organization.we_vote_id)
            if positive_value_exists(results['voter_guide_list_found']):
                voter_guide_list = results['voter_guide_list']
                for voter_guide in voter_guide_list:
                    # Note that "refresh_one_voter_guide_from_organization" doesn't save changes
                    refresh_results = self.refresh_one_voter_guide_from_organization(voter_guide, organization)
                    if positive_value_exists(refresh_results['values_changed']):
                        voter_guide = refresh_results['voter_guide']
                        voter_guide.save()
                        success = True
                        voter_guides_updated += 1
        status += "UPDATED_VOTER_GUIDES_WITH_ORG_DATA: " + str(voter_guides_updated) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
        }
        return results

    def update_voter_guide_social_media_statistics(self, organization):
        """
        Update voter_guide entry with details retrieved from Twitter, Facebook, or ???
        DALE 2017-11-06 This function needs to be refactored
        """
        success = False
        status = ""
        voter_guide = VoterGuide()

        if organization:
            if positive_value_exists(organization.twitter_followers_count):
                results = self.retrieve_most_recent_voter_guide_for_org(organization_we_vote_id=organization.we_vote_id)

                if results['voter_guide_found']:
                    voter_guide = results['voter_guide']
                    if positive_value_exists(voter_guide.id):
                        refresh_results = self.refresh_one_voter_guide_from_organization(voter_guide, organization)
                        if positive_value_exists(refresh_results['values_changed']):
                            voter_guide = refresh_results['voter_guide']
                            voter_guide.save()
                            success = True
                            status += " SAVED_ORG_TWITTER_DETAILS"
                        else:
                            success = True
                            status = " NO_CHANGES_SAVED_TO_ORG_TWITTER_DETAILS"

                voter_guide_list_manager = VoterGuideListManager()
                results = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
                    organization.we_vote_id)
                if positive_value_exists(results['voter_guide_list_found']):
                    voter_guide_list = results['voter_guide_list']
                    for voter_guide in voter_guide_list:
                        if not positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large) or \
                                not positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_medium) or \
                                not positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_tiny):
                            refresh_results = self.refresh_one_voter_guide_from_organization(voter_guide, organization)
                            if positive_value_exists(refresh_results['values_changed']):
                                voter_guide = refresh_results['voter_guide']
                                voter_guide.save()
                                success = True
                                status += " SAVED_ORG_TWITTER_DETAILS-EARLIER VERSION"

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
            'voter_guide':              voter_guide,
        }
        return results

    def refresh_one_voter_guide_from_organization(self, voter_guide, organization):
        """
        This function does not save voter_guide
        :param voter_guide:
        :param organization:
        :return:
        """
        success = True
        status = ""
        values_changed = False
        if voter_guide.display_name != organization.organization_name:
            voter_guide.display_name = organization.organization_name
            values_changed = True
        if voter_guide.voter_guide_owner_type != organization.organization_type:
            voter_guide.voter_guide_owner_type = organization.organization_type
            values_changed = True
        if voter_guide.twitter_followers_count != organization.twitter_followers_count:
            voter_guide.twitter_followers_count = organization.twitter_followers_count
            values_changed = True
        if voter_guide.twitter_description != organization.twitter_description:
            voter_guide.twitter_description = organization.twitter_description
            values_changed = True
        if voter_guide.twitter_handle != organization.organization_twitter_handle:
            voter_guide.twitter_handle = organization.organization_twitter_handle
            values_changed = True
        if voter_guide.image_url != organization.organization_photo_url():
            voter_guide.image_url = organization.organization_photo_url()
            values_changed = True
        if voter_guide.we_vote_hosted_profile_image_url_large != \
                organization.we_vote_hosted_profile_image_url_large:
            voter_guide.we_vote_hosted_profile_image_url_large = \
                organization.we_vote_hosted_profile_image_url_large
            values_changed = True
        if voter_guide.we_vote_hosted_profile_image_url_medium != \
                organization.we_vote_hosted_profile_image_url_medium:
            voter_guide.we_vote_hosted_profile_image_url_medium = \
                organization.we_vote_hosted_profile_image_url_medium
            values_changed = True
        if voter_guide.we_vote_hosted_profile_image_url_tiny != \
                organization.we_vote_hosted_profile_image_url_tiny:
            voter_guide.we_vote_hosted_profile_image_url_tiny = \
                organization.we_vote_hosted_profile_image_url_tiny
            values_changed = True
        if positive_value_exists(voter_guide.google_civic_election_id) \
                and not positive_value_exists(voter_guide.election_day_text):
            election_manager = ElectionManager()
            election_results = election_manager.retrieve_election(voter_guide.google_civic_election_id)
            if election_results['election_found']:
                election = election_results['election']
                voter_guide.election_day_text = election.election_day_text
                values_changed = True

        results = {
            'values_changed':   values_changed,
            'voter_guide':      voter_guide,
            'status':           status,
            'success':          success,
        }
        return results

    def delete_voter_guide(self, voter_guide_id):
        voter_guide_id = convert_to_int(voter_guide_id)
        voter_guide_deleted = False

        try:
            if voter_guide_id:
                results = self.retrieve_voter_guide(voter_guide_id)
                if results['voter_guide_found']:
                    voter_guide = results['voter_guide']
                    voter_guide_id = voter_guide.id
                    voter_guide.delete()
                    voter_guide_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':              voter_guide_deleted,
            'voter_guide_deleted': voter_guide_deleted,
            'voter_guide_id':      voter_guide_id,
        }
        return results

    def refresh_cached_voter_guide_info(self, voter_guide):
        """
        Make sure that the voter guide information has been updated with the latest information in the organization
        table. NOTE: Dale started building this routine, and then discovered
        that update_or_create_organization_voter_guide_by_election_id does this "refresh" function
        """
        voter_guide_change = False

        # Start with "speaker" information (Organization, Voter, or Public Figure)
        if positive_value_exists(voter_guide.organization_we_vote_id):
            if not positive_value_exists(voter_guide.display_name) \
                    or not positive_value_exists(voter_guide.image_url) \
                    or not positive_value_exists(voter_guide.twitter_handle) \
                    or not positive_value_exists(voter_guide.twitter_description):
                try:
                    # We need to look in the organization table for display_name & image_url
                    organization_manager = OrganizationManager()
                    organization_id = 0
                    results = organization_manager.retrieve_organization(organization_id,
                                                                         voter_guide.organization_we_vote_id)
                    if results['organization_found']:
                        organization = results['organization']
                        if not positive_value_exists(voter_guide.display_name):
                            # speaker_display_name is missing so look it up from source
                            voter_guide.display_name = organization.organization_name
                            voter_guide_change = True
                        if not positive_value_exists(voter_guide.image_url):
                            # image_url is missing so look it up from source
                            voter_guide.image_url = organization.organization_photo_url()
                            voter_guide_change = True
                        if not positive_value_exists(voter_guide.twitter_handle):
                            # twitter_url is missing so look it up from source
                            voter_guide.twitter_handle = organization.organization_twitter_handle
                            voter_guide_change = True
                        if not positive_value_exists(voter_guide.twitter_description):
                            # twitter_description is missing so look it up from source
                            voter_guide.twitter_description = organization.twitter_description
                            voter_guide_change = True
                except Exception as e:
                    pass
        elif positive_value_exists(voter_guide.voter_id):
            pass  # The following to be updated
            # if not positive_value_exists(voter_guide.speaker_display_name) or \
            #         not positive_value_exists(voter_guide.voter_we_vote_id) or \
            #         not positive_value_exists(voter_guide.speaker_image_url_https):
            #     try:
            #         # We need to look in the voter table for speaker_display_name
            #         voter_manager = VoterManager()
            #         results = voter_manager.retrieve_voter_by_id(voter_guide.voter_id)
            #         if results['voter_found']:
            #             voter = results['voter']
            #             if not positive_value_exists(voter_guide.speaker_display_name):
            #                 # speaker_display_name is missing so look it up from source
            #                 voter_guide.speaker_display_name = voter.get_full_name()
            #                 voter_guide_change = True
            #             if not positive_value_exists(voter_guide.voter_we_vote_id):
            #                 # speaker_we_vote_id is missing so look it up from source
            #                 voter_guide.voter_we_vote_id = voter.we_vote_id
            #                 voter_guide_change = True
            #             if not positive_value_exists(voter_guide.speaker_image_url_https):
            #                 # speaker_image_url_https is missing so look it up from source
            #                 voter_guide.speaker_image_url_https = voter.voter_photo_url()
            #                 voter_guide_change = True
            #     except Exception as e:
            #         pass

        elif positive_value_exists(voter_guide.public_figure_we_vote_id):
            pass

        # TODO Add code to refresh pledge_goal and pledge_count from PledgeToVote

        if positive_value_exists(voter_guide.google_civic_election_id) and not positive_value_exists(voter_guide.election_day_text):
            election_manager = ElectionManager()
            election_results = election_manager.retrieve_election(voter_guide.google_civic_election_id)
            if election_results['election_found']:
                election = election_results['election']
                voter_guide.election_day_text = election.election_day_text
                voter_guide_change = True

        if voter_guide_change:
            voter_guide.save()

        return voter_guide

    def save_voter_guide_object(self, voter_guide):
        """
        """
        try:
            voter_guide.save()
        except Exception as e:
            handle_exception(e, logger=logger)

        return voter_guide


class VoterGuide(models.Model):
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our voter_guide
    # info with other organizations running their own We Vote servers
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "vg" (for voter guide), and then a sequential integer like "123".
    # We generate this id on initial save keep the last value in WeVoteSetting.we_vote_id_last_voter_guide_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=True)

    # NOTE: We are using we_vote_id's instead of internal ids
    # The unique id of the organization. May be null if voter_guide owned by a public figure or voter instead of org.
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure. May be null if voter_guide owned by org or voter instead of public figure.
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure. May be null if voter_guide owned by org or public figure instead of voter.
    owner_we_vote_id = models.CharField(
        verbose_name="individual voter's we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the voter that owns this guide. May be null if voter_guide owned by an org
    # or public figure instead of by a voter.
    # DEPRECATE THIS - 2015-11-11 We should use
    owner_voter_id = models.PositiveIntegerField(
        verbose_name="the unique voter id of the voter who this guide is about", default=0, null=True, blank=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True)
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    state_code = models.CharField(verbose_name="state the voter_guide is related to", max_length=2, null=True)

    # Usually in one of these two formats 2015, 2014-2015
    vote_smart_time_span = models.CharField(
        verbose_name="the period in which the organization stated this position", max_length=255, null=True,
        blank=True, unique=False)

    # This might be the organization name, or the
    display_name = models.CharField(
        verbose_name="display title for this voter guide", max_length=255, null=True, blank=True, unique=False)

    image_url = models.URLField(verbose_name='image url of logo/photo associated with voter guide',
                                blank=True, null=True)
    we_vote_hosted_profile_image_url_large = models.URLField(
        verbose_name='large version image url of logo/photo associated with voter guide', blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.URLField(
        verbose_name='medium version image url of logo/photo associated with voter guide', blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.URLField(
        verbose_name='tiny version image url of logo/photo associated with voter guide', blank=True, null=True)

    # Mapped directly from organization.organization_type
    voter_guide_owner_type = models.CharField(
        verbose_name="is owner org, public figure, or voter?", max_length=2, choices=ORGANIZATION_TYPE_CHOICES,
        default=UNKNOWN)

    twitter_handle = models.CharField(verbose_name='twitter screen_name', max_length=255, null=True, unique=False)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)
    twitter_followers_count = models.PositiveIntegerField(
        verbose_name="number of twitter followers", null=True, blank=True, default=0)

    pledge_goal = models.PositiveIntegerField(
        verbose_name="target number of voters for pledge drive", null=True, blank=True, default=0)
    pledge_count = models.PositiveIntegerField(
        verbose_name="number of voters who have pledged", null=True, blank=True, default=0)

    vote_smart_ratings_only = models.BooleanField(default=False)

    # We usually cache the voter guide name, but in case we haven't, we force the lookup
    def voter_guide_display_name(self):
        if self.display_name:
            return self.display_name
        elif self.voter_guide_owner_type == ORGANIZATION:
            return self.retrieve_organization_display_name()
        return ''

    def retrieve_organization_display_name(self):
        organization_manager = OrganizationManager()
        organization_id = 0
        organization_we_vote_id = self.organization_we_vote_id
        results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)
        if results['organization_found']:
            organization = results['organization']
            organization_name = organization.organization_name
            return organization_name

    # We try to cache the image_url, but in case we haven't, we force the lookup
    def voter_guide_image_url(self):
        if self.image_url:
            return self.image_url
        elif self.voter_guide_owner_type == ORGANIZATION:
            organization_manager = OrganizationManager()
            organization_id = 0
            organization_we_vote_id = self.organization_we_vote_id
            results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)
            if results['organization_found']:
                organization = results['organization']
                organization_photo_url = organization.organization_photo_url()
                return organization_photo_url
        return ''

    # The date of the last change to this voter_guide
    # TODO convert to date_last_changed
    last_updated = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # We want to map these here so they are available in the templates
    CORPORATION = CORPORATION
    GROUP = GROUP  # Group of people (not an individual), but org status unknown
    INDIVIDUAL = INDIVIDUAL
    NEWS_ORGANIZATION = NEWS_ORGANIZATION
    NONPROFIT = NONPROFIT
    NONPROFIT_501C3 = NONPROFIT_501C3
    NONPROFIT_501C4 = NONPROFIT_501C4
    POLITICAL_ACTION_COMMITTEE = POLITICAL_ACTION_COMMITTEE
    ORGANIZATION = ORGANIZATION  # Deprecate in favor of GROUP
    PUBLIC_FIGURE = PUBLIC_FIGURE
    VOTER = VOTER  # Deprecate in favor of Individual
    UNKNOWN = UNKNOWN

    def __unicode__(self):
        return self.last_updated

    class Meta:
        ordering = ('last_updated',)

    objects = VoterGuideManager()

    def organization(self):
        try:
            organization = Organization.objects.get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("voter_guide.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("voter_guide.organization did not find")
            return
        return organization

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this voter_guide came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            self.generate_new_we_vote_id()
        super(VoterGuide, self).save(*args, **kwargs)

    def generate_new_we_vote_id(self):
        # ...generate a new id
        site_unique_id_prefix = fetch_site_unique_id_prefix()
        next_local_integer = fetch_next_we_vote_id_voter_guide_integer()
        # "wv" = We Vote
        # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
        # "vg" = tells us this is a unique id for a voter guide
        # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
        self.we_vote_id = "wv{site_unique_id_prefix}vg{next_integer}".format(
            site_unique_id_prefix=site_unique_id_prefix,
            next_integer=next_local_integer,
        )
        # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        return


# This is the class that we use to rapidly show lists of voter guides, regardless of whether they are from an
# organization, public figure, or voter
class VoterGuideListManager(models.Model):
    """
    A set of methods to retrieve a list of voter_guides
    """

    # NOTE: This is extremely simple way to retrieve voter guides, used by admin tools. Being replaced by:
    #  retrieve_voter_guides_by_ballot_item(ballot_item_we_vote_id) AND
    #  retrieve_voter_guides_by_election(google_civic_election_id)
    def retrieve_voter_guides_for_election(self, google_civic_election_id):
        voter_guide_list = []
        voter_guide_list_found = False

        try:
            # voter_guide_query = VoterGuide.objects.order_by('-twitter_followers_count')
            voter_guide_query = VoterGuide.objects.order_by('display_name')
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_list = voter_guide_query.filter(
                google_civic_election_id=google_civic_election_id)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_voter_guides_for_election: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_voter_guides_by_organization_list(self, organization_we_vote_ids_followed_by_voter,
                                                   filter_by_this_google_civic_election_id=False):
        voter_guide_list = []
        voter_guide_list_found = False

        if not type(organization_we_vote_ids_followed_by_voter) is list:
            status = 'NO_VOTER_GUIDES_FOUND_MISSING_ORGANIZATION_LIST'
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'voter_guide_list_found':       voter_guide_list_found,
                'voter_guide_list':             voter_guide_list,
            }
            return results

        if not len(organization_we_vote_ids_followed_by_voter):
            status = 'NO_VOTER_GUIDES_FOUND_NO_ORGANIZATIONS_IN_LIST'
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'voter_guide_list_found':       voter_guide_list_found,
                'voter_guide_list':             voter_guide_list,
            }
            return results

        try:
            voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.filter(
                organization_we_vote_id__in=organization_we_vote_ids_followed_by_voter)
            test_election = 2000
            voter_guide_query = voter_guide_query.exclude(google_civic_election_id=test_election)
            if filter_by_this_google_civic_election_id:
                voter_guide_query = voter_guide_query.filter(
                    google_civic_election_id=filter_by_this_google_civic_election_id)
            voter_guide_query = voter_guide_query.order_by('-twitter_followers_count')
            voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDES_FOUND_BY_ORGANIZATION_LIST'
            else:
                status = 'NO_VOTER_GUIDES_FOUND_BY_ORGANIZATION_LIST'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        # If we have multiple voter guides for one org, we only want to show the most recent
        if voter_guide_list_found:
            voter_guide_list_filtered = self.remove_older_voter_guides_for_each_org(voter_guide_list)
        else:
            voter_guide_list_filtered = []

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list_filtered,
        }
        return results

    def retrieve_all_voter_guides_by_organization_we_vote_id(self, organization_we_vote_id, for_editing=True):
        return self.retrieve_all_voter_guides(organization_we_vote_id, for_editing=for_editing)

    def retrieve_all_voter_guides_by_voter_id(self, owner_voter_id):
        organization_we_vote_id = ""
        return self.retrieve_all_voter_guides(organization_we_vote_id, owner_voter_id)

    def retrieve_all_voter_guides_by_voter_we_vote_id(self, owner_voter_we_vote_id, for_editing=True):
        organization_we_vote_id = ""
        owner_voter_id = 0
        return self.retrieve_all_voter_guides(organization_we_vote_id, owner_voter_id, owner_voter_we_vote_id,
                                              for_editing)

    def retrieve_all_voter_guides(self, organization_we_vote_id, owner_voter_id=0, owner_voter_we_vote_id="",
                                  for_editing=True):
        voter_guide_list = []
        voter_guide_list_found = False

        if not positive_value_exists(organization_we_vote_id) and not positive_value_exists(owner_voter_id) and \
                not positive_value_exists(owner_voter_we_vote_id):
            status = 'NO_VOTER_GUIDES_FOUND-MISSING_REQUIRED_VARIABLE '
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'voter_guide_list_found':       voter_guide_list_found,
                'voter_guide_list':             voter_guide_list,
            }
            return results

        try:
            if positive_value_exists(for_editing):
                voter_guide_query = VoterGuide.objects.all()
            else:
                voter_guide_query = VoterGuide.objects.using('readonly').all()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            if positive_value_exists(organization_we_vote_id):
                voter_guide_query = voter_guide_query.filter(
                    organization_we_vote_id__iexact=organization_we_vote_id)
            elif positive_value_exists(owner_voter_id):
                voter_guide_query = voter_guide_query.filter(
                    owner_voter_id=owner_voter_id)
            elif positive_value_exists(owner_voter_we_vote_id):
                voter_guide_query = voter_guide_query.filter(
                    owner_we_vote_id__iexact=owner_voter_we_vote_id)
            voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDES_FOUND_BY_RETRIEVE_ALL_VOTER_GUIDES '
            else:
                status = 'NO_VOTER_GUIDES_FOUND_BY_RETRIEVE_ALL_VOTER_GUIDES '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_all_voter_guides: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_voter_guides_to_follow_by_election(self, google_civic_election_id, organization_we_vote_id_list,
                                                    search_string,
                                                    start_retrieve_at_this_number=0,
                                                    maximum_number_to_retrieve=0, sort_by='', sort_order=''):
        voter_guide_list = []
        voter_guide_list_found = False
        if not positive_value_exists(maximum_number_to_retrieve):
            maximum_number_to_retrieve = 30

        try:
            voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            if search_string:
                voter_guide_query = voter_guide_query.filter(Q(display_name__icontains=search_string) |
                                                             Q(twitter_handle__icontains=search_string))
            else:
                # If not searching, make sure we do not include individuals
                voter_guide_query = voter_guide_query.exclude(voter_guide_owner_type__iexact=INDIVIDUAL)

            voter_guide_query = voter_guide_query.filter(
                Q(google_civic_election_id=google_civic_election_id) &
                Q(organization_we_vote_id__in=organization_we_vote_id_list)
            )

            if positive_value_exists(start_retrieve_at_this_number):
                query_start_number = start_retrieve_at_this_number
                query_end_number = start_retrieve_at_this_number + maximum_number_to_retrieve
            else:
                query_start_number = 0
                query_end_number = maximum_number_to_retrieve

            if sort_order == 'desc':
                voter_guide_query = voter_guide_query.order_by('-' + sort_by)[query_start_number:query_end_number]
            else:
                voter_guide_query = voter_guide_query.order_by(sort_by)[query_start_number:query_end_number]

            voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDES_FOUND_BY_ELECTION '
            else:
                status = 'NO_VOTER_GUIDES_FOUND_BY_ELECTION '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        # status += " len(organization_we_vote_id_list): " + str(len(organization_we_vote_id_list)) + " :: "
        # for one_we_vote_id in organization_we_vote_id_list:
        #     status += one_we_vote_id + " "

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_voter_guides_to_follow_by_time_span(self, orgs_we_need_found_by_position_and_time_span_list_of_dicts,
                                                     search_string,
                                                     maximum_number_to_retrieve=0, sort_by='', sort_order=''):
        """
        Get the voter guides for orgs that we found by looking at the positions for an org found based on time span
        """
        voter_guide_list = []
        voter_guide_list_found = False
        if not positive_value_exists(maximum_number_to_retrieve):
            maximum_number_to_retrieve = 30

        if not len(orgs_we_need_found_by_position_and_time_span_list_of_dicts):
            status = "NO_VOTER_GUIDES_FOUND_BY_TIME_SPAN"
            results = {
                'success': True,
                'status': status,
                'voter_guide_list_found': voter_guide_list_found,
                'voter_guide_list': voter_guide_list,
            }
            return results

        try:
            voter_guide_query = VoterGuide.objects.all()

            # Retrieve all pairs that match vote_smart_time_span / organization_we_vote_id
            filter_list = Q()
            for item in orgs_we_need_found_by_position_and_time_span_list_of_dicts:
                filter_list |= Q(vote_smart_time_span=item['vote_smart_time_span'],
                                 organization_we_vote_id__iexact=item['organization_we_vote_id'])
            voter_guide_query = voter_guide_query.filter(filter_list)

            if search_string:
                voter_guide_query = voter_guide_query.filter(Q(display_name__icontains=search_string) |
                                                                   Q(twitter_handle__icontains=search_string))

            if sort_order == 'desc':
                voter_guide_query = voter_guide_query.order_by('-' + sort_by)[:maximum_number_to_retrieve]
            else:
                voter_guide_query = voter_guide_query.order_by(sort_by)[:maximum_number_to_retrieve]

            voter_guide_list = voter_guide_query
            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_voter_guides_to_follow_generic(self, organization_we_vote_ids_followed_or_ignored_by_voter,
                                                search_string,
                                                maximum_number_to_retrieve=0, sort_by='', sort_order=''):
        """
        Get the voter guides for orgs that we found by looking at the positions for an org found based on time span
        """
        voter_guide_list = []
        voter_guide_list_found = False
        if not positive_value_exists(maximum_number_to_retrieve):
            maximum_number_to_retrieve = 30

        try:
            voter_guide_query = VoterGuide.objects.all()
            # As of August 2018, we no longer want to support Vote Smart ratings voter guides
            voter_guide_query = voter_guide_query.exclude(vote_smart_time_span__isnull=False)
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)

            if len(organization_we_vote_ids_followed_or_ignored_by_voter):
                voter_guide_query = voter_guide_query.exclude(
                    organization_we_vote_id__in=organization_we_vote_ids_followed_or_ignored_by_voter)

            if search_string:
                # Each word in the search string can be anywhere in any field we search
                data = search_string.split()  # split search_string into a list

                for search_string_part in data:
                    voter_guide_query = voter_guide_query.filter(Q(display_name__icontains=search_string_part) |
                                                                 Q(twitter_handle__icontains=search_string_part))
            else:
                # If not searching, make sure we do not include individuals
                voter_guide_query = voter_guide_query.exclude(voter_guide_owner_type__iexact=INDIVIDUAL)

                # We also want to exclude voter guides with election_day_text smaller than today's date
                timezone = pytz.timezone("America/Los_Angeles")
                datetime_now = timezone.localize(datetime.now())
                two_days = timedelta(days=2)
                datetime_two_days_ago = datetime_now - two_days
                earliest_date_to_show = datetime_two_days_ago.strftime("%Y-%m-%d")
                voter_guide_query = voter_guide_query.exclude(election_day_text__lt=earliest_date_to_show)
                voter_guide_query = voter_guide_query.exclude(election_day_text__isnull=True)

            if sort_order == 'desc':
                voter_guide_query = voter_guide_query.order_by('-' + sort_by)[:maximum_number_to_retrieve]
            else:
                voter_guide_query = voter_guide_query.order_by(sort_by)[:maximum_number_to_retrieve]

            voter_guide_list = list(voter_guide_query)
            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND_GENERIC_VOTER_GUIDES_TO_FOLLOW'
            else:
                status = 'NO_VOTER_GUIDES_FOUND_GENERIC_VOTER_GUIDES_TO_FOLLOW'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        # If we have multiple voter guides for one org, we only want to show the most recent
        if voter_guide_list_found:
            voter_guide_list_filtered = self.remove_older_voter_guides_for_each_org(voter_guide_list)
        else:
            voter_guide_list_filtered = []

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list_filtered,
        }
        return results

    def remove_older_voter_guides_for_each_org(self, voter_guide_list):
        # If we have multiple voter guides for one org, we only want to show the most recent
        organization_already_reviewed = []
        organization_with_multiple_voter_guides = []
        newest_voter_guide_for_org = {}  # Figure out the newest voter guide per org that we should show
        for one_voter_guide in voter_guide_list:
            if one_voter_guide.organization_we_vote_id:
                if one_voter_guide.organization_we_vote_id not in organization_already_reviewed:
                    organization_already_reviewed.append(one_voter_guide.organization_we_vote_id)
                # Are we dealing with a time span (instead of google_civic_election_id)?
                if positive_value_exists(one_voter_guide.vote_smart_time_span):
                    # Take the first four digits of one_voter_guide.vote_smart_time_span
                    first_four_digits = convert_to_int(one_voter_guide.vote_smart_time_span[:4])
                    # And figure out the newest voter guide for each org
                    if one_voter_guide.organization_we_vote_id in newest_voter_guide_for_org:
                        # If we are here, it means we have seen this organization once already
                        if one_voter_guide.organization_we_vote_id not in organization_with_multiple_voter_guides:
                            organization_with_multiple_voter_guides.append(one_voter_guide.organization_we_vote_id)
                        # If this voter guide is newer than the one already looked at, update newest_voter_guide_for_org
                        if first_four_digits > newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id]:
                            newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id] = first_four_digits
                    else:
                        newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id] = first_four_digits

        voter_guide_list_filtered = []
        for one_voter_guide in voter_guide_list:
            if one_voter_guide.organization_we_vote_id in organization_with_multiple_voter_guides:
                if positive_value_exists(one_voter_guide.vote_smart_time_span):
                    first_four_digits = convert_to_int(one_voter_guide.vote_smart_time_span[:4])
                    if newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id] == first_four_digits:
                        # If this voter guide is the newest from among the org's voter guides, include in results
                        voter_guide_list_filtered.append(one_voter_guide)
            else:
                voter_guide_list_filtered.append(one_voter_guide)

        return voter_guide_list_filtered

    def retrieve_all_voter_guides_order_by(self, order_by='', limit_number=0, search_string='',
                                           google_civic_election_id=0, show_individuals=False):
        voter_guide_list = []
        voter_guide_list_found = False
        try:
            voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.exclude(vote_smart_time_span__isnull=False)
            if not positive_value_exists(show_individuals):
                voter_guide_query = voter_guide_query.exclude(voter_guide_owner_type__iexact=INDIVIDUAL)
            if positive_value_exists(google_civic_election_id):
                voter_guide_query = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)
            if order_by == 'google_civic_election_id':
                voter_guide_query = voter_guide_query.order_by(
                    '-vote_smart_time_span', '-google_civic_election_id')
            else:
                voter_guide_query = voter_guide_query.order_by('-twitter_followers_count')

            if positive_value_exists(search_string):
                search_words = search_string.split()
                for one_word in search_words:
                    filters = []

                    new_filter = Q(we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(display_name__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(google_civic_election_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(owner_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(public_figure_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(state_code__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(twitter_handle__icontains=one_word)
                    filters.append(new_filter)

                    # Add the first query
                    if len(filters):
                        final_filters = filters.pop()

                        # ...and "OR" the remaining items in the list
                        for item in filters:
                            final_filters |= item

                        voter_guide_query = voter_guide_query.filter(final_filters)

            if positive_value_exists(limit_number):
                voter_guide_list = voter_guide_query[:limit_number]
            else:
                voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_all_voter_guides_order_by: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def reorder_voter_guide_list(self, voter_guide_list, field_to_order_by, asc_or_desc='desc'):
        def get_key_to_sort_by():
            if field_to_order_by == 'twitter_followers_count':
                return 'twitter_followers_count'
            else:
                return 'twitter_followers_count'

        if not len(voter_guide_list):
            return []

        # If we set this to 'desc', then Reverse the sort below. Otherwise sort 'asc' (ascending)
        is_desc = True if asc_or_desc == 'desc' else False

        voter_guide_list_sorted = sorted(voter_guide_list, key=operator.attrgetter(get_key_to_sort_by()),
                                         reverse=is_desc)

        return voter_guide_list_sorted

    def retrieve_possible_duplicate_voter_guides(self, google_civic_election_id, vote_smart_time_span,
                                                 organization_we_vote_id, public_figure_we_vote_id,
                                                 twitter_handle,
                                                 we_vote_id_from_master=''):
        voter_guide_list_objects = []
        filters = []
        voter_guide_list_found = False

        try:
            voter_guide_query = VoterGuide.objects.all()
            if positive_value_exists(google_civic_election_id):
                voter_guide_query = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)
            elif positive_value_exists(vote_smart_time_span):
                voter_guide_query = voter_guide_query.filter(vote_smart_time_span__iexact=vote_smart_time_span)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                voter_guide_query = voter_guide_query.exclude(we_vote_id__iexact=we_vote_id_from_master)

            # We want to find candidates with *any* of these values
            if positive_value_exists(organization_we_vote_id):
                new_filter = Q(organization_we_vote_id__iexact=organization_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(public_figure_we_vote_id):
                new_filter = Q(public_figure_we_vote_id__iexact=public_figure_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(twitter_handle):
                new_filter = Q(twitter_handle__iexact=twitter_handle)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                voter_guide_query = voter_guide_query.filter(final_filters)

            voter_guide_list_objects = voter_guide_query

            if len(voter_guide_list_objects):
                voter_guide_list_found = True
                status = 'DUPLICATE_VOTER_GUIDES_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_VOTER_GUIDES_RETRIEVED'
                success = True
        except VoterGuide.DoesNotExist:
            # No voter guides found. Not a problem.
            status = 'NO_DUPLICATE_VOTER_GUIDES_FOUND_DoesNotExist'
            voter_guide_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_voter_guides ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'voter_guide_list_found':   voter_guide_list_found,
            'voter_guide_list':         voter_guide_list_objects,
        }
        return results


class VoterGuidePossibilityManager(models.Manager):
    """
    A class for working with the VoterGuidePossibility model
    """
    def update_or_create_voter_guide_possibility(
            self, voter_guide_possibility_url,
            voter_guide_possibility_id=0,
            target_google_civic_election_id=0,
            updated_values={}):
        exception_multiple_object_returned = False
        success = False
        new_voter_guide_possibility_created = False
        voter_guide_possibility = VoterGuidePossibility()
        voter_guide_possibility_found = False
        status = ""

        if positive_value_exists(voter_guide_possibility_id):
            # Check before we try to create a new entry
            try:
                voter_guide_possibility = VoterGuidePossibility.objects.get(
                    id=voter_guide_possibility_id,
                )
                voter_guide_possibility_found = True
                success = True
                status += 'VOTER_GUIDE_POSSIBILITY_FOUND_BY_ID '
            except VoterGuidePossibility.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_VOTER_GUIDE_POSSIBILITY_NOT_FOUND_BY_WE_VOTE_ID "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        if not voter_guide_possibility_found:
            try:
                voter_guide_possibility = VoterGuidePossibility.objects.get(
                    voter_guide_possibility_url__iexact=voter_guide_possibility_url,
                    target_google_civic_election_id=target_google_civic_election_id,
                )
                voter_guide_possibility_found = True
                success = True
                status += 'VOTER_GUIDE_POSSIBILITY_FOUND_BY_URL '
            except VoterGuidePossibility.MultipleObjectsReturned as e:
                status += 'MULTIPLE_MATCHING_VOTER_GUIDE_POSSIBILITIES_FOUND_BY_URL-CREATE_NEW '
            except VoterGuidePossibility.DoesNotExist:
                status += "RETRIEVE_VOTER_GUIDE_POSSIBILITY_NOT_FOUND_BY_URL "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_BY_URL ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        if voter_guide_possibility_found:
            # Update record
            try:
                new_voter_guide_possibility_created = False
                voter_guide_possibility_updated = False
                voter_guide_possibility_has_changes = False
                for key, value in updated_values.items():
                    if hasattr(voter_guide_possibility, key):
                        voter_guide_possibility_has_changes = True
                        setattr(voter_guide_possibility, key, value)
                if voter_guide_possibility_has_changes and positive_value_exists(voter_guide_possibility.id):
                    voter_guide_possibility.save()
                    voter_guide_possibility_id = voter_guide_possibility.id
                    voter_guide_possibility_updated = True
                if voter_guide_possibility_updated:
                    success = True
                    status += "VOTER_GUIDE_POSSIBILITY_UPDATED "
                else:
                    success = False
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_UPDATED "
            except Exception as e:
                status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        else:
            # Create record
            try:
                new_voter_guide_possibility_created = False
                voter_guide_possibility = VoterGuidePossibility.objects.create(
                    voter_guide_possibility_url=voter_guide_possibility_url,
                    target_google_civic_election_id=target_google_civic_election_id,
                )
                if positive_value_exists(voter_guide_possibility.id):
                    for key, value in updated_values.items():
                        if hasattr(voter_guide_possibility, key):
                            setattr(voter_guide_possibility, key, value)
                    voter_guide_possibility.save()
                    voter_guide_possibility_id = voter_guide_possibility.id
                    new_voter_guide_possibility_created = True
                if new_voter_guide_possibility_created:
                    success = True
                    status += "VOTER_GUIDE_POSSIBILITY_CREATED "
                else:
                    success = False
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_CREATED "
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOTER_GUIDE_POSSIBILITY ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                              success,
            'status':                               status,
            'MultipleObjectsReturned':              exception_multiple_object_returned,
            'voter_guide_possibility_saved':        success,
            'new_voter_guide_possibility_created':  new_voter_guide_possibility_created,
            'voter_guide_possibility':              voter_guide_possibility,
            'voter_guide_possibility_id':           voter_guide_possibility_id,
        }
        return results

    def retrieve_voter_guide_possibility_from_url(self, voter_guide_possibility_url):
        voter_guide_possibility_id = 0
        google_civic_election_id = 0
        return self.retrieve_voter_guide_possibility(voter_guide_possibility_id, google_civic_election_id,
                                                     voter_guide_possibility_url)

    def retrieve_voter_guide_possibility(self, voter_guide_possibility_id=0, google_civic_election_id=0,
                                         voter_guide_possibility_url='',
                                         organization_we_vote_id=None,
                                         public_figure_we_vote_id=None,
                                         owner_we_vote_id=None):
        voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        organization_we_vote_id = convert_to_str(organization_we_vote_id)
        owner_we_vote_id = convert_to_str(owner_we_vote_id)

        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_guide_possibility_on_stage = VoterGuidePossibility()
        voter_guide_possibility_on_stage_id = 0
        try:
            if positive_value_exists(voter_guide_possibility_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_ID"  # Set this in case the get fails
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(id=voter_guide_possibility_id)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_ID"
                success = True
            elif positive_value_exists(voter_guide_possibility_url):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_URL"  # Set this in case the get fails
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    voter_guide_possibility_url=voter_guide_possibility_url)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_URL"
                success = True
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                # Set this status in case the 'get' fails
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_ORGANIZATION_WE_VOTE_ID "
                # TODO: Update this to deal with the google_civic_election_id being spread across 50 fields
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    google_civic_election_id=google_civic_election_id,
                    organization_we_vote_id__iexact=organization_we_vote_id)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_ORGANIZATION_WE_VOTE_ID"
                success = True
            elif positive_value_exists(owner_we_vote_id) and positive_value_exists(google_civic_election_id):
                # Set this status in case the 'get' fails
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_VOTER_WE_VOTE_ID"
                # TODO: Update this to deal with the google_civic_election_id being spread across 50 fields
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    google_civic_election_id=google_civic_election_id,
                    owner_we_vote_id__iexact=owner_we_vote_id)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_VOTER_WE_VOTE_ID"
                success = True
            else:
                status = "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_INSUFFICIENT_VARIABLES"
                success = False
        except VoterGuidePossibility.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status += ", ERROR_MORE_THAN_ONE_VOTER_GUIDE_POSSIBILITY_FOUND"
            success = False
        except VoterGuidePossibility.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status = "VOTER_GUIDE_POSSIBILITY_NOT_FOUND"
            success = True

        voter_guide_possibility_on_stage_found = True if voter_guide_possibility_on_stage_id > 0 else False
        results = {
            'success':                          success,
            'status':                           status,
            'organization_we_vote_id':          voter_guide_possibility_on_stage.organization_we_vote_id,
            'voter_guide_possibility':          voter_guide_possibility_on_stage,
            'voter_guide_possibility_found':    voter_guide_possibility_on_stage_found,
            'voter_guide_possibility_id':       voter_guide_possibility_on_stage_id,
            'voter_guide_possibility_url':      voter_guide_possibility_on_stage.voter_guide_possibility_url,
            'error_result':                     error_result,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
        }
        return results

    def retrieve_voter_guide_possibility_list(self, order_by='', limit_number=0, search_string='',
                                              google_civic_election_id=0,
                                              hide_from_active_review=False,
                                              cannot_find_endorsements=False,
                                              candidates_missing_from_we_vote=False):
        candidates_missing_from_we_vote = positive_value_exists(candidates_missing_from_we_vote)
        cannot_find_endorsements = positive_value_exists(cannot_find_endorsements)
        hide_from_active_review = positive_value_exists(hide_from_active_review)
        voter_guide_possibility_list = []
        voter_guide_possibility_list_found = False
        try:
            voter_guide_query = VoterGuidePossibility.objects.all()
            voter_guide_query = voter_guide_query.order_by(order_by)

            # Allow searching for voter guide possibilities that are being ignored
            if not positive_value_exists(search_string):
                voter_guide_query = voter_guide_query.exclude(ignore_this_source=True)
                voter_guide_query = voter_guide_query.filter(hide_from_active_review=hide_from_active_review)
                # Cannot find endorsements
                if positive_value_exists(cannot_find_endorsements):
                    voter_guide_query = voter_guide_query.filter(cannot_find_endorsements=cannot_find_endorsements)
                elif not positive_value_exists(hide_from_active_review) \
                        and not positive_value_exists(candidates_missing_from_we_vote):
                    # Only search for cannot_find_endorsements set to false if NOT showing 'Archived'
                    # or 'Candidates/Measures Missing'
                    voter_guide_query = voter_guide_query.filter(cannot_find_endorsements=False)
                # Candidates/Measures Missing
                if positive_value_exists(candidates_missing_from_we_vote):
                    voter_guide_query = voter_guide_query.filter(
                        candidates_missing_from_we_vote=candidates_missing_from_we_vote)
                elif not positive_value_exists(hide_from_active_review) \
                        and not positive_value_exists(cannot_find_endorsements):
                    # Only search for candidates_missing_from_we_vote set to false if NOT showing 'Archived'
                    # or 'Endorsements Not Available Yet'
                    voter_guide_query = voter_guide_query.filter(
                        candidates_missing_from_we_vote=False)

            if positive_value_exists(search_string):
                search_words = search_string.split()
                candidate_number_list = CANDIDATE_NUMBER_LIST
                for one_word in search_words:
                    filters = []

                    new_filter = Q(ballot_items_raw__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_name__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_twitter_handle__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(voter_guide_possibility_url__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(voter_who_submitted_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(voter_who_submitted_name__icontains=one_word)
                    filters.append(new_filter)

                    # new_filter = Q(candidate_we_vote_id_001__icontains=one_word)
                    # filters.append(new_filter)

                    for one_number in candidate_number_list:
                        key = "candidate_we_vote_id_" + one_number + "__icontains"
                        new_filter = Q(**{key: one_word})
                        filters.append(new_filter)

                        key = "candidate_name_" + one_number + "__icontains"
                        new_filter = Q(**{key: one_word})
                        filters.append(new_filter)

                    # Add the first query
                    if len(filters):
                        final_filters = filters.pop()

                        # ...and "OR" the remaining items in the list
                        for item in filters:
                            final_filters |= item

                        voter_guide_query = voter_guide_query.filter(final_filters)

            if positive_value_exists(limit_number):
                voter_guide_possibility_list = voter_guide_query[:limit_number]
            else:
                voter_guide_possibility_list = list(voter_guide_query)

            if len(voter_guide_possibility_list):
                voter_guide_possibility_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_all_voter_guides_order_by: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                              success,
            'status':                               status,
            'voter_guide_possibility_list_found':   voter_guide_possibility_list_found,
            'voter_guide_possibility_list':         voter_guide_possibility_list,
        }
        return results

    def delete_voter_guide_possibility(self, voter_guide_possibility_id):
        voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
        voter_guide_possibility_deleted = False

        try:
            if positive_value_exists(voter_guide_possibility_id):
                results = self.retrieve_voter_guide_possibility(voter_guide_possibility_id)
                if results['voter_guide_possibility_found']:
                    voter_guide_possibility = results['voter_guide_possibility']
                    voter_guide_possibility_id = voter_guide_possibility.id
                    voter_guide_possibility.delete()
                    voter_guide_possibility_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':                          voter_guide_possibility_deleted,
            'voter_guide_possibility_deleted':  voter_guide_possibility_deleted,
            'voter_guide_possibility_id':       voter_guide_possibility_id,
        }
        return results


class VoterGuidePossibility(models.Model):
    """
    We ask volunteers to enter a list of urls that might have voter guides. This table stores the URLs and partial
    information, prior to a full-fledged voter guide being saved in the VoterGuide table.
    """
    # We are relying on built-in Python id field

    # Where a volunteer thinks there is a voter guide
    voter_guide_possibility_url = models.URLField(verbose_name='url of possible voter guide', blank=True, null=True)

    # The unique id of the organization, if/when we know it
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id", max_length=255, null=True, blank=True, unique=False)

    voter_who_submitted_name = models.CharField(
        verbose_name="voter name who submitted this", max_length=255, null=True, blank=True, unique=False)

    voter_who_submitted_we_vote_id = models.CharField(
        verbose_name="voter we vote id who submitted this", max_length=255, null=True, blank=True, unique=False)

    state_code = models.CharField(verbose_name="state the voter guide is related to", max_length=2, null=True)

    # Mapped directly from organization.organization_type
    voter_guide_owner_type = models.CharField(
        verbose_name="is owner org, public figure, or voter?", max_length=2, choices=ORGANIZATION_TYPE_CHOICES,
        default=UNKNOWN)

    organization_name = models.CharField(
        verbose_name="organization name", max_length=255, null=True, blank=True, unique=False)
    organization_twitter_handle = models.CharField(
        verbose_name="organization twitter handle", max_length=255, null=True, blank=True, unique=False)
    # These are the candidates or measures on the voter guide (comma separated, or on own lines)
    ballot_items_raw = models.TextField(null=True, blank=True,)

    # What election was used as the target for finding endorsements?
    target_google_civic_election_id = models.PositiveIntegerField(null=True)

    # Data manager sees candidates or measures on voter guide that are not in the We Vote database
    candidates_missing_from_we_vote = models.BooleanField(default=False)

    # Data manager cannot find upcoming endorsements (may not be posted yet)
    cannot_find_endorsements = models.BooleanField(default=False)

    # Data manager will need to put more work into this in order to capture all of the details
    capture_detailed_comments = models.BooleanField(default=False)

    # While processing and reviewing this organization's endorsements, leave out positions already stored
    ignore_stored_positions = models.BooleanField(default=False)

    # This website is not a good source for future endorsements
    ignore_this_source = models.BooleanField(default=False)

    # Has this VoterGuidePossibility been used to create a batch in the import_export_batch system?
    hide_from_active_review = models.BooleanField(default=False)
    batch_header_id = models.PositiveIntegerField(null=True)

    # For internal notes regarding gathering data
    internal_notes = models.TextField(null=True, blank=True, default=None)

    # The date of the last change to this voter_guide_possibility
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)  # last_updated

    def __unicode__(self):
        return self.date_last_changed

    class Meta:
        ordering = ('date_last_changed',)

    objects = VoterGuideManager()

    def organization(self):
        if not positive_value_exists(self.organization_we_vote_id):
            return

        try:
            organization = Organization.objects.get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("voter_guide_possibility.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("voter_guide_possibility.organization did not find")
            return
        return organization

    def positions_ready_to_save_as_batch(self):
        candidates_in_batch_exist_in_database = False
        organization_found = False
        if positive_value_exists(self.organization_we_vote_id):
            organization_found = True

            if positive_value_exists(self.number_of_candidates_in_database()):
                candidates_in_batch_exist_in_database = True

        if positive_value_exists(self.voter_guide_possibility_url) and organization_found \
                and candidates_in_batch_exist_in_database:
            return True

        return False

    def number_of_candidates(self):
        number_of_candidates_count = 0
        candidate_number_list = CANDIDATE_NUMBER_LIST

        for candidate_number in candidate_number_list:
            if number_of_candidates_count >= len(candidate_number_list):
                break
            if positive_value_exists(getattr(self, 'candidate_name_' + candidate_number)):
                number_of_candidates_count += 1
            else:
                return number_of_candidates_count

        return number_of_candidates_count

    def number_of_candidates_in_database(self):
        number_of_candidates_count = 0
        number_of_candidates_in_database_count = 0
        candidate_number_list = CANDIDATE_NUMBER_LIST

        for candidate_number in candidate_number_list:
            if number_of_candidates_count >= len(candidate_number_list):
                break
            if positive_value_exists(getattr(self, 'candidate_name_' + candidate_number)):
                number_of_candidates_count += 1
            else:
                # Whenever we find an entry without a candidate_name_ we exit
                return number_of_candidates_in_database_count

            # We put this *after* the "exit valve" (when there isn't a value in "candidate_name_"
            if positive_value_exists(getattr(self, 'candidate_we_vote_id_' + candidate_number)):
                number_of_candidates_in_database_count += 1

        return number_of_candidates_in_database_count

    def number_of_candidates_not_in_database(self):
        number_of_candidates_count = 0
        number_of_candidates_not_in_database_count = 0
        candidate_number_list = CANDIDATE_NUMBER_LIST

        for candidate_number in candidate_number_list:
            if number_of_candidates_count >= len(candidate_number_list):
                break
            if positive_value_exists(getattr(self, 'candidate_name_' + candidate_number)):
                number_of_candidates_count += 1
            else:
                # Whenever we find an entry without a candidate_name_ we exit
                return number_of_candidates_not_in_database_count

            # We put this *after* the "exit valve" (when there isn't a value in "candidate_name_"
            if not positive_value_exists(getattr(self, 'candidate_we_vote_id_' + candidate_number)):
                number_of_candidates_not_in_database_count += 1

        return number_of_candidates_not_in_database_count

    candidate_name_001 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_001 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_001 = models.TextField(null=True, blank=True)
    google_civic_election_id_001 = models.PositiveIntegerField(null=True)
    stance_about_candidate_001 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_002 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_002 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_002 = models.TextField(null=True, blank=True)
    google_civic_election_id_002 = models.PositiveIntegerField(null=True)
    stance_about_candidate_002 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_003 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_003 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_003 = models.TextField(null=True, blank=True)
    google_civic_election_id_003 = models.PositiveIntegerField(null=True)
    stance_about_candidate_003 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_004 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_004 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_004 = models.TextField(null=True, blank=True)
    google_civic_election_id_004 = models.PositiveIntegerField(null=True)
    stance_about_candidate_004 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_005 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_005 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_005 = models.TextField(null=True, blank=True)
    google_civic_election_id_005 = models.PositiveIntegerField(null=True)
    stance_about_candidate_005 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_006 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_006 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_006 = models.TextField(null=True, blank=True)
    google_civic_election_id_006 = models.PositiveIntegerField(null=True)
    stance_about_candidate_006 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_007 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_007 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_007 = models.TextField(null=True, blank=True)
    google_civic_election_id_007 = models.PositiveIntegerField(null=True)
    stance_about_candidate_007 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_008 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_008 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_008 = models.TextField(null=True, blank=True)
    google_civic_election_id_008 = models.PositiveIntegerField(null=True)
    stance_about_candidate_008 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_009 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_009 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_009 = models.TextField(null=True, blank=True)
    google_civic_election_id_009 = models.PositiveIntegerField(null=True)
    stance_about_candidate_009 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_010 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_010 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_010 = models.TextField(null=True, blank=True)
    google_civic_election_id_010 = models.PositiveIntegerField(null=True)
    stance_about_candidate_010 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_011 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_011 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_011 = models.TextField(null=True, blank=True)
    google_civic_election_id_011 = models.PositiveIntegerField(null=True)
    stance_about_candidate_011 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_012 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_012 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_012 = models.TextField(null=True, blank=True)
    google_civic_election_id_012 = models.PositiveIntegerField(null=True)
    stance_about_candidate_012 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_013 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_013 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_013 = models.TextField(null=True, blank=True)
    google_civic_election_id_013 = models.PositiveIntegerField(null=True)
    stance_about_candidate_013 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_014 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_014 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_014 = models.TextField(null=True, blank=True)
    google_civic_election_id_014 = models.PositiveIntegerField(null=True)
    stance_about_candidate_014 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_015 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_015 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_015 = models.TextField(null=True, blank=True)
    google_civic_election_id_015 = models.PositiveIntegerField(null=True)
    stance_about_candidate_015 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_016 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_016 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_016 = models.TextField(null=True, blank=True)
    google_civic_election_id_016 = models.PositiveIntegerField(null=True)
    stance_about_candidate_016 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_017 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_017 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_017 = models.TextField(null=True, blank=True)
    google_civic_election_id_017 = models.PositiveIntegerField(null=True)
    stance_about_candidate_017 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_018 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_018 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_018 = models.TextField(null=True, blank=True)
    google_civic_election_id_018 = models.PositiveIntegerField(null=True)
    stance_about_candidate_018 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_019 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_019 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_019 = models.TextField(null=True, blank=True)
    google_civic_election_id_019 = models.PositiveIntegerField(null=True)
    stance_about_candidate_019 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_020 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_020 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_020 = models.TextField(null=True, blank=True)
    google_civic_election_id_020 = models.PositiveIntegerField(null=True)
    stance_about_candidate_020 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_021 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_021 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_021 = models.TextField(null=True, blank=True)
    google_civic_election_id_021 = models.PositiveIntegerField(null=True)
    stance_about_candidate_021 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_022 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_022 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_022 = models.TextField(null=True, blank=True)
    google_civic_election_id_022 = models.PositiveIntegerField(null=True)
    stance_about_candidate_022 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_023 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_023 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_023 = models.TextField(null=True, blank=True)
    google_civic_election_id_023 = models.PositiveIntegerField(null=True)
    stance_about_candidate_023 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_024 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_024 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_024 = models.TextField(null=True, blank=True)
    google_civic_election_id_024 = models.PositiveIntegerField(null=True)
    stance_about_candidate_024 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_025 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_025 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_025 = models.TextField(null=True, blank=True)
    google_civic_election_id_025 = models.PositiveIntegerField(null=True)
    stance_about_candidate_025 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_026 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_026 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_026 = models.TextField(null=True, blank=True)
    google_civic_election_id_026 = models.PositiveIntegerField(null=True)
    stance_about_candidate_026 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_027 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_027 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_027 = models.TextField(null=True, blank=True)
    google_civic_election_id_027 = models.PositiveIntegerField(null=True)
    stance_about_candidate_027 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_028 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_028 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_028 = models.TextField(null=True, blank=True)
    google_civic_election_id_028 = models.PositiveIntegerField(null=True)
    stance_about_candidate_028 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_029 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_029 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_029 = models.TextField(null=True, blank=True)
    google_civic_election_id_029 = models.PositiveIntegerField(null=True)
    stance_about_candidate_029 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_030 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_030 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_030 = models.TextField(null=True, blank=True)
    google_civic_election_id_030 = models.PositiveIntegerField(null=True)
    stance_about_candidate_030 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_031 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_031 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_031 = models.TextField(null=True, blank=True)
    google_civic_election_id_031 = models.PositiveIntegerField(null=True)
    stance_about_candidate_031 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_032 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_032 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_032 = models.TextField(null=True, blank=True)
    google_civic_election_id_032 = models.PositiveIntegerField(null=True)
    stance_about_candidate_032 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_033 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_033 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_033 = models.TextField(null=True, blank=True)
    google_civic_election_id_033 = models.PositiveIntegerField(null=True)
    stance_about_candidate_033 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_034 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_034 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_034 = models.TextField(null=True, blank=True)
    google_civic_election_id_034 = models.PositiveIntegerField(null=True)
    stance_about_candidate_034 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_035 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_035 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_035 = models.TextField(null=True, blank=True)
    google_civic_election_id_035 = models.PositiveIntegerField(null=True)
    stance_about_candidate_035 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_036 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_036 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_036 = models.TextField(null=True, blank=True)
    google_civic_election_id_036 = models.PositiveIntegerField(null=True)
    stance_about_candidate_036 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_037 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_037 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_037 = models.TextField(null=True, blank=True)
    google_civic_election_id_037 = models.PositiveIntegerField(null=True)
    stance_about_candidate_037 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_038 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_038 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_038 = models.TextField(null=True, blank=True)
    google_civic_election_id_038 = models.PositiveIntegerField(null=True)
    stance_about_candidate_038 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_039 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_039 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_039 = models.TextField(null=True, blank=True)
    google_civic_election_id_039 = models.PositiveIntegerField(null=True)
    stance_about_candidate_039 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_040 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_040 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_040 = models.TextField(null=True, blank=True)
    google_civic_election_id_040 = models.PositiveIntegerField(null=True)
    stance_about_candidate_040 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_041 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_041 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_041 = models.TextField(null=True, blank=True)
    google_civic_election_id_041 = models.PositiveIntegerField(null=True)
    stance_about_candidate_041 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_042 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_042 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_042 = models.TextField(null=True, blank=True)
    google_civic_election_id_042 = models.PositiveIntegerField(null=True)
    stance_about_candidate_042 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_043 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_043 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_043 = models.TextField(null=True, blank=True)
    google_civic_election_id_043 = models.PositiveIntegerField(null=True)
    stance_about_candidate_043 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_044 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_044 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_044 = models.TextField(null=True, blank=True)
    google_civic_election_id_044 = models.PositiveIntegerField(null=True)
    stance_about_candidate_044 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_045 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_045 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_045 = models.TextField(null=True, blank=True)
    google_civic_election_id_045 = models.PositiveIntegerField(null=True)
    stance_about_candidate_045 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_046 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_046 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_046 = models.TextField(null=True, blank=True)
    google_civic_election_id_046 = models.PositiveIntegerField(null=True)
    stance_about_candidate_046 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_047 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_047 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_047 = models.TextField(null=True, blank=True)
    google_civic_election_id_047 = models.PositiveIntegerField(null=True)
    stance_about_candidate_047 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_048 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_048 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_048 = models.TextField(null=True, blank=True)
    google_civic_election_id_048 = models.PositiveIntegerField(null=True)
    stance_about_candidate_048 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_049 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_049 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_049 = models.TextField(null=True, blank=True)
    google_civic_election_id_049 = models.PositiveIntegerField(null=True)
    stance_about_candidate_049 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_050 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_050 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_050 = models.TextField(null=True, blank=True)
    google_civic_election_id_050 = models.PositiveIntegerField(null=True)
    stance_about_candidate_050 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_051 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_051 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_051 = models.TextField(null=True, blank=True)
    google_civic_election_id_051 = models.PositiveIntegerField(null=True)
    stance_about_candidate_051 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_052 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_052 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_052 = models.TextField(null=True, blank=True)
    google_civic_election_id_052 = models.PositiveIntegerField(null=True)
    stance_about_candidate_052 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_053 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_053 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_053 = models.TextField(null=True, blank=True)
    google_civic_election_id_053 = models.PositiveIntegerField(null=True)
    stance_about_candidate_053 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_054 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_054 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_054 = models.TextField(null=True, blank=True)
    google_civic_election_id_054 = models.PositiveIntegerField(null=True)
    stance_about_candidate_054 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_055 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_055 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_055 = models.TextField(null=True, blank=True)
    google_civic_election_id_055 = models.PositiveIntegerField(null=True)
    stance_about_candidate_055 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_056 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_056 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_056 = models.TextField(null=True, blank=True)
    google_civic_election_id_056 = models.PositiveIntegerField(null=True)
    stance_about_candidate_056 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_057 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_057 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_057 = models.TextField(null=True, blank=True)
    google_civic_election_id_057 = models.PositiveIntegerField(null=True)
    stance_about_candidate_057 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_058 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_058 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_058 = models.TextField(null=True, blank=True)
    google_civic_election_id_058 = models.PositiveIntegerField(null=True)
    stance_about_candidate_058 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_059 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_059 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_059 = models.TextField(null=True, blank=True)
    google_civic_election_id_059 = models.PositiveIntegerField(null=True)
    stance_about_candidate_059 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_060 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_060 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_060 = models.TextField(null=True, blank=True)
    google_civic_election_id_060 = models.PositiveIntegerField(null=True)
    stance_about_candidate_060 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_061 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_061 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_061 = models.TextField(null=True, blank=True)
    google_civic_election_id_061 = models.PositiveIntegerField(null=True)
    stance_about_candidate_061 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_062 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_062 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_062 = models.TextField(null=True, blank=True)
    google_civic_election_id_062 = models.PositiveIntegerField(null=True)
    stance_about_candidate_062 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_063 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_063 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_063 = models.TextField(null=True, blank=True)
    google_civic_election_id_063 = models.PositiveIntegerField(null=True)
    stance_about_candidate_063 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_064 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_064 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_064 = models.TextField(null=True, blank=True)
    google_civic_election_id_064 = models.PositiveIntegerField(null=True)
    stance_about_candidate_064 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_065 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_065 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_065 = models.TextField(null=True, blank=True)
    google_civic_election_id_065 = models.PositiveIntegerField(null=True)
    stance_about_candidate_065 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_066 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_066 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_066 = models.TextField(null=True, blank=True)
    google_civic_election_id_066 = models.PositiveIntegerField(null=True)
    stance_about_candidate_066 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_067 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_067 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_067 = models.TextField(null=True, blank=True)
    google_civic_election_id_067 = models.PositiveIntegerField(null=True)
    stance_about_candidate_067 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_068 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_068 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_068 = models.TextField(null=True, blank=True)
    google_civic_election_id_068 = models.PositiveIntegerField(null=True)
    stance_about_candidate_068 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_069 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_069 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_069 = models.TextField(null=True, blank=True)
    google_civic_election_id_069 = models.PositiveIntegerField(null=True)
    stance_about_candidate_069 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_070 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_070 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_070 = models.TextField(null=True, blank=True)
    google_civic_election_id_070 = models.PositiveIntegerField(null=True)
    stance_about_candidate_070 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_071 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_071 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_071 = models.TextField(null=True, blank=True)
    google_civic_election_id_071 = models.PositiveIntegerField(null=True)
    stance_about_candidate_071 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_072 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_072 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_072 = models.TextField(null=True, blank=True)
    google_civic_election_id_072 = models.PositiveIntegerField(null=True)
    stance_about_candidate_072 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_073 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_073 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_073 = models.TextField(null=True, blank=True)
    google_civic_election_id_073 = models.PositiveIntegerField(null=True)
    stance_about_candidate_073 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_074 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_074 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_074 = models.TextField(null=True, blank=True)
    google_civic_election_id_074 = models.PositiveIntegerField(null=True)
    stance_about_candidate_074 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_075 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_075 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_075 = models.TextField(null=True, blank=True)
    google_civic_election_id_075 = models.PositiveIntegerField(null=True)
    stance_about_candidate_075 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_076 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_076 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_076 = models.TextField(null=True, blank=True)
    google_civic_election_id_076 = models.PositiveIntegerField(null=True)
    stance_about_candidate_076 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_077 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_077 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_077 = models.TextField(null=True, blank=True)
    google_civic_election_id_077 = models.PositiveIntegerField(null=True)
    stance_about_candidate_077 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_078 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_078 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_078 = models.TextField(null=True, blank=True)
    google_civic_election_id_078 = models.PositiveIntegerField(null=True)
    stance_about_candidate_078 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_079 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_079 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_079 = models.TextField(null=True, blank=True)
    google_civic_election_id_079 = models.PositiveIntegerField(null=True)
    stance_about_candidate_079 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_080 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_080 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_080 = models.TextField(null=True, blank=True)
    google_civic_election_id_080 = models.PositiveIntegerField(null=True)
    stance_about_candidate_080 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_081 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_081 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_081 = models.TextField(null=True, blank=True)
    google_civic_election_id_081 = models.PositiveIntegerField(null=True)
    stance_about_candidate_081 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_082 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_082 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_082 = models.TextField(null=True, blank=True)
    google_civic_election_id_082 = models.PositiveIntegerField(null=True)
    stance_about_candidate_082 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_083 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_083 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_083 = models.TextField(null=True, blank=True)
    google_civic_election_id_083 = models.PositiveIntegerField(null=True)
    stance_about_candidate_083 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_084 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_084 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_084 = models.TextField(null=True, blank=True)
    google_civic_election_id_084 = models.PositiveIntegerField(null=True)
    stance_about_candidate_084 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_085 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_085 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_085 = models.TextField(null=True, blank=True)
    google_civic_election_id_085 = models.PositiveIntegerField(null=True)
    stance_about_candidate_085 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_086 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_086 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_086 = models.TextField(null=True, blank=True)
    google_civic_election_id_086 = models.PositiveIntegerField(null=True)
    stance_about_candidate_086 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_087 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_087 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_087 = models.TextField(null=True, blank=True)
    google_civic_election_id_087 = models.PositiveIntegerField(null=True)
    stance_about_candidate_087 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_088 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_088 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_088 = models.TextField(null=True, blank=True)
    google_civic_election_id_088 = models.PositiveIntegerField(null=True)
    stance_about_candidate_088 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_089 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_089 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_089 = models.TextField(null=True, blank=True)
    google_civic_election_id_089 = models.PositiveIntegerField(null=True)
    stance_about_candidate_089 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_090 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_090 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_090 = models.TextField(null=True, blank=True)
    google_civic_election_id_090 = models.PositiveIntegerField(null=True)
    stance_about_candidate_090 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_091 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_091 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_091 = models.TextField(null=True, blank=True)
    google_civic_election_id_091 = models.PositiveIntegerField(null=True)
    stance_about_candidate_091 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_092 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_092 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_092 = models.TextField(null=True, blank=True)
    google_civic_election_id_092 = models.PositiveIntegerField(null=True)
    stance_about_candidate_092 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_093 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_093 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_093 = models.TextField(null=True, blank=True)
    google_civic_election_id_093 = models.PositiveIntegerField(null=True)
    stance_about_candidate_093 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_094 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_094 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_094 = models.TextField(null=True, blank=True)
    google_civic_election_id_094 = models.PositiveIntegerField(null=True)
    stance_about_candidate_094 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_095 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_095 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_095 = models.TextField(null=True, blank=True)
    google_civic_election_id_095 = models.PositiveIntegerField(null=True)
    stance_about_candidate_095 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_096 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_096 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_096 = models.TextField(null=True, blank=True)
    google_civic_election_id_096 = models.PositiveIntegerField(null=True)
    stance_about_candidate_096 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_097 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_097 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_097 = models.TextField(null=True, blank=True)
    google_civic_election_id_097 = models.PositiveIntegerField(null=True)
    stance_about_candidate_097 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_098 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_098 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_098 = models.TextField(null=True, blank=True)
    google_civic_election_id_098 = models.PositiveIntegerField(null=True)
    stance_about_candidate_098 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_099 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_099 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_099 = models.TextField(null=True, blank=True)
    google_civic_election_id_099 = models.PositiveIntegerField(null=True)
    stance_about_candidate_099 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_100 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_100 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_100 = models.TextField(null=True, blank=True)
    google_civic_election_id_100 = models.PositiveIntegerField(null=True)
    stance_about_candidate_100 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_101 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_101 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_101 = models.TextField(null=True, blank=True)
    google_civic_election_id_101 = models.PositiveIntegerField(null=True)
    stance_about_candidate_101 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_102 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_102 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_102 = models.TextField(null=True, blank=True)
    google_civic_election_id_102 = models.PositiveIntegerField(null=True)
    stance_about_candidate_102 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_103 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_103 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_103 = models.TextField(null=True, blank=True)
    google_civic_election_id_103 = models.PositiveIntegerField(null=True)
    stance_about_candidate_103 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_104 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_104 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_104 = models.TextField(null=True, blank=True)
    google_civic_election_id_104 = models.PositiveIntegerField(null=True)
    stance_about_candidate_104 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_105 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_105 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_105 = models.TextField(null=True, blank=True)
    google_civic_election_id_105 = models.PositiveIntegerField(null=True)
    stance_about_candidate_105 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_106 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_106 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_106 = models.TextField(null=True, blank=True)
    google_civic_election_id_106 = models.PositiveIntegerField(null=True)
    stance_about_candidate_106 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_107 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_107 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_107 = models.TextField(null=True, blank=True)
    google_civic_election_id_107 = models.PositiveIntegerField(null=True)
    stance_about_candidate_107 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_108 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_108 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_108 = models.TextField(null=True, blank=True)
    google_civic_election_id_108 = models.PositiveIntegerField(null=True)
    stance_about_candidate_108 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_109 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_109 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_109 = models.TextField(null=True, blank=True)
    google_civic_election_id_109 = models.PositiveIntegerField(null=True)
    stance_about_candidate_109 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_110 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_110 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_110 = models.TextField(null=True, blank=True)
    google_civic_election_id_110 = models.PositiveIntegerField(null=True)
    stance_about_candidate_110 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_111 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_111 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_111 = models.TextField(null=True, blank=True)
    google_civic_election_id_111 = models.PositiveIntegerField(null=True)
    stance_about_candidate_111 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_112 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_112 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_112 = models.TextField(null=True, blank=True)
    google_civic_election_id_112 = models.PositiveIntegerField(null=True)
    stance_about_candidate_112 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_113 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_113 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_113 = models.TextField(null=True, blank=True)
    google_civic_election_id_113 = models.PositiveIntegerField(null=True)
    stance_about_candidate_113 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_114 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_114 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_114 = models.TextField(null=True, blank=True)
    google_civic_election_id_114 = models.PositiveIntegerField(null=True)
    stance_about_candidate_114 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_115 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_115 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_115 = models.TextField(null=True, blank=True)
    google_civic_election_id_115 = models.PositiveIntegerField(null=True)
    stance_about_candidate_115 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_116 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_116 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_116 = models.TextField(null=True, blank=True)
    google_civic_election_id_116 = models.PositiveIntegerField(null=True)
    stance_about_candidate_116 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_117 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_117 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_117 = models.TextField(null=True, blank=True)
    google_civic_election_id_117 = models.PositiveIntegerField(null=True)
    stance_about_candidate_117 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_118 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_118 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_118 = models.TextField(null=True, blank=True)
    google_civic_election_id_118 = models.PositiveIntegerField(null=True)
    stance_about_candidate_118 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_119 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_119 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_119 = models.TextField(null=True, blank=True)
    google_civic_election_id_119 = models.PositiveIntegerField(null=True)
    stance_about_candidate_119 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_120 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_120 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_120 = models.TextField(null=True, blank=True)
    google_civic_election_id_120 = models.PositiveIntegerField(null=True)
    stance_about_candidate_120 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_121 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_121 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_121 = models.TextField(null=True, blank=True)
    google_civic_election_id_121 = models.PositiveIntegerField(null=True)
    stance_about_candidate_121 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_122 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_122 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_122 = models.TextField(null=True, blank=True)
    google_civic_election_id_122 = models.PositiveIntegerField(null=True)
    stance_about_candidate_122 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_123 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_123 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_123 = models.TextField(null=True, blank=True)
    google_civic_election_id_123 = models.PositiveIntegerField(null=True)
    stance_about_candidate_123 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_124 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_124 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_124 = models.TextField(null=True, blank=True)
    google_civic_election_id_124 = models.PositiveIntegerField(null=True)
    stance_about_candidate_124 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_125 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_125 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_125 = models.TextField(null=True, blank=True)
    google_civic_election_id_125 = models.PositiveIntegerField(null=True)
    stance_about_candidate_125 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_126 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_126 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_126 = models.TextField(null=True, blank=True)
    google_civic_election_id_126 = models.PositiveIntegerField(null=True)
    stance_about_candidate_126 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_127 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_127 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_127 = models.TextField(null=True, blank=True)
    google_civic_election_id_127 = models.PositiveIntegerField(null=True)
    stance_about_candidate_127 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_128 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_128 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_128 = models.TextField(null=True, blank=True)
    google_civic_election_id_128 = models.PositiveIntegerField(null=True)
    stance_about_candidate_128 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_129 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_129 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_129 = models.TextField(null=True, blank=True)
    google_civic_election_id_129 = models.PositiveIntegerField(null=True)
    stance_about_candidate_129 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_130 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_130 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_130 = models.TextField(null=True, blank=True)
    google_civic_election_id_130 = models.PositiveIntegerField(null=True)
    stance_about_candidate_130 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_131 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_131 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_131 = models.TextField(null=True, blank=True)
    google_civic_election_id_131 = models.PositiveIntegerField(null=True)
    stance_about_candidate_131 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_132 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_132 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_132 = models.TextField(null=True, blank=True)
    google_civic_election_id_132 = models.PositiveIntegerField(null=True)
    stance_about_candidate_132 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_133 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_133 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_133 = models.TextField(null=True, blank=True)
    google_civic_election_id_133 = models.PositiveIntegerField(null=True)
    stance_about_candidate_133 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_134 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_134 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_134 = models.TextField(null=True, blank=True)
    google_civic_election_id_134 = models.PositiveIntegerField(null=True)
    stance_about_candidate_134 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_135 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_135 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_135 = models.TextField(null=True, blank=True)
    google_civic_election_id_135 = models.PositiveIntegerField(null=True)
    stance_about_candidate_135 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_136 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_136 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_136 = models.TextField(null=True, blank=True)
    google_civic_election_id_136 = models.PositiveIntegerField(null=True)
    stance_about_candidate_136 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_137 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_137 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_137 = models.TextField(null=True, blank=True)
    google_civic_election_id_137 = models.PositiveIntegerField(null=True)
    stance_about_candidate_137 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_138 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_138 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_138 = models.TextField(null=True, blank=True)
    google_civic_election_id_138 = models.PositiveIntegerField(null=True)
    stance_about_candidate_138 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_139 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_139 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_139 = models.TextField(null=True, blank=True)
    google_civic_election_id_139 = models.PositiveIntegerField(null=True)
    stance_about_candidate_139 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_140 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_140 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_140 = models.TextField(null=True, blank=True)
    google_civic_election_id_140 = models.PositiveIntegerField(null=True)
    stance_about_candidate_140 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_141 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_141 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_141 = models.TextField(null=True, blank=True)
    google_civic_election_id_141 = models.PositiveIntegerField(null=True)
    stance_about_candidate_141 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_142 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_142 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_142 = models.TextField(null=True, blank=True)
    google_civic_election_id_142 = models.PositiveIntegerField(null=True)
    stance_about_candidate_142 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_143 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_143 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_143 = models.TextField(null=True, blank=True)
    google_civic_election_id_143 = models.PositiveIntegerField(null=True)
    stance_about_candidate_143 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_144 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_144 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_144 = models.TextField(null=True, blank=True)
    google_civic_election_id_144 = models.PositiveIntegerField(null=True)
    stance_about_candidate_144 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_145 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_145 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_145 = models.TextField(null=True, blank=True)
    google_civic_election_id_145 = models.PositiveIntegerField(null=True)
    stance_about_candidate_145 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_146 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_146 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_146 = models.TextField(null=True, blank=True)
    google_civic_election_id_146 = models.PositiveIntegerField(null=True)
    stance_about_candidate_146 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_147 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_147 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_147 = models.TextField(null=True, blank=True)
    google_civic_election_id_147 = models.PositiveIntegerField(null=True)
    stance_about_candidate_147 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_148 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_148 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_148 = models.TextField(null=True, blank=True)
    google_civic_election_id_148 = models.PositiveIntegerField(null=True)
    stance_about_candidate_148 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_149 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_149 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_149 = models.TextField(null=True, blank=True)
    google_civic_election_id_149 = models.PositiveIntegerField(null=True)
    stance_about_candidate_149 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_150 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_150 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_150 = models.TextField(null=True, blank=True)
    google_civic_election_id_150 = models.PositiveIntegerField(null=True)
    stance_about_candidate_150 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_151 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_151 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_151 = models.TextField(null=True, blank=True)
    google_civic_election_id_151 = models.PositiveIntegerField(null=True)
    stance_about_candidate_151 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_152 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_152 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_152 = models.TextField(null=True, blank=True)
    google_civic_election_id_152 = models.PositiveIntegerField(null=True)
    stance_about_candidate_152 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_153 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_153 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_153 = models.TextField(null=True, blank=True)
    google_civic_election_id_153 = models.PositiveIntegerField(null=True)
    stance_about_candidate_153 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_154 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_154 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_154 = models.TextField(null=True, blank=True)
    google_civic_election_id_154 = models.PositiveIntegerField(null=True)
    stance_about_candidate_154 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_155 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_155 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_155 = models.TextField(null=True, blank=True)
    google_civic_election_id_155 = models.PositiveIntegerField(null=True)
    stance_about_candidate_155 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_156 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_156 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_156 = models.TextField(null=True, blank=True)
    google_civic_election_id_156 = models.PositiveIntegerField(null=True)
    stance_about_candidate_156 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_157 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_157 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_157 = models.TextField(null=True, blank=True)
    google_civic_election_id_157 = models.PositiveIntegerField(null=True)
    stance_about_candidate_157 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_158 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_158 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_158 = models.TextField(null=True, blank=True)
    google_civic_election_id_158 = models.PositiveIntegerField(null=True)
    stance_about_candidate_158 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_159 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_159 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_159 = models.TextField(null=True, blank=True)
    google_civic_election_id_159 = models.PositiveIntegerField(null=True)
    stance_about_candidate_159 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_160 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_160 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_160 = models.TextField(null=True, blank=True)
    google_civic_election_id_160 = models.PositiveIntegerField(null=True)
    stance_about_candidate_160 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_161 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_161 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_161 = models.TextField(null=True, blank=True)
    google_civic_election_id_161 = models.PositiveIntegerField(null=True)
    stance_about_candidate_161 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_162 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_162 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_162 = models.TextField(null=True, blank=True)
    google_civic_election_id_162 = models.PositiveIntegerField(null=True)
    stance_about_candidate_162 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_163 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_163 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_163 = models.TextField(null=True, blank=True)
    google_civic_election_id_163 = models.PositiveIntegerField(null=True)
    stance_about_candidate_163 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_164 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_164 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_164 = models.TextField(null=True, blank=True)
    google_civic_election_id_164 = models.PositiveIntegerField(null=True)
    stance_about_candidate_164 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_165 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_165 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_165 = models.TextField(null=True, blank=True)
    google_civic_election_id_165 = models.PositiveIntegerField(null=True)
    stance_about_candidate_165 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_166 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_166 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_166 = models.TextField(null=True, blank=True)
    google_civic_election_id_166 = models.PositiveIntegerField(null=True)
    stance_about_candidate_166 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_167 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_167 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_167 = models.TextField(null=True, blank=True)
    google_civic_election_id_167 = models.PositiveIntegerField(null=True)
    stance_about_candidate_167 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_168 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_168 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_168 = models.TextField(null=True, blank=True)
    google_civic_election_id_168 = models.PositiveIntegerField(null=True)
    stance_about_candidate_168 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_169 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_169 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_169 = models.TextField(null=True, blank=True)
    google_civic_election_id_169 = models.PositiveIntegerField(null=True)
    stance_about_candidate_169 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_170 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_170 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_170 = models.TextField(null=True, blank=True)
    google_civic_election_id_170 = models.PositiveIntegerField(null=True)
    stance_about_candidate_170 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_171 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_171 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_171 = models.TextField(null=True, blank=True)
    google_civic_election_id_171 = models.PositiveIntegerField(null=True)
    stance_about_candidate_171 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_172 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_172 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_172 = models.TextField(null=True, blank=True)
    google_civic_election_id_172 = models.PositiveIntegerField(null=True)
    stance_about_candidate_172 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_173 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_173 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_173 = models.TextField(null=True, blank=True)
    google_civic_election_id_173 = models.PositiveIntegerField(null=True)
    stance_about_candidate_173 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_174 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_174 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_174 = models.TextField(null=True, blank=True)
    google_civic_election_id_174 = models.PositiveIntegerField(null=True)
    stance_about_candidate_174 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_175 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_175 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_175 = models.TextField(null=True, blank=True)
    google_civic_election_id_175 = models.PositiveIntegerField(null=True)
    stance_about_candidate_175 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_176 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_176 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_176 = models.TextField(null=True, blank=True)
    google_civic_election_id_176 = models.PositiveIntegerField(null=True)
    stance_about_candidate_176 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_177 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_177 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_177 = models.TextField(null=True, blank=True)
    google_civic_election_id_177 = models.PositiveIntegerField(null=True)
    stance_about_candidate_177 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_178 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_178 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_178 = models.TextField(null=True, blank=True)
    google_civic_election_id_178 = models.PositiveIntegerField(null=True)
    stance_about_candidate_178 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_179 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_179 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_179 = models.TextField(null=True, blank=True)
    google_civic_election_id_179 = models.PositiveIntegerField(null=True)
    stance_about_candidate_179 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_180 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_180 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_180 = models.TextField(null=True, blank=True)
    google_civic_election_id_180 = models.PositiveIntegerField(null=True)
    stance_about_candidate_180 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_181 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_181 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_181 = models.TextField(null=True, blank=True)
    google_civic_election_id_181 = models.PositiveIntegerField(null=True)
    stance_about_candidate_181 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_182 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_182 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_182 = models.TextField(null=True, blank=True)
    google_civic_election_id_182 = models.PositiveIntegerField(null=True)
    stance_about_candidate_182 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_183 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_183 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_183 = models.TextField(null=True, blank=True)
    google_civic_election_id_183 = models.PositiveIntegerField(null=True)
    stance_about_candidate_183 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_184 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_184 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_184 = models.TextField(null=True, blank=True)
    google_civic_election_id_184 = models.PositiveIntegerField(null=True)
    stance_about_candidate_184 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_185 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_185 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_185 = models.TextField(null=True, blank=True)
    google_civic_election_id_185 = models.PositiveIntegerField(null=True)
    stance_about_candidate_185 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_186 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_186 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_186 = models.TextField(null=True, blank=True)
    google_civic_election_id_186 = models.PositiveIntegerField(null=True)
    stance_about_candidate_186 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_187 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_187 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_187 = models.TextField(null=True, blank=True)
    google_civic_election_id_187 = models.PositiveIntegerField(null=True)
    stance_about_candidate_187 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_188 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_188 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_188 = models.TextField(null=True, blank=True)
    google_civic_election_id_188 = models.PositiveIntegerField(null=True)
    stance_about_candidate_188 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_189 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_189 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_189 = models.TextField(null=True, blank=True)
    google_civic_election_id_189 = models.PositiveIntegerField(null=True)
    stance_about_candidate_189 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_190 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_190 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_190 = models.TextField(null=True, blank=True)
    google_civic_election_id_190 = models.PositiveIntegerField(null=True)
    stance_about_candidate_190 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_191 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_191 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_191 = models.TextField(null=True, blank=True)
    google_civic_election_id_191 = models.PositiveIntegerField(null=True)
    stance_about_candidate_191 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_192 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_192 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_192 = models.TextField(null=True, blank=True)
    google_civic_election_id_192 = models.PositiveIntegerField(null=True)
    stance_about_candidate_192 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_193 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_193 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_193 = models.TextField(null=True, blank=True)
    google_civic_election_id_193 = models.PositiveIntegerField(null=True)
    stance_about_candidate_193 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_194 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_194 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_194 = models.TextField(null=True, blank=True)
    google_civic_election_id_194 = models.PositiveIntegerField(null=True)
    stance_about_candidate_194 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_195 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_195 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_195 = models.TextField(null=True, blank=True)
    google_civic_election_id_195 = models.PositiveIntegerField(null=True)
    stance_about_candidate_195 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_196 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_196 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_196 = models.TextField(null=True, blank=True)
    google_civic_election_id_196 = models.PositiveIntegerField(null=True)
    stance_about_candidate_196 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_197 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_197 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_197 = models.TextField(null=True, blank=True)
    google_civic_election_id_197 = models.PositiveIntegerField(null=True)
    stance_about_candidate_197 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_198 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_198 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_198 = models.TextField(null=True, blank=True)
    google_civic_election_id_198 = models.PositiveIntegerField(null=True)
    stance_about_candidate_198 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_199 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_199 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_199 = models.TextField(null=True, blank=True)
    google_civic_election_id_199 = models.PositiveIntegerField(null=True)
    stance_about_candidate_199 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    
    candidate_name_200 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_200 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_200 = models.TextField(null=True, blank=True)
    google_civic_election_id_200 = models.PositiveIntegerField(null=True)
    stance_about_candidate_200 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_201 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_201 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_201 = models.TextField(null=True, blank=True)
    google_civic_election_id_201 = models.PositiveIntegerField(null=True)
    stance_about_candidate_201 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_202 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_202 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_202 = models.TextField(null=True, blank=True)
    google_civic_election_id_202 = models.PositiveIntegerField(null=True)
    stance_about_candidate_202 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_203 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_203 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_203 = models.TextField(null=True, blank=True)
    google_civic_election_id_203 = models.PositiveIntegerField(null=True)
    stance_about_candidate_203 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_204 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_204 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_204 = models.TextField(null=True, blank=True)
    google_civic_election_id_204 = models.PositiveIntegerField(null=True)
    stance_about_candidate_204 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_205 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_205 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_205 = models.TextField(null=True, blank=True)
    google_civic_election_id_205 = models.PositiveIntegerField(null=True)
    stance_about_candidate_205 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_206 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_206 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_206 = models.TextField(null=True, blank=True)
    google_civic_election_id_206 = models.PositiveIntegerField(null=True)
    stance_about_candidate_206 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_207 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_207 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_207 = models.TextField(null=True, blank=True)
    google_civic_election_id_207 = models.PositiveIntegerField(null=True)
    stance_about_candidate_207 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_208 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_208 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_208 = models.TextField(null=True, blank=True)
    google_civic_election_id_208 = models.PositiveIntegerField(null=True)
    stance_about_candidate_208 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_209 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_209 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_209 = models.TextField(null=True, blank=True)
    google_civic_election_id_209 = models.PositiveIntegerField(null=True)
    stance_about_candidate_209 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_210 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_210 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_210 = models.TextField(null=True, blank=True)
    google_civic_election_id_210 = models.PositiveIntegerField(null=True)
    stance_about_candidate_210 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_211 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_211 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_211 = models.TextField(null=True, blank=True)
    google_civic_election_id_211 = models.PositiveIntegerField(null=True)
    stance_about_candidate_211 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_212 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_212 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_212 = models.TextField(null=True, blank=True)
    google_civic_election_id_212 = models.PositiveIntegerField(null=True)
    stance_about_candidate_212 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_213 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_213 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_213 = models.TextField(null=True, blank=True)
    google_civic_election_id_213 = models.PositiveIntegerField(null=True)
    stance_about_candidate_213 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_214 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_214 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_214 = models.TextField(null=True, blank=True)
    google_civic_election_id_214 = models.PositiveIntegerField(null=True)
    stance_about_candidate_214 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_215 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_215 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_215 = models.TextField(null=True, blank=True)
    google_civic_election_id_215 = models.PositiveIntegerField(null=True)
    stance_about_candidate_215 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_216 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_216 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_216 = models.TextField(null=True, blank=True)
    google_civic_election_id_216 = models.PositiveIntegerField(null=True)
    stance_about_candidate_216 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_217 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_217 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_217 = models.TextField(null=True, blank=True)
    google_civic_election_id_217 = models.PositiveIntegerField(null=True)
    stance_about_candidate_217 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_218 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_218 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_218 = models.TextField(null=True, blank=True)
    google_civic_election_id_218 = models.PositiveIntegerField(null=True)
    stance_about_candidate_218 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_219 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_219 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_219 = models.TextField(null=True, blank=True)
    google_civic_election_id_219 = models.PositiveIntegerField(null=True)
    stance_about_candidate_219 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_220 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_220 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_220 = models.TextField(null=True, blank=True)
    google_civic_election_id_220 = models.PositiveIntegerField(null=True)
    stance_about_candidate_220 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_221 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_221 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_221 = models.TextField(null=True, blank=True)
    google_civic_election_id_221 = models.PositiveIntegerField(null=True)
    stance_about_candidate_221 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_222 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_222 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_222 = models.TextField(null=True, blank=True)
    google_civic_election_id_222 = models.PositiveIntegerField(null=True)
    stance_about_candidate_222 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_223 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_223 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_223 = models.TextField(null=True, blank=True)
    google_civic_election_id_223 = models.PositiveIntegerField(null=True)
    stance_about_candidate_223 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_224 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_224 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_224 = models.TextField(null=True, blank=True)
    google_civic_election_id_224 = models.PositiveIntegerField(null=True)
    stance_about_candidate_224 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_225 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_225 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_225 = models.TextField(null=True, blank=True)
    google_civic_election_id_225 = models.PositiveIntegerField(null=True)
    stance_about_candidate_225 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_226 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_226 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_226 = models.TextField(null=True, blank=True)
    google_civic_election_id_226 = models.PositiveIntegerField(null=True)
    stance_about_candidate_226 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_227 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_227 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_227 = models.TextField(null=True, blank=True)
    google_civic_election_id_227 = models.PositiveIntegerField(null=True)
    stance_about_candidate_227 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_228 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_228 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_228 = models.TextField(null=True, blank=True)
    google_civic_election_id_228 = models.PositiveIntegerField(null=True)
    stance_about_candidate_228 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_229 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_229 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_229 = models.TextField(null=True, blank=True)
    google_civic_election_id_229 = models.PositiveIntegerField(null=True)
    stance_about_candidate_229 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_230 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_230 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_230 = models.TextField(null=True, blank=True)
    google_civic_election_id_230 = models.PositiveIntegerField(null=True)
    stance_about_candidate_230 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_231 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_231 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_231 = models.TextField(null=True, blank=True)
    google_civic_election_id_231 = models.PositiveIntegerField(null=True)
    stance_about_candidate_231 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_232 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_232 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_232 = models.TextField(null=True, blank=True)
    google_civic_election_id_232 = models.PositiveIntegerField(null=True)
    stance_about_candidate_232 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_233 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_233 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_233 = models.TextField(null=True, blank=True)
    google_civic_election_id_233 = models.PositiveIntegerField(null=True)
    stance_about_candidate_233 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_234 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_234 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_234 = models.TextField(null=True, blank=True)
    google_civic_election_id_234 = models.PositiveIntegerField(null=True)
    stance_about_candidate_234 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_235 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_235 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_235 = models.TextField(null=True, blank=True)
    google_civic_election_id_235 = models.PositiveIntegerField(null=True)
    stance_about_candidate_235 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_236 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_236 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_236 = models.TextField(null=True, blank=True)
    google_civic_election_id_236 = models.PositiveIntegerField(null=True)
    stance_about_candidate_236 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_237 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_237 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_237 = models.TextField(null=True, blank=True)
    google_civic_election_id_237 = models.PositiveIntegerField(null=True)
    stance_about_candidate_237 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_238 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_238 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_238 = models.TextField(null=True, blank=True)
    google_civic_election_id_238 = models.PositiveIntegerField(null=True)
    stance_about_candidate_238 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_239 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_239 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_239 = models.TextField(null=True, blank=True)
    google_civic_election_id_239 = models.PositiveIntegerField(null=True)
    stance_about_candidate_239 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_240 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_240 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_240 = models.TextField(null=True, blank=True)
    google_civic_election_id_240 = models.PositiveIntegerField(null=True)
    stance_about_candidate_240 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_241 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_241 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_241 = models.TextField(null=True, blank=True)
    google_civic_election_id_241 = models.PositiveIntegerField(null=True)
    stance_about_candidate_241 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_242 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_242 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_242 = models.TextField(null=True, blank=True)
    google_civic_election_id_242 = models.PositiveIntegerField(null=True)
    stance_about_candidate_242 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_243 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_243 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_243 = models.TextField(null=True, blank=True)
    google_civic_election_id_243 = models.PositiveIntegerField(null=True)
    stance_about_candidate_243 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_244 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_244 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_244 = models.TextField(null=True, blank=True)
    google_civic_election_id_244 = models.PositiveIntegerField(null=True)
    stance_about_candidate_244 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_245 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_245 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_245 = models.TextField(null=True, blank=True)
    google_civic_election_id_245 = models.PositiveIntegerField(null=True)
    stance_about_candidate_245 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_246 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_246 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_246 = models.TextField(null=True, blank=True)
    google_civic_election_id_246 = models.PositiveIntegerField(null=True)
    stance_about_candidate_246 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_247 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_247 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_247 = models.TextField(null=True, blank=True)
    google_civic_election_id_247 = models.PositiveIntegerField(null=True)
    stance_about_candidate_247 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_248 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_248 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_248 = models.TextField(null=True, blank=True)
    google_civic_election_id_248 = models.PositiveIntegerField(null=True)
    stance_about_candidate_248 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_249 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_249 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_249 = models.TextField(null=True, blank=True)
    google_civic_election_id_249 = models.PositiveIntegerField(null=True)
    stance_about_candidate_249 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_250 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_250 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_250 = models.TextField(null=True, blank=True)
    google_civic_election_id_250 = models.PositiveIntegerField(null=True)
    stance_about_candidate_250 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_251 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_251 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_251 = models.TextField(null=True, blank=True)
    google_civic_election_id_251 = models.PositiveIntegerField(null=True)
    stance_about_candidate_251 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_252 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_252 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_252 = models.TextField(null=True, blank=True)
    google_civic_election_id_252 = models.PositiveIntegerField(null=True)
    stance_about_candidate_252 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_253 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_253 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_253 = models.TextField(null=True, blank=True)
    google_civic_election_id_253 = models.PositiveIntegerField(null=True)
    stance_about_candidate_253 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_254 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_254 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_254 = models.TextField(null=True, blank=True)
    google_civic_election_id_254 = models.PositiveIntegerField(null=True)
    stance_about_candidate_254 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_255 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_255 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_255 = models.TextField(null=True, blank=True)
    google_civic_election_id_255 = models.PositiveIntegerField(null=True)
    stance_about_candidate_255 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_256 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_256 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_256 = models.TextField(null=True, blank=True)
    google_civic_election_id_256 = models.PositiveIntegerField(null=True)
    stance_about_candidate_256 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_257 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_257 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_257 = models.TextField(null=True, blank=True)
    google_civic_election_id_257 = models.PositiveIntegerField(null=True)
    stance_about_candidate_257 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_258 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_258 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_258 = models.TextField(null=True, blank=True)
    google_civic_election_id_258 = models.PositiveIntegerField(null=True)
    stance_about_candidate_258 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_259 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_259 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_259 = models.TextField(null=True, blank=True)
    google_civic_election_id_259 = models.PositiveIntegerField(null=True)
    stance_about_candidate_259 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_260 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_260 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_260 = models.TextField(null=True, blank=True)
    google_civic_election_id_260 = models.PositiveIntegerField(null=True)
    stance_about_candidate_260 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_261 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_261 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_261 = models.TextField(null=True, blank=True)
    google_civic_election_id_261 = models.PositiveIntegerField(null=True)
    stance_about_candidate_261 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_262 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_262 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_262 = models.TextField(null=True, blank=True)
    google_civic_election_id_262 = models.PositiveIntegerField(null=True)
    stance_about_candidate_262 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_263 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_263 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_263 = models.TextField(null=True, blank=True)
    google_civic_election_id_263 = models.PositiveIntegerField(null=True)
    stance_about_candidate_263 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_264 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_264 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_264 = models.TextField(null=True, blank=True)
    google_civic_election_id_264 = models.PositiveIntegerField(null=True)
    stance_about_candidate_264 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_265 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_265 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_265 = models.TextField(null=True, blank=True)
    google_civic_election_id_265 = models.PositiveIntegerField(null=True)
    stance_about_candidate_265 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_266 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_266 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_266 = models.TextField(null=True, blank=True)
    google_civic_election_id_266 = models.PositiveIntegerField(null=True)
    stance_about_candidate_266 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_267 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_267 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_267 = models.TextField(null=True, blank=True)
    google_civic_election_id_267 = models.PositiveIntegerField(null=True)
    stance_about_candidate_267 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_268 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_268 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_268 = models.TextField(null=True, blank=True)
    google_civic_election_id_268 = models.PositiveIntegerField(null=True)
    stance_about_candidate_268 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_269 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_269 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_269 = models.TextField(null=True, blank=True)
    google_civic_election_id_269 = models.PositiveIntegerField(null=True)
    stance_about_candidate_269 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_270 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_270 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_270 = models.TextField(null=True, blank=True)
    google_civic_election_id_270 = models.PositiveIntegerField(null=True)
    stance_about_candidate_270 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_271 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_271 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_271 = models.TextField(null=True, blank=True)
    google_civic_election_id_271 = models.PositiveIntegerField(null=True)
    stance_about_candidate_271 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_272 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_272 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_272 = models.TextField(null=True, blank=True)
    google_civic_election_id_272 = models.PositiveIntegerField(null=True)
    stance_about_candidate_272 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_273 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_273 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_273 = models.TextField(null=True, blank=True)
    google_civic_election_id_273 = models.PositiveIntegerField(null=True)
    stance_about_candidate_273 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_274 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_274 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_274 = models.TextField(null=True, blank=True)
    google_civic_election_id_274 = models.PositiveIntegerField(null=True)
    stance_about_candidate_274 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_275 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_275 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_275 = models.TextField(null=True, blank=True)
    google_civic_election_id_275 = models.PositiveIntegerField(null=True)
    stance_about_candidate_275 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_276 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_276 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_276 = models.TextField(null=True, blank=True)
    google_civic_election_id_276 = models.PositiveIntegerField(null=True)
    stance_about_candidate_276 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_277 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_277 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_277 = models.TextField(null=True, blank=True)
    google_civic_election_id_277 = models.PositiveIntegerField(null=True)
    stance_about_candidate_277 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_278 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_278 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_278 = models.TextField(null=True, blank=True)
    google_civic_election_id_278 = models.PositiveIntegerField(null=True)
    stance_about_candidate_278 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_279 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_279 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_279 = models.TextField(null=True, blank=True)
    google_civic_election_id_279 = models.PositiveIntegerField(null=True)
    stance_about_candidate_279 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_280 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_280 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_280 = models.TextField(null=True, blank=True)
    google_civic_election_id_280 = models.PositiveIntegerField(null=True)
    stance_about_candidate_280 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_281 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_281 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_281 = models.TextField(null=True, blank=True)
    google_civic_election_id_281 = models.PositiveIntegerField(null=True)
    stance_about_candidate_281 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_282 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_282 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_282 = models.TextField(null=True, blank=True)
    google_civic_election_id_282 = models.PositiveIntegerField(null=True)
    stance_about_candidate_282 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_283 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_283 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_283 = models.TextField(null=True, blank=True)
    google_civic_election_id_283 = models.PositiveIntegerField(null=True)
    stance_about_candidate_283 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_284 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_284 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_284 = models.TextField(null=True, blank=True)
    google_civic_election_id_284 = models.PositiveIntegerField(null=True)
    stance_about_candidate_284 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_285 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_285 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_285 = models.TextField(null=True, blank=True)
    google_civic_election_id_285 = models.PositiveIntegerField(null=True)
    stance_about_candidate_285 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_286 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_286 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_286 = models.TextField(null=True, blank=True)
    google_civic_election_id_286 = models.PositiveIntegerField(null=True)
    stance_about_candidate_286 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_287 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_287 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_287 = models.TextField(null=True, blank=True)
    google_civic_election_id_287 = models.PositiveIntegerField(null=True)
    stance_about_candidate_287 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_288 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_288 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_288 = models.TextField(null=True, blank=True)
    google_civic_election_id_288 = models.PositiveIntegerField(null=True)
    stance_about_candidate_288 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_289 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_289 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_289 = models.TextField(null=True, blank=True)
    google_civic_election_id_289 = models.PositiveIntegerField(null=True)
    stance_about_candidate_289 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_290 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_290 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_290 = models.TextField(null=True, blank=True)
    google_civic_election_id_290 = models.PositiveIntegerField(null=True)
    stance_about_candidate_290 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_291 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_291 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_291 = models.TextField(null=True, blank=True)
    google_civic_election_id_291 = models.PositiveIntegerField(null=True)
    stance_about_candidate_291 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_292 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_292 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_292 = models.TextField(null=True, blank=True)
    google_civic_election_id_292 = models.PositiveIntegerField(null=True)
    stance_about_candidate_292 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_293 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_293 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_293 = models.TextField(null=True, blank=True)
    google_civic_election_id_293 = models.PositiveIntegerField(null=True)
    stance_about_candidate_293 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_294 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_294 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_294 = models.TextField(null=True, blank=True)
    google_civic_election_id_294 = models.PositiveIntegerField(null=True)
    stance_about_candidate_294 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_295 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_295 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_295 = models.TextField(null=True, blank=True)
    google_civic_election_id_295 = models.PositiveIntegerField(null=True)
    stance_about_candidate_295 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_296 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_296 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_296 = models.TextField(null=True, blank=True)
    google_civic_election_id_296 = models.PositiveIntegerField(null=True)
    stance_about_candidate_296 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_297 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_297 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_297 = models.TextField(null=True, blank=True)
    google_civic_election_id_297 = models.PositiveIntegerField(null=True)
    stance_about_candidate_297 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_298 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_298 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_298 = models.TextField(null=True, blank=True)
    google_civic_election_id_298 = models.PositiveIntegerField(null=True)
    stance_about_candidate_298 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_299 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_299 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_299 = models.TextField(null=True, blank=True)
    google_civic_election_id_299 = models.PositiveIntegerField(null=True)
    stance_about_candidate_299 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)

    candidate_name_300 = models.CharField(max_length=255, null=True, unique=False)
    candidate_we_vote_id_300 = models.CharField(max_length=255, null=True, unique=False)
    comment_about_candidate_300 = models.TextField(null=True, blank=True)
    google_civic_election_id_300 = models.PositiveIntegerField(null=True)
    stance_about_candidate_300 = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    # This is the end
