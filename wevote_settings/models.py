# wevote_settings/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_saved_exception
import string
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, generate_random_string, positive_value_exists


SUGGESTED_VOTER_GUIDE_FROM_PRIOR = 'SUGGESTED_VOTER_GUIDE_FROM_PRIOR'
RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS = 'RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS'
RETRIEVE_POSSIBLE_GOOGLE_LINKS = 'RETRIEVE_POSSIBLE_GOOGLE_LINKS'
RETRIEVE_POSSIBLE_TWITTER_HANDLES = 'RETRIEVE_POSSIBLE_TWITTER_HANDLES'
STOP_BULK_SEARCH_TWITTER_LINK_POSSIBILITY = 'STOP_BULK_SEARCH_TWITTER_LINK_POSSIBILITY'

KIND_OF_ACTION_CHOICES = (
    (RETRIEVE_POSSIBLE_FACEBOOK_PHOTOS, 'Retrieve possible Facebook photos'),
    (RETRIEVE_POSSIBLE_GOOGLE_LINKS, 'Retrieve possible google links'),
    (RETRIEVE_POSSIBLE_TWITTER_HANDLES, 'Retrieve possible twitter handles'),
    (STOP_BULK_SEARCH_TWITTER_LINK_POSSIBILITY, 'Stop search for Bulk twitter links'),
)

logger = wevote_functions.admin.get_logger(__name__)


class WeVoteSetting(models.Model):
    """
    Settings needed for the operation of this site
    """
    name = models.CharField(verbose_name='setting name', blank=True, null=True, max_length=255)

    # We store in the settings database values of many different kind of data types
    STRING = 'S'
    INTEGER = 'I'
    BOOLEAN = 'B'
    VALUE_TYPE_CHOICES = (
        (STRING, 'String'),
        (INTEGER, 'Integer'),
        (BOOLEAN, 'Boolean'),
    )
    value_type = models.CharField("value_type", max_length=1, choices=VALUE_TYPE_CHOICES, default=STRING)

    # Only one of these fields is filled for each entry
    string_value = models.CharField(verbose_name='string value', max_length=255, null=True, blank=True)
    integer_value = models.BigIntegerField(verbose_name='integer value', null=True, blank=True)
    boolean_value = models.BooleanField(verbose_name='boolean value', blank=True, default=False)


class WeVoteSettingsManager(models.Model):
    """
    Manage all of the site settings
    """
    def fetch_setting(self, setting_name):
        setting_name = setting_name.strip()
        try:
            if setting_name != '':
                we_vote_setting = WeVoteSetting.objects.get(name=setting_name)
                if we_vote_setting.value_type == WeVoteSetting.BOOLEAN:
                    return we_vote_setting.boolean_value
                elif we_vote_setting.value_type == WeVoteSetting.INTEGER:
                    return we_vote_setting.integer_value
                elif we_vote_setting.value_type == WeVoteSetting.STRING:
                    return we_vote_setting.string_value
        except WeVoteSetting.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            return ''
        except WeVoteSetting.DoesNotExist:
            return ''
        except Exception as e:
            print("Settings exception: ", e)
            return ''

        return ''

    def save_setting(self, setting_name, setting_value, value_type=None):
        accepted_value_types = ['bool', 'int', 'str']

        if value_type is None:
            if type(setting_value).__name__ == 'bool':
                value_type = WeVoteSetting.BOOLEAN
            elif type(setting_value).__name__ == 'int':
                value_type = WeVoteSetting.INTEGER
            elif type(setting_value).__name__ == 'str':
                value_type = WeVoteSetting.STRING
            elif type(setting_value).__name__ == 'list':
                logger.info("setting is a list. To be developed")
                value_type = WeVoteSetting.STRING
            else:
                value_type = WeVoteSetting.STRING
        elif value_type not in accepted_value_types:
            # Not a recognized value_type, save as a str
            value_type = WeVoteSetting.STRING

        # Does this setting already exist?
        we_vote_setting = None
        we_vote_setting_id = 0
        we_vote_setting_exists = False
        we_vote_setting_does_not_exist = False
        try:
            we_vote_setting = WeVoteSetting.objects.get(name=setting_name)
            we_vote_setting_exists = True
        except WeVoteSetting.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except WeVoteSetting.DoesNotExist:
            we_vote_setting_does_not_exist = True

        we_vote_setting_manager = WeVoteSettingsManager()
        if we_vote_setting_exists:
            # Update this position with new values
            try:
                we_vote_setting.value_type = value_type
                we_vote_setting = we_vote_setting_manager.set_setting_value_by_type(
                    we_vote_setting, setting_value, value_type)
                we_vote_setting.save()
                we_vote_setting_id = we_vote_setting.id
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
        elif we_vote_setting_does_not_exist:
            try:
                # Create new
                we_vote_setting = WeVoteSetting(
                    value_type=value_type,
                    name=setting_name,
                )
                we_vote_setting = we_vote_setting_manager.set_setting_value_by_type(
                    we_vote_setting, setting_value, value_type)
                we_vote_setting.save()
                we_vote_setting_id = we_vote_setting.id
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)

        results = {
            'success':                  True if we_vote_setting_id else False,
            'we_vote_setting':          we_vote_setting,
        }
        return results

    def set_setting_value_by_type(self, we_vote_setting, setting_value, setting_type):
        if setting_type == WeVoteSetting.BOOLEAN:
            we_vote_setting.boolean_value = setting_value
            we_vote_setting.integer_value = None
            we_vote_setting.string_value = None
        elif setting_type == WeVoteSetting.INTEGER:
            we_vote_setting.boolean_value = False
            we_vote_setting.integer_value = setting_value
            we_vote_setting.string_value = None
        else:  # All other kinds of settings are strings
            we_vote_setting.boolean_value = False
            we_vote_setting.integer_value = None
            we_vote_setting.string_value = setting_value
        return we_vote_setting

# site_unique_id_prefix
# we_vote_id_last_org_integer
# we_vote_id_last_position_integer


def fetch_site_unique_id_prefix():
    we_vote_settings_manager = WeVoteSettingsManager()
    site_unique_id_prefix = we_vote_settings_manager.fetch_setting('site_unique_id_prefix')

    if site_unique_id_prefix is '':
        safety_valve = 0
        # TODO Create table to keep collection of prefix's used by other sites
        site_unique_id_prefix_reserved = ['1r', 'yf']
        # Even though it reduced the number of unique prefixes, I don't want to rely on lowercase vs. uppercase
        #  in case the id ever gets converted to all upper case or lower case
        characters_in_random_string = string.ascii_lowercase + string.digits
        site_unique_id_prefix = generate_random_string(2, characters_in_random_string)
        while (site_unique_id_prefix in site_unique_id_prefix_reserved) and (safety_valve < 100):
            safety_valve += 1
            site_unique_id_prefix = generate_random_string(2, characters_in_random_string)
            # Break out when we have a unique site_unique_id_prefix
        we_vote_settings_manager.save_setting('site_unique_id_prefix', site_unique_id_prefix)
        # TODO Each We Vote site needs to keep a local copy of site_unique_id_prefix's that are in use, AND
        # TODO Each We Vote site also needs to publish site_unique_id_prefix's in use by that organization
    return site_unique_id_prefix


def fetch_next_we_vote_id_integer(we_vote_id_last_setting_name):
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_integer = we_vote_settings_manager.fetch_setting(we_vote_id_last_setting_name)
    we_vote_id_next_integer = convert_to_int(we_vote_id_last_integer)
    we_vote_id_next_integer += 1
    we_vote_settings_manager.save_setting(we_vote_id_last_setting_name, we_vote_id_next_integer)
    return we_vote_id_next_integer


def fetch_next_we_vote_id_ballot_returned_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_ballot_returned_integer')


def fetch_next_we_vote_id_org_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_org_integer')


def fetch_next_we_vote_id_position_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_position_integer')


def fetch_next_we_vote_id_candidate_campaign_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_candidate_campaign_integer')


def fetch_next_we_vote_id_contest_office_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_contest_office_integer')


def fetch_next_we_vote_id_elected_office_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_elected_office_integer')


def fetch_next_we_vote_id_elected_official_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_elected_official_integer')


def fetch_next_we_vote_id_contest_measure_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_contest_measure_integer')


def fetch_next_we_vote_id_email_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_email_integer')


def fetch_next_we_vote_id_issue_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_issue_integer')


def fetch_next_we_vote_id_measure_campaign_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_measure_campaign_integer')


def fetch_next_we_vote_id_pledge_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_pledge_integer')


def fetch_next_we_vote_id_politician_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_politician_integer')


def fetch_next_we_vote_id_polling_location_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_polling_location_integer')


def fetch_next_we_vote_id_quick_info_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_quick_info_integer')


def fetch_next_we_vote_id_quick_info_master_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_quick_info_master_integer')


def fetch_next_we_vote_id_sms_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_sms_integer')


def fetch_next_we_vote_id_voter_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_voter_integer')


def fetch_next_we_vote_id_voter_guide_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_last_voter_guide_integer')


def fetch_next_we_vote_id_electoral_district_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_electoral_district_integer')


def fetch_next_we_vote_id_party_integer():
    return fetch_next_we_vote_id_integer('we_vote_id_party_integer')


class RemoteRequestHistory(models.Model):
    """
    Keep a log of events when reaching out to Remote servers with requests
    """
    # The data and time we reached out to the Remote server
    datetime_of_action = models.DateTimeField(verbose_name='date and time of action', auto_now=True)
    # If a 'ballot' entry, store the election this is for
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)

    kind_of_action = models.CharField(verbose_name="kind of action to take", max_length=50,
                                      choices=KIND_OF_ACTION_CHOICES, null=True)
    candidate_campaign_we_vote_id = models.CharField(verbose_name="candidate we vote id", max_length=255, unique=False,
                                                     null=True)

    organization_we_vote_id = models.CharField(verbose_name="we vote id for the org owner", max_length=255,
                                               unique=False, null=True)
    number_of_results = models.PositiveIntegerField(verbose_name="number of results", null=True, default=0)
    status = models.CharField(verbose_name="Request status message", max_length=255, default="", null=True, blank=True)


class RemoteRequestHistoryManager(models.Model):

    def __unicode__(self):
        return "RemoteRequestHistoryManager"

    def create_remote_request_history_entry(self, kind_of_action, google_civic_election_id,
                                            candidate_campaign_we_vote_id='', organization_we_vote_id='',
                                            number_of_results=0, status=''):
        """
        Create a new entry for twitter link search request in the RemoteRequestHistory
        :param kind_of_action: 
        :param google_civic_election_id: 
        :param candidate_campaign_we_vote_id: 
        :param organization_we_vote_id: 
        :param number_of_results: 
        :param status: 
        :return: 
        """

        success = False
        create_status = ""
        remote_request_history_entry_created = False
        remote_request_history_entry = ''

        # save this entry
        try:
            remote_request_history_entry = RemoteRequestHistory.objects.create(
                kind_of_action=kind_of_action, google_civic_election_id=google_civic_election_id,
                candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                organization_we_vote_id=organization_we_vote_id, number_of_results=number_of_results,
                status=status)
            if remote_request_history_entry:
                success = True
                create_status += "REMOTE_REQUEST_HISTORY_ENTRY_CREATED"
                remote_request_history_entry_created = True
            else:
                success = False
                create_status += "CREATE_REMOTE_REQUEST_HISTORY_ENTRY_FAILED"
        except Exception as e:
            status += "REMOTE_REQUEST_HISTORY_ENTRY_ERROR"
            handle_record_not_saved_exception(e, logger=logger)

        results = {
            'success': success,
            'status': create_status,
            'remote_request_history_entry_created': remote_request_history_entry_created,
            'remote_request_history_entry': remote_request_history_entry,
        }
        return results

    def remote_request_history_entry_exists(self, kind_of_action, google_civic_election_id,
                                            candidate_campaign_we_vote_id='', organization_we_vote_id=''):
        success = False
        status = ""

        try:
            list_query = RemoteRequestHistory.objects.all()
            list_query = list_query.filter(kind_of_action__iexact=kind_of_action)
            list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(candidate_campaign_we_vote_id):
                list_query = list_query.filter(candidate_campaign_we_vote_id__iexact=candidate_campaign_we_vote_id)
            if positive_value_exists(organization_we_vote_id):
                list_query = list_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            list_query_count = list_query.count()
            if positive_value_exists(list_query_count):
                return True
        except Exception as e:
            status += "REMOTE_REQUEST_HISTORY_LIST_NOT_FOUND-EXCEPTION "

        return False

    def retrieve_remote_request_history_list(self, google_civic_election_id=0):
        success = False
        status = ""
        remote_request_history_list = []

        try:
            list_query = RemoteRequestHistory.objects.all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            remote_request_history_list = list(list_query)
            remote_request_history_list_found = True
            status += "REMOTE_REQUEST_HISTORY_LIST_FOUND "
        except Exception as e:
            remote_request_history_list_found = False
            status += "REMOTE_REQUEST_HISTORY_LIST_NOT_FOUND-EXCEPTION "

        results = {
            'success': success,
            'status': status,
            'remote_request_history_list': remote_request_history_list,
            'remote_request_history_list_found': remote_request_history_list_found,
        }
        return results
