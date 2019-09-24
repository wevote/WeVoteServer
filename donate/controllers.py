# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime, timezone
from donate.models import DonationManager, MasterFeaturePackage
from organization.models import OrganizationManager
from wevote_functions.functions import get_ip_from_headers, positive_value_exists
from wevote_functions.admin import get_logger
from wevote_functions.functions import convert_pennies_integer_to_dollars_string, get_voter_device_id
from voter.models import VoterManager
import json
import stripe
import textwrap


logger = get_logger(__name__)
stripe.api_key = get_environment_variable("STRIPE_SECRET_KEY")
if (not stripe.api_key.startswith("sk_")):
    logger.error("Configuration error, the stripe secret key, must begin with 'sk_' -- don't use the publishable key "
                 "on the server!")


def donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id):
    status = ''
    active_paid_plan_found = False
    donation_plan_definition_list = []
    donation_plan_definition_list_json = []
    coupon_code = ''
    we_vote_donation_plan_identifier = ''
    plan_type_enum = ''
    stripe_customer_id = ''
    stripe_subscription_id = False
    next_invoice_retrieved = False
    last_amount_paid = 0
    subscription_active = ''
    subscription_canceled_at = ''
    subscription_ended_at = ''
    subscription_found = False

    donation_manager = DonationManager()
    if positive_value_exists(linked_organization_we_vote_id):
        plan_results = donation_manager.retrieve_donation_plan_definition_list(
            organization_we_vote_id=linked_organization_we_vote_id, return_json_version=True)
        donation_plan_definition_list = plan_results['donation_plan_definition_list']
        donation_plan_definition_list_json = plan_results['donation_plan_definition_list_json']
    elif positive_value_exists(voter_we_vote_id):
        plan_results = donation_manager.retrieve_donation_plan_definition_list(
            voter_we_vote_id=voter_we_vote_id, return_json_version=True)
        donation_plan_definition_list = plan_results['donation_plan_definition_list']
        donation_plan_definition_list_json = plan_results['donation_plan_definition_list_json']

    status += "SUCCESSFULLY_RETRIEVED_DONATION_HISTORY "
    success = True

    for donation_plan_definition in donation_plan_definition_list:
        if positive_value_exists(donation_plan_definition.is_organization_plan):
            if positive_value_exists(donation_plan_definition.donation_plan_is_active):
                active_paid_plan_found = True
                donation_plan_definition_id = donation_plan_definition.id
                plan_type_enum = donation_plan_definition.plan_type_enum
                coupon_code = donation_plan_definition.coupon_code
                we_vote_donation_plan_identifier = donation_plan_definition.donation_plan_id
                stripe_customer_id = donation_plan_definition.stripe_customer_id
                stripe_subscription_id = donation_plan_definition.stripe_subscription_id
                if not positive_value_exists(stripe_subscription_id) \
                        and not donation_plan_definition.paid_without_stripe:
                    # Reach out to Stripe to match existing subscription
                    subscription_list_results = stripe.Subscription.list(limit=10)
                    if 'data' in subscription_list_results and len(subscription_list_results['data']):
                        for one_subscription in subscription_list_results['data']:
                            if 'plan' in one_subscription and 'id' in one_subscription['plan']:
                                if one_subscription['plan']['id'] == donation_plan_definition.donation_plan_id:
                                    stripe_subscription_id = one_subscription['id']
                                    donation_plan_definition.stripe_subscription_id = one_subscription['id']
                                    donation_plan_definition.save()
                                    break

    credit_card_last_four = ''
    email = ''
    exp_month = ''
    exp_year = ''
    if positive_value_exists(stripe_customer_id):
        try:
            customer = stripe.Customer.retrieve(stripe_customer_id)
            email = customer['email']
            source = customer['sources']['data'][0]
            id_card = source['id']
            address_zip = source['address_zip']
            brand = source['brand']
            country = source['country']
            exp_month = source['exp_month']
            exp_year = source['exp_year']
            funding = source['funding']
            credit_card_last_four = source['last4']
        except Exception as e:
            status += "CUSTOMER_COULD_NOT_BE_RETRIEVED_FROM_STRIPE " + str(e) + " "

    amount_due = ''
    invoice_date = ''
    period_start = ''
    period_end = ''
    if positive_value_exists(stripe_subscription_id):
        try:
            next_invoice_results = stripe.Invoice.upcoming(subscription=stripe_subscription_id)
            amount_due = convert_pennies_integer_to_dollars_string(next_invoice_results['amount_due'])

            if 'lines' in next_invoice_results:
                if 'data' in next_invoice_results['lines']:
                    one_line = next_invoice_results['lines']['data'][0]
                    if 'period' in one_line:
                        period_start_unix_time = 0
                        period_end_unix_time = 0
                        if 'start' in one_line['period']:
                            period_start_unix_time = one_line['period']['start']
                        if 'end' in one_line['period']:
                            period_end_unix_time = one_line['period']['end']
                        if type(period_start_unix_time) is int:
                            period_start = datetime.fromtimestamp(period_start_unix_time, timezone.utc)
                        else:
                            period_start = ''
                        if type(period_end_unix_time) is int:
                            period_end = datetime.fromtimestamp(period_end_unix_time, timezone.utc)
                        else:
                            period_end = ''

            if type(next_invoice_results['created']) is int:
                invoice_date = datetime.fromtimestamp(next_invoice_results['created'], timezone.utc)
            else:
                invoice_date = ''
            next_invoice_retrieved = True
        except Exception as e:
            status += "NEXT_INVOICE_COULD_NOT_BE_RETRIEVED_FROM_STRIPE "

    if positive_value_exists(next_invoice_retrieved):
        if positive_value_exists(exp_month) and positive_value_exists(exp_year):
            credit_card_expiration = str(exp_month) + "/" + str(exp_year)
        else:
            credit_card_expiration = ''
        next_invoice = {
            'next_invoice_found':       True,
            'amount_due':               amount_due,
            'invoice_date':             str(invoice_date),
            'period_start':             str(period_start),
            'period_end':               str(period_end),
            'credit_card_last_four':    credit_card_last_four,
            'credit_card_expiration':   credit_card_expiration,
            'billing_contact':          email,
        }
    else:
        next_invoice = {
            'next_invoice_found':       False,
        }

    active_paid_plan = {
        'coupon_code':              coupon_code,
        'donation_plan_id':         we_vote_donation_plan_identifier,
        'next_invoice':             next_invoice,
        'plan_type_enum':           plan_type_enum,
        'stripe_subscription_id':   stripe_subscription_id,
        'subscription_active':      active_paid_plan_found,
        # 'subscription_canceled_at': subscription_canceled_at,
        # 'subscription_ended_at':    subscription_ended_at,
    }
    results = {
        'status': status,
        'success': success,
        'active_paid_plan': active_paid_plan,
        'donation_plan_definition_list_json':   donation_plan_definition_list_json,
    }
    return results


def donation_with_stripe_for_api(request, token, email, donation_amount, monthly_donation, voter_we_vote_id,
                                 is_organization_plan, coupon_code, plan_type_enum, organization_we_vote_id):
    """
    Initiate a donation or organization subscription plan using the Stripe Payment API, and record details in our DB
    :param request:
    :param token: The Stripe token.id for the card and transaction
    :param email:
    :param donation_amount:
    :param monthly_donation:
    :param voter_we_vote_id:
    :param is_organization_plan:  True for a organization plan, False for a donation (one time or donation subscription)
    :param coupon_code: Our coupon codes for pricing and features that are looked up
           in the OrganizationSubscriptionPlans
    :param plan_type_enum: Type of organization plan, or undefined for donations
    :param organization_we_vote_id: The organization that benefits from this paid plan (subscription)
    :return:
    """

    donation_manager = DonationManager()
    success = False
    saved_stripe_donation = False
    donation_entry_saved = False
    donation_date_time = datetime.today()
    donation_status = ''
    if positive_value_exists(is_organization_plan):
        donation_journal_action_taken = 'VOTER_SUBMITTED_SUBSCRIPTION'
    else:
        donation_journal_action_taken = 'VOTER_SUBMITTED_DONATION'
    charge_id = ''
    amount = 0
    currency = ''
    stripe_customer_id = ''
    stripe_subscription_created = False
    donation_plan_definition_already_exists = False
    subscription_saved = 'NOT_APPLICABLE'
    status = ''
    error_message = ''
    funding = ''
    livemode = False
    created = None
    failure_code = ''
    failure_message = ''
    network_status = ''
    reason = ''
    seller_message = ''
    stripe_type = ''
    paid = ''
    amount_refunded = 0
    refund_count = 0
    address_zip = ''
    brand = ''
    country = ''
    exp_month = 0
    exp_year = 0
    last4 = 0
    id_card = ''
    stripe_object = ''
    stripe_status = ''
    stripe_subscription_id = None
    subscription_plan_id = None
    subscription_created_at = None
    subscription_canceled_at = None
    subscription_ended_at = None
    create_donation_entry = False
    create_subscription_entry = False
    charge = None
    not_loggedin_voter_we_vote_id = None
    org_subs_already_exists = False
    organization_saved = False

    ip_address = get_ip_from_headers(request)

    if not positive_value_exists(ip_address):
        ip_address = ''

    if not positive_value_exists(voter_we_vote_id):
        status += "DONATION_WITH_STRIPE_VOTER_WE_VOTE_ID_MISSING "
        error_results = {
            'status':                   status,
            'success':                  success,
            'amount_paid':              amount,
            'charge_id':                charge_id,   # Always 0 here
            'customer_id':              stripe_customer_id,
            'donation_entry_saved':     donation_entry_saved,
            'monthly_donation':         monthly_donation,
            'organization_saved':       organization_saved,
            'org_subs_already_exists':  False,
            'plan_type_enum':           plan_type_enum,
            'saved_stripe_donation':    saved_stripe_donation,
            'stripe_subscription_created':    stripe_subscription_created,
            'subscription':             subscription_saved,
        }

        return error_results

    if not positive_value_exists(email) and not is_organization_plan:
        status += "DONATION_WITH_STRIPE_EMAIL_MISSING "
        error_results = {
            'status':                   status,
            'success':                  success,
            'amount_paid':              amount,
            'charge_id':                charge_id,    # Always 0 here
            'customer_id':              stripe_customer_id,
            'donation_entry_saved':     donation_entry_saved,
            'monthly_donation':         monthly_donation,
            'org_subs_already_exists':  False,
            'organization_saved':       organization_saved,
            'plan_type_enum':           plan_type_enum,
            'saved_stripe_donation':    saved_stripe_donation,
            'stripe_subscription_created':    stripe_subscription_created,
            'subscription':             subscription_saved,
        }

        return error_results

    # Use a default coupon_code if none is specified
    if len(coupon_code) < 2:
        coupon_code = 'DEFAULT-' + plan_type_enum

    # If is_organization_plan, set the price from the coupon, not whatever was passed in.
    if is_organization_plan:
        increment_redemption_cnt = False
        coupon_price, org_subs_id = DonationManager.get_coupon_price(plan_type_enum, coupon_code,
                                                                     increment_redemption_cnt)
        if int(donation_amount) > 0:
            print("Warning for developers, the donation_amount that is passed in for organization plans is ignored,"
                  " the value is read from the coupon")
        donation_amount = coupon_price

    try:
        results = donation_manager.retrieve_stripe_customer_id_from_donate_link_to_voter(voter_we_vote_id)
        if results['success']:
            stripe_customer_id = results['stripe_customer_id']
            status += "STRIPE_CUSTOMER_ID_ALREADY_EXISTS "
        else:
            customer = stripe.Customer.create(
                source=token,
                email=email
            )
            stripe_customer_id = customer.stripe_id
            saved_results = donation_manager.create_donate_link_to_voter(stripe_customer_id, voter_we_vote_id)
            status += saved_results['status']

        if not positive_value_exists(stripe_customer_id):
            status += "STRIPE_CUSTOMER_ID_MISSING "
        else:
            if positive_value_exists(is_organization_plan):
                # If here, we are processing organization subscription
                donation_status += 'DONATION_SUBSCRIPTION_SETUP '
                if "MONTHLY" in plan_type_enum:
                    recurring_interval = 'month'
                elif "YEARLY" in plan_type_enum:
                    recurring_interval = 'year'
                else:
                    recurring_interval = 'year'
                subscription_results = donation_manager.create_organization_subscription(
                    stripe_customer_id, voter_we_vote_id, donation_amount, donation_date_time,
                    email, coupon_code, plan_type_enum, organization_we_vote_id,
                    recurring_interval)

                donation_plan_definition_already_exists = \
                    subscription_results['donation_plan_definition_already_exists']
                stripe_subscription_created = subscription_results['stripe_subscription_created']
                if donation_plan_definition_already_exists:
                    charge_id = 0
                else:
                    status += textwrap.shorten(subscription_results['status'] + " " + status, width=255,
                                               placeholder="...")
                    success = subscription_results['success']
                    create_subscription_entry = True
                    stripe_subscription_id = subscription_results['stripe_subscription_id']
                    subscription_plan_id = subscription_results['subscription_plan_id']
                    subscription_created_at = None
                    if type(subscription_results['subscription_created_at']) is int:
                        subscription_created_at = datetime.fromtimestamp(
                            subscription_results['subscription_created_at'],
                            timezone.utc)
                    created = subscription_created_at
                    subscription_canceled_at = None
                    subscription_ended_at = None
            else:
                # If here, we are processing a donation
                if positive_value_exists(monthly_donation):
                    donation_status += 'DONATION_SUBSCRIPTION_SETUP '
                    recurring_donation_results = donation_manager.create_recurring_donation(
                        stripe_customer_id, voter_we_vote_id,
                        donation_amount, donation_date_time,
                        email, is_organization_plan,
                        coupon_code, plan_type_enum,
                        organization_we_vote_id)

                    org_subs_already_exists = recurring_donation_results['org_subs_already_exists']
                    stripe_subscription_created = recurring_donation_results['stripe_subscription_created']
                    if org_subs_already_exists:
                        charge_id = 0
                    else:
                        subscription_saved = recurring_donation_results['voter_subscription_saved']
                        status += textwrap.shorten(recurring_donation_results['status'] +
                                                   " " + status, width=255, placeholder="...")
                        success = recurring_donation_results['success']
                        create_subscription_entry = True
                        stripe_subscription_id = recurring_donation_results['subscription_id']
                        subscription_plan_id = recurring_donation_results['subscription_plan_id']
                        subscription_created_at = None
                        if type(recurring_donation_results['subscription_created_at']) is int:
                            subscription_created_at = \
                                datetime.fromtimestamp(recurring_donation_results['subscription_created_at'],
                                                       timezone.utc)
                        created = subscription_created_at
                        subscription_canceled_at = None
                        subscription_ended_at = None
                else:  # One time charge
                    charge = stripe.Charge.create(
                        amount=donation_amount,
                        currency="usd",
                        source=token,
                        metadata={
                            'voter_we_vote_id': voter_we_vote_id,
                            'coupon_code': coupon_code,
                            'plan_type_enum': plan_type_enum,
                            'organization_we_vote_id': organization_we_vote_id
                        }
                    )
                    status += textwrap.shorten("STRIPE_CHARGE_SUCCESSFUL " + status, width=255, placeholder="...")
                    create_donation_entry = True
                    charge_id = charge.id
                    success = positive_value_exists(charge_id)

        if positive_value_exists(charge_id):
            saved_stripe_donation = True
            donation_status += ' DONATION_PROCESSED_SUCCESSFULLY '
            amount = charge['amount']
            currency = charge['currency']
            amount_refunded = charge['amount_refunded']
            funding = charge['source']['funding']
            livemode = charge['livemode']
            created = datetime.fromtimestamp(charge['created'], timezone.utc)
            failure_code = str(charge['failure_code'])
            failure_message = str(charge['failure_message'])
            network_status = charge['outcome']['network_status']
            reason = str(charge['outcome']['reason'])
            seller_message = charge['outcome']['seller_message']
            stripe_type = charge['outcome']['type']
            paid = str(charge['paid'])
            amount_refunded = charge['amount_refunded']
            refund_count = charge['refunds']['total_count']
            email = charge['source']['name']
            address_zip = charge['source']['address_zip']
            brand = charge['source']['brand']
            country = charge['source']['country']
            exp_month = charge['source']['exp_month']
            exp_year = charge['source']['exp_year']
            last4 = int(charge['source']['last4'])
            id_card = charge['source']['id']
            stripe_object = charge['source']['object']
            stripe_status = charge['status']
            logger.debug("Stripe charge successful: " + charge_id + ", amount: " + str(amount) + ", voter_we_vote_id:" +
                         voter_we_vote_id)
        else:
            amount = donation_amount
    except stripe.error.CardError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status += " STRIPE_STATUS_IS: {http_status} STRIPE_CARD_ERROR_IS: {error_type} " \
                           "STRIPE_MESSAGE_IS: {error_message} " \
                           "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                     error_message=error_from_json['message'])
        status += textwrap.shorten(donation_status + " " + status, width=255, placeholder="...")
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("donation_with_stripe_for_api, CardError: " + error_message)
        # error_text_description = donation_status
    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status += " STRIPE_STATUS_IS: {http_status} STRIPE_ERROR_IS: {error_type} " \
                           "STRIPE_MESSAGE_IS: {error_message} " \
                           "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                     error_message=error_from_json['message'])
        status += textwrap.shorten(donation_status + " " + status, width=255, placeholder="...")
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("donation_with_stripe_for_api, StripeError : " + donation_status)
    except Exception as err:
        # Something else happened, completely unrelated to Stripe
        donation_status += "A_NON_STRIPE_ERROR_OCCURRED "
        logger.error("donation_with_stripe_for_api threw " + str(err))
        status += textwrap.shorten(donation_status + " " + status, width=255, placeholder="...")
        error_message = 'Your payment was unsuccessful. Please try again later.'
    if "already has the maximum 25 current subscriptions" in status:
        error_message = \
            "No more than 25 active subscriptions are allowed, please delete a subscription before adding another."
        logger.debug("donation_with_stripe_for_api: " + error_message)

    # action_result should be CANCEL_REQUEST_FAILED, CANCEL_REQUEST_SUCCEEDED, DONATION_PROCESSED_SUCCESSFULLY,
    #    STRIPE_DONATION_NOT_COMPLETED
    action_result = donation_status

    logged_in = is_voter_logged_in(request)
    # print("is_voter_logged_in() = " + str(logged_in))
    if not logged_in:
        not_loggedin_voter_we_vote_id = voter_we_vote_id

    if create_subscription_entry:
        # Create Journal entry for a new subscription, with some fields from the initial payment on that subscription
        donation_journal_entry = donation_manager.create_donation_journal_entry(
            "SUBSCRIPTION_SETUP_AND_INITIAL", ip_address, stripe_customer_id,
            voter_we_vote_id, charge_id, amount, currency, funding,
            livemode, donation_journal_action_taken, action_result, created,
            failure_code, failure_message, network_status, reason, seller_message,
            stripe_type, paid, amount_refunded, refund_count,
            email, address_zip, brand, country,
            exp_month, exp_year, last4, id_card, stripe_object,
            stripe_status, status,
            stripe_subscription_id, subscription_plan_id, subscription_created_at, subscription_canceled_at,
            subscription_ended_at, not_loggedin_voter_we_vote_id,
            is_organization_plan, coupon_code, plan_type_enum, organization_we_vote_id)
        donation_entry_saved = donation_journal_entry['success']
        status += textwrap.shorten(donation_journal_entry['status'] + " " + status, width=255, placeholder="...")
        logger.debug("Stripe subscription created successfully, stripe_subscription_id: " + stripe_subscription_id +
                     ", amount: " + str(amount) +
                     ", voter_we_vote_id:" + voter_we_vote_id)

    # These methods have long lists of parameters, the line breaks in the parameters may look messy, but are purposeful
    if create_donation_entry or stripe_subscription_created or donation_plan_definition_already_exists:
        # Create the Journal entry for a payment initiated by the UI. (Automatic payments from the subscription will be
        donation_journal_entry = \
            donation_manager.create_donation_journal_entry(
                "PAYMENT_FROM_UI", ip_address, stripe_customer_id,
                voter_we_vote_id, charge_id, amount, currency, funding,
                livemode, donation_journal_action_taken, action_result, created,
                failure_code, failure_message, network_status, reason, seller_message,
                stripe_type, paid, amount_refunded, refund_count,
                email, address_zip, brand, country,
                exp_month, exp_year, last4, id_card, stripe_object,
                stripe_status, status,
                stripe_subscription_id, subscription_plan_id, None, None,
                None, not_loggedin_voter_we_vote_id,
                is_organization_plan, coupon_code, plan_type_enum, organization_we_vote_id)
        status += textwrap.shorten(donation_journal_entry['status'] + " " + status, width=255, placeholder="...")

    if 'PROFESSIONAL' in plan_type_enum:
        chosen_feature_package = 'PROFESSIONAL'
    elif 'ENTERPRISE' in plan_type_enum:
        chosen_feature_package = 'ENTERPRISE'
    else:
        chosen_feature_package = ''
    if positive_value_exists(is_organization_plan) \
            and (chosen_feature_package == 'PROFESSIONAL' or chosen_feature_package == 'ENTERPRISE') \
            and positive_value_exists(organization_we_vote_id) \
            and (positive_value_exists(stripe_subscription_created)
                 or positive_value_exists(donation_plan_definition_already_exists)):
        # Switch the organization to this plan. This might be adjusted by the Stripe call backs
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if organization_results['organization_found']:
            organization = organization_results['organization']
            try:
                master_feature_package_query = MasterFeaturePackage.objects.all()
                master_feature_package_list = list(master_feature_package_query)
                for feature_package in master_feature_package_list:
                    if feature_package.master_feature_package == chosen_feature_package:
                        organization.features_provided_bitmap = feature_package.features_provided_bitmap
            except Exception as e:
                status += "UNABLE_TO_UPDATE_FEATURES_PROVIDED_BITMAP: " + str(e) + " "
            try:
                organization.chosen_feature_package = chosen_feature_package
                organization.save()
                organization_saved = True
                status += "ORGANIZATION_FEATURE_PACKAGE_SAVED "
            except Exception as e:
                organization_saved = False
                status += "ORGANIZATION_FEATURE_PACKAGE_NOT_SAVED: " + str(e) + " "

    results = {
        'status': status,
        'success': success,
        'amount_paid': donation_amount,
        'charge_id': charge_id,
        'customer_id': stripe_customer_id,
        'donation_entry_saved': donation_entry_saved,
        'error_message_for_voter': error_message,
        'monthly_donation': monthly_donation,
        'org_subs_already_exists': org_subs_already_exists,
        'organization_saved': organization_saved,
        'plan_type_enum': plan_type_enum,
        'saved_stripe_donation': saved_stripe_donation,
        'stripe_subscription_created': stripe_subscription_created,
        'subscription': subscription_saved,
    }

    return results


def is_voter_logged_in(request):
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        logger.error("invalid voter_device_id passed to is_voter_logged_in" + voter_device_id)
        return False
    voter = voter_results['voter']
    return voter.is_signed_in()


def translate_stripe_error_to_voter_explanation_text(donation_http_status, error_type):
    """

    :param donation_http_status:
    :param error_type:
    :return:
    """
    donation_manager = DonationManager()
    generic_voter_error_message = 'Your payment was unsuccessful. Please try again later.'

    if donation_http_status == 402:
        error_message_for_voter = donation_manager.retrieve_stripe_card_error_message(error_type)
    else:
        error_message_for_voter = generic_voter_error_message

    return error_message_for_voter


# Get a list of all prior donations by the voter that is associated with this voter_we_vote_id
# If they donated without logging in and then ended the session, they are out of luck for tracking past donations
def donation_journal_history_for_a_voter(voter_we_vote_id):
    """

    :param voter_we_vote_id:
    :return:
    """
    donation_manager = DonationManager()
    donation_journal_results = donation_manager.retrieve_donation_journal_list(voter_we_vote_id)
    refund_days = get_environment_variable("STRIPE_REFUND_DAYS")  # Should be 30, the num of days we will allow refunds

    simple_donation_list = []
    if donation_journal_results['success']:
        for donation_row in donation_journal_results['donation_journal_list']:
            json_data = {
                'donation_journal_id': donation_row.id,
                'created': str(donation_row.created),
                'amount': '{:20,.2f}'.format(donation_row.amount/100).strip(),
                'currency': donation_row.currency.upper(),
                'record_enum': donation_row.record_enum,
                'funding': donation_row.funding.title(),
                'brand': donation_row.brand,
                'exp_month': donation_row.exp_month,
                'exp_year': donation_row.exp_year,
                'last4': '{:04d}'.format(donation_row.last4),
                'stripe_status': donation_row.stripe_status,
                'charge_id': donation_row.charge_id,
                'plan_type_enum': donation_row.plan_type_enum,
                'subscription_id': donation_row.subscription_id,
                'subscription_canceled_at': str(donation_row.subscription_canceled_at),
                'subscription_ended_at': str(donation_row.subscription_ended_at),
                'refund_days_limit': refund_days,
                'last_charged': str(donation_row.last_charged),
                'is_organization_plan': positive_value_exists(donation_row.is_organization_plan),
                'organization_we_vote_id': str(donation_row.organization_we_vote_id),
            }
            simple_donation_list.append(json_data)

    return simple_donation_list


def donation_process_stripe_webhook_event(event):
    """
    NOTE: These are the only six events that we handle from the webhook
    :param event:
    :return:
    """
    logger.info("WEBHOOK received: donation_process_stripe_webhook_event: " + event.type)
    # write_event_to_local_file(event);

    if event['type'] == 'charge.succeeded':
        return donation_process_charge(event)
    elif event['type'] == 'customer.subscription.deleted':
        return donation_process_subscription_deleted(event)
    elif event['type'] == 'customer.subscription.updated':
        return donation_process_subscription_updated(event)
    elif event['type'] == 'invoice.payment_succeeded':
        return donation_process_subscription_payment(event)
    elif event['type'] == 'charge.refunded':
        return donation_process_refund_payment(event)
    elif event['type'] == 'invoice.created':
        return donation_process_invoice_created(event)

    logger.info("WEBHOOK ignored: donation_process_stripe_webhook_event: " + event.type)
    return


def write_event_to_local_file(event):
    target = open(event['type'] + "-" + str(datetime.now()) + ".txt", 'w')
    target.write(str(event))
    target.close()
    return


def donation_process_charge(event):           # 'charge.succeeded'
    """

    :param event:
    :return:
    """
    try:
        charge = event['data']['object']
        source = charge['source']
        outcome = charge['outcome']
        customer = charge['customer']
        results = DonationManager.does_donation_journal_charge_exist(charge['id'])

        # Handle stripe test urls with no customer
        if outcome is None:
            outcome = []

        if 'network_status' in outcome:
            network_status = outcome['network_status']
        else:
            network_status = ""
        if customer is None:
            customer = "none"
        else:
            customer = str(charge['customer'])
        if 'reason' in outcome:
            reason = outcome['reason']
        else:
            reason = 'none'
        if 'seller_message' in outcome:
            seller_message = outcome['seller_message']
        else:
            seller_message = 'none'

            # Charges from subscription payments, won't have our metadata
        try:
            voter_we_vote_id = charge['metadata']['voter_we_vote_id']
            if voter_we_vote_id:
                # Has our metadata?  Then we have already made a journal entry at the time of the donation
                logger.info("Stripe 'charge.succeeded' received for a PAYMENT_FROM_UI -- ignored, charge = " + charge)
                return
        except Exception:
            voter_we_vote_id = DonationManager.find_we_vote_voter_id_for_stripe_customer(customer)

        voter_manager = VoterManager()
        organization_we_vote_id = \
            voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(voter_we_vote_id)

        if results['success'] and not results['exists']:
            # Create the Journal entry for a payment initiated by an automatic subscription payment.
            metadata = charge['metadata']
            is_organization_plan = metadata['is_organization_plan'] if 'is_organization_plan' in metadata else False
            coupon_code = metadata['coupon_code'] if 'coupon_code' in metadata else ''
            plan_type_enum = metadata['plan_type_enum'] if 'plan_type_enum' in metadata else ''
            organization_we_vote_id = metadata['organization_we_vote_id'] if 'organization_we_vote_id' in metadata \
                else organization_we_vote_id

            journal = DonationManager.get_missing_charge_info(voter_we_vote_id, organization_we_vote_id,
                                                              charge['amount'])
            success = journal['success']
            status = ''
            subscription_id = journal['subscription_id'] if success else 'no'
            subscription_plan_id = journal['subscription_plan_id'] if success else ''
            is_organization_plan = journal['is_organization_plan'] if success else is_organization_plan
            plan_type_enum = journal['plan_type_enum'] if success else plan_type_enum
            coupon_code = journal['coupon_code'] if success else coupon_code

            # This is a long list of parameters, the line breaks in the parameters may look messy, but are purposeful
            DonationManager.create_donation_journal_entry(
                "PAYMENT_AUTO_SUBSCRIPTION", "0.0.0.0", customer,
                voter_we_vote_id, charge['id'], charge['amount'], charge['currency'], source['funding'],
                charge['livemode'], "",  "", datetime.fromtimestamp(charge['created'], timezone.utc),
                str(charge['failure_code']), str(charge['failure_message']), network_status, reason, seller_message,
                event['type'], charge['paid'], 0, charge['refunds']['total_count'],
                source['name'], source['address_zip'], source['brand'], source['country'],
                source['exp_month'], source['exp_year'], int(source['last4']), charge['source']['id'], event['id'],
                charge['status'], status, subscription_id, subscription_plan_id,
                None, None, None, None,
                is_organization_plan, coupon_code, plan_type_enum, organization_we_vote_id)
            logger.debug("Stripe subscription payment from webhook: " + str(charge['customer']) + ", amount: " +
                         str(charge['amount']) + ", last4:" + str(source['last4']))
            DonationManager.update_subscription_with_latest_charge_date(charge['invoice'], charge['created'])

    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        logger.error("donation_process_charge, Stripe: " + error_from_json)

    except Exception as err:
        logger.error("donation_process_charge, general: " + str(err))

    return


def donation_process_subscription_deleted(event):
    """

    :param event:
    :return:
    """
    donation_manager = DonationManager()
    data = event['data']
    subscription = data['object']
    subscription_ended_at = subscription['ended_at']
    subscription_canceled_at = subscription['canceled_at']
    customer_id = subscription['customer']
    subscription_id = subscription['id']

    # At this time we are only supporting the UI for canceling subscriptions
    if subscription_canceled_at is not None or subscription_ended_at is not None:
        donation_manager.mark_donation_journal_canceled_or_ended(subscription_id, customer_id, subscription_ended_at,
                                                                 subscription_canceled_at)
    return None


# Handle this event (in the same way for now) if it comes in from Stripe
def donation_process_subscription_updated(event):
    """

    :param event:
    :return:
    """
    return donation_process_subscription_deleted(event)


def move_donation_info_to_another_organization(from_organization_we_vote_id, to_organization_we_vote_id):
    status = "MOVE_DONATION_INFO_TO_ANOTHER_ORGANIZATION"
    success = True

    if not positive_value_exists(from_organization_we_vote_id) or not positive_value_exists(to_organization_we_vote_id):
        status += "MISSING_ORGANIZATION_WE_VOTE_ID "
        success = False

        results = {
            'status':                       status,
            'success':                      success,
            'from_organization_we_vote_id': from_organization_we_vote_id,
            'to_organization_we_vote_id':   to_organization_we_vote_id,
        }
        return results

    if from_organization_we_vote_id == to_organization_we_vote_id:
        status += "MOVE_DONATION_INFO-FROM_AND_TO_ORGANIZATION_WE_VOTE_IDS_IDENTICAL "
        success = False

        results = {
            'status':                       status,
            'success':                      success,
            'from_organization_we_vote_id': from_organization_we_vote_id,
            'to_organization_we_vote_id':   to_organization_we_vote_id,
        }
        return results

    # All we really need to do is find the donations that are associated with the "from" organization, and change their
    # organization_we_vote_id to the "to" organization.
    results = DonationManager.move_donation_journal_entries_from_organization_to_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += results['status']

    results = DonationManager.move_donation_plan_definition_entries_from_organization_to_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += results['status']

    results = {
        'status': status,
        'success': success,
        'from_organization_we_vote_id': from_organization_we_vote_id,
        'to_organization_we_vote_id': to_organization_we_vote_id,
    }
    return results


def move_donation_info_to_another_voter(from_voter, to_voter):
    """
    Within a session, if the voter donates before logging in, the donations will be created under a new unique
    voter_we_vote_id.  Subsequently when they login, their proper voter_we_vote_id will come into effect.  If we did not
    call this method before the end of the session, those "un-logged-in" donations would not be associated with the voter.
    Unfortunately at this time "un-logged-in" donations created in a session that was ended before logging in will not
    be associated with the correct voter -- we could do this in the future by doing something with email addresses.
    :param from_voter:
    :param to_voter:
    :return:
    """
    status = "MOVE_DONATION_INFO_TO_ANOTHER_VOTER "
    success = True

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status += textwrap.shorten("MOVE_DONATION_INFO_MISSING_FROM_OR_TO_VOTER_ID " + status, width=255,
                                  placeholder="...")

        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    if from_voter.we_vote_id == to_voter.we_vote_id:
        status += "MOVE_DONATION_INFO-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "

    # All we really need to do is find the donations that are associated with the "from" voter, and change their
    # voter_we_vote_id to the "to" voter.
    results = DonationManager.move_donation_journal_entries_from_voter_to_voter(from_voter, to_voter)
    status += results['status']

    donate_link_results = DonationManager.move_donate_link_to_voter_from_voter_to_voter(from_voter, to_voter)
    status += donate_link_results['status']

    donation_plan_results = \
        DonationManager.move_donation_plan_definition_entries_from_voter_to_voter(from_voter, to_voter)
    status += donation_plan_results['status']

    results = {
        'status': status,
        'success': success,
        'from_voter': from_voter,
        'to_voter': to_voter,
    }
    return results


# see https://stripe.com/docs/subscriptions/lifecycle
def donation_process_subscription_payment(event):
    dataobject = event['data']['object']
    amount = dataobject['amount_due']
    currency = dataobject['currency']
    customer_id = dataobject['customer']
    plan = dataobject['lines']['data'][0]['plan']
    plan_id = plan['id']

    row_id = DonationManager.check_for_subscription_in_db_without_card_info(customer_id, plan_id)
    if row_id == -1:
        print("Subscription card info is already in db for latest " + plan_id)
        return None

    try:
        customer = stripe.Customer.retrieve(customer_id)
        source = customer['sources']['data'][0]
        id_card = source['id']
        address_zip = source['address_zip']
        brand = source['brand']
        country = source['country']
        exp_month = source['exp_month']
        exp_year = source['exp_year']
        funding = source['funding']
        last4 = source['last4']

        DonationManager.update_subscription_in_db(row_id, amount, currency, id_card, address_zip, brand, country,
                                                  exp_month, exp_year, last4, funding)
    except Exception as err:
        logger.error("donation_process_subscription_payment: " + str(err))

    return None


def donation_process_refund_payment(event):
    # The Stripe webhook has sent a refund event "charge.refunded"
    success = False
    logger.debug("donation_process_refund_payment: " + json.dumps(event))
    dataobject = event['data']['object']
    charge = dataobject['id']
    paid = dataobject['paid']  # boolean
    if paid:
        success = DonationManager.update_journal_entry_for_refund_completed(charge)

    return success


def donation_process_invoice_created(event):
    """
    The only way to associate an incoming automatic payment for a subscription payment
    'invoice.payment_succeeded' is to cache the invoice id number and subscription id when the
    invoice created event arrives.  Then when the 'invoice.payment_succeeded' arrives a few seconds
    later, we can update the subscription 'last_charged' field since we will have cached the
    subscription id
    :param event: The Stripe event
    :return:
    """

    try:
        dataobject = event['data']['object']
        customer_id = dataobject['customer']
        plan = dataobject['lines']['data'][0]['plan']
        donation_plan_id = plan['id']
        subscription_id = dataobject['subscription']
        invoice_id = dataobject['id']
        invoice_date = datetime.fromtimestamp(dataobject['date'], timezone.utc)
        return DonationManager.update_donation_invoice(subscription_id, donation_plan_id, invoice_id,
                                                       invoice_date, customer_id)
    except Exception as e:
        logger.error("donation_process_invoice_created threw " + str(e))

    return


def donation_refund_for_api(request, charge, voter_we_vote_id):
    # The WebApp has requested a refund

    try:
        refund = stripe.Refund.create(
            charge=charge
        )
    except stripe.error.InvalidRequestError as err:
        body = err.json_body
        error_string = body['error']['message']
        logger.error("donation_refund_for_api: " + error_string)
        success = DonationManager.update_journal_entry_for_already_refunded(charge, voter_we_vote_id)
        return success

    except DonationManager.DoesNotExist as err:
        logger.error("donation_refund_for_api returned DoesNotExist for : " + charge)
        return False

    except Exception as err:
        logger.error("donation_refund_for_api: " + str(err))
        return False

    success = DonationManager.update_journal_entry_for_refund(charge, voter_we_vote_id, refund)

    return success


def donation_subscription_cancellation_for_api(voter_we_vote_id, plan_type_enum='', stripe_subscription_id=''):
    """
    We expect either plan_type_enum or stripe_subscription_id. If plan_type_enum is passed in, then
    stripe_subscription_id might be replaced with another value
    :param voter_we_vote_id:
    :param plan_type_enum:
    :param stripe_subscription_id:
    :return:
    """
    status = ''
    success = False
    donation_plan_definition_id = 0
    stripe_customer_id = ''
    canceled_at = ''
    ended_at = ''
    email = ''
    voter_we_vote_id_from_subscription = ''
    livemode = ''
    organization_saved = False

    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id)
    if not voter_results['voter_found']:
        status += voter_results['status']
        json_returned = {
            'status': status,
            'active_paid_plan': {},
            'subscription_id': stripe_subscription_id,
            'customer_id': '',
            'canceled_at': '',
            'ended_at': '',
            'email': '',
            'voter_we_vote_id': voter_we_vote_id,
            'donation_plan_definition_list': [],
            'livemode': '',
            'donation_list': [],
            'success': False,
        }
        return json_returned

    voter = voter_results['voter']
    linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    donation_manager = DonationManager()
    if positive_value_exists(plan_type_enum):
        results = donation_manager.retrieve_donation_plan_definition(
            organization_we_vote_id=linked_organization_we_vote_id, is_organization_plan=True,
            plan_type_enum=plan_type_enum, donation_plan_is_active=True)
        if results['donation_plan_definition_found']:
            donation_plan_definition = results['donation_plan_definition']
            donation_plan_definition_id = donation_plan_definition.id
            if positive_value_exists(donation_plan_definition.stripe_subscription_id):
                stripe_subscription_id = donation_plan_definition.stripe_subscription_id
            elif not donation_plan_definition.paid_without_stripe:
                # Reach out to Stripe to match existing subscription
                subscription_list_results = stripe.Subscription.list(limit=10)
                if 'data' in subscription_list_results and len(subscription_list_results['data']):
                    for one_subscription in subscription_list_results['data']:
                        if 'plan' in one_subscription and 'id' in one_subscription['plan']:
                            if one_subscription['plan']['id'] == donation_plan_definition.donation_plan_id:
                                stripe_subscription_id = one_subscription['id']
                                donation_plan_definition.stripe_subscription_id = one_subscription['id']
                                donation_plan_definition.save()
                                break

    if positive_value_exists(stripe_subscription_id):
        # Make sure this voter has the right to cancel this subscription_id
        try:
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            stripe_customer_id = subscription['customer']
            canceled_at = subscription['canceled_at']
            ended_at = subscription['ended_at']
            if 'email' in subscription['metadata']:
                email_raw = subscription['metadata']['email']
                if type(email_raw) == str:
                    email = email_raw
                elif type(email_raw) == tuple:
                    email = email_raw[0],
            if 'voter_we_vote_id' in subscription['metadata']:
                voter_we_vote_id_raw = subscription['metadata']['voter_we_vote_id']
                if type(voter_we_vote_id_raw) == str:
                    voter_we_vote_id_from_subscription = voter_we_vote_id_raw
                elif type(voter_we_vote_id_raw) == tuple:
                    voter_we_vote_id_from_subscription = voter_we_vote_id_raw[0],
            livemode = subscription['livemode']

            if not positive_value_exists(canceled_at):
                results = subscription.delete()
                status += "STRIPE_SUBSCRIPTION_DELETED "
                status += results['status']
                canceled_at = results['canceled_at']
                ended_at = results['ended_at']
            else:
                status += "STRIPE_SUBSCRIPTION_PREVIOUSLY_DELETED "
        except Exception as e:
            logger.error("donation_subscription_cancellation_for_api err " + str(e))
            status += "DONATION_SUBSCRIPTION_CANCELLATION err:" + str(e) + " "
            success = False

        try:
            results = donation_manager.mark_donation_journal_canceled_or_ended(
                stripe_subscription_id, stripe_customer_id, ended_at, canceled_at)
            status += results['status']

            results = donation_manager.mark_donation_plan_definition_canceled(
                donation_plan_definition_id=donation_plan_definition_id, stripe_subscription_id=stripe_subscription_id)
            status += results['status']
        except Exception as e:
            logger.error("MARK_JOURNAL_OR_DONATION_PLAN_DEFINITION err " + str(e))
            status += "DONATION_SUBSCRIPTION_CANCELLATION err:" + str(e) + " "
            success = False

    active_results = donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id)
    active_paid_plan = active_results['active_paid_plan']
    donation_plan_definition_list_json = active_results['donation_plan_definition_list_json']

    # Switch the organization to this plan. This might be adjusted by the Stripe call backs
    organization_manager = OrganizationManager()
    organization_results = organization_manager.retrieve_organization_from_we_vote_id(linked_organization_we_vote_id)
    if organization_results['organization_found']:
        organization = organization_results['organization']
        chosen_feature_package = "FREE"
        try:
            master_feature_package_query = MasterFeaturePackage.objects.all()
            master_feature_package_list = list(master_feature_package_query)
            for feature_package in master_feature_package_list:
                if feature_package.master_feature_package == chosen_feature_package:
                    organization.features_provided_bitmap = feature_package.features_provided_bitmap
        except Exception as e:
            status += "UNABLE_TO_UPDATE_FEATURES_PROVIDED_BITMAP: " + str(e) + " "
        try:
            organization.chosen_feature_package = chosen_feature_package
            organization.save()
            organization_saved = True
            status += "ORGANIZATION_FEATURE_PACKAGE_SAVED "
        except Exception as e:
            organization_saved = False
            status += "ORGANIZATION_FEATURE_PACKAGE_NOT_SAVED: " + str(e) + " "

    json_returned = {
        'status':           status,
        'success':          success,
        'subscription_id':  stripe_subscription_id,
        'active_paid_plan': active_paid_plan,
        'customer_id':      stripe_customer_id,
        'canceled_at':      canceled_at,
        'ended_at':         ended_at,
        'email':            email,
        'voter_we_vote_id': voter_we_vote_id_from_subscription
        if positive_value_exists(voter_we_vote_id_from_subscription)
        else voter_we_vote_id,
        'livemode':         livemode,
        'organization_saved': organization_saved,
        'donation_list':    donation_journal_history_for_a_voter(voter_we_vote_id),
        'donation_plan_definition_list':   donation_plan_definition_list_json,
    }
    return json_returned
