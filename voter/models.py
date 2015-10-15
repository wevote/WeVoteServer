# voter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser, PermissionsMixin
)
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from exception.models import handle_exception, handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
# from region_jurisdiction.models import Jurisdiction
import wevote_functions.admin
from wevote_functions.models import convert_to_int, generate_voter_device_id
from validate_email import validate_email


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
        now = timezone.now()
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

    def retrieve_voter_from_voter_device_id(self, voter_device_id):
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        voter_id = results['voter_id']

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

    def retrieve_voter_by_id(self, voter_id):
        email = ''
        voter_manager = VoterManager()
        return voter_manager.retrieve_voter(voter_id, email)

    def retrieve_voter(self, voter_id, email):
        voter_id = convert_to_int(voter_id)
        if not validate_email(email):
            # We do not want to search for an invalid email
            email = None
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_on_stage = Voter()

        try:
            if voter_id > 0:
                voter_on_stage = Voter.objects.get(id=voter_id)
                # If still here, we found an existing voter
                voter_id = voter_on_stage.id
            elif email is not '' and email is not None:
                voter_on_stage = Voter.objects.get(
                    email=email)
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


class Voter(AbstractBaseUser):
    """
    A fully featured User model with admin-compliant permissions that uses
    a full-length email field as the username.

    No fields are required, since at its very simplest, we only need the voter_id based on a voter_device_id.
    """
    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

    # Redefine the basic fields that would normally be defined in User
    # username = models.CharField(unique=True, max_length=20, validators=[alphanumeric])  # Increase max_length to 255
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True, null=True, blank=True)
    first_name = models.CharField(verbose_name='first name', max_length=255, null=True, blank=True)
    last_name = models.CharField(verbose_name='last name', max_length=255, null=True, blank=True)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    # Facebook username
    # Consider just using username
    fb_username = models.CharField(unique=True, max_length=20, validators=[alphanumeric], null=True)

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

    objects = VoterManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Since we need to store a voter based solely on voter_device_id, no values are required

    # We override the save function to allow for the email field to be empty. If NOT empty, email must be unique.
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
            if not validate_email(self.email):  # ...make sure it is a valid email
                # If it isn't a valid email, don't save the value as an email -- just save a blank field
                self.email = None

        super(Voter, self).save(*args, **kwargs)

    def get_full_name(self):
        # The user is identified by their email address
        if self.email:
            return self.email

        return self.first_name+" "+self.last_name

    def get_short_name(self):
        # return self.first_name
        # The user is identified by their email address
        return self.email

    def __str__(self):              # __unicode__ on Python 2
        # return self.get_full_name(self)
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin


class VoterDeviceLink(models.Model):
    """
    There can be many voter_device_id's for every voter_id. (See commentary in class VoterDeviceLinkManager)
    """
    # The id for this object is not used in any searches
    # A randomly generated identifier that gets stored as a cookie on a single device
    # See wevote_functions.models, function generate_voter_device_id for a discussion of voter_device_id length
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
        except VoterDeviceLink.DoesNotExist as e:
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

    address = models.CharField(max_length=254, blank=False, null=False, verbose_name='address as entered')

    latitude = models.CharField(max_length=254, blank=True, null=True, verbose_name='latitude returned from Google')
    longitude = models.CharField(max_length=254, blank=True, null=True, verbose_name='longitude returned from Google')
    normalized_line1 = models.CharField(max_length=254, blank=True, null=True,
                                        verbose_name='normalized address line 1 returned from Google')
    normalized_line2 = models.CharField(max_length=254, blank=True, null=True,
                                        verbose_name='normalized address line 2 returned from Google')
    normalized_city = models.CharField(max_length=254, blank=True, null=True,
                                       verbose_name='normalized city returned from Google')
    normalized_state = models.CharField(max_length=254, blank=True, null=True,
                                        verbose_name='normalized state returned from Google')
    normalized_zip = models.CharField(max_length=254, blank=True, null=True,
                                      verbose_name='normalized zip returned from Google')

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

    def retrieve_address(self, voter_address_id, voter_id, address_type):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_address_on_stage = VoterAddress()

        try:
            if voter_address_id > 0:
                voter_address_on_stage = VoterAddress.objects.get(id=voter_address_id)
                voter_address_id = voter_address_on_stage.id
            elif voter_id > 0 and address_type in (BALLOT_ADDRESS, MAILING_ADDRESS, FORMER_BALLOT_ADDRESS):
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
                    'address': raw_address_text,
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

    # TODO IMPLEMENT THIS
    # def update_or_create_from_google(self, voter_id, address_type, address):
    #     """
    #     After we have called Google's voterInfoQuery, we want to save locally the normalized information returned
    #     from Google.
    #     :param voter_id:
    #     :param address_type:
    #     :param updated_values:
    #     :return:
    #     """
    #     status = ''
    #     exception_multiple_object_returned = False
    #     voter_address_id = 0
    #     voter_address_on_stage = VoterAddress()
    #
    #     if voter_id > 0 and address_type in (BALLOT_ADDRESS, MAILING_ADDRESS, FORMER_BALLOT_ADDRESS):
    #         try:
    #             voter_address_on_stage, success = VoterAddress.objects.update_or_create(
    #                 voter_id=voter_id, address_type=address_type, address=address)
    #             voter_address_id = voter_address_on_stage.id
    #         except VoterAddress.MultipleObjectsReturned as e:
    #             handle_record_found_more_than_one_exception(e, logger=logger)
    #             success = False
    #             exception_multiple_object_returned = True
    #     else:
    #         success = False
    #         status = 'MISSING_VOTER_ID_OR_ADDRESS_TYPE'
    #
    #     results = {
    #         'success':                  success,
    #         'status':                   status,
    #         'MultipleObjectsReturned':  exception_multiple_object_returned,
    #         'voter_address_saved':      True if voter_address_id > 0 else False,
    #         'voter_address_id':         voter_address_id,
    #         'address_type':             address_type,
    #         'voter_address':            voter_address_on_stage,
    #     }
    #     return results
