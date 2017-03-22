# wevote_settings/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_saved_exception
import string
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, generate_random_string


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
    boolean_value = models.BooleanField(verbose_name='boolean value', blank=True)


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
        we_vote_setting = WeVoteSetting()
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


def fetch_next_we_vote_id_last_org_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_org_integer = we_vote_settings_manager.fetch_setting('we_vote_id_last_org_integer')
    we_vote_id_last_org_integer = convert_to_int(we_vote_id_last_org_integer)
    we_vote_id_last_org_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_org_integer', we_vote_id_last_org_integer)
    return we_vote_id_last_org_integer


def fetch_next_we_vote_id_last_position_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_position_integer = we_vote_settings_manager.fetch_setting('we_vote_id_last_position_integer')
    we_vote_id_last_position_integer = convert_to_int(we_vote_id_last_position_integer)
    we_vote_id_last_position_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_position_integer', we_vote_id_last_position_integer)
    return we_vote_id_last_position_integer


def fetch_next_we_vote_id_last_candidate_campaign_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_candidate_campaign_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_last_candidate_campaign_integer')
    we_vote_id_last_candidate_campaign_integer = convert_to_int(we_vote_id_last_candidate_campaign_integer)
    we_vote_id_last_candidate_campaign_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_candidate_campaign_integer',
                                          we_vote_id_last_candidate_campaign_integer)
    return we_vote_id_last_candidate_campaign_integer


def fetch_next_we_vote_id_last_contest_office_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_contest_office_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_last_contest_office_integer')
    we_vote_id_last_contest_office_integer = convert_to_int(we_vote_id_last_contest_office_integer)
    we_vote_id_last_contest_office_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_contest_office_integer',
                                          we_vote_id_last_contest_office_integer)
    return we_vote_id_last_contest_office_integer


def fetch_next_we_vote_id_last_contest_measure_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_contest_measure_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_last_contest_measure_integer')
    we_vote_id_last_contest_measure_integer = convert_to_int(we_vote_id_last_contest_measure_integer)
    we_vote_id_last_contest_measure_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_contest_measure_integer',
                                          we_vote_id_last_contest_measure_integer)
    return we_vote_id_last_contest_measure_integer


def fetch_next_we_vote_id_last_email_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_email_integer = we_vote_settings_manager.fetch_setting('we_vote_id_last_email_integer')
    we_vote_id_last_email_integer = convert_to_int(we_vote_id_last_email_integer)
    we_vote_id_last_email_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_email_integer',
                                          we_vote_id_last_email_integer)
    return we_vote_id_last_email_integer


def fetch_next_we_vote_id_last_measure_campaign_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_measure_campaign_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_last_measure_campaign_integer')
    we_vote_id_last_measure_campaign_integer = convert_to_int(we_vote_id_last_measure_campaign_integer)
    we_vote_id_last_measure_campaign_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_measure_campaign_integer',
                                          we_vote_id_last_measure_campaign_integer)
    return we_vote_id_last_measure_campaign_integer


def fetch_next_we_vote_id_last_politician_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_politician_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_last_politician_integer')
    we_vote_id_last_politician_integer = convert_to_int(we_vote_id_last_politician_integer)
    we_vote_id_last_politician_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_politician_integer',
                                          we_vote_id_last_politician_integer)
    return we_vote_id_last_politician_integer


def fetch_next_we_vote_id_last_polling_location_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_polling_location_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_last_polling_location_integer')
    we_vote_id_last_polling_location_integer = convert_to_int(we_vote_id_last_polling_location_integer)
    we_vote_id_last_polling_location_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_polling_location_integer',
                                          we_vote_id_last_polling_location_integer)
    return we_vote_id_last_polling_location_integer


def fetch_next_we_vote_id_last_quick_info_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_quick_info_integer = we_vote_settings_manager.fetch_setting('we_vote_id_last_quick_info_integer')
    we_vote_id_last_quick_info_integer = convert_to_int(we_vote_id_last_quick_info_integer)
    we_vote_id_last_quick_info_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_quick_info_integer', we_vote_id_last_quick_info_integer)
    return we_vote_id_last_quick_info_integer


def fetch_next_we_vote_id_last_quick_info_master_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_quick_info_master_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_last_quick_info_master_integer')
    we_vote_id_last_quick_info_master_integer = convert_to_int(we_vote_id_last_quick_info_master_integer)
    we_vote_id_last_quick_info_master_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_quick_info_master_integer',
                                          we_vote_id_last_quick_info_master_integer)
    return we_vote_id_last_quick_info_master_integer


def fetch_next_we_vote_id_last_voter_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_voter_integer = we_vote_settings_manager.fetch_setting('we_vote_id_last_voter_integer')
    we_vote_id_last_voter_integer = convert_to_int(we_vote_id_last_voter_integer)
    we_vote_id_last_voter_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_voter_integer', we_vote_id_last_voter_integer)
    return we_vote_id_last_voter_integer


# Related to voter guide
def fetch_next_we_vote_id_last_voter_guide_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_last_voter_guide_integer = we_vote_settings_manager.fetch_setting('we_vote_id_last_voter_guide_integer')
    we_vote_id_last_voter_guide_integer = convert_to_int(we_vote_id_last_voter_guide_integer)
    we_vote_id_last_voter_guide_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_last_voter_guide_integer', we_vote_id_last_voter_guide_integer)
    return we_vote_id_last_voter_guide_integer


def fetch_next_we_vote_election_id_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    last_integer = we_vote_settings_manager.fetch_setting('we_vote_last_election_id_integer')
    last_integer = convert_to_int(last_integer)
    if last_integer >= 1000000:
        last_integer += 1
    else:
        last_integer = 1000000
    we_vote_settings_manager.save_setting('we_vote_last_election_id_integer', last_integer)
    return last_integer

def fetch_next_we_vote_id_electoral_district_integer():
    we_vote_settings_manager = WeVoteSettingsManager()
    we_vote_id_electoral_district_integer = \
        we_vote_settings_manager.fetch_setting('we_vote_id_electoral_district_integer')
    we_vote_id_electoral_district_integer = convert_to_int(we_vote_id_electoral_district_integer)
    we_vote_id_electoral_district_integer += 1
    we_vote_settings_manager.save_setting('we_vote_id_electoral_district_integer',
                                          we_vote_id_electoral_district_integer)
    return we_vote_id_electoral_district_integer
