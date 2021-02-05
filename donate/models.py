# donate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models, IntegrityError
from datetime import datetime, timezone, timedelta
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from organization.models import CHOSEN_FAVICON_ALLOWED, CHOSEN_FULL_DOMAIN_ALLOWED, CHOSEN_GOOGLE_ANALYTICS_ALLOWED, \
    CHOSEN_SOCIAL_SHARE_IMAGE_ALLOWED, CHOSEN_SOCIAL_SHARE_DESCRIPTION_ALLOWED, CHOSEN_PROMOTED_ORGANIZATIONS_ALLOWED

import wevote_functions.admin
from voter.models import VoterManager
from wevote_functions.functions import positive_value_exists, convert_date_to_date_as_integer
import stripe
import textwrap
import time
import django.utils.timezone as tm


logger = wevote_functions.admin.get_logger(__name__)

SAME_DAY_MONTHLY = 'SAME_DAY_MONTHLY'
SAME_DAY_ANNUALLY = 'SAME_DAY_ANNUALLY'
BILLING_FREQUENCY_CHOICES = ((SAME_DAY_MONTHLY, 'SAME_DAY_MONTHLY'),
                             (SAME_DAY_ANNUALLY, 'SAME_DAY_ANNUALLY'))
CURRENCY_USD = 'usd'
CURRENCY_CAD = 'cad'
CURRENCY_CHOICES = ((CURRENCY_USD, 'usd'),
                    (CURRENCY_CAD, 'cad'))
FREE = 'FREE'
PROFESSIONAL_MONTHLY = 'PROFESSIONAL_MONTHLY'
PROFESSIONAL_YEARLY = 'PROFESSIONAL_YEARLY'
PROFESSIONAL_PAID_WITHOUT_STRIPE = 'PROFESSIONAL_PAID_WITHOUT_STRIPE'
ENTERPRISE_MONTHLY = 'ENTERPRISE_MONTHLY'
ENTERPRISE_YEARLY = 'ENTERPRISE_YEARLY'
ENTERPRISE_PAID_WITHOUT_STRIPE = 'ENTERPRISE_YEARLY'
ORGANIZATION_PLAN_OPTIONS = (
    (FREE, 'FREE'),
    (PROFESSIONAL_MONTHLY, 'PROFESSIONAL_MONTHLY'),
    (PROFESSIONAL_YEARLY, 'PROFESSIONAL_YEARLY'),
    (PROFESSIONAL_PAID_WITHOUT_STRIPE, 'PROFESSIONAL_PAID_WITHOUT_STRIPE'),
    (ENTERPRISE_MONTHLY, 'ENTERPRISE_MONTHLY'),
    (ENTERPRISE_YEARLY, 'ENTERPRISE_YEARLY'),
    (ENTERPRISE_PAID_WITHOUT_STRIPE, 'ENTERPRISE_PAID_WITHOUT_STRIPE'))

# Stripes currency support https://support.stripe.com/questions/which-currencies-does-stripe-support


class DonateLinkToVoter(models.Model):
    """
    This table links voter_we_vote_ids with Stripe customer IDs. A row is created when a stripe donation is made for the
    first time.
    """
    # The unique customer id from a stripe donation
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255,
                                          unique=True, null=False, blank=False)
    # There are scenarios where a voter_we_vote_id might have multiple customer_id's
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=False, null=False,
                                        blank=False)


class DonationPlanDefinition(models.Model):
    """
    This table tracks donation plans (recurring donations) and organization subscription plans (paid subscriptions)
    """
    donation_plan_id = models.CharField(verbose_name="unique recurring donation plan id", default="", max_length=255,
                                        null=False, blank=False)
    plan_name = models.CharField(verbose_name="donation plan name", max_length=255, null=False, blank=False)
    # Stripe uses integer pennies for amount (ex: 2000 = $20.00)
    base_cost = models.PositiveIntegerField(verbose_name="recurring donation amount", default=0, null=False)
    billing_interval = models.CharField(verbose_name="recurring donation frequency", max_length=255,
                                        choices=BILLING_FREQUENCY_CHOICES,
                                        null=True, blank=True)
    currency = models.CharField(verbose_name="currency", max_length=255, choices=CURRENCY_CHOICES, default=CURRENCY_USD,
                                null=False, blank=False)
    donation_plan_is_active = models.BooleanField(verbose_name="status of recurring donation plan", default=True,)
    is_organization_plan = models.BooleanField(
        verbose_name="is this a organization plan (and not a personal donation subscription)",
        default=False)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the person who created this subscription",
        max_length=255, default=None, null=True, blank=True, unique=False, db_index=True)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the organization who benefits from the organization subscription",
        max_length=255, default=None, null=True, blank=True, unique=False, db_index=True)
    plan_type_enum = models.CharField(verbose_name="enum of plan type {FREE, PROFESSIONAL_MONTHLY, ENTERPRISE, etc}",
                                      max_length=32, choices=ORGANIZATION_PLAN_OPTIONS, null=True, blank=True,
                                      default="")
    coupon_code = models.CharField(verbose_name="organization subscription coupon codes",
                                   max_length=255, null=False, blank=False, default="")
    organization_subscription_plan_id = models.PositiveIntegerField(
        verbose_name="the id of the OrganizationSubscriptionPlans used to create this plan, resulting from the use "
                     "of a coupon code, or a default coupon code", default=0, null=False)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=32,
                                          null=True, blank=False)
    stripe_subscription_id = models.CharField(
        verbose_name="unique subscription id for one voter, amount, and creation time",
        max_length=32, null=True, blank=True)
    paid_without_stripe = models.BooleanField(
        verbose_name="is this organization subscription plan paid via the We Vote accounting dept by check, etf, etc",
        default=False, blank=False)
    paid_without_stripe_expiration_date = models.DateTimeField(
        verbose_name="On this day, deactivate this plan, that is paid without stripe",
        auto_now=False, auto_now_add=False, null=True)
    paid_without_stripe_comment = models.CharField(verbose_name="accounting comment for accounts paid without stripe",
                                                   max_length=255, null=True, blank=True, default="")


class DonationJournal(models.Model):
    """
     This table tracks donation, subscription plans and refund activity
     """
    record_enum = models.CharField(
        verbose_name="enum of record type {PAYMENT_FROM_UI, PAYMENT_AUTO_SUBSCRIPTION, SUBSCRIPTION_SETUP_AND_INITIAL}",
        max_length=32, unique=False, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, unique=False, null=False,
                                        blank=False)
    not_loggedin_voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, unique=False,
                                                     null=True, blank=True)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=32,
                                          unique=False, null=False, blank=False)
    charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=32, default="",
                                 null=True, blank=True)
    subscription_id = models.CharField(verbose_name="unique subscription id for one voter, amount, and creation time",
                                       max_length=32, default="", null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name="donation amount", default=0, null=False)
    currency = models.CharField(verbose_name="donation currency country code", max_length=8, default="", null=True,
                                blank=True)
    funding = models.CharField(verbose_name="stripe returns 'credit' also might be debit, etc", max_length=32,
                               default="", null=True, blank=True)
    livemode = models.BooleanField(verbose_name="True: Live transaction, False: Test transaction", default=False,
                                   blank=False)
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
    reason = models.CharField(verbose_name="reason for failure reported by stripe", max_length=255, default="",
                              null=True, blank=True)
    seller_message = models.CharField(verbose_name="plain text message to us from stripe", max_length=255, default="",
                                      null=True, blank=True)
    stripe_type = models.CharField(verbose_name="authorization outcome message to us from stripe", max_length=64,
                                   default="", null=True, blank=True)
    paid = models.CharField(verbose_name="payment outcome message to us from stripe", max_length=64, default="",
                            null=True, blank=True)
    amount_refunded = models.PositiveIntegerField(verbose_name="refund amount", default=0, null=False)
    refund_count = models.PositiveIntegerField(
            verbose_name="Number of refunds, in the case of partials (currently not supported)", default=0, null=False)
    email = models.CharField(verbose_name="stripe returns the donor's email address as a name", max_length=255,
                             default="", null=True, blank=True)
    address_zip = models.CharField(verbose_name="stripe returns the donor's zip code", max_length=32, default="",
                                   null=True, blank=True)
    brand = models.CharField(verbose_name="the brand of the credit card, eg. Visa, Amex", max_length=32, default="",
                             null=True, blank=True)
    country = models.CharField(verbose_name="the country code of the bank that issued the credit card", max_length=8,
                               default="", null=True, blank=True)
    exp_month = models.PositiveIntegerField(verbose_name="the expiration month of the credit card", default=0,
                                            null=False)
    exp_year = models.PositiveIntegerField(verbose_name="the expiration year of the credit card", default=0, null=False)
    last4 = models.PositiveIntegerField(verbose_name="the last 4 digits of the credit card", default=0, null=False)
    id_card = models.CharField(verbose_name="stripe's internal id code for the credit card", max_length=32, default="",
                               null=True, blank=True)
    stripe_object = models.CharField(verbose_name="stripe returns 'card' for card, maybe different for bitcoin, etc.",
                                     max_length=32, default="", null=True, blank=True)
    stripe_status = models.CharField(verbose_name="status string reported by stripe", max_length=64, default="",
                                     null=True, blank=True)
    status = models.CharField(verbose_name="our generated status message", max_length=255, default="", null=True,
                              blank=True)
    subscription_plan_id = models.CharField(verbose_name="stripe subscription plan id", max_length=64, default="",
                                            unique=False, null=True, blank=True)
    subscription_created_at = models.DateTimeField(verbose_name="stripe subscription creation timestamp",
                                                   auto_now=False, auto_now_add=False, null=True)
    subscription_canceled_at = models.DateTimeField(verbose_name="stripe subscription canceled timestamp",
                                                    auto_now=False, auto_now_add=False, null=True)
    subscription_ended_at = models.DateTimeField(verbose_name="stripe subscription ended timestamp", auto_now=False,
                                                 auto_now_add=False, null=True)
    ip_address = models.GenericIPAddressField(verbose_name="user ip address", protocol='both', unpack_ipv4=False,
                                              null=True, blank=True, unique=False)
    last_charged = models.DateTimeField(verbose_name="stripe subscription most recent charge timestamp", auto_now=False,
                                        auto_now_add=False, null=True)
    is_organization_plan = models.BooleanField(
        verbose_name="is this a organization plan (and not a personal donation subscription)", default=False)
    plan_type_enum = models.CharField(verbose_name="enum of plan type {FREE, PROFESSIONAL_MONTHLY, ENTERPRISE, etc}",
                                      max_length=32, choices=ORGANIZATION_PLAN_OPTIONS, null=True, blank=True,
                                      default="")
    coupon_code = models.CharField(verbose_name="organization subscription coupon codes",
                                   max_length=255, null=False, blank=False, default="")
    organization_we_vote_id = models.CharField(verbose_name="unique organization we vote user id", max_length=32,
                                               unique=False, null=True, blank=True)


class OrganizationSubscriptionPlans(models.Model):
    """
    OrganizationSubscriptionPlans also known as "Coupon Codes" are pricing and feature sets, if the end user enters a
    coupon code on the signup form, they will get a specific pre-created OrganizationSubscriptionPlans that may have a
    lower than list price and potentially a different feature set.
    OrganizationSubscriptionPlans rows are immutable, the admin interface that creates them, never changes an existing
    row, only creates a new one -- if you want to add a new feature for all existing instance of DonationPlanDefinitions
    with the previous OrganizationSubscriptionPlans.id value, you will have to bulk update them to the new id value.
    Coupon Codes are collections of pricing, features, with an instance expiration date.
    The "25" in "25OFF" simply associates a coupon with a price, it could be numerical discount or a percentage
    A Coupon code is categorized by PlanType (professional, enterprise, etc.)
    OrganizationSubscriptionPlans.id can map to many DonationPlanDefinition.organization_coupon_code_id
    There will need to be a default-professional and default-enterprise OrganizationSubscriptionPlans that are created on
    the fly if one does not exist, these coupons would not display in the end user ui.  In the UI they display as blank
    coupon codes.
    """
    coupon_code = models.CharField(verbose_name="organization subscription coupon codes",
                                   max_length=255, null=False, blank=False)
    coupon_expires_date = models.DateTimeField(
        verbose_name="after this date, this coupon (display_plan_name) can not be used for new plans", auto_now=False,
        auto_now_add=False, null=True)
    plan_type_enum = models.CharField(verbose_name="enum of plan type {FREE, PROFESSIONAL, ENTERPRISE, etc}",
                                      max_length=32, choices=ORGANIZATION_PLAN_OPTIONS, null=True, blank=True)
    plan_created_at = models.DateTimeField(verbose_name="plan creation timestamp, mostly for debugging",
                                           default=tm.now)
    hidden_plan_comment = models.CharField(verbose_name="organization subscription hidden comment",
                                           max_length=255, null=False, blank=False, default="")
    coupon_applied_message = models.CharField(verbose_name="message to display on screen when coupon is applied",
                                              max_length=255, null=False, blank=False)
    monthly_price_stripe = models.PositiveIntegerField(
        verbose_name="The monthly price of this monthly plan, the amount we charge with stripe", default=0, null=False)
    annual_price_stripe = models.PositiveIntegerField(
        verbose_name="The annual price of this annual plan, the amount we charge with stripe", default=0, null=False)
    # 2019-08-26 To discuss: Deprecate features_provided_bitmap in this table in favor of looking up the features
    # that this plan provides in MasterFeaturePackage per the constant stored here in master_feature_package.
    features_provided_bitmap = models.BigIntegerField(verbose_name="organization features provided bitmap", null=False,
                                                      default=0)
    master_feature_package = models.CharField(
        verbose_name="plan type {PROFESSIONAL, ENTERPRISE} that has the features_provided_bitmap definition",
        max_length=255, null=True, blank=True)
    redemptions = models.PositiveIntegerField(verbose_name="the number of times this plan has been redeemed", default=0,
                                              null=False)
    is_archived = models.BooleanField(verbose_name="stop offering this plan for new clients", default=False,)


class MasterFeaturePackage(models.Model):
    """
    The master definition of which features are provide with each plan type. For example, changing the features provided
    for "PROFESSIONAL" affects everyone with that plan. If we want to give new clients a different set of features,
    (or Beta features) can be set up on a new plan. We did not set up master_feature_package as an enum so we can add
    new feature bundles under new subscription_plan_type like PROFESSIONAL_2019_AUG
    """
    master_feature_package = models.CharField(
        verbose_name="plan type {FREE, PROFESSIONAL, ENTERPRISE} that is referred to in OrganizationSubscriptionPlans",
        max_length=255, null=True, blank=True)
    features_provided_bitmap = models.BigIntegerField(
        verbose_name="organization features provided bitmap", null=False, default=0)


class DonationInvoice(models.Model):
    """
    This is a generated table that caches donation invoices, since they contain both the invoice id and subscription id
    that is necessary to associate the charge succeeded stripe event with a subscription
    """
    subscription_id = models.CharField(verbose_name="unique stripe subscription id",
                                       max_length=64, default="", null=True, blank=True)
    donation_plan_id = models.CharField(
        verbose_name="plan id for one voter and an amount, can have duplicates "
        "if voter has multiple subscriptions for the same amount", default="", max_length=255, null=False, blank=False)
    invoice_id = models.CharField(verbose_name="unique stripe invoice id for one payment",
                                  max_length=64, default="", null=True, blank=True)
    invoice_date = models.DateTimeField(verbose_name="creation date for this stripe invoice", auto_now=False,
                                        auto_now_add=False, null=True)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=32,
                                          unique=False, null=False, blank=False)


class DonationManager(models.Manager):

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
                new_customer_id_created = DonateLinkToVoter.objects.create(
                    stripe_customer_id=stripe_customer_id, voter_we_vote_id=voter_we_vote_id)
                success = True
                status = 'STRIPE_CUSTOMER_ID_SAVED '
            except:
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
                stripe_customer_id_queryset = DonateLinkToVoter.objects.filter(
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
    def retrieve_or_create_recurring_donation_plan(voter_we_vote_id, we_vote_donation_plan_identifier, donation_amount,
                                                   is_organization_plan, coupon_code, plan_type_enum,
                                                   organization_we_vote_id, recurring_interval):
        """
        June 2017, we create these records, but never read them for donations
        August 2019, we read them for organization paid subscriptions
        :param voter_we_vote_id:
        :param we_vote_donation_plan_identifier:
        :param donation_amount:
        :param is_organization_plan:
        :param coupon_code:
        :param plan_type_enum:
        :param organization_we_vote_id:
        :param recurring_interval:
        :return:
        """
        # recurring_donation_plan_id = voter_we_vote_id + "-monthly-" + str(donation_amount)
        # plan_name = donation_plan_id + " Plan"
        billing_interval = "monthly"  # This would be a good place to start for annual payment paid subscriptions
        currency = "usd"
        donation_plan_is_active = True
        exception_multiple_object_returned = False
        status = ''
        stripe_plan_id = ''
        success = False
        org_subs_id = 0
        org_subs_already_exists = False

        try:
            # the donation plan needs to exist in two places: our stripe account and our database
            # plans can be created here or in our stripe account dashboard
            donation_plan_query, is_new = DonationPlanDefinition.objects.get_or_create(
                donation_plan_id=we_vote_donation_plan_identifier,
                plan_name=we_vote_donation_plan_identifier,
                base_cost=donation_amount,
                billing_interval=billing_interval,
                currency=currency,
                coupon_code=coupon_code,
                plan_type_enum=plan_type_enum,
                donation_plan_is_active=donation_plan_is_active,
                is_organization_plan=is_organization_plan,
                voter_we_vote_id=voter_we_vote_id,
                organization_we_vote_id=organization_we_vote_id,
                organization_subscription_plan_id=org_subs_id
            )
            if is_new:
                # if a donation plan is not found, we've added it to our database
                success = True
                status += 'SUBSCRIPTION_PLAN_CREATED_IN_DATABASE '
            else:
                # if it is found, do nothing - no need to update
                success = True
                status += 'DONATION_PLAN_ALREADY_EXISTS_IN_DATABASE '

            plan_id_query = stripe.Plan.retrieve(we_vote_donation_plan_identifier)
            if positive_value_exists(plan_id_query.id):
                stripe_plan_id = plan_id_query.id
                logger.debug("Stripe, plan_id_query.id " + plan_id_query.id)
        except DonationManager.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            success = False
            status += 'MULTIPLE_MATCHING_SUBSCRIPTION_PLANS_FOUND '
            exception_multiple_object_returned = True

        except stripe.error.StripeError:
            pass

        except Exception as e:
            handle_exception(e, logger=logger)

        if recurring_interval in ('month', 'year') and not positive_value_exists(stripe_plan_id) \
                and not org_subs_already_exists:
            # if plan doesn't exist in stripe, we need to create it (note it's already been created in database)
            plan = stripe.Plan.create(
                amount=donation_amount,
                interval=recurring_interval,
                currency="usd",
                nickname=we_vote_donation_plan_identifier,
                id=we_vote_donation_plan_identifier,
                product={
                    "name": we_vote_donation_plan_identifier,
                    "type": "service"
                },
            )
            if plan.id:
                success = True
                status += 'SUBSCRIPTION_PLAN_CREATED_IN_STRIPE '
            else:
                success = False
                status += 'SUBSCRIPTION_PLAN_NOT_CREATED_IN_STRIPE '
        else:
            status += 'STRIPE_PLAN_NOT_CREATED-REQUIREMENTS_NOT_SATISFIED '
        results = {
            'success': success,
            'status': status,
            'org_subs_already_exists': org_subs_already_exists,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'recurring_donation_plan_id': we_vote_donation_plan_identifier,
        }
        return results

    @staticmethod
    def retrieve_or_create_subscription_plan_definition(
            voter_we_vote_id,
            organization_we_vote_id,
            stripe_customer_id,
            we_vote_donation_plan_identifier,
            subscription_cost_pennies,
            coupon_code,
            plan_type_enum,
            recurring_interval):
        """
        August 2019, we read these records for organization paid subscriptions
        :param voter_we_vote_id:
        :param organization_we_vote_id:
        :param stripe_customer_id:
        :param we_vote_donation_plan_identifier:
        :param subscription_cost_pennies:
        :param coupon_code:
        :param plan_type_enum:
        :param recurring_interval:
        :return:
        """
        # recurring_interval is based on the Stripe constants: month and year
        # billing_interval is based on BILLING_FREQUENCY_CHOICES: SAME_DAY_MONTHLY, SAME_DAY_ANNUALLY
        if recurring_interval == 'month':
            billing_interval = SAME_DAY_MONTHLY
        elif recurring_interval == 'year':
            billing_interval = SAME_DAY_ANNUALLY
        else:
            billing_interval = SAME_DAY_MONTHLY
        currency = "usd"
        exception_multiple_object_returned = False
        is_new = False
        is_organization_plan = True
        status = ''
        stripe_plan_id = ''
        success = False
        org_subs_id = 0
        donation_plan_definition = None
        donation_plan_definition_already_exists = False

        donation_plan_definition_id = 0
        try:
            # the donation plan needs to exist in two places: our stripe account and our database
            # plans can be created here or in our stripe account dashboard
            defaults_for_create = {
                'coupon_code': coupon_code,
                'currency': currency,
                'donation_plan_id': we_vote_donation_plan_identifier,
                'organization_subscription_plan_id': org_subs_id,
                'plan_name': we_vote_donation_plan_identifier,
                'stripe_customer_id': stripe_customer_id,
                'voter_we_vote_id': voter_we_vote_id,
            }
            donation_plan_definition, is_new = DonationPlanDefinition.objects.get_or_create(
                base_cost=subscription_cost_pennies,
                billing_interval=billing_interval,
                donation_plan_is_active=True,
                plan_type_enum=plan_type_enum,
                is_organization_plan=is_organization_plan,
                organization_we_vote_id=organization_we_vote_id,
                defaults=defaults_for_create,
            )

            if is_new:
                # if a donation plan is not found, we've added it to our database
                success = True
                status += 'SUBSCRIPTION_PLAN_DEFINITION_CREATED_IN_DATABASE '
            else:
                # if it is found, do nothing - no need to update
                success = True
                status += 'SUBSCRIPTION_PLAN_DEFINITION_ALREADY_EXISTS_IN_DATABASE '
                donation_plan_definition_already_exists = True

            we_vote_donation_plan_identifier = donation_plan_definition.donation_plan_id
            donation_plan_definition_id = donation_plan_definition.id
        except DonationPlanDefinition.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            success = False
            status += 'MULTIPLE_MATCHING_SUBSCRIPTION_PLANS_FOUND '
            exception_multiple_object_returned = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status += 'DONATION_PLAN_DEFINITION_GET_OR_CREATE-EXCEPTION: ' + str(e) + ' '

        try:
            stripe_plan = stripe.Plan.retrieve(we_vote_donation_plan_identifier)
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
                    nickname=we_vote_donation_plan_identifier,
                    id=we_vote_donation_plan_identifier,
                    product={
                        "name": we_vote_donation_plan_identifier,
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
            'recurring_donation_plan_id': we_vote_donation_plan_identifier,
        }
        return results

    @staticmethod
    def create_donation_journal_entry(
            record_enum, ip_address, stripe_customer_id,
            voter_we_vote_id, charge_id, amount, currency, funding,
            livemode, action_taken, action_result, created,
            failure_code, failure_message, network_status, reason, seller_message,
            stripe_type, paid, amount_refunded, refund_count,
            email, address_zip, brand, country,
            exp_month, exp_year, last4, id_card, stripe_object,
            stripe_status, status,
            subscription_id, subscription_plan_id, subscription_created_at, subscription_canceled_at,
            subscription_ended_at, not_loggedin_voter_we_vote_id,
            is_organization_plan, coupon_code, plan_type_enum, organization_we_vote_id):
        """
        This function receives a long list of parameters, the line breaks in the parameters may look messy,
        but are purposeful
        """
        status = ''
        new_history_entry = 0
        try:
            # This is a long list of parameters, the line breaks in the parameters may look messy, but are purposeful
            new_history_entry = DonationJournal.objects.create(
                record_enum=record_enum, ip_address=ip_address, stripe_customer_id=stripe_customer_id,
                voter_we_vote_id=voter_we_vote_id, charge_id=charge_id, amount=amount, currency=currency,
                funding=funding,
                livemode=livemode, action_taken=action_taken, action_result=action_result, created=created,
                failure_code=failure_code, failure_message=failure_message, network_status=network_status,
                reason=reason, seller_message=seller_message,
                stripe_type=stripe_type, paid=paid, amount_refunded=amount_refunded, refund_count=refund_count,
                email=email, address_zip=address_zip, brand=brand, country=country,
                exp_month=exp_month, exp_year=exp_year, last4=last4, id_card=id_card, stripe_object=stripe_object,
                stripe_status=stripe_status, status=status,
                subscription_id=subscription_id, subscription_plan_id=subscription_plan_id,
                subscription_created_at=subscription_created_at, subscription_canceled_at=subscription_canceled_at,
                subscription_ended_at=subscription_ended_at,
                not_loggedin_voter_we_vote_id=not_loggedin_voter_we_vote_id,
                is_organization_plan=is_organization_plan, coupon_code=coupon_code, plan_type_enum=plan_type_enum,
                organization_we_vote_id=organization_we_vote_id)

            success = True
            status = 'NEW_DONATION_JOURNAL_ENTRY_SAVED '
        except Exception as e:
            success = False
            status += 'UNABLE_TO_SAVE_DONATION_JOURNAL_ENTRY, EXCEPTION: ' + str(e) + ' '

        saved_results = {
            'success': success,
            'status': status,
            'donation_journal_created': new_history_entry
        }
        return saved_results

    def create_recurring_donation(self, stripe_customer_id, voter_we_vote_id, donation_amount, start_date_time, email,
                                  is_organization_plan, coupon_code, plan_type_enum, organization_we_vote_id):
        """

        :param stripe_customer_id:
        :param voter_we_vote_id:
        :param donation_amount:
        :param start_date_time:
        :param email:
        :param is_organization_plan:
        :param coupon_code:
        :param plan_type_enum:
        :param organization_we_vote_id:
        :return:
        """
        plan_error = False
        status = ""
        success = False
        stripe_subscription_created = False
        org_subs_already_exists = False
        org_segment = "organization-" if is_organization_plan else ""
        periodicity ="-monthly-"
        if "_YEARLY" in plan_type_enum:
            periodicity = "-yearly-"
        we_vote_donation_plan_identifier = voter_we_vote_id + periodicity + org_segment + str(donation_amount)

        donation_plan_results = self.retrieve_or_create_recurring_donation_plan(
            voter_we_vote_id, we_vote_donation_plan_identifier, donation_amount, is_organization_plan, coupon_code, plan_type_enum,
            organization_we_vote_id, 'month')
        org_subs_already_exists = donation_plan_results['org_subs_already_exists']
        success = donation_plan_results['success']
        status += donation_plan_results['status']
        if not org_subs_already_exists and success:
            try:
                # If not logged in, this voter_we_vote_id will not be the same as the logged in id.
                # Passing the voter_we_vote_id to the subscription gives us a chance to associate logged in with not
                # logged in subscriptions in the future
                subscription = stripe.Subscription.create(
                    customer=stripe_customer_id,
                    plan=we_vote_donation_plan_identifier,
                    metadata={'voter_we_vote_id': voter_we_vote_id, 'email': email}
                )
                success = True
                subscription_id = subscription['id']
                status += "USER_SUCCESSFULLY_SUBSCRIBED_TO_PLAN "
                stripe_subscription_created = True

                results = {
                    'success': success,
                    'status': status,
                    'voter_subscription_saved': status,
                    'stripe_subscription_created': stripe_subscription_created,
                    'subscription_plan_id': we_vote_donation_plan_identifier,
                    'subscription_created_at': subscription['created'],
                    'subscription_id': subscription_id,
                    'org_subs_already_exists': False,
                }

            except stripe.error.StripeError as e:
                success = False
                body = e.json_body
                err = body['error']
                status += "STRIPE_ERROR_IS_" + err['message'] + "_END"
                logger.error("create_recurring_donation StripeError: " + status)

                results = {
                    'success': False,
                    'status': status,
                    'voter_subscription_saved': False,
                    'org_subs_already_exists': False,
                    'stripe_subscription_created': stripe_subscription_created,
                    'subscription_plan_id': "",
                    'subscription_created_at': "",
                    'subscription_id': ""
                }
        else:
            results = {
                'success': success,
                'status': status,
                'voter_subscription_saved': False,
                'org_subs_already_exists': org_subs_already_exists,
                'stripe_subscription_created': stripe_subscription_created,
                'subscription_plan_id': "",
                'subscription_created_at': "",
                'subscription_id': ""
            }

        return results

    def create_organization_subscription(
            self, stripe_customer_id, voter_we_vote_id, donation_amount, start_date_time, email,
            coupon_code, plan_type_enum, organization_we_vote_id, recurring_interval):
        """

        :param stripe_customer_id:
        :param voter_we_vote_id:
        :param donation_amount:
        :param start_date_time:
        :param email:
        :param coupon_code:
        :param plan_type_enum:
        :param organization_we_vote_id:
        :param recurring_interval:
        :return:
        """
        status = ""
        success = False
        stripe_subscription_created = False
        subscription_created_at = ''
        stripe_subscription_id = ''

        org_segment = "organization-"
        periodicity ="-monthly-"
        if "_YEARLY" in plan_type_enum:
            periodicity = "-yearly-"
        we_vote_donation_plan_identifier = voter_we_vote_id + periodicity + org_segment + str(donation_amount)

        # We have already previously retrieved the coupon_price, and updated the donation_amount.
        # Here, we are incrementing the redemption counter
        increment_redemption_count = True
        coupon_price, org_subs_id = DonationManager.get_coupon_price(plan_type_enum, coupon_code,
                                                                     increment_redemption_count)

        plan_results = self.retrieve_or_create_subscription_plan_definition(
            voter_we_vote_id, organization_we_vote_id, stripe_customer_id,
            we_vote_donation_plan_identifier, donation_amount, coupon_code, plan_type_enum,
            recurring_interval)
        donation_plan_definition_already_exists = plan_results['donation_plan_definition_already_exists']
        status = plan_results['status']
        donation_plan_definition_id = plan_results['donation_plan_definition_id']
        if plan_results['success']:
            donation_plan_definition = plan_results['donation_plan_definition']
            try:
                # If not logged in, this voter_we_vote_id will not be the same as the logged in id.
                # Passing the voter_we_vote_id to the subscription gives us a chance to associate logged in with not
                # logged in subscriptions in the future
                subscription = stripe.Subscription.create(
                    customer=stripe_customer_id,
                    plan=we_vote_donation_plan_identifier,
                    metadata={
                        'organization_we_vote_id': organization_we_vote_id,
                        'voter_we_vote_id': voter_we_vote_id,
                        'email': email
                    }
                )
                stripe_subscription_created = True
                success = True
                stripe_subscription_id = subscription['id']
                subscription_created_at = subscription['created']
                status += "USER_SUCCESSFULLY_SUBSCRIBED_TO_PLAN "
            except stripe.error.StripeError as e:
                success = False
                body = e.json_body
                err = body['error']
                status = "STRIPE_ERROR_IS_" + err['message'] + "_END"
                logger.error("create_recurring_donation StripeError: " + status)

            if positive_value_exists(stripe_subscription_id):
                try:
                    donation_plan_definition.stripe_subscription_id = stripe_subscription_id
                    donation_plan_definition.save()
                    status += "STRIPE_SUBSCRIPTION_ID_SAVED_IN_DONATION_PLAN_DEFINITION "
                except Exception as e:
                    status += "FAILED_TO_SAVE_STRIPE_SUBSCRIPTION_ID_IN_DONATION_PLAN_DEFINITION "
        results = {
            'success': success,
            'status': status,
            'stripe_subscription_created': stripe_subscription_created,
            'subscription_plan_id': we_vote_donation_plan_identifier,
            'subscription_created_at': subscription_created_at,
            'stripe_subscription_id': stripe_subscription_id,
            'donation_plan_definition_already_exists': donation_plan_definition_already_exists,
        }
        return results

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
            donation_queryset = DonationJournal.objects.all().order_by('-created')
            donation_queryset = donation_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            donation_journal_list = list(donation_queryset)

            if len(donation_journal_list):
                success = True
                status += ' CACHED_WE_VOTE_DONATION_JOURNAL_HISTORY_LIST_RETRIEVED '
            else:
                donation_journal_list = []
                success = True
                status += ' NO_DONATION_JOURNAL_HISTORY_EXISTS_FOR_THIS_VOTER '

        except DonationJournal.DoesNotExist:
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
    def retrieve_donation_plan_definition(voter_we_vote_id='', organization_we_vote_id='', is_organization_plan=True,
                                          plan_type_enum='', donation_plan_is_active=True):
        donation_plan_definition = None
        donation_plan_definition_found = False
        status = ''

        try:
            donation_queryset = DonationPlanDefinition.objects.all().order_by('-id')
            if positive_value_exists(voter_we_vote_id):
                donation_queryset = donation_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            elif positive_value_exists(organization_we_vote_id):
                donation_queryset = donation_queryset.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            donation_queryset = donation_queryset.filter(is_organization_plan=is_organization_plan)
            if positive_value_exists(plan_type_enum):
                donation_queryset = donation_queryset.filter(plan_type_enum__iexact=plan_type_enum)
            if positive_value_exists(donation_plan_is_active):
                donation_queryset = donation_queryset.filter(donation_plan_is_active=donation_plan_is_active)
            donation_plan_definition_list = list(donation_queryset)

            if len(donation_plan_definition_list):
                donation_plan_definition = donation_plan_definition_list[0]
                donation_plan_definition_found = True
                status += 'DONATION_PLAN_DEFINITION_RETRIEVED '
                success = True
            else:
                donation_plan_definition_list = []
                status += 'DONATION_PLAN_DEFINITION_LIST_EMPTY '
                success = True

        except DonationPlanDefinition.DoesNotExist:
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
    def retrieve_donation_plan_definition_list(voter_we_vote_id='', organization_we_vote_id='',
                                               return_json_version=False):
        donation_plan_definition_list = []
        donation_plan_definition_list_json = []
        status = ''

        try:
            donation_queryset = DonationPlanDefinition.objects.all().order_by('-id')
            if positive_value_exists(voter_we_vote_id):
                donation_queryset = donation_queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            if positive_value_exists(organization_we_vote_id):
                donation_queryset = donation_queryset.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            donation_plan_definition_list = list(donation_queryset)

            if len(donation_plan_definition_list):
                status += 'DONATION_PLAN_DEFINITION_LIST_RETRIEVED '
                success = True
            else:
                donation_plan_definition_list = []
                status += 'DONATION_PLAN_DEFINITION_LIST_EMPTY '
                success = True

        except DonationPlanDefinition.DoesNotExist:
            status += "DONATION_PLAN_DEFINITION_LIST_EMPTY2 "
            success = True

        except Exception as e:
            status += "DONATION_PLAN_DEFINITION_LIST-FAILED_TO_RETRIEVE " + str(e) + " "
            success = False
            # handle_exception(e, logger=logger, exception_message=status)

        if positive_value_exists(return_json_version):
            for donation_plan_definition in donation_plan_definition_list:
                json = {
                    'base_cost':    donation_plan_definition.base_cost,
                    'billing_interval': donation_plan_definition.billing_interval,
                    'coupon_code': donation_plan_definition.coupon_code,
                    'currency': donation_plan_definition.currency,
                    'donation_plan_id': donation_plan_definition.donation_plan_id,
                    'donation_plan_is_active': donation_plan_definition.donation_plan_is_active,
                    'is_organization_plan': donation_plan_definition.is_organization_plan,
                    'organization_subscription_plan_id': donation_plan_definition.organization_subscription_plan_id,
                    'organization_we_vote_id': donation_plan_definition.organization_we_vote_id,
                    'paid_without_stripe': donation_plan_definition.paid_without_stripe,
                    'paid_without_stripe_comment': donation_plan_definition.paid_without_stripe_comment,
                    'paid_without_stripe_expiration_date': donation_plan_definition.paid_without_stripe_expiration_date,
                    'plan_name': donation_plan_definition.plan_name,
                    'plan_type_enum': donation_plan_definition.plan_type_enum,
                    'voter_we_vote_id': donation_plan_definition.voter_we_vote_id,
                }
                donation_plan_definition_list_json.append(json)

        results = {
            'success':                          success,
            'status':                           status,
            'donation_plan_definition_list':    donation_plan_definition_list,
            'donation_plan_definition_list_json': donation_plan_definition_list_json,
        }

        return results

    @staticmethod
    def retrieve_master_feature_package(chosen_feature_package):
        status = ''
        master_feature_package = None
        master_feature_package_found = False

        try:
            master_feature_package = MasterFeaturePackage.objects.get(
                master_feature_package__iexact=chosen_feature_package)
            master_feature_package_found = True
            success = True
        except MasterFeaturePackage.DoesNotExist:
            status += "MASTER_FEATURE_PACKAGE_NOT_FOUND "
            success = True
        except Exception as e:
            status += "MASTER_FEATURE_PACKAGE_EXCEPTION: " + str(e) + " "
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'master_feature_package':       master_feature_package,
            'master_feature_package_found': master_feature_package_found,
        }

        return results

    @staticmethod
    def does_donation_journal_charge_exist(charge_id):
        """

        :param charge_id:
        :return:
        """
        try:
            donation_queryset = DonationJournal.objects.all()
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
    def does_paid_subscription_exist(organization_we_vote_id):
        found_live_paid_subscription_for_the_org = False
        try:
            donation_queryset = DonationJournal.objects.all()
            donation_queryset = donation_queryset.filter(record_enum='SUBSCRIPTION_SETUP_AND_INITIAL',
                                                         is_organization_plan=True)

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

    @staticmethod
    def retrieve_subscription_plan_list():
        """
        Retrieve coupons
        :return:
        """
        subscription_plan_list = []
        status = ''

        DonationManager.create_initial_coupons()
        DonationManager.create_initial_master_feature_packages()
        try:
            plan_queryset = OrganizationSubscriptionPlans.objects.order_by('-plan_created_at')
            subscription_plan_list = plan_queryset

            if len(plan_queryset):
                success = True
                status += ' ORGANIZATIONAL_SUBSCRIPTION_PLANS_LIST_RETRIEVED '
            else:
                subscription_plan_list = []
                success = False
                status += " NO_ORGANIZATIONAL_SUBSCRIPTION_PLAN_EXISTS "

        except Exception as e:
            status += " FAILED_TO_RETRIEVE_ORGANIZATIONAL_SUBSCRIPTION_PLANS_LIST "
            success = False
            handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success': success,
            'status': status,
            'subscription_plan_list': subscription_plan_list
        }

        return results

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
            subscription_row = DonationJournal.objects.get(subscription_id=stripe_subscription_id,
                                                           stripe_customer_id=customer_id,
                                                           record_enum='SUBSCRIPTION_SETUP_AND_INITIAL')
            subscription_row.subscription_ended_at = datetime.fromtimestamp(subscription_ended_at, timezone.utc)
            subscription_row.subscription_canceled_at = datetime.fromtimestamp(subscription_canceled_at, timezone.utc)
            subscription_row.save()
            status += "DONATION_JOURNAL_SAVED-MARKED_CANCELED "
            success = True
        except DonationJournal.DoesNotExist:
            status += "mark_donation_journal_canceled_or_ended: " + \
                      "Subscription " + stripe_subscription_id + " with customer_id " + \
                      customer_id + " does not exist"
            logger.error(status)
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
    def mark_donation_plan_definition_canceled(donation_plan_definition_id=0, stripe_subscription_id=''):
        status = ''
        success = False
        donation_plan_definition = None
        donation_plan_definition_found = False
        try:
            if positive_value_exists(donation_plan_definition_id):
                donation_plan_definition = DonationPlanDefinition.objects.get(id=donation_plan_definition_id)
                donation_plan_definition_found = True
            elif positive_value_exists(stripe_subscription_id):
                donation_plan_definition = DonationPlanDefinition.objects.get(
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
            handle_exception(e, logger=logger, exception_message="Exception in mark_donation_plan_definition_canceled")
            status += "MARK_DONATION_PLAN_DEFINITION-FAILED: " + str(e) + " "
        return {
            'status':   status,
            'success':  success,
        }

    @staticmethod
    def mark_latest_donation_plan_definition_canceled(voter_we_vote_id):
        # There can only be one active organization paid plan at one time, so mark the first active one as inactive
        try:
            voter_manager = VoterManager()
            org_we_vote_id = voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(voter_we_vote_id)

            rows = DonationPlanDefinition.objects.get(organization_we_vote_id__iexact=org_we_vote_id,
                                                      is_organization_plan=True,
                                                      donation_plan_is_active=True)
            if len(rows):
                row = rows[0]
                row.donation_plan_is_active = False
                print('DonationPlanDefinition for ' + org_we_vote_id + ' is now marked as inactive')
                row.save()
            else:
                print('DonationPlanDefinition for ' + org_we_vote_id + ' not found')
                logger.error('DonationPlanDefinition for ' + org_we_vote_id +
                             ' not found in mark_latest_donation_plan_definition_canceled')

            # TODO: STEVE STEVE STEVE seperately make sure that we only find the active ones
        except Exception as e:
            logger.error('DonationPlanDefinition for ' + org_we_vote_id +
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
            donate_link_query = DonateLinkToVoter.objects.all()
            donate_link_query = donate_link_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            donate_link_list = list(donate_link_query)
            status += "move_donate_link_to_voter_from_voter_to_voter LIST_RETRIEVED-" + \
                      voter_we_vote_id + "-TO-" + to_voter_we_vote_id + " LENGTH: " + str(len(donate_link_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donate_link_to_voter_from_voter_to_voter "
            logger.error("move_donate_link_to_voter_from_voter_to_voter 2:" + status)
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
    def move_donation_journal_entries_from_voter_to_voter(from_voter, to_voter):
        """

        :param from_voter:
        :param to_voter:
        :return:
        """
        status = ''
        donation_journal_list = []
        voter_we_vote_id = from_voter.we_vote_id
        to_voter_we_vote_id = to_voter.we_vote_id

        try:
            donation_journal_query = DonationJournal.objects.all()
            donation_journal_query = donation_journal_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            donation_journal_list = list(donation_journal_query)
            status += "move_donation_journal_entries_from_voter_to_voter LIST_RETRIEVED-" + \
                      voter_we_vote_id + "-TO-" + to_voter_we_vote_id + \
                      " LENGTH: " + str(len(donation_journal_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donation_journal_entries_from_voter_to_voter "
            logger.error("move_donation_journal_entries_from_voter_to_voter 2:" + status)
            success = False

        donation_journal_migration_count = 0
        donation_journal_migration_fails = 0
        for donation_journal in donation_journal_list:
            try:
                donation_journal.voter_we_vote_id = to_voter_we_vote_id
                donation_journal.save()
                donation_journal_migration_count += 1
            except Exception as e:
                donation_journal_migration_fails += 1

        if positive_value_exists(donation_journal_migration_count):
            status += "DONATION_JOURNAL_MOVED: " + str(donation_journal_migration_count) + " "
        if positive_value_exists(donation_journal_migration_fails):
            status += "DONATION_JOURNAL_FAILS: " + str(donation_journal_migration_fails) + " "

        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    @staticmethod
    def move_donation_plan_definition_entries_from_voter_to_voter(from_voter, to_voter):
        """

        :param from_voter:
        :param to_voter:
        :return:
        """
        status = ''
        donation_plan_definition_list = []
        voter_we_vote_id = from_voter.we_vote_id
        to_voter_we_vote_id = to_voter.we_vote_id

        try:
            donation_plan_definition_query = DonationPlanDefinition.objects.all()
            donation_plan_definition_query = donation_plan_definition_query.filter(
                voter_we_vote_id__iexact=voter_we_vote_id)
            donation_plan_definition_list = list(donation_plan_definition_query)
            status += "move_donation_plan_definition_entries_from_voter_to_voter LIST_RETRIEVED-" + \
                      voter_we_vote_id + "-TO-" + to_voter_we_vote_id + \
                      " LENGTH: " + str(len(donation_plan_definition_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donation_plan_definition_entries_from_voter_to_voter "
            logger.error("move_donation_plan_definition_entries_from_voter_to_voter 2:" + status)
            success = False

        donation_plan_definition_migration_count = 0
        donation_plan_definition_migration_fails = 0
        for donation_plan_definition in donation_plan_definition_list:
            try:
                donation_plan_definition.voter_we_vote_id = to_voter_we_vote_id
                donation_plan_definition.save()
                donation_plan_definition_migration_count += 1
            except Exception as e:
                donation_plan_definition_migration_fails += 1

        if positive_value_exists(donation_plan_definition_migration_count):
            status += "DONATION_PLAN_DEFINITION_MOVED: " + str(donation_plan_definition_migration_count) + " "
        if positive_value_exists(donation_plan_definition_migration_fails):
            status += "DONATION_PLAN_DEFINITION_FAILS: " + str(donation_plan_definition_migration_fails) + " "

        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    @staticmethod
    def move_donation_journal_entries_from_organization_to_organization(
            from_organization_we_vote_id, to_organization_we_vote_id):
        """

        :param from_organization_we_vote_id:
        :param to_organization_we_vote_id:
        :return:
        """
        status = ''
        donation_journal_list = []

        try:
            donation_journal_query = DonationJournal.objects.all()
            donation_journal_query = donation_journal_query.filter(
                organization_we_vote_id__iexact=from_organization_we_vote_id)
            donation_journal_list = list(donation_journal_query)
            status += "move_donation_journal_entries_from_organization_to_organization LIST_RETRIEVED-" + \
                      from_organization_we_vote_id + "-TO-" + to_organization_we_vote_id +  \
                      " LENGTH: " + str(len(donation_journal_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donation_journal_entries_from_organization_to_organization "
            logger.error("move_donation_journal_entries_from_organization_to_organization 2:" + status)
            success = False

        donation_journal_migration_count = 0
        donation_journal_migration_fails = 0
        for donation_journal in donation_journal_list:
            try:
                donation_journal.organization_we_vote_id = to_organization_we_vote_id
                donation_journal.save()
                donation_journal_migration_count += 1
            except Exception as e:
                donation_journal_migration_fails += 1

        if positive_value_exists(donation_journal_migration_count):
            status += "DONATION_JOURNAL_MOVED: " + str(donation_journal_migration_count) + " "
        if positive_value_exists(donation_journal_migration_fails):
            status += "DONATION_JOURNAL_FAILS: " + str(donation_journal_migration_fails) + " "

        results = {
            'status':                       status,
            'success':                      success,
            'from_organization_we_vote_id': from_organization_we_vote_id,
            'to_organization_we_vote_id':   to_organization_we_vote_id,
        }
        return results

    @staticmethod
    def move_donation_plan_definition_entries_from_organization_to_organization(
            from_organization_we_vote_id, to_organization_we_vote_id):
        """

        :param from_organization_we_vote_id:
        :param to_organization_we_vote_id:
        :return:
        """
        status = ''
        donation_plan_definition_list = []

        try:
            donation_plan_definition_query = DonationPlanDefinition.objects.all()
            donation_plan_definition_query = donation_plan_definition_query.filter(
                organization_we_vote_id__iexact=from_organization_we_vote_id)
            donation_plan_definition_list = list(donation_plan_definition_query)
            status += "move_donation_plan_definition_entries_from_organization_to_organization LIST_RETRIEVED-" + \
                      from_organization_we_vote_id + "-TO-" + to_organization_we_vote_id + \
                      " LENGTH: " + str(len(donation_plan_definition_list)) + " "
            logger.debug(status)
            success = True
        except Exception as e:
            status += "RETRIEVE_EXCEPTION_IN-move_donation_plan_definition_entries_from_organization_to_organization "
            logger.error("move_donation_plan_definition_entries_from_organization_to_organization 2:" + status)
            success = False

        donation_plan_definition_migration_count = 0
        donation_plan_definition_migration_fails = 0
        for donation_plan_definition in donation_plan_definition_list:
            try:
                donation_plan_definition.organization_we_vote_id = to_organization_we_vote_id
                donation_plan_definition.save()
                donation_plan_definition_migration_count += 1
            except Exception as e:
                donation_plan_definition_migration_fails += 1

        if positive_value_exists(donation_plan_definition_migration_count):
            status += "DONATION_PLAN_DEFINITION_MOVED: " + str(donation_plan_definition_migration_count) + " "
        if positive_value_exists(donation_plan_definition_migration_fails):
            status += "DONATION_PLAN_DEFINITION_FAILS: " + str(donation_plan_definition_migration_fails) + " "

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
            queryset = DonationJournal.objects.all().order_by('-id')
            rows = queryset.filter(subscription_plan_id=plan_id)
            if len(rows):
                row = rows[0]
                if row.last4 == 0:
                    row_id = row.id
        except DonationJournal.DoesNotExist:
            logger.error("check_for_subscription_in_db_without_card_info row does not exist for stripe customer" +
                         customer)
        except Exception as e:
            logger.error("check_for_subscription_in_db_without_card_info Exception " + str(e))

        return row_id

    @staticmethod
    def update_subscription_in_db(row_id, amount, currency, id_card, address_zip, brand, country, exp_month, exp_year,
                                  last4, funding):
        try:
            row = DonationJournal.objects.get(id=row_id)
            row.amount = amount
            row.currency = currency
            row.id_card = id_card
            row.address_zip = address_zip
            row.brand = brand
            row.country = country
            row.exp_month = exp_month
            row.exp_year = exp_year
            row.last4 = last4
            row.funding = funding
            row.save()
            logger.debug("update_subscription_in_db row=" + str(row_id) + ", plan_id=" + str(row.subscription_plan_id) +
                         ", amount=" + str(amount))
        except Exception as err:
            logger.error("update_subscription_in_db: " + str(err))

        return

    @staticmethod
    def find_we_vote_voter_id_for_stripe_customer(stripe_customer_id):

        try:
            queryset = DonationJournal.objects.all().order_by('-id')
            rows = queryset.filter(stripe_customer_id=stripe_customer_id)
            for row in rows:
                if row.not_loggedin_voter_we_vote_id == None and \
                   row.record_enum == "SUBSCRIPTION_SETUP_AND_INITIAL" and \
                   row.voter_we_vote_id != "":
                    return row.voter_we_vote_id
            for row in rows:
                if row.not_loggedin_voter_we_vote_id != None:
                    return row.not_loggedin_voter_we_vote_id

            return ""

        except DonationJournal.DoesNotExist:
            logger.error("find_we_vote_voter_id_for_stripe_customer row does not exist")
        except Exception as e:
            logger.error("find_we_vote_voter_id_for_stripe_customer: " + str(e))

        return ""

    @staticmethod
    def update_journal_entry_for_refund(charge, voter_we_vote_id, refund):
        if refund and refund['amount'] > 0 and refund['status'] == "succeeded":
            row = DonationJournal.objects.get(charge_id__iexact=charge, voter_we_vote_id__iexact=voter_we_vote_id)
            row.status = textwrap.shorten(row.status + " CHARGE_REFUND_REQUESTED" + "_" + str(refund['created']) +
                                          "_" + refund['currency'] + "_" + str(refund['amount']) + "_REFUND_ID" +
                                          refund['id'] + " ", width=255, placeholder="...")
            row.amount_refunded = refund['amount']
            row.stripe_status = "refund pending"
            row.save()
            logger.debug("update_journal_entry_for_refund for charge " + charge + ", with status: " + row.status)

            return "True"

        logger.error("update_journal_entry_for_refund bad charge or refund for charge_id " + charge +
                     " and voter_we_vote_id " + voter_we_vote_id)
        return "False"

    @staticmethod
    def update_journal_entry_for_already_refunded(charge, voter_we_vote_id):
        row = DonationJournal.objects.get(charge_id__iexact=charge, voter_we_vote_id__iexact=voter_we_vote_id)
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
            queryset = DonationJournal.objects.all().order_by('-id')
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

        except DonationJournal.DoesNotExist:
            logger.error("update_journal_entry_for_refund_completed row does not exist for charge " + charge)
        return "False"

    @staticmethod
    def update_donation_invoice(subscription_id, we_vote_donation_plan_identifier, invoice_id, invoice_date, customer_id):
        """
        Store the invoice for later use, when the charge.succeeded comes through
        :param subscription_id:
        :param we_vote_donation_plan_identifier:
        :param invoice_id:
        :param invoice_date:
        :param customer_id:
        :return:
        """
        debug = logger.debug("update_donation_invoice: " + we_vote_donation_plan_identifier + " " + subscription_id + " " + invoice_id)

        try:
            new_invoice_entry = DonationInvoice.objects.create(
                subscription_id=subscription_id, donation_plan_id=we_vote_donation_plan_identifier, invoice_id=invoice_id,
                invoice_date=invoice_date, stripe_customer_id=customer_id)

            success = True
            status = 'NEW_INVOICE_ENTRY_SAVED'

        except Exception as e:
            success = False

        saved_results = {
            'success': success,
            'status': status,
            'history_entry_saved': new_invoice_entry
        }
        return saved_results

    @staticmethod
    def update_subscription_with_latest_charge_date(invoice_id, invoice_date):
        """
        Get the last_charged into the subscription row in the DonationJournal
        :param: invoice_id:
        :param invoice_date:
        :return:
        """

        # First find the subscription_id from the cached invoices
        row_invoice = DonationInvoice.objects.get(invoice_id=invoice_id)
        try:
            subscription_id = row_invoice.subscription_id
        except Exception as e:
            # Sometimes the payment, comes a second before the invoice (yuck), so try one more time in 10 seconds
            logger.debug("update_subscription_with_latest_charge_date: trying again after 10 sec for " + invoice_id)
            time.sleep(10)
            row_invoice = DonationInvoice.objects.get(invoice_id=invoice_id)
            subscription_id = row_invoice.subscription_id

        try:
            # Then find the subscription in the DonationJournal row that matches the subscription_id
            row_subscription = DonationJournal.objects.get(subscription_id=subscription_id,
                                                           record_enum="SUBSCRIPTION_SETUP_AND_INITIAL")
            row_subscription.last_charged = datetime.fromtimestamp(invoice_date, timezone.utc)
            row_subscription.save()
            logger.debug("update_subscription_with_latest_charge_date: " + invoice_id + " " +
                        subscription_id + "  journal row: " + str(row_subscription.id))

            # Finally, remove older invoice records ... the invoice records are only needed for a minute or two.
            # Save 10 days worth of invoice, in case we need to diagnose a problem.
            how_many_days= 10
            queryset = DonationInvoice.objects.filter(invoice_date__lte=datetime.fromtimestamp(
                int(time.time()), timezone.utc) - timedelta(days=how_many_days))
            logger.info("update_subscription_with_latest_charge_date: DELETED " + str(queryset.count()) +
                        " invoice rows that were older than " + str(how_many_days) + " days old.")
            queryset.delete()

        except Exception as e:
            handle_exception(e, logger=logger,
                             exception_message="update_subscription_with_latest_charge_date: " + str(e))
        return

    @staticmethod
    def get_missing_charge_info(voter_we_vote_id, organization_we_vote_id, amount):
        try:
            # Then find the SUBSCRIPTION_SETUP_AND_INITIAL in the DonationJournal row that matches this charge.succeeded
            queryset = DonationJournal.objects.all().order_by('-id')
            journal_rows = queryset.filter(voter_we_vote_id__iexact=voter_we_vote_id,
                                   organization_we_vote_id__iexact=organization_we_vote_id,
                                   amount=amount,
                                   record_enum__iexact="SUBSCRIPTION_SETUP_AND_INITIAL")

            if len(journal_rows):
                row = journal_rows[0]
                journal = {
                    'subscription_plan_id': row.subscription_plan_id,
                    'subscription_id': row.subscription_id,
                    'is_organization_plan': row.is_organization_plan,
                    'plan_type_enum': row.plan_type_enum,
                    'coupon_code': row.coupon_code,
                    'success': True,
                    'status:': "Row found",
                }

        except DonationJournal.DoesNotExist:
            logger.error("Donation Journal table does not exist")
            journal = {
                'subscription_plan_id': '',
                'subscription_id': '',
                'is_organization_plan': '',
                'plan_type_enum': '',
                'coupon_code': '',
                'success': False,
                'status:': "Donation Journal table does not exist",
            }

        except Exception as e:
            logger.error("subscription info row does not exist for voter ", e)
            journal = {
                'subscription_plan_id': '',
                'subscription_id': '',
                'is_organization_plan': '',
                'plan_type_enum': '',
                'coupon_code': '',
                'success': False,
                'status:': "Donation Journal table does not exist",
            }

        return journal

    @staticmethod
    def create_initial_coupons():
        # If there is no 25OFF, create one -- so that developers have at least one coupon, and the defaults, in the db
        pro_features_provided_bitmap = 0
        pro_features_provided_bitmap += CHOSEN_FULL_DOMAIN_ALLOWED
        pro_features_provided_bitmap += CHOSEN_PROMOTED_ORGANIZATIONS_ALLOWED

        enterprise_features_provided_bitmap = 0
        enterprise_features_provided_bitmap += CHOSEN_FAVICON_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_FULL_DOMAIN_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_GOOGLE_ANALYTICS_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_SOCIAL_SHARE_IMAGE_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_SOCIAL_SHARE_DESCRIPTION_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_PROMOTED_ORGANIZATIONS_ALLOWED

        # We do not want default pricing for Enterprise, so we set these up with "is_archived" set
        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=ENTERPRISE_MONTHLY, coupon_code='DEFAULT-ENTERPRISE_MONTHLY')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='DEFAULT-ENTERPRISE_MONTHLY',
                plan_type_enum=ENTERPRISE_MONTHLY,
                defaults={
                    'coupon_applied_message': 'Not visible on screen, since this is a default.',
                    'monthly_price_stripe': 0,
                    'annual_price_stripe': 0,
                    'master_feature_package': 'ENTERPRISE',
                    'features_provided_bitmap': enterprise_features_provided_bitmap,
                    'hidden_plan_comment': 'We do not share default Enterprise pricing.',
                    'is_archived': True,
                }
            )

        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=ENTERPRISE_YEARLY, coupon_code='DEFAULT-ENTERPRISE_YEARLY')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='DEFAULT-ENTERPRISE_YEARLY',
                plan_type_enum=ENTERPRISE_YEARLY,
                defaults={
                    'coupon_applied_message': 'Not visible on screen, since this is a default',
                    'monthly_price_stripe': 0,
                    'annual_price_stripe': 0,
                    'master_feature_package': 'ENTERPRISE',
                    'features_provided_bitmap': enterprise_features_provided_bitmap,
                    'hidden_plan_comment': 'We do not share default Enterprise pricing.',
                    'is_archived': True,
                }
            )

        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=PROFESSIONAL_MONTHLY, coupon_code='DEFAULT-PROFESSIONAL_MONTHLY')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='DEFAULT-PROFESSIONAL_MONTHLY',
                plan_type_enum=PROFESSIONAL_MONTHLY,
                defaults={
                    'coupon_applied_message': 'Not visible on screen, since this is a default',
                    'monthly_price_stripe': 15000,
                    'annual_price_stripe': 0,
                    'master_feature_package': 'PROFESSIONAL',
                    'features_provided_bitmap': pro_features_provided_bitmap,
                    'hidden_plan_comment': '',
                }
            )

        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=PROFESSIONAL_YEARLY, coupon_code='DEFAULT-PROFESSIONAL_YEARLY')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='DEFAULT-PROFESSIONAL_YEARLY',
                plan_type_enum=PROFESSIONAL_YEARLY,
                defaults={
                    'coupon_applied_message': 'Not visible on screen, since this is a default',
                    'monthly_price_stripe': 0,
                    'annual_price_stripe': 150000,
                    'master_feature_package': 'PROFESSIONAL',
                    'features_provided_bitmap': pro_features_provided_bitmap,
                    'hidden_plan_comment': '',
                }
            )

        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=PROFESSIONAL_MONTHLY, coupon_code='25OFF')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='25OFF',
                plan_type_enum=PROFESSIONAL_MONTHLY,
                defaults={
                    'coupon_applied_message': 'You save $25 per month.',
                    'monthly_price_stripe': 12500,
                    'annual_price_stripe': 0,
                    'master_feature_package': 'PROFESSIONAL',
                    'features_provided_bitmap': pro_features_provided_bitmap,
                    'hidden_plan_comment': '',
                }
            )

        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=PROFESSIONAL_YEARLY, coupon_code='25OFF')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='25OFF',
                plan_type_enum=PROFESSIONAL_YEARLY,
                defaults={
                    'coupon_applied_message': 'You save $300 per year.',
                    'monthly_price_stripe': 0,
                    'annual_price_stripe': 120000,
                    'master_feature_package': 'PROFESSIONAL',
                    'features_provided_bitmap': pro_features_provided_bitmap,
                    'hidden_plan_comment': '',
                }
            )

        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=ENTERPRISE_MONTHLY, coupon_code='VOTE9X3')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='VOTE9X3',
                plan_type_enum=ENTERPRISE_MONTHLY,
                defaults={
                    'coupon_applied_message': '',
                    'monthly_price_stripe': 22500,
                    'annual_price_stripe': 0,
                    'master_feature_package': 'ENTERPRISE',
                    'features_provided_bitmap': enterprise_features_provided_bitmap,
                    'hidden_plan_comment': 'Nonprofit, annual revenues < $1M',
                }
            )

        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=ENTERPRISE_YEARLY, coupon_code='VOTE9X3')
        if not coupon_queryset:
            coupon, coupon_created = OrganizationSubscriptionPlans.objects.get_or_create(
                coupon_code='VOTE9X3',
                plan_type_enum=ENTERPRISE_YEARLY,
                defaults={
                    'coupon_applied_message': '',
                    'monthly_price_stripe': 0,
                    'annual_price_stripe': 225000,
                    'master_feature_package': 'ENTERPRISE',
                    'features_provided_bitmap': enterprise_features_provided_bitmap,
                    'hidden_plan_comment': 'Nonprofit, annual revenues < $1M',
                }
            )
        return

    @staticmethod
    def create_initial_master_feature_packages():
        """
        The master feature packages we want to keep updated.
        Make sure these match the features provided in organizationIndex
        :return:
        """
        master_feature_package, package_created = MasterFeaturePackage.objects.update_or_create(
            master_feature_package='FREE',
            defaults={
                'master_feature_package': 'FREE',
                'features_provided_bitmap': 0,
            }
        )
        pro_features_provided_bitmap = 0
        pro_features_provided_bitmap += CHOSEN_FULL_DOMAIN_ALLOWED
        pro_features_provided_bitmap += CHOSEN_PROMOTED_ORGANIZATIONS_ALLOWED
        master_feature_package, package_created = MasterFeaturePackage.objects.update_or_create(
            master_feature_package='PROFESSIONAL',
            defaults={
                'master_feature_package': 'PROFESSIONAL',
                'features_provided_bitmap': pro_features_provided_bitmap,
            }
        )
        enterprise_features_provided_bitmap = 0
        enterprise_features_provided_bitmap += CHOSEN_FAVICON_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_FULL_DOMAIN_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_GOOGLE_ANALYTICS_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_SOCIAL_SHARE_IMAGE_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_SOCIAL_SHARE_DESCRIPTION_ALLOWED
        enterprise_features_provided_bitmap += CHOSEN_PROMOTED_ORGANIZATIONS_ALLOWED
        master_feature_package, package_created = MasterFeaturePackage.objects.update_or_create(
            master_feature_package='ENTERPRISE',
            defaults={
                'master_feature_package': 'ENTERPRISE',
                'features_provided_bitmap': enterprise_features_provided_bitmap,
            }
        )

    @staticmethod
    def retrieve_coupon_summary(coupon_code):  # couponSummaryRetrieve
        status = ""
        success = True
        coupon_applied_message = ""
        coupon_match_found = False
        coupon_plan_list = []
        coupon_still_valid = False
        enterprise_plan_coupon_price_per_month_pay_monthly = 0
        enterprise_plan_coupon_price_per_month_pay_monthly_found = False
        enterprise_plan_coupon_price_per_month_pay_yearly = 0
        enterprise_plan_coupon_price_per_month_pay_yearly_found = False
        pro_plan_coupon_price_per_month_pay_monthly = 0
        pro_plan_coupon_price_per_month_pay_monthly_found = False
        pro_plan_coupon_price_per_month_pay_yearly = 0
        pro_plan_coupon_price_per_month_pay_yearly_found = False
        valid_for_enterprise_plan = False
        valid_for_professional_plan = False

        if not positive_value_exists(coupon_code):
            success = False
            status += "VALIDATE_COUPON_CODE_MISSING "
            results = {
                'coupon_applied_message':           '',
                'coupon_code_string':               coupon_code,
                'coupon_match_found':               False,
                'coupon_still_valid':               False,
                'enterprise_plan_coupon_price_per_month_pay_yearly': enterprise_plan_coupon_price_per_month_pay_yearly,
                'enterprise_plan_coupon_price_per_month_pay_monthly':
                    enterprise_plan_coupon_price_per_month_pay_monthly,
                'pro_plan_coupon_price_per_month_pay_yearly':        pro_plan_coupon_price_per_month_pay_yearly,
                'pro_plan_coupon_price_per_month_pay_monthly':       pro_plan_coupon_price_per_month_pay_monthly,
                'valid_for_enterprise_plan':        valid_for_enterprise_plan,
                'valid_for_professional_plan':      valid_for_professional_plan,
                'status':                           status,
                'success':                          success,
            }
            return results

        DonationManager.create_initial_coupons()

        try:
            # First find the subscription_id from the cached invoices
            coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
                coupon_code__iexact=coupon_code).order_by('-plan_created_at')
            coupon_queryset = coupon_queryset.exclude(is_archived=True)

            coupon_plan_list = list(coupon_queryset)
        except Exception as e:
            logger.debug("validate_coupon threw: ", e)

        valid_for_enterprise_plan = False
        valid_for_professional_plan = False
        date_now_as_integer = convert_date_to_date_as_integer(datetime.now().date())
        for coupon in coupon_plan_list:
            if coupon.coupon_expires_date:
                expires_as_integer = convert_date_to_date_as_integer(coupon.coupon_expires_date)
                if date_now_as_integer > expires_as_integer:
                    # Skip this part of the coupon
                    continue

            if coupon.plan_type_enum == ENTERPRISE_MONTHLY:
                # Only proceed if a newer coupon hasn't already been found
                if not enterprise_plan_coupon_price_per_month_pay_monthly_found:
                    coupon_match_found = True
                    coupon_still_valid = True
                    enterprise_plan_coupon_price_per_month_pay_monthly_found = True
                    enterprise_plan_coupon_price_per_month_pay_monthly = coupon.monthly_price_stripe
                    valid_for_enterprise_plan = True
            elif coupon.plan_type_enum == ENTERPRISE_YEARLY:
                # Only proceed if a newer coupon hasn't already been found
                if not enterprise_plan_coupon_price_per_month_pay_yearly_found:
                    coupon_match_found = True
                    coupon_still_valid = True
                    enterprise_plan_coupon_price_per_month_pay_yearly_found = True
                    enterprise_plan_coupon_price_per_month_pay_yearly = coupon.annual_price_stripe / 12
                    valid_for_enterprise_plan = True
            elif coupon.plan_type_enum == PROFESSIONAL_MONTHLY:
                # Only proceed if a newer coupon hasn't already been found
                if not pro_plan_coupon_price_per_month_pay_monthly_found:
                    coupon_match_found = True
                    coupon_still_valid = True
                    pro_plan_coupon_price_per_month_pay_monthly_found = True
                    pro_plan_coupon_price_per_month_pay_monthly = coupon.monthly_price_stripe
                    valid_for_professional_plan = True
            elif coupon.plan_type_enum == PROFESSIONAL_YEARLY:
                # Only proceed if a newer coupon hasn't already been found
                if not pro_plan_coupon_price_per_month_pay_yearly_found:
                    coupon_match_found = True
                    coupon_still_valid = True
                    pro_plan_coupon_price_per_month_pay_yearly_found = True
                    pro_plan_coupon_price_per_month_pay_yearly = coupon.annual_price_stripe / 12
                    valid_for_professional_plan = True

        results = {
            'coupon_applied_message':           coupon_applied_message,
            'coupon_code_string':               coupon_code,
            'coupon_match_found':               coupon_match_found,
            'coupon_still_valid':               coupon_still_valid,
            'enterprise_plan_coupon_price_per_month_pay_yearly':    enterprise_plan_coupon_price_per_month_pay_yearly,
            'enterprise_plan_coupon_price_per_month_pay_monthly':   enterprise_plan_coupon_price_per_month_pay_monthly,
            'pro_plan_coupon_price_per_month_pay_yearly':           pro_plan_coupon_price_per_month_pay_yearly,
            'pro_plan_coupon_price_per_month_pay_monthly':          pro_plan_coupon_price_per_month_pay_monthly,
            'valid_for_enterprise_plan':        valid_for_enterprise_plan,
            'valid_for_professional_plan':      valid_for_professional_plan,
            'status':                           status,
            'success':                          success,
        }
        return results

    @staticmethod
    def retrieve_default_pricing():  # defaultPricing
        status = ""
        success = True
        default_pricing_list = []
        enterprise_plan_full_price_per_month_pay_monthly = 0
        enterprise_plan_full_price_per_month_pay_monthly_found = False
        enterprise_plan_full_price_per_month_pay_yearly = 0
        enterprise_plan_full_price_per_month_pay_yearly_found = False
        pro_plan_full_price_per_month_pay_monthly = 0
        pro_plan_full_price_per_month_pay_monthly_found = False
        pro_plan_full_price_per_month_pay_yearly = 0
        pro_plan_full_price_per_month_pay_yearly_found = False

        try:
            default_pricing_queryset = OrganizationSubscriptionPlans.objects.filter(
                coupon_code__in=['DEFAULT-ENTERPRISE_MONTHLY', 'DEFAULT-ENTERPRISE_YEARLY',
                                 'DEFAULT-PROFESSIONAL_MONTHLY', 'DEFAULT-PROFESSIONAL_YEARLY']
            ).order_by('-plan_created_at')
            default_pricing_queryset = default_pricing_queryset.exclude(is_archived=True)

            default_pricing_list = list(default_pricing_queryset)
        except Exception as e:
            logger.debug("retrieve_default_pricing threw: ", e)

        valid_for_enterprise_plan = False
        valid_for_professional_plan = False
        date_now_as_integer = convert_date_to_date_as_integer(datetime.now().date())
        for coupon in default_pricing_list:
            if coupon.coupon_expires_date:
                expires_as_integer = convert_date_to_date_as_integer(coupon.coupon_expires_date)
                if date_now_as_integer > expires_as_integer:
                    # Skip this part of the coupon
                    continue

            if coupon.plan_type_enum == ENTERPRISE_MONTHLY:
                # Only proceed if a newer coupon hasn't already been found
                if not enterprise_plan_full_price_per_month_pay_monthly_found:
                    enterprise_plan_full_price_per_month_pay_monthly_found = True
                    enterprise_plan_full_price_per_month_pay_monthly = coupon.monthly_price_stripe
                    valid_for_enterprise_plan = True
            elif coupon.plan_type_enum == ENTERPRISE_YEARLY:
                # Only proceed if a newer coupon hasn't already been found
                if not enterprise_plan_full_price_per_month_pay_yearly_found:
                    enterprise_plan_full_price_per_month_pay_yearly_found = True
                    enterprise_plan_full_price_per_month_pay_yearly = coupon.annual_price_stripe / 12
                    valid_for_enterprise_plan = True
            elif coupon.plan_type_enum == PROFESSIONAL_MONTHLY:
                # Only proceed if a newer coupon hasn't already been found
                if not pro_plan_full_price_per_month_pay_monthly_found:
                    pro_plan_full_price_per_month_pay_monthly_found = True
                    pro_plan_full_price_per_month_pay_monthly = coupon.monthly_price_stripe
                    valid_for_professional_plan = True
            elif coupon.plan_type_enum == PROFESSIONAL_YEARLY:
                # Only proceed if a newer coupon hasn't already been found
                if not pro_plan_full_price_per_month_pay_yearly_found:
                    pro_plan_full_price_per_month_pay_yearly_found = True
                    pro_plan_full_price_per_month_pay_yearly = coupon.annual_price_stripe / 12
                    valid_for_professional_plan = True

        results = {
            'enterprise_plan_full_price_per_month_pay_monthly': enterprise_plan_full_price_per_month_pay_monthly,
            'enterprise_plan_full_price_per_month_pay_yearly':  enterprise_plan_full_price_per_month_pay_yearly,
            'pro_plan_full_price_per_month_pay_monthly':        pro_plan_full_price_per_month_pay_monthly,
            'pro_plan_full_price_per_month_pay_yearly':         pro_plan_full_price_per_month_pay_yearly,
            'valid_for_enterprise_plan':        valid_for_enterprise_plan,
            'valid_for_professional_plan':      valid_for_professional_plan,
            'status':                           status,
            'success':                          success,
        }
        return results

    @staticmethod
    def validate_coupon(plan_type_enum, coupon_code):
        # First find the subscription_id from the cached invoices
        status = ""
        coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
            plan_type_enum=plan_type_enum, coupon_code=coupon_code).order_by('-plan_created_at')
        coupon_queryset = coupon_queryset.exclude(is_archived=True)
        if not coupon_queryset:
            coupon = []
            status = 'COUPON_MATCH_NOT_FOUND '
        else:
            coupon = coupon_queryset[0]
        coupon_match_found = False
        coupon_still_valid = False
        monthly_price_stripe = 0
        annual_price_stripe = 0
        success = False

        coupon_applied_message = ""

        try:
            if coupon:
                coupon_match_found = True
                status = 'COUPON_MATCH_FOUND '

                expires = coupon.coupon_expires_date
                if expires is None:
                    coupon_still_valid = True
                else:
                    today_date_as_integer = convert_date_to_date_as_integer(datetime.now().date())
                    expires_as_integer = convert_date_to_date_as_integer(expires)
                    if today_date_as_integer < expires_as_integer:
                        coupon_still_valid = True

                if 'MONTHLY' in plan_type_enum:
                    monthly_price_stripe = coupon.monthly_price_stripe if coupon_match_found else 0
                else:
                    annual_price_stripe = coupon.annual_price_stripe if coupon_match_found else 0

                coupon_applied_message = coupon.coupon_applied_message
                success = True

        except Exception as e:
            logger.debug("validate_coupon threw: ", e)

        results = {
            'coupon_applied_message':           coupon_applied_message,
            'coupon_match_found':               coupon_match_found,
            'coupon_still_valid':               coupon_still_valid,
            'monthly_price_stripe':             monthly_price_stripe,
            'annual_price_stripe':              annual_price_stripe,
            'status':                           status,
            'success':                          success,
        }
        return results

    @staticmethod
    def get_coupon_price(plan_type_enum, coupon_code, increment_redemption_count):
        """
        By the time we get here, the coupon has already been verified, so it will exist
        Return the price from the latest version of the coupon
        :param plan_type_enum:
        :param coupon_code:
        :param increment_redemption_count:
        :return: price
        """
        price = -1
        org_subs_id = -1
        try:
            coupon_queryset = OrganizationSubscriptionPlans.objects.filter(
                plan_type_enum=plan_type_enum, coupon_code=coupon_code).order_by('-plan_created_at')
            coupon_queryset = coupon_queryset.exclude(is_archived=True)
            coupon_list = list(coupon_queryset)
            if len(coupon_list):
                coupon = coupon_queryset[0]
                if 'MONTHLY' in plan_type_enum:
                    price = coupon.monthly_price_stripe
                else:
                    price = coupon.annual_price_stripe

                if increment_redemption_count:
                    coupon.redemptions += 1
                    coupon.save()

                org_subs_id = coupon.id
        except Exception as e:
            logger.debug("get_coupon_price threw: ", e)

        return price, org_subs_id

