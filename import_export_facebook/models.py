# import_export_facebook/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.validators import RegexValidator
from django.db import models
from email_outbound.models import SEND_STATUS_CHOICES, TO_BE_PROCESSED
from wevote_functions.functions import generate_random_string, positive_value_exists

FRIEND_INVITATION_FACEBOOK_TEMPLATE = 'FRIEND_INVITATION_FACEBOOK_TEMPLATE'
GENERIC_EMAIL_FACEBOOK_TEMPLATE = 'GENERIC_EMAIL_FACEBOOK_TEMPLATE'
KIND_OF_FACEBOOK_TEMPLATE_CHOICES = (
    (GENERIC_EMAIL_FACEBOOK_TEMPLATE,  'Generic Email'),
    (FRIEND_INVITATION_FACEBOOK_TEMPLATE, 'Invite Friend'),
)


class FacebookAuthResponse(models.Model):
    """
    This is the authResponse data from a Facebook authentication
    """
    voter_device_id = models.CharField(
        verbose_name="voter_device_id initiating Facebook Auth", max_length=255, null=False, blank=False, unique=True)
    datetime_of_authorization = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)

    # Comes from Facebook authResponse FACEBOOK_LOGGED_IN
    facebook_access_token = models.CharField(
        verbose_name="accessToken from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_expires_in = models.IntegerField(verbose_name="expiresIn from Facebook", null=True, blank=True)
    facebook_signed_request = models.TextField(verbose_name="signedRequest from Facebook", null=True, blank=True)
    facebook_user_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)

    # Comes from FACEBOOK_RECEIVED_DATA
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    facebook_first_name = models.CharField(
        verbose_name="first_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_middle_name = models.CharField(
        verbose_name="first_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_last_name = models.CharField(
        verbose_name="first_name from Facebook", max_length=255, null=True, blank=True, unique=False)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of image from facebook', blank=True, null=True)

    def get_full_name(self):
        full_name = self.facebook_first_name if positive_value_exists(self.facebook_first_name) else ''
        full_name += " " if positive_value_exists(self.facebook_first_name) \
            and positive_value_exists(self.facebook_last_name) else ''
        full_name += self.facebook_last_name if positive_value_exists(self.facebook_last_name) else ''

        if not positive_value_exists(full_name) and positive_value_exists(self.facebook_email):
            full_name = self.email.split("@", 1)[0]

        return full_name


class FacebookLinkToVoter(models.Model):
    """
    This is the link between a Facebook account and a We Vote voter account
    """
    voter_we_vote_id = models.CharField(verbose_name="we vote id for the email owner", max_length=255, unique=True)
    facebook_user_id = models.BigIntegerField(verbose_name="facebook big integer id", null=False, unique=True)
    secret_key = models.CharField(
        verbose_name="secret key to verify ownership facebook account", max_length=255, null=False, unique=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=False, auto_now=True)


class FacebookMessageOutboundDescription(models.Model):
    """
    A description of the Facebook direct message we want to send.
    """
    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

    kind_of_send_template = models.CharField(max_length=50, choices=KIND_OF_FACEBOOK_TEMPLATE_CHOICES,
                                             default=GENERIC_EMAIL_FACEBOOK_TEMPLATE)
    sender_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the sender", max_length=255, null=True, blank=True, unique=False)
    recipient_voter_we_vote_id = models.CharField(
        verbose_name="we vote id for the recipient if we have it", max_length=255, null=True, blank=True, unique=False)
    recipient_facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    recipient_facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                                 null=True, blank=True)
    recipient_fb_username = models.CharField(unique=True, max_length=20, validators=[alphanumeric], null=True)
    send_status = models.CharField(max_length=50, choices=SEND_STATUS_CHOICES, default=TO_BE_PROCESSED)


class FacebookManager(models.Model):
    def __unicode__(self):
        return "FacebookManager"

    def create_facebook_link_to_voter(self, facebook_user_id, voter_we_vote_id):

        # Any attempts to save a facebook_link using either facebook_user_id or voter_we_vote_id that already
        #  exist in the table will fail, since those fields are required to be unique.
        facebook_secret_key = generate_random_string(12)

        try:
            facebook_link_to_voter = FacebookLinkToVoter.objects.create(
                facebook_user_id=facebook_user_id,
                voter_we_vote_id=voter_we_vote_id,
                secret_key=facebook_secret_key,
            )
            facebook_link_to_voter_saved = True
            success = True
            status = "FACEBOOK_LINK_TO_VOTER_CREATED"
        except Exception as e:
            facebook_link_to_voter_saved = False
            facebook_link_to_voter = FacebookLinkToVoter()
            success = False
            status = "FACEBOOK_LINK_TO_VOTER_NOT_CREATED"

        results = {
            'success':                      success,
            'status':                       status,
            'facebook_link_to_voter_saved': facebook_link_to_voter_saved,
            'facebook_link_to_voter':       facebook_link_to_voter,
        }
        return results

    def update_or_create_facebook_auth_response(
            self, voter_device_id, facebook_access_token, facebook_user_id, facebook_expires_in,
            facebook_signed_request,
            facebook_email, facebook_first_name, facebook_middle_name, facebook_last_name,
            facebook_profile_image_url_https):

        defaults = {
            "voter_device_id": voter_device_id,
        }
        if positive_value_exists(facebook_access_token):
            defaults["facebook_access_token"] = facebook_access_token
        if positive_value_exists(facebook_user_id):
            defaults["facebook_user_id"] = facebook_user_id
        if positive_value_exists(facebook_expires_in):
            defaults["facebook_expires_in"] = facebook_expires_in
        if positive_value_exists(facebook_signed_request):
            defaults["facebook_signed_request"] = facebook_signed_request
        if positive_value_exists(facebook_email):
            defaults["facebook_email"] = facebook_email
        if positive_value_exists(facebook_first_name):
            defaults["facebook_first_name"] = facebook_first_name
        if positive_value_exists(facebook_middle_name):
            defaults["facebook_middle_name"] = facebook_middle_name
        if positive_value_exists(facebook_last_name):
            defaults["facebook_last_name"] = facebook_last_name
        if positive_value_exists(facebook_profile_image_url_https):
            defaults["facebook_profile_image_url_https"] = facebook_profile_image_url_https

        try:
            facebook_auth_response, created = FacebookAuthResponse.objects.update_or_create(
                voter_device_id__iexact=voter_device_id,
                defaults=defaults,
            )
            facebook_auth_response_saved = True
            success = True
            status = "FACEBOOK_AUTH_RESPONSE_UPDATED_OR_CREATED"
        except Exception as e:
            facebook_auth_response_saved = False
            facebook_auth_response = FacebookAuthResponse()
            success = False
            created = False
            status = "FACEBOOK_AUTH_RESPONSE_NOT_UPDATED_OR_CREATED"

        results = {
            'success': success,
            'status': status,
            'facebook_auth_response_saved': facebook_auth_response_saved,
            'facebook_auth_response_created': created,
            'facebook_auth_response': facebook_auth_response,
        }
        return results

    def retrieve_facebook_auth_response(self, voter_device_id):
        """

        :param voter_device_id:
        :return:
        """
        facebook_auth_response = FacebookAuthResponse()
        facebook_auth_response_id = 0

        try:
            if positive_value_exists(voter_device_id):
                facebook_auth_response = FacebookAuthResponse.objects.get(
                    voter_device_id__iexact=voter_device_id,
                )
                facebook_auth_response_id = facebook_auth_response.id
                facebook_auth_response_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_FOUND_BY_VOTER_DEVICE_ID"
            else:
                facebook_auth_response_found = False
                success = False
                status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_VARIABLES_MISSING"
        except FacebookAuthResponse.DoesNotExist:
            facebook_auth_response_found = False
            success = True
            status = "RETRIEVE_FACEBOOK_AUTH_RESPONSE_NOT_FOUND"
        except Exception as e:
            facebook_auth_response_found = False
            success = False
            status = 'FAILED retrieve_facebook_auth_response'

        results = {
            'success': success,
            'status': status,
            'facebook_auth_response_found': facebook_auth_response_found,
            'facebook_auth_response_id': facebook_auth_response_id,
            'facebook_auth_response': facebook_auth_response,
        }
        return results

    def fetch_facebook_id_from_voter_we_vote_id(self, voter_we_vote_id):
        facebook_user_id = 0
        facebook_results = self.retrieve_facebook_link_to_voter(facebook_user_id, voter_we_vote_id)
        if facebook_results['facebook_link_to_voter_found']:
            facebook_link_to_voter = facebook_results['facebook_link_to_voter']
            facebook_user_id = facebook_link_to_voter.facebook_user_id
        return facebook_user_id

    def retrieve_facebook_link_to_voter_from_voter_we_vote_id(self, voter_we_vote_id):
        facebook_user_id = 0
        facebook_secret_key = ""
        return self.retrieve_facebook_link_to_voter(facebook_user_id, voter_we_vote_id, facebook_secret_key)

    def retrieve_facebook_link_to_voter_from_facebook_secret_key(self, facebook_secret_key):
        facebook_user_id = 0
        voter_we_vote_id = ""
        return self.retrieve_facebook_link_to_voter(facebook_user_id, voter_we_vote_id, facebook_secret_key)

    def retrieve_facebook_link_to_voter(self, facebook_user_id=0, voter_we_vote_id='', facebook_secret_key=''):
        """

        :param facebook_user_id:
        :param voter_we_vote_id:
        :param facebook_secret_key:
        :return:
        """
        facebook_link_to_voter = FacebookLinkToVoter()
        facebook_link_to_voter_id = 0

        try:
            if positive_value_exists(facebook_user_id):
                facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                    facebook_user_id=facebook_user_id,
                )
                facebook_link_to_voter_id = facebook_link_to_voter.id
                facebook_link_to_voter_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_FOUND_BY_FACEBOOK_USER_ID"
            elif positive_value_exists(voter_we_vote_id):
                facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                )
                facebook_link_to_voter_id = facebook_link_to_voter.id
                facebook_link_to_voter_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_FOUND_BY_VOTER_WE_VOTE_ID"
            elif positive_value_exists(facebook_secret_key):
                facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                    secret_key=facebook_secret_key,
                )
                facebook_link_to_voter_id = facebook_link_to_voter.id
                facebook_link_to_voter_found = True
                success = True
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_FOUND_BY_FACEBOOK_SECRET_KEY"
            else:
                facebook_link_to_voter_found = False
                success = False
                status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_VARIABLES_MISSING"
        except FacebookLinkToVoter.DoesNotExist:
            facebook_link_to_voter_found = False
            success = True
            status = "RETRIEVE_FACEBOOK_LINK_TO_VOTER_NOT_FOUND"
        except Exception as e:
            facebook_link_to_voter_found = False
            success = False
            status = 'FAILED retrieve_facebook_link_to_voter'

        results = {
            'success': success,
            'status': status,
            'facebook_link_to_voter_found': facebook_link_to_voter_found,
            'facebook_link_to_voter_id': facebook_link_to_voter_id,
            'facebook_link_to_voter': facebook_link_to_voter,
        }
        return results
