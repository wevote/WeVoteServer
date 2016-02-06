# voter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.contrib.auth.models import (BaseUserManager, AbstractBaseUser)  # PermissionsMixin
from django.core.validators import RegexValidator
from exception.models import handle_exception, handle_record_found_more_than_one_exception,\
    handle_record_not_saved_exception
from validate_email import validate_email
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, generate_voter_device_id, get_voter_device_id, \
    positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_voter_integer, fetch_site_unique_id_prefix


logger = wevote_functions.admin.get_logger(__name__)


# This way of extending the base user described here:
# https://docs.djangoproject.com/en/1.8/topics/auth/customizing/#a-full-example
# I then altered with this: http://buildthis.com/customizing-djangos-default-user-model/


# class VoterTwitterLink(models.Model):
#     voter_id
#     twitter_handle
#     confirmed_signin_date


# See AUTH_USER_MODEL in config/base.py
class VoterManager(BaseUserManager):

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
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)

        results = {
            'email_not_valid':      email_not_valid,
            'password_not_valid':   password_not_valid,
            'voter_created':        True if voter_id > 0 else False,
            'voter':                voter,
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

    def retrieve_voter_from_voter_device_id(self, voter_device_id):
        voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)

        if not voter_id:
            results = {
                'voter_found':  False,
                'voter_id':     0,
                'voter':        Voter(),
            }
            return results

        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
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
        results = self.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter = results['voter']
            return voter.we_vote_id
        else:
            return None

    def fetch_local_id_from_we_vote_id(self, voter_we_vote_id):
        results = self.retrieve_voter_by_we_vote_id(voter_we_vote_id)
        if results['voter_found']:
            voter = results['voter']
            return voter.id
        else:
            return 0

    def retrieve_voter_by_id(self, voter_id):
        email = ''
        voter_we_vote_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email, voter_we_vote_id)

    def retrieve_voter_by_we_vote_id(self, voter_we_vote_id):
        voter_id = ''
        email = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email, voter_we_vote_id)

    def retrieve_voter_by_twitter_request_token(self, twitter_request_token):
        voter_id = ''
        email = ''
        voter_we_vote_id = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email, voter_we_vote_id, twitter_request_token)

    def retrieve_voter_by_facebook_id(self, facebook_id):
        voter_id = ''
        email = ''
        voter_we_vote_id = ''
        twitter_request_token = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email, voter_we_vote_id, twitter_request_token, facebook_id)

    def retrieve_voter(self, voter_id, email='', voter_we_vote_id='', twitter_request_token='', facebook_id=''):
        voter_id = convert_to_int(voter_id)
        if not validate_email(email):
            # We do not want to search for an invalid email
            email = None
        if positive_value_exists(voter_we_vote_id):
            voter_we_vote_id = voter_we_vote_id.strip()
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_on_stage = Voter()

        try:
            if positive_value_exists(voter_id):
                voter_on_stage = Voter.objects.get(id=voter_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
            elif email is not '' and email is not None:
                voter_on_stage = Voter.objects.get(
                    email=email)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
            elif positive_value_exists(voter_we_vote_id):
                voter_on_stage = Voter.objects.get(
                    we_vote_id=voter_we_vote_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
            elif positive_value_exists(twitter_request_token):
                voter_on_stage = Voter.objects.get(
                    twitter_request_token=twitter_request_token)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
            elif positive_value_exists(facebook_id):
                voter_on_stage = Voter.objects.get(
                    facebook_id=facebook_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
            else:
                voter_id = 0
                error_result = True
        except Voter.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
        except Voter.DoesNotExist as e:
            error_result = True
            exception_does_not_exist = True

        results = {
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_found':              True if voter_id > 0 else False,
            'voter_id':                 voter_id,
            'voter':                    voter_on_stage,
        }
        return results

    def create_voter_with_voter_device_id(self, voter_device_id):
        logger.info("create_voter_with_voter_device_id(voter_device_id)")

    def clear_out_abandoned_voter_records(self):
        # We will need a method that identifies and deletes abandoned voter records that don't have enough information
        #  to ever be used
        logger.info("clear_out_abandoned_voter_records")

    def save_facebook_user_values(self, voter, facebook_id, facebook_email):
        try:
            if facebook_id == 0:
                voter.facebook_id = 0
            elif positive_value_exists(facebook_id):
                voter.facebook_id = facebook_id

            if facebook_email == '':
                voter.facebook_email = ''
            elif positive_value_exists(facebook_email):
                voter.facebook_email = facebook_email

            voter.save()
            success = True
            status = "SAVED_VOTER_TWITTER_VALUES"
        except Exception as e:
            status = "UNABLE_TO_SAVE_VOTER_TWITTER_VALUES"
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    def save_twitter_user_values(self, voter, twitter_user_object):
        try:
            # 'id': 132728535,
            voter.twitter_id = twitter_user_object.id
            # 'id_str': '132728535',
            # 'utc_offset': 32400,
            # 'description': "Cars, Musics, Games, Electronics, toys, food, etc... I'm just a typical boy!",
            # 'profile_image_url': 'http://a1.twimg.com/profile_images/1213351752/_2_2__normal.jpg',
            voter.twitter_profile_image_url_https = twitter_user_object.profile_image_url_https
            # 'profile_background_image_url': 'http://a2.twimg.com/a/1294785484/images/themes/theme15/bg.png',
            # 'screen_name': 'jaeeeee',
            voter.twitter_screen_name = twitter_user_object.screen_name
            # 'lang': 'en',
            # 'name': 'Jae Jung Chung',
            # 'url': 'http://www.carbonize.co.kr',
            # 'time_zone': 'Seoul',
            voter.save()
            success = True
            status = "SAVED_VOTER_TWITTER_VALUES"
        except Exception as e:
            status = "UNABLE_TO_SAVE_VOTER_TWITTER_VALUES"
            success = False
            handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)

        results = {
            'status':   status,
            'success':  success,
            'voter':    voter,
        }
        return results

    def update_voter_photos(self, voter_id, facebook_profile_image_url_https, facebook_photo_variable_exists):
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


class Voter(AbstractBaseUser):
    """
    A fully featured User model with admin-compliant permissions that uses
    a full-length email field as the username.

    No fields are required, since at its very simplest, we only need the voter_id based on a voter_device_id.
    """
    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our voter info with other
    # organizations running the we_vote server
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "voter", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_org_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=True)

    # Redefine the basic fields that would normally be defined in User
    # username = models.CharField(unique=True, max_length=20, validators=[alphanumeric])  # Increase max_length to 255
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True, null=True, blank=True)
    first_name = models.CharField(verbose_name='first name', max_length=255, null=True, blank=True)
    last_name = models.CharField(verbose_name='last name', max_length=255, null=True, blank=True)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_verified_volunteer = models.BooleanField(default=False)

    # Facebook session information
    facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    fb_username = models.CharField(unique=True, max_length=20, validators=[alphanumeric], null=True)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of image from facebook', blank=True, null=True)

    # Twitter session information
    twitter_id = models.BigIntegerField(verbose_name="twitter big integer id", null=True, blank=True)
    twitter_screen_name = models.CharField(verbose_name='twitter screen name / handle',
                                           max_length=255, null=True, unique=False)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of logo from twitter', blank=True, null=True)

    twitter_request_token = models.TextField(verbose_name='twitter request token', null=True, blank=True)
    twitter_request_secret = models.TextField(verbose_name='twitter request secret', null=True, blank=True)
    twitter_access_token = models.TextField(verbose_name='twitter access token', null=True, blank=True)
    twitter_access_secret = models.TextField(verbose_name='twitter access secret', null=True, blank=True)
    twitter_connection_active = models.BooleanField(default=False)

    # Custom We Vote fields
    middle_name = models.CharField(max_length=255, null=True, blank=True)
#     image_displayed
#     image_twitter
#     image_facebook
#     blocked
#     flags (ex/ signed_in)
#     password_hashed
#     password_reset_key
#     password_reset_request_time
#     last_activity

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
            self.email = self.email.lower().strip()
            if not validate_email(self.email):  # ...make sure it is a valid email
                # If it isn't a valid email, don't save the value as an email -- just save a blank field
                self.email = None
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_voter_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "voter" = tells us this is a unique id for an org
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}voter{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
            # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        super(Voter, self).save(*args, **kwargs)

    def get_full_name(self):
        full_name = self.first_name if positive_value_exists(self.first_name) else ''
        full_name += " " if positive_value_exists(self.first_name) and positive_value_exists(self.last_name) else ''
        full_name += self.last_name if positive_value_exists(self.last_name) else ''
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
        # return self.get_full_name(self)
        return self.email

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

    @property
    def is_staff(self):
        """
        Is the user a member of staff?
        """
        # Simplest possible answer: All admins are staff
        return self.is_admin

    def voter_photo_url(self):
        if self.facebook_profile_image_url_https:
            return self.facebook_profile_image_url_https
        elif self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https
        return ''

    def signed_in_personal(self):
        if positive_value_exists(self.email) or positive_value_exists(self.facebook_id) or \
                positive_value_exists(self.twitter_access_token) or positive_value_exists(self.is_authenticated()):
            return True
        return False


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
    voter_id = models.IntegerField(verbose_name="voter unique identifier", null=False, blank=False, unique=False)

    def generate_voter_device_id(self):
        # A simple mapping to this function
        return generate_voter_device_id()


class VoterDeviceLinkManager(models.Model):
    """
    In order to start gathering information about a voter prior to authentication, we use a long randomized string
    stored as a browser cookie. As soon as we get any other identifiable information from a voter (like an email
    address), we capture that so the Voter record can be portable among devices. Note that any voter might be using
    We Vote from different browsers. The VoterDeviceLink links one or more voter_device_id's to one voter_id.

    Since (prior to authentication) every voter_device_id will have its own voter_id record, we merge and delete Voter
    records whenever we can.
    """

    def __str__(self):              # __unicode__ on Python 2
        return "Voter Device Id Manager"

    def retrieve_voter_device_link_from_voter_device_id(self, voter_device_id):
        voter_id = 0
        voter_device_link_id = 0
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id, voter_id, voter_device_link_id)

        return results

    def retrieve_voter_device_link(self, voter_device_id, voter_id, voter_device_link_id):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_device_link_on_stage = VoterDeviceLink()

        try:
            if voter_device_id is not '':
                voter_device_link_on_stage = VoterDeviceLink.objects.get(voter_device_id=voter_device_id)
                voter_device_link_id = voter_device_link_on_stage.id
            elif voter_id > 0:
                voter_device_link_on_stage = VoterDeviceLink.objects.get(voter_id=voter_id)
                # If still here, we found an existing position
                voter_device_link_id = voter_device_link_on_stage.id
            elif voter_device_link_id > 0:
                voter_device_link_on_stage = VoterDeviceLink.objects.get(id=voter_device_link_id)
                # If still here, we found an existing position
                voter_device_link_id = voter_device_link_on_stage.id
            else:
                voter_device_link_id = 0
        except VoterDeviceLink.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
        except VoterDeviceLink.DoesNotExist:
            error_result = True
            exception_does_not_exist = True

        results = {
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'voter_device_link_found':      True if voter_device_link_id > 0 else False,
            'voter_device_link':            voter_device_link_on_stage,
        }
        return results

    def save_new_voter_device_link(self, voter_device_id, voter_id):
        error_result = False
        exception_record_not_saved = False
        missing_required_variables = False
        voter_device_link_on_stage = VoterDeviceLink()
        voter_device_link_id = 0

        try:
            if voter_device_id is not '' and voter_id > 0:
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


# This method *just* returns the voter_id or 0
def fetch_voter_id_from_voter_device_link(voter_device_id):
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_device_id)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        return voter_device_link.voter_id
    return 0


def retrieve_voter_authority(request):
    voter_device_id = get_voter_device_id(request)
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    if results['voter_found']:
        voter = results['voter']
        authority_results = {
            'voter_found':              True,
            'is_active':                positive_value_exists(voter.is_active),
            'is_admin':                 positive_value_exists(voter.is_admin),
            'is_verified_volunteer':    positive_value_exists(voter.is_verified_volunteer),
        }
        return authority_results

    authority_results = {
        'voter_found':              False,
        'is_active':                False,
        'is_admin':                 False,
        'is_verified_volunteer':    False,
    }
    return authority_results


def voter_has_authority(request, authority_required):
    authority_results = retrieve_voter_authority(request)
    if not positive_value_exists(authority_results['is_active']):
        return False
    if 'admin' in authority_required:
        if positive_value_exists(authority_results['is_admin']):
            return True
    if 'verified_volunteer' in authority_required:
        if positive_value_exists(authority_results['is_verified_volunteer']) or \
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
    voter_id = models.IntegerField(verbose_name="voter unique identifier", null=False, blank=False, unique=False)
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

    refreshed_from_google = models.BooleanField(
        verbose_name="have normalized fields been updated from Google since address change?", default=False)


class VoterAddressManager(models.Model):

    def __unicode__(self):
        return "VoterAddressManager"

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

    def retrieve_address(self, voter_address_id, voter_id, address_type):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_address_on_stage = VoterAddress()

        try:
            if positive_value_exists(voter_address_id):
                voter_address_on_stage = VoterAddress.objects.get(id=voter_address_id)
                voter_address_id = voter_address_on_stage.id
            elif positive_value_exists(voter_id) and address_type in (BALLOT_ADDRESS, MAILING_ADDRESS,
                                                                      FORMER_BALLOT_ADDRESS):
                voter_address_on_stage = VoterAddress.objects.get(voter_id=voter_id, address_type=address_type)
                # If still here, we found an existing address
                voter_address_id = voter_address_on_stage.id
        except VoterAddress.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
        except VoterAddress.DoesNotExist:
            error_result = True
            exception_does_not_exist = True

        results = {
            'success':                  True if voter_address_id > 0 else False,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_address_found':      True if voter_address_id > 0 else False,
            'voter_address_id':         voter_address_id,
            'voter_address':            voter_address_on_stage,
        }
        return results

    # # TODO TEST THIS
    # def retrieve_addresses(self, voter_id):
    #     error_result = False
    #     exception_does_not_exist = False
    #     # voter_addresses_on_stage = # How to typecast?
    #     number_of_addresses = 0
    #
    #     try:
    #         if voter_id > 0:
    #             voter_addresses_on_stage = VoterAddress.objects.get(voter_id=voter_id)
    #             number_of_addresses = len(voter_addresses_on_stage)
    #     except VoterAddress.DoesNotExist:
    #         error_result = True
    #         exception_does_not_exist = True
    #
    #     results = {
    #         'error_result':             error_result,
    #         'DoesNotExist':             exception_does_not_exist,
    #         'voter_addresses_found':    True if number_of_addresses > 0 else False,
    #         'voter_addresses_on_stage': voter_addresses_on_stage,
    #         'number_of_addresses':      number_of_addresses,
    #     }
    #     return results

    def update_or_create_voter_address(self, voter_id, address_type, raw_address_text):
        """
        NOTE: This approach won't support multiple FORMER_BALLOT_ADDRESS
        :param voter_id:
        :param address_type:
        :param raw_address_text:
        :return:
        """
        status = ''
        exception_multiple_object_returned = False
        new_address_created = False

        if voter_id > 0 and address_type in (BALLOT_ADDRESS, MAILING_ADDRESS, FORMER_BALLOT_ADDRESS):
            try:
                updated_values = {
                    # Values we search against
                    'voter_id': voter_id,
                    'address_type': address_type,
                    # The rest of the values
                    'text_for_map_search': raw_address_text,
                    'latitude': None,
                    'longitude': None,
                    'normalized_line1': None,
                    'normalized_line2': None,
                    'normalized_city': None,
                    'normalized_state': None,
                    'normalized_zip': None,
                    'refreshed_from_google': False,
                }

                voter_address_on_stage, new_address_created = VoterAddress.objects.update_or_create(
                    voter_id__exact=voter_id, address_type=address_type, defaults=updated_values)
                success = True
            except VoterAddress.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_ADDRESSES_FOUND'
                exception_multiple_object_returned = True
        else:
            success = False
            status = 'MISSING_VOTER_ID_OR_ADDRESS_TYPE'

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_address_saved':      success,
            'address_type':             address_type,
            'new_address_created':      new_address_created,
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


def voter_setup(request):
    generate_voter_device_id_if_needed = True
    voter_device_id = get_voter_device_id(request, generate_voter_device_id_if_needed)
    voter_id = 0
    voter_id_found = False
    store_new_voter_device_id_in_cookie = True

    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_device_link_manager.retrieve_voter_device_link_from_voter_device_id(voter_device_id)
    if results['voter_device_link_found']:
        voter_device_link = results['voter_device_link']
        voter_id = voter_device_link.voter_id
        voter_id_found = True if positive_value_exists(voter_id) else False
        store_new_voter_device_id_in_cookie = False if positive_value_exists(voter_id_found) else True

    # If existing voter not found, create a new voter
    if not voter_id_found:
        # Create a new voter and return the id
        voter_manager = VoterManager()
        results = voter_manager.create_voter()

        if results['voter_created']:
            voter = results['voter']
            voter_id = voter.id

            # Now save the voter_device_link
            results = voter_device_link_manager.save_new_voter_device_link(voter_device_id, voter_id)

            if results['voter_device_link_created']:
                voter_device_link = results['voter_device_link']
                voter_id = voter_device_link.voter_id
                voter_id_found = True if voter_id > 0 else False
            else:
                voter_id = 0
                voter_id_found = False

    final_results = {
        'voter_id':                 voter_id,
        'voter_device_id':          voter_device_id,
        'voter_id_found':           voter_id_found,
        'store_new_voter_device_id_in_cookie':   store_new_voter_device_id_in_cookie,
    }
    return final_results
