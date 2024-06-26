# voter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json
import re
import string
import sys
from datetime import datetime, timedelta

import pytz
import requests
import usaddress
from django.contrib.auth.models import (BaseUserManager, AbstractBaseUser)  # PermissionsMixin
from django.core.validators import RegexValidator
from django.db import (models, IntegrityError)
from django.db.models import Q
from django.utils.timezone import now
from geopy import get_geocoder_for_service
from validate_email import validate_email

import wevote_functions.admin
from apple.models import AppleUser
from config.base import get_environment_variable, get_environment_variable_default
from exception.models import handle_exception, handle_record_found_more_than_one_exception, \
    handle_record_not_saved_exception
from import_export_facebook.models import FacebookManager
from sms.models import SMSManager
from twitter.models import TwitterUserManager
from wevote_functions.functions import extract_state_code_from_address_string, convert_to_int, generate_random_string, \
    generate_voter_device_id, get_voter_api_device_id, positive_value_exists
from wevote_functions.functions_date import generate_localized_datetime_from_obj
from wevote_settings.models import fetch_next_we_vote_id_voter_integer, fetch_site_unique_id_prefix

logger = wevote_functions.admin.get_logger(__name__)
SUPPORT_OPPOSE_MODAL_SHOWN = 1  # When this bit is set, we know the voter has seen the initial support/oppose modal
BALLOT_INTRO_MODAL_SHOWN = 2  # When this bit is set, we know the voter has seen the initial ballot introduction modal
BALLOT_INTRO_ISSUES_COMPLETED = 4  # When this bit is set, the voter follows at least one issue (no need for intro)
BALLOT_INTRO_ORGANIZATIONS_COMPLETED = 8  # ...the voter follows at least one organization (no need for intro)
BALLOT_INTRO_POSITIONS_COMPLETED = 16  # ...the voter has taken at least one position (no need for intro)
BALLOT_INTRO_FRIENDS_COMPLETED = 32  # ...the voter has reached out to at least one friend (no need for intro)
BALLOT_INTRO_SHARE_COMPLETED = 64  # ...the voter has shared at least one item (no need for intro)
BALLOT_INTRO_VOTE_COMPLETED = 128  # ...the voter learned about casting their vote (no need for intro)

INTERFACE_STATUS_THRESHOLD_ISSUES_FOLLOWED = 3
INTERFACE_STATUS_THRESHOLD_ORGANIZATIONS_FOLLOWED = 5

# Notifications that get set from the WebApp
# notification_flag_integer_to_set, notification_flag_integer_to_unset
# Used for notification_settings bits. Which notification options has the voter chosen?
NOTIFICATION_ZERO = 0
NOTIFICATION_NEWSLETTER_OPT_IN = 1  # "I would like to receive the We Vote newsletter" - newsletter
# NOTIFICATION_FRIEND_REQUESTS = n/a,  # In App: "New friend requests"
NOTIFICATION_FRIEND_REQUESTS_EMAIL = 2  # Email: "New friend requests" - friendinvite
NOTIFICATION_FRIEND_REQUESTS_SMS = 4  # SMS: "New friend requests"
# NOTIFICATION_SUGGESTED_FRIENDS = n/a  # In App: "Suggestions of people you may know"
NOTIFICATION_SUGGESTED_FRIENDS_EMAIL = 8  # Email: "Suggestions of people you may know" - suggestedfriend
NOTIFICATION_SUGGESTED_FRIENDS_SMS = 16  # SMS: "Suggestions of people you may know"
# NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT = n/a  # In App: "Friends' opinions (on your ballot)"
NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL = 32  # Email: "Friends' opinions (on your ballot)" - friendopinions
NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_SMS = 64  # SMS: "Friends' opinions (on your ballot)"
NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS = 128  # In App: "Friends' opinions (other regions)"
NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL = 256  # Email: "Friends' opinions (other regions)" - friendopinionsall
NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS = 512  # SMS: "Friends' opinions (other regions)"
# NOTIFICATION_VOTER_DAILY_SUMMARY = n/a  # In App: When a friend posts something, or reacts to another post
NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL = 1024  # Email: When a friend posts something - dailyfriendactivity
NOTIFICATION_VOTER_DAILY_SUMMARY_SMS = 2048  # SMS: When a friend posts something
# TODO 2022-07-19 UPDATES NEEDED TO SUPPORT THESE NEW VALUES
NOTIFICATION_FRIEND_REQUEST_RESPONSES_EMAIL = 4096  # Email: "Show me responses to my friend requests" - friendaccept
NOTIFICATION_FRIEND_REQUEST_RESPONSES_SMS = 8192,  # SMS: "Show me responses to my friend requests"
NOTIFICATION_LOGIN_EMAIL = 16384  # Email: "Show me email login requests" - login
NOTIFICATION_LOGIN_SMS = 32768  # SMS: "Show me SMS login requests"
NOTIFICATION_FRIEND_MESSAGES_EMAIL = 65536  # Email: "Show me messages from friends" - friendmessage
NOTIFICATION_FRIEND_MESSAGES_SMS = 131072  # SMS: "Show me messages from friends"

# Default to set for new voters
NOTIFICATION_SETTINGS_FLAGS_DEFAULT = \
    NOTIFICATION_NEWSLETTER_OPT_IN + \
    NOTIFICATION_FRIEND_REQUESTS_EMAIL + \
    NOTIFICATION_SUGGESTED_FRIENDS_EMAIL + \
    NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL + \
    NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS + \
    NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL + \
    NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL

NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE = 5
NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME = 25

# See process_maintenance_status_flags in /voter/controllers.py
MAINTENANCE_STATUS_FLAGS_TASK_ONE = 1
MAINTENANCE_STATUS_FLAGS_TASK_TWO = 2
MAINTENANCE_STATUS_FLAGS_COMPLETED = MAINTENANCE_STATUS_FLAGS_TASK_ONE + MAINTENANCE_STATUS_FLAGS_TASK_TWO

PROFILE_IMAGE_TYPE_FACEBOOK = 'FACEBOOK'
PROFILE_IMAGE_TYPE_TWITTER = 'TWITTER'
PROFILE_IMAGE_TYPE_UNKNOWN = 'UNKNOWN'
PROFILE_IMAGE_TYPE_UPLOADED = 'UPLOADED'
PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES = (
    (PROFILE_IMAGE_TYPE_FACEBOOK, 'Facebook'),
    (PROFILE_IMAGE_TYPE_TWITTER, 'Twitter'),
    (PROFILE_IMAGE_TYPE_UNKNOWN, 'Unknown'),
    (PROFILE_IMAGE_TYPE_UPLOADED, 'Uploaded'),
)

IMPORT_CONTACT_GOOGLE_PEOPLE = 'GOOGLE_PEOPLE_API'
IMPORT_CONTACT_SOURCE_CHOICES = (
    (IMPORT_CONTACT_GOOGLE_PEOPLE, 'Google People API'),
)

VALID_STATES = ['AL', 'AK', 'AZ', 'AR', 'AS', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'GU', 'HI', 'ID', 'IL',
                'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
                'NJ', 'NM', 'NY', 'NC', 'ND', 'NP', 'OH', 'OK', 'OR', 'PA', 'PR', 'RI', 'SC', 'SD', 'TN', 'TX',
                'TT', 'UT', 'VT', 'VA', 'VI', 'WA', 'WV', 'WI', 'WY']

GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
GEOCODE_TIMEOUT = 10


# See AUTH_USER_MODEL in config/base.py


class VoterManager(BaseUserManager):

    def __repr__(self):
        return '__repr__ for VoterManager'

    def clear_out_collisions_for_linked_organization_we_vote_id(self, current_voter_we_vote_id,
                                                                organization_we_vote_id):
        status = ""
        success = True
        collision_results = self.retrieve_voter_by_organization_we_vote_id(
            organization_we_vote_id)
        if collision_results['voter_found']:
            collision_voter = collision_results['voter']
            if collision_voter.we_vote_id != current_voter_we_vote_id:
                # Release the linked_organization_we_vote_id from collision_voter so it can be used on voter
                try:
                    collision_voter.linked_organization_we_vote_id = None
                    collision_voter.save()

                    # TODO DALE UPDATE positions to remove voter_we_vote_id
                    # Since we are disconnecting the organization from the voter, do we want to go through
                    # positions and split them apart?
                except Exception as e:
                    success = False
                    status += " UNABLE_TO_UPDATE_COLLISION_VOTER_WITH_EMPTY_ORGANIZATION_WE_VOTE_ID"
        results = {
            'success':  success,
            'status':   status
        }
        return results

    @staticmethod
    def alter_linked_organization_we_vote_id(voter, linked_organization_we_vote_id=None):
        status = ""
        success = True
        if voter and hasattr(voter, "first_name"):
            try:
                voter.linked_organization_we_vote_id = linked_organization_we_vote_id
                voter.save()
            except Exception as e:
                success = False
                status += " UNABLE_TO_UPDATE_VOTER_LINKED_ORGANIZATION_WE_VOTE_ID: " + str(e)
        else:
            status += "INVALID_VOTER "
        results = {
            'success':  success,
            'status':   status
        }
        return results

    @staticmethod
    def update_or_create_contact_email_augmented(
            checked_against_open_people=None,
            checked_against_sendgrid=None,
            checked_against_snovio=None,
            checked_against_targetsmart=None,
            email_address_text='',
            existing_contact_email_augmented_dict=None,
            has_known_bounces=None,
            has_mx_or_a_record=None,
            has_suspected_bounces=None,
            is_invalid=None,
            is_verified=None,
            open_people_city=None,
            open_people_first_name=None,
            open_people_last_name=None,
            open_people_middle_name=None,
            open_people_state_code=None,
            open_people_zip_code=None,
            sendgrid_id=None,
            snovio_id=None,
            snovio_locality=None,
            snovio_source_state=None,
            targetsmart_id=None,
            targetsmart_source_state=None,
    ):
        if existing_contact_email_augmented_dict is None:
            existing_contact_email_augmented_dict = {}
        status = ""
        success = True
        contact_email_augmented = None
        contact_email_augmented_found = False
        contact_email_augmented_created = False
        contact_email_augmented_updated = False

        # Instead of retrieving emails one at a time, we retrieve a list based on the batch we are running
        email_address_text_lower = email_address_text.lower()
        if email_address_text_lower in existing_contact_email_augmented_dict:
            contact_email_augmented_found = True
            contact_email_augmented = existing_contact_email_augmented_dict[email_address_text_lower]

        if not contact_email_augmented_found:
            try:
                contact_email_augmented, contact_email_augmented_created = ContactEmailAugmented.objects.get_or_create(
                    email_address_text__iexact=email_address_text_lower,
                    defaults={'email_address_text': email_address_text_lower}
                )
                contact_email_augmented_found = True
                status += "CONTACT_EMAIL_AUGMENTED_GET_OR_CREATE_SUCCESS "
            except Exception as e:
                contact_email_augmented = None
                success = False
                status += "CONTACT_EMAIL_AUGMENTED_NOT_CREATED: " + str(e) + " "

        if success:
            try:
                change_to_save = False
                if checked_against_open_people is not None:
                    if contact_email_augmented.checked_against_open_people != checked_against_open_people:
                        contact_email_augmented.checked_against_open_people = checked_against_open_people
                        contact_email_augmented.date_last_checked_against_open_people = now()
                        change_to_save = True
                if checked_against_sendgrid is not None:
                    if contact_email_augmented.checked_against_sendgrid != checked_against_sendgrid:
                        contact_email_augmented.checked_against_sendgrid = checked_against_sendgrid
                        contact_email_augmented.date_last_checked_against_sendgrid = now()
                        change_to_save = True
                if checked_against_snovio is not None:
                    if contact_email_augmented.checked_against_snovio != checked_against_snovio:
                        contact_email_augmented.checked_against_snovio = checked_against_snovio
                        contact_email_augmented.date_last_checked_against_snovio = now()
                        change_to_save = True
                if checked_against_targetsmart is not None:
                    if contact_email_augmented.checked_against_targetsmart != checked_against_targetsmart:
                        contact_email_augmented.checked_against_targetsmart = checked_against_targetsmart
                        contact_email_augmented.date_last_checked_against_targetsmart = now()
                        change_to_save = True
                if has_known_bounces is not None:
                    if contact_email_augmented.has_known_bounces != has_known_bounces:
                        contact_email_augmented.has_known_bounces = has_known_bounces
                        change_to_save = True
                if has_mx_or_a_record is not None:
                    if contact_email_augmented.has_mx_or_a_record != has_mx_or_a_record:
                        contact_email_augmented.has_mx_or_a_record = has_mx_or_a_record
                        change_to_save = True
                if has_suspected_bounces is not None:
                    if contact_email_augmented.has_suspected_bounces != has_suspected_bounces:
                        contact_email_augmented.has_suspected_bounces = has_suspected_bounces
                        change_to_save = True
                if is_invalid is not None:
                    if contact_email_augmented.is_invalid != is_invalid:
                        contact_email_augmented.is_invalid = is_invalid
                        change_to_save = True
                if is_verified is not None:
                    if contact_email_augmented.is_verified != is_verified:
                        contact_email_augmented.is_verified = is_verified
                        change_to_save = True
                if open_people_city is not None:
                    if contact_email_augmented.open_people_city != open_people_city:
                        contact_email_augmented.open_people_city = open_people_city
                        change_to_save = True
                if open_people_first_name is not None:
                    if contact_email_augmented.open_people_first_name != open_people_first_name:
                        contact_email_augmented.open_people_first_name = open_people_first_name
                        change_to_save = True
                if open_people_last_name is not None:
                    if contact_email_augmented.open_people_last_name != open_people_last_name:
                        contact_email_augmented.open_people_last_name = open_people_last_name
                        change_to_save = True
                if open_people_middle_name is not None:
                    if contact_email_augmented.open_people_middle_name != open_people_middle_name:
                        contact_email_augmented.open_people_middle_name = open_people_middle_name
                        change_to_save = True
                if open_people_state_code is not None:
                    if contact_email_augmented.open_people_state_code != open_people_state_code:
                        contact_email_augmented.open_people_state_code = open_people_state_code
                        change_to_save = True
                if open_people_zip_code is not None:
                    if contact_email_augmented.open_people_zip_code != open_people_zip_code:
                        contact_email_augmented.open_people_zip_code = open_people_zip_code
                        change_to_save = True
                if snovio_id is not None:
                    if contact_email_augmented.snovio_id != snovio_id:
                        contact_email_augmented.snovio_id = snovio_id
                        change_to_save = True
                if snovio_locality is not None:
                    if contact_email_augmented.snovio_locality != snovio_locality:
                        contact_email_augmented.snovio_locality = snovio_locality
                        change_to_save = True
                if snovio_source_state is not None:
                    if contact_email_augmented.snovio_source_state != snovio_source_state:
                        contact_email_augmented.snovio_source_state = snovio_source_state
                        change_to_save = True
                if targetsmart_id is not None:
                    if contact_email_augmented.targetsmart_id != targetsmart_id:
                        contact_email_augmented.targetsmart_id = targetsmart_id
                        change_to_save = True
                if targetsmart_source_state is not None:
                    if contact_email_augmented.targetsmart_source_state != targetsmart_source_state:
                        contact_email_augmented.targetsmart_source_state = targetsmart_source_state
                        change_to_save = True
                if change_to_save:
                    contact_email_augmented.save()
                    contact_email_augmented_updated = True
                    success = True
                    status += "CONTACT_EMAIL_AUGMENTED_UPDATED "
                else:
                    status += "NO_CHANGE_TO_CONTACT_EMAIL_AUGMENTED "
            except Exception as e:
                contact_email_augmented = None
                success = False
                status += "CONTACT_EMAIL_AUGMENTED_NOT_UPDATED: " + str(e) + " "

        results = {
            'success':                          success,
            'status':                           status,
            'contact_email_augmented':          contact_email_augmented,
            'contact_email_augmented_created':  contact_email_augmented_created,
            'contact_email_augmented_found':    contact_email_augmented_found,
            'contact_email_augmented_updated':  contact_email_augmented_updated,
        }
        return results

    @staticmethod
    def update_or_create_voter_contact_email(
            city=None,
            display_name=None,
            email_address_text='',
            existing_voter_contact_email_dict={},
            first_name=None,
            from_google_people_api=False,
            google_contact_id=None,
            google_date_last_updated=None,
            google_display_name=None,
            google_first_name=None,
            google_last_name=None,
            ignore_contact=None,
            imported_by_voter_we_vote_id='',
            is_friend=None,
            last_name=None,
            middle_name=None,
            state_code=None,
            zip_code=None,
            phone_number=None,
            api_type=None,
    ):
        """

        :param city:
        :param display_name:
        :param email_address_text:
        :param existing_voter_contact_email_dict:
        :param first_name:
        :param from_google_people_api:
        :param google_contact_id:
        :param google_date_last_updated:
        :param google_display_name:
        :param google_first_name:
        :param google_last_name:
        :param ignore_contact:
        :param imported_by_voter_we_vote_id:
        :param is_friend:
        :param last_name:
        :param middle_name:
        :param state_code:
        :param zip_code:
        :param phone_number,
        :param api_type,
        :return:
        """
        status = ""
        success = True
        voter_contact_email = None
        voter_contact_email_found = False
        voter_contact_email_created = False

        source_specified = positive_value_exists(from_google_people_api)
        if not source_specified or not positive_value_exists(email_address_text):
            status += "CREATE_OR_UPDATE_VOTER_CONTACT_EMAIL-MISSING_REQUIRED_VARIABLES "
            results = {
                'success':                      False,
                'status':                       status,
                'voter_contact_email':          None,
                'voter_contact_email_created':  voter_contact_email_created,
                'voter_contact_email_found':    voter_contact_email_found,
            }
            return results

        email_address_text_lower = email_address_text.lower()
        if email_address_text_lower in existing_voter_contact_email_dict:
            voter_contact_email_found = True
            voter_contact_email = existing_voter_contact_email_dict[email_address_text_lower]

        if voter_contact_email_found:
            try:
                change_to_save = False
                if positive_value_exists(from_google_people_api):
                    # Sept 2022:  has_data_from_google_people_api assumed a different data structure for google and
                    # apple, this variable will always be true
                    if not positive_value_exists(voter_contact_email.has_data_from_google_people_api):
                        voter_contact_email.has_data_from_google_people_api = True
                        change_to_save = True
                    if google_contact_id is not None:
                        if voter_contact_email.google_contact_id != google_contact_id:
                            voter_contact_email.google_contact_id = google_contact_id
                            change_to_save = True
                    if google_date_last_updated is not None:
                        if voter_contact_email.google_date_last_updated != google_date_last_updated:
                            voter_contact_email.google_date_last_updated = google_date_last_updated
                            change_to_save = True
                    if google_display_name is not None:
                        if voter_contact_email.google_display_name != google_display_name:
                            voter_contact_email.google_display_name = google_display_name
                            change_to_save = True
                    if google_first_name is not None:
                        if voter_contact_email.google_first_name != google_first_name:
                            voter_contact_email.google_first_name = google_first_name
                            change_to_save = True
                    if google_last_name is not None:
                        if voter_contact_email.google_last_name != google_last_name:
                            voter_contact_email.google_last_name = google_last_name
                            change_to_save = True
                    if phone_number is not None:
                        if voter_contact_email.phone_number != phone_number:
                            voter_contact_email.phone_number = phone_number
                            change_to_save = True
                    if api_type is not None:
                        if voter_contact_email.api_type != api_type:
                            voter_contact_email.api_type = api_type   # Might as well save the latest one
                            change_to_save = True
                if city is not None:
                    if voter_contact_email.city != city:
                        voter_contact_email.city = city
                        change_to_save = True
                if display_name is not None:
                    # If we force a specific display_name...
                    if voter_contact_email.display_name != display_name:
                        voter_contact_email.display_name = display_name
                        change_to_save = True
                if first_name is not None:
                    if voter_contact_email.first_name != first_name:
                        voter_contact_email.first_name = first_name
                        change_to_save = True
                if ignore_contact is not None:
                    if voter_contact_email.ignore_contact != ignore_contact:
                        voter_contact_email.ignore_contact = ignore_contact
                        change_to_save = True
                if is_friend is not None:
                    if voter_contact_email.is_friend != is_friend:
                        voter_contact_email.is_friend = is_friend
                        change_to_save = True
                if last_name is not None:
                    if voter_contact_email.last_name != last_name:
                        voter_contact_email.last_name = last_name
                        change_to_save = True
                if middle_name is not None:
                    if voter_contact_email.middle_name != middle_name:
                        voter_contact_email.middle_name = middle_name
                        change_to_save = True
                if state_code is not None:
                    if voter_contact_email.state_code != state_code:
                        voter_contact_email.state_code = state_code
                        change_to_save = True
                if zip_code is not None:
                    if voter_contact_email.zip_code != zip_code:
                        voter_contact_email.zip_code = zip_code
                        change_to_save = True
                if change_to_save:
                    voter_contact_email.save()
                    voter_contact_email_created = True
                    success = True
                    status += "VOTER_CONTACT_EMAIL_UPDATED "
                else:
                    status += "NO_CHANGE_TO_VOTER_CONTACT_EMAIL "
            except Exception as e:
                voter_contact_email_created = False
                voter_contact_email = None
                success = False
                status += "VOTER_CONTACT_EMAIL_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                change_to_save = False
                if positive_value_exists(from_google_people_api):
                    voter_contact_email = VoterContactEmail.objects.create(
                        google_date_last_updated=google_date_last_updated,
                        email_address_text=email_address_text,
                        google_contact_id=google_contact_id,
                        google_display_name=google_display_name,
                        google_first_name=google_first_name,
                        google_last_name=google_last_name,
                        has_data_from_google_people_api=True,
                        imported_by_voter_we_vote_id=imported_by_voter_we_vote_id,
                        state_code=state_code,
                        phone_number=phone_number,
                        api_type=api_type,
                    )
                else:
                    status += "NOT_A_RECOGNIZED_CONTACT_TYPE "
                    results = {
                        'success': False,
                        'status': status,
                        'voter_contact_email': None,
                        'voter_contact_email_created': voter_contact_email_created,
                        'voter_contact_email_found': voter_contact_email_found,
                    }
                    return results
                if ignore_contact is not None:
                    voter_contact_email.ignore_contact = ignore_contact
                    change_to_save = True
                if is_friend is not None:
                    voter_contact_email.is_friend = is_friend
                    change_to_save = True
                if change_to_save:
                    voter_contact_email.save()
                voter_contact_email_created = True
                voter_contact_email_found = True
                status += "VOTER_CONTACT_EMAIL_CREATED "
            except Exception as e:
                voter_contact_email_created = False
                voter_contact_email_found = False
                voter_contact_email = None
                success = False
                status += "VOTER_CONTACT_EMAIL_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'voter_contact_email':          voter_contact_email,
            'voter_contact_email_created':  voter_contact_email_created,
            'voter_contact_email_found':    voter_contact_email_found,
        }
        return results

    def update_or_create_voter_plan(
            self,
            voter_we_vote_id='',
            google_civic_election_id=0,
            show_to_public=None,
            state_code=None,
            voter_plan_data_serialized=None,
            voter_plan_text=None):
        status = ""
        voter_plan_found = False
        voter_plan_created = False
        voter_plan = None

        if positive_value_exists(google_civic_election_id):
            google_civic_election_id = convert_to_int(google_civic_election_id)
        else:
            google_civic_election_id = 0
        if not positive_value_exists(google_civic_election_id) \
                or not positive_value_exists(voter_we_vote_id) \
                or not positive_value_exists(voter_plan_text):
            status += "CREATE_OR_UPDATE_VOTER_PLAN-MISSING_REQUIRED_VARIABLES "
            results = {
                'success':              False,
                'status':               status,
                'voter_plan_found':     voter_plan_found,
                'voter_plan_created':   voter_plan_created,
                'voter_plan':           None,
            }
            return results

        results = self.retrieve_voter_plan_list(
            google_civic_election_id=google_civic_election_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=False)
        voter_plan_list = results['voter_plan_list']
        if positive_value_exists(len(voter_plan_list)):
            voter_plan = voter_plan_list[0]
            voter_plan_found = True
        success = results['success']
        status += results['status']
        if not positive_value_exists(success):
            status += "CREATE_OR_UPDATE_VOTER_PLAN-PROBLEM_RETRIEVING_EXISTING "
            results = {
                'success': False,
                'status': status,
                'voter_plan_found': voter_plan_found,
                'voter_plan_created': voter_plan_created,
                'voter_plan': None,
            }
            return results

        if voter_plan_found:
            try:
                change_to_save = False
                if show_to_public is not None:
                    voter_plan.show_to_public = show_to_public
                    change_to_save = True
                if state_code is not None:
                    voter_plan.state_code = state_code
                    change_to_save = True
                if voter_plan_data_serialized is not None:
                    voter_plan.voter_plan_data_serialized = voter_plan_data_serialized
                    change_to_save = True
                if voter_plan_text is not None:
                    voter_plan.voter_plan_text = voter_plan_text
                    change_to_save = True
                if change_to_save:
                    voter_plan.save()
                    voter_plan_created = True
                    success = True
                    status += "VOTER_PLAN_UPDATED "
            except Exception as e:
                voter_plan_created = False
                voter_plan = None
                success = False
                status += "VOTER_PLAN_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                voter_plan = VoterPlan.objects.create(
                    google_civic_election_id=google_civic_election_id,
                    voter_we_vote_id=voter_we_vote_id,
                    show_to_public=show_to_public,
                    state_code=state_code,
                    voter_plan_data_serialized=voter_plan_data_serialized,
                    voter_plan_text=voter_plan_text,
                )
                voter_plan_created = True
                voter_plan_found = True
                status += "VOTER_PLAN_CREATED "
            except Exception as e:
                voter_plan_created = False
                voter_plan = None
                success = False
                status += "VOTER_PLAN_NOT_CREATED: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'voter_plan_found':     voter_plan_found,
            'voter_plan_created':   voter_plan_created,
            'voter_plan':           voter_plan,
        }
        return results

    def create_user(self, email=None, username=None, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        email = self.normalize_email(email)
        user = self.model(email=self.normalize_email(email))

        # python-social-auth will pass the username and email
        if username:
            user.fb_username = username

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(email, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user

    def create_voter(self, email=None, password=None):
        email = self.normalize_email(email)
        email_not_valid = False
        password_not_valid = False

        voter = Voter()
        voter_id = 0
        voter_created = False
        try:
            if validate_email(email):
                voter.email = email
            else:
                email_not_valid = True

            if password:
                voter.set_password(password)
            else:
                password_not_valid = True
            voter.save()
            voter_id = voter.id
            voter_created = True
        except IntegrityError as e:
            handle_record_not_saved_exception(e, logger=logger)
            logger.error("create_voter IntegrityError exception (#1): " + str(e))
            try:
                # Trying to save again will increment the 'we_vote_id_last_voter_integer'
                # by calling 'fetch_next_we_vote_id_voter_integer'
                # TODO We could get into a race condition where multiple creates could be failing at once, so we
                #  should look more closely at this
                voter.save()
                voter_id = voter.id
                voter_created = True
            except IntegrityError as e:
                handle_record_not_saved_exception(e, logger=logger)
                logger.error("create_voter IntegrityError exception (#2): " + str(e))
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                logger.error("create_voter general exception (#1): " + str(e))

        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            logger.error("create_voter general exception (#2): " + str(e))

        results = {
            'email_not_valid':      email_not_valid,
            'password_not_valid':   password_not_valid,
            'voter_created':        voter_created,
            'voter':                voter,
        }
        return results

    @staticmethod
    def create_developer(first_name, last_name, email, password):
        voter = Voter()
        try:
            voter.set_password(password)
            voter.first_name = first_name
            voter.last_name = last_name
            voter.email = email
            voter.is_admin = True
            voter.is_verified_volunteer = True
            voter.is_active = True
            voter.save()
            logger.debug("create_voter successfully created developer (voter) : " + first_name)

        except IntegrityError as e:
            handle_record_not_saved_exception(e, logger=logger)
            print("create_developer IntegrityError exception:" + str(e))
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            logger.debug("create_voter general exception: " + str(e))

        return voter

    @staticmethod
    def create_new_voter_account(
            first_name,
            last_name,
            email,
            password,
            is_admin=False,
            is_analytics_admin=False,
            is_partner_organization=False,
            is_political_data_manager=False,
            is_political_data_viewer=False,
            is_verified_volunteer=False,
            is_voter_manager=False):
        """
        Create a new voter, called from the api.wevoteusa.org/voter page
        :param first_name:
        :param last_name:
        :param email:
        :param password:
        :param is_admin:
        :param is_analytics_admin:
        :param is_partner_organization:
        :param is_political_data_manager:
        :param is_political_data_viewer:
        :param is_verified_volunteer:
        :param is_voter_manager:
        :return:
        """
        voter = Voter()
        success = False
        status = ""
        duplicate_email = False
        email_address_object_created = False
        email_address_we_vote_id = ''
        voter_created = False
        try:
            voter.set_password(password)
            voter.first_name = first_name
            voter.last_name = last_name
            voter.email = email
            voter.is_admin = is_admin
            voter.is_analytics_admin = is_analytics_admin
            voter.is_partner_organization = is_partner_organization
            voter.is_political_data_manager = is_political_data_manager
            voter.is_political_data_viewer = is_political_data_viewer
            voter.is_verified_volunteer = is_verified_volunteer
            voter.is_voter_manager = is_voter_manager
            voter.is_active = True
            voter.save()
            voter_created = True
            success = True
            status = "Created voter " + str(voter.we_vote_id) + " "
            logger.debug("create_new_voter_account successfully created (voter) : " + first_name)
        except IntegrityError as e:
            status += "FAILED_TO_CREATE_VOTER_INTEGRITY: " + str(e) + " "
            handle_record_not_saved_exception(e, logger=logger)
            print("create_new_voter_account IntegrityError exception:" + str(e))
            if "voter_voter_email_key" in str(e):
                duplicate_email = True
        except Exception as e:
            status += "FAILED_TO_CREATE_VOTER: " + str(e) + " "
            handle_record_not_saved_exception(e, logger=logger)
            logger.debug("create_new_voter_account general exception: " + str(e))

        if voter_created:
            try:
                from email_outbound.models import EmailManager
                email_manager = EmailManager()
                email_results = email_manager.create_email_address(
                    normalized_email_address=email,
                    voter_we_vote_id=voter.we_vote_id,
                    email_ownership_is_verified=True,
                )
                email_address_object_created = True
                status += email_results['status']
                if email_results['email_address_object_saved']:
                    email_address_object = email_results['email_address_object']
                    email_address_we_vote_id = email_address_object.we_vote_id
            except Exception as e:
                status += "FAILED_TO_CREATE_VOTER_EMAIL_ADDRESS: " + str(e) + " "
                handle_record_not_saved_exception(e, logger=logger)
                logger.debug("ERROR_SAVING_NEW_EMAIL create_new_voter_account general exception: " + str(e))

        if email_address_object_created:
            try:
                voter.email_ownership_is_verified = True
                voter.primary_email_we_vote_id = email_address_we_vote_id
                voter.save()
                status += "VOTER_CREATED_EMAIL_OWNERSHIP_VERIFIED "
            except Exception as e:
                status += "FAILED_TO_UPDATE_VOTER_WITH_EMAIL_ADDRESS: " + str(e) + " "
                handle_record_not_saved_exception(e, logger=logger)
                logger.debug("ERROR_SAVING_NEW_EMAIL create_new_voter_account general exception: " + str(e))

        results = {
            'success': success,
            'status': status,
            'duplicate_email': duplicate_email,
            'voter': voter,
        }

        return results

    def delete_voter(self, email):
        email = self.normalize_email(email)
        voter_id = 0
        voter_we_vote_id = ''
        voter_deleted = False

        if positive_value_exists(email) and validate_email(email):
            email_valid = True
        else:
            email_valid = False

        try:
            if email_valid:
                results = self.retrieve_voter(voter_id, email, voter_we_vote_id)
                if results['voter_found']:
                    voter = results['voter']
                    voter_id = voter.id
                    voter.delete()
                    voter_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'email_not_valid':      True if not email_valid else False,
            'voter_deleted':        voter_deleted,
            'voter_id':             voter_id,
        }
        return results

    @staticmethod
    def duplicate_voter(voter):
        """
        Starting with an existing voter, create a duplicate version with different we_vote_id
        :param voter:
        :return:
        """
        voter_id = 0
        success = False
        status = ""
        try:
            voter.id = None  # Remove the primary key so it is forced to save a new entry
            voter.pk = None
            voter.email = None
            voter.email_ownership_is_verified = False
            voter.facebook_id = None
            voter.facebook_email = None
            voter.fb_username = None
            voter.linked_organization_we_vote_id = None
            voter.twitter_voters_access_token = None
            voter.twitter_voters_access_token_secret = None
            voter.twitter_connection_active = False
            voter.twitter_id = None
            voter.twitter_request_secret = None
            voter.twitter_request_token = None
            voter.twitter_screen_name = None
            voter.primary_email_we_vote_id = None
            voter.we_vote_id = None  # Clear out existing we_vote_id
            voter.generate_new_we_vote_id()
            voter.save()
            status += "DUPLICATE_VOTER_SUCCESSFUL"
            voter_id = voter.id
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            status += "DUPLICATE_VOTER_FAILED"

        results = {
            'success':          success,
            'status':           status,
            'voter_duplicated': True if voter_id > 0 else False,
            'voter':            voter,
        }
        return results

    @staticmethod
    def retrieve_contact_email_augmented_list(
            checked_against_open_people_more_than_x_days_ago=None,
            checked_against_sendgrid_more_than_x_days_ago=None,
            checked_against_snovio_more_than_x_days_ago=None,
            checked_against_targetsmart_more_than_x_days_ago=None,
            email_address_text_list=None,
            read_only=True):
        success = True
        status = ""
        contact_email_augmented_list = []

        try:
            if positive_value_exists(read_only):
                list_query = ContactEmailAugmented.objects.using('readonly').all()
            else:
                list_query = ContactEmailAugmented.objects.all()

            # Filter based on when record was last augmented
            if checked_against_open_people_more_than_x_days_ago == 0:
                # Don't limit by if/when data was retrieved previously
                pass
            elif checked_against_open_people_more_than_x_days_ago is not None:
                # Only retrieve the record if it hasn't been retrieved, or was retrieved more than x days ago
                the_date_x_days_ago = now() - timedelta(days=checked_against_open_people_more_than_x_days_ago)
                list_query = list_query.filter(
                    Q(checked_against_open_people=False) |
                    Q(date_last_checked_against_open_people__isnull=True) |
                    Q(date_last_checked_against_open_people__lt=the_date_x_days_ago))
            elif checked_against_sendgrid_more_than_x_days_ago == 0:
                # Don't limit by if/when SendGrid data was retrieved previously
                pass
            elif checked_against_sendgrid_more_than_x_days_ago is not None:
                # Only retrieve the record if it hasn't been retrieved, or was retrieved more than x days ago
                the_date_x_days_ago = now() - timedelta(days=checked_against_sendgrid_more_than_x_days_ago)
                list_query = list_query.filter(
                    Q(checked_against_sendgrid=False) |
                    Q(date_last_checked_against_sendgrid__isnull=True) |
                    Q(date_last_checked_against_sendgrid__lt=the_date_x_days_ago))
            elif checked_against_snovio_more_than_x_days_ago == 0:
                # Don't limit by if/when SnovIO data was retrieved previously
                pass
            elif checked_against_snovio_more_than_x_days_ago is not None:
                # Only retrieve the record if it hasn't been retrieved, or was retrieved more than x days ago
                the_date_x_days_ago = now() - timedelta(days=checked_against_snovio_more_than_x_days_ago)
                list_query = list_query.filter(
                    Q(checked_against_snovio=False) |
                    Q(date_last_checked_against_snovio__isnull=True) |
                    Q(date_last_checked_against_snovio__lt=the_date_x_days_ago))
            elif checked_against_targetsmart_more_than_x_days_ago == 0:
                # Don't limit by if/when TargetSmart data was retrieved previously
                pass
            elif checked_against_targetsmart_more_than_x_days_ago is not None:
                # Only retrieve the record if it hasn't been retrieved, or was retrieved more than x days ago
                the_date_x_days_ago = now() - timedelta(days=checked_against_targetsmart_more_than_x_days_ago)
                list_query = list_query.filter(
                    Q(checked_against_targetsmart=False) |
                    Q(date_last_checked_against_targetsmart__isnull=True) |
                    Q(date_last_checked_against_targetsmart__lt=the_date_x_days_ago))

            # Limit the records we retrieve to this email list
            if email_address_text_list is not None and len(email_address_text_list) > 0:
                filters = []
                for email_address_text in email_address_text_list:
                    new_filter = Q(email_address_text__iexact=email_address_text)
                    filters.append(new_filter)
                if len(filters):
                    final_filters = filters.pop()
                    for item in filters:
                        final_filters |= item
                    list_query = list_query.filter(final_filters)

            contact_email_augmented_list = list(list_query)
            if len(contact_email_augmented_list) > 0:
                status += "CONTACT_EMAIL_AUGMENTED_LIST_FOUND "
                contact_email_augmented_list_found = True
            else:
                status += "NO_CONTACT_EMAIL_AUGMENTED_ITEMS_FOUND "
                contact_email_augmented_list_found = False
        except Exception as e:
            contact_email_augmented_list_found = False
            status += "CONTACT_EMAIL_AUGMENTED_LIST_NOT_FOUND-EXCEPTION: " + str(e) + ' '
            success = False

        email_addresses_returned_list = []
        if contact_email_augmented_list_found:
            for contact_email_augmented in contact_email_augmented_list:
                email_addresses_returned_list.append(contact_email_augmented.email_address_text)

        contact_email_augmented_list_as_dict = {}
        for contact_email_augmented in contact_email_augmented_list:
            email_address_text_lower = contact_email_augmented.email_address_text.lower()
            contact_email_augmented_list_as_dict[email_address_text_lower] = contact_email_augmented

        results = {
            'success':                              success,
            'status':                               status,
            'contact_email_augmented_list':         contact_email_augmented_list,
            'contact_email_augmented_list_as_dict': contact_email_augmented_list_as_dict,
            'contact_email_augmented_list_found':   contact_email_augmented_list_found,
            'email_addresses_returned_list':        email_addresses_returned_list,
        }
        return results

    @staticmethod
    def retrieve_voter_contact_email(
            email_address_text='',
            imported_by_voter_we_vote_id='',
            read_only=False):
        success = True
        status = ""
        voter_contact_email = None
        voter_contact_email_found = False

        if not positive_value_exists(email_address_text) or \
                not positive_value_exists(imported_by_voter_we_vote_id):
            status += "MISSING_IMPORTED_BY_VOTER_WE_VOTE_ID "
            results = {
                'success':                      False,
                'status':                       status,
                'voter_contact_email':          voter_contact_email,
                'voter_contact_email_found':    voter_contact_email_found,
            }
            return results

        try:
            if positive_value_exists(read_only):
                query = VoterContactEmail.objects.using('readonly').all()
            else:
                query = VoterContactEmail.objects.all()
            query = query.filter(imported_by_voter_we_vote_id=imported_by_voter_we_vote_id)
            query = query.filter(email_address_text__iexact=email_address_text)
            list_of_voter_contact_emails = list(query)
            if len(list_of_voter_contact_emails) > 1:
                first_saved = False
                for one_voter_contact_email in list_of_voter_contact_emails:
                    if first_saved:
                        if positive_value_exists(read_only):
                            try:
                                voter_contact_email.delete()
                            except Exception as e:
                                status += "VOTER_CONTACT_EMAIL_DELETE-EXCEPTION: " + str(e) + ' '
                    else:
                        voter_contact_email = one_voter_contact_email
                        voter_contact_email_found = True
            elif len(list_of_voter_contact_emails) == 1:
                voter_contact_email = list_of_voter_contact_emails[0]
                voter_contact_email_found = True
            else:
                voter_contact_email_found = False
                status += "VOTER_CONTACT_EMAIL_NOT_FOUND "
        except Exception as e:
            voter_contact_email_found = False
            status += "VOTER_CONTACT_EMAIL_NOT_FOUND-EXCEPTION: " + str(e) + ' '
            success = False

        results = {
            'success':                          success,
            'status':                           status,
            'voter_contact_email':              voter_contact_email,
            'voter_contact_email_found':        voter_contact_email_found,
        }
        return results

    @staticmethod
    def retrieve_voter_contact_email_list(imported_by_voter_we_vote_id='', read_only=True):
        success = True
        status = ""
        voter_contact_email_list = []

        try:
            if positive_value_exists(read_only):
                list_query = VoterContactEmail.objects.using('readonly').all()
            else:
                list_query = VoterContactEmail.objects.all()
            if positive_value_exists(imported_by_voter_we_vote_id):
                list_query = list_query.filter(imported_by_voter_we_vote_id=imported_by_voter_we_vote_id)
            else:
                status += "MISSING_IMPORTED_BY_VOTER_WE_VOTE_ID "
                results = {
                    'success':                          False,
                    'status':                           status,
                    'voter_contact_email_list':         [],
                    'voter_contact_email_list_found':   False,
                }
                return results
            voter_contact_email_list = list(list_query)
            if len(voter_contact_email_list) > 0:
                status += "VOTER_CONTACT_EMAIL_LIST_FOUND "
                voter_contact_email_list_found = True
            else:
                status += "NO_VOTER_CONTACT_EMAILS_FOUND "
                voter_contact_email_list_found = False
        except Exception as e:
            voter_contact_email_list_found = False
            status += "VOTER_CONTACT_EMAIL_LIST_NOT_FOUND-EXCEPTION: " + str(e) + ' '
            success = False

        email_addresses_returned_list = []
        if voter_contact_email_list_found:
            for voter_contact_email in voter_contact_email_list:
                email_address_text_lower_case = voter_contact_email.email_address_text.lower()
                if email_address_text_lower_case not in email_addresses_returned_list:
                    email_addresses_returned_list.append(email_address_text_lower_case)

        results = {
            'success':                          success,
            'status':                           status,
            'email_addresses_returned_list':    email_addresses_returned_list,
            'voter_contact_email_list':         voter_contact_email_list,
            'voter_contact_email_list_found':   voter_contact_email_list_found,
        }
        return results

    @staticmethod
    def retrieve_voter_from_voter_device_id(voter_device_id, read_only=False):
        success = True
        status = ''
        voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)

        if not voter_id:
            status += "MISSING_VOTER_ID "
            success = False
            results = {
                'status':       status,
                'success':      success,
                'voter_found':  False,
                'voter_id':     0,
                'voter':        Voter(),
            }
            return results

        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id, read_only=read_only)
        status += results['status']
        if not results['success']:
            success = False
        if results['voter_found']:
            voter_on_stage = results['voter']
            voter_on_stage_found = True
            voter_id = results['voter_id']
        else:
            voter_on_stage = Voter()
            voter_on_stage_found = False
            voter_id = 0

        results = {
            'status':       status,
            'success':      success,
            'voter_found':  voter_on_stage_found,
            'voter_id':     voter_id,
            'voter':        voter_on_stage,
        }
        return results

    def fetch_we_vote_id_from_local_id(self, voter_id):
        results = self.retrieve_voter_by_id(voter_id, read_only=True)
        if results['voter_found']:
            voter = results['voter']
            return voter.we_vote_id
        else:
            return None

    def fetch_local_id_from_we_vote_id(self, voter_we_vote_id):
        results = self.retrieve_voter_by_we_vote_id(voter_we_vote_id, read_only=True)
        if results['voter_found']:
            voter = results['voter']
            return voter.id
        else:
            return 0

    @staticmethod
    def fetch_facebook_id_from_voter_we_vote_id(voter_we_vote_id):
        if positive_value_exists(voter_we_vote_id):
            facebook_manager = FacebookManager()
            facebook_id = facebook_manager.fetch_facebook_id_from_voter_we_vote_id(voter_we_vote_id)
        else:
            facebook_id = 0

        return facebook_id

    @staticmethod
    def fetch_twitter_id_from_voter_we_vote_id(voter_we_vote_id):
        if positive_value_exists(voter_we_vote_id):
            twitter_user_manager = TwitterUserManager()
            voter_twitter_id = twitter_user_manager.fetch_twitter_id_from_voter_we_vote_id(voter_we_vote_id)
        else:
            voter_twitter_id = ''

        return voter_twitter_id

    @staticmethod
    def fetch_twitter_handle_from_voter_we_vote_id(voter_we_vote_id):
        if positive_value_exists(voter_we_vote_id):
            twitter_user_manager = TwitterUserManager()
            voter_twitter_handle = twitter_user_manager.fetch_twitter_handle_from_voter_we_vote_id(voter_we_vote_id)
        else:
            voter_twitter_handle = ''

        return voter_twitter_handle

    def fetch_linked_organization_we_vote_id_from_local_id(self, voter_id):
        results = self.retrieve_voter_by_id(voter_id, read_only=True)
        if results['voter_found']:
            voter = results['voter']
            return voter.linked_organization_we_vote_id
        else:
            return None

    def fetch_linked_organization_we_vote_id_by_voter_we_vote_id(self, voter_we_vote_id):
        results = self.retrieve_voter_by_we_vote_id(voter_we_vote_id, read_only=True)
        if results['voter_found']:
            voter = results['voter']
            return voter.linked_organization_we_vote_id
        else:
            return None

    def fetch_voter_we_vote_id_by_linked_organization_we_vote_id(self, linked_organization_we_vote_id):
        results = self.retrieve_voter_by_organization_we_vote_id(linked_organization_we_vote_id, read_only=True)
        if results['voter_found']:
            voter = results['voter']
            return voter.we_vote_id
        else:
            return None

    @staticmethod
    def this_voter_has_first_or_last_name_saved(voter):
        try:
            if positive_value_exists(voter.first_name) or positive_value_exists(voter.last_name):
                return True
            else:
                return False
        except AttributeError:
            return False

    def repair_facebook_related_voter_caching(self, facebook_id):
        """
        Since cached facebook values are occasionally used, we want to
        make sure this cached facebook data is up-to-date.
        :param facebook_id:
        :return:
        """
        status = ""
        success = False
        filters = []
        voter_list_found = False
        voter_list_objects = []

        if not positive_value_exists(facebook_id):
            status += "FACEBOOK_ID_NOT_INCLUDED "
            error_results = {
                'status':               status,
                'success':              success,
            }
            return error_results

        facebook_manager = FacebookManager()
        facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter_from_facebook_id(
            facebook_id, read_only=True)
        if not facebook_link_results['facebook_link_to_voter_found']:
            # We don't have an official FacebookLinkToVoter, so we don't want to clean up any caching
            status += "FACEBOOK_LINK_TO_VOTER_NOT_FOUND-CACHING_REPAIR_NOT_EXECUTED "
        else:
            # Is there an official FacebookLinkToVoter for this Twitter account? If so, update the information.
            facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']

            # Loop through all the voters that have any of these fields set:
            # - voter.facebook_id
            # - voter.fb_username -- possibly in future. Not supported now
            try:
                voter_queryset = Voter.objects.all()

                # We want to find voters with *any* of these values
                new_filter = Q(facebook_id=facebook_id)
                filters.append(new_filter)

                # if positive_value_exists(facebook_user.fb_username):
                #     new_filter = Q(fb_username__iexact=facebook_user.fb_username)
                #     filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    voter_queryset = voter_queryset.filter(final_filters)

                voter_list_objects = list(voter_queryset)

                if len(voter_list_objects):
                    voter_list_found = True
                    status += 'FACEBOOK_RELATED_VOTERS_RETRIEVED '
                    success = True
                else:
                    status += 'NO_FACEBOOK_RELATED_VOTERS_RETRIEVED1 '
                    success = True
            except Voter.DoesNotExist:
                # No voters found. Not a problem.
                status += 'NO_FACEBOOK_RELATED_VOTERS_RETRIEVED2 '
                voter_list_objects = []
                success = True
            except Exception as e:
                handle_exception(e, logger=logger)
                status = 'FAILED repair_facebook_related_voter_caching ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

            if voter_list_found:
                # Loop through all voters found with facebook_id
                # If not the official FacebookLinkToVoter, then clear out those values.
                for voter in voter_list_objects:
                    if voter.we_vote_id != facebook_link_to_voter.voter_we_vote_id:
                        try:
                            voter.facebook_id = 0
                            voter.save()
                            status += "CLEARED_FACEBOOK_VALUES-voter.we_vote_id " \
                                      "" + voter.we_vote_id + " "
                        except Exception as e:
                            status += "COULD_NOT_CLEAR_FACEBOOK_VALUES-voter.we_vote_id " \
                                      "" + voter.we_vote_id + " "

            # Now make sure that the voter table has values for the voter linked with the
            # official FacebookLinkToVoter
            voter_results = self.retrieve_voter_by_we_vote_id(
                facebook_link_to_voter.voter_we_vote_id, read_only=False)
            if not voter_results['voter_found']:
                status += "REPAIR_FACEBOOK_CACHING-COULD_NOT_UPDATE_LINKED_VOTER "
            else:
                linked_voter = voter_results['voter']
                try:
                    save_voter = False
                    if linked_voter.facebook_id != facebook_id:
                        linked_voter.facebook_id = facebook_id
                        save_voter = True
                    if save_voter:
                        linked_voter.save()
                        status += "REPAIR_FACEBOOK_CACHING-SAVED_LINKED_VOTER "
                    else:
                        status += "REPAIR_FACEBOOK_CACHING-NO_NEED_TO_SAVE_LINKED_VOTER "

                except Exception as e:
                    status += "REPAIR_FACEBOOK_CACHING-COULD_NOT_SAVE_LINKED_VOTER: " + str(e) + " "

        results = {
            'status': status,
            'success': success,
        }
        return results

    def repair_twitter_related_voter_caching(self, twitter_user_id):
        """
        Since cached twitter values are occasionally used, we want to
        make sure this cached twitter data is up-to-date.
        :param twitter_user_id:
        :return:
        """
        status = ""
        success = False
        filters = []
        voter_list_found = False
        voter_list_objects = []

        if not positive_value_exists(twitter_user_id):
            status += "TWITTER_USER_ID_NOT_INCLUDED "
            error_results = {
                'status':               status,
                'success':              success,
            }
            return error_results

        twitter_user_manager = TwitterUserManager()
        twitter_link_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_twitter_user_id(
            twitter_user_id, read_only=True)
        if not twitter_link_results['twitter_link_to_voter_found']:
            # We don't have an official TwitterLinkToVoter, so we don't want to clean up any caching
            status += "TWITTER_LINK_TO_VOTER_NOT_FOUND-CACHING_REPAIR_NOT_EXECUTED "
        else:
            # Is there an official TwitterLinkToVoter for this Twitter account? If so, update the information.
            twitter_link_to_voter = twitter_link_results['twitter_link_to_voter']

            twitter_results = \
                twitter_user_manager.retrieve_twitter_user_locally_or_remotely(twitter_link_to_voter.twitter_id)

            if not twitter_results['twitter_user_found']:
                status += "REPAIR_TWITTER_CACHING-TWITTER_USER_NOT_FOUND "
            else:
                twitter_user = twitter_results['twitter_user']

                # Loop through all the voters that have any of these fields set:
                # - voter.twitter_id
                # - voter.twitter_screen_name
                try:
                    voter_queryset = Voter.objects.all()

                    # We want to find voters with *any* of these values
                    new_filter = Q(twitter_id=twitter_user_id)
                    filters.append(new_filter)

                    if positive_value_exists(twitter_user.twitter_handle):
                        new_filter = Q(twitter_screen_name__iexact=twitter_user.twitter_handle)
                        filters.append(new_filter)

                    # Add the first query
                    if len(filters):
                        final_filters = filters.pop()

                        # ...and "OR" the remaining items in the list
                        for item in filters:
                            final_filters |= item

                        voter_queryset = voter_queryset.filter(final_filters)

                    voter_list_objects = list(voter_queryset)

                    if len(voter_list_objects):
                        voter_list_found = True
                        status += 'REPAIR_TWITTER_CACHING-TWITTER_RELATED_VOTERS_RETRIEVED '
                        success = True
                    else:
                        status += 'REPAIR_TWITTER_CACHING-NO_TWITTER_RELATED_VOTERS_RETRIEVED1 '
                        success = True
                except Voter.DoesNotExist:
                    # No voters found. Not a problem.
                    status += 'REPAIR_TWITTER_CACHING-NO_TWITTER_RELATED_VOTERS_RETRIEVED2 '
                    voter_list_objects = []
                    success = True
                except Exception as e:
                    handle_exception(e, logger=logger)
                    status = 'FAILED repair_twitter_related_voter_caching ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

                if voter_list_found:
                    # Loop through all voters found with twitter_id and twitter_screen_name
                    # If not the official TwitterLinkToVoter, then clear out those values.
                    for voter in voter_list_objects:
                        if voter.we_vote_id != twitter_link_to_voter.voter_we_vote_id:
                            try:
                                voter.twitter_id = 0
                                voter.twitter_screen_name = ""
                                voter.save()
                                status += "CLEARED_TWITTER_VALUES-voter.we_vote_id " \
                                          "" + voter.we_vote_id + " "
                            except Exception as e:
                                status += "COULD_NOT_CLEAR_TWITTER_VALUES-voter.we_vote_id " \
                                          "" + voter.we_vote_id + " "

                # Now make sure that the voter table has values for the voter linked with the
                # official TwitterLinkToVoter
                voter_results = self.retrieve_voter_by_we_vote_id(
                    twitter_link_to_voter.voter_we_vote_id)
                if not voter_results['voter_found']:
                    status += "REPAIR_TWITTER_CACHING-COULD_NOT_UPDATE_LINKED_VOTER "
                else:
                    linked_voter = voter_results['voter']
                    try:
                        save_voter = False
                        if linked_voter.twitter_id != twitter_user_id:
                            linked_voter.twitter_id = twitter_user_id
                            save_voter = True
                        if linked_voter.twitter_screen_name != twitter_user.twitter_handle:
                            linked_voter.twitter_screen_name = twitter_user.twitter_handle
                            save_voter = True
                        if linked_voter.twitter_name != twitter_user.twitter_name:
                            linked_voter.twitter_name = twitter_user.twitter_name
                            save_voter = True
                        if linked_voter.twitter_profile_image_url_https != twitter_user.twitter_profile_image_url_https:
                            linked_voter.twitter_profile_image_url_https = twitter_user.twitter_profile_image_url_https
                            save_voter = True
                        if linked_voter.we_vote_hosted_profile_twitter_image_url_large != \
                                twitter_user.we_vote_hosted_profile_image_url_large:
                            linked_voter.we_vote_hosted_profile_twitter_image_url_large = \
                                twitter_user.we_vote_hosted_profile_image_url_large
                            save_voter = True
                        if linked_voter.we_vote_hosted_profile_twitter_image_url_medium != \
                                twitter_user.we_vote_hosted_profile_image_url_medium:
                            linked_voter.we_vote_hosted_profile_twitter_image_url_medium = \
                                twitter_user.we_vote_hosted_profile_image_url_medium
                            save_voter = True
                        if linked_voter.we_vote_hosted_profile_twitter_image_url_tiny != \
                                twitter_user.we_vote_hosted_profile_image_url_tiny:
                            linked_voter.we_vote_hosted_profile_twitter_image_url_tiny = \
                                twitter_user.we_vote_hosted_profile_image_url_tiny
                            save_voter = True
                        if linked_voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                            linked_voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
                            save_voter = True
                        if linked_voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                            if linked_voter.we_vote_hosted_profile_image_url_large != \
                                    twitter_user.we_vote_hosted_profile_image_url_large:
                                linked_voter.we_vote_hosted_profile_image_url_large = \
                                    twitter_user.we_vote_hosted_profile_image_url_large
                                save_voter = True
                            if linked_voter.we_vote_hosted_profile_image_url_medium != \
                                    twitter_user.we_vote_hosted_profile_image_url_medium:
                                linked_voter.we_vote_hosted_profile_image_url_medium = \
                                    twitter_user.we_vote_hosted_profile_image_url_medium
                                save_voter = True
                            if linked_voter.we_vote_hosted_profile_image_url_tiny != \
                                    twitter_user.we_vote_hosted_profile_image_url_tiny:
                                linked_voter.we_vote_hosted_profile_image_url_tiny = \
                                    twitter_user.we_vote_hosted_profile_image_url_tiny
                                save_voter = True

                        if save_voter:
                            linked_voter.save()
                            status += "REPAIR_TWITTER_CACHING-SAVED_LINKED_VOTER "
                        else:
                            status += "REPAIR_TWITTER_CACHING-NO_NEED_TO_SAVE_LINKED_VOTER "

                    except Exception as e:
                        status += "REPAIR_TWITTER_CACHING-COULD_NOT_SAVE_LINKED_VOTER: " + str(e) + " "

        results = {
            'status': status,
            'success': success,
        }
        return results

    @staticmethod
    def retrieve_voter_by_id(voter_id, read_only=False):
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, read_only=read_only)

    @staticmethod
    def retrieve_voter_by_email(email, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email=email, read_only=read_only)

    @staticmethod
    def retrieve_voter_by_we_vote_id(voter_we_vote_id, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, voter_we_vote_id=voter_we_vote_id, read_only=read_only)

    @staticmethod
    def retrieve_voter_by_twitter_request_token(twitter_request_token):
        voter_id = ''
        email = ''
        voter_we_vote_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email, voter_we_vote_id, twitter_request_token)

    # def retrieve_voter_by_facebook_id(self, facebook_id, read_only=False):
    #     voter_id = ''
    #     voter_manager = VoterManager()
    #     return voter_manager.retrieve_voter(voter_id, facebook_id=facebook_id, read_only=read_only)

    @staticmethod
    def retrieve_voter_by_facebook_id(facebook_id, read_only=False):
        voter_id = ''
        voter_we_vote_id = ''

        facebook_manager = FacebookManager()
        facebook_retrieve_results = facebook_manager.retrieve_facebook_link_to_voter(facebook_id, read_only=True)
        if facebook_retrieve_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_retrieve_results['facebook_link_to_voter']
            voter_we_vote_id = facebook_link_to_voter.voter_we_vote_id

        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, voter_we_vote_id=voter_we_vote_id, read_only=read_only)

    @staticmethod
    def retrieve_voter_by_facebook_id_old(facebook_id):
        """
        This method should only be used to heal old data.
        :param facebook_id:
        :return:
        """
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, facebook_id=facebook_id)

    @staticmethod
    def retrieve_voter_by_twitter_id(twitter_id, read_only=False):
        voter_id = ''
        voter_we_vote_id = ''

        twitter_user_manager = TwitterUserManager()
        twitter_retrieve_results = twitter_user_manager.retrieve_twitter_link_to_voter_from_twitter_user_id(
            twitter_id, read_only=True)
        if twitter_retrieve_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_retrieve_results['twitter_link_to_voter']
            voter_we_vote_id = twitter_link_to_voter.voter_we_vote_id

        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, voter_we_vote_id=voter_we_vote_id, read_only=read_only)

    @staticmethod
    def retrieve_voter_by_sms(normalized_sms_phone_number, read_only=False):
        voter_id = ''
        voter_we_vote_id = ''

        sms_manager = SMSManager()
        results = sms_manager.retrieve_voter_we_vote_id_from_normalized_sms_phone_number(normalized_sms_phone_number)
        if results['voter_we_vote_id_found']:
            voter_we_vote_id = results['voter_we_vote_id']

        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, voter_we_vote_id=voter_we_vote_id, read_only=read_only)

    @staticmethod
    def retrieve_voter_by_twitter_id_old(twitter_id):
        """
        This is a function we want to eventually deprecate as we move away from storing the twitter_id
        in the voter table
        :param twitter_id:
        :return:
        """
        voter_id = ''
        email = ''
        voter_we_vote_id = ''
        twitter_request_token = ''
        facebook_id = 0
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email, voter_we_vote_id, twitter_request_token, facebook_id,
                                            twitter_id)

    @staticmethod
    def retrieve_voter_by_organization_we_vote_id(organization_we_vote_id, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, organization_we_vote_id=organization_we_vote_id,
                                            read_only=read_only)

    @staticmethod
    def retrieve_voter_by_primary_email_we_vote_id(primary_email_we_vote_id, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, primary_email_we_vote_id=primary_email_we_vote_id,
                                            read_only=read_only)

    @staticmethod
    def retrieve_voter(
            voter_id, email='',
            voter_we_vote_id='',
            twitter_request_token='',
            facebook_id=0,
            twitter_id=0,
            sms='',
            organization_we_vote_id='',
            primary_email_we_vote_id='',
            read_only=False):
        voter_id = convert_to_int(voter_id)
        if not validate_email(email):
            # We do not want to search for an invalid email
            email = None
        if positive_value_exists(voter_we_vote_id):
            voter_we_vote_id = voter_we_vote_id.strip().lower()
        if positive_value_exists(organization_we_vote_id):
            organization_we_vote_id = organization_we_vote_id.strip().lower()
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        status = ""
        voter_on_stage = Voter()
        voter_found = False

        try:
            if positive_value_exists(voter_id):
                if read_only:
                    voter_on_stage = Voter.objects.using('readonly').get(id=voter_id)
                else:
                    voter_on_stage = Voter.objects.get(id=voter_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
                voter_found = True
                success = True
                status += "VOTER_RETRIEVED_BY_VOTER_ID "
            elif email != '' and email is not None:
                if read_only:
                    voter_queryset = Voter.objects.using('readonly').all()
                else:
                    voter_queryset = Voter.objects.all()
                voter_queryset = voter_queryset.filter(Q(email__iexact=email))
                voter_queryset = voter_queryset.order_by('-email_ownership_is_verified')  # Get verified entries first
                voter_list = list(voter_queryset[:1])
                if len(voter_list):
                    voter_on_stage = voter_list[0]
                    voter_id = voter_on_stage.id
                    voter_found = True
                    success = True
                    status += "VOTER_RETRIEVED_BY_VOTER_EMAIL "
                else:
                    voter_on_stage = Voter()
                    voter_id = 0
                    success = True
            elif positive_value_exists(voter_we_vote_id):
                if read_only:
                    voter_on_stage = Voter.objects.using('readonly').get(we_vote_id__iexact=voter_we_vote_id)
                else:
                    voter_on_stage = Voter.objects.get(we_vote_id__iexact=voter_we_vote_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
                voter_found = True
                success = True
                status += "VOTER_RETRIEVED_BY_VOTER_WE_VOTE_ID "
            elif positive_value_exists(twitter_request_token):
                if read_only:
                    voter_on_stage = Voter.objects.using('readonly').get(twitter_request_token=twitter_request_token)
                else:
                    voter_on_stage = Voter.objects.get(twitter_request_token=twitter_request_token)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
                voter_found = True
                success = True
                status += "VOTER_RETRIEVED_BY_TWITTER_REQUEST_TOKEN "
            elif positive_value_exists(facebook_id):
                # 2016-11-22 This is only used to heal data. When retrieving by facebook_id,
                # we use the FacebookLinkToVoter table
                # We try to keep voter.facebook_id up-to-date for rapid retrieve, but it is cached data and not master
                if read_only:
                    voter_on_stage = Voter.objects.using('readonly').get(facebook_id=facebook_id)
                else:
                    voter_on_stage = Voter.objects.get(facebook_id=facebook_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
                voter_found = True
                success = True
                status += "VOTER_RETRIEVED_BY_FACEBOOK_ID "
            elif positive_value_exists(twitter_id):
                # 2016-11-22 This is only used to heal data. When retrieving by twitter_id,
                # we use the TwitterLinkToVoter table
                # We try to keep voter.twitter_id up-to-date for rapid retrieve, but it is cached data and not master
                # We put this in an extra try block because there might be multiple voters with twitter_id
                try:
                    if read_only:
                        voter_on_stage = Voter.objects.using('readonly').get(twitter_id=twitter_id)
                    else:
                        voter_on_stage = Voter.objects.get(twitter_id=twitter_id)
                    # If still here, we found a single existing voter
                    voter_id = voter_on_stage.id
                    voter_found = True
                    success = True
                    status += "VOTER_RETRIEVED_BY_TWITTER_ID "
                except Voter.MultipleObjectsReturned as e:
                    # If there are multiple entries, we do not want to guess which one to use here
                    voter_on_stage = Voter()
                    voter_id = 0
                    success = False
                except Voter.DoesNotExist as e:
                    voter_id = 0
                    error_result = True
                    exception_does_not_exist = True
                    success = True
            elif positive_value_exists(organization_we_vote_id):
                if read_only:
                    voter_on_stage = Voter.objects.using('readonly').get(
                        linked_organization_we_vote_id__iexact=organization_we_vote_id)
                else:
                    voter_on_stage = Voter.objects.get(
                        linked_organization_we_vote_id__iexact=organization_we_vote_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
                voter_found = True
                success = True
                status += "VOTER_RETRIEVED_BY_ORGANIZATION_WE_VOTE_ID "
            elif positive_value_exists(primary_email_we_vote_id):
                if read_only:
                    voter_on_stage = Voter.objects.using('readonly').get(
                        primary_email_we_vote_id__iexact=primary_email_we_vote_id)
                else:
                    voter_on_stage = Voter.objects.get(primary_email_we_vote_id__iexact=primary_email_we_vote_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
                voter_found = True
                success = True
                status += "VOTER_RETRIEVED_BY_PRIMARY_EMAIL_WE_VOTE_ID "
            else:
                voter_id = 0
                error_result = True
                success = False
        except Voter.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            voter_id = 0
        except Voter.DoesNotExist as e:
            error_result = True
            exception_does_not_exist = True
            success = True
            status += "VOTER_NOT_FOUND "
            voter_id = 0

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_found':              voter_found,
            'voter_id':                 voter_id,
            'voter':                    voter_on_stage,
        }
        return results

    @staticmethod
    def retrieve_voter_list_with_emails():
        """
        Retrieve list of voter that are registered for newsletter

        :return result: dictionary with status and list of voters
        """
        voter_list = list()
        result = dict()
        status = 'NO_VOTER_LIST'
        # get query set of voters with verified emails
        # voter_queryset = Voter.objects.extra(where=["notification_settings_flags & %s = 1",
        #                                             "email_ownership_is_verified = True"],
        #                                      params=[NOTIFICATION_NEWSLETTER_OPT_IN])
        voter_queryset = Voter.objects.filter(email_ownership_is_verified=True)
        voter_queryset = voter_queryset.exclude((Q(email__isnull=True) | Q(email='')))

        if voter_queryset.exists():
            voter_list.extend(voter_queryset)

        result = {
            'status':   status,
            'voter_list':   voter_list,
        }

        return result

    @staticmethod
    def retrieve_voter_list_by_permissions(
            is_admin=False,
            is_analytics_admin=False,
            is_partner_organization=False,
            is_political_data_manager=False,
            is_political_data_viewer=False,
            is_verified_volunteer=False,
            is_voter_manager=False,
            or_filter=True):
        """
        Retrieve list of voters based on the permissions they have been granted

        :return result: dictionary with status and list of voters
        """
        voter_list = list()
        status = ''

        if not positive_value_exists(is_admin) \
                and not positive_value_exists(is_analytics_admin) \
                and not positive_value_exists(is_partner_organization) \
                and not positive_value_exists(is_political_data_manager) \
                and not positive_value_exists(is_political_data_viewer) \
                and not positive_value_exists(is_verified_volunteer) \
                and not positive_value_exists(is_voter_manager):
            status += "MUST_SPECIFY_ONE_PERMISSION_TYPE "
            result = {
                'status': status,
                'voter_list': voter_list,
            }
            return result

        voter_queryset = Voter.objects.all()
        voter_queryset = voter_queryset.order_by('first_name')

        voter_raw_filters = []
        if positive_value_exists(is_admin):
            new_voter_filter = Q(is_admin=True)
            voter_raw_filters.append(new_voter_filter)
        if positive_value_exists(is_analytics_admin):
            new_voter_filter = Q(is_analytics_admin=True)
            voter_raw_filters.append(new_voter_filter)
        if positive_value_exists(is_partner_organization):
            new_voter_filter = Q(is_partner_organization=True)
            voter_raw_filters.append(new_voter_filter)
        if positive_value_exists(is_political_data_manager):
            new_voter_filter = Q(is_political_data_manager=True)
            voter_raw_filters.append(new_voter_filter)
        if positive_value_exists(is_political_data_viewer):
            new_voter_filter = Q(is_political_data_viewer=True)
            voter_raw_filters.append(new_voter_filter)
        if positive_value_exists(is_verified_volunteer):
            new_voter_filter = Q(is_verified_volunteer=True)
            voter_raw_filters.append(new_voter_filter)
        if positive_value_exists(is_voter_manager):
            new_voter_filter = Q(is_voter_manager=True)
            voter_raw_filters.append(new_voter_filter)

        if len(voter_raw_filters):
            final_voter_filters = voter_raw_filters.pop()

            for item in voter_raw_filters:
                if positive_value_exists(or_filter):
                    # "OR" the remaining items in the list
                    final_voter_filters |= item
                else:
                    # "AND" the remaining items in the list
                    final_voter_filters &= item

            voter_queryset = voter_queryset.filter(final_voter_filters)

        if voter_queryset.exists():
            voter_list.extend(voter_queryset)

        result = {
            'status':       status,
            'voter_list':   voter_list,
        }
        return result

    @staticmethod
    def retrieve_voter_list_by_name(first_name, last_name):
        """
        Retrieve list of voters based on name match

        :return result: dictionary with status and list of voters
        """
        voter_list = list()
        status = 'LIST'

        voter_queryset = Voter.objects.all().filter(first_name=first_name).filter(last_name=last_name)

        if voter_queryset.exists():
            voter_list.extend(voter_queryset)

        result = {
            'status':       status,
            'voter_list':   voter_list,
        }
        return result

    @staticmethod
    def retrieve_voter_list_by_we_vote_id_list(voter_we_vote_id_list=[], read_only=True):
        status = ''
        voter_list = []

        try:
            if read_only:
                query = Voter.objects.using('readonly').filter(we_vote_id__in=voter_we_vote_id_list)
            else:
                query = Voter.objects.filter(we_vote_id__in=voter_we_vote_id_list)
            voter_list = list(query)
            success = True
            voter_list_found = True
            status += "VOTER_LIST_RETRIEVED_BY_VOTER_WE_VOTE_ID_LIST "
        except Exception as e:
            success = False
            voter_list_found = False
            status += "VOTER_LIST_NOT_RETRIEVED_BY_VOTER_WE_VOTE_ID_LIST: " + str(e) + " "

        result = {
            'status':           status,
            'success':          success,
            'voter_list':       voter_list,
            'voter_list_found': voter_list_found,
        }
        return result

    @staticmethod
    def retrieve_voter_plan_list(google_civic_election_id=0, voter_we_vote_id='', read_only=True):
        success = True
        status = ""
        voter_plan_list = []

        try:
            if positive_value_exists(read_only):
                list_query = VoterPlan.objects.using('readonly').all()
            else:
                list_query = VoterPlan.objects.all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(voter_we_vote_id):
                list_query = list_query.filter(voter_we_vote_id=voter_we_vote_id)
            else:
                list_query = list_query.filter(show_to_public=True)
            list_query = list_query.order_by('-date_last_changed')
            voter_plan_list = list_query[:25]
            voter_plan_list_found = True
            status += "VOTER_PLAN_LIST_FOUND "
        except Exception as e:
            voter_plan_list_found = False
            status += "VOTER_PLAN_LIST_NOT_FOUND-EXCEPTION: " + str(e) + ' '
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'voter_plan_list':          voter_plan_list,
            'voter_plan_list_found':    voter_plan_list_found,
        }
        return results

    @staticmethod
    def create_voter_with_voter_device_id(voter_device_id):
        logger.info("create_voter_with_voter_device_id(voter_device_id)")

    @staticmethod
    def clear_out_abandoned_voter_records():
        # We will need a method that identifies and deletes abandoned voter records that don't have enough information
        #  to ever be used
        logger.info("clear_out_abandoned_voter_records")

    @staticmethod
    def remove_voter_cached_email_entries_from_email_address_object(email_address_object):
        status = ""
        success = False

        voter_manager = VoterManager()
        if positive_value_exists(email_address_object.normalized_email_address):
            voter_found_by_email_results = voter_manager.retrieve_voter_by_email(
                email_address_object.normalized_email_address)
            if voter_found_by_email_results['voter_found']:
                voter_found_by_email = voter_found_by_email_results['voter']

                # Wipe this voter's email values...
                try:
                    voter_found_by_email.email = None
                    voter_found_by_email.primary_email_we_vote_id = None
                    voter_found_by_email.email_ownership_is_verified = False
                    voter_found_by_email.save()
                    status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_EMAIL "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_EMAIL: " + str(e) + " "

        if positive_value_exists(email_address_object.we_vote_id):
            voter_by_primary_email_results = voter_manager.retrieve_voter_by_primary_email_we_vote_id(
                email_address_object.we_vote_id)
            if voter_by_primary_email_results['voter_found']:
                voter_found_by_primary_email_we_vote_id = voter_by_primary_email_results['voter']

                # Wipe this voter's email values...
                try:
                    voter_found_by_primary_email_we_vote_id.email = None
                    voter_found_by_primary_email_we_vote_id.primary_email_we_vote_id = None
                    voter_found_by_primary_email_we_vote_id.email_ownership_is_verified = False
                    voter_found_by_primary_email_we_vote_id.save()
                    status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID: " + str(e) + " "

        results = {
            'success': success,
            'status': status,
        }
        return results

    @staticmethod
    def remove_voter_cached_sms_entries_from_sms_phone_number(sms_phone_number):
        status = ""
        success = False

        voter_manager = VoterManager()
        if positive_value_exists(sms_phone_number.normalized_sms_phone_number):
            voter_found_by_sms_results = voter_manager.retrieve_voter_by_sms(
                sms_phone_number.normalized_sms_phone_number)
            if voter_found_by_sms_results['voter_found']:
                voter_found_by_sms = voter_found_by_sms_results['voter']

                # Wipe this voter's sms values...
                try:
                    voter_found_by_sms.sms = None
                    voter_found_by_sms.primary_sms_we_vote_id = None
                    voter_found_by_sms.sms_ownership_is_verified = False
                    voter_found_by_sms.save()
                    status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_SMS "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_SMS: " + str(e) + " "

        if positive_value_exists(sms_phone_number.we_vote_id):
            voter_by_primary_email_results = voter_manager.retrieve_voter_by_primary_email_we_vote_id(
                sms_phone_number.we_vote_id)
            if voter_by_primary_email_results['voter_found']:
                voter_found_by_primary_email_we_vote_id = voter_by_primary_email_results['voter']

                # Wipe this voter's email values...
                try:
                    voter_found_by_primary_email_we_vote_id.email = None
                    voter_found_by_primary_email_we_vote_id.primary_email_we_vote_id = None
                    voter_found_by_primary_email_we_vote_id.email_ownership_is_verified = False
                    voter_found_by_primary_email_we_vote_id.save()
                    status += "ABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_CLEAN_OUT_VOTER_FOUND_BY_PRIMARY_EMAIL_WE_VOTE_ID: " + str(e) + " "

        results = {
            'success': success,
            'status': status,
        }
        return results

    @staticmethod
    def save_facebook_user_values(
            voter,
            facebook_auth_response,
            cached_facebook_profile_image_url_https=None,
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        # 1/11/23: This is now only called from voter_cache_facebook_images_process() within an SQS job
        status = ''
        try:
            hosted_profile_facebook_saved = False
            hosted_profile_image_saved = False

            if positive_value_exists(facebook_auth_response.facebook_user_id):
                voter.facebook_id = facebook_auth_response.facebook_user_id
            if positive_value_exists(facebook_auth_response.facebook_first_name):
                voter.first_name = facebook_auth_response.facebook_first_name
            if positive_value_exists(facebook_auth_response.facebook_middle_name):
                voter.middle_name = facebook_auth_response.facebook_middle_name
            if positive_value_exists(facebook_auth_response.facebook_last_name):
                voter.last_name = facebook_auth_response.facebook_last_name
            if positive_value_exists(cached_facebook_profile_image_url_https):
                voter.facebook_profile_image_url_https = cached_facebook_profile_image_url_https
            else:
                voter.facebook_profile_image_url_https = facebook_auth_response.facebook_profile_image_url_https
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                hosted_profile_facebook_saved = True
                voter.we_vote_hosted_profile_facebook_image_url_large = we_vote_hosted_profile_image_url_large
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                voter.we_vote_hosted_profile_facebook_image_url_medium = we_vote_hosted_profile_image_url_medium
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                voter.we_vote_hosted_profile_facebook_image_url_tiny = we_vote_hosted_profile_image_url_tiny
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN or not \
                    positive_value_exists(voter.profile_image_type_currently_active):
                voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_FACEBOOK
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                if positive_value_exists(we_vote_hosted_profile_image_url_large):
                    hosted_profile_image_saved = True
                    voter.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                    voter.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                    voter.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny

            # voter_readwrite = Voter.objects.get(id=voter.id)
            # voter_readonly = Voter.objects.using('readonly').get(id=voter.id)
            # logger.error(
            #     '(Ok) save_facebook_user_values  voter_readonly %s  voter_readwrite %s' %
            #     (voter_readonly.we_vote_hosted_profile_image_url_large,
            #      voter_readwrite.we_vote_hosted_profile_image_url_large))

            logger.error(
                '(Ok) save_facebook_user_values %s %s (%s)(%s) at %s active %s  %s  %s  %s' %
                (voter.first_name, voter.last_name, voter.we_vote_id, facebook_auth_response.facebook_user_id,
                 voter.date_last_changed, voter.profile_image_type_currently_active,
                 we_vote_hosted_profile_image_url_large, hosted_profile_facebook_saved, hosted_profile_image_saved))
            voter.save()
            success = True
            status += "SAVED_FACEBOOK_USER_VALUES "
        except Exception as e:
            status += "UNABLE_TO_SAVE_FACEBOOK_USER_VALUES: " + str(e) + " "
            success = False

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    @staticmethod
    def save_facebook_user_values_from_dict(
            voter,
            facebook_user_dict,
            cached_facebook_profile_image_url_https=None,
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        try:
            if 'id' in facebook_user_dict:
                voter.facebook_id = facebook_user_dict['id']
            if cached_facebook_profile_image_url_https:
                voter.facebook_profile_image_url_https = cached_facebook_profile_image_url_https
            elif 'profile_image_url_https' in facebook_user_dict:
                voter.facebook_profile_image_url_https = facebook_user_dict['profile_image_url_https']
            if 'fb_username' in facebook_user_dict:
                voter.fb_username = facebook_user_dict['fb_username']
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                voter.we_vote_hosted_profile_facebook_image_url_large = we_vote_hosted_profile_image_url_large
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                voter.we_vote_hosted_profile_facebook_image_url_medium = we_vote_hosted_profile_image_url_medium
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                voter.we_vote_hosted_profile_facebook_image_url_tiny = we_vote_hosted_profile_image_url_tiny
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_FACEBOOK
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                if positive_value_exists(we_vote_hosted_profile_image_url_large):
                    voter.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                    voter.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                    voter.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny

            voter.save()
            success = True
            status = "SAVED_FACEBOOK_USER_VALUES_FROM_DICT "
        except Exception as e:
            status = "UNABLE_TO_SAVE_FACEBOOK_USER_VALUES_FROM_DICT: " + str(e) + " "
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    @staticmethod
    def save_twitter_user_values(
            voter,
            twitter_user_object,
            cached_twitter_profile_image_url_https=None,
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        """
        This is used to store the cached values in the voter record after authentication.
        Please also see import_export_twitter/models.py TwitterAuthResponse->save_twitter_auth_values
        :param voter:
        :param twitter_user_object:
        :param cached_twitter_profile_image_url_https:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny:
        :return:
        """
        status = ""
        try:
            voter_to_save = False
            # We try to keep voter.twitter_id up-to-date for rapid retrieve, but it is cached data and not master
            if hasattr(twitter_user_object, "id") and positive_value_exists(twitter_user_object.id):
                voter.twitter_id = twitter_user_object.id
                voter_to_save = True
            # 'id_str': '132728535',
            # 'utc_offset': 32400,
            # 'description': "Cars, Musics, Games, Electronics, toys, food, etc... I'm just a typical boy!",
            # 'profile_image_url': 'http://a1.twimg.com/profile_images/1213351752/_2_2__normal.jpg',
            if positive_value_exists(cached_twitter_profile_image_url_https):
                voter.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                voter_to_save = True
            elif hasattr(twitter_user_object, "profile_image_url") and \
                    positive_value_exists(twitter_user_object.profile_image_url):
                voter.twitter_profile_image_url_https = twitter_user_object.profile_image_url
                voter_to_save = True
            # Always update to latest Twitter image
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                voter.we_vote_hosted_profile_twitter_image_url_large = we_vote_hosted_profile_image_url_large
                voter_to_save = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                voter.we_vote_hosted_profile_twitter_image_url_medium = we_vote_hosted_profile_image_url_medium
                voter_to_save = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                voter.we_vote_hosted_profile_twitter_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                voter_to_save = True
            # If a profile image preference hasn't been saved, make Twitter the default
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
                voter_to_save = True
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                if positive_value_exists(we_vote_hosted_profile_image_url_large):
                    voter.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                    voter_to_save = True
                if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                    voter.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                    voter_to_save = True
                if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                    voter.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                    voter_to_save = True
            # 'profile_background_image_url': 'http://a2.twimg.com/a/1294785484/images/themes/theme15/bg.png',
            # 'username': 'jaeeeee',
            if hasattr(twitter_user_object, "username") and positive_value_exists(twitter_user_object.username):
                voter.twitter_screen_name = twitter_user_object.username
                voter_to_save = True
            # 'lang': 'en',
            if hasattr(twitter_user_object, "name") and positive_value_exists(twitter_user_object.name):
                voter.twitter_name = twitter_user_object.name
                voter_to_save = True
            # 'url': 'http://www.carbonize.co.kr',
            # 'time_zone': 'Seoul',
            if voter_to_save:
                voter.save()
            success = True
            status += "SAVED_VOTER_TWITTER_VALUES_FROM_TWITTER_USER_VALUES "
        except Exception as e:
            status += "UNABLE_TO_SAVE_VOTER_TWITTER_VALUES_FROM_TWITTER_USER_VALUES: " + str(e) + " "
            success = False

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    @staticmethod
    def save_twitter_user_values_from_twitter_auth_response(
            voter,
            twitter_auth_response,
            cached_twitter_profile_image_url_https=None,
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        """
        This is used to store the cached values in the voter record from the twitter_auth_response object once
        voter agrees to a merge.
        NOTE 2016-10-21 Do NOT save TwitterAuthResponse values -- only photo and "soft" data
        :param voter:
        :param twitter_auth_response:
        :param cached_twitter_profile_image_url_https:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny:
        :return:
        """
        try:
            voter_to_save = False
            # We try to keep voter.twitter_id up-to-date for rapid retrieve, but it is cached data and not master
            if hasattr(twitter_auth_response, "twitter_id") and positive_value_exists(twitter_auth_response.twitter_id):
                voter.twitter_id = twitter_auth_response.twitter_id
                voter_to_save = True
            # 'id_str': '132728535',
            # 'utc_offset': 32400,
            # 'description': "Cars, Musics, Games, Electronics, toys, food, etc... I'm just a typical boy!",
            # 'profile_image_url': 'http://a1.twimg.com/profile_images/1213351752/_2_2__normal.jpg',
            if positive_value_exists(cached_twitter_profile_image_url_https):
                voter.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                voter_to_save = True
            elif hasattr(twitter_auth_response, "twitter_profile_image_url_https") and \
                    positive_value_exists(twitter_auth_response.twitter_profile_image_url_https):
                voter.twitter_profile_image_url_https = twitter_auth_response.twitter_profile_image_url_https
                voter_to_save = True
            # Always update to latest Twitter image
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                voter.we_vote_hosted_profile_twitter_image_url_large = we_vote_hosted_profile_image_url_large
                voter_to_save = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                voter.we_vote_hosted_profile_twitter_image_url_medium = we_vote_hosted_profile_image_url_medium
                voter_to_save = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                voter.we_vote_hosted_profile_twitter_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                voter_to_save = True
            # If a profile image preference hasn't been saved, make Twitter the default
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
                voter_to_save = True
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                if positive_value_exists(we_vote_hosted_profile_image_url_large):
                    voter.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                    voter_to_save = True
                if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                    voter.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                    voter_to_save = True
                if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                    voter.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                    voter_to_save = True
            # 'profile_background_image_url': 'http://a2.twimg.com/a/1294785484/images/themes/theme15/bg.png',
            # 'username': 'jaeeeee',
            if hasattr(twitter_auth_response, "twitter_screen_name") and \
                    positive_value_exists(twitter_auth_response.twitter_screen_name):
                voter.twitter_screen_name = twitter_auth_response.twitter_screen_name
                voter_to_save = True
            # 'lang': 'en',
            if hasattr(twitter_auth_response, "twitter_name") and \
                    positive_value_exists(twitter_auth_response.twitter_name):
                voter.twitter_name = twitter_auth_response.twitter_name
                voter_to_save = True
            # 'url': 'http://www.carbonize.co.kr',
            # 'time_zone': 'Seoul',

            if voter_to_save:
                voter.save()
            success = True
            status = "SAVED_VOTER_TWITTER_VALUES_FROM_TWITTER_AUTH_RESPONSE "
        except Exception as e:
            status = "UNABLE_TO_SAVE_VOTER_TWITTER_VALUES_FROM_TWITTER_AUTH_RESPONSE: " + str(e) + " "
            success = False

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    @staticmethod
    def save_twitter_user_values_from_dict(
            voter,
            twitter_user_dict,
            cached_twitter_profile_image_url_https=None,
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        status = ""
        try:
            # 'id': 132728535,
            if 'id' in twitter_user_dict:
                voter.twitter_id = twitter_user_dict['id']
            # 'id_str': '132728535',
            # 'utc_offset': 32400,
            # 'description': "Cars, Musics, Games, Electronics, toys, food, etc... I'm just a typical boy!",
            # 'profile_image_url': 'http://a1.twimg.com/profile_images/1213351752/_2_2__normal.jpg',
            if cached_twitter_profile_image_url_https:
                voter.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
            elif 'profile_image_url' in twitter_user_dict:
                voter.twitter_profile_image_url_https = twitter_user_dict['profile_image_url']
            # 'profile_background_image_url': 'http://a2.twimg.com/a/1294785484/images/themes/theme15/bg.png',
            # 'username': 'jaeeeee',
            if 'username' in twitter_user_dict:
                voter.twitter_screen_name = twitter_user_dict['username']
            if 'name' in twitter_user_dict:
                voter.twitter_name = twitter_user_dict['name']
            # Always update to latest Twitter image
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                voter.we_vote_hosted_profile_twitter_image_url_large = we_vote_hosted_profile_image_url_large
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                voter.we_vote_hosted_profile_twitter_image_url_medium = we_vote_hosted_profile_image_url_medium
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                voter.we_vote_hosted_profile_twitter_image_url_tiny = we_vote_hosted_profile_image_url_tiny
            # If a profile image preference hasn't been saved, make Twitter the default
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
            if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                if positive_value_exists(we_vote_hosted_profile_image_url_large):
                    voter.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                    voter.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                    voter.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny

            # 'lang': 'en',
            # 'name': 'Jae Jung Chung',
            # 'url': 'http://www.carbonize.co.kr',
            # 'time_zone': 'Seoul',
            voter.save()
            success = True
            status += "SAVED_VOTER_TWITTER_VALUES_FROM_USER_DICT_VALUES "
        except Exception as e:
            status += "UNABLE_TO_SAVE_VOTER_TWITTER_VALUES_FROM_USER_DICT_VALUES: " + str(e) + " "
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    @staticmethod
    def update_contact_email_augmented_list_not_found(
            checked_against_open_people=None,
            checked_against_sendgrid=None,
            checked_against_snovio=None,
            checked_against_targetsmart=None,
            email_address_text_list=None):
        success = True
        status = ""
        contact_email_augmented_list_updated = False
        number_updated = 0

        try:
            list_query = ContactEmailAugmented.objects.all()
            list_query = list_query.filter(email_address_text__in=email_address_text_list)

            if checked_against_open_people:
                number_updated = list_query.update(checked_against_open_people=True,
                                                   date_last_checked_against_open_people=now())
                contact_email_augmented_list_updated = True
            elif checked_against_sendgrid:
                number_updated = list_query.update(checked_against_sendgrid=True,
                                                   date_last_checked_against_sendgrid=now())
                contact_email_augmented_list_updated = True
            elif checked_against_snovio:
                number_updated = list_query.update(checked_against_snovio=True,
                                                   date_last_checked_against_snovio=now())
                contact_email_augmented_list_updated = True
            elif checked_against_targetsmart:
                number_updated = list_query.update(checked_against_targetsmart=True,
                                                   date_last_checked_against_targetsmart=now())
                contact_email_augmented_list_updated = True
            status += "CONTACT_EMAIL_AUGMENTED_LIST_NUMBER_UPDATED: " + str(number_updated) + ' '
        except Exception as e:
            status += "CONTACT_EMAIL_AUGMENTED_LIST_NOT_UPDATED: " + str(e) + ' '
            success = False

        results = {
            'success':                              success,
            'status':                               status,
            'contact_email_augmented_list_updated': contact_email_augmented_list_updated,
            'number_updated':                       number_updated,
        }
        return results

    def update_issues_interface_status(self, voter_we_vote_id, number_of_issues_followed):
        """
        Based on the number of issues the voter has followed, and set the
        BALLOT_INTRO_ISSUES_COMPLETED interface_status_flag to true if 5 or more issues have been followed.
        If not, set to false.

        :param voter_we_vote_id:
        :param number_of_issues_followed:
        :return:
        """
        status = ""
        success = False

        results = self.retrieve_voter_by_we_vote_id(voter_we_vote_id)
        if results['voter_found']:
            voter = results['voter']

            try:
                # If the voter is currently following the required number of issues or greater, mark the
                #  requirement as complete
                if number_of_issues_followed >= INTERFACE_STATUS_THRESHOLD_ISSUES_FOLLOWED:
                    # Update the setting if not true
                    if not voter.is_interface_status_flag_set(BALLOT_INTRO_ISSUES_COMPLETED):
                        voter.set_interface_status_flags(BALLOT_INTRO_ISSUES_COMPLETED)
                        voter.save()
                else:
                    # Update the setting if true
                    if voter.is_interface_status_flag_set(BALLOT_INTRO_ISSUES_COMPLETED):
                        voter.unset_interface_status_flags(BALLOT_INTRO_ISSUES_COMPLETED)
                        voter.save()
                success = True
            except Exception as e:
                pass

        results = {
            'status': status,
            'success': success,
        }
        return results

    def update_organizations_interface_status(self, voter_we_vote_id, number_of_organizations_followed):
        """
        Based on the number of organizations the voter has followed, and set the
        BALLOT_INTRO_ORGANIZATIONS_COMPLETED interface_status_flag to true if 5 or more issues have been followed.
        If not, set to false.

        :param voter_we_vote_id:
        :param number_of_organizations_followed:
        :return:
        """
        status = ""
        success = False

        results = self.retrieve_voter_by_we_vote_id(voter_we_vote_id)
        if results['voter_found']:
            voter = results['voter']

            try:
                # If the voter is currently following the required number of organizations or greater, mark the
                #  requirement as complete
                if number_of_organizations_followed >= INTERFACE_STATUS_THRESHOLD_ORGANIZATIONS_FOLLOWED:
                    # Update the setting if flag is false
                    if not voter.is_interface_status_flag_set(BALLOT_INTRO_ORGANIZATIONS_COMPLETED):
                        voter.set_interface_status_flags(BALLOT_INTRO_ORGANIZATIONS_COMPLETED)
                        voter.save()
                else:
                    # Update the setting if flag is true
                    if voter.is_interface_status_flag_set(BALLOT_INTRO_ORGANIZATIONS_COMPLETED):
                        voter.unset_interface_status_flags(BALLOT_INTRO_ORGANIZATIONS_COMPLETED)
                success = True
            except Exception as e:
                pass

        results = {
            'status': status,
            'success': success,
        }
        return results

    def reset_voter_image_details(self, voter, twitter_profile_image_url_https=None,
                                  facebook_profile_image_url_https=None):
        """
        Reset Voter image details from we voter image
        :param voter:
        :param twitter_profile_image_url_https:
        :param facebook_profile_image_url_https:
        :return:
        """
        value_changed = False
        voter_results = self.retrieve_voter_by_we_vote_id(voter.we_vote_id)
        voter = voter_results['voter']
        if voter_results['voter_found']:
            if positive_value_exists(twitter_profile_image_url_https):
                voter.twitter_profile_image_url_https = twitter_profile_image_url_https
                voter.we_vote_hosted_profile_twitter_image_url_large = None
                voter.we_vote_hosted_profile_twitter_image_url_medium = None
                voter.we_vote_hosted_profile_twitter_image_url_tiny = None
                if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN:
                    voter.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
                if voter.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                    voter.we_vote_hosted_profile_image_url_large = None
                    voter.we_vote_hosted_profile_image_url_medium = None
                    voter.we_vote_hosted_profile_image_url_tiny = None
                value_changed = True
            if positive_value_exists(facebook_profile_image_url_https):
                voter.facebook_profile_image_url_https = facebook_profile_image_url_https
                value_changed = True

            if value_changed:
                voter.save()
                success = True
                status = "RESET_VOTER_IMAGE_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_IN_VOTER_IMAGE_DETAILS"
        else:
            success = False
            status = "VOTER_NOT_FOUND"

        results = {
            'success':  success,
            'status':   status,
            'voter':    voter
        }
        return results

    def update_voter_twitter_details(
            self,
            twitter_id='',
            twitter_dict={},
            cached_twitter_profile_image_url_https='',
            we_vote_hosted_profile_image_url_large='',
            we_vote_hosted_profile_image_url_medium='',
            we_vote_hosted_profile_image_url_tiny=''):
        """
        Update existing voter entry with details retrieved from the Twitter API
        :param twitter_id:
        :param twitter_dict:
        :param cached_twitter_profile_image_url_https:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny:
        :return:
        """
        voter_results = self.retrieve_voter_by_twitter_id(twitter_id)
        voter = voter_results['voter']
        if voter_results['voter_found']:
            # Twitter user already exists so update twitter user details
            results = self.save_twitter_user_values_from_dict(
                voter, twitter_dict,
                cached_twitter_profile_image_url_https=cached_twitter_profile_image_url_https,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
        else:
            results = {
                'success':  False,
                'status':   'VOTER_NOT_FOUND',
                'voter':    voter
            }
        return results

    def update_voter_photos(self, voter_id, facebook_profile_image_url_https, facebook_photo_variable_exists):
        """
        Used by voterPhotoSave - this function is deprecated. Please do not extend.
        :param voter_id:
        :param facebook_profile_image_url_https:
        :param facebook_photo_variable_exists:
        :return:
        """
        results = self.retrieve_voter(voter_id)

        if results['voter_found']:
            voter = results['voter']

            try:
                if facebook_photo_variable_exists:
                    voter.facebook_profile_image_url_https = facebook_profile_image_url_https
                voter.save()
                status = "SAVED_VOTER_PHOTOS"
                success = True
            except Exception as e:
                status = "UNABLE_TO_SAVE_VOTER_PHOTOS"
                success = False
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        else:
            # If here, we were unable to find pre-existing Voter
            status = "UNABLE_TO_FIND_VOTER_FOR_UPDATE_VOTER_PHOTOS"
            voter = Voter()
            success = False

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    def update_voter_by_id(
            self,
            voter_id,
            facebook_email=False,
            facebook_profile_image_url_https=False,
            first_name=False,
            middle_name=False,
            last_name=False,
            interface_status_flags=False,
            flag_integer_to_set=False,
            flag_integer_to_unset=False,
            notification_settings_flags=False,
            notification_flag_integer_to_set=False,
            notification_flag_integer_to_unset=False,
            profile_image_type_currently_active=False,
            twitter_profile_image_url_https=False,
            we_vote_hosted_profile_facebook_image_url_large=False,
            we_vote_hosted_profile_facebook_image_url_medium=False,
            we_vote_hosted_profile_facebook_image_url_tiny=False,
            we_vote_hosted_profile_image_url_large=False,
            we_vote_hosted_profile_image_url_medium=False,
            we_vote_hosted_profile_image_url_tiny=False,
            we_vote_hosted_profile_twitter_image_url_large=False,
            we_vote_hosted_profile_twitter_image_url_medium=False,
            we_vote_hosted_profile_twitter_image_url_tiny=False,
            we_vote_hosted_profile_uploaded_image_url_large=False,
            we_vote_hosted_profile_uploaded_image_url_medium=False,
            we_vote_hosted_profile_uploaded_image_url_tiny=False,
    ):
        voter_updated = False
        success = False
        results = self.retrieve_voter(voter_id)
        status = results['status']

        if results['voter_found']:
            voter = results['voter']

            results = self.update_voter_by_object(
                voter,
                facebook_email=facebook_email,
                facebook_profile_image_url_https=facebook_profile_image_url_https,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                interface_status_flags=interface_status_flags,
                flag_integer_to_set=flag_integer_to_set,
                flag_integer_to_unset=flag_integer_to_unset,
                notification_settings_flags=notification_settings_flags,
                notification_flag_integer_to_set=notification_flag_integer_to_set,
                notification_flag_integer_to_unset=notification_flag_integer_to_unset,
                profile_image_type_currently_active=profile_image_type_currently_active,
                twitter_profile_image_url_https=twitter_profile_image_url_https,
                we_vote_hosted_profile_facebook_image_url_large=we_vote_hosted_profile_facebook_image_url_large,
                we_vote_hosted_profile_facebook_image_url_medium=we_vote_hosted_profile_facebook_image_url_medium,
                we_vote_hosted_profile_facebook_image_url_tiny=we_vote_hosted_profile_facebook_image_url_tiny,
                we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny,
                we_vote_hosted_profile_twitter_image_url_large=we_vote_hosted_profile_twitter_image_url_large,
                we_vote_hosted_profile_twitter_image_url_medium=we_vote_hosted_profile_twitter_image_url_medium,
                we_vote_hosted_profile_twitter_image_url_tiny=we_vote_hosted_profile_twitter_image_url_tiny,
                we_vote_hosted_profile_uploaded_image_url_large=we_vote_hosted_profile_uploaded_image_url_large,
                we_vote_hosted_profile_uploaded_image_url_medium=we_vote_hosted_profile_uploaded_image_url_medium,
                we_vote_hosted_profile_uploaded_image_url_tiny=we_vote_hosted_profile_uploaded_image_url_tiny,
            )
            success = results['success']
            status += results['status']
            voter_updated = results['voter_updated']
        else:
            voter = Voter()
            status += "UPDATE_VOTER_BY_ID-COULD_NOT_RETRIEVE_VOTER "

        results = {
            'status': status,
            'success': success,
            'voter': voter,
            'voter_updated': voter_updated,
        }
        return results

    def update_voter_name_by_object(self, voter, first_name=False, last_name=False):
        return self.update_voter_by_object(
            voter,
            first_name=first_name,
            last_name=last_name)

    @staticmethod
    def update_voter_by_object(
            voter,
            facebook_email=False,
            facebook_profile_image_url_https=False,
            first_name=False,
            middle_name=False,
            last_name=False,
            interface_status_flags=False,
            flag_integer_to_set=False,
            flag_integer_to_unset=False,
            notification_settings_flags=False,
            notification_flag_integer_to_set=False,
            notification_flag_integer_to_unset=False,
            profile_image_type_currently_active=False,
            twitter_profile_image_url_https=False,
            we_vote_hosted_profile_facebook_image_url_large=False,
            we_vote_hosted_profile_facebook_image_url_medium=False,
            we_vote_hosted_profile_facebook_image_url_tiny=False,
            we_vote_hosted_profile_image_url_large=False,
            we_vote_hosted_profile_image_url_medium=False,
            we_vote_hosted_profile_image_url_tiny=False,
            we_vote_hosted_profile_twitter_image_url_large=False,
            we_vote_hosted_profile_twitter_image_url_medium=False,
            we_vote_hosted_profile_twitter_image_url_tiny=False,
            we_vote_hosted_profile_uploaded_image_url_large=False,
            we_vote_hosted_profile_uploaded_image_url_medium=False,
            we_vote_hosted_profile_uploaded_image_url_tiny=False,
            data_to_preserve=False):
        status = ""
        voter_updated = False

        try:
            test_we_vote_id = voter.we_vote_id
            voter_found = True
        except AttributeError as e:
            status += "UPDATE_VOTER_BY_OBJECT-VOTER_NOT_FOUND "
            handle_record_not_saved_exception(e, logger=logger)
            voter_found = False

        if voter_found:
            try:
                should_save_voter = False
                if facebook_email is not False:
                    voter.facebook_email = facebook_email
                    should_save_voter = True
                if facebook_profile_image_url_https is not False:
                    voter.facebook_profile_image_url_https = facebook_profile_image_url_https
                    should_save_voter = True
                if first_name is not False:
                    voter.first_name = first_name
                    should_save_voter = True
                if middle_name is not False:
                    voter.middle_name = middle_name
                    should_save_voter = True
                if last_name is not False:
                    voter.last_name = last_name
                    should_save_voter = True
                if profile_image_type_currently_active is not False:
                    voter.profile_image_type_currently_active = profile_image_type_currently_active
                    should_save_voter = True
                if twitter_profile_image_url_https is not False:
                    voter.last_name = last_name
                    should_save_voter = True
                if we_vote_hosted_profile_facebook_image_url_large is not False:
                    voter.we_vote_hosted_profile_facebook_image_url_large = \
                        we_vote_hosted_profile_facebook_image_url_large
                    should_save_voter = True
                if we_vote_hosted_profile_facebook_image_url_medium is not False:
                    voter.we_vote_hosted_profile_facebook_image_url_medium = \
                        we_vote_hosted_profile_facebook_image_url_medium
                    should_save_voter = True
                if we_vote_hosted_profile_facebook_image_url_tiny is not False:
                    voter.we_vote_hosted_profile_facebook_image_url_tiny = \
                        we_vote_hosted_profile_facebook_image_url_tiny
                    should_save_voter = True
                if we_vote_hosted_profile_image_url_large is not False:
                    voter.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                    should_save_voter = True
                if we_vote_hosted_profile_image_url_medium is not False:
                    voter.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                    should_save_voter = True
                if we_vote_hosted_profile_image_url_tiny is not False:
                    voter.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                    should_save_voter = True
                if we_vote_hosted_profile_twitter_image_url_large is not False:
                    voter.we_vote_hosted_profile_twitter_image_url_large = \
                        we_vote_hosted_profile_twitter_image_url_large
                    should_save_voter = True
                if we_vote_hosted_profile_twitter_image_url_medium is not False:
                    voter.we_vote_hosted_profile_twitter_image_url_medium = \
                        we_vote_hosted_profile_twitter_image_url_medium
                    should_save_voter = True
                if we_vote_hosted_profile_twitter_image_url_tiny is not False:
                    voter.we_vote_hosted_profile_twitter_image_url_tiny = we_vote_hosted_profile_twitter_image_url_tiny
                    should_save_voter = True
                if we_vote_hosted_profile_uploaded_image_url_large is not False:
                    voter.we_vote_hosted_profile_uploaded_image_url_large = \
                        we_vote_hosted_profile_uploaded_image_url_large
                    should_save_voter = True
                if we_vote_hosted_profile_uploaded_image_url_medium is not False:
                    voter.we_vote_hosted_profile_uploaded_image_url_medium = \
                        we_vote_hosted_profile_uploaded_image_url_medium
                    should_save_voter = True
                if we_vote_hosted_profile_uploaded_image_url_tiny is not False:
                    voter.we_vote_hosted_profile_uploaded_image_url_tiny = \
                        we_vote_hosted_profile_uploaded_image_url_tiny
                    should_save_voter = True
                if positive_value_exists(data_to_preserve):
                    voter.data_to_preserve = data_to_preserve
                    should_save_voter = True
                if interface_status_flags is not False:
                    # If here, we set the entire value to a new positive integer
                    voter.interface_status_flags = interface_status_flags
                    should_save_voter = True
                else:
                    # If here, we flip or un-flip one or more bits
                    if flag_integer_to_set is not False:
                        voter.set_interface_status_flags(flag_integer_to_set)
                        should_save_voter = True
                    if flag_integer_to_unset is not False:
                        voter.unset_interface_status_flags(flag_integer_to_unset)
                        should_save_voter = True
                if notification_settings_flags is not False:
                    # If here, we set the entire value to a new positive integer
                    voter.notification_settings_flags = notification_settings_flags
                    should_save_voter = True
                else:
                    # If here, we flip or un-flip one or more bits
                    if notification_flag_integer_to_set is not False:
                        voter.set_notification_settings_flags(notification_flag_integer_to_set)
                        should_save_voter = True
                    if notification_flag_integer_to_unset is not False:
                        voter.unset_notification_settings_flags(notification_flag_integer_to_unset)
                        should_save_voter = True
                if should_save_voter:
                    voter.save()
                    voter_updated = True
                status += "UPDATED_VOTER "
                success = True
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                status += "UNABLE_TO_UPDATE_VOTER: " + str(e) + " "
                success = False
                voter_updated = False

        else:
            # If here, we were unable to find pre-existing Voter
            status = "UNABLE_TO_FIND_VOTER_FOR_UPDATE_VOTER "
            voter = Voter()
            success = False
            voter_updated = False

        results = {
            'status':                       status,
            'success':                      success,
            'voter':                        voter,
            'voter_updated':                voter_updated,
        }
        return results

    @staticmethod
    def update_voter_email_ownership_verified(voter, email_address_object):
        status = ""
        success = True  # Assume success unless we hit a problem
        voter_updated = False
        voter_manager = VoterManager()

        try:
            should_save_voter = False
            if email_address_object.email_ownership_is_verified:
                voter.primary_email_we_vote_id = email_address_object.we_vote_id
                voter.email = email_address_object.normalized_email_address
                voter.email_ownership_is_verified = True
                should_save_voter = True
            else:
                status += "EMAIL_OWNERSHIP_NOT_VERIFIED "

            if should_save_voter:
                voter.save()
                voter_updated = True
                status += "UPDATED_VOTER_EMAIL_OWNERSHIP "
            else:
                status += "NO_SAVE_TO_VOTER "

            success = True
        except Exception as e:
            status += "UNABLE_TO_UPDATE_INCOMING_VOTER: " + str(e) + " "
            # We tried to update the incoming voter found but got an error, so we retrieve voter's based on
            #  normalized_email address, and then by primary_email_we_vote_id
            remove_cached_results = voter_manager.remove_voter_cached_email_entries_from_email_address_object(
                email_address_object)
            status += remove_cached_results['status']

            # And now, try to save again
            try:
                voter.primary_email_we_vote_id = email_address_object.we_vote_id
                voter.email = email_address_object.normalized_email_address
                voter.email_ownership_is_verified = True
                voter.save()
                voter_updated = True
                status += "UPDATED_VOTER_EMAIL_OWNERSHIP2 "
                success = True
            except Exception as e:
                success = False
                status += "UNABLE_TO_UPDATE_VOTER_EMAIL_OWNERSHIP2: " + str(e) + ' '

        results = {
            'status': status,
            'success': success,
            'voter': voter,
            'voter_updated': voter_updated,
        }
        return results

    @staticmethod
    def update_voter_sms_ownership_verified(voter, sms_phone_number):
        status = ""
        success = True  # Assume success unless we hit a problem
        voter_updated = False
        voter_manager = VoterManager()

        try:
            should_save_voter = False
            if sms_phone_number.sms_ownership_is_verified:
                voter.primary_sms_we_vote_id = sms_phone_number.we_vote_id
                voter.normalized_sms_phone_number = sms_phone_number.normalized_sms_phone_number
                voter.sms_ownership_is_verified = True
                should_save_voter = True

            if should_save_voter:
                voter.save()
                voter_updated = True
            status += "UPDATED_VOTER_SMS_OWNERSHIP "
            success = True
        except Exception as e:
            status += "UNABLE_TO_UPDATE_INCOMING_VOTER: " + str(e) + ' '
            # We tried to update the incoming voter found but got an error, so we retrieve voter's based on
            #  normalized_email address, and then by primary_email_we_vote_id
            remove_cached_results = voter_manager.remove_voter_cached_sms_entries_from_sms_phone_number(
                sms_phone_number)
            status += remove_cached_results['status']

            # And now, try to save again
            try:
                voter.primary_sms_we_vote_id = sms_phone_number.we_vote_id
                voter.normalized_sms_phone_number = sms_phone_number.normalized_sms_phone_number
                voter.sms_ownership_is_verified = True
                voter.save()
                voter_updated = True
                status += "UPDATED_VOTER_EMAIL_OWNERSHIP2 "
                success = True
            except Exception as e:
                success = False
                status += "UNABLE_TO_UPDATE_VOTER_EMAIL_OWNERSHIP2: " + str(e) + ' '

        results = {
            'status':           status,
            'success':          success,
            'voter':            voter,
            'voter_updated':    voter_updated,
        }
        return results

    @staticmethod
    def update_voter_with_facebook_link_verified(voter, facebook_user_id, facebook_email):
        should_save_voter = False
        voter_updated = False

        try:
            voter.facebook_id = facebook_user_id
            voter.facebook_email = facebook_email
            should_save_voter = True

            if should_save_voter:
                voter.save()
                voter_updated = True
            status = "UPDATED_VOTER_WITH_FACEBOOK_LINK"
            success = True
        except Exception as e:
            status = "UNABLE_TO_UPDATE_VOTER_WITH_FACEBOOK_LINK"
            success = False
            voter_updated = False

        results = {
            'status': status,
            'success': success,
            'voter': voter,
            'voter_updated': voter_updated,
        }
        return results

    @staticmethod
    def update_voter_with_twitter_link_verified(voter, twitter_id):
        """
        I think this was originally built with the idea that we would cache the Twitter ID in the
        voter record for quick lookup. As of 2016-10-29 I don't think we can cache the twitter_id reliably
        because of the complexities of merging accounts and the chances for errors. So we should deprecate this.
        :param voter:
        :param twitter_id:
        :return:
        """
        should_save_voter = False
        voter_updated = False

        try:
            if positive_value_exists(twitter_id):
                voter.twitter_id = twitter_id
                should_save_voter = True

            if should_save_voter:
                voter.save()
                voter_updated = True
                status = "UPDATED_VOTER_WITH_TWITTER_LINK"
                success = True
            else:
                status = "NOT_UPDATED_VOTER_WITH_TWITTER_LINK"
                success = False
        except Exception as e:
            status = "UNABLE_TO_UPDATE_VOTER_WITH_TWITTER_LINK"
            success = False
            voter_updated = False

        results = {
            'status': status,
            'success': success,
            'voter': voter,
            'voter_updated': voter_updated,
        }
        return results


class Voter(AbstractBaseUser):
    """
    A fully featured User model with admin-compliant permissions that uses
    a full-length email field as the username.

    No fields are required, since at its very simplest, we only need the voter_id based on a voter_device_id.
    """

    MultipleObjectsReturned = None
    DoesNotExist = None

    def __repr__(self):
        return '__repr__ for Voter'

    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our voter info with other
    # organizations running the we_vote server
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "voter", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_org_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=True, db_index=True)
    # When a person using an organization's Twitter handle signs in, we create a voter account. This is how
    #  we link the voter account to the organization.
    linked_organization_we_vote_id = models.CharField(
        verbose_name="we vote id for linked organization", max_length=255, null=True, unique=True, db_index=True)

    # Redefine the basic fields that would normally be defined in User
    # username = models.CharField(unique=True, max_length=50, validators=[alphanumeric])  # Increase max_length to 255
    # We cache the email here for quick lookup, but the official email address for the voter
    # is referenced by primary_email_we_vote_id and stored in the EmailAddress table
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True, null=True, blank=True)
    primary_email_we_vote_id = models.CharField(
        verbose_name="we vote id for primary email for this voter", max_length=255, null=True, blank=True, unique=True)
    # This "email_ownership_is_verified" is a copy of the master data in EmailAddress.email_ownership_is_verified
    email_ownership_is_verified = models.BooleanField(default=False)
    normalized_sms_phone_number = models.CharField(max_length=50, null=True, blank=True)
    primary_sms_we_vote_id = models.CharField(
        verbose_name="we vote id for primary phone number", max_length=255, null=True, blank=True, unique=True)
    sms_ownership_is_verified = models.BooleanField(default=False)
    first_name = models.CharField(verbose_name='first name', max_length=255, null=True, blank=True)
    middle_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(verbose_name='last name', max_length=255, null=True, blank=True)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    # friend_count helps us quickly identify voters who have friends
    friend_count = models.PositiveIntegerField(default=None, null=True)
    # The Federal Information Processing Standard (FIPS) code is a five-digit code that
    # uniquely identifies counties and county equivalents in the United States.
    # The first two digits of the code identify the state,
    # and the last three digits identify the county or county equivalent.
    county_fips_code = models.CharField(max_length=5, null=True)
    county_name = models.CharField(max_length=255, null=True)
    # Lat/Long is used for statistics. For returning ballot data, use VoterAddress Lat/Long
    latitude = models.FloatField(default=None, null=True)
    longitude = models.FloatField(default=None, null=True)
    state_code_for_display = models.CharField(max_length=2, null=True, blank=True)
    state_code_for_display_hidden = models.BooleanField(default=False)
    state_code_for_display_updated = models.BooleanField(default=False)  # Meant to be a transitory field during update

    # Once a voter takes a position, follows an org or other save-worthy data, mark this true
    data_to_preserve = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_analytics_admin = models.BooleanField(default=False)
    is_partner_organization = models.BooleanField(default=False)
    is_political_data_manager = models.BooleanField(default=False)
    is_political_data_viewer = models.BooleanField(default=False)
    is_signed_in_cached = models.BooleanField(default=None, null=True, db_index=True)  # For analytics reports
    is_verified_volunteer = models.BooleanField(default=False)
    is_voter_manager = models.BooleanField(default=False)

    # Facebook session information
    facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    fb_username = models.CharField(max_length=50, validators=[alphanumeric], null=True)
    facebook_profile_image_url_https = models.TextField(
        verbose_name='url of image from facebook', blank=True, null=True)

    # Twitter session information
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, blank=True)
    twitter_name = models.CharField(verbose_name="display name from twitter", max_length=255, null=True, blank=True)
    twitter_screen_name = models.CharField(
        verbose_name='twitter screen name / handle', max_length=255, null=True, unique=False)
    twitter_profile_image_url_https = models.TextField(verbose_name='url of logo from twitter', blank=True, null=True)
    # Image we are using as the profile photo (could be sourced from Twitter, Facebook or uploaded directly by voter)
    we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    # Which voter image is currently active?
    profile_image_type_currently_active = models.CharField(
        max_length=11, choices=PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES, default=PROFILE_IMAGE_TYPE_UNKNOWN)
    # Image for voter from Facebook
    we_vote_hosted_profile_facebook_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_tiny = models.TextField(blank=True, null=True)
    # Image for voter from Twitter
    we_vote_hosted_profile_twitter_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_tiny = models.TextField(blank=True, null=True)
    # Image uploaded to We Vote from voter
    we_vote_hosted_profile_uploaded_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_tiny = models.TextField(blank=True, null=True)

    twitter_request_token = models.TextField(verbose_name='twitter request token', null=True, blank=True)
    twitter_request_secret = models.TextField(verbose_name='twitter request secret', null=True, blank=True)
    twitter_voters_access_token = models.TextField(verbose_name='twitter access token', null=True, blank=True)
    twitter_voters_access_token_secret = models.TextField(verbose_name='twitter access token secret', null=True, blank=True)
    twitter_connection_active = models.BooleanField(default=False)

    # What notification settings has the voter chosen? This is using a series of bits.
    # Default new voters is determined by NOTIFICATION_SETTINGS_FLAGS_DEFAULT (set above)
    notification_settings_flags = models.PositiveIntegerField(default=NOTIFICATION_SETTINGS_FLAGS_DEFAULT)

    # Interface Status Flags is a positive integer, when represented as a stream of bits,
    # each bit maps to a status of a variable's boolean value
    # for eg. the first bit(rightmost bit) = 1 means, the SUPPORT_OPPOSE_MODAL_SHOWN_BIT has been shown
    # more constants at top of this file
    interface_status_flags = models.PositiveIntegerField(verbose_name="interface status flags", default=0)

    # This is how we keep track of whether we have run certain updates on voter records
    #  to the latest defaults, for example
    # For example, have we updated a voter's notification_settings_flags after adding new feature?
    # We update the default value for maintenance_status_flags for new voters with MAINTENANCE_STATUS_FLAGS_COMPLETED
    #  since we updated the NOTIFICATION_SETTINGS_FLAGS_DEFAULT to match what we want after all the maintenance
    #  tasks have run.
    # As all previous voters are updated with the newest NOTIFICATION_SETTINGS defaults,
    #  we AND maintenance_status_flags with the new MAINTENANCE_STATUS_FLAGS_TASK_... so it ends up matching
    #  MAINTENANCE_STATUS_FLAGS_COMPLETED = MAINTENANCE_STATUS_FLAGS_TASK_ONE + MAINTENANCE_STATUS_FLAGS_TASK_TWO
    # See process_maintenance_status_flags in /voter/controllers.py
    maintenance_status_flags = models.PositiveIntegerField(default=MAINTENANCE_STATUS_FLAGS_COMPLETED)

    # The unique ID of the election this voter is currently looking at. (Provided by Google Civic)
    # DALE 2015-10-29 We are replacing this with looking up the value in the ballot_items table, and then
    # storing in cookie
    # current_google_civic_election_id = models.PositiveIntegerField(
    #     verbose_name="google civic election id", null=True, unique=False)
    voter_issues_lookup_updated = models.BooleanField(default=False)

    objects = VoterManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Since we need to store a voter based solely on voter_device_id, no values are required

    # We override the save function to allow for the email field to be empty. If NOT empty, email must be unique.
    # We also want to auto-generate we_vote_id
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()  # Hopefully reduces junk to ""
            if self.email != "":  # If it's not blank
                if not validate_email(self.email):  # ...make sure it is a valid email
                    # If it isn't a valid email, don't save the value as an email -- just save a blank field
                    self.email = None
        if self.email == "":
            self.email = None
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            self.generate_new_we_vote_id()
        super(Voter, self).save(*args, **kwargs)

    def generate_new_we_vote_id(self):
        # ...generate a new id
        site_unique_id_prefix = fetch_site_unique_id_prefix()
        next_local_integer = fetch_next_we_vote_id_voter_integer()
        # "wv" = We Vote
        # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
        # "voter" = tells us this is a unique id for an org
        # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
        self.we_vote_id = "wv{site_unique_id_prefix}voter{next_integer}".format(
            site_unique_id_prefix=site_unique_id_prefix,
            next_integer=next_local_integer,
        )
        # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        return

    def get_full_name(self, real_name_only=False):
        """

        :param real_name_only: Only return a real name if we have it. Otherwise return blank. If false, make up a
        placeholder name.
        :return:
        """
        allow_placeholder_name = not real_name_only

        full_name = self.first_name if positive_value_exists(self.first_name) else ''
        full_name += " " if positive_value_exists(self.first_name) and positive_value_exists(self.last_name) else ''
        full_name += self.last_name if positive_value_exists(self.last_name) else ''

        if not positive_value_exists(full_name):
            if positive_value_exists(self.twitter_name):
                full_name = self.twitter_name
            elif allow_placeholder_name:
                full_name = self.twitter_screen_name

        if not positive_value_exists(full_name):
            if positive_value_exists(self.email) and allow_placeholder_name:
                full_name = self.email.split("@", 1)[0]

        if not positive_value_exists(full_name):
            if allow_placeholder_name and positive_value_exists(self.we_vote_id):
                full_name = "Voter-" + self.we_vote_id

        return full_name

    def get_short_name(self):
        # return self.first_name
        # The user is identified by their email address
        return self.email

    def voter_can_retrieve_account(self):
        if positive_value_exists(self.email):
            return True
        else:
            return False

    def __str__(self):              # __unicode__ on Python 2
        if self.has_valid_email():
            return str(self.email)
        elif positive_value_exists(self.twitter_screen_name):
            return str(self.twitter_screen_name)
        else:
            return str(self.get_full_name())

    @staticmethod
    def has_perm(perm, obj=None):
        """
        Does the user have a specific permission?
        """
        # Simplest possible answer: Yes, always
        return True

    @staticmethod
    def has_module_perms(app_label):
        """
        Does the user have permissions to view the app `app_label`?
        """
        # Simplest possible answer: Yes, always
        return True

    def is_opt_in_newsletter(self):
        if self.is_notification_status_flag_set(NOTIFICATION_NEWSLETTER_OPT_IN):
            return True
        return False

    @property
    def is_staff(self):
        """
        Is the user a member of staff?
        """
        # Simplest possible answer: All admins are staff
        return self.is_admin

    def voter_photo_url(self):
        if self.we_vote_hosted_profile_image_url_large:
            return self.we_vote_hosted_profile_image_url_large
        elif self.we_vote_hosted_profile_uploaded_image_url_large:
            return self.we_vote_hosted_profile_uploaded_image_url_large
        elif self.we_vote_hosted_profile_facebook_image_url_large:
            return self.we_vote_hosted_profile_facebook_image_url_large
        elif self.we_vote_hosted_profile_twitter_image_url_large:
            return self.we_vote_hosted_profile_twitter_image_url_large
        elif self.facebook_profile_image_url_https:
            return self.facebook_profile_image_url_https
        elif self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https
        return ''

    def is_signed_in(self):
        # Can't include signed_in_with_apple here since, the iOS version should be specific to one device
        # We start with signed_in_with_email and signed_in_with_sms_phone_number since they don't require another
        # database call
        if self.signed_in_with_email() or \
                self.signed_in_with_sms_phone_number() or \
                self.signed_in_with_apple() or \
                self.signed_in_facebook() or \
                self.signed_in_twitter():
            return True
        return False

    def signed_in_facebook(self):
        facebook_manager = FacebookManager()
        facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(0, self.we_vote_id, read_only=True)
        if facebook_link_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']
            if positive_value_exists(facebook_link_to_voter.facebook_user_id):
                return True
        return False

    @staticmethod
    def signed_in_google():
        return False

    def signed_in_twitter(self):
        twitter_user_manager = TwitterUserManager()
        twitter_link_results = twitter_user_manager.retrieve_twitter_link_to_voter(0, self.we_vote_id, read_only=True)
        if twitter_link_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_link_results['twitter_link_to_voter']
            if positive_value_exists(twitter_link_to_voter.twitter_id):
                return True
        return False

    def signed_in_with_apple(self):
        try:
            apple_object = AppleUser.objects.using('readonly').get(voter_we_vote_id__iexact=self.we_vote_id)
            return True
        except AppleUser.DoesNotExist:
            return False
        except Exception as e:
            return False

    def signed_in_with_email(self):
        # TODO DALE Consider merging with has_email_with_verified_ownership
        verified_email_found = (positive_value_exists(self.email) or
                                positive_value_exists(self.primary_email_we_vote_id)) and \
                               self.email_ownership_is_verified
        if verified_email_found:
            return True
        return False

    def has_valid_email(self):
        if self.has_email_with_verified_ownership():
            return True
        return False

    def signed_in_with_sms_phone_number(self):
        verified_sms_found = (positive_value_exists(self.normalized_sms_phone_number) or
                              positive_value_exists(self.primary_sms_we_vote_id)) and \
                              self.sms_ownership_is_verified
        return verified_sms_found

    def has_data_to_preserve(self):
        # Does this voter record have any values associated in this table that are unique
        if self.has_email_with_verified_ownership() or self.signed_in_twitter() or self.signed_in_facebook():
            return True
        elif self.data_to_preserve:
            # Has any important data been stored in other tables attached to this voter account?
            return True

        return False

    def has_email_with_verified_ownership(self):
        # TODO DALE Consider merging with signed_in_with_email
        # Because there might be some cases where we can't update the email because of caching issues
        # (voter.email must be unique, and there was a bug where we tried to wipe out voter.email by setting
        # it to "", which failed), we only require email_ownership_is_verified to be true
        # if positive_value_exists(self.email) and self.email_ownership_is_verified:
        if self.email_ownership_is_verified:
            return True
        return False

    # for every bit set in flag_integer_to_set,
    # corresponding bits in self.interface_status_flags will be set
    def set_interface_status_flags(self, flag_integer_to_set):
        self.interface_status_flags |= flag_integer_to_set

    # for every bit set in flag_integer_to_unset,
    # corresponding bits in self.interface_status_flags will be unset
    def unset_interface_status_flags(self, flag_integer_to_unset):
        self.interface_status_flags = ~flag_integer_to_unset & self.interface_status_flags

    def is_interface_status_flag_set(self, flag_integer):
        """
        Is the interface_status flag (or flags) specified by flag_integer set for this voter?
        :param flag_integer:
        :return:
        """
        return positive_value_exists(flag_integer & self.interface_status_flags)

    def set_notification_settings_flags(self, notification_flag_integer_to_set):
        self.notification_settings_flags |= notification_flag_integer_to_set

    def unset_notification_settings_flags(self, notification_flag_integer_to_unset):
        self.notification_settings_flags = ~notification_flag_integer_to_unset & self.notification_settings_flags

    def is_notification_status_flag_set(self, flag_integer):
        """
        Is the notification_status flag (or flags) specified by flag_integer set for this voter?
        :param flag_integer:
        :return:
        """
        return positive_value_exists(flag_integer & self.notification_settings_flags)


# VoterChangeLog
EMAIL_ADDRESS_TABLE = 'EmailAddress'
VOTER_ADDRESS_TABLE = 'VoterAddress'
VOTER_TABLE = 'Voter'
CHANGE_TABLE_CHOICES = (
    (EMAIL_ADDRESS_TABLE, 'EmailAddress'),
    (VOTER_ADDRESS_TABLE, 'VoterAddress'),
    (VOTER_TABLE, 'Voter'),
)


class VoterChangeLog(models.Model):
    """
    For keeping track of settings changes either by voter or by system. (i.e., setting new default values)
    """
    # The voter who had a change
    voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    date_of_change = models.DateTimeField(null=True, auto_now=True)
    change_table = models.CharField(max_length=50, choices=CHANGE_TABLE_CHOICES, default=VOTER_TABLE)
    change_field = models.CharField(max_length=255, null=True)
    change_description = models.CharField(max_length=255, null=True)
    is_system_update = models.BooleanField(default=False)

    BOOLEAN = 'B'
    INTEGER = 'I'
    STRING = 'S'
    TEXT = 'T'
    VALUE_TYPE_CHOICES = (
        (BOOLEAN, 'Boolean'),
        (INTEGER, 'Integer'),
        (STRING, 'String'),
        (TEXT, 'Text'),
    )
    value_type = models.CharField("value_type", max_length=1, choices=VALUE_TYPE_CHOICES, default=STRING)

    text_value_from = models.TextField(null=True)
    text_value_to = models.TextField(null=True)

    string_value_from = models.CharField(max_length=255, null=True)
    string_value_to = models.CharField(max_length=255, null=True)

    integer_value_from = models.BigIntegerField(null=True)
    integer_value_to = models.BigIntegerField(null=True)

    boolean_value_from = models.BooleanField(default=None, null=True)
    boolean_value_to = models.BooleanField(default=None, null=True)


class VoterContactEmail(models.Model):
    """
    One contact imported from third-party voter address book. Voter may delete at any time.
    """
    objects = None
    city = models.CharField(max_length=255, default=None, null=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True, db_index=True)
    display_name = models.CharField(max_length=255, default=None, null=True)
    email_address_text = models.TextField(null=True, blank=True, db_index=True)
    first_name = models.CharField(max_length=255, default=None, null=True)
    google_contact_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    google_date_last_updated = models.DateTimeField(null=True)
    google_display_name = models.CharField(max_length=255, default=None, null=True)
    google_first_name = models.CharField(max_length=255, default=None, null=True)
    google_last_name = models.CharField(max_length=255, default=None, null=True)
    has_data_from_google_people_api = models.BooleanField(default=False)
    ignore_contact = models.BooleanField(default=False)
    imported_by_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    is_friend = models.BooleanField(default=False)
    last_name = models.CharField(max_length=255, default=None, null=True)
    middle_name = models.CharField(max_length=255, default=None, null=True)
    state_code = models.CharField(max_length=2, default=None, null=True, db_index=True)
    voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    zip_code = models.CharField(max_length=10, default=None, null=True)
    phone_number = models.CharField(verbose_name="contact phone number", max_length=64, null=True, blank=True)
    api_type = models.CharField(verbose_name="apple google android etc", max_length=16, default="google")

# class VoterContactSMS(models.Model):
#     """
#     One contact imported from third-party voter address book. Voter may delete at any time.
#     """
#     date_last_changed = models.DateTimeField(null=True, auto_now=True, db_index=True)
#     google_contact_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
#     google_date_last_updated = models.DateTimeField(null=True)
#     google_display_name = models.CharField(max_length=255, default=None, null=True)
#     google_first_name = models.CharField(max_length=255, default=None, null=True)
#     google_last_name = models.CharField(max_length=255, default=None, null=True)
#     ignore_contact = models.BooleanField(default=False)
#     imported_by_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
#     normalized_sms_phone_number = models.CharField(max_length=50, default=None, null=True)
#     state_code = models.CharField(max_length=2, default=None, null=True, db_index=True)


class ContactEmailAugmented(models.Model):
    """
    What information have we retrieved to augment this one email address?
    """
    objects = None
    checked_against_open_people = models.BooleanField(db_index=True, default=False)
    checked_against_sendgrid = models.BooleanField(db_index=True, default=False)
    checked_against_snovio = models.BooleanField(db_index=True, default=False)
    checked_against_targetsmart = models.BooleanField(db_index=True, default=False)
    date_last_checked_against_open_people = models.DateTimeField(null=True)
    date_last_checked_against_sendgrid = models.DateTimeField(null=True)
    date_last_checked_against_snovio = models.DateTimeField(null=True)
    date_last_checked_against_targetsmart = models.DateTimeField(null=True)
    email_address_text = models.TextField(db_index=True, null=False, unique=True)
    has_known_bounces = models.BooleanField(default=False)
    has_mx_or_a_record = models.BooleanField(default=False)
    has_suspected_bounces = models.BooleanField(default=False)
    is_invalid = models.BooleanField(db_index=True, default=False)
    is_verified = models.BooleanField(db_index=True, default=False)
    open_people_first_name = models.CharField(max_length=255, null=True)
    open_people_last_name = models.CharField(max_length=255, null=True)
    open_people_middle_name = models.CharField(max_length=255, null=True)
    open_people_city = models.CharField(max_length=255, null=True)
    open_people_state_code = models.CharField(max_length=2, null=True)
    open_people_zip_code = models.CharField(max_length=10, null=True)
    snovio_id = models.CharField(max_length=255, null=True)
    snovio_locality = models.CharField(max_length=255, null=True)
    snovio_source_state = models.CharField(max_length=2, null=True)
    targetsmart_id = models.CharField(max_length=255, null=True)
    targetsmart_source_state = models.CharField(max_length=2, null=True)


class ContactSMSAugmented(models.Model):
    """
    What information have we retrieved to augment what we know about this one phone number?
    """
    checked_against_open_people = models.BooleanField(db_index=True, default=False)
    checked_against_sendgrid = models.BooleanField(db_index=True, default=False)
    checked_against_targetsmart = models.BooleanField(db_index=True, default=False)
    date_last_checked_against_open_people = models.DateTimeField(null=True)
    date_last_checked_against_sendgrid = models.DateTimeField(null=True)
    date_last_checked_against_targetsmart = models.DateTimeField(null=True)
    is_augmented = models.BooleanField(db_index=True, default=False)
    is_invalid = models.BooleanField(db_index=True, default=False)
    is_verified = models.BooleanField(db_index=True, default=False)
    normalized_sms_phone_number = models.CharField(db_index=True, max_length=50, null=False, unique=True)
    open_people_city = models.CharField(max_length=255, null=True)
    open_people_state_code = models.CharField(max_length=2, null=True)
    open_people_zip_code = models.CharField(max_length=10, null=True)
    snovio_id = models.CharField(max_length=255, null=True)
    snovio_locality = models.CharField(max_length=255, null=True)
    snovio_source_state = models.CharField(max_length=2, null=True)
    targetsmart_id = models.CharField(max_length=255, null=True)
    targetsmart_source_state = models.CharField(max_length=2, null=True)


class VoterDeviceLink(models.Model):
    """
    There can be many voter_device_id's for every voter_id. (See commentary in class VoterDeviceLinkManager)
    """
    # The id for this object is not used in any searches
    # A randomly generated identifier that gets stored as a cookie on a single device
    # See wevote_functions.functions, function generate_voter_device_id for a discussion of voter_device_id length
    MultipleObjectsReturned = None
    DoesNotExist = None
    objects = None
    voter_device_id = models.CharField(verbose_name='voter device id',
                                       max_length=255, null=False, blank=False, unique=True)
    # The voter_id associated with voter_device_id
    voter_id = models.BigIntegerField(verbose_name="voter unique identifier", null=False, blank=False, unique=False)

    # The unique ID of the election (provided by Google Civic) that the voter is looking at on this device
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False)
    state_code = models.CharField(verbose_name="us state the device is most recently active in",
                                  max_length=255, null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)  # last_updated
    date_election_last_changed = models.DateTimeField(null=True)  # last_updated
    # secret_code is a six digit number that can be sent via text or email to sign in
    secret_code = models.CharField(verbose_name="single use secret code tied to this device", max_length=6, null=True)
    # We store a random string for email and another for sms that allows us to tie an unverified email or sms to a voter
    email_secret_key = models.CharField(
        verbose_name="secret key to verify ownership of email", max_length=255, null=True, blank=True, unique=True)
    sms_secret_key = models.CharField(
        verbose_name="secret key to verify ownership of sms", max_length=255, null=True, blank=True, unique=True)
    # Each secret code requested is only valid for one day
    date_secret_code_generated = models.DateTimeField(null=True)
    # A voter may only attempt to enter a secret code 5 times before a new secret code must be requested
    secret_code_number_of_failed_tries_for_this_code = models.PositiveIntegerField(null=True)
    # The number of failed attempts at entering secret code (since last success)
    # This is so we can lock high profile accounts that are being hacked
    secret_code_number_of_failed_tries_all_time = models.PositiveIntegerField(null=True)
    platform_type = models.CharField(
        verbose_name="Platform type string {IOS, ANDROID, WEBAPP}", max_length=32, null=True,
        blank=True)
    firebase_fcm_token = models.CharField(
        verbose_name="the Firebase Cloud Messaging (FCW) token for this device", max_length=255, null=True,
        blank=True)

    @staticmethod
    def generate_voter_device_id():
        # A simple mapping to this function
        return generate_voter_device_id()


class VoterDeviceLinkManager(models.Manager):
    """
    In order to start gathering information about a voter prior to authentication, we use a long randomized string
    stored as a browser cookie. As soon as we get any other identifiable information from a voter (like an email
    address), we capture that so the Voter record can be portable among devices. Note that any voter might be using
    We Vote from different browsers. The VoterDeviceLink links one or more voter_device_id's to one voter_id.

    Since (prior to authentication) every voter_device_id will have its own voter_id record, we merge and delete Voter
    records whenever we can.
    """

    def __init__(self):
        self.objects = None

    def __str__(self):              # __unicode__ on Python 2
        return "Voter Device Id Manager"

    @staticmethod
    def clear_secret_key(email_secret_key='', sms_secret_key=''):
        email_secret_key_found = False
        sms_secret_key_found = False
        voter_device_link = None
        status = ''
        success = True

        try:
            if positive_value_exists(email_secret_key):
                voter_device_link = VoterDeviceLink.objects.get(
                    email_secret_key=email_secret_key,
                )
                email_secret_key_found = True
        except VoterDeviceLink.DoesNotExist:
            status += "EMAIL_SECRET_KEY_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'EMAIL_SECRET_KEY_RETRIEVE_ERROR: ' + str(e) + ' '

        if email_secret_key_found:
            try:
                voter_device_link.email_secret_key = None
                voter_device_link.save()
            except Exception as e:
                success = False
                status += 'EMAIL_SECRET_KEY_SAVE_ERROR: ' + str(e) + ' '

        try:
            if positive_value_exists(sms_secret_key):
                voter_device_link = VoterDeviceLink.objects.get(
                    sms_secret_key=sms_secret_key,
                )
                sms_secret_key_found = True
        except VoterDeviceLink.DoesNotExist:
            status += "SMS_SECRET_KEY_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'SMS_SECRET_KEY_RETRIEVE_ERROR: ' + str(e) + ' '

        if sms_secret_key_found:
            try:
                voter_device_link.sms_secret_key = None
                voter_device_link.save()
            except Exception as e:
                success = False
                status += 'SMS_SECRET_KEY_SAVE_ERROR: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
        }
        return results

    @staticmethod
    def delete_all_voter_device_links(voter_device_id):
        voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)

        try:
            if positive_value_exists(voter_id):
                VoterDeviceLink.objects.filter(voter_id=voter_id).delete()
                status = "DELETE_ALL_VOTER_DEVICE_LINKS_SUCCESSFUL "
                success = True
            else:
                status = "DELETE_ALL_VOTER_DEVICE_LINKS-MISSING_VARIABLES "
                success = False
        except Exception as e:
            status = "DELETE_ALL_VOTER_DEVICE_LINKS-DATABASE_DELETE_EXCEPTION: " + str(e) + " "
            success = False

        results = {
            'success':  success,
            'status':   status,
        }
        return results

    @staticmethod
    def delete_all_voter_device_links_by_voter_id(voter_id):
        status = ""
        try:
            if positive_value_exists(voter_id):
                VoterDeviceLink.objects.filter(voter_id=voter_id).delete()
                status += "DELETE_ALL_VOTER_DEVICE_LINKS_SUCCESSFUL "
                success = True
            else:
                status += "DELETE_ALL_VOTER_DEVICE_LINKS-MISSING_VARIABLES "
                success = False
        except Exception as e:
            status += "DELETE_ALL_VOTER_DEVICE_LINKS-DATABASE_DELETE_EXCEPTION: " + str(e) + " "
            success = False

        results = {
            'success':  success,
            'status':   status,
        }
        return results

    @staticmethod
    def delete_voter_device_link(voter_device_id):
        try:
            if positive_value_exists(voter_device_id):
                VoterDeviceLink.objects.filter(voter_device_id=voter_device_id).delete()
                status = "DELETE_VOTER_DEVICE_LINK_SUCCESSFUL "
                success = True
            else:
                status = "DELETE_VOTER_DEVICE_LINK-MISSING_VARIABLES "
                success = False
        except Exception as e:
            status = "DELETE_VOTER_DEVICE_LINK-DATABASE_DELETE_EXCEPTION: " + str(e) + " "
            success = False

        results = {
            'success':  success,
            'status':   status,
        }
        return results

    @staticmethod
    def retrieve_voter_device_link_from_voter_device_id(voter_device_id, read_only=False):
        voter_id = 0
        voter_device_link_id = 0
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.retrieve_voter_device_link(
            voter_device_id, voter_id=voter_id, voter_device_link_id=voter_device_link_id, read_only=read_only)
        return results

    @staticmethod
    def retrieve_voter_device_link(voter_device_id, voter_id=0, voter_device_link_id=0, read_only=False):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        status = ""
        success = True
        voter_device_link_on_stage = VoterDeviceLink()

        try:
            if positive_value_exists(voter_device_id):
                status += " RETRIEVE_VOTER_DEVICE_LINK-GET_BY_VOTER_DEVICE_ID "
                if read_only and 'test' not in sys.argv:
                    voter_device_link_on_stage = VoterDeviceLink.objects.using('readonly').get(
                        voter_device_id=voter_device_id)
                else:
                    voter_device_link_on_stage = VoterDeviceLink.objects.get(voter_device_id=voter_device_id)
                voter_device_link_id = voter_device_link_on_stage.id
            elif positive_value_exists(voter_id):
                status += " RETRIEVE_VOTER_DEVICE_LINK-GET_BY_VOTER_ID "
                if read_only:
                    voter_device_link_query = VoterDeviceLink.objects.using('readonly').all()
                else:
                    voter_device_link_query = VoterDeviceLink.objects.all()
                voter_device_link_query = voter_device_link_query.filter(voter_id=voter_id)
                voter_device_link_query = voter_device_link_query.order_by('id')
                voter_device_link_list = list(voter_device_link_query)
                try:
                    voter_device_link_on_stage = voter_device_link_list.pop()  # Pop the last created
                    # If still here, we found an existing position
                    voter_device_link_id = voter_device_link_on_stage.id
                except Exception as e:
                    voter_device_link_id = 0
            elif positive_value_exists(voter_device_link_id):
                status += " RETRIEVE_VOTER_DEVICE_LINK-GET_BY_VOTER_DEVICE_LINK_ID "
                if read_only:
                    voter_device_link_on_stage = VoterDeviceLink.objects.using('readonly').get(id=voter_device_link_id)
                else:
                    voter_device_link_on_stage = VoterDeviceLink.objects.get(id=voter_device_link_id)
                # If still here, we found an existing position
                voter_device_link_id = voter_device_link_on_stage.id
            else:
                voter_device_link_id = 0
                status += " RETRIEVE_VOTER_DEVICE_LINK-MISSING_REQUIRED_SEARCH_VARIABLES "
        except VoterDeviceLink.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            status += " RETRIEVE_VOTER_DEVICE_LINK-MULTIPLE_OBJECTS_RETURNED "
        except VoterDeviceLink.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status += " RETRIEVE_VOTER_DEVICE_LINK-DOES_NOT_EXIST "
        except Exception as e:
            status += " RETRIEVE_VOTER_DEVICE_LINK-EXCEPTION: " + str(e) + " "
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'voter_device_link_found':      True if voter_device_link_id > 0 else False,
            'voter_device_link':            voter_device_link_on_stage,
        }
        return results

    @staticmethod
    def retrieve_voter_device_link_list(google_civic_election_id=0, voter_id=0):
        success = False
        status = ""
        voter_device_link_list = []

        try:
            list_query = VoterDeviceLink.objects.all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(voter_id):
                list_query = list_query.filter(voter_id=voter_id)
            voter_device_link_list = list(list_query)
            voter_device_link_list_found = True
            status += "VOTER_DEVICE_LINK_LIST_FOUND "
        except Exception as e:
            voter_device_link_list_found = False
            status += "VOTER_DEVICE_LINK_LIST_NOT_FOUND-EXCEPTION: " + str(e) + " "

        results = {
            'success': success,
            'status': status,
            'voter_device_link_list': voter_device_link_list,
            'voter_device_link_list_found': voter_device_link_list_found,
        }
        return results

    def retrieve_voter_secret_code_up_to_date(self, voter_device_id='', cordova_review_bypass=False):
        """
        We allow a voter 6 attempts/5 failures (NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE)
        to enter each secret_code before we require the secret code be regenerated by the voter.
        For each voter_device_id we allow 25 (NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME) consecutive failures
        before we lock out the voter_device_id. This is in order to protect against brute force attacks.
        :param voter_device_id:
        :param cordova_review_bypass:
        :return:
        """
        success = True
        status = ""
        secret_code = ''
        # NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE = 5
        # NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME = 25
        secret_code_system_locked_for_this_voter_device_id = False

        results = self.retrieve_voter_device_link(voter_device_id)
        if results['voter_device_link_found']:
            voter_device_link = results['voter_device_link']
            if cordova_review_bypass:
                results = self.update_voter_device_link_with_new_secret_code(voter_device_link, cordova_review_bypass)
                voter_device_link = results['voter_device_link']
                secret_code = voter_device_link.secret_code
            elif voter_device_link.secret_code_number_of_failed_tries_all_time is not None \
                    and voter_device_link.secret_code_number_of_failed_tries_all_time > \
                    NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME:
                secret_code_system_locked_for_this_voter_device_id = True
            else:
                if voter_device_link.secret_code_number_of_failed_tries_for_this_code is not None \
                        and voter_device_link.secret_code_number_of_failed_tries_for_this_code > \
                        NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE:
                    # If voter has used up the number of attempts to enter the secret code, create new secret code
                    results = self.update_voter_device_link_with_new_secret_code(
                        voter_device_link,
                        cordova_review_bypass)
                    status += results['status']
                    if results['voter_device_link_updated']:
                        voter_device_link = results['voter_device_link']
                        secret_code = voter_device_link.secret_code
                if voter_device_link.date_secret_code_generated \
                        and positive_value_exists(voter_device_link.secret_code):
                    # We have an existing secret code. Verify it is still valid.
                    # timezone = pytz.timezone("America/Los_Angeles")
                    # datetime_now = timezone.localize(datetime.now())
                    datetime_now = generate_localized_datetime_from_obj()[1]
                    secret_code_is_stale_duration = timedelta(days=1)
                    secret_code_is_stale_date = voter_device_link.date_secret_code_generated + \
                        secret_code_is_stale_duration
                    if secret_code_is_stale_date > datetime_now:
                        secret_code = voter_device_link.secret_code
                else:
                    # Either date_secret_code_generated or secret_code are missing -- generate new ones
                    pass
                if not positive_value_exists(secret_code):
                    # If our secret code has expired or doesn't exist, create a new secret code
                    results = self.update_voter_device_link_with_new_secret_code(voter_device_link,
                                                                                 cordova_review_bypass)
                    status += results['status']
                    if results['voter_device_link_updated']:
                        voter_device_link = results['voter_device_link']
                        secret_code = voter_device_link.secret_code

        results = {
            'success':      success,
            'status':       status,
            'secret_code':  secret_code,
            'secret_code_system_locked_for_this_voter_device_id': secret_code_system_locked_for_this_voter_device_id,
        }
        return results

    @staticmethod
    def save_new_voter_device_link(voter_device_id, voter_id):
        error_result = False
        exception_record_not_saved = False
        missing_required_variables = False
        voter_device_link_on_stage = VoterDeviceLink()
        voter_device_link_id = 0

        try:
            if positive_value_exists(voter_device_id) and positive_value_exists(voter_id):
                voter_device_link_on_stage.voter_device_id = voter_device_id
                voter_device_link_on_stage.voter_id = voter_id
                voter_device_link_on_stage.save()

                voter_device_link_id = voter_device_link_on_stage.id
            else:
                missing_required_variables = True
                voter_device_link_id = 0
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            error_result = True
            exception_record_not_saved = True

        results = {
            'error_result':                 error_result,
            'missing_required_variables':   missing_required_variables,
            'RecordNotSaved':               exception_record_not_saved,
            'voter_device_link_created':    True if voter_device_link_id > 0 else False,
            'voter_device_link':            voter_device_link_on_stage,
        }
        return results

    def update_voter_device_link_with_election_id(self, voter_device_link, google_civic_election_id):
        voter_object = None
        return self.update_voter_device_link(voter_device_link, voter_object, google_civic_election_id)

    def update_voter_device_link_with_state_code(self, voter_device_link, state_code):
        voter_object = None
        google_civic_election_id = 0
        return self.update_voter_device_link(voter_device_link, voter_object, google_civic_election_id, state_code)

    def update_voter_device_link_with_new_secret_code(self, voter_device_link, cordova_review_bypass=False):
        return self.update_voter_device_link(voter_device_link, generate_new_secret_code=True,
                                             cordova_review_bypass=cordova_review_bypass)

    def update_voter_device_link_with_email_secret_key(self, voter_device_link, email_secret_key=False):
        return self.update_voter_device_link(voter_device_link, email_secret_key=email_secret_key)

    def update_voter_device_link_with_sms_secret_key(self, voter_device_link, sms_secret_key=False):
        return self.update_voter_device_link(voter_device_link, sms_secret_key=sms_secret_key)

    @staticmethod
    def update_voter_device_link(
            voter_device_link,
            voter_object=None,
            google_civic_election_id=0,
            state_code='',
            generate_new_secret_code=False,
            delete_secret_code=False,
            email_secret_key=False,
            sms_secret_key=False,
            called_recursively=False,
            cordova_review_bypass=False):
        """
        Update existing voter_device_link with a new voter_id or google_civic_election_id
        """
        status = ""
        success = True
        error_result = False
        exception_record_not_saved = False
        missing_required_variables = False
        voter_device_link_id = 0

        if positive_value_exists(called_recursively):
            status += "UPDATING_VOTER_DEVICE_LINK_RECURSIVELY "
        try:
            if positive_value_exists(voter_device_link.voter_device_id):
                if voter_object and positive_value_exists(voter_object.id):
                    voter_device_link.voter_id = voter_object.id
                if positive_value_exists(google_civic_election_id):
                    voter_device_link.date_election_last_changed = now()
                    voter_device_link.google_civic_election_id = google_civic_election_id
                elif google_civic_election_id == 0:
                    # If set literally to 0, save it
                    voter_device_link.date_election_last_changed = None
                    voter_device_link.google_civic_election_id = 0
                if positive_value_exists(state_code):
                    voter_device_link.state_code = state_code
                if email_secret_key is not False:
                    voter_device_link.email_secret_key = email_secret_key
                if sms_secret_key is not False:
                    voter_device_link.sms_secret_key = sms_secret_key
                if positive_value_exists(generate_new_secret_code):
                    if cordova_review_bypass:
                        voter_device_link.secret_code = get_environment_variable_default("SOCIAL_AUTH_SMS_BYPASS",
                                                                                         "123456")
                    else:
                        voter_device_link.secret_code = generate_random_string(string_length=6, chars=string.digits)
                    timezone = pytz.timezone("America/Los_Angeles")
                    voter_device_link.date_secret_code_generated = timezone.localize(datetime.now())
                    voter_device_link.secret_code_number_of_failed_tries_for_this_code = 0
                if positive_value_exists(delete_secret_code):
                    voter_device_link.secret_code = None
                    voter_device_link.date_secret_code_generated = None
                    voter_device_link.secret_code_number_of_failed_tries_for_this_code = None
                voter_device_link.save()
                status += "UPDATED_VOTER_DEVICE_LINK "
                voter_device_link_id = voter_device_link.id
            else:
                missing_required_variables = True
                voter_device_link_id = 0
                status += "UPDATE-MISSING_VOTER_DEVICE_ID "
        except IntegrityError as e:
            handle_record_not_saved_exception(e, logger=logger)
            error_result = True
            exception_record_not_saved = True
            status += "UPDATE_VOTER_DEVICE_INTEGRITY_ERROR: " + str(e) + " "
            success = False
            # There are three fields which require that they are unique
            # If voter tries to sign in with an email, the email_secret_key gets attached to that voter_device_link
            # If voter clears out cookies, and then tries to sign in again with the same email, we need to be able
            #  to clear out email_secret_key so voter can sign in in other browser
            # If this is a secondary recursive call of this function, don't proceed
            if positive_value_exists(email_secret_key) and not positive_value_exists(called_recursively):
                # status += "CLEARING_EMAIL_SECRET_KEY "
                status += "NEED_TO_CLEAR_EMAIL_SECRET_KEY-BUT_NOT_FOR_NOW "
                voter_device_link_manager = VoterDeviceLinkManager()
                clear_results = voter_device_link_manager.clear_secret_key(email_secret_key=email_secret_key)
                if clear_results['success']:
                    save_results = voter_device_link_manager.update_voter_device_link(
                        voter_device_link=voter_device_link,
                        voter_object=voter_object,
                        google_civic_election_id=google_civic_election_id,
                        state_code=state_code,
                        generate_new_secret_code=generate_new_secret_code,
                        delete_secret_code=delete_secret_code,
                        email_secret_key=email_secret_key,
                        sms_secret_key=sms_secret_key,
                        called_recursively=True,
                    )
                    return save_results
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            error_result = True
            exception_record_not_saved = True
            status += "UPDATE_VOTER_DEVICE_LINK_SAVE_FAILURE: " + str(e) + " "
            success = False

        results = {
            'status':                       status,
            'success':                      success,
            'error_result':                 error_result,
            'missing_required_variables':   missing_required_variables,
            'RecordNotSaved':               exception_record_not_saved,
            'voter_device_link_updated':    True if voter_device_link_id > 0 else False,
            'voter_device_link':            voter_device_link,
        }
        return results

    def voter_verify_secret_code(self, voter_device_id='', secret_code=''):
        success = False
        status = ""
        # NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE = 5
        # NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME = 25
        incorrect_secret_code_entered = False
        number_of_tries_remaining_for_this_code = 0
        secret_code_system_locked_for_this_voter_device_id = False
        secret_code_verified = False
        voter_must_request_new_code = True

        results = self.retrieve_voter_device_link(voter_device_id)
        if results['voter_device_link_found']:
            voter_device_link = results['voter_device_link']
            if voter_device_link.secret_code_number_of_failed_tries_all_time is not None \
                    and voter_device_link.secret_code_number_of_failed_tries_all_time > \
                    NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME:
                number_of_tries_remaining_for_this_code = 0
                secret_code_system_locked_for_this_voter_device_id = True
                status += "SECRET_CODE_SYSTEM_LOCKED-VERIFY_CODE "
            else:
                if voter_device_link.secret_code_number_of_failed_tries_for_this_code is not None \
                        and voter_device_link.secret_code_number_of_failed_tries_for_this_code > \
                        NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE:
                    # If voter has used up the number of attempts to enter the secret code, tell voter to
                    # generate new code
                    number_of_tries_remaining_for_this_code = 0
                    voter_must_request_new_code = True
                    status += "THIS_CODE_HAS_EXCEEDED_ALLOWED_TRIES "
                else:
                    if voter_device_link.secret_code_number_of_failed_tries_for_this_code is None:
                        secret_code_number_of_failed_tries_for_this_code = 0
                    else:
                        secret_code_number_of_failed_tries_for_this_code = \
                            voter_device_link.secret_code_number_of_failed_tries_for_this_code
                    number_of_tries_remaining_for_this_code = NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE - \
                        secret_code_number_of_failed_tries_for_this_code
                    status += "NUMBER_OF_FAILED_TRIES_FOR_THIS_CODE: " + \
                              str(secret_code_number_of_failed_tries_for_this_code) + " "
                    if not positive_value_exists(number_of_tries_remaining_for_this_code):
                        voter_must_request_new_code = True
                        status += "VOTER_DEVICE_LINK_NO_MORE_TRIES_REMAINING_FOR_THIS_CODE "
                    elif voter_device_link.date_secret_code_generated \
                            and positive_value_exists(voter_device_link.secret_code):
                        # We have an existing secret code. Verify it is still valid.
                        # timezone = pytz.timezone("America/Los_Angeles")
                        # datetime_now = timezone.localize(datetime.now())
                        datetime_now = generate_localized_datetime_from_obj()[1]
                        secret_code_is_stale_duration = timedelta(days=1)
                        secret_code_is_stale_date = voter_device_link.date_secret_code_generated + \
                            secret_code_is_stale_duration
                        if secret_code_is_stale_date > datetime_now:
                            if secret_code == voter_device_link.secret_code:
                                status += "VALID_SECRET_CODE_FOUND "
                                secret_code_verified = True
                                voter_must_request_new_code = False
                            else:
                                status += "SECRET_CODE_DOES_NOT_MATCH "
                                incorrect_secret_code_entered = True
                                voter_must_request_new_code = False
                        else:
                            number_of_tries_remaining_for_this_code = 0
                            voter_must_request_new_code = True
                            status += "SECRET_CODE_HAS_EXPIRED "
                    else:
                        number_of_tries_remaining_for_this_code = 0
                        voter_must_request_new_code = True
                        status += "VOTER_DEVICE_LINK_MISSING_SECRET_CODE "
            if secret_code_verified:
                # Remove existing secret code and reset counters
                try:
                    voter_device_link.date_secret_code_generated = None
                    voter_device_link.secret_code = None
                    voter_device_link.secret_code_number_of_failed_tries_all_time = None
                    voter_device_link.secret_code_number_of_failed_tries_for_this_code = None
                    voter_device_link.save()
                except Exception as e:
                    status += "FAILED_RESETTING_SECRET_CODE_AND_COUNTERS: " + str(e) + " "
            else:
                # Increase counts
                try:
                    # For all time
                    if voter_device_link.secret_code_number_of_failed_tries_all_time is None:
                        secret_code_number_of_failed_tries_all_time = 0
                    else:
                        secret_code_number_of_failed_tries_all_time = \
                            voter_device_link.secret_code_number_of_failed_tries_all_time
                    secret_code_number_of_failed_tries_all_time += 1
                    voter_device_link.secret_code_number_of_failed_tries_all_time = \
                        secret_code_number_of_failed_tries_all_time
                    # For this code
                    if voter_device_link.secret_code_number_of_failed_tries_for_this_code is None:
                        secret_code_number_of_failed_tries_for_this_code = 0
                    else:
                        secret_code_number_of_failed_tries_for_this_code = \
                            voter_device_link.secret_code_number_of_failed_tries_for_this_code
                    secret_code_number_of_failed_tries_for_this_code += 1
                    voter_device_link.secret_code_number_of_failed_tries_for_this_code = \
                        secret_code_number_of_failed_tries_for_this_code
                    # Now save
                    voter_device_link.save()
                except Exception as e:
                    status += "FAILED_INCREASING_COUNTERS: " + str(e) + " "
        results = {
            'status':                                   status,
            'success':                                  success,
            'incorrect_secret_code_entered':            incorrect_secret_code_entered,
            'number_of_tries_remaining_for_this_code':  number_of_tries_remaining_for_this_code,
            'secret_code_system_locked_for_this_voter_device_id':   secret_code_system_locked_for_this_voter_device_id,
            'secret_code_verified':                     secret_code_verified,
            'voter_must_request_new_code':              voter_must_request_new_code,
        }
        return results


class VoterIssuesLookup(models.Model):
    """
    A table for rapid lookup (analytics) of how many voters follow each Issue / Value / Topic.
    """
    #
    # We are relying on built-in Python id field

    objects = None
    voter_we_vote_id = models.CharField(max_length=255, null=True, unique=True, db_index=True)
    likely_democrat_from_issues = models.BooleanField(default=None, null=True)
    likely_green_from_issues = models.BooleanField(default=None, null=True)
    likely_left_from_issues = models.BooleanField(default=None, null=True)
    likely_libertarian_from_issues = models.BooleanField(default=None, null=True)
    likely_party_from_issues_analyzed = models.BooleanField(default=False)
    likely_republican_from_issues = models.BooleanField(default=None, null=True)
    likely_right_from_issues = models.BooleanField(default=None, null=True)

    affordable_housing = models.BooleanField(default=None, null=True)
    animals = models.BooleanField(default=None, null=True)
    bicycling = models.BooleanField(default=None, null=True)
    borders = models.BooleanField(default=None, null=True)
    climate_change = models.BooleanField(default=None, null=True)
    color = models.BooleanField(default=None, null=True)
    conservative = models.BooleanField(default=None, null=True)
    democratic_clubs = models.BooleanField(default=None, null=True)
    democratic_politicians = models.BooleanField(default=None, null=True)
    green_clubs = models.BooleanField(default=None, null=True)
    green_politicians = models.BooleanField(default=None, null=True)
    gun_reform = models.BooleanField(default=None, null=True)
    homeless = models.BooleanField(default=None, null=True)
    immigration = models.BooleanField(default=None, null=True)
    independent_politicians = models.BooleanField(default=None, null=True)
    justice_reform = models.BooleanField(default=None, null=True)
    lgbtq = models.BooleanField(default=None, null=True)
    libertarian_clubs = models.BooleanField(default=None, null=True)
    libertarian_politicians = models.BooleanField(default=None, null=True)
    low_income = models.BooleanField(default=None, null=True)
    maga = models.BooleanField(default=None, null=True)
    marijuana = models.BooleanField(default=None, null=True)
    money_in_politics = models.BooleanField(default=None, null=True)
    pro_choice = models.BooleanField(default=None, null=True)
    pro_life = models.BooleanField(default=None, null=True)
    pro_public_schools = models.BooleanField(default=None, null=True)
    pro_school_choice = models.BooleanField(default=None, null=True)
    progressive = models.BooleanField(default=None, null=True)
    public_healthcare = models.BooleanField(default=None, null=True)
    republican_clubs = models.BooleanField(default=None, null=True)
    republican_politicians = models.BooleanField(default=None, null=True)
    second_amendment = models.BooleanField(default=None, null=True)
    social_security = models.BooleanField(default=None, null=True)
    student_debt = models.BooleanField(default=None, null=True)
    voting_rights = models.BooleanField(default=None, null=True)
    womens_equality = models.BooleanField(default=None, null=True)


# This method *just* returns the voter_id or 0
def fetch_voter_id_from_voter_device_link(voter_device_id):
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(
        voter_device_id, read_only=True)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        return voter_device_link.voter_id
    return 0


# This method *just* returns the voter_id or 0
def fetch_voter_id_from_voter_we_vote_id(we_vote_id):
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_we_vote_id(we_vote_id, read_only=True)
    if results['voter_found']:
        voter = results['voter']
        return voter.id
    return 0


# This method *just* returns the voter_we_vote_id or ""
def fetch_voter_we_vote_id_from_voter_id(voter_id):
    if not positive_value_exists(voter_id):
        return ""
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_by_id(voter_id, read_only=True)
    if results['voter_found']:
        voter = results['voter']
        return voter.we_vote_id
    return ""


# It is better to use voter_manager.retrieve_voter_from_voter_device_id
# def fetch_voter_from_voter_device_link(voter_device_id):
#     voter_device_link_manager = VoterDeviceLinkManager()
#     results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_device_id)
#     if results['voter_device_link_found']:
#         voter_device_link = results['voter_device_link']
#         voter_id = voter_device_link.voter_id
#         voter_manager = VoterManager()
#         results = voter_manager.retrieve_voter_by_id(voter_id)
#         if results['voter_found']:
#             voter = results['voter']
#             return voter
#         return ""


def fetch_api_voter_from_request(request):
    """
    For use on API server only
    :param request:
    :return:
    """
    voter_api_device_id = get_voter_api_device_id(request)
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id, read_only=True)
    if results['voter_found']:
        voter = results['voter']
        return voter

    return None


def fetch_voter_from_voter_device_link(voter_device_id):
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(
        voter_device_id, read_only=True)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        voter_id = voter_device_link.voter_id
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id, read_only=True)
        if results['voter_found']:
            voter = results['voter']
            return voter
        return None
    return None


def fetch_voter_we_vote_id_from_voter_device_link(voter_device_id):
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_device_id,
                                                                                        read_only=True)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        voter_id = voter_device_link.voter_id
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id, read_only=True)
        if results['voter_found']:
            voter = results['voter']
            return voter.we_vote_id
        return ""


def retrieve_voter_authority(request):
    voter_api_device_id = get_voter_api_device_id(request)
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id, read_only=True)
    if results['voter_found']:
        voter = results['voter']
        authority_results = {
            'voter_found':                  True,
            'is_active':                    positive_value_exists(voter.is_active),
            'is_admin':                     positive_value_exists(voter.is_admin),
            'is_analytics_admin':           positive_value_exists(voter.is_analytics_admin),
            'is_partner_organization':      positive_value_exists(voter.is_partner_organization),
            'is_political_data_manager':    positive_value_exists(voter.is_political_data_manager),
            'is_political_data_viewer':     positive_value_exists(voter.is_political_data_viewer),
            'is_verified_volunteer':        positive_value_exists(voter.is_verified_volunteer),
            'is_voter_manager':             positive_value_exists(voter.is_voter_manager),
        }
        return authority_results

    authority_results = {
        'voter_found':                  False,
        'is_active':                    False,
        'is_admin':                     False,
        'is_analytics_admin':           False,
        'is_partner_organization':      False,
        'is_political_data_manager':    False,
        'is_political_data_viewer':     False,
        'is_verified_volunteer':        False,
        'is_voter_manager':             False,
    }
    return authority_results


def voter_has_authority(request, authority_required, authority_results=None):
    if not authority_results:
        authority_results = retrieve_voter_authority(request)
    if not positive_value_exists(authority_results['is_active']):
        return False
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    if 'admin' in authority_required and \
            positive_value_exists(authority_results['is_admin']):
        return True
    if 'analytics_admin' in authority_required and \
            (
            positive_value_exists(authority_results['is_analytics_admin']) or
            positive_value_exists(authority_results['is_admin'])
            ):
        return True
    if 'voter_manager' in authority_required and \
            (
            positive_value_exists(authority_results['is_voter_manager']) or
            positive_value_exists(authority_results['is_admin'])
            ):
        return True
    if 'partner_organization' in authority_required and \
            (
            positive_value_exists(authority_results['is_partner_organization']) or
            positive_value_exists(authority_results['is_political_data_manager']) or
            positive_value_exists(authority_results['is_admin'])
            ):
        return True
    if 'political_data_manager' in authority_required and \
            (
            positive_value_exists(authority_results['is_political_data_manager']) or
            positive_value_exists(authority_results['is_admin'])
            ):
        return True
    if 'political_data_viewer' in authority_required and \
            (
            positive_value_exists(authority_results['is_political_data_viewer']) or
            positive_value_exists(authority_results['is_analytics_admin']) or
            positive_value_exists(authority_results['is_verified_volunteer']) or
            positive_value_exists(authority_results['is_political_data_manager']) or
            positive_value_exists(authority_results['is_admin'])
            ):
        return True
    if 'verified_volunteer' in authority_required and \
            (
            positive_value_exists(authority_results['is_verified_volunteer']) or
            positive_value_exists(authority_results['is_analytics_admin']) or
            positive_value_exists(authority_results['is_political_data_manager']) or
            positive_value_exists(authority_results['is_voter_manager']) or
            positive_value_exists(authority_results['is_admin'])
            ):
        return True
    return False

# class VoterJurisdictionLink(models.Model):
#     """
#     all the jurisdictions the Voter is in
#     """
#     voter = models.ForeignKey(Voter, null=False, blank=False, verbose_name='voter')
#     jurisdiction = models.ForeignKey(Jurisdiction,
#                                      null=False, blank=False, verbose_name="jurisdiction this voter votes in")


BALLOT_ADDRESS = 'B'
MAILING_ADDRESS = 'M'
FORMER_BALLOT_ADDRESS = 'F'
ADDRESS_TYPE_CHOICES = (
    (BALLOT_ADDRESS, 'Address Where Registered to Vote'),
    (MAILING_ADDRESS, 'Mailing Address'),
    (FORMER_BALLOT_ADDRESS, 'Prior Address'),
)


class VoterAddress(models.Model):
    """
    An address of a registered voter for ballot purposes.
    """
    #
    # We are relying on built-in Python id field

    # The voter_id that owns this address
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None
    voter_id = models.BigIntegerField(
        verbose_name="voter unique identifier", null=False, blank=False, unique=False, db_index=True)
    address_type = models.CharField(
        verbose_name="type of address", max_length=1, choices=ADDRESS_TYPE_CHOICES, default=BALLOT_ADDRESS)

    text_for_map_search = models.CharField(max_length=255, blank=False, null=False, verbose_name='address as entered')
    invalid_address = models.BooleanField(verbose_name="Garbage, misspelled, or unparsable address", null=True)

    latitude = models.CharField(max_length=255, blank=True, null=True, verbose_name='latitude returned from Google')
    longitude = models.CharField(max_length=255, blank=True, null=True, verbose_name='longitude returned from Google')
    normalized_line1 = models.CharField(max_length=255, blank=True, null=True,
                                        verbose_name='normalized address line 1 returned from Google')
    normalized_line2 = models.CharField(max_length=255, blank=True, null=True,
                                        verbose_name='normalized address line 2 returned from Google')
    normalized_city = models.CharField(max_length=255, blank=True, null=True,
                                       verbose_name='normalized city returned from Google')
    normalized_state = models.CharField(max_length=255, blank=True, null=True,
                                        verbose_name='normalized state returned from Google')
    normalized_zip = models.CharField(max_length=255, blank=True, null=True,
                                      verbose_name='normalized zip returned from Google')
    county_fips_code = models.CharField(max_length=5, null=True, verbose_name="FIPS code for this county")
    county_name = models.CharField(max_length=255, null=True)
    # This is the election_id last found for this address
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id for this address", null=True, unique=False)
    # The last election day this address was used to retrieve a ballot
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)

    ballot_location_display_name = models.CharField(
        verbose_name="display name of ballot voter is viewing", max_length=255, default=None, null=True,
        blank=True, unique=False)
    ballot_returned_we_vote_id = models.CharField(
        verbose_name="we vote id of the ballot", max_length=255, default=None, null=True,
        blank=True, unique=False)

    refreshed_from_google = models.BooleanField(
        verbose_name="have normalized fields been updated from Google since address change?",
        default=False, db_index=True)

    voter_entered_address = models.BooleanField(verbose_name="Did the voter manually enter an address?", default=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)  # last_updated

    def get_state_code_from_text_for_map_search(self):
        if positive_value_exists(self.text_for_map_search):
            return extract_state_code_from_address_string(self.text_for_map_search)
        else:
            return ""


class VoterAddressManager(models.Manager):
    def __unicode__(self):
        return "VoterAddressManager"

    @staticmethod
    def retrieve_address(voter_address_id, voter_id=0, address_type=''):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_address_on_stage = None
        voter_address_has_value = False

        if not positive_value_exists(address_type):
            # Provide a default
            address_type = BALLOT_ADDRESS

        try:
            if positive_value_exists(voter_address_id):
                voter_address_on_stage = VoterAddress.objects.get(id=voter_address_id)
                voter_address_id = voter_address_on_stage.id
                voter_address_found = True
                status = "VOTER_ADDRESS_FOUND_BY_ID"
                success = True
                voter_address_has_value = True if positive_value_exists(voter_address_on_stage.text_for_map_search) \
                    else False
            elif positive_value_exists(voter_id) and address_type in (BALLOT_ADDRESS, MAILING_ADDRESS,
                                                                      FORMER_BALLOT_ADDRESS):
                voter_address_on_stage = VoterAddress.objects.get(voter_id=voter_id, address_type=address_type)
                # If still here, we found an existing address
                voter_address_id = voter_address_on_stage.id
                voter_address_found = True
                status = "VOTER_ADDRESS_FOUND_BY_VOTER_ID_AND_ADDRESS_TYPE"
                success = True
                voter_address_has_value = True if positive_value_exists(voter_address_on_stage.text_for_map_search) \
                    else False
            else:
                voter_address_found = False
                status = "VOTER_ADDRESS_NOT_FOUND-MISSING_REQUIRED_VARIABLES"
                success = False
        except VoterAddress.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            status = "VOTER_ADDRESS_MULTIPLE_OBJECTS_RETURNED"
            exception_multiple_object_returned = True
            success = False
            voter_address_found = False
        except VoterAddress.DoesNotExist:
            error_result = True
            status = "VOTER_ADDRESS_DOES_NOT_EXIST"
            exception_does_not_exist = True
            success = True
            voter_address_found = False

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_address_found':      voter_address_found,
            'voter_address_has_value':  voter_address_has_value,
            'voter_address_id':         voter_address_id,
            'voter_address':            voter_address_on_stage,
        }
        return results

    @staticmethod
    def retrieve_ballot_address_from_voter_id(voter_id):
        voter_address_id = 0
        address_type = BALLOT_ADDRESS
        voter_address_manager = VoterAddressManager()
        return voter_address_manager.retrieve_address(voter_address_id, voter_id, address_type)

    def retrieve_ballot_map_text_from_voter_id(self, voter_id):
        results = self.retrieve_ballot_address_from_voter_id(voter_id)

        ballot_map_text = ''
        if results['voter_address_found']:
            voter_address = results['voter_address']
            minimum_normalized_address_data_exists = positive_value_exists(
                voter_address.normalized_city) or positive_value_exists(
                    voter_address.normalized_state) or positive_value_exists(voter_address.normalized_zip)
            if minimum_normalized_address_data_exists:
                ballot_map_text += voter_address.normalized_line1 \
                    if positive_value_exists(voter_address.normalized_line1) else ''
                ballot_map_text += ", " \
                    if positive_value_exists(voter_address.normalized_line1) \
                    and positive_value_exists(voter_address.normalized_city) \
                    else ''
                ballot_map_text += voter_address.normalized_city \
                    if positive_value_exists(voter_address.normalized_city) else ''
                ballot_map_text += ", " \
                    if positive_value_exists(voter_address.normalized_city) \
                    and positive_value_exists(voter_address.normalized_state) \
                    else ''
                ballot_map_text += voter_address.normalized_state \
                    if positive_value_exists(voter_address.normalized_state) else ''
                ballot_map_text += " " + voter_address.normalized_zip \
                    if positive_value_exists(voter_address.normalized_zip) else ''
            elif positive_value_exists(voter_address.text_for_map_search):
                ballot_map_text += voter_address.text_for_map_search
        return ballot_map_text

    @staticmethod
    def retrieve_voter_address_list(google_civic_election_id=0, voter_id=0):
        success = True
        status = ""
        voter_address_list = []

        try:
            list_query = VoterAddress.objects.all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(voter_id):
                list_query = list_query.filter(voter_id=voter_id)
            voter_address_list = list(list_query)
            voter_address_list_found = True
            status += "VOTER_ADDRESS_LIST_FOUND "
        except Exception as e:
            voter_address_list_found = False
            status += "VOTER_ADDRESS_LIST_NOT_FOUND-EXCEPTION: " + str(e) + ' '
            success = False

        results = {
            'success': success,
            'status': status,
            'voter_address_list': voter_address_list,
            'voter_address_list_found': voter_address_list_found,
        }
        return results

    def retrieve_text_for_map_search_from_voter_id(self, voter_id):
        results = self.retrieve_ballot_address_from_voter_id(voter_id)

        text_for_map_search = ''
        if results['voter_address_found']:
            voter_address = results['voter_address']
            text_for_map_search = voter_address.text_for_map_search
        return text_for_map_search

    def update_or_create_voter_address(
            self,
            voter_id=0,
            address_type='',
            raw_address_text='',
            google_civic_election_id=False,
            voter_entered_address=True):
        """
        NOTE: This approach won't support multiple FORMER_BALLOT_ADDRESS
        :param voter_id:
        :param address_type:
        :param raw_address_text:
        :param google_civic_election_id:
        :param voter_entered_address:
        :return:
        """
        status = ''
        success = True
        exception_multiple_object_returned = False
        new_address_created = False
        voter_address_has_value = False
        voter_address_on_stage = None
        voter_address_on_stage_found = False
        google_civic_election_id = google_civic_election_id if positive_value_exists(google_civic_election_id) else 0

        if positive_value_exists(voter_id) and address_type in (BALLOT_ADDRESS, MAILING_ADDRESS, FORMER_BALLOT_ADDRESS):
            try:
                google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)
                place_found, line1, state, city, zip_code = self.parse_address(raw_address_text)
                invalid_address = True
                fips, county, latitude, longitude = '', '', '', ''
                if place_found:             # if a city was found, then hopefully a line1 was found
                    invalid_address = False
                    location = google_client.geocode(raw_address_text, sensor=False,
                                                     timeout=GEOCODE_TIMEOUT)
                    latitude, longitude = location.latitude, location.longitude
                    fips, county, fallback = self.get_fips_from_fcc(latitude, longitude, city, state)
                elif len(zip_code) > 0:     # With no city, Google can do plenty with just a zip code (but no line1)
                    invalid_address = False
                    loc = google_client.geocode(zip_code, sensor=False, timeout=GEOCODE_TIMEOUT)
                    address, latitude, longitude = loc.address, loc.latitude, loc.longitude
                    place_found, line1, state, city, zip_code = self.parse_address(address)
                    fips, county, fallback = self.get_fips_from_fcc(latitude, longitude, city, state)

                updated_values = {
                    # Values we search against
                    'voter_id': voter_id,
                    'address_type': address_type,
                    # The rest of the values are to be saved
                    'text_for_map_search':      raw_address_text,
                    'latitude':                 latitude,
                    'longitude':                longitude,
                    'county_fips_code':         fips,
                    'county_name':              county,
                    'normalized_line1':         line1,
                    'normalized_line2':         None,
                    'normalized_city':          city,
                    'normalized_state':         state,
                    'normalized_zip':           zip_code,
                    'invalid_address':          invalid_address,
                    # We clear out former values for these so voter_ballot_items_retrieve_for_api resets them
                    'refreshed_from_google':    False,
                    'voter_entered_address':    voter_entered_address,
                    'google_civic_election_id': google_civic_election_id,
                    'election_day_text':        '',
                }

                voter_address_on_stage, new_address_created = VoterAddress.objects.update_or_create(
                    voter_id__exact=voter_id, address_type=address_type, defaults=updated_values)
                voter_address_on_stage_found = voter_address_on_stage.id
                voter_address_has_value = positive_value_exists(voter_address_on_stage.text_for_map_search)

                status = self.save_address_and_dupe_back_to_voter(voter_address_on_stage, status)
                success = True
                status += "UPDATE_OR_CREATE_SUCCESSFUL "
            except Exception as e:
                status += f'CRASHING_GOOGLE_GEOCODER: '

            except VoterAddress.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status += 'MULTIPLE_MATCHING_ADDRESSES_FOUND '
                exception_multiple_object_returned = True

            
        else:
            success = False
            status += 'MISSING_VOTER_ID_OR_ADDRESS_TYPE '

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_address_saved':      success,
            'address_type':             address_type,
            'new_address_created':      new_address_created,
            'voter_address_found':      voter_address_on_stage_found,
            'voter_address_has_value':  voter_address_has_value,
            'voter_address':            voter_address_on_stage,
        }
        return results

    def update_voter_address_with_normalized_values(self, voter_id, voter_address_dict):
        voter_address_id = 0
        address_type = BALLOT_ADDRESS
        results = self.retrieve_address(voter_address_id, voter_id, address_type)
        status = ''

        if results['success']:
            voter_address = results['voter_address']
            voter_address_exists = \
                voter_address and hasattr(voter_address, 'voter_id') and positive_value_exists(voter_address.voter_id)

            if voter_address_exists:
                try:
                    voter_address.normalized_line1 = voter_address_dict['line1']
                    voter_address.normalized_city = voter_address_dict['city']
                    voter_address.normalized_state = voter_address_dict['state']
                    voter_address.normalized_zip = voter_address_dict['zip']
                    voter_address.refreshed_from_google = True
                    voter_address.save()
                    status += "SAVED_VOTER_ADDRESS_WITH_NORMALIZED_VALUES "
                    success = True
                except Exception as e:
                    status += "UNABLE_TO_SAVE_VOTER_ADDRESS_WITH_NORMALIZED_VALUES "
                    success = False
                    handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
            else:
                status += "VOTER_ADDRESS_DOES_NOT_EXIST "
                success = False
        else:
            # If here, we were unable to find pre-existing VoterAddress
            status = "UNABLE_TO_FIND_VOTER_ADDRESS"
            voter_address = None  # TODO Finish this for "create new" case
            success = False

        results = {
            'status':           status,
            'success':          success,
            'voter_address':    voter_address,
        }
        return results

    def update_existing_voter_address_object(self, voter_address_object):
        status = ""
        results = self.retrieve_address(voter_address_object.id)

        if results['success']:
            try:
                voter_address_object.save()  # Save the incoming object
                status += "UPDATED_EXISTING_VOTER_ADDRESS "
                success = True
                voter_address_found = True
            except Exception as e:
                status += "UNABLE_TO_UPDATE_EXISTING_VOTER_ADDRESS "
                success = False
                voter_address_found = False
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            # If here, we were unable to find pre-existing VoterAddress
            status += "UNABLE_TO_FIND_AND_UPDATE_VOTER_ADDRESS "
            voter_address_object = None
            success = False
            voter_address_found = False

        results = {
            'status':               status,
            'success':              success,
            'voter_address':        voter_address_object,
            'voter_address_found':  voter_address_found,
        }
        return results

    def fetch_address_basic_count(self):
        or_filter = True
        refreshed_from_google = False
        has_election = True
        google_civic_election_id = False
        has_latitude_longitude = False
        return self.fetch_address_count(or_filter, refreshed_from_google, has_election, google_civic_election_id,
                                        has_latitude_longitude)

    def fetch_address_full_address_count(self):
        or_filter = True
        refreshed_from_google = False  # This tells us the person entered their full address
        has_election = False
        google_civic_election_id = False
        has_latitude_longitude = False
        return self.fetch_address_count(or_filter, refreshed_from_google, has_election, google_civic_election_id,
                                        has_latitude_longitude, longer_than_this_number=22)

    @staticmethod
    def fetch_address_count(
            or_filter=True,
            refreshed_from_google=False,
            has_election=False,
            google_civic_election_id=False,
            has_latitude_longitude=False,
            longer_than_this_number=0):
        voter_address_queryset = VoterAddress.objects.using('readonly').all()

        voter_raw_filters = []
        if positive_value_exists(or_filter):
            if positive_value_exists(refreshed_from_google):
                new_voter_filter = Q(refreshed_from_google=True)
                voter_raw_filters.append(new_voter_filter)
            if positive_value_exists(has_election):
                new_voter_filter = Q(google_civic_election_id__isnull=False)
                voter_raw_filters.append(new_voter_filter)
                new_voter_filter = Q(google_civic_election_id__gt=0)
                voter_raw_filters.append(new_voter_filter)
            if positive_value_exists(google_civic_election_id):
                google_civic_election_id = convert_to_int(google_civic_election_id)
                new_voter_filter = Q(google_civic_election_id=google_civic_election_id)
                voter_raw_filters.append(new_voter_filter)
            if positive_value_exists(has_latitude_longitude):
                new_voter_filter = Q(latitude__isnull=False)
                voter_raw_filters.append(new_voter_filter)

        else:
            # Add "and" filter here
            pass

        if positive_value_exists(or_filter):
            if len(voter_raw_filters):
                final_voter_filters = voter_raw_filters.pop()

                # ...and "OR" the remaining items in the list
                for item in voter_raw_filters:
                    final_voter_filters |= item

                voter_address_queryset = voter_address_queryset.filter(final_voter_filters)

        if positive_value_exists(longer_than_this_number):
            from django.db.models.functions import Length
            voter_address_queryset = \
                voter_address_queryset.annotate(text_len=Length('text_for_map_search'))\
                .filter(text_len__gt=longer_than_this_number)

        voter_address_count = 0
        try:
            voter_address_count = voter_address_queryset.count()
        except Exception as e:
            pass

        return voter_address_count

    def duplicate_voter_address_from_voter_id(self, from_voter_id, to_voter_id):
        voter_address_id = 0
        results = self.retrieve_address(voter_address_id, from_voter_id)
        if results['voter_address_found']:
            voter_address = results['voter_address']
            return self.duplicate_voter_address(voter_address, to_voter_id)

        results = {
            'success':                  False,
            'status':                   "EXISTING_VOTER_ADDRESS_NOT_FOUND",
            'voter_address_duplicated': False,
            'voter_address':            None,
        }
        return results

    @staticmethod
    def duplicate_voter_address(voter_address, new_voter_id):
        """
        Starting with an existing voter_address, create a duplicate version for a duplicated voter
        :param voter_address:
        :param new_voter_id:
        :return:
        """
        voter_address_duplicated = False
        success = False
        status = ""
        try:
            voter_address.id = None  # Remove the primary key so it is forced to save a new entry
            voter_address.pk = None
            voter_address.voter_id = new_voter_id
            voter_address.save()
            status += "DUPLICATE_VOTER_ADDRESS_SUCCESSFUL"
            voter_address_duplicated = True
        except Exception as e:
            status += "DUPLICATE_VOTER_ADDRESS_FAILED"

        results = {
            'success':                  success,
            'status':                   status,
            'voter_address_duplicated': voter_address_duplicated,
            'voter_address':            voter_address,
        }
        return results

    @staticmethod
    def city_key_cleaner(raw):
        clean = raw.replace(',', '').replace('.', '').replace('Twp', '').replace('Township', '').\
            replace('St ', 'Saint ').replace('Ft ', 'Fort ').strip()
        return clean

    @staticmethod
    def parse_address(typed_address):
        place_found = False
        line1, state, city, zip_code = '', '', '', ''
        if len(typed_address) == 0:
            return place_found, line1, state, city, zip_code
        if re.search(r"^\d{5}$", typed_address):
            return True, line1, state, city, typed_address
        text_no_usa = typed_address if not typed_address.endswith(', USA') else typed_address.replace(', USA', '')
        line1 = text_no_usa
        line1low = line1.lower()

        parsed = usaddress.parse(text_no_usa)
        for tup in parsed:
            (value, key) = tup
            if key == 'PlaceName':
                if place_found:  # handle multiple word cities like Tahoe City and Half Moon Bay
                    city = city + ' ' + (value.replace(',', '').replace('.', '').capitalize())
                else:
                    city = value.replace(',', '').replace('.', '').capitalize()
                    place_found = True
            elif key == 'StateName':
                if value != 'USA':
                    state = value.upper().replace('.', "").replace(',', "")
            elif key == 'ZipCode':
                zip_code = value

        f1 = line1low.find((city + ', ' + state).lower())
        f2 = line1low.find((city + ' ' + state).lower())
        if f1 > 0:
            line1 = line1[:f1].replace(',', '').strip()
        elif f1 == 0:
            line1 = ''
        elif f2 > 0:
            line1 = line1[:f2].replace(',', '').strip()
        elif f2 == 0:
            line1 = ''

        return place_found, line1, state, city, zip_code

    FIPS_LOOKUP = False

    @staticmethod
    def get_lookup():
        fl = __class__.FIPS_LOOKUP
        if fl is not False:
            return fl

        with open('voter/fipsCodesWithPosition.json') as file:
            # Fallback lookup for city/state to fips and county
            __class__.FIPS_LOOKUP = json.load(file)
            return __class__.FIPS_LOOKUP

    def get_fips_from_fcc(self, latitude, longitude, city, state):
        url = 'https://geo.fcc.gov/api/census/block/find?latitude=' + str(latitude) + '&longitude=' + str(longitude) + \
              '&censusYear=2020&showall=false&format=json'
        fips, county = '', ''
        fallback = False
        try:
            response = requests.get(url)
            block = response.json()
            county_leaf = block['County']
            fips = county_leaf['FIPS']
            county = county_leaf['name'].replace('County', '').strip()
        except Exception:
            # On July 29, 2023, the fcc api started failing for many coordinates, but was working again on the 31st
            logger.error('Failing FCC Fips Lookup: ' + url)

        if fips == '':
            key = (self.city_key_cleaner(city) + ',' + state).lower()
            lookup = self.get_lookup()
            if key in lookup:
                payload = lookup[key]
                fips = payload['fips']
                county = payload['county']
            err = 'FIPS_FROM_FCC using fallback file fips: ' if county != '' else \
                'FIPS_FROM_FCC CITY NOT IN fallback file fips: '
            logger.error('%s', err + state + '-' + county + '-' + city + '-' + fips)
            fallback = True
        return fips, county, fallback

    @staticmethod
    def set_normalized_address_fields(address, line1, city, state, zip_code):
        if positive_value_exists(line1):
            address.normalized_line1 = line1
        if positive_value_exists(city):
            address.normalized_city = city
        if positive_value_exists(state):
            address.normalized_state = state
        if positive_value_exists(zip_code):
            address.normalized_zip = zip_code

    @staticmethod
    def add_fips_to_address(address, fips, county, latitude, longitude):
        address.county_fips_code = fips
        address.county_name = county
        address.latitude = latitude
        address.longitude = longitude

    @staticmethod
    def mark_address_as_invalid(voter_address):
        # TODO: this function is reused when new voters are created, remove this log line anytime after mid august 2023
        logger.error('%s', 'mark_address_as_invalid, Marking as invalid: ' + voter_address.text_for_map_search)

        voter_address.invalid_address = True
        voter_address.save()

    @staticmethod
    def save_address_and_dupe_back_to_voter(voter_address, status):
        # save updates to voter_address
        voter_address.invalid_address = False
        voter_address.save()

        try:
            # duplicate the newly acquired field data to voter record (as requested in the jira issue)
            # There is no existing data of any value in Voter to be concerned about overwriting
            voter = Voter.objects.get(id=voter_address.voter_id)
            voter.county_fips_code = voter_address.county_fips_code
            voter.county_name = voter_address.county_name
            if positive_value_exists(voter_address.latitude):
                voter.latitude = positive_value_exists(voter_address.latitude)
            if positive_value_exists(voter_address.longitude):
                voter.longitude = voter_address.longitude
            voter.save()
        except Exception as e:
            err = " VOTER_" + str(voter_address.voter_id) + "_NOT_UPDATED_WITH_ADDRESS: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=err)
            status += err
        return status

    def update_fips_codes_for_all_voteraddresses(self, limit):  # /apis/v1/voterUpdateFips/?limit=10000
        status = ''
        garbled = 0
        unique_saved = 0
        dupes_updated = 0
        failed = 0
        google_lookups = 0
        google_lookups_failed = 0
        fcc_success = 0
        fcc_fallback = 0
        try:
            google_client = get_geocoder_for_service('google')(GOOGLE_MAPS_API_KEY)

            addresses_to_fix = VoterAddress.objects.exclude(invalid_address=True).order_by('text_for_map_search')
            total_addresses = 0
            try:
                # with Python 9, in July 2023, this throws an exception every time -- hopefully not with Python 11
                # total_addresses = len(addresses_to_fix)
                # 8/1/23 This caused a "Worker with pid 10 was terminated due to signal 9
                total_addresses = addresses_to_fix.count()

            except Exception as elen:
                logger.error('%s', 'Length of query set calculation error: ' + str(elen))

            prior_text_for_map_search = ''
            prior_voter_address = {}

            cnt = 0
            for voter_address in addresses_to_fix.iterator():
                if google_lookups >= int(limit):
                    break
                this_text_for_map_search = voter_address.text_for_map_search
                logger.error('%s', 'UPDATE_FIPS_CODES loop cnt: ' + str(cnt) +
                             ', Google lookups: ' + str(google_lookups) + ', Dupes updated: ' + str(dupes_updated) +
                             ', FCC Success: ' + str(fcc_success) + ', FCC Fallback: ' + str(fcc_fallback))
                cnt += 1
                if not positive_value_exists(this_text_for_map_search):
                    self.mark_address_as_invalid(voter_address)
                    garbled += 1
                elif prior_text_for_map_search != this_text_for_map_search:
                    place_found, line1, state, city, zip_code = self.parse_address(this_text_for_map_search)

                    if not place_found:
                        self.mark_address_as_invalid(voter_address)
                        garbled += 1
                    else:
                        try:
                            google_lookups += 1
                            if (len(state) == 0 or len(state) > 2 or len(city) == 0) and len(zip_code) > 4:
                                # If all we have is a zip code, Google does pretty well
                                loc = google_client.geocode(zip_code, sensor=False, timeout=GEOCODE_TIMEOUT)
                                if loc is None:
                                    raise Exception("Google geocode failed to process zip_code: " + zip_code)
                                address, latitude, longitude = loc.address, loc.latitude, loc.longitude
                                place_found, line1, state, city, zip_code = self.parse_address(address)
                            else:
                                loc = google_client.geocode(this_text_for_map_search, sensor=False,
                                                            timeout=GEOCODE_TIMEOUT)
                                if loc is None:
                                    raise Exception("Google geocode failed to process address: " +
                                                    this_text_for_map_search)
                                latitude, longitude = loc.latitude, loc.longitude
                            fips, county, fallback = self.get_fips_from_fcc(latitude, longitude, city, state)
                            if fallback:
                                fcc_fallback += 1
                            else:
                                fcc_success += 1

                        except Exception as goog:
                            google_lookups_failed += 1
                            logger.error('%s', 'Google api exception: ' + str(goog) + ' -- ' + this_text_for_map_search)
                            self.mark_address_as_invalid(voter_address)
                            continue

                        try:
                            if state in VALID_STATES and len(city) > 2:
                                self.set_normalized_address_fields(voter_address, line1, city, state, zip_code)
                                self.add_fips_to_address(voter_address, fips, county, latitude, longitude)
                                try:
                                    if positive_value_exists(voter_address.county_fips_code):
                                        status = self.save_address_and_dupe_back_to_voter(voter_address, status)
                                        unique_saved += 1
                                        prior_voter_address = voter_address
                                        prior_text_for_map_search = this_text_for_map_search
                                    else:
                                        failed += 1
                                except Exception as e:
                                    logger.error('Failed to save addr: ' + str(e) + ' -- ' +
                                                 this_text_for_map_search)
                                    failed += 1
                                    self.mark_address_as_invalid(voter_address)
                            else:
                                garbled += 1
                                logger.error('%s', 'FAILURE to process address: ' + this_text_for_map_search)
                                self.mark_address_as_invalid(voter_address)

                        except Exception as ge:
                            logger.error('%s', 'General exception in unique save: ' + str(ge))
                else:
                    try:
                        # This voter_address is a duplicate text_for_map_search as in the prior address in the q set
                        normalized_city, normalized_state, normalized_line1, normalized_zip, county_fips_code, \
                            county_name, latitude, longitude = prior_voter_address.normalized_city, \
                            prior_voter_address.normalized_state, prior_voter_address.normalized_line1, \
                            prior_voter_address.normalized_zip, prior_voter_address.county_fips_code, \
                            prior_voter_address.county_name, prior_voter_address.latitude, \
                            prior_voter_address.longitude
                        self.set_normalized_address_fields(voter_address, normalized_line1, normalized_city,
                                                           normalized_state, normalized_zip)
                        self.add_fips_to_address(voter_address, county_fips_code, county_name, latitude, longitude)
                        status = self.save_address_and_dupe_back_to_voter(voter_address, status)
                        dupes_updated += 1

                    except Exception as gedu:
                        logger.error('%s', 'General exception in dupe update: ' + str(gedu))

            stats = 'ADDRESESS_TO_PROCESS ' + str(total_addresses) + \
                    ' GOOGLE_API_ATTEMPTED ' + str(google_lookups) + \
                    ' GOOGLE_API_FAILED ' + str(google_lookups_failed) + \
                    ' SAVED_UNIQUE ' + str(unique_saved) + ' SAVED_DUPES_UPDATED ' + str(dupes_updated) + \
                    ' FCC_API_SUCCESS ' + str(fcc_success) + ' FIPS_FROM_FALLBACK ' + str(fcc_fallback) + \
                    ' GARBLED_ADDRESSES ' + str(garbled) + ' ADDRESS_NOT_IN_FIPS__BACKUP ' + str(failed)
            # logger.error('%s', 'update_fips_codes_for_all_voteraddresses status: ' + status)
            logger.error('%s', 'update_fips_codes_for_all_voteraddresses statistics: ' + stats)
            status += stats
            success = True

        except Exception as ge_outer:
            logger.error('%s', 'General exception outer: ' + str(ge_outer))
            success = False

        results = {
            'status':               status,
            'success':              success,

        }
        return results


def voter_setup(request):
    """
    This is only used for sign in on the API server, and is not used for WebApp
    :param request:
    :return:
    """
    generate_voter_api_device_id_if_needed = True
    voter_api_device_id = get_voter_api_device_id(request, generate_voter_api_device_id_if_needed)

    voter_id = 0
    voter_id_found = False
    store_new_voter_api_device_id_in_cookie = True

    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_api_device_id)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        voter_id = voter_device_link.voter_id
        voter_id_found = True if positive_value_exists(voter_id) else False
        store_new_voter_api_device_id_in_cookie = False if positive_value_exists(voter_id_found) else True

    # If existing voter not found, create a new voter
    if not voter_id_found:
        # Create a new voter and return the id
        voter_manager = VoterManager()
        results = voter_manager.create_voter()

        if results['voter_created']:
            voter = results['voter']
            voter_id = voter.id

            # Now save the voter_device_link
            results = voter_device_link_manager.save_new_voter_device_link(voter_api_device_id, voter_id)

            if results['voter_device_link_created']:
                voter_device_link = results['voter_device_link']
                voter_id = voter_device_link.voter_id
                voter_id_found = True if voter_id > 0 else False
                store_new_voter_api_device_id_in_cookie = True
            else:
                voter_id = 0
                voter_id_found = False

    final_results = {
        'voter_id':                                 voter_id,
        'voter_api_device_id':                      voter_api_device_id,
        'voter_id_found':                           voter_id_found,
        'store_new_voter_api_device_id_in_cookie':  store_new_voter_api_device_id_in_cookie,
    }
    return final_results


class VoterMergeLog(models.Model):
    """
    To capture status through the process
    """
    from_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=False)
    log_datetime = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    status = models.TextField(null=True, blank=True)
    step_duration = models.PositiveIntegerField(default=None, null=True)
    step_name = models.CharField(max_length=255, default=None, null=True)
    success = models.BooleanField(default=False)
    to_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=False)


class VoterMergeStatus(models.Model):
    """
    To keep track of the process of merging voters and their attached organizations
    """
    from_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=False)
    to_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=False)
    from_linked_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=False)
    to_linked_organization_we_vote_id = models.CharField(max_length=255, default=None, null=True, unique=False)
    move_apple_user_complete = models.BooleanField(default=False)
    move_apple_user_milliseconds = models.PositiveIntegerField(default=None, null=True)
    repair_positions_complete = models.BooleanField(default=False)
    repair_positions_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_candidate_change_log_complete = models.BooleanField(default=False)
    move_candidate_change_log_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_positions_complete = models.BooleanField(default=False)
    move_positions_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_organization_complete = models.BooleanField(default=False)
    move_organization_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_friends_complete = models.BooleanField(default=False)
    move_friends_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_follows_complete = models.BooleanField(default=False)
    move_follows_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_membership_link_complete = models.BooleanField(default=False)
    move_membership_link_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_org_team_complete = models.BooleanField(default=False)
    move_org_team_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_follow_issues_complete = models.BooleanField(default=False)
    move_follow_issues_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_email_complete = models.BooleanField(default=False)
    move_email_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_sms_complete = models.BooleanField(default=False)
    move_sms_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_facebook_complete = models.BooleanField(default=False)
    move_facebook_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_twitter_complete = models.BooleanField(default=False)
    move_twitter_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_voter_change_log_complete = models.BooleanField(default=False)
    move_voter_change_log_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_voter_contact_complete = models.BooleanField(default=False)
    move_voter_contact_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_voter_plan_complete = models.BooleanField(default=False)
    move_voter_plan_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_donations_complete = models.BooleanField(default=False)
    move_donations_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_voter_guides_complete = models.BooleanField(default=False)
    move_voter_guides_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_shared_items_complete = models.BooleanField(default=False)
    move_shared_items_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_activity_notices_complete = models.BooleanField(default=False)
    move_activity_notices_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_activity_posts_complete = models.BooleanField(default=False)
    move_activity_posts_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_activity_comments_complete = models.BooleanField(default=False)
    move_activity_comments_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_campaignx_complete = models.BooleanField(default=False)
    move_campaignx_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_analytics_complete = models.BooleanField(default=False)
    move_analytics_milliseconds = models.PositiveIntegerField(default=None, null=True)
    merge_voter_complete = models.BooleanField(default=False)
    merge_voter_milliseconds = models.PositiveIntegerField(default=None, null=True)
    move_images_complete = models.BooleanField(default=False)
    move_images_milliseconds = models.PositiveIntegerField(default=None, null=True)
    send_emails_complete = models.BooleanField(default=False)
    send_emails_milliseconds = models.PositiveIntegerField(default=None, null=True)
    final_position_repair_complete = models.BooleanField(default=False)
    final_position_repair_milliseconds = models.PositiveIntegerField(default=None, null=True)
    total_merge_complete = models.BooleanField(default=False)
    total_merge_milliseconds = models.PositiveIntegerField(default=None, null=True)


class VoterMetricsManager(models.Manager):
    def fetch_voter_count_with_sign_in(self):
        return self.fetch_voter_count(
            or_filter=True, has_twitter=True, has_facebook=True, has_verified_email=True, has_verified_sms=True)

    def fetch_voter_count_with_twitter(self):
        return self.fetch_voter_count(or_filter=True, has_twitter=True)

    def fetch_voter_count_with_facebook(self):
        return self.fetch_voter_count(or_filter=True, has_facebook=True)

    def fetch_voter_count_with_verified_email(self):
        return self.fetch_voter_count(or_filter=True, has_verified_email=True)

    def fetch_voter_count_with_verified_sms(self):
        return self.fetch_voter_count(or_filter=True, has_verified_sms=True)

    @staticmethod
    def fetch_voter_count(
            or_filter=True,
            has_twitter=False,
            has_facebook=False,
            has_email=False,
            has_verified_email=False,
            has_verified_sms=False,
            by_notification_settings=0,
            by_interface_status_flags=0):
        if 'test' in sys.argv:
            # If coming from a test, we cannot use readonly
            voter_queryset = Voter.objects.all()
        else:
            voter_queryset = Voter.objects.using('readonly').all()

        voter_raw_filters = []
        if positive_value_exists(or_filter):
            if positive_value_exists(has_twitter):
                new_voter_filter = Q(twitter_id__isnull=False)
                voter_raw_filters.append(new_voter_filter)
                new_voter_filter = Q(twitter_id__gt=0)
                voter_raw_filters.append(new_voter_filter)
            if positive_value_exists(has_facebook):
                new_voter_filter = Q(facebook_id__isnull=False)
                voter_raw_filters.append(new_voter_filter)
                new_voter_filter = Q(facebook_id__gt=0)
                voter_raw_filters.append(new_voter_filter)
            if positive_value_exists(has_verified_email):
                new_voter_filter = Q(primary_email_we_vote_id__isnull=False)
                voter_raw_filters.append(new_voter_filter)
            if positive_value_exists(has_verified_sms):
                new_voter_filter = Q(primary_sms_we_vote_id__isnull=False)
                voter_raw_filters.append(new_voter_filter)

        else:
            # Add "and" filter here
            pass

        if positive_value_exists(or_filter):
            if len(voter_raw_filters):
                final_voter_filters = voter_raw_filters.pop()

                # ...and "OR" the remaining items in the list
                for item in voter_raw_filters:
                    final_voter_filters |= item

                voter_queryset = voter_queryset.filter(final_voter_filters)

        voter_count = 0
        try:
            voter_count = voter_queryset.count()
        except Exception as e:
            pass

        return voter_count

    @staticmethod
    def fetch_voter_entered_full_address(voter_id):
        count_result = None
        try:
            count_query = VoterAddress.objects.using('readonly').all()
            count_query = count_query.filter(voter_id=voter_id)
            count_query = count_query.filter(refreshed_from_google=True)
            count_result = count_query.count()
        except Exception as e:
            pass
        return positive_value_exists(count_result)

    @staticmethod
    def fetch_voters_with_plan_count(google_civic_election_id_list=[], state_code_list=[]):
        if 'test' in sys.argv:
            # If coming from a test, we cannot use readonly
            plan_queryset = VoterPlan.objects.all()
        else:
            plan_queryset = VoterPlan.objects.using('readonly').all()

        if positive_value_exists(len(google_civic_election_id_list)):
            plan_queryset = plan_queryset.filter(google_civic_election_id__in=google_civic_election_id_list)
        if positive_value_exists(len(state_code_list)):
            plan_queryset = plan_queryset.filter(state_code__in=state_code_list)
        plan_queryset = plan_queryset.values('voter_we_vote_id').distinct()

        plan_count = 0
        try:
            plan_count = plan_queryset.count()
        except Exception as e:
            pass

        return plan_count


class VoterPlan(models.Model):
    """
    One voter's plan for when they will cast their vote for one election.
    """
    objects = None
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=None, null=True, db_index=True)
    state_code = models.CharField(verbose_name="us state code", max_length=2, null=True)
    voter_display_name = models.CharField(max_length=255, default=None, null=True)
    voter_display_city_state = models.CharField(max_length=255, default=None, null=True)
    voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    voter_plan_data_serialized = models.TextField(null=True, blank=True)
    voter_plan_text = models.TextField(null=True, blank=True)
    show_to_public = models.BooleanField(default=False)
    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now_add=True, db_index=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)
