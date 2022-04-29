# voter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import (models, IntegrityError)
from django.db.models import Q
from django.contrib.auth.models import (BaseUserManager, AbstractBaseUser)  # PermissionsMixin
from django.core.validators import RegexValidator
from django.utils.timezone import now
from datetime import datetime, timedelta
from apple.models import AppleUser
from exception.models import handle_exception, handle_record_found_more_than_one_exception,\
    handle_record_not_saved_exception
from import_export_facebook.models import FacebookManager
import pytz
from sms.models import SMSManager
import string
import sys
from twitter.models import TwitterUserManager
from validate_email import validate_email
import wevote_functions.admin
from wevote_functions.functions import extract_state_code_from_address_string, convert_to_int, generate_random_string, \
    generate_voter_device_id, get_voter_api_device_id, positive_value_exists
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
NOTIFICATION_NEWSLETTER_OPT_IN = 1  # "I would like to receive the We Vote newsletter"
# NOTIFICATION_FRIEND_REQUESTS = n/a,  # In App: "New friend requests, and responses to your requests"
NOTIFICATION_FRIEND_REQUESTS_EMAIL = 2  # Email: "New friend requests, and responses to your requests"
NOTIFICATION_FRIEND_REQUESTS_SMS = 4  # SMS: "New friend requests, and responses to your requests"
# NOTIFICATION_SUGGESTED_FRIENDS = n/a  # In App: "Suggestions of people you may know"
NOTIFICATION_SUGGESTED_FRIENDS_EMAIL = 8  # Email: "Suggestions of people you may know"
NOTIFICATION_SUGGESTED_FRIENDS_SMS = 16  # SMS: "Suggestions of people you may know"
# NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT = n/a  # In App: "Friends' opinions (on your ballot)"
NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_EMAIL = 32  # Email: "Friends' opinions (on your ballot)"
NOTIFICATION_FRIEND_OPINIONS_YOUR_BALLOT_SMS = 64  # SMS: "Friends' opinions (on your ballot)"
NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS = 128  # In App: "Friends' opinions (other regions)"
NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_EMAIL = 256  # Email: "Friends' opinions (other regions)"
NOTIFICATION_FRIEND_OPINIONS_OTHER_REGIONS_SMS = 512  # SMS: "Friends' opinions (other regions)"
# NOTIFICATION_VOTER_DAILY_SUMMARY = n/a  # In App: When a friend posts something, or reacts to another post
NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL = 1024  # Email: When a friend posts something, or reacts to another post
NOTIFICATION_VOTER_DAILY_SUMMARY_SMS = 2048  # SMS: When a friend posts something, or reacts to another post

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

    def alter_linked_organization_we_vote_id(self, voter, linked_organization_we_vote_id=None):
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

    def update_or_create_contact_email_augmented(
            self,
            checked_against_open_people=None,
            checked_against_sendgrid=None,
            checked_against_snovio=None,
            checked_against_targetsmart=None,
            email_address_text='',
            existing_contact_email_augmented_dict={},
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

    def update_or_create_voter_contact_email(
            self,
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
            last_name=None,
            middle_name=None,
            state_code=None,
            zip_code=None,
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
        :param last_name:
        :param middle_name:
        :param state_code:
        :param zip_code:
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
                        # state_code=state_code,
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
            logger.debug("create_voter IntegrityError exception (#1): " + str(e))
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
                logger.debug("create_voter IntegrityError exception (#2): " + str(e))
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                logger.debug("create_voter general exception (#1): " + str(e))


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

    def create_developer(self, first_name, last_name, email, password):
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

    def create_new_voter_account(self, first_name, last_name, email, password, is_admin, is_analytics_admin,
                                 is_partner_organization, is_political_data_manager, is_political_data_viewer,
                                 is_verified_volunteer):
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
        :return:
        """
        voter = Voter()
        success = False
        status = "Failed to create voter"
        duplicate_email = False
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
            voter.is_active = True
            voter.save()
            success = True
            status = "Created voter " + voter.we_vote_id
            logger.debug("create_new_voter_account successfully created (voter) : " + first_name)

        except IntegrityError as e:
            status += ", " + str(e)
            handle_record_not_saved_exception(e, logger=logger)
            print("create_new_voter_account IntegrityError exception:" + str(e))
            if "voter_voter_email_key" in str(e):
                duplicate_email = True
        except Exception as e:
            status += ", " + str(e)
            handle_record_not_saved_exception(e, logger=logger)
            logger.debug("create_new_voter_account general exception: " + str(e))

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

    def duplicate_voter(self, voter):
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
            voter.twitter_access_secret = None
            voter.twitter_access_token = None
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

    def retrieve_contact_email_augmented_list(
            self,
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

    def retrieve_voter_contact_email_list(self, imported_by_voter_we_vote_id='', read_only=True):
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
                email_addresses_returned_list.append(voter_contact_email.email_address_text)

        results = {
            'success':                          success,
            'status':                           status,
            'email_addresses_returned_list':    email_addresses_returned_list,
            'voter_contact_email_list':         voter_contact_email_list,
            'voter_contact_email_list_found':   voter_contact_email_list_found,
        }
        return results

    def retrieve_voter_from_voter_device_id(self, voter_device_id, read_only=False):
        voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)

        if not voter_id:
            results = {
                'voter_found':  False,
                'voter_id':     0,
                'voter':        Voter(),
            }
            return results

        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id, read_only=read_only)
        if results['voter_found']:
            voter_on_stage = results['voter']
            voter_on_stage_found = True
            voter_id = results['voter_id']
        else:
            voter_on_stage = Voter()
            voter_on_stage_found = False
            voter_id = 0

        results = {
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

    def fetch_facebook_id_from_voter_we_vote_id(self, voter_we_vote_id):
        if positive_value_exists(voter_we_vote_id):
            facebook_manager = FacebookManager()
            facebook_id = facebook_manager.fetch_facebook_id_from_voter_we_vote_id(voter_we_vote_id)
        else:
            facebook_id = 0

        return facebook_id

    def fetch_twitter_id_from_voter_we_vote_id(self, voter_we_vote_id):
        if positive_value_exists(voter_we_vote_id):
            twitter_user_manager = TwitterUserManager()
            voter_twitter_id = twitter_user_manager.fetch_twitter_id_from_voter_we_vote_id(voter_we_vote_id)
        else:
            voter_twitter_id = ''

        return voter_twitter_id

    def fetch_twitter_handle_from_voter_we_vote_id(self, voter_we_vote_id):
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

    def this_voter_has_first_or_last_name_saved(self, voter):
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
            facebook_id)
        if not facebook_link_results['facebook_link_to_voter_found']:
            # We don't have an official FacebookLinkToVoter, so we don't want to clean up any caching
            status += "FACEBOOK_LINK_TO_VOTER_NOT_FOUND-CACHING_REPAIR_NOT_EXECUTED "
        else:
            # Is there an official FacebookLinkToVoter for this Twitter account? If so, update the information.
            facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']

            # Loop through all of the voters that have any of these fields set:
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
                facebook_link_to_voter.voter_we_vote_id)
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

                # Loop through all of the voters that have any of these fields set:
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

    def retrieve_voter_by_id(self, voter_id, read_only=False):
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, read_only=read_only)

    def retrieve_voter_by_email(self, email, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email=email, read_only=read_only)

    def retrieve_voter_by_we_vote_id(self, voter_we_vote_id, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, voter_we_vote_id=voter_we_vote_id, read_only=read_only)

    def retrieve_voter_by_twitter_request_token(self, twitter_request_token):
        voter_id = ''
        email = ''
        voter_we_vote_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email, voter_we_vote_id, twitter_request_token)

    def retrieve_voter_by_facebook_id(self, facebook_id, read_only=False):
        voter_id = ''
        voter_we_vote_id = ''

        facebook_manager = FacebookManager()
        facebook_retrieve_results = facebook_manager.retrieve_facebook_link_to_voter(facebook_id)
        if facebook_retrieve_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_retrieve_results['facebook_link_to_voter']
            voter_we_vote_id = facebook_link_to_voter.voter_we_vote_id

        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, voter_we_vote_id=voter_we_vote_id, read_only=read_only)

    def retrieve_voter_by_facebook_id_old(self, facebook_id):
        """
        This method should only be used to heal old data.
        :param facebook_id:
        :return:
        """
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, facebook_id=facebook_id)

    def retrieve_voter_by_twitter_id(self, twitter_id, read_only=False):
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

    def retrieve_voter_by_sms(self, normalized_sms_phone_number, read_only=False):
        voter_id = ''
        voter_we_vote_id = ''

        sms_manager = SMSManager()
        results = sms_manager.retrieve_voter_we_vote_id_from_normalized_sms_phone_number(normalized_sms_phone_number)
        if results['voter_we_vote_id_found']:
            voter_we_vote_id = results['voter_we_vote_id']

        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, voter_we_vote_id=voter_we_vote_id, read_only=read_only)

    def retrieve_voter_by_twitter_id_old(self, twitter_id):
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

    def retrieve_voter_by_organization_we_vote_id(self, organization_we_vote_id, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, organization_we_vote_id=organization_we_vote_id,
                                            read_only=read_only)

    def retrieve_voter_by_primary_email_we_vote_id(self, primary_email_we_vote_id, read_only=False):
        voter_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, primary_email_we_vote_id=primary_email_we_vote_id,
                                            read_only=read_only)

    def retrieve_voter(self, voter_id, email='', voter_we_vote_id='', twitter_request_token='', facebook_id=0,
                       twitter_id=0, sms='', organization_we_vote_id='', primary_email_we_vote_id='', read_only=False):
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

    def retrieve_voter_list_with_emails(self):
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

    def retrieve_voter_list_by_permissions(
            self,
            is_admin=False,
            is_analytics_admin=False,
            is_partner_organization=False,
            is_political_data_manager=False,
            is_political_data_viewer=False,
            is_verified_volunteer=False,
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
                and not positive_value_exists(is_verified_volunteer):
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

    def retrieve_voter_list_by_name(self, first_name, last_name):
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

    def retrieve_voter_list_by_we_vote_id_list(self, voter_we_vote_id_list=[], read_only=True):
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

    def retrieve_voter_plan_list(self, google_civic_election_id=0, voter_we_vote_id='', read_only=True):
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

    def create_voter_with_voter_device_id(self, voter_device_id):
        logger.info("create_voter_with_voter_device_id(voter_device_id)")

    def clear_out_abandoned_voter_records(self):
        # We will need a method that identifies and deletes abandoned voter records that don't have enough information
        #  to ever be used
        logger.info("clear_out_abandoned_voter_records")

    def remove_voter_cached_email_entries_from_email_address_object(self, email_address_object):
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

    def remove_voter_cached_sms_entries_from_sms_phone_number(self, sms_phone_number):
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

    def save_facebook_user_values(self, voter, facebook_auth_response,
                                  cached_facebook_profile_image_url_https=None,
                                  we_vote_hosted_profile_image_url_large=None,
                                  we_vote_hosted_profile_image_url_medium=None,
                                  we_vote_hosted_profile_image_url_tiny=None):
        status = ''
        try:
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

    def save_facebook_user_values_from_dict(self, voter, facebook_user_dict,
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

    def save_twitter_user_values(self, voter, twitter_user_object,
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
            elif hasattr(twitter_user_object, "profile_image_url_https") and \
                    positive_value_exists(twitter_user_object.profile_image_url_https):
                voter.twitter_profile_image_url_https = twitter_user_object.profile_image_url_https
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
            # 'screen_name': 'jaeeeee',
            if hasattr(twitter_user_object, "screen_name") and positive_value_exists(twitter_user_object.screen_name):
                voter.twitter_screen_name = twitter_user_object.screen_name
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

    def save_twitter_user_values_from_twitter_auth_response(self, voter, twitter_auth_response,
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
            # 'screen_name': 'jaeeeee',
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

    def save_twitter_user_values_from_dict(self, voter, twitter_user_dict,
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
            elif 'profile_image_url_https' in twitter_user_dict:
                voter.twitter_profile_image_url_https = twitter_user_dict['profile_image_url_https']
            # 'profile_background_image_url': 'http://a2.twimg.com/a/1294785484/images/themes/theme15/bg.png',
            # 'screen_name': 'jaeeeee',
            if 'screen_name' in twitter_user_dict:
                voter.twitter_screen_name = twitter_user_dict['screen_name']
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

    def update_contact_email_augmented_list_not_found(
            self,
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
            twitter_json={},
            cached_twitter_profile_image_url_https='',
            we_vote_hosted_profile_image_url_large='',
            we_vote_hosted_profile_image_url_medium='',
            we_vote_hosted_profile_image_url_tiny=''):
        """
        Update existing voter entry with details retrieved from the Twitter API
        :param twitter_id:
        :param twitter_json:
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
                voter, twitter_json,
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

    def update_voter_by_object(
            self,
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

    def update_voter_email_ownership_verified(self, voter, email_address_object):
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

    def update_voter_sms_ownership_verified(self, voter, sms_phone_number):
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

    def update_voter_with_facebook_link_verified(self, voter, facebook_user_id, facebook_email):
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

    def update_voter_with_twitter_link_verified(self, voter, twitter_id):
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
        verbose_name="we vote id for linked organization", max_length=255, null=True, blank=True, unique=True)

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

    # Once a voter takes a position, follows an org or other save-worthy data, mark this true
    data_to_preserve = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_analytics_admin = models.BooleanField(default=False)
    is_partner_organization = models.BooleanField(default=False)
    is_political_data_manager = models.BooleanField(default=False)
    is_political_data_viewer = models.BooleanField(default=False)
    is_verified_volunteer = models.BooleanField(default=False)

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
        max_length=10, choices=PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES, default=PROFILE_IMAGE_TYPE_UNKNOWN)
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
    twitter_access_token = models.TextField(verbose_name='twitter access token', null=True, blank=True)
    twitter_access_secret = models.TextField(verbose_name='twitter access secret', null=True, blank=True)
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
    #  since we updated the NOTIFICATION_SETTINGS_FLAGS_DEFAULT to match what we want after all of the maintenance
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

    def has_perm(self, perm, obj=None):
        """
        Does the user have a specific permission?
        """
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
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
        if self.signed_in_with_apple() or \
                self.signed_in_with_email() or \
                self.signed_in_facebook() or \
                self.signed_in_with_sms_phone_number() or \
                self.signed_in_twitter():
            return True
        return False

    def signed_in_facebook(self):
        facebook_manager = FacebookManager()
        facebook_link_results = facebook_manager.retrieve_facebook_link_to_voter(0, self.we_vote_id)
        if facebook_link_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_link_results['facebook_link_to_voter']
            if positive_value_exists(facebook_link_to_voter.facebook_user_id):
                return True
        return False

    def signed_in_google(self):
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
            apple_object = AppleUser.objects.get(voter_we_vote_id__iexact=self.we_vote_id)
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
    last_name = models.CharField(max_length=255, default=None, null=True)
    middle_name = models.CharField(max_length=255, default=None, null=True)
    state_code = models.CharField(max_length=2, default=None, null=True, db_index=True)
    voter_we_vote_id = models.CharField(max_length=255, default=None, null=True, db_index=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    zip_code = models.CharField(max_length=10, default=None, null=True)


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

    def generate_voter_device_id(self):
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

    def clear_secret_key(self, email_secret_key='', sms_secret_key=''):
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

    def delete_all_voter_device_links(self, voter_device_id):
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

    def delete_all_voter_device_links_by_voter_id(self, voter_id):
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

    def delete_voter_device_link(self, voter_device_id):
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

    def retrieve_voter_device_link_from_voter_device_id(self, voter_device_id, read_only=False):
        voter_id = 0
        voter_device_link_id = 0
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.retrieve_voter_device_link(
            voter_device_id, voter_id=voter_id, voter_device_link_id=voter_device_link_id, read_only=read_only)
        return results

    def retrieve_voter_device_link(self, voter_device_id, voter_id=0, voter_device_link_id=0, read_only=False):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        status = ""
        voter_device_link_on_stage = VoterDeviceLink()

        try:
            if positive_value_exists(voter_device_id):
                status += " RETRIEVE_VOTER_DEVICE_LINK-GET_BY_VOTER_DEVICE_ID "
                if read_only and not 'test' in sys.argv:
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

        results = {
            'success':                      True if not error_result else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'voter_device_link_found':      True if voter_device_link_id > 0 else False,
            'voter_device_link':            voter_device_link_on_stage,
        }
        return results

    def retrieve_voter_device_link_list(self, google_civic_election_id=0, voter_id=0):
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

    def retrieve_voter_secret_code_up_to_date(self, voter_device_id=''):
        """
        We allow a voter 6 attempts/5 failures (NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE)
        to enter each secret_code before we require the secret code be regenerated by the voter.
        For each voter_device_id we allow 25 (NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME) consecutive failures
        before we lock out the voter_device_id. This is in order to protect against brute force attacks.
        :param voter_device_id:
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
            if voter_device_link.secret_code_number_of_failed_tries_all_time is not None \
                    and voter_device_link.secret_code_number_of_failed_tries_all_time > \
                    NUMBER_OF_FAILED_TRIES_ALLOWED_ALL_TIME:
                secret_code_system_locked_for_this_voter_device_id = True
            else:
                if voter_device_link.secret_code_number_of_failed_tries_for_this_code is not None \
                        and voter_device_link.secret_code_number_of_failed_tries_for_this_code > \
                        NUMBER_OF_FAILED_TRIES_ALLOWED_PER_SECRET_CODE:
                    # If voter has used up the number of attempts to enter the secret code, create new secret code
                    results = self.update_voter_device_link_with_new_secret_code(voter_device_link)
                    status += results['status']
                    if results['voter_device_link_updated']:
                        voter_device_link = results['voter_device_link']
                        secret_code = voter_device_link.secret_code
                if voter_device_link.date_secret_code_generated \
                        and positive_value_exists(voter_device_link.secret_code):
                    # We have an existing secret code. Verify it is still valid.
                    timezone = pytz.timezone("America/Los_Angeles")
                    datetime_now = timezone.localize(datetime.now())
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
                    results = self.update_voter_device_link_with_new_secret_code(voter_device_link)
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

    def save_new_voter_device_link(self, voter_device_id, voter_id):
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

    def update_voter_device_link_with_new_secret_code(self, voter_device_link):
        return self.update_voter_device_link(voter_device_link, generate_new_secret_code=True)

    def update_voter_device_link_with_email_secret_key(self, voter_device_link, email_secret_key=False):
        return self.update_voter_device_link(voter_device_link, email_secret_key=email_secret_key)

    def update_voter_device_link_with_sms_secret_key(self, voter_device_link, sms_secret_key=False):
        return self.update_voter_device_link(voter_device_link, sms_secret_key=sms_secret_key)

    def update_voter_device_link(
            self,
            voter_device_link,
            voter_object=None,
            google_civic_election_id=0,
            state_code='',
            generate_new_secret_code=False,
            delete_secret_code=False,
            email_secret_key=False,
            sms_secret_key=False):
        """
        Update existing voter_device_link with a new voter_id or google_civic_election_id
        """
        status = ""
        success = True
        error_result = False
        exception_record_not_saved = False
        missing_required_variables = False
        voter_device_link_id = 0

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
                        timezone = pytz.timezone("America/Los_Angeles")
                        datetime_now = timezone.localize(datetime.now())
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
    }
    return authority_results


def voter_has_authority(request, authority_required, authority_results=None):
    if not authority_results:
        authority_results = retrieve_voter_authority(request)
    if not positive_value_exists(authority_results['is_active']):
        return False
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    if 'admin' in authority_required:
        if positive_value_exists(authority_results['is_admin']):
            return True
    if 'analytics_admin' in authority_required:
        if positive_value_exists(authority_results['is_analytics_admin']) or \
                positive_value_exists(authority_results['is_admin']):
            return True
    if 'partner_organization' in authority_required:
        if positive_value_exists(authority_results['is_partner_organization']) or \
                positive_value_exists(authority_results['is_political_data_manager']) or \
                positive_value_exists(authority_results['is_admin']):
            return True
    if 'political_data_manager' in authority_required:
        if positive_value_exists(authority_results['is_political_data_manager']) or \
                positive_value_exists(authority_results['is_admin']):
            return True
    if 'political_data_viewer' in authority_required:
        if positive_value_exists(authority_results['is_political_data_viewer']) or \
                positive_value_exists(authority_results['is_analytics_admin']) or \
                positive_value_exists(authority_results['is_verified_volunteer']) or \
                positive_value_exists(authority_results['is_political_data_manager']) or \
                positive_value_exists(authority_results['is_admin']):
            return True
    if 'verified_volunteer' in authority_required:
        if positive_value_exists(authority_results['is_verified_volunteer']) or \
                positive_value_exists(authority_results['is_analytics_admin']) or \
                positive_value_exists(authority_results['is_political_data_manager']) or \
                positive_value_exists(authority_results['is_admin']):
            return True
    return False

# class VoterJurisdictionLink(models.Model):
#     """
#     All of the jurisdictions the Voter is in
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
    voter_id = models.BigIntegerField(
        verbose_name="voter unique identifier", null=False, blank=False, unique=False, db_index=True)
    address_type = models.CharField(
        verbose_name="type of address", max_length=1, choices=ADDRESS_TYPE_CHOICES, default=BALLOT_ADDRESS)

    text_for_map_search = models.CharField(max_length=255, blank=False, null=False, verbose_name='address as entered')

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

    def retrieve_address(self, voter_address_id, voter_id=0, address_type=''):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_address_on_stage = VoterAddress()
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

    def retrieve_ballot_address_from_voter_id(self, voter_id):
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

    def retrieve_voter_address_list(self, google_civic_election_id=0, voter_id=0):
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
        exception_multiple_object_returned = False
        new_address_created = False
        voter_address_has_value = False
        voter_address_on_stage = None
        voter_address_on_stage_found = False
        google_civic_election_id = google_civic_election_id if positive_value_exists(google_civic_election_id) else 0

        if positive_value_exists(voter_id) and address_type in (BALLOT_ADDRESS, MAILING_ADDRESS, FORMER_BALLOT_ADDRESS):
            try:
                updated_values = {
                    # Values we search against
                    'voter_id': voter_id,
                    'address_type': address_type,
                    # The rest of the values are to be saved
                    'text_for_map_search':      raw_address_text,
                    'latitude':                 None,
                    'longitude':                None,
                    'normalized_line1':         None,
                    'normalized_line2':         None,
                    'normalized_city':          None,
                    'normalized_state':         None,
                    'normalized_zip':           None,
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
                success = True
                status += "UPDATE_OR_CREATE_SUCCESSFUL "
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

        if results['success']:
            voter_address = results['voter_address']

            try:
                voter_address.normalized_line1 = voter_address_dict['line1']
                voter_address.normalized_city = voter_address_dict['city']
                voter_address.normalized_state = voter_address_dict['state']
                voter_address.normalized_zip = voter_address_dict['zip']
                voter_address.refreshed_from_google = True
                voter_address.save()
                status = "SAVED_VOTER_ADDRESS_WITH_NORMALIZED_VALUES"
                success = True
            except Exception as e:
                status = "UNABLE_TO_SAVE_VOTER_ADDRESS_WITH_NORMALIZED_VALUES"
                success = False
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        else:
            # If here, we were unable to find pre-existing VoterAddress
            status = "UNABLE_TO_FIND_VOTER_ADDRESS"
            voter_address = VoterAddress()  # TODO Finish this for "create new" case
            success = False

        results = {
            'status':   status,
            'success':  success,
            'voter_address': voter_address,
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

    def fetch_address_count(self, or_filter=True,
                            refreshed_from_google=False, has_election=False, google_civic_election_id=False,
                            has_latitude_longitude=False, longer_than_this_number=0):
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
            'voter_address':            VoterAddress(),
        }
        return results

    def duplicate_voter_address(self, voter_address, new_voter_id):
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

    def fetch_voter_count(self, or_filter=True,
                          has_twitter=False, has_facebook=False, has_email=False, has_verified_email=False,
                          has_verified_sms=False,
                          by_notification_settings=0, by_interface_status_flags=0):
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

    def fetch_voter_entered_full_address(self, voter_id):
        count_result = None
        try:
            count_query = VoterAddress.objects.using('readonly').all()
            count_query = count_query.filter(voter_id=voter_id)
            count_query = count_query.filter(refreshed_from_google=True)
            count_result = count_query.count()
        except Exception as e:
            pass
        return positive_value_exists(count_result)

    def fetch_voters_with_plan_count(self, google_civic_election_id_list=[], state_code_list=[]):
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

