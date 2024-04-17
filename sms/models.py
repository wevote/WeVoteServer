# sms/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from twilio.rest import Client
from config.base import get_environment_variable
from wevote_functions.functions import generate_random_string, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_sms_integer, fetch_site_unique_id_prefix

GENERIC_SMS_TEMPLATE = 'SIGN_IN_CODE_SMS_TEMPLATE'
SIGN_IN_CODE_SMS_TEMPLATE = 'SIGN_IN_CODE_SMS_TEMPLATE'
KIND_OF_SMS_TEMPLATE_CHOICES = (
    (SIGN_IN_CODE_SMS_TEMPLATE, 'Send code to verify sign in.'),
)

TO_BE_PROCESSED = 'TO_BE_PROCESSED'
BEING_ASSEMBLED = 'BEING_ASSEMBLED'
SCHEDULED = 'SCHEDULED'
ASSEMBLY_STATUS_CHOICES = (
    (TO_BE_PROCESSED,  'Email to be assembled'),
    (BEING_ASSEMBLED, 'Email being assembled with template'),
    (SCHEDULED, 'Sent to the scheduler'),
)
WAITING_FOR_VERIFICATION = 'WAITING_FOR_VERIFICATION'

BEING_SENT = 'BEING_SENT'
SENT = 'SENT'
SEND_STATUS_CHOICES = (
    (TO_BE_PROCESSED,  'Message to be processed'),
    (BEING_SENT, 'Message being sent'),
    (SENT, 'Message sent'),
)

SMS_SECRET_KEY_LENGTH = 12


class SMSPhoneNumber(models.Model):
    """
    We give every sms address its own unique we_vote_id for things like invitations
    """
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "sms", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_sms_integer
    we_vote_id = models.CharField(
        verbose_name="we vote id of this sms address", max_length=255, default=None, null=True,
        blank=True, unique=True)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sms owner", max_length=255, null=True, blank=True, unique=False)
    # Until an SMSPhoneNumber has had its ownership verified, multiple voter accounts can try to use it
    normalized_sms_phone_number = models.CharField(
        verbose_name='sms address', max_length=50, null=False, blank=False, unique=False)
    # Has this sms been verified by the owner?
    sms_ownership_is_verified = models.BooleanField(default=False)
    # Has this sms had a permanent bounce? If so, we should not send sms to it.
    sms_permanent_bounce = models.BooleanField(default=False)
    secret_key = models.CharField(
        verbose_name="secret key to verify ownership of sms", max_length=255, null=True, blank=True, unique=True)
    deleted = models.BooleanField(default=False)  # If sms address is removed from person's account, mark as deleted

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_sms_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "sms" = tells us this is a unique id for a SMSPhoneNumber
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}sms{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(SMSPhoneNumber, self).save(*args, **kwargs)


class SMSOutboundDescription(models.Model):
    """
    Specifications for a single sms we want to send. This data is used to assemble an SMSScheduled
    """
    kind_of_sms_template = models.CharField(
        max_length=50, choices=KIND_OF_SMS_TEMPLATE_CHOICES, default=GENERIC_SMS_TEMPLATE)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    sender_voter_sms = models.CharField(
        verbose_name='sms address for sender', max_length=50, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    recipient_sms_we_vote_id = models.CharField(
        verbose_name="sms we vote id for recipient", max_length=255, null=True, blank=True, unique=False)
    # We include this here for data monitoring and debugging
    recipient_voter_sms = models.CharField(
        verbose_name='sms address for recipient', max_length=50, null=True, blank=True, unique=False)
    template_variables_in_json = models.TextField(null=True, blank=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


class SMSScheduled(models.Model):
    """
    Tells the sms server literally what to send. If an sms bounces temporarily, we will
    want to trigger the SMSOutboundDescription to generate an new SMSScheduled entry.
    """
    message_text = models.TextField(null=True, blank=True)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    sender_voter_sms = models.CharField(
        verbose_name='sender sms address', max_length=50, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient", max_length=255, null=True, blank=True, unique=False)
    recipient_sms_we_vote_id = models.CharField(
        verbose_name="we vote id for the sms", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_sms = models.CharField(
        verbose_name='recipient sms address', max_length=50, null=True, blank=True, unique=False)
    send_status = models.CharField(max_length=50, choices=SEND_STATUS_CHOICES, default=TO_BE_PROCESSED)
    sms_description_id = models.PositiveIntegerField(
        verbose_name="the internal id of SMSOutboundDescription", default=0, null=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)


def convert_phone_number_to_e164(phone_number):
    # https://www.twilio.com/docs/glossary/what-e164    we want +15105551212
    # Assume only US, Canada, Mexico numbers
    just_the_digits = ''.join(filter(str.isdigit, phone_number))
    lnum = len(just_the_digits)

    if lnum == 10 and just_the_digits[0] != '1':   # 5105551212
        return "+1" + just_the_digits
    elif lnum == 11 and just_the_digits[0] == '1':     # 15105551212
        return "+" + just_the_digits
    else:
        return False


def send_scheduled_sms_via_twilio(sms_scheduled):
    """
    Send a single scheduled sms
    :param sms_scheduled:
    :return:
    """
    status = ""
    success = False
    sms_scheduled_sent = False

    twilio_api_turned_off_for_testing = False
    if twilio_api_turned_off_for_testing:
        status += "TWILIO_TURNED_OFF_FOR_TESTING "
        results = {
            'success':              success,
            'status':               status,
            'sms_scheduled_sent':   True,
        }
        return results

    try:
        account_sid = get_environment_variable("TWILIO_ACCOUNT_SID")
        auth_token = get_environment_variable("TWILIO_AUTH_TOKEN")
        from_phone_number = get_environment_variable("SYSTEM_SENDER_SMS_PHONE_NUMBER")
        to = convert_phone_number_to_e164(sms_scheduled.recipient_voter_sms)
        if not to:
            status += "SENDING_VIA_TWILIO_INVALID_TO_NUMBER "
            print("invalid to phone number for twilio: " + sms_scheduled.recipient_voter_sms)
        elif len(account_sid) and len(account_sid):
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                to,
                from_=from_phone_number,
                body=sms_scheduled.message_text)
            status += "SENT_VIA_TWILIO "
            if message.error_code:
                status += "TWILIO_ERROR_" + str(message.error_code) + " MSG_" + str(message.error_message) + ' '
            else:
                success = True
                sms_scheduled_sent = True
        else:
            status += "COULD_NOT_SEND_VIA_TWILIO_ACCOUNT_SETTINGS_ARE_INCORRECT "
    except Exception as e:
        print(e)
        status += "COULD_NOT_SEND_VIA_TWILIO " + str(e) + ' '

    results = {
        'success':              success,
        'status':               status,
        'sms_scheduled_sent':   sms_scheduled_sent,
    }
    return results


class SMSManager(models.Manager):
    def __unicode__(self):
        return "SMSManager"

    @staticmethod
    def clear_secret_key_from_sms_phone_number(sms_secret_key):
        """

        :param sms_secret_key:
        :return:
        """
        sms_phone_number_found = False
        sms_phone_number = None
        status = ''

        try:
            if positive_value_exists(sms_secret_key):
                sms_phone_number = SMSPhoneNumber.objects.get(
                    secret_key=sms_secret_key,
                )
                sms_phone_number_found = True
                success = True
            else:
                sms_phone_number_found = False
                success = False
                status += "SECRET_KEY_MISSING "
        except SMSPhoneNumber.DoesNotExist:
            success = True
            status += "PHONE_NUMBER_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'SMS_DB_RETRIEVE_ERROR ' + str(e) + ' '

        if sms_phone_number_found:
            try:
                sms_phone_number.secret_key = None
                sms_phone_number.save()
            except Exception as e:
                success = False
                status += 'SMS_DB_SAVE_ERROR ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
        }
        return results

    def create_sms_phone_number_for_voter(self, normalized_sms_phone_number, voter, sms_ownership_is_verified=False):
        return self.create_sms_phone_number(normalized_sms_phone_number, voter.we_vote_id, sms_ownership_is_verified)

    @staticmethod
    def create_sms_phone_number(
            normalized_sms_phone_number,
            voter_we_vote_id='',
            sms_ownership_is_verified=False):
        secret_key = generate_random_string(SMS_SECRET_KEY_LENGTH)
        normalized_sms_phone_number = str(normalized_sms_phone_number)
        normalized_sms_phone_number = normalized_sms_phone_number.strip()
        normalized_sms_phone_number = normalized_sms_phone_number.lower()
        status = ''

        if not positive_value_exists(normalized_sms_phone_number):
            sms_phone_number = SMSPhoneNumber()
            results = {
                'success':                  False,
                'status':                   "SMS_PHONE_NUMBER_FOR_VOTER_MISSING_RAW_SMS",
                'sms_phone_number_saved':   False,
                'sms_phone_number':         sms_phone_number,
            }
            return results

        try:
            sms_phone_number = SMSPhoneNumber.objects.create(
                normalized_sms_phone_number=normalized_sms_phone_number,
                voter_we_vote_id=voter_we_vote_id,
                sms_ownership_is_verified=sms_ownership_is_verified,
                secret_key=secret_key,
            )
            sms_phone_number_saved = True
            success = True
            status += "SMS_PHONE_NUMBER_FOR_VOTER_CREATED "
        except Exception as e:
            sms_phone_number_saved = False
            sms_phone_number = SMSPhoneNumber()
            success = False
            status += "SMS_PHONE_NUMBER_FOR_VOTER_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'sms_phone_number_saved':   sms_phone_number_saved,
            'sms_phone_number':         sms_phone_number,
        }
        return results

    @staticmethod
    def create_sms_description(
            sender_voter_we_vote_id,
            sender_voter_sms,
            recipient_voter_we_vote_id='',
            recipient_sms_we_vote_id='',
            recipient_voter_sms='',
            template_variables_in_json='',
            kind_of_sms_template=''):
        status = ""
        if not positive_value_exists(kind_of_sms_template):
            kind_of_sms_template = GENERIC_SMS_TEMPLATE

        try:
            sms_description = SMSOutboundDescription.objects.create(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                sender_voter_sms=sender_voter_sms,
                recipient_voter_we_vote_id=recipient_voter_we_vote_id,
                recipient_sms_we_vote_id=recipient_sms_we_vote_id,
                recipient_voter_sms=recipient_voter_sms,
                kind_of_sms_template=kind_of_sms_template,
                template_variables_in_json=template_variables_in_json,
            )
            sms_description_saved = True
            success = True
            status += "SMS_DESCRIPTION_CREATED "
        except Exception as e:
            sms_description_saved = False
            sms_description = SMSOutboundDescription()
            success = False
            status += "SMS_DESCRIPTION_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'sms_description_saved':    sms_description_saved,
            'sms_description':          sms_description,
        }
        return results

    @staticmethod
    def retrieve_sms_phone_number(
            normalized_sms_phone_number,
            sms_phone_number_we_vote_id='',
            voter_we_vote_id=''):
        """
        There are cases where we store multiple entries for the same normalized_sms_phone_number (prior to an sms
        address being verified)
        :param normalized_sms_phone_number:
        :param sms_phone_number_we_vote_id:
        :param voter_we_vote_id:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        sms_phone_number_found = False
        sms_phone_number = SMSPhoneNumber()
        sms_phone_number_id = 0
        sms_phone_number_list_found = False
        sms_phone_number_list = []
        status = ""

        try:
            if positive_value_exists(sms_phone_number_we_vote_id):
                if positive_value_exists(voter_we_vote_id):
                    sms_phone_number = SMSPhoneNumber.objects.get(
                        we_vote_id__iexact=sms_phone_number_we_vote_id,
                        voter_we_vote_id__iexact=voter_we_vote_id,
                        deleted=False
                    )
                else:
                    sms_phone_number = SMSPhoneNumber.objects.get(
                        we_vote_id__iexact=sms_phone_number_we_vote_id,
                        deleted=False
                    )
                sms_phone_number_id = sms_phone_number.id
                sms_phone_number_we_vote_id = sms_phone_number.we_vote_id
                sms_phone_number_found = True
                success = True
                status += "RETRIEVE_SMS_PHONE_NUMBER_FOUND_BY_WE_VOTE_ID "
            elif positive_value_exists(normalized_sms_phone_number):
                sms_phone_number_queryset = SMSPhoneNumber.objects.all()
                if positive_value_exists(voter_we_vote_id):
                    sms_phone_number_queryset = sms_phone_number_queryset.filter(
                        normalized_sms_phone_number__iexact=normalized_sms_phone_number,
                        voter_we_vote_id__iexact=voter_we_vote_id,
                        deleted=False
                    )
                else:
                    sms_phone_number_queryset = sms_phone_number_queryset.filter(
                        normalized_sms_phone_number__iexact=normalized_sms_phone_number,
                        deleted=False
                    )
                # We need the sms that has been verified sms at top of list
                sms_phone_number_queryset = sms_phone_number_queryset.order_by('-sms_ownership_is_verified')
                sms_phone_number_list = sms_phone_number_queryset

                if len(sms_phone_number_list):
                    if len(sms_phone_number_list) == 1:
                        # If only one sms is found, return the results as a single sms
                        sms_phone_number = sms_phone_number_list[0]
                        sms_phone_number_id = sms_phone_number.id
                        sms_phone_number_we_vote_id = sms_phone_number.we_vote_id
                        sms_phone_number_found = True
                        sms_phone_number_list_found = False
                        success = True
                        status += "RETRIEVE_SMS_PHONE_NUMBER_FOUND_BY_NORMALIZED_SMS_PHONE_NUMBER "
                    else:
                        success = True
                        sms_phone_number_list_found = True
                        status += 'RETRIEVE_SMS_PHONE_NUMBER_OBJECT-SMS_PHONE_NUMBER_LIST_RETRIEVED '
                else:
                    success = True
                    sms_phone_number_list_found = False
                    status += 'RETRIEVE_SMS_PHONE_NUMBER_OBJECT-NO_SMS_PHONE_NUMBER_LIST_RETRIEVED '
            else:
                sms_phone_number_found = False
                success = False
                status += "RETRIEVE_SMS_PHONE_NUMBER_VARIABLES_MISSING "
        except SMSPhoneNumber.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_SMS_PHONE_NUMBER_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_sms_phone_number SMSPhoneNumber '

        results = {
            'success':                      success,
            'status':                       status,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'sms_phone_number_found':       sms_phone_number_found,
            'sms_phone_number_id':          sms_phone_number_id,
            'sms_phone_number_we_vote_id':  sms_phone_number_we_vote_id,
            'sms_phone_number':             sms_phone_number,
            'sms_phone_number_list_found':  sms_phone_number_list_found,
            'sms_phone_number_list':        sms_phone_number_list,
        }
        return results

    @staticmethod
    def retrieve_voter_we_vote_id_from_normalized_sms_phone_number(normalized_sms_phone_number):
        success = True
        status = ''
        voter_we_vote_id_found = False
        voter_we_vote_id = ''

        try:
            sms_phone_number_queryset = SMSPhoneNumber.objects.all()
            sms_phone_number_queryset = sms_phone_number_queryset.filter(
                normalized_sms_phone_number__iexact=normalized_sms_phone_number,
                sms_ownership_is_verified=True,
                deleted=False
            )
            sms_phone_number_list = sms_phone_number_queryset
            if len(sms_phone_number_list):
                sms_phone_number = sms_phone_number_list[0]
                voter_we_vote_id = sms_phone_number.voter_we_vote_id
                voter_we_vote_id_found = True
        except Exception as e:
            success = False
            status += "RETRIEVE_VOTER_WE_VOTE_ID_FAILED " + str(e) + ' '

        results = {
            'success':                  success,
            'status':                   status,
            'voter_we_vote_id_found':   voter_we_vote_id_found,
            'voter_we_vote_id':         voter_we_vote_id,
        }
        return results

    @staticmethod
    def retrieve_sms_phone_number_from_secret_key(sms_secret_key):
        """
        :param sms_secret_key:
        :return:
        """
        sms_phone_number_found = False
        sms_phone_number = SMSPhoneNumber()
        sms_phone_number_id = 0
        sms_phone_number_we_vote_id = ""
        sms_ownership_is_verified = False
        status = ''

        try:
            if positive_value_exists(sms_secret_key):
                sms_phone_number = SMSPhoneNumber.objects.get(
                    secret_key=sms_secret_key,
                    deleted=False
                )
                sms_phone_number_id = sms_phone_number.id
                sms_phone_number_we_vote_id = sms_phone_number.we_vote_id
                sms_ownership_is_verified = sms_phone_number.sms_ownership_is_verified
                sms_phone_number_found = True
                success = True
                status += "SMS_PHONE_NUMBER_SIGN_IN_BY_WE_VOTE_ID "
            else:
                sms_phone_number_found = False
                success = False
                status += "SMS_PHONE_NUMBER_SIGN_IN_VARIABLES_MISSING "
        except SMSPhoneNumber.DoesNotExist:
            success = True
            status += "SMS_PHONE_NUMBER_SIGN_IN_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_sms_phone_number_from_secret_key SMSPhoneNumber ' + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'sms_phone_number_found':       sms_phone_number_found,
            'sms_phone_number_id':          sms_phone_number_id,
            'sms_phone_number_we_vote_id':  sms_phone_number_we_vote_id,
            'sms_phone_number':             sms_phone_number,
            'sms_ownership_is_verified':    sms_ownership_is_verified,
        }
        return results

    @staticmethod
    def verify_sms_phone_number_from_secret_key(sms_secret_key):
        """

        :param sms_secret_key:
        :return:
        """
        sms_phone_number_found = False
        sms_phone_number = SMSPhoneNumber()
        sms_phone_number_id = 0
        sms_phone_number_we_vote_id = ""
        status = ''

        try:
            if positive_value_exists(sms_secret_key):
                sms_phone_number = SMSPhoneNumber.objects.get(
                    secret_key=sms_secret_key,
                    sms_ownership_is_verified=False,
                    deleted=False
                )
                sms_phone_number_id = sms_phone_number.id
                sms_phone_number_we_vote_id = sms_phone_number.we_vote_id
                sms_phone_number_found = True
                success = True
                status += "VERIFY_SMS_PHONE_NUMBER_FOUND_BY_WE_VOTE_ID "
            else:
                sms_phone_number_found = False
                success = False
                status += "VERIFY_SMS_PHONE_NUMBER_VARIABLES_MISSING "
        except SMSPhoneNumber.DoesNotExist:
            success = True
            status += "VERIFY_SMS_PHONE_NUMBER_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED verify_sms_phone_number_from_secret_key SMSPhoneNumber '

        sms_ownership_is_verified = False
        if sms_phone_number_found:
            try:
                # Note that we leave the secret key in place so we can the owner we_vote_id in a subsequent call
                sms_phone_number.sms_ownership_is_verified = True
                sms_phone_number.save()
                sms_ownership_is_verified = True
            except Exception as e:
                success = False
                status += 'FAILED_TO_SAVE_SMS_OWNERSHIP_IS_VERIFIED '

        results = {
            'success':                      success,
            'status':                       status,
            'sms_phone_number_found':       sms_phone_number_found,
            'sms_phone_number_id':          sms_phone_number_id,
            'sms_phone_number_we_vote_id':  sms_phone_number_we_vote_id,
            'sms_phone_number':             sms_phone_number,
            'sms_ownership_is_verified':    sms_ownership_is_verified,
        }
        return results

    @staticmethod
    def retrieve_voter_sms_phone_number_list(voter_we_vote_id):
        """

        :param voter_we_vote_id:
        :return:
        """
        status = ""
        if not positive_value_exists(voter_we_vote_id):
            success = False
            status += 'VALID_VOTER_WE_VOTE_ID_MISSING '
            results = {
                'success':                  success,
                'status':                   status,
                'voter_we_vote_id':         voter_we_vote_id,
                'sms_phone_number_list_found': False,
                'sms_phone_number_list':       [],
            }
            return results

        sms_phone_number_list = []
        try:
            sms_phone_number_queryset = SMSPhoneNumber.objects.all()
            sms_phone_number_queryset = sms_phone_number_queryset.filter(
                voter_we_vote_id__iexact=voter_we_vote_id,
                deleted=False
            )
            sms_phone_number_queryset = sms_phone_number_queryset.order_by('-id')  # Put most recent sms at top of list
            sms_phone_number_list = sms_phone_number_queryset

            if len(sms_phone_number_list):
                success = True
                sms_phone_number_list_found = True
                status += 'SMS_PHONE_NUMBER_LIST_RETRIEVED '
            else:
                success = True
                sms_phone_number_list_found = False
                status += 'NO_SMS_PHONE_NUMBER_LIST_RETRIEVED '
        except SMSPhoneNumber.DoesNotExist:
            # No data found. Not a problem.
            success = True
            sms_phone_number_list_found = False
            status += 'NO_SMS_PHONE_NUMBER_LIST_RETRIEVED_DoesNotExist '
            sms_phone_number_list = []
        except Exception as e:
            success = False
            sms_phone_number_list_found = False
            status += 'FAILED retrieve_voter_sms_phone_number_list SMSPhoneNumber ' + str(e) + ' '

        results = {
            'success': success,
            'status': status,
            'voter_we_vote_id': voter_we_vote_id,
            'sms_phone_number_list_found': sms_phone_number_list_found,
            'sms_phone_number_list': sms_phone_number_list,
        }
        return results

    @staticmethod
    def retrieve_primary_sms_with_ownership_verified(
            voter_we_vote_id='',
            normalized_sms_phone_number='',
            sms_we_vote_id=''):
        sms_phone_number_list = []
        sms_phone_number_list_found = False
        sms_phone_number = SMSPhoneNumber()
        sms_phone_number_found = False
        status = ''
        try:
            if positive_value_exists(voter_we_vote_id):
                sms_phone_number_queryset = SMSPhoneNumber.objects.all()
                sms_phone_number_queryset = sms_phone_number_queryset.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    sms_ownership_is_verified=True,
                    deleted=False
                )
                sms_phone_number_queryset = sms_phone_number_queryset.order_by('-id')
                sms_phone_number_list = sms_phone_number_queryset
            elif positive_value_exists(normalized_sms_phone_number):
                sms_phone_number_queryset = SMSPhoneNumber.objects.all()
                sms_phone_number_queryset = sms_phone_number_queryset.filter(
                    normalized_sms_phone_number__iexact=normalized_sms_phone_number,
                    sms_ownership_is_verified=True,
                    deleted=False
                )
                sms_phone_number_queryset = sms_phone_number_queryset.order_by('-id')
                sms_phone_number_list = sms_phone_number_queryset
            elif positive_value_exists(sms_we_vote_id):
                sms_phone_number_queryset = SMSPhoneNumber.objects.all()
                sms_phone_number_queryset = sms_phone_number_queryset.filter(
                    we_vote_id__iexact=sms_we_vote_id,
                    sms_ownership_is_verified=True,
                    deleted=False
                )
                sms_phone_number_queryset = sms_phone_number_queryset.order_by('-id')
                sms_phone_number_list = sms_phone_number_queryset
            else:
                sms_phone_number_list = []
            if len(sms_phone_number_list):
                success = True
                sms_phone_number_list_found = True
                status += 'RETRIEVE_PRIMARY_SMS_PHONE_NUMBER_OBJECT-SMS_PHONE_NUMBER_LIST_RETRIEVED '
            else:
                success = True
                sms_phone_number_list_found = False
                status += 'RETRIEVE_PRIMARY_SMS_PHONE_NUMBER_OBJECT-NO_SMS_PHONE_NUMBER_LIST_RETRIEVED '
        except SMSPhoneNumber.DoesNotExist:
            success = True
            status += "RETRIEVE_PRIMARY_SMS_PHONE_NUMBER_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_primary_sms_with_ownership_verified SMSPhoneNumber ' + str(e) + ' '

        if sms_phone_number_list_found:
            sms_phone_number_found = True
            sms_phone_number = sms_phone_number_list[0]

        results = {
            'success':                  success,
            'status':                   status,
            'sms_phone_number_found':   sms_phone_number_found,
            'sms_phone_number':         sms_phone_number,
        }
        return results

    def fetch_primary_sms_with_ownership_verified(self, voter_we_vote_id):
        results = self.retrieve_primary_sms_with_ownership_verified(voter_we_vote_id=voter_we_vote_id)
        if results['sms_phone_number_found']:
            sms_phone_number = results['sms_phone_number']
            return sms_phone_number.normalized_sms_phone_number

        return ""

    def find_and_merge_all_duplicate_sms(self, voter_we_vote_id):
        success = True
        status = ''
        already_merged_sms_we_vote_ids = []

        list_results = self.retrieve_voter_sms_phone_number_list(voter_we_vote_id)
        if list_results['sms_phone_number_list_found']:
            initial_sms_phone_number_list = list_results['sms_phone_number_list']
            for sms_phone_number_object in initial_sms_phone_number_list:
                for comparison_sms_phone_number_object in initial_sms_phone_number_list:
                    if comparison_sms_phone_number_object.we_vote_id in already_merged_sms_we_vote_ids:
                        # If this sms has already been merged, skip forward
                        continue
                    if sms_phone_number_object.normalized_sms_phone_number != \
                            comparison_sms_phone_number_object.normalized_sms_phone_number:
                        # If we are looking at different sms numbers, skip forward
                        continue
                    if sms_phone_number_object.we_vote_id == comparison_sms_phone_number_object.we_vote_id:
                        # If we are looking at the same sms entry, skip forward
                        continue
                    # Merge verified sms addresses where both are verified
                    if sms_phone_number_object.sms_ownership_is_verified \
                            and comparison_sms_phone_number_object.sms_ownership_is_verified:
                        # friend_results = update_friend_invitation_email_link_with_new_email(
                        #     comparison_sms_phone_number_object.we_vote_id, sms_phone_number_object.we_vote_id)
                        # if not friend_results['success']:
                        #     status += friend_results['status']
                        merge_results = self.merge_two_duplicate_sms(
                            sms_phone_number_object, comparison_sms_phone_number_object)
                        status += merge_results['status']
                        already_merged_sms_we_vote_ids.append(sms_phone_number_object.we_vote_id)
                        already_merged_sms_we_vote_ids.append(comparison_sms_phone_number_object.we_vote_id)
                    # Merge verified sms numbers where both are not verified
                    elif not sms_phone_number_object.sms_ownership_is_verified \
                            and not comparison_sms_phone_number_object.sms_ownership_is_verified:
                        # friend_results = update_friend_invitation_email_link_with_new_email(
                        #     comparison_sms_phone_number_object.we_vote_id, sms_phone_number_object.we_vote_id)
                        # if not friend_results['success']:
                        #     status += friend_results['status']
                        merge_results = self.merge_two_duplicate_sms(
                            sms_phone_number_object, comparison_sms_phone_number_object)
                        status += merge_results['status']
                        already_merged_sms_we_vote_ids.append(sms_phone_number_object.we_vote_id)
                        already_merged_sms_we_vote_ids.append(comparison_sms_phone_number_object.we_vote_id)

        # Now look for the same phone number where one is verified and the other isn't
        list_results2 = self.retrieve_voter_sms_phone_number_list(voter_we_vote_id)
        if list_results2['sms_phone_number_list_found']:
            initial_sms_phone_number_list = list_results2['sms_phone_number_list']
            for sms_phone_number_object in initial_sms_phone_number_list:
                for comparison_sms_phone_number_object in initial_sms_phone_number_list:
                    if comparison_sms_phone_number_object.we_vote_id in already_merged_sms_we_vote_ids:
                        # If this sms has already been merged, skip forward
                        continue
                    if sms_phone_number_object.normalized_sms_phone_number != \
                            comparison_sms_phone_number_object.normalized_sms_phone_number:
                        # If we are looking at different sms addresses, skip forward
                        continue
                    if sms_phone_number_object.we_vote_id == comparison_sms_phone_number_object.we_vote_id:
                        # If we are looking at the same sms entry, skip forward
                        continue
                    # If here, the normalized_sms_phone_numbers match
                    if sms_phone_number_object.sms_ownership_is_verified:
                        # Delete the comparison_sms_phone_number
                        try:
                            # friend_results = update_friend_invitation_email_link_with_new_email(
                            #     comparison_sms_phone_number_object.we_vote_id, sms_phone_number_object.we_vote_id)
                            # if not friend_results['success']:
                            #     status += friend_results['status']
                            already_merged_sms_we_vote_ids.append(sms_phone_number_object.we_vote_id)
                            already_merged_sms_we_vote_ids.append(comparison_sms_phone_number_object.we_vote_id)
                            comparison_sms_phone_number_object.delete()
                        except Exception as e:
                            status += "COULD_NOT_DELETE_UNVERIFIED_PHONE_NUMBER " + str(e) + " "
        results = {
            'success': success,
            'status': status,
        }
        return results

    @staticmethod
    def merge_two_duplicate_sms(sms_phone_number_object1, sms_phone_number_object2):
        """
        We assume that the checking to see if these are duplicates has been done outside of this function.
        We will keep sms_phone_number_object1 and eliminate sms_phone_number_object2.
        :param sms_phone_number_object1:
        :param sms_phone_number_object2:
        :return:
        """
        success = True
        status = ''

        try:
            test_we_vote_id = sms_phone_number_object1.we_vote_id
            test_we_vote_id = sms_phone_number_object2.we_vote_id
        except Exception as e:
            status += 'PROBLEM_WITH_PHONE_NUMBER1_OR_PHONE_NUMBER2 ' + str(e) + ' '
            success = False
            results = {
                'success': success,
                'status': status,
            }
            return results

        if sms_phone_number_object1.voter_we_vote_id != sms_phone_number_object2.voter_we_vote_id:
            status += 'ONLY_MERGE_PHONE_NUMBERS_FROM_SAME_VOTER '
            success = False
            results = {
                'success': success,
                'status': status,
            }
            return results

        if sms_phone_number_object1.normalized_sms_phone_number != sms_phone_number_object2.normalized_sms_phone_number:
            status += 'ONLY_MERGE_PHONE_NUMBERS_WITH_SAME_NORMALIZED_PHONE_NUMBER_ADDRESS '
            success = False
            results = {
                'success': success,
                'status': status,
            }
            return results

        at_least_one_is_verified = sms_phone_number_object1.sms_ownership_is_verified \
            or sms_phone_number_object2.sms_ownership_is_verified
        both_are_bouncing = sms_phone_number_object1.sms_permanent_bounce \
            and sms_phone_number_object2.sms_permanent_bounce

        try:
            sms_phone_number_object1.sms_ownership_is_verified = at_least_one_is_verified
            sms_phone_number_object1.sms_permanent_bounce = both_are_bouncing
            sms_phone_number_object1.save()
        except Exception as e:
            status += "COULD_NOT_SAVE_PHONE_NUMBER1 " + str(e) + " "

        # We don't need to handle repairing the primary sms link here
        # because it is done in heal_primary_sms_data_for_voter

        # Are there any scheduled messages for sms_phone_number_object2 waiting to send?

        try:
            sms_phone_number_object2.delete()
        except Exception as e:
            status += "COULD_NOT_DELETE_PHONE_NUMBER2 " + str(e) + " "
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

    @staticmethod
    def retrieve_scheduled_sms_list_from_send_status(sender_voter_we_vote_id, send_status):
        scheduled_sms_list = []
        status = ""
        try:
            sms_scheduled_queryset = SMSScheduled.objects.all()
            sms_scheduled_queryset = sms_scheduled_queryset.filter(
                sender_voter_we_vote_id=sender_voter_we_vote_id,
                send_status=send_status,
            )
            scheduled_sms_list = sms_scheduled_queryset

            if len(scheduled_sms_list):
                success = True
                scheduled_sms_list_found = True
                status += 'SCHEDULED_SMS_LIST_RETRIEVED '
            else:
                success = True
                scheduled_sms_list_found = False
                status += 'NO_SCHEDULED_SMS_LIST_RETRIEVED '
        except SMSScheduled.DoesNotExist:
            # No data found. Not a problem.
            success = True
            scheduled_sms_list_found = False
            status += 'NO_SCHEDULED_SMS_LIST_RETRIEVED_DoesNotExist '
            scheduled_sms_list = []
        except Exception as e:
            success = False
            scheduled_sms_list_found = False
            status += 'FAILED retrieve_scheduled_sms_list_from_send_status SMSPhoneNumber ' + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'scheduled_sms_list_found': scheduled_sms_list_found,
            'scheduled_sms_list':       scheduled_sms_list,
        }
        return results

    @staticmethod
    def update_scheduled_sms_with_new_send_status(sms_scheduled_object, send_status):
        try:
            sms_scheduled_object.send_status = send_status
            sms_scheduled_object.save()
            return sms_scheduled_object
        except Exception as e:
            return sms_scheduled_object

    @staticmethod
    def schedule_sms(sms_description, message_text, send_status=TO_BE_PROCESSED):
        status = ''
        try:
            sms_scheduled = SMSScheduled.objects.create(
                sender_voter_we_vote_id=sms_description.sender_voter_we_vote_id,
                sender_voter_sms=sms_description.sender_voter_sms,
                recipient_voter_we_vote_id=sms_description.recipient_voter_we_vote_id,
                recipient_sms_we_vote_id=sms_description.recipient_sms_we_vote_id,
                recipient_voter_sms=sms_description.recipient_voter_sms,
                message_text=message_text,
                sms_description_id=sms_description.id,
                send_status=send_status,
            )
            sms_scheduled_saved = True
            sms_scheduled_id = sms_scheduled.id
            success = True
            status += "SCHEDULE_SMS_CREATED "
        except Exception as e:
            sms_scheduled_saved = False
            sms_scheduled = SMSScheduled()
            sms_scheduled_id = 0
            success = False
            status += "SCHEDULE_SMS_NOT_CREATED " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'sms_scheduled_saved':  sms_scheduled_saved,
            'sms_scheduled_id':     sms_scheduled_id,
            'sms_scheduled':        sms_scheduled,
        }
        return results

    @staticmethod
    def send_scheduled_sms(sms_scheduled):
        success = True
        status = ""

        # sender_voter_sms is not required, because we use a system sms

        if not positive_value_exists(sms_scheduled.recipient_voter_sms):
            status += "MISSING_RECIPIENT_VOTER_SMS "
            success = False

        if not positive_value_exists(sms_scheduled.message_text):
            status += "MISSING_SMS_MESSAGE "
            success = False

        if success:
            return send_scheduled_sms_via_twilio(sms_scheduled)
        else:
            sms_scheduled_sent = False
            results = {
                'success': success,
                'status': status,
                'sms_scheduled_sent': sms_scheduled_sent,
            }
            return results

    def update_sms_phone_number_with_new_secret_key(self, sms_we_vote_id):
        results = self.retrieve_sms_phone_number('', sms_we_vote_id)
        if results['sms_phone_number_found']:
            sms_phone_number = results['sms_phone_number']
            try:
                sms_phone_number.secret_key = generate_random_string(SMS_SECRET_KEY_LENGTH)
                sms_phone_number.save()
                return sms_phone_number.secret_key
            except Exception as e:
                return ""
        else:
            return ""

    @staticmethod
    def update_sms_phone_number_as_verified(sms_phone_number):
        try:
            sms_phone_number.sms_ownership_is_verified = True
            sms_phone_number.save()
            return sms_phone_number
        except Exception as e:
            return sms_phone_number
