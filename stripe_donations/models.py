# stripe_donations/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models, transaction
from django.db.models import Q
from datetime import datetime, timezone
from exception.models import handle_exception, handle_record_found_more_than_one_exception
# from organization.models import CHOSEN_FAVICON_ALLOWED, CHOSEN_FULL_DOMAIN_ALLOWED, CHOSEN_GOOGLE_ANALYTICS_ALLOWED, \
#     CHOSEN_SOCIAL_SHARE_IMAGE_ALLOWED, CHOSEN_SOCIAL_SHARE_DESCRIPTION_ALLOWED, CHOSEN_PROMOTED_ORGANIZATIONS_ALLOWED
import wevote_functions.admin
from voter.models import VoterManager
from wevote_functions.functions import positive_value_exists
import stripe
import textwrap

logger = wevote_functions.admin.get_logger(__name__)

# SAME_DAY_MONTHLY = 'SAME_DAY_MONTHLY'
# SAME_DAY_ANNUALLY = 'SAME_DAY_ANNUALLY'
# BILLING_FREQUENCY_CHOICES = ((SAME_DAY_MONTHLY, 'SAME_DAY_MONTHLY'),
#                              (SAME_DAY_ANNUALLY, 'SAME_DAY_ANNUALLY'))
# CURRENCY_USD = 'usd'
# CURRENCY_CAD = 'cad'
# CURRENCY_CHOICES = ((CURRENCY_USD, 'usd'),
#                     (CURRENCY_CAD, 'cad'))
# FREE = 'FREE'
# PROFESSIONAL_MONTHLY = 'PROFESSIONAL_MONTHLY'
# PROFESSIONAL_YEARLY = 'PROFESSIONAL_YEARLY'
# PROFESSIONAL_PAID_WITHOUT_STRIPE = 'PROFESSIONAL_PAID_WITHOUT_STRIPE'
# ENTERPRISE_MONTHLY = 'ENTERPRISE_MONTHLY'
# ENTERPRISE_YEARLY = 'ENTERPRISE_YEARLY'
# ENTERPRISE_PAID_WITHOUT_STRIPE = 'ENTERPRISE_YEARLY'
# ORGANIZATION_PLAN_OPTIONS = (
#     (FREE, 'FREE'),
#     (PROFESSIONAL_MONTHLY, 'PROFESSIONAL_MONTHLY'),
#     (PROFESSIONAL_YEARLY, 'PROFESSIONAL_YEARLY'),
#     (PROFESSIONAL_PAID_WITHOUT_STRIPE, 'PROFESSIONAL_PAID_WITHOUT_STRIPE'),
#     (ENTERPRISE_MONTHLY, 'ENTERPRISE_MONTHLY'),
#     (ENTERPRISE_YEARLY, 'ENTERPRISE_YEARLY'),
#     (ENTERPRISE_PAID_WITHOUT_STRIPE, 'ENTERPRISE_PAID_WITHOUT_STRIPE'))

# Stripes currency support https://support.stripe.com/questions/which-currencies-does-stripe-support


class StripeLinkToVoter(models.Model):
    """
    This table links voter_we_vote_ids with Stripe customer IDs. A row is created when a stripe donation is made for the
    first time.
    """
    # The unique customer id from a stripe donation
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255,
                                          null=False, blank=False)
    # There are scenarios where a voter_we_vote_id might have multiple customer_id's
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=False, null=False,
                                        blank=False)


class StripeSubscription(models.Model):
    """
    This table tracks subscriptions (recurring donations) and donations
    """
    objects = None
    DoesNotExist = None
    we_plan_id = models.CharField(verbose_name="donation plan name", max_length=64, null=False, blank=True)
    stripe_subscription_id = models.CharField(verbose_name="Stripe subscription id", max_length=32, null=True,
                                              blank=True)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the person who created this subscription",
        max_length=64, default='', null=True, blank=True, unique=False, db_index=True)
    not_loggedin_voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, default='',
                                                     unique=False, null=True, blank=True)
    stripe_customer_id = models.CharField(verbose_name="stripe customer id", max_length=32, null=True, blank=True)
    # Stripe uses integer pennies for amount (ex: 2000 = $20.00)
    amount = models.PositiveIntegerField(verbose_name="recurring donation amount", default=0, null=False)
    billing_interval = models.CharField(verbose_name="recurring donation frequency", max_length=64, default="month",
                                        null=False)
    currency = models.CharField(verbose_name="currency", max_length=64, default="usd", null=False)
    donation_plan_is_active = models.BooleanField(verbose_name="status of recurring donation plan", default=True,)
    subscription_created_at = models.DateTimeField(verbose_name="stripe subscription creation timestamp",
                                                   auto_now=False, auto_now_add=False, null=True)
    subscription_canceled_at = models.DateTimeField(verbose_name="stripe subscription canceled timestamp",
                                                    auto_now=False, auto_now_add=False, null=True)
    subscription_ended_at = models.DateTimeField(verbose_name="stripe subscription ended timestamp", auto_now=False,
                                                 auto_now_add=False, null=True)
    stripe_charge_id = models.CharField(verbose_name="Stripe charge id", max_length=32, null=True, blank=True)
    last_charged = models.DateTimeField(verbose_name="stripe subscription most recent charge timestamp", auto_now=False,
                                        auto_now_add=False, null=True)
    brand = models.CharField(verbose_name="the brand of the credit card, eg. Visa, Amex", max_length=32, default="",
                             null=True, blank=True)
    exp_month = models.PositiveIntegerField(verbose_name="the expiration month of the credit card", default=0,
                                            null=False)
    exp_year = models.PositiveIntegerField(verbose_name="the expiration year of the credit card", default=0, null=False)
    last4 = models.PositiveIntegerField(verbose_name="the last 4 digits of the credit card", default=0, null=False)
    # campaignx_we_vote_id = models.CharField(max_length=64, null=True)
    # campaign_title = models.CharField(verbose_name="title of campaign", max_length=255, null=False, blank=False)
    stripe_request_id = models.CharField(verbose_name="stripe initial request id", max_length=32, null=True, blank=True)
    linked_organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the organization who benefits from the organization subscription, "
                     "but does not include the organizations that get credif for Chip Ins",
        max_length=64, default=None, null=True, blank=True, unique=False, db_index=True)
    api_version = models.CharField(verbose_name="Stripe API Version", max_length=32, null=True, blank=True)
    livemode = models.BooleanField(verbose_name="True: Live transaction, False: Test transaction", default=False,
                                   blank=False)
    client_ip = models.CharField(verbose_name="Client IP address as seen by Stripe", max_length=32,
                                 null=True, blank=True)


class StripePayments(models.Model):
    """
     This table tracks donation, subscription plans and refund activity
     """
    objects = None
    DoesNotExist = None
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, unique=False, null=True,
                                        default='', blank=True)
    not_loggedin_voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, unique=False,
                                                     null=True, default='', blank=True)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=32,
                                          null=True, blank=True)
    stripe_charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=32,
                                        default="", null=True, blank=True)
    stripe_card_id = models.CharField(verbose_name="unique id for a credit/debit card", max_length=32, default="",
                                      null=True, blank=True)
    stripe_request_id = models.CharField(verbose_name="stripe initial request id", max_length=32, null=True, blank=True)
    stripe_subscription_id = models.CharField(
        verbose_name="unique subscription id for one voter, amount, and creation time",
        max_length=32, default="", null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name="donation amount", default=0, null=True)
    currency = models.CharField(verbose_name="donation currency country code", max_length=8, default="", null=True,
                                blank=True)
    funding = models.CharField(verbose_name="stripe returns 'credit' also might be debit, etc", max_length=32,
                               default="", null=True, blank=True)
    livemode = models.BooleanField(verbose_name="True: Live transaction, False: Test transaction", default=False,
                                   blank=True)
    action_taken = models.CharField(verbose_name="action taken", max_length=64, default="", null=True, blank=True)
    action_result = models.CharField(verbose_name="action result", max_length=64, default="", null=True, blank=True)
    created = models.DateTimeField(verbose_name="stripe record creation timestamp", auto_now=False,
                                   auto_now_add=False)
    failure_code = models.CharField(verbose_name="failure code reported by stripe", max_length=32, default="",
                                    null=True, blank=True)
    failure_message = models.CharField(verbose_name="failure message reported by stripe", max_length=255, default="",
                                       null=True, blank=True)
    network_status = models.CharField(verbose_name="network status reported by stripe", max_length=64, default="",
                                      null=True, blank=True)
    billing_reason = models.CharField(verbose_name="reason for billing from by stripe", max_length=64, default="",
                                      null=True, blank=True)
    reason = models.CharField(verbose_name="reason for failure reported by stripe", max_length=255, default="",
                              null=True, blank=True)
    seller_message = models.CharField(verbose_name="plain text message to us from stripe", max_length=255, default="",
                                      null=True, blank=True)
    stripe_type = models.CharField(verbose_name="authorization outcome message to us from stripe", max_length=64,
                                   default="", null=True, blank=True)
    payment_msg = models.CharField(verbose_name="payment outcome message to us from stripe", max_length=64, default="",
                                   null=True, blank=True)
    is_paid = models.BooleanField(verbose_name="Charge has been paid", default=False)
    is_refunded = models.BooleanField(verbose_name="Charge has been refunded", default=False)
    source_obj = models.CharField(verbose_name="stripe returns the donor's zip code", max_length=32, default="card",
                                  null=True, blank=True)
    amount_refunded = models.PositiveIntegerField(verbose_name="refund amount", default=0, null=True)
    email = models.CharField(verbose_name="stripe returns the donor's email address as a name", max_length=255,
                             default="", null=True, blank=True)
    address_zip = models.CharField(verbose_name="stripe returns the donor's zip code", max_length=32, default="",
                                   null=True, blank=True)
    brand = models.CharField(verbose_name="the brand of the credit card, eg. Visa, Amex", max_length=32, default="",
                             null=True, blank=True)
    country = models.CharField(verbose_name="the country code of the bank that issued the credit card", max_length=8,
                               default="", null=True, blank=True)
    exp_month = models.PositiveIntegerField(verbose_name="the expiration month of the credit card", default=0,
                                            null=True)
    exp_year = models.PositiveIntegerField(verbose_name="the expiration year of the credit card", default=0, null=True)
    last4 = models.PositiveIntegerField(verbose_name="the last 4 digits of the credit card", default=0, null=True)
    stripe_status = models.CharField(verbose_name="status string reported by stripe", max_length=64, default="",
                                     null=True, blank=True)
    status = models.CharField(verbose_name="our generated status message", max_length=255, default="", null=True,
                              blank=True)
    we_plan_id = models.CharField(verbose_name="WeVote subscription plan id", max_length=64, default="",
                                  unique=False, null=True, blank=True)
    paid_at = models.DateTimeField(verbose_name="stripe subscription most recent charge timestamp", auto_now=False,
                                   auto_now_add=False, null=True)
    ip_address = models.GenericIPAddressField(verbose_name="user ip address", protocol='both', unpack_ipv4=False,
                                              null=True, blank=True, unique=False)
    is_chip_in = models.BooleanField(
        verbose_name="Is this a Campaign 'Chip In' payment?", default=False)
    is_premium_plan = models.BooleanField(
        verbose_name="is this a premium organization plan (and not a personal donation subscription)?", default=False)
    is_monthly_donation = models.BooleanField(
        verbose_name="is this a repeating monthly subscription donation?", default=False)
    campaignx_wevote_id = models.CharField(
        verbose_name="Campaign we vote id, in order to credit chip ins", max_length=32, unique=False, null=True,
        blank=True)
    record_enum = models.CharField(
        verbose_name="enum of record type {PAYMENT_FROM_UI, PAYMENT_AUTO_SUBSCRIPTION, SUBSCRIPTION_SETUP_AND_INITIAL}",
        max_length=32, unique=False, null=True, blank=True)
    api_version = models.CharField(
        verbose_name="Stripe API Version at creation time",
        max_length=32, null=True, blank=True)


class StripeManager(models.Manager):

    @staticmethod
    def create_donate_link_to_voter(stripe_customer_id, voter_we_vote_id):
        """"

        :param stripe_customer_id:
        :param voter_we_vote_id:
        :return:
        """
        new_customer_id_created = False

        if not voter_we_vote_id:
            success = False
            status = 'MISSING_VOTER_WE_VOTE_ID'
        else:
            try:
                new_customer_id_created = StripeLinkToVoter.objects.create(
                    stripe_customer_id=stripe_customer_id, voter_we_vote_id=voter_we_vote_id)
                success = True
                status = 'STRIPE_CUSTOMER_ID_SAVED '
            except Exception as e:
                success = False
                status = 'STRIPE_CUSTOMER_ID_NOT_SAVED '

        saved_results = {
            'success': success,
            'status': status,
            'new_stripe_customer_id': new_customer_id_created
        }
        return saved_results

    @staticmethod
    def retrieve_stripe_customer_id_from_donate_link_to_voter(voter_we_vote_id):
        """

        :param voter_we_vote_id:
        :return:
        """
        stripe_customer_id = ''
        status = ''
        success = bool
        if positive_value_exists(voter_we_vote_id):
            try:
                stripe_customer_id_queryset = StripeLinkToVoter.objects.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id).values()
                stripe_customer_id = stripe_customer_id_queryset[0]['stripe_customer_id']
                if positive_value_exists(stripe_customer_id):
                    success = True
                    status = "STRIPE_CUSTOMER_ID_RETRIEVED"
                else:
                    success = False
                    status = "EXISTING_STRIPE_CUSTOMER_ID_NOT_FOUND"
            except Exception as e:
                success = False
                status = "STRIPE_CUSTOMER_ID_RETRIEVAL_ATTEMPT_FAILED"

        results = {
            'success': success,
            'status': status,
            'stripe_customer_id': stripe_customer_id,
        }
        return results

    @staticmethod
    def retrieve_voter_we_vote_id_from_donate_link_to_voter(stripe_customer_id):
        """

        :param stripe_customer_id:
        :return:
        """
        voter_we_vote_id = ''
        status = ''
        success = bool
        if positive_value_exists(stripe_customer_id):
            try:
                voter_id_queryset = StripeLinkToVoter.objects.filter(
                    stripe_customer_id__iexact=stripe_customer_id).values()
                voter_we_vote_id = voter_id_queryset[0]['voter_we_vote_id']
                if positive_value_exists(voter_we_vote_id):
                    success = True
                    status = "VOTER_WE_VOTE_ID_RETRIEVED"
                else:
                    success = False
                    status = "EXISTING_VOTER_WE_VOTE_ID_NOT_FOUND"
            except Exception as e:
                success = False
                status = "VOTER_WE_VOTE_ID_RETRIEVAL_ATTEMPT_FAILED"

        results = {
            'success': success,
            'status': status,
            'voter_we_vote_id': voter_we_vote_id,
        }
        return results

    @staticmethod
    def retrieve_voter_we_vote_id_via_stripe_request_id(stripe_request_id):
        """

        :param stripe_request_id:
        :return:
        """
        voter_we_vote_id = ''
        not_loggedin_voter_we_vote_id = ''
        status = ''
        success = bool
        if positive_value_exists(stripe_request_id):
            try:
                voter_id_queryset = StripeSubscription.objects.filter(
                    stripe_request_id__iexact=stripe_request_id).values()
                voter_we_vote_id = voter_id_queryset[0]['voter_we_vote_id']
                not_loggedin_voter_we_vote_id = voter_id_queryset[0]['not_loggedin_voter_we_vote_id']
                if positive_value_exists(voter_we_vote_id) or positive_value_exists(not_loggedin_voter_we_vote_id):
                    success = True
                    status = "VOTER_WE_VOTE_ID_RETRIEVED"
                else:
                    success = False
                    status = "EXISTING_VOTER_WE_VOTE_ID_NOT_FOUND"
            except Exception as e:
                success = False
                status = "VOTER_WE_VOTE_ID_RETRIEVAL_ATTEMPT_FAILED"

        results = {
            'success': success,
            'status': status,
            'voter_we_vote_id': voter_we_vote_id,
            'not_loggedin_voter_we_vote_id': not_loggedin_voter_we_vote_id,
        }
        return results

    @staticmethod
    def retrieve_voter_we_vote_id_via_amount_and_customer_id(amount, stripe_customer_id):
        """

        :param amount:
        :param stripe_customer_id:
        :return:
        """
        voter_we_vote_id = ''
        status = ''
        success = bool
        if positive_value_exists(stripe_customer_id):
            try:
                subscription_queryset = StripeSubscription.objects.all().order_by('-id')
                subscription_queryset = subscription_queryset.filter(
                    Q(amount=amount) | Q(stripe_customer_id=stripe_customer_id)
                )
                subscription_list = list(subscription_queryset)
                highest_id_row = subscription_list[0]
                voter_we_vote_id = highest_id_row.voter_we_vote_id
                not_loggedin_voter_we_vote_id = highest_id_row.not_loggedin_voter_we_vote_id
                if positive_value_exists(voter_we_vote_id) or positive_value_exists(not_loggedin_voter_we_vote_id):
                    success = True
                    status = "VOTER_WE_VOTE_ID_RETRIEVED"
                else:
                    success = False
                    status = "EXISTING_VOTER_WE_VOTE_ID_NOT_FOUND"
            except Exception as e:
                success = False
                status = "VOTER_WE_VOTE_ID_RETRIEVAL_ATTEMPT_FAILED"

        results = {
            'success': success,
            'status': status,
            'voter_we_vote_id': voter_we_vote_id,
            'not_loggedin_voter_we_vote_id': not_loggedin_voter_we_vote_id,
        }
        return results

    @staticmethod
    def retrieve_or_create_recurring_donation_plan(voter_we_vote_id, we_plan_id, donation_amount,
                                                   is_premium_plan, coupon_code, premium_plan_type_enum,
                                                   linked_organization_we_vote_id, recurring_interval, client_ip,
                                                   stripe_customer_id, is_signed_in):
        """
        June 2017, we create these records, but never read them for donations
        August 2019, we read them for subscriptions and (someday) organization paid subscriptions
        :param voter_we_vote_id:
        :param we_plan_id:
        :param donation_amount:
        :param is_premium_plan:
        :param coupon_code:
        :param premium_plan_type_enum:
        :param linked_organization_we_vote_id:
        :param recurring_interval:
        :param client_ip
        :param stripe_customer_id
        :param is_signed_in
        :return:
        """
        # recurring_we_plan_id = voter_we_vote_id + "-monthly-" + str(donation_amount)
        # we_plan_id = we_plan_id + " Plan"
        billing_interval = "monthly"  # This would be a good place to start for annual payment paid subscriptions
        currency = "usd"
        donation_plan_is_active = True
        exception_multiple_object_returned = False
        status = ''
        stripe_plan_id = ''
        success = False
        subscription_already_exists = False

        try:
            # the donation plan needs to exist in two places: our stripe account and our database
            # plans can be created here or in our stripe account dashboard

            if is_signed_in:
                voter_we_vote_id_2 = voter_we_vote_id
                not_loggedin_voter_we_vote_id = ''
            else:
                voter_we_vote_id_2 = ''
                not_loggedin_voter_we_vote_id = voter_we_vote_id

            subs_data = {
                'we_plan_id': we_plan_id,
                'amount': donation_amount,
                'billing_interval': billing_interval,
                'currency': currency,
                'donation_plan_is_active': donation_plan_is_active,
                'voter_we_vote_id': voter_we_vote_id_2,
                'not_loggedin_voter_we_vote_id': not_loggedin_voter_we_vote_id,
                'linked_organization_we_vote_id': linked_organization_we_vote_id,
                # 'organization_subscription_plan_id=org_subs_id,
                'client_ip': client_ip,
                'stripe_customer_id': stripe_customer_id,
                'stripe_charge_id': 'needs-match',
                'brand': 'needs-match',
                'exp_month': '0',
                'exp_year': '0',
                'last4': '0',
                'billing_reason': 'donationWithStripe_Api'
            }
            is_new, donation_plan_query = StripeManager.stripe_subscription_create_or_update(subs_data)

            if is_new:
                # if a donation plan is not found, we've added it to our database
                success = True
                status += 'SUBSCRIPTION_PLAN_CREATED_IN_DATABASE '
            else:
                # if it is found, do nothing - no need to update
                success = True
                status += 'DONATION_PLAN_ALREADY_EXISTS_IN_DATABASE '

            plan_id_query = {}
            try:
                plan_id_query = stripe.Plan.retrieve(we_plan_id)
            except stripe.error.StripeError as stripeError:
                # logger.error('Stripe (informational for splunk) error (1): %s', stripeError)
                pass

            if positive_value_exists(plan_id_query):
                if positive_value_exists(plan_id_query.id):
                    stripe_plan_id = plan_id_query.id
                    logger.debug("Stripe, plan_id_query.id " + plan_id_query.id)
        except StripeManager.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            success = False
            status += 'MULTIPLE_MATCHING_SUBSCRIPTION_PLANS_FOUND '
            exception_multiple_object_returned = True

        except stripe.error.StripeError as stripeError:
            logger.error('%s', 'Stripe error (2):', stripeError)
            pass

        except Exception as e:
            handle_exception(e, logger=logger)

        # if recurring_interval in ('month', 'year') and not positive_value_exists(stripe_plan_id) \
        #         and not org_subs_already_exists:
        #     # if plan doesn't exist in stripe, we need to create it (note it's already been created in database)
        #     plan = stripe.Plan.create(
        #         amount=donation_amount,
        #         interval=recurring_interval,
        #         currency="usd",
        #         nickname=we_plan_id,
        #         id=we_plan_id,
        #         product={
        #             "name": we_plan_id,
        #             "type": "service"
        #         },
        #     )
        #     if plan.id:
        #         success = True
        #         status += 'SUBSCRIPTION_PLAN_CREATED_IN_STRIPE '
        #     else:
        #         success = False
        #         status += 'SUBSCRIPTION_PLAN_NOT_CREATED_IN_STRIPE '
        # else:
        #     status += 'STRIPE_PLAN_NOT_CREATED-REQUIREMENTS_NOT_SATISFIED_OR_STRIPE_PLAN_ALREADY_EXISTS '
        results = {
            'success': success,
            'status': status,
            'subscription_already_exists': subscription_already_exists,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'recurring_we_plan_id': we_plan_id,
        }
        return results

    @staticmethod
    def retrieve_or_create_subscription_plan_definition(
            voter_we_vote_id,
            linked_organization_we_vote_id,
            stripe_customer_id,
            we_plan_id,
            subscription_cost_pennies,
            coupon_code,
            premium_plan_type_enum,
            recurring_interval):
        """
        August 2019, we read these records for organization paid subscriptions
        :param voter_we_vote_id:
        :param linked_organization_we_vote_id:
        :param stripe_customer_id:
        :param we_plan_id:
        :param subscription_cost_pennies:
        :param coupon_code:
        :param premium_plan_type_enum:
        :param recurring_interval:
        :return:
        """
        # recurring_interval is based on the Stripe constants: month and year
        # billing_interval is based on BILLING_FREQUENCY_CHOICES: SAME_DAY_MONTHLY, SAME_DAY_ANNUALLY
        # if recurring_interval == 'month':
        #     billing_interval = SAME_DAY_MONTHLY
        # elif recurring_interval == 'year':
        #     billing_interval = SAME_DAY_ANNUALLY
        # else:
        #     billing_interval = SAME_DAY_MONTHLY
        currency = "usd"
        exception_multiple_object_returned = False
        is_new = False
        is_premium_plan = True
        status = ''
        stripe_plan_id = ''
        success = False
        org_subs_id = 0
        donation_plan_definition = None
        donation_plan_definition_already_exists = False

        donation_plan_definition_id = 0
        try:
            # the subscription (used to be donation plan) needs to exist in two places: our stripe acct and our database
            # plans can be created here or in our stripe account dashboard
            subs_data = {
                # billing_interval': billing_interval,
                'amount': subscription_cost_pennies,
                'coupon_code': coupon_code,
                'currency': currency,
                'donation_plan_is_active': True,
                'is_premium_plan': is_premium_plan,
                'linked_organization_we_vote_id': linked_organization_we_vote_id,
                'organization_subscription_plan_id': org_subs_id,
                'premium_plan_type_enum': premium_plan_type_enum,
                'stripe_customer_id': stripe_customer_id,
                'voter_we_vote_id': voter_we_vote_id,
                'we_plan_id': we_plan_id,
            }
            is_new, donation_plan_query = StripeManager.stripe_subscription_create_or_update(subs_data)

            if is_new:
                # if a donation plan is not found, we've added it to our database
                success = True
                status += 'SUBSCRIPTION_PLAN_DEFINITION_CREATED_IN_DATABASE '
            else:
                # if it is found, do nothing - no need to update
                success = True
                status += 'SUBSCRIPTION_PLAN_DEFINITION_ALREADY_EXISTS_IN_DATABASE '
                donation_plan_definition_already_exists = True

            we_plan_id = donation_plan_definition.we_plan_id
            donation_plan_definition_id = donation_plan_definition.id
        except StripeSubscription.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            success = False
            status += 'MULTIPLE_MATCHING_SUBSCRIPTION_PLANS_FOUND '
            exception_multiple_object_returned = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'DONATION_PLAN_DEFINITION_GET_OR_CREATE-EXCEPTION: ' + str(e) + ' '

        try:
            stripe_plan = stripe.Plan.retrieve(we_plan_id)
            if positive_value_exists(stripe_plan.id):
                stripe_plan_id = stripe_plan.id
                logger.debug("Stripe, stripe_plan.id " + stripe_plan.id)
                status += 'EXISTING_STRIPE_PLAN_FOUND: ' + str(stripe_plan_id) + ' '
            else:
                status += 'EXISTING_STRIPE_PLAN_NOT_FOUND '
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'STRIPE_PLAN_RETRIEVE-EXCEPTION: ' + str(e) + ' '
        # except stripe.error.StripeError:
        #     pass

        if not positive_value_exists(stripe_plan_id):
            status += 'STRIPE_PLAN_TO_BE_CREATED '
            if recurring_interval in ('month', 'year'):
                # if plan doesn't exist in stripe, we need to create it (note it's already been created in database)
                plan = stripe.Plan.create(
                    amount=subscription_cost_pennies,
                    interval=recurring_interval,
                    currency="usd",
                    nickname=we_plan_id,
                    id=we_plan_id,
                    product={
                        "name": we_plan_id,
                        "type": "service"
                    },
                )
                if plan.id:
                    stripe_plan_id = plan.id
                    success = True
                    status += 'STRIPE_PLAN_CREATED_IN_STRIPE '
                else:
                    success = False
                    status += 'STRIPE_PLAN_NOT_CREATED_IN_STRIPE '
            else:
                status += 'STRIPE_PLAN_NOT_CREATED-REQUIREMENTS_NOT_SATISFIED '
        results = {
            'success': success,
            'status': status,
            'donation_plan_definition': donation_plan_definition,
            'donation_plan_definition_id': donation_plan_definition_id,
            'donation_plan_definition_already_exists': donation_plan_definition_already_exists,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'recurring_we_plan_id': we_plan_id,
        }
        return results

    @staticmethod
    def create_subscription_entry(subscription):
        print('create_subscription_entry', subscription)
        status = ''
        new_history_entry = 0
        try:
            new_history_entry = StripeManager.stripe_subscription_create_or_update(subscription)
            success = True
            status = 'NEW_DONATION_PAYMENT_ENTRY_SAVED '
        except Exception as e:
            success = False
            status += 'UNABLE_TO_SAVE_DONATION_PAYMENT_ENTRY, EXCEPTION: ' + str(e) + ' '

        saved_results = {
            'success': success,
            'status': status,
            'donation_journal_created': new_history_entry
        }
        return saved_results

    def create_recurring_donation(self, stripe_customer_id, voter_we_vote_id, donation_amount, start_date_time, email,
                                  is_premium_plan, coupon_code, premium_plan_type_enum, linked_organization_we_vote_id,
                                  client_ip, payment_method_id, is_signed_in):
        """

        :param stripe_customer_id:
        :param voter_we_vote_id:
        :param donation_amount:
        :param start_date_time:
        :param email:
        :param is_premium_plan:
        :param coupon_code:
        :param premium_plan_type_enum:
        :param linked_organization_we_vote_id:
        :param client_ip
        :param payment_method_id
        :param: is_signed_in
        :return:
        """
        plan_error = False
        status = ""
        results = {}
        stripe_subscription_created = False
        org_segment = "organization-" if is_premium_plan else ""
        periodicity = "-monthly-"
        if "_YEARLY" in premium_plan_type_enum:
            periodicity = "-yearly-"
        we_plan_id = voter_we_vote_id + periodicity + org_segment + str(donation_amount)

        donation_plan_results = self.retrieve_or_create_recurring_donation_plan(
            voter_we_vote_id, we_plan_id, donation_amount, is_premium_plan, coupon_code,
            premium_plan_type_enum, linked_organization_we_vote_id, 'month', client_ip, stripe_customer_id,
            is_signed_in)
        subscription_already_exists = donation_plan_results['subscription_already_exists']
        success = donation_plan_results['success']
        status += donation_plan_results['status']
        if not subscription_already_exists and success:
            try:
                # If not logged in, this voter_we_vote_id will not be the same as the logged in id.
                # Passing the voter_we_vote_id to the subscription gives us a chance to associate logged in with not
                # logged in subscriptions in the future
                name = "product_for_" + we_plan_id
                productc = stripe.Product.create(name=name)
                nickname = we_plan_id
                pricec = stripe.Price.create(
                    unit_amount=donation_amount,
                    currency="usd",
                    recurring={"interval": "month"},
                    product=productc.stripe_id,
                    nickname=nickname
                )

                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=stripe_customer_id,
                )

                subscription = stripe.Subscription.create(
                    customer=stripe_customer_id,
                    items=[
                        {'price': pricec.stripe_id, }
                    ],
                    default_payment_method=payment_method_id
                )
                success = True
                stripe_subscription_id = subscription['id']
                status += "USER_SUCCESSFULLY_SUBSCRIBED_TO_PLAN "
                stripe_subscription_created = True

                results = {
                    'success': success,
                    'status': status,
                    'voter_subscription_saved': status,
                    'stripe_subscription_created': stripe_subscription_created,
                    'code': '',
                    'decline_code': '',
                    'error_message': '',
                    'subscription_plan_id': we_plan_id,
                    'subscription_created_at': subscription['created'],
                    'stripe_subscription_id': stripe_subscription_id,
                    'subscription_already_exists': False,
                }

            except AttributeError as err:
                # Something else happened, completely unrelated to Stripe
                logger.error("create_recurring_donation caught: ", err)
                pass

            except stripe.error.StripeError as e:
                success = False
                body = e.json_body
                err = body['error']
                status += "STRIPE_ERROR_IS_" + err['message'] + "_END"
                logger.error("%s", "create_recurring_donation StripeError: " + status)

                remove_results = self.remove_subscription(we_plan_id)
                status += " " + remove_results['status']

                results = {
                    'success': False,
                    'status': status,
                    'voter_subscription_saved': False,
                    'subscription_already_exists': False,
                    'stripe_subscription_created': stripe_subscription_created,
                    'code': err['code'],
                    'decline_code': err['decline_code'],
                    'error_message': err['message'],
                    'subscription_plan_id': "",
                    'subscription_created_at': "",
                    'stripe_subscription_id': ""
                }
        else:
            results = {
                'success': success,
                'status': status,
                'voter_subscription_saved': False,
                'subscription_already_exists': subscription_already_exists,
                'stripe_subscription_created': stripe_subscription_created,
                'code': '',
                'decline_code': '',
                'error_message': '',
                'subscription_plan_id': "",
                'subscription_created_at': "",
                'stripe_subscription_id': ""
            }

        return results

    # def create_organization_subscription(
    #         self, stripe_customer_id, voter_we_vote_id, donation_amount, start_date_time, email,
    #         coupon_code, premium_plan_type_enum, linked_organization_we_vote_id, recurring_interval):
    #     """
    #
    #     :param stripe_customer_id:
    #     :param voter_we_vote_id:
    #     :param donation_amount:
    #     :param start_date_time:
    #     :param email:
    #     :param coupon_code:
    #     :param premium_plan_type_enum:
    #     :param linked_organization_we_vote_id:
    #     :param recurring_interval:
    #     :return:
    #     """
    #     status = ""
    #     success = False
    #     stripe_subscription_created = False
    #     subscription_created_at = ''
    #     stripe_subscription_id = ''
    #
    #     org_segment = "organization-"
    #     periodicity ="-monthly-"
    #     if "_YEARLY" in premium_plan_type_enum:
    #         periodicity = "-yearly-"
    #     we_plan_id = voter_we_vote_id + periodicity + org_segment + str(donation_amount)
    #
    #     # We have already previously retrieved the coupon_price, and updated the donation_amount.
    #     # Here, we are incrementing the redemption counter
    #     increment_redemption_count = True
    #     coupon_price, org_subs_id = DonationManager.get_coupon_price(premium_plan_type_enum, coupon_code,
    #                                                                  increment_redemption_count)
    #
    #     plan_results = self.retrieve_or_create_subscription_plan_definition(
    #         voter_we_vote_id, linked_organization_we_vote_id, stripe_customer_id,
    #         we_plan_id, donation_amount, coupon_code, premium_plan_type_enum,
    #         recurring_interval)
    #     donation_plan_definition_already_exists = plan_results['donation_plan_definition_already_exists']
    #     status = plan_results['status']
    #     donation_plan_definition_id = plan_results['donation_plan_definition_id']
    #     if plan_results['success']:
    #         donation_plan_definition = plan_results['donation_plan_definition']
    #         try:
    #             # If not logged in, this voter_we_vote_id will not be the same as the logged in id.
    #             # Passing the voter_we_vote_id to the subscription gives us a chance to associate logged in with not
    #             # logged in subscriptions in the future
    #             subscription = stripe.Subscription.create(
    #                 customer=stripe_customer_id,
    #                 plan=we_plan_id,
    #                 metadata={
    #                     'linked_organization_we_vote_id': linked_organization_we_vote_id,
    #                     'voter_we_vote_id': voter_we_vote_id,
    #                     'email': email
    #                 }
    #             )
    #             stripe_subscription_created = True
    #             success = True
    #             stripe_subscription_id = subscription['id']
    #             subscription_created_at = subscription['created']
    #             status += "USER_SUCCESSFULLY_SUBSCRIBED_TO_PLAN "
    #         except stripe.error.StripeError as e:
    #             success = False
    #             body = e.json_body
    #             err = body['error']
    #             status = "STRIPE_ERROR_IS_" + err['message'] + "_END"
    #             logger.error('%s', "create_recurring_donation StripeError: " + status)
    #
    #         if positive_value_exists(stripe_subscription_id):
    #             try:
    #                 donation_plan_definition.stripe_subscription_id = stripe_subscription_id
    #                 donation_plan_definition.save()
    #                 status += "STRIPE_SUBSCRIPTION_ID_SAVED_IN_DONATION_PLAN_DEFINITION "
    #             except Exception as e:
    #                 status += "FAILED_TO_SAVE_STRIPE_SUBSCRIPTION_ID_IN_DONATION_PLAN_DEFINITION "
    #     results = {
    #         'success': success,
    #         'status': status,
    #         'stripe_subscription_created': stripe_subscription_created,
    #         'subscription_plan_id': we_plan_id,
    #         'subscription_created_at': subscription_created_at,
    #         'stripe_subscription_id': stripe_subscription_id,
    #         'donation_plan_definition_already_exists': donation_plan_definition_already_exists,
    #     }
    #     return results

    @staticmethod
    def retrieve_stripe_card_error_message(error_type):
        """

        :param error_type:
        :return:
        """
        voter_card_error_message = 'Your card has been declined for an unknown reason. Contact your bank for more' \
                                   ' information.'

        card_error_message = {
            'approve_with_id': 'The transaction cannot be authorized. Please try again or contact your bank.',
            'card_not_supported': 'Your card does not support this type of purchase. Contact your bank for more '
                                  'information.',
            'card_velocity_exceeded': 'You have exceeded the balance or credit limit available on your card.',
            'currency_not_supported': 'Your card does not support the specified currency.',
            'duplicate_transaction': 'This transaction has been declined because a transaction with identical amount '
                                     'and credit card information was submitted very recently.',
            'fraudulent': 'This transaction has been flagged as potentially fraudulent. Contact your bank for more '
                          'information.',
            'incorrect_number': 'Your card number is incorrect. Please enter the correct number and try again.',
            'incorrect_pin': 'Your pin is incorrect. Please enter the correct number and try again.',
            'incorrect_zip': 'Your ZIP/postal code is incorrect. Please enter the correct number and try again.',
            'insufficient_funds': 'Your card has insufficient funds to complete this transaction.',
            'invalid_account': 'Your card, or account the card is connected to, is invalid. Contact your bank for more'
                               ' information.',
            'invalid_amount': 'The payment amount exceeds the amount that is allowed. Contact your bank for more '
                              'information.',
            'invalid_cvc': 'Your CVC number is incorrect. Please enter the correct number and try again.',
            'invalid_expiry_year': 'The expiration year is invalid. Please enter the correct number and try again.',
            'invalid_number': 'Your card number is incorrect. Please enter the correct number and try again.',
            'invalid_pin': 'Your pin is incorrect. Please enter the correct number and try again.',
            'issuer_not_available': 'The payment cannot be authorized. Please try again or contact your bank.',
            'new_account_information_available': 'Your card, or account the card is connected to, is invalid. Contact '
                                                 'your bank for more information.',
            'withdrawal_count_limit_exceeded': 'You have exceeded the balance or credit limit on your card. Please try '
                                               'another payment method.',
            'pin_try_exceeded': 'The allowable number of PIN tries has been exceeded. Please try again later or use '
                                   'another payment method.',
            'processing_error': 'An error occurred while processing the card. Please try again.'
        }

        for error in card_error_message:
            if error == error_type:
                voter_card_error_message = card_error_message[error]
                break
                # Any other error types that are not in this dict will use the generic voter_card_error_message

        return voter_card_error_message

    @staticmethod
    def retrieve_donation_journal_list(voter_we_vote_id):
        """

        :param voter_we_vote_id:
        :return:
        """
        donation_journal_list = []
        status = ''

        try:
            donation_queryset = StripePayments.objects.all().order_by('-created')
            donation_queryset = donation_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            donation_journal_list = list(donation_queryset)

            if len(donation_journal_list):
                success = True
                status += ' CACHED_WE_VOTE_DONATION_PAYMENT_HISTORY_LIST_RETRIEVED '
            else:
                donation_journal_list = []
                success = True
                status += ' NO_DONATION_PAYMENT_HISTORY_EXISTS_FOR_THIS_VOTER '

        except StripePayments.DoesNotExist:
            status += " WE_VOTE_HISTORY_DOES_NOT_EXIST "
            success = True

        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_WE_VOTE_HISTORY_LIST "
            success = False
            # handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'status':                   status,
            'donation_journal_list':    donation_journal_list,
        }

        return results

    @staticmethod
    def retrieve_donation_subscription_list(voter_we_vote_id):
        """

        :param voter_we_vote_id:
        :return:
        """
        subscription_list = []
        status = ''

        try:
            subscription_queryset = StripeSubscription.objects.all().order_by('-subscription_created_at')
            subscription_queryset = subscription_queryset.filter(
                Q(voter_we_vote_id__iexact=voter_we_vote_id) | Q(not_loggedin_voter_we_vote_id__iexact=voter_we_vote_id)
            )
            subscription_list = list(subscription_queryset)

            if len(subscription_list):
                success = True
                status += ' CACHED_WE_VOTE_DONATION_SUBSCRIPTION_LIST_RETRIEVED '
            else:
                subscription_list = []
                success = True
                status += ' NO_DONATION_SUBSCRIPTION_LIST_EXISTS_FOR_THIS_VOTER '

        except StripePayments.DoesNotExist:
            status += " DONATION_SUBSCRIPTION_LIST_DOES_NOT_EXIST "
            success = True

        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_DONATION_SUBSCRIPTION_LIST "
            success = False
            # handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'subscription_status':      status,
            'subscription_list':        subscription_list,
        }

        return results

    @staticmethod
    def retrieve_payment_for_charge(stripe_charge_id):
        status = ''
        payment = []

        try:
            payment_queryset = StripePayments.objects.all().order_by('-created')
            payment_queryset = payment_queryset.filter(stripe_charge_id__iexact=stripe_charge_id)
            payment_list = list(payment_queryset)

            if len(payment_list):
                success = True
                status += ' CACHED_WE_VOTE_DONATION_PAYMENT_LIST_RETRIEVED_FOR_CHARGE_ID '
                payment = payment_list[0]

            else:
                payment_list = []
                success = True
                status += ' NO_DONATION_PAYMENT_LIST_EXISTS_FOR_THIS_VOTER_FOR_CHARGE_ID '

        except StripePayments.DoesNotExist:
            status += " DONATION_PAYMENT_LIST_DOES_NOT_EXIST_FOR_CHARGE_ID "
            success = True

        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_DONATION_PAYMENT_LIST_FOR_CHARGE_ID "
            success = False
            # handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'payment_status':           status,
            'payment':                  payment,
        }

        return results

    @staticmethod
    def retrieve_donation_payment_list(voter_we_vote_id):
        """

        :param voter_we_vote_id:
        :return:
        """
        status = ''
        payment_list = []

        try:
            payment_queryset = StripePayments.objects.all().order_by('-created')
            payment_queryset = payment_queryset.filter(
                Q(voter_we_vote_id__iexact=voter_we_vote_id) | Q(not_loggedin_voter_we_vote_id__iexact=voter_we_vote_id)
            )
            payment_list = list(payment_queryset)

            if len(payment_list):
                success = True
                status += ' CACHED_WE_VOTE_DONATION_PAYMENT_LIST_RETRIEVED '
            else:
                payment_list = []
                success = True
                status += ' NO_DONATION_PAYMENT_LIST_EXISTS_FOR_THIS_VOTER '

        except StripePayments.DoesNotExist:
            status += " DONATION_PAYMENT_LIST_DOES_NOT_EXIST "
            success = True

        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_DONATION_PAYMENT_LIST "
            success = False
            # handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success':                  success,
            'payment_status':           status,
            'payment_list':             payment_list,
        }

        return results

    @staticmethod
    def retrieve_donation_plan_definition(voter_we_vote_id='', linked_organization_we_vote_id='', is_premium_plan=True,
                                          premium_plan_type_enum='', donation_plan_is_active=True):
        donation_plan_definition = None
        donation_plan_definition_found = False
        status = ''

        try:
            donation_queryset = StripeSubscription.objects.all().order_by('-id')
            if positive_value_exists(voter_we_vote_id):
                donation_queryset = donation_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            elif positive_value_exists(linked_organization_we_vote_id):
                donation_queryset = donation_queryset.filter(linked_organization_we_vote_id__iexact=linked_organization_we_vote_id)
            donation_queryset = donation_queryset.filter(is_premium_plan=is_premium_plan)
            if positive_value_exists(premium_plan_type_enum):
                donation_queryset = donation_queryset.filter(premium_plan_type_enum__iexact=premium_plan_type_enum)
            if positive_value_exists(donation_plan_is_active):
                donation_queryset = donation_queryset.filter(donation_plan_is_active=donation_plan_is_active)
            subscription_list = list(donation_queryset)

            if len(subscription_list):
                donation_plan_definition = subscription_list[0]
                donation_plan_definition_found = True
                status += 'DONATION_PLAN_DEFINITION_RETRIEVED '
                success = True
            else:
                status += 'DONATION_PLAN_DEFINITION_LIST_EMPTY '
                success = True

        except StripeSubscription.DoesNotExist:
            status += "DONATION_PLAN_DEFINITION_LIST_EMPTY2 "
            success = True

        except Exception as e:
            status += "DONATION_PLAN_DEFINITION_LIST-FAILED_TO_RETRIEVE " + str(e) + " "
            success = False

        results = {
            'success':                          success,
            'status':                           status,
            'donation_plan_definition':         donation_plan_definition,
            'donation_plan_definition_found':   donation_plan_definition_found,
        }

        return results

    @staticmethod
    def retrieve_subscription_list(voter_we_vote_id='', linked_organization_we_vote_id='',
                                               return_json_version=False):
        subscription_list = []
        subscription_list_json = []
        status = ''

        try:
            donation_queryset = StripeSubscription.objects.all().order_by('-id')
            if positive_value_exists(voter_we_vote_id):
                donation_queryset = donation_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            if positive_value_exists(linked_organization_we_vote_id):
                donation_queryset = donation_queryset.filter(linked_organization_we_vote_id__iexact=linked_organization_we_vote_id)
            subscription_list = list(donation_queryset)

            if len(subscription_list):
                status += 'subscription_LIST_RETRIEVED '
                success = True
            else:
                subscription_list = []
                status += 'subscription_LIST_EMPTY '
                success = True

        except StripeSubscription.DoesNotExist:
            status += "subscription_LIST_EMPTY2 "
            success = True

        except Exception as e:
            status += "subscription_LIST-FAILED_TO_RETRIEVE " + str(e) + " "
            success = False
            # handle_exception(e, logger=logger, exception_message=status)

        if positive_value_exists(return_json_version):
            for subscription in subscription_list:
                json = {
                    'amount':                   subscription.amount,
                    'brand':                    subscription.brand,
                    'billing_interval':         subscription.billing_interval,
                    'currency':                 subscription.currency,
                    'donation_plan_is_active':  subscription.donation_plan_is_active,
                    'exp_month':                subscription.exp_month,
                    'exp_year':                 subscription.exp_year,
                    'last4':                    subscription.last4,
                    'last_charged':             subscription.last_charged,
                    'linked_organization_we_vote_id': subscription.linked_organization_we_vote_id,
                    'stripe_subscription_id':   subscription.stripe_subscription_id,
                    'subscription_canceled_at': subscription.subscription_canceled_at,
                    'subscription_created_at':  subscription.subscription_created_at,
                    'subscription_ended_at':    subscription.subscription_ended_at,
                    'voter_we_vote_id':         subscription.voter_we_vote_id,
                    'we_plan_id': subscription.we_plan_id,
                    # 'coupon_code': subscription.coupon_code,
                    # 'is_premium_plan': subscription.is_premium_plan,
                    # 'organization_subscription_plan_id': subscription.organization_subscription_plan_id,
                    # 'paid_without_stripe': subscription.paid_without_stripe,
                    # 'paid_without_stripe_comment': subscription.paid_without_stripe_comment,
                    # 'paid_without_stripe_expiration_date':
                    #         subscription.paid_without_stripe_expiration_date,
                    # 'plan_id': subscription.plan_name,
                    # 'premium_plan_type_enum': subscription.premium_plan_type_enum,
                }
                subscription_list_json.append(json)

        results = {
            'success':                success,
            'status':                 status,
            'subscription_list':      subscription_list,
            'subscription_list_json': subscription_list_json,
        }

        return results

    # @staticmethod
    # def retrieve_master_feature_package(chosen_feature_package):
    #     status = ''
    #     master_feature_package = None
    #     master_feature_package_found = False
    #
    #     try:
    #         master_feature_package = MasterFeaturePackage.objects.get(
    #             master_feature_package__iexact=chosen_feature_package)
    #         master_feature_package_found = True
    #         success = True
    #     except MasterFeaturePackage.DoesNotExist:
    #         status += "MASTER_FEATURE_PACKAGE_NOT_FOUND "
    #         success = True
    #     except Exception as e:
    #         status += "MASTER_FEATURE_PACKAGE_EXCEPTION: " + str(e) + " "
    #         success = False
    #
    #     results = {
    #         'success':                      success,
    #         'status':                       status,
    #         'master_feature_package':       master_feature_package,
    #         'master_feature_package_found': master_feature_package_found,
    #     }
    #
    #     return results

    @staticmethod
    def does_donation_journal_charge_exist(charge_id):
        """

        :param charge_id:
        :return:
        """
        try:
            donation_queryset = StripePayments.objects.all()
            donation_queryset = donation_queryset.filter(charge_id=charge_id)

            if len(donation_queryset):
                exists = True
                success = True
            else:
                exists = False
                success = True

        except Exception as e:
            exists = False
            success = True
            handle_exception(e, logger=logger, exception_message="Exception in does_donation_journal_charge_exist")

        results = {
            'exists': exists,
            'success': success,
        }

        return results

    @staticmethod
    def does_paid_subscription_exist(linked_organization_we_vote_id):
        found_live_paid_subscription_for_the_org = False
        try:
            donation_queryset = StripePayments.objects.all()
            donation_queryset = donation_queryset.filter(record_enum='SUBSCRIPTION_SETUP_AND_INITIAL',
                                                         is_premium_plan=True)

            if len(donation_queryset) == 0:
                found_live_paid_subscription_for_the_org = False
            else:
                journal_list_objects = list(donation_queryset)
                for journal in journal_list_objects:
                    if not positive_value_exists(journal.subscription_canceled_at):
                        print('does_paid_subscription_exist FOUND LIVE SUBSCRIPTION AT id: ' + str(journal.id))
                        found_live_paid_subscription_for_the_org = True

        except Exception as e:
            found_live_paid_subscription_for_the_org = False
            handle_exception(e, logger=logger, exception_message="Exception in does_paid_subscription_exist")

        return found_live_paid_subscription_for_the_org

    # @staticmethod
    # def retrieve_subscription_plan_list():
    #     """
    #     Retrieve coupons
    #     :return:
    #     """
    #     subscription_plan_list = []
    #     status = ''
    #
    #     DonationManager.create_initial_coupons()
    #     DonationManager.create_initial_master_feature_packages()
    #     try:
    #         plan_queryset = OrganizationSubscriptionPlans.objects.order_by('-plan_created_at')
    #         subscription_plan_list = plan_queryset
    #
    #         if len(plan_queryset):
    #             success = True
    #             status += ' ORGANIZATIONAL_SUBSCRIPTION_PLANS_LIST_RETRIEVED '
    #         else:
    #             subscription_plan_list = []
    #             success = False
    #             status += " NO_ORGANIZATIONAL_SUBSCRIPTION_PLAN_EXISTS "
    #
    #     except Exception as e:
    #         status += " FAILED_TO_RETRIEVE_ORGANIZATIONAL_SUBSCRIPTION_PLANS_LIST "
    #         success = False
    #         handle_exception(e, logger=logger, exception_message=status)
    #
    #     results = {
    #         'success': success,
    #         'status': status,
    #         'subscription_plan_list': subscription_plan_list
    #     }
    #
    #     return results

    @staticmethod
    def mark_donation_journal_canceled_or_ended(stripe_subscription_id, customer_id, subscription_ended_at,
                                                subscription_canceled_at):
        """

        :param stripe_subscription_id:
        :param customer_id:
        :param subscription_ended_at:
        :param subscription_canceled_at:
        :return:
        """
        status = ''
        try:
            subscription_row = StripeSubscription.objects.get(stripe_subscription_id=stripe_subscription_id)
            subscription_row.subscription_ended_at = datetime.fromtimestamp(subscription_ended_at, timezone.utc)
            subscription_row.subscription_canceled_at = datetime.fromtimestamp(subscription_canceled_at, timezone.utc)
            subscription_row.donation_plan_is_active = False
            subscription_row.save()
            status += "DONATION_PAYMENT_SAVED-MARKED_CANCELED "
            success = True
        except StripePayments.DoesNotExist:
            status += "mark_donation_journal_canceled_or_ended: " + \
                      "Subscription " + stripe_subscription_id + " with customer_id " + \
                      customer_id + " does not exist"
            logger.error('%s', status)
            success = True
        except Exception as e:
            handle_exception(e, logger=logger, exception_message="Exception in mark_donation_journal_canceled_or_ended")
            status += "mark_donation_journal_canceled_or_ended EXCEPTION: " + str(e) + " "
            success = False

        return {
            'status':   status,
            'success':  success,
        }

    @staticmethod
    def mark_subscription_as_canceled(donation_plan_definition_id=0, stripe_subscription_id=''):
        status = ''
        success = False
        donation_plan_definition = None
        donation_plan_definition_found = False
        try:
            if positive_value_exists(donation_plan_definition_id):
                donation_plan_definition = StripeSubscription.objects.get(id=donation_plan_definition_id)
                donation_plan_definition_found = True
            elif positive_value_exists(stripe_subscription_id):
                donation_plan_definition = StripeSubscription.objects.get(
                    stripe_subscription_id=stripe_subscription_id)
                donation_plan_definition_found = True

            if donation_plan_definition_found:
                status += "DONATION_PLAN_DEFINITION_FOUND "
                donation_plan_definition.donation_plan_is_active = False
                donation_plan_definition.save()
                status += "DONATION_PLAN_DEFINITION_SAVED "
            else:
                status += "DONATION_PLAN_DEFINITION_NOT_FOUND "
        except Exception as e:
            handle_exception(e, logger=logger, exception_message="Exception in mark_subscription_as_canceled")
            status += "MARK_DONATION_PLAN_DEFINITION-FAILED: " + str(e) + " "
        return {
            'status':   status,
            'success':  success,
        }

    @staticmethod
    def remove_subscription(we_plan_id):
        success = False
        status = ''
        try:
            StripeSubscription.objects.get(we_plan_id=we_plan_id, stripe_charge_id__isnull=True).delete()
            success = True
            status = 'SUBSCRIPTION_DELETED_ON_INITIAL_CHARGE_FAILURE'
        except Exception as e:
            handle_exception(e, logger=logger, exception_message="Exception in mark_subscription_as_canceled")
            status = "DELETE_SUBSCRIPTION-FAILED: " + str(e) + " "
        return {
            'status':   status,
            'success':  success,
        }

    @staticmethod
    def mark_latest_donation_plan_definition_canceled(voter_we_vote_id):
        # There can only be one active organization paid plan at one time, so mark the first active one as inactive
        org_we_vote_id = ''
        try:
            voter_manager = VoterManager()
            org_we_vote_id = voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(voter_we_vote_id)

            rows = StripeSubscription.objects.get(linked_organization_we_vote_id__iexact=org_we_vote_id,
                                                  is_premium_plan=True,
                                                  donation_plan_is_active=True)
            if len(rows):
                row = rows[0]
                row.donation_plan_is_active = False
                print('StripeSubscription for ' + org_we_vote_id + ' is now marked as inactive')
                row.save()
            else:
                print('StripeSubscription for ' + org_we_vote_id + ' not found')
                logger.error('%s', 'StripeSubscription for ' + org_we_vote_id +
                             ' not found in mark_latest_donation_plan_definition_canceled')

        except Exception as e:
            logger.error('%s', 'StripeSubscription for ' + org_we_vote_id +
                         ' threw exception: ' + str(e))
        return

    @staticmethod
    def move_donate_link_to_voter_from_voter_to_voter(from_voter, to_voter):
        """

        :param from_voter:
        :param to_voter:
        :return:
        """
        status = ''
        donate_link_list = []
        voter_we_vote_id = from_voter.we_vote_id
        to_voter_we_vote_id = to_voter.we_vote_id

        try:
            donate_link_query = StripeLinkToVoter.objects.all()
            donate_link_query = donate_link_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            donate_link_list = list(donate_link_query)
            status += "move_donate_link_to_voter_from_voter_to_voter LIST_RETRIEVED-" + \
                      voter_we_vote_id + "-TO-" + to_voter_we_vote_id + " LENGTH: " + str(len(donate_link_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donate_link_to_voter_from_voter_to_voter "
            logger.error('%s', "move_donate_link_to_voter_from_voter_to_voter 2:" + status)
            success = False

        donate_link_migration_count = 0
        donate_link_migration_fails = 0
        for donate_link in donate_link_list:
            try:
                donate_link.voter_we_vote_id = to_voter_we_vote_id
                donate_link.save()
                donate_link_migration_count += 1
            except Exception as e:
                donate_link_migration_fails += 1

        if positive_value_exists(donate_link_migration_count):
            status += "DONATE_LINK_MOVED: " + str(donate_link_migration_count) + " "
        if positive_value_exists(donate_link_migration_fails):
            status += "DONATE_LINK_FAILS: " + str(donate_link_migration_fails) + " "

        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    @staticmethod
    def move_donation_payment_entries_from_voter_to_voter(from_voter, to_voter):
        """

        :param from_voter:
        :param to_voter:
        :return:
        """
        status = ''
        donation_payments_list = []
        voter_we_vote_id = from_voter.we_vote_id
        to_voter_we_vote_id = to_voter.we_vote_id

        try:
            donation_payments_query = StripePayments.objects.all()
            donation_payments_query = donation_payments_query.filter(
                Q(voter_we_vote_id__iexact=voter_we_vote_id) | Q(not_loggedin_voter_we_vote_id__iexact=voter_we_vote_id)
            )
            donation_payments_list = list(donation_payments_query)
            status += "move_donation_payment_entries_from_voter_to_voter LIST_RETRIEVED-" + \
                      voter_we_vote_id + "-TO-" + to_voter_we_vote_id + \
                      " LENGTH: " + str(len(donation_payments_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donation_payment_entries_from_voter_to_voter "
            logger.error('%s', "move_donation_payment_entries_from_voter_to_voter 2:", e)
            success = False

        donation_payment_migration_count = 0
        donation_payment_migration_fails = 0
        for donation_payment in donation_payments_list:
            try:
                donation_payment.voter_we_vote_id = to_voter_we_vote_id
                donation_payment.save()
                donation_payment_migration_count += 1
            except Exception as e:
                donation_payment_migration_fails += 1

        if positive_value_exists(donation_payment_migration_count):
            status += "DONATION_PAYMENT_MOVED: " + str(donation_payment_migration_count) + " "
        if positive_value_exists(donation_payment_migration_fails):
            status += "DONATION_PAYMENT_FAILS: " + str(donation_payment_migration_fails) + " "

        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    @staticmethod
    def move_stripe_subscription_entries_from_voter_to_voter(from_voter, to_voter):
        """

        :param from_voter:
        :param to_voter:
        :return:
        """
        status = ''
        donation_subscription_list = []
        voter_we_vote_id = from_voter.we_vote_id
        to_voter_we_vote_id = to_voter.we_vote_id

        try:
            donation_subscription_query = StripeSubscription.objects.all()
            # donation_plan_definition_query = donation_plan_definition_query.filter(
            #     voter_we_vote_id__iexact=voter_we_vote_id)

            donation_subscription_query = donation_subscription_query.filter(
                Q(voter_we_vote_id=voter_we_vote_id) | Q(not_loggedin_voter_we_vote_id=voter_we_vote_id)
            )

            donation_subscription_list = list(donation_subscription_query)
            status += "move_stripe_subscription_entries_from_voter_to_voter LIST_RETRIEVED-" + \
                      voter_we_vote_id + "-TO-" + to_voter_we_vote_id + \
                      " LENGTH: " + str(len(donation_subscription_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_stripe_subscription_entries_from_voter_to_voter "
            logger.error('%s', "move_stripe_subscription_entries_from_voter_to_voter 2:" + status)
            success = False

        donation_subscription_migration_count = 0
        donation_subscription_migration_fails = 0
        for donation_subscription in donation_subscription_list:
            try:
                donation_subscription.voter_we_vote_id = to_voter_we_vote_id
                donation_subscription.save()
                donation_subscription_migration_count += 1
            except Exception as e:
                donation_subscription_migration_fails += 1

        if positive_value_exists(donation_subscription_migration_count):
            status += "DONATION_PLAN_DEFINITION_MOVED: " + str(donation_subscription_migration_count) + " "
        if positive_value_exists(donation_subscription_migration_fails):
            status += "DONATION_PLAN_DEFINITION_FAILS: " + str(donation_subscription_migration_fails) + " "

        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    @staticmethod
    def move_donation_payment_entries_from_organization_to_organization(
            from_organization_we_vote_id, to_organization_we_vote_id):
        """

        :param from_organization_we_vote_id:
        :param to_organization_we_vote_id:
        :return:
        """
        status = ''
        donation_payments_list = []

        try:
            donation_payments_query = StripePayments.objects.all()
            donation_payments_query = donation_payments_query.filter(
                linked_organization_we_vote_id__iexact=from_organization_we_vote_id)
            donation_payments_list = list(donation_payments_query)
            status += "move_donation_payment_entries_from_organization_to_organization LIST_RETRIEVED-" + \
                      from_organization_we_vote_id + "-TO-" + to_organization_we_vote_id +  \
                      " LENGTH: " + str(len(donation_payments_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donation_payment_entries_from_organization_to_organization "
            logger.error('%s', "move_donation_payment_entries_from_organization_to_organization 2:" + status)
            success = False

        donation_payment_migration_count = 0
        donation_payment_migration_fails = 0
        for donation_payment in donation_payments_list:
            try:
                donation_payment.linked_organization_we_vote_id = to_organization_we_vote_id
                donation_payment.save()
                donation_payment_migration_count += 1
            except Exception as e:
                donation_payment_migration_fails += 1

        if positive_value_exists(donation_payment_migration_count):
            status += "DONATION_PAYMENT_MOVED: " + str(donation_payment_migration_count) + " "
        if positive_value_exists(donation_payment_migration_fails):
            status += "DONATION_PAYMENT_FAILS: " + str(donation_payment_migration_fails) + " "

        results = {
            'status':                       status,
            'success':                      success,
            'from_organization_we_vote_id': from_organization_we_vote_id,
            'to_organization_we_vote_id':   to_organization_we_vote_id,
        }
        return results

    @staticmethod
    def move_stripe_donation_payments_from_organization_to_organization(
            from_organization_we_vote_id, to_organization_we_vote_id):
        """

        :param from_organization_we_vote_id:
        :param to_organization_we_vote_id:
        :return:
        """
        status = ''
        payments_list = []

        try:
            payments_query = StripeSubscription.objects.all()
            payments_query = payments_query.filter(
                linked_organization_we_vote_id__iexact=from_organization_we_vote_id)
            payments_list = list(payments_query)
            status += "move_stripe_donation_payments_from_organization_to_organization LIST_RETRIEVED-" + \
                      from_organization_we_vote_id + "-TO-" + to_organization_we_vote_id + \
                      " LENGTH: " + str(len(payments_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_stripe_donation_payments_from_organization_to_organization "
            logger.error('%s', "move_stripe_donation_payments_from_organization_to_organization 2:" + status)
            success = False

        payments_migration_count = 0
        payments_migration_fails = 0
        for donation_plan_definition in payments_list:
            try:
                donation_plan_definition.linked_organization_we_vote_id = to_organization_we_vote_id
                donation_plan_definition.save()
                payments_migration_count += 1
            except Exception as e:
                payments_migration_fails += 1

        if positive_value_exists(payments_migration_count):
            status += "DONATION_PLAN_DEFINITION_MOVED: " + str(payments_migration_count) + " "
        if positive_value_exists(payments_migration_fails):
            status += "DONATION_PLAN_DEFINITION_FAILS: " + str(payments_migration_fails) + " "

        results = {
            'status':                       status,
            'success':                      success,
            'from_organization_we_vote_id': from_organization_we_vote_id,
            'to_organization_we_vote_id':   to_organization_we_vote_id,
        }
        return results

    @staticmethod
    def check_for_subscription_in_db_without_card_info(customer, plan_id):
        # get the rows with the correct subscription_plan_id, most recently created first (created a few seconds ago)
        # since subscription_plan_id has the we_voter_voter_id, it is very specific
        row_id = -1
        try:
            queryset = StripePayments.objects.all().order_by('-id')
            rows = queryset.filter(subscription_plan_id=plan_id)
            if len(rows):
                row = rows[0]
                if row.last4 == 0:
                    row_id = row.id
        except StripePayments.DoesNotExist:
            logger.error('%s', "check_for_subscription_in_db_without_card_info row does not exist for stripe customer" +
                         customer)
        except Exception as e:
            logger.error('%s', "check_for_subscription_in_db_without_card_info Exception " + str(e))

        return row_id

    @staticmethod
    def update_subscription_on_charge_success(we_plan_id, stripe_request_id, stripe_subscription_id,
                                              stripe_charge_id, subscription_created_at, last_charged,
                                              amount, billing_reason, api_version):
        try:
            charge_data = {
                'amount': amount,
                'we_plan_id': we_plan_id,
                'stripe_request_id': stripe_request_id,
                'stripe_subscription_id': stripe_subscription_id,
                'stripe_charge_id': stripe_charge_id,
                'subscription_created_at': subscription_created_at,
                'last_charged': last_charged,
                'api_version': api_version,
                'voter_we_vote_id': 'unknown',
                'billing_reason': billing_reason,
            }
            StripeManager.stripe_subscription_create_or_update(charge_data)
            logger.debug("update_subscription_on_charge_success plan_id=" + we_plan_id + ", stripe_subscription_id=" +
                         stripe_subscription_id)
        except Exception as err:
            logger.error('%s', "update_subscription_on_charge_success: " + str(err))

        return

    @staticmethod
    def update_subscription_and_payment_on_charge_success(charge_data):
        try:
            StripeManager.stripe_payment_create_or_update(charge_data)
            logger.debug("update_subscription_and_payment_on_charge_success PAYMENTS stripe_charge_id=" +
                         charge_data['stripe_charge_id'])

            StripeManager.stripe_subscription_create_or_update(charge_data)
            logger.debug("update_subscription_and_payment_on_charge_success SUBSCRIPTION stripe_charge_id=" +
                         charge_data['stripe_charge_id'])

        except StripeSubscription.DoesNotExist as err:
            logger.error('%s', "update_subscription_and_payment_on_charge_success StripeSubscription.DoesNotExist: " +
                         str(err))

        except Exception as err:
            logger.error('%s', "update_subscription_and_payment_on_charge_success: " + str(err))

        return

    @staticmethod
    def add_to_row_if_in_dictionary (key, dict, row):
        if key in dict.keys() and dict[key] is not None:
            setattr(row, key, dict[key])

    @staticmethod
    def stripe_payment_create_or_update(charge_data):
        print('stripe_payment_create_or_update PAYMENTS >>>>>> ', charge_data)
        print('stripe_payment_create_or_update PAYMENTS >>>>>> VOTER TEST',  'voter_we_vote_id' in charge_data.keys() and charge_data['voter_we_vote_id'])

        # print('stripe_payment_create_or_update PAYMENTS >>>>>> amount: ', charge_data['amount'], ' stripe_charge_id:',  charge_data['stripe_charge_id'])
        with transaction.atomic():
            try:
                row = None
                try:
                    payment_queryset = StripePayments.objects.all().order_by('-created')
                    exact_match_subset = payment_queryset.filter(Q(amount=charge_data['amount']) & Q(stripe_charge_id=charge_data['stripe_charge_id']))
                    if len(exact_match_subset):
                        print('stripe_payment_create_or_update exact_match_subset (line 1806) length', len(exact_match_subset))
                        row = exact_match_subset[0]
                        try:
                            for arrow in exact_match_subset:
                                print('ARROWS row amount: ', arrow.amount, 'arrow.id', arrow.id, arrow.stripe_charge_id, 'arrow.created', arrow.created, 'arrow.billing_reason', arrow.billing_reason)
                        except Exception as err:
                            logger.error("ARROW err" + str(err))
                    else:
                        # charge_succeeded can precede payment_succeeded
                        # ** is the "unpacking syntax"
                        remove_keys_from_subs = [
                            'billing_interval', 'donation_plan_is_active', 'subscription_created_at',
                            'subscription_canceled_at', 'subscription_ended_at', 'last_charged',
                            'linked_organization_we_vote_id character', 'client_ip']
                        for key in remove_keys_from_subs:
                            if key in charge_data:
                                del charge_data[key]
                        if 'billing_reason' not in charge_data.keys():
                            charge_data['billing_reason'] = ''
                        print('StripePayments.objects.create PAYMENTS >>>>>> Create New Row, amount: ',
                              charge_data['amount'], 'billing_reason:', charge_data['billing_reason'],
                              'stripe_charge_id:', charge_data['stripe_charge_id'], 'created:', charge_data['created'])
                        return StripePayments.objects.create(**charge_data)

                except Exception as err:
                    logger.error('%s', "stripe_subscription_create_or_update(a) unpacking syntax: " + str(err))

                # Saves the data items that come in from webhooks
                for key in charge_data:
                    StripeManager.add_to_row_if_in_dictionary(key, charge_data, row)

                row.save()
                print('StripePayments.objects.create Adding to existing row amount: ', charge_data['amount'],
                      'billing_reason:', charge_data['billing_reason'], 'stripe_charge_id:',
                      charge_data['stripe_charge_id'], 'created:', charge_data['created'])

            except StripePayments.DoesNotExist as err:
                logger.error('%s', "stripe_payment_create_or_update StripePayments.DoesNotExist: " + str(err))

            except Exception as err:
                logger.error('%s', "stripe_payment_create_or_update: " + str(err))

            return

    @staticmethod
    def stripe_subscription_create_or_update(subs_data):
        if subs_data['billing_reason'] == 'donationWithStripe_Api':
            print('API received: donationWithStripe_Api')
        print('stripe_subscription_create_or_update SUBSCRIPTIONS <<<<<<', subs_data)
        row = None
        # Webhooks can arrive faster than we can complete this method, so need to lock the row, to guarantee the write
        with transaction.atomic():
            try:
                row = None
                subscription_queryset = StripeSubscription.objects.all().order_by('-id')
                exact_match_subset = subscription_queryset.filter(Q(stripe_charge_id=subs_data['stripe_charge_id']))
                exact_match_subset = exact_match_subset.exclude(Q(stripe_charge_id='needs-match'))
                if len(exact_match_subset) > 0:
                    row = exact_match_subset[0]
                else:
                    customer_and_amount_subset = subscription_queryset.filter(
                        Q(brand='needs-match') &
                        Q(stripe_charge_id=subs_data['stripe_charge_id']) &
                        Q(amount=subs_data['amount']))
                    if len(customer_and_amount_subset) > 0:
                        row = customer_and_amount_subset[0]
                    else:
                        needs_match_subset = subscription_queryset.filter(
                            Q(stripe_charge_id='needs-match') &
                            Q(amount=subs_data['amount']))
                            # &                      Q(voter_we_vote_id=subs_data['voter_we_vote_id']))
                        if len(needs_match_subset) > 0:
                            row = needs_match_subset[0]

                if row is None:
                    entry = None
                    try:
                        # charge_succeeded can precede payment_succeeded
                        # ** is the "unpacking syntax"
                        remove_keys_from_payment = [
                            'amount_refunded', 'address_zip', 'amount_refunded', 'country', 'created', 'failure_code',
                            'failure_message',
                            'is_paid', 'is_refunded', 'network_status', 'reason', 'seller_message', 'stripe_status',
                            'status', 'stripe_card_id', 'billing_reason']
                        for key in remove_keys_from_payment:
                            if key in subs_data:
                                del subs_data[key]
                        entry = StripeSubscription.objects.create(**subs_data)
                    except Exception as err:
                        logger.error('%s', "stripe_subscription_create_or_update unpacking syntax (b): " + str(err))
                    is_new = True
                    return is_new, entry
                else:
                    if subs_data['billing_reason'] == 'subscription_create':
                        row.stripe_subscription_id = subs_data['stripe_subscription_id']
                        row.stripe_request_id = subs_data['stripe_request_id']
                        row.subscription_created_at = subs_data['subscription_created_at']
                        row.stripe_charge_id = subs_data['stripe_charge_id']
                        row.last_charged = subs_data['last_charged']
                        row.api_version = subs_data['api_version']
                        row.save()
                        is_new = False
                        entry = row
                        return is_new, entry
                    elif subs_data['billing_reason'] == 'charge.succeeded':
                        row.stripe_charge_id = subs_data['stripe_charge_id']
                    row.brand = subs_data['brand']
                    row.exp_month = subs_data['exp_month']
                    row.exp_year = subs_data['exp_year']
                    row.last4 = subs_data['last4']
                    row.save()
                    logger.debug("stripe_subscription_create_or_update  row updated")

            except StripeSubscription.DoesNotExist as err:
                logger.error('%s', "stripe_subscription_create_or_update StripeSubscription.DoesNotExist: " + str(err))

            except Exception as err:
                logger.error('%s', "stripe_subscription_create_or_update: " + str(err))

            is_new = False
            entry = row
            return is_new, entry

    # @staticmethod
    # def add_payment_on_charge_success(payment):
    #     try:
    #         new_payment = StripeManager.stripe_payment_create_or_update(payment)
    #         # new_payment = StripePayments.objects.create(**payment)
    #         logger.debug("add_payment_on_charge_success amount=" + new_payment.amount)
    #     except Exception as err:
    #         logger.error('%s', "add_payment_on_charge_success: " + str(err))
    #
    #     return

    @staticmethod
    def find_we_vote_voter_id_for_stripe_customer(stripe_customer_id):

        try:
            queryset = StripePayments.objects.all().order_by('-id')
            rows = queryset.filter(stripe_customer_id=stripe_customer_id)
            for row in rows:
                if row.not_loggedin_voter_we_vote_id is None and \
                   row.record_enum == "SUBSCRIPTION_SETUP_AND_INITIAL" and \
                   row.voter_we_vote_id != "":
                    return row.voter_we_vote_id
            for row in rows:
                if row.not_loggedin_voter_we_vote_id is not None:
                    return row.not_loggedin_voter_we_vote_id

            return ""

        except StripePayments.DoesNotExist:
            logger.error('%s', "find_we_vote_voter_id_for_stripe_customer row does not exist")
        except Exception as e:
            logger.error('%s', "find_we_vote_voter_id_for_stripe_customer: " + str(e))

        return ""

    @staticmethod
    def update_journal_entry_for_refund(charge, voter_we_vote_id, refund):
        if refund and refund['amount'] > 0 and refund['status'] == "succeeded":
            row = StripePayments.objects.get(charge_id__iexact=charge, voter_we_vote_id__iexact=voter_we_vote_id)
            row.status = textwrap.shorten(row.status + " CHARGE_REFUND_REQUESTED" + "_" + str(refund['created']) +
                                          "_" + refund['currency'] + "_" + str(refund['amount']) + "_REFUND_ID" +
                                          refund['id'] + " ", width=255, placeholder="...")
            row.amount_refunded = refund['amount']
            row.stripe_status = "refund pending"
            row.save()
            logger.debug("update_journal_entry_for_refund for charge " + charge + ", with status: " + row.status)

            return "True"

        logger.error('%s', "update_journal_entry_for_refund bad charge or refund for charge_id " + charge +
                     " and voter_we_vote_id " + voter_we_vote_id)
        return "False"

    @staticmethod
    def update_journal_entry_for_already_refunded(charge, voter_we_vote_id):
        row = StripePayments.objects.get(charge_id__iexact=charge, voter_we_vote_id__iexact=voter_we_vote_id)
        row.status = textwrap.shorten(row.status + "CHARGE_WAS_ALREADY_REFUNDED_" + str(datetime.utcnow()) + " ",
                                      width=255, placeholder="...")
        row.amount_refunded = row.amount
        row.stripe_status = "refunded"
        row.save()
        logger.debug("update_journal_entry_for_refund_completed for charge " + charge + ", with status: " + row.status)

        return "True"

    @staticmethod
    def update_journal_entry_for_refund_completed(charge):
        logger.debug("update_journal_entry_for_refund_completed: " + charge)
        try:
            queryset = StripePayments.objects.all().order_by('-id')
            rows = queryset.filter(charge_id=charge)
            # There should only be one match, but super rarely, if the process gets interrupted, you can get multiples,
            #   We need to get the most recent one.
            if len(rows):
                row = rows[0]
                row.status = textwrap.shorten(row.status + "CHARGE_REFUNDED_" + str(datetime.utcnow()) + " ", width=255,
                                              placeholder="...")
                row.stripe_status = "refunded"
                row.save()
                logger.debug("update_journal_entry_for_refund_completed for charge " + charge + ", with status: " +
                             row.status)
                return "True"

        except StripePayments.DoesNotExist:
            logger.error('%s', "update_journal_entry_for_refund_completed row does not exist for charge " + charge)
        return "False"

    @staticmethod
    def move_subscription_entries_from_organization_to_organization(
            from_organization_we_vote_id, to_organization_we_vote_id):
        """

        :param from_organization_we_vote_id:
        :param to_organization_we_vote_id:
        :return:
        """
        status = ''
        subscription_definition_list = []

        try:
            subscription_definition_query = StripeSubscription.objects.all()
            subscription_definition_query = subscription_definition_query.filter(
                linked_organization_we_vote_id__iexact=from_organization_we_vote_id)
            subscription_definition_list = list(subscription_definition_query)
            status += "move_subscription_entries_from_organization_to_organization LIST_RETRIEVED-" + \
                      from_organization_we_vote_id + "-TO-" + to_organization_we_vote_id + \
                      " LENGTH: " + str(len(subscription_definition_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_subscription_entries_from_organization_to_organization "
            logger.error('%s', "move_subscription_entries_from_organization_to_organization 2:" + status)
            success = False

        subscription_definition_migration_count = 0
        subscription_definition_migration_fails = 0
        for subscription_definition in subscription_definition_list:
            try:
                subscription_definition.linked_organization_we_vote_id = to_organization_we_vote_id
                subscription_definition.save()
                subscription_definition_migration_count += 1
            except Exception as e:
                subscription_definition_migration_fails += 1

        if positive_value_exists(subscription_definition_migration_count):
            status += "DONATION_PLAN_DEFINITION_MOVED: " + str(subscription_definition_migration_count) + " "
        if positive_value_exists(subscription_definition_migration_fails):
            status += "DONATION_PLAN_DEFINITION_FAILS: " + str(subscription_definition_migration_fails) + " "

        results = {
            'status':                       status,
            'success':                      success,
            'from_organization_we_vote_id': from_organization_we_vote_id,
            'to_organization_we_vote_id':   to_organization_we_vote_id,
        }
        return results
