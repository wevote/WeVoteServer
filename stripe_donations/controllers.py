# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

import json
import textwrap
import time
from datetime import datetime, timezone

import pytz
import stripe

from campaign.models import CampaignXManager
from config.base import get_environment_variable, get_environment_variable_default
from stripe_donations.models import StripeManager, StripeDispute
from voter.models import VoterManager
from wevote_functions.admin import get_logger
from wevote_functions.functions import convert_pennies_integer_to_dollars_string, get_voter_device_id
from wevote_functions.functions import positive_value_exists

logger = get_logger(__name__)
stripe.api_key = get_environment_variable_default("STRIPE_SECRET_KEY", "")

# November 2023, probably won't be using Stripe in the future
# if len(stripe.api_key) and not stripe.api_key.startswith("sk_"):
#     logger.error("Configuration error, the stripe secret key, must begin with 'sk_' -- don't use the publishable key "
#                  "on the server!")


def donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id):
    status = ''
    active_paid_plan_found = False
    subscription_list = []
    subscription_list_json = []
    coupon_code = ''
    we_plan_id = ''
    premium_plan_type_enum = ''
    stripe_customer_id = ''
    stripe_subscription_id = False
    next_invoice_retrieved = False
    last_amount_paid = 0
    subscription_active = ''
    subscription_canceled_at = ''
    subscription_ended_at = ''
    subscription_found = False

    donation_manager = StripeManager()
    if positive_value_exists(linked_organization_we_vote_id):
        plan_results = donation_manager.retrieve_subscription_list(
            linked_organization_we_vote_id=linked_organization_we_vote_id, return_json_version=True)
        subscription_list = plan_results['subscription_list']
        subscription_list_json = plan_results['subscription_list_json']
    elif positive_value_exists(voter_we_vote_id):
        plan_results = donation_manager.retrieve_subscription_list(
            voter_we_vote_id=voter_we_vote_id, return_json_version=True)
        subscription_list = plan_results['subscription_list']
        subscription_list_json = plan_results['subscription_list_json']

    status += "SUCCESSFULLY_RETRIEVED_DONATION_HISTORY "
    success = True

    for donation_plan_definition in subscription_list:
        # if positive_value_exists(donation_plan_definition.is_premium_plan):
        if positive_value_exists(donation_plan_definition.donation_plan_is_active):
            active_paid_plan_found = True
            donation_plan_definition_id = donation_plan_definition.id
            # premium_plan_type_enum = donation_plan_definition.premium_plan_type_enum
            # coupon_code = donation_plan_definition.coupon_code
            we_plan_id = donation_plan_definition.we_plan_id
            stripe_customer_id = donation_plan_definition.stripe_customer_id
            stripe_subscription_id = donation_plan_definition.stripe_subscription_id
            if not positive_value_exists(stripe_subscription_id):
                # Reach out to Stripe to match existing subscription
                subscription_list_results = stripe.Subscription.list(limit=10)
                if 'data' in subscription_list_results and len(subscription_list_results['data']):
                    for one_subscription in subscription_list_results['data']:
                        if 'plan' in one_subscription and 'id' in one_subscription['plan']:
                            if one_subscription['plan']['id'] == donation_plan_definition.we_plan_id:
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
        # 'coupon_code':              coupon_code,
        'we_plan_id':               we_plan_id,
        'next_invoice':             next_invoice,
        'premium_plan_type_enum':   premium_plan_type_enum,
        'stripe_subscription_id':   stripe_subscription_id,
        'subscription_active':      active_paid_plan_found,
        # 'subscription_canceled_at': subscription_canceled_at,
        # 'subscription_ended_at':    subscription_ended_at,
    }
    results = {
        'status': status,
        'success': success,
        'active_paid_plan': active_paid_plan,
        'subscription_list_json':   subscription_list_json,
    }
    return results


def donation_with_stripe_for_api(request, token, email, donation_amount,
                                 is_chip_in, is_monthly_donation, is_premium_plan,
                                 client_ip, campaignx_we_vote_id, payment_method_id, coupon_code,
                                 premium_plan_type_enum,
                                 voter_we_vote_id, linked_organization_we_vote_id):
    """
    Initiate a donation or organization subscription plan using the Stripe Payment API, and record details in our DB
    :param request:
    :param token: The Stripe token.id for the card and transaction
    :param email:
    :param donation_amount:  the amount of the donation, but not used for organization subscriptions
    :param is_chip_in: (boolean) is this a "Chip in" to a Campaign donation
    :param is_monthly_donation: (boolean) is this a monthly donation subscription
    :param is_premium_plan:  True for a premium organization plan, False for a donation (one time or donation subs.)
    :param client_ip: As reported by Stripe (i.e. outside looking in)
    :param campaignx_we_vote_id: To track Campaign "Chip In"s
    :param payment_method_id: payment method selected/created on the client CheckoutForm.jsx
    :param coupon_code: Our coupon codes for pricing and features that are looked up
           in the OrganizationSubscriptionPlans
    :param premium_plan_type_enum: Type of premium organization plan, or undefined for donations
    :param voter_we_vote_id:
    :param linked_organization_we_vote_id: The organization that benefits from this paid plan (subscription)
    :return:
    """

    donation_manager = StripeManager()
    results = {
        'status': '',
        'success': False,
        'amount_paid': donation_amount,
        'charge_id': '',
        'stripe_customer_id': '',
        'donation_entry_saved': False,
        'error_message_for_voter': '',
        'stripe_failure_code': '',
        'is_chip_in': is_chip_in,
        'is_monthly_donation': is_monthly_donation,
        'is_premium_plan': is_premium_plan,
        'subscription_already_exists': False,
        'org_subs_already_exists': False,
        'organization_saved': False,
        'premium_plan_type_enum': premium_plan_type_enum,
        'saved_stripe_donation': '',
        'stripe_subscription_created': False,
        'subscription_saved': 'NOT_APPLICABLE',
    }

    charge, not_loggedin_voter_we_vote_id = None, None
    donation_date_time = datetime.today()
    raw_donation_status = ''
    is_signed_in = is_voter_logged_in(request)

    if is_premium_plan:
        results['amount_paid'] = 0

    if not positive_value_exists(voter_we_vote_id):
        results['status'] += "DONATION_WITH_STRIPE_VOTER_WE_VOTE_ID_MISSING "
        return results

    if not positive_value_exists(email) and not is_premium_plan:
        results['status'] += "DONATION_WITH_STRIPE_EMAIL_MISSING "
        results['error_message_for_voter'] = 'An email address is required by our payment processor.'
        return results

    # Use a default coupon_code if none is specified
    if is_premium_plan:
        if len(coupon_code) < 2:
            coupon_code = 'DEFAULT-' + results['premium_plan_type_enum']
    else:
        coupon_code = ''

    # If is_premium_plan, set the price from the coupon, not whatever was passed in.
    if is_premium_plan:
        increment_redemption_cnt = False
        coupon_price, org_subs_id = StripeManager.get_coupon_price(results['premium_plan_type_enum'], coupon_code,
                                                                   increment_redemption_cnt)
        if int(donation_amount) > 0:
            print("Warning for developers, the donation_amount that is passed in for premium organization plans is ignored,"
                  " the value is read from the coupon")
        donation_amount = coupon_price

    try:
        dm_results = donation_manager.retrieve_stripe_customer_id_from_donate_link_to_voter(voter_we_vote_id)
        if dm_results['success']:
            results['stripe_customer_id'] = dm_results['stripe_customer_id']
            results['status'] += "STRIPE_CUSTOMER_ID_ALREADY_EXISTS "
        else:
            customer = stripe.Customer.create(
                source=token,
                email=email
            )
            results['stripe_customer_id'] = customer.stripe_id
            saved_results = donation_manager.create_donate_link_to_voter(customer.stripe_id, voter_we_vote_id)
            results['status'] += saved_results['status']

        if not positive_value_exists(results['stripe_customer_id']):
            results['status'] += "STRIPE_CUSTOMER_ID_MISSING "
        else:
            # if positive_value_exists(is_premium_plan):
            #     # If here, we are processing organization subscription
            #     results['status'] += 'DONATION_SUBSCRIPTION_SETUP '
            #     if "MONTHLY" in results['premium_plan_type_enum']:
            #         recurring_interval = 'month'
            #     elif "YEARLY" in results['premium_plan_type_enum']:
            #         recurring_interval = 'year'
            #     else:
            #         recurring_interval = 'year'
            #     subscription_results = donation_manager.create_organization_subscription(
            #         results['stripe_customer_id'], voter_we_vote_id, donation_amount, donation_date_time,
            #         email, coupon_code, results['premium_plan_type_enum'], linked_organization_we_vote_id,
            #         recurring_interval)
            #
            #     donation_plan_definition_already_exists = \
            #         subscription_results['donation_plan_definition_already_exists']
            #     results['stripe_subscription_created'] = subscription_results['stripe_subscription_created']
            #     if donation_plan_definition_already_exists:
            #         results['charge_id'] = ''
            #     else:
            #         results['status'] += textwrap.shorten(subscription_results['status'] + " " + results['status'],
            #                                               width=255, placeholder="...")
            #         results['success'] = subscription_results['success']
            #         create_subscription_entry = True
            #         stripe_subscription_id = subscription_results['stripe_subscription_id']
            #         subscription_plan_id = subscription_results['subscription_plan_id']
            #         subscription_created_at = None
            #         if type(subscription_results['subscription_created_at']) is int:
            #             subscription_created_at = datetime.fromtimestamp(
            #                 subscription_results['subscription_created_at'],
            #                 timezone.utc)
            #         created = subscription_created_at
            #         subscription_canceled_at = None
            #         subscription_ended_at = None
            # else:
            # If here, we are processing a donation subscription or Campaign membership
            if positive_value_exists(is_monthly_donation):
                results['status'] += 'DONATION_SUBSCRIPTION_SETUP '
                # The Stripe API calls are made within the following function call
                recurring_donation_results = donation_manager.create_recurring_donation(
                    results['stripe_customer_id'], voter_we_vote_id,
                    donation_amount, donation_date_time,
                    email, is_premium_plan,
                    coupon_code, results['premium_plan_type_enum'],
                    linked_organization_we_vote_id, client_ip, payment_method_id, is_signed_in)

                results['subscription_already_exists'] = recurring_donation_results['subscription_already_exists']
                results['stripe_subscription_created'] = recurring_donation_results['stripe_subscription_created']
                results['stripe_subscription_id'] = recurring_donation_results['stripe_subscription_id']
                stripe_subscription_success = recurring_donation_results['success']

                if not stripe_subscription_success:
                    results['subscription_saved'] = 'NOT_SAVED'
                    results['status'] += textwrap.shorten(recurring_donation_results['status'] +
                                                          " " + results['status'], width=255, placeholder="...")
                    results['success'] = stripe_subscription_success
                    results['error_message_for_voter'] = recurring_donation_results['error_message']
                    results['stripe_failure_code'] = recurring_donation_results['code']
                    results['amount_paid'] = 0
                    return results
                elif results['subscription_already_exists']:
                    results['charge_id'] = ''
                else:
                    results['subscription_saved'] = recurring_donation_results['voter_subscription_saved']
                    results['status'] += textwrap.shorten(recurring_donation_results['status'] +
                                                          " " + results['status'], width=255, placeholder="...")
                    results['success'] = recurring_donation_results['success']
                    create_subscription_entry = True
                    stripe_subscription_id = recurring_donation_results['stripe_subscription_id']
                    subscription_plan_id = recurring_donation_results['subscription_plan_id']
                    subscription_created_at = None
                    if type(recurring_donation_results['subscription_created_at']) is int:
                        subscription_created_at = \
                            datetime.fromtimestamp(recurring_donation_results['subscription_created_at'],
                                                   timezone.utc)
            else:  # One time charge
                charge = stripe.Charge.create(
                    amount=donation_amount,
                    currency="usd",
                    source=token,
                    metadata={
                        'email': email,
                        # 'one_time_donation': True,
                        'linked_organization_we_vote_id': linked_organization_we_vote_id,
                        'premium_plan_type_enum': results['premium_plan_type_enum'],
                        'voter_we_vote_id': voter_we_vote_id,
                        'coupon_code': coupon_code,
                        'stripe_customer_id': dm_results['stripe_customer_id'],
                        'is_chip_in': is_chip_in,
                        'is_monthly_donation': is_monthly_donation,
                        'is_premium_plan': is_premium_plan,
                        'campaignx_we_vote_id': campaignx_we_vote_id,
                    }
                )
                results['status'] += textwrap.shorten("STRIPE_CHARGE_SUCCESSFUL " + results['status'], width=255,
                                                      placeholder="...")
                results['charge_id'] = charge.id
                results['success'] = positive_value_exists(charge.id)

        if positive_value_exists(charge) and positive_value_exists(charge.id):
            results['saved_stripe_donation'] = True
            results['status'] += ' DONATION_PROCESSED_SUCCESSFULLY '
            results['stripe_failure_code'] = ''       # Do this to clear the flux store of any prior errors
            results['error_message_for_voter'] = ''
            amount = charge['amount']
            logger.debug("donation_with_stripe_for_api - charge successful: " + charge.id + ", amount: " + str(amount) + ", voter_we_vote_id:" +
                         voter_we_vote_id)

    except stripe.error.CardError as e:
        body = e.json_body
        error_from_json = body['error']
        raw_donation_status += " STRIPE_STATUS_IS: {http_status} STRIPE_CARD_ERROR_IS: {error_type} " \
                               "STRIPE_MESSAGE_IS: {error_message} " \
                               "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                         error_message=error_from_json['message'])
        results['status'] += textwrap.shorten(raw_donation_status + " " + results['status'], width=255,
                                              placeholder="...")
        results['stripe_failure_code'] = e.code
        results['error_message_for_voter'] = error_from_json['message']
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("DONATION donation_with_stripe_for_api, CardError: " + error_message)
    # except KeyError as e:   (July 2021: Only received this once, on a test card with a decline for cvc)
    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        raw_donation_status += " STRIPE_STATUS_IS: {http_status} STRIPE_ERROR_IS: {error_type} " \
                               "STRIPE_MESSAGE_IS: {error_message} " \
                               "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                         error_message=error_from_json['message'])
        results['status'] += textwrap.shorten(raw_donation_status + " " + results['status'], width=255,
                                              placeholder="...")
        try:
            results['stripe_failure_code'] = e.code
            results['error_message_for_voter'] = error_from_json['message']
        except Exception as e:
            # Don't know how to reproduce this, so just in case the error codes don't exist ....
            pass
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("DONATION donation_with_stripe_for_api, StripeError : " + raw_donation_status)
    except Exception as err:
        # Something else happened, completely unrelated to Stripe
        logger.error("DONATION donation_with_stripe_for_api caught: ", err)
        raw_donation_status += "A_NON_STRIPE_ERROR_OCCURRED "
        logger.error("DONATION donation_with_stripe_for_api threw " + str(err))
        results['status'] += textwrap.shorten(raw_donation_status + " " + results['status'], width=255,
                                              placeholder="...")
        error_message = 'Your payment was unsuccessful. Please try again later.'
    if "already has the maximum 25 current subscriptions" in results['status']:
        error_message = \
            "No more than 25 active subscriptions are allowed, please delete a subscription before adding another."
        logger.debug("donation_with_stripe_for_api: " + error_message)

    # action_result should be CANCEL_REQUEST_FAILED, CANCEL_REQUEST_SUCCEEDED, DONATION_PROCESSED_SUCCESSFULLY,
    #    STRIPE_DONATION_NOT_COMPLETED, DONATION_SUBSCRIPTION_SETUP
    # action_result = raw_donation_status

    # print("is_voter_logged_in() = " + str(is_signed_in))
    if not is_signed_in:
        results['not_loggedin_voter_we_vote_id'] = voter_we_vote_id

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
        logger.error("DONATION invalid voter_device_id passed to is_voter_logged_in" + voter_device_id)
        return False
    voter = voter_results['voter']
    return voter.is_signed_in()


def translate_stripe_error_to_voter_explanation_text(donation_http_status, error_type):
    """

    :param donation_http_status:
    :param error_type:
    :return:
    """
    donation_manager = StripeManager()
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
    donation_manager = StripeManager()
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
                'premium_plan_type_enum': donation_row.premium_plan_type_enum,
                'stripe_subscription_id': donation_row.stripe_subscription_id,
                'subscription_canceled_at': str(donation_row.subscription_canceled_at),
                'subscription_ended_at': str(donation_row.subscription_ended_at),
                'refund_days_limit': refund_days,
                'last_charged': str(donation_row.last_charged),
                'is_premium_plan': positive_value_exists(donation_row.is_premium_plan),
                'linked_organization_we_vote_id': str(donation_row.linked_organization_we_vote_id),
            }
            simple_donation_list.append(json_data)

    return simple_donation_list


# Get a list of all prior donations by the voter that is associated with this voter_we_vote_id
# If they donated without logging in and then ended the session, they are out of luck for tracking past donations
def donation_lists_for_a_voter(voter_we_vote_id):
    """

    :param voter_we_vote_id:
    :return:
    """
    donation_manager = StripeManager()
    refund_days = get_environment_variable("STRIPE_REFUND_DAYS")  # Should be 30, the num of days we will allow refunds
    donation_payments = donation_manager.retrieve_donation_payment_list(voter_we_vote_id)

    donation_payments_list = []
    if donation_payments['success']:
        for payment_row in donation_payments['payment_list']:
            json_data = {
                'payment_id': payment_row.id,
                'created': str(payment_row.created),
                'amount': '{:20,.2f}'.format(payment_row.amount/100).strip(),
                'currency': payment_row.currency.upper(),
                'record_enum': payment_row.record_enum,
                'funding': payment_row.funding.title(),
                'brand': payment_row.brand,
                'exp_month': payment_row.exp_month,
                'exp_year': payment_row.exp_year,
                'last4': '{:04d}'.format(payment_row.last4),
                'stripe_status': payment_row.stripe_status,
                'charge_id': payment_row.stripe_charge_id,
                # 'premium_plan_type_enum': payment_row.premium_plan_type_enum,
                'stripe_subscription_id': payment_row.stripe_subscription_id,
                'refund_days_limit': refund_days,
                'last_charged': str(payment_row.paid_at),
                'is_chip_in': payment_row.is_chip_in,
                'is_monthly_donation': payment_row.is_monthly_donation,
                'is_premium_plan': payment_row.is_premium_plan,
                'campaignx_we_vote_id': payment_row.campaignx_we_vote_id,
                'campaign_title': CampaignXManager.retrieve_campaignx_title(payment_row.campaignx_we_vote_id),
                'voter_we_vote_id': payment_row.voter_we_vote_id,

                # 'is_premium_plan': positive_value_exists(payment_row.is_premium_plan),
                # 'linked_organization_we_vote_id': str(payment_row.linked_organization_we_vote_id),
            }
            donation_payments_list.append(json_data)

    donation_subscriptions = donation_manager.retrieve_donation_subscription_list(voter_we_vote_id)
    donation_subscription_list = []
    if donation_subscriptions['success']:
        for subscription_row in donation_subscriptions['subscription_list']:
            payment_struct = donation_manager.retrieve_payment_for_charge(subscription_row.stripe_charge_id)
            payment = payment_struct['payment']
            json_data = {
                'subscription_id': subscription_row.id,
                'subscription_created_at': str(subscription_row.subscription_created_at),
                'amount': '{:20,.2f}'.format(subscription_row.amount/100).strip(),
                'currency': subscription_row.currency,
                # 'record_enum': subscription_row.record_enum,
                # 'funding': subscription_row.funding,
                'brand': payment.brand if payment else '',
                'exp_month': payment.exp_month if payment else '',
                'exp_year': payment.exp_year if payment else '',
                'last4': '{:04d}'.format(payment.last4) if payment else '',
                'stripe_status': payment.stripe_status if payment else '',
                'charge_id': subscription_row.stripe_charge_id,
                # 'premium_plan_type_enum': subscription_row.premium_plan_type_enum,
                'stripe_subscription_id': subscription_row.stripe_subscription_id,
                'subscription_canceled_at': str(subscription_row.subscription_canceled_at),
                'subscription_ended_at': str(subscription_row.subscription_ended_at),
                'refund_days_limit': refund_days,
                'last_charged': str(payment.paid_at) if payment else '',
                # 'is_premium_plan': positive_value_exists(subscription_row.is_premium_plan),
                # 'linked_organization_we_vote_id': str(subscription_row.linked_organization_we_vote_id),
            }
            donation_subscription_list.append(json_data)

    return donation_subscription_list, donation_payments_list


def donation_process_stripe_webhook_event(event):  # donationStripeWebhook
    """
    NOTE: These are the only six events that we handle from the webhook
    :param event:
    :return:
    """
    etype = event.type
    api_version = event.api_version
    logger.error("DONATION WEBHOOK received: donation_process_stripe_webhook_event: " + etype)
    # print("WEBHOOK received: donation_process_stripe_webhook_event: " + etype)
    # write_event_to_local_file(event)      # for debugging

    if etype == 'charge.succeeded':
        return donation_process_charge(event)
    elif etype == 'customer.subscription.deleted':
        return donation_process_subscription_deleted(event)
    elif etype == 'customer.subscription.updated':
        return donation_process_subscription_updated(event)
    elif etype == 'invoice.payment_succeeded':
        return donation_process_subscription_payment(event)
    elif etype == 'charge.refunded':
        return donation_process_refund_payment(event)
    elif event['type'] == 'charge.dispute.created' or 'charge.dispute.funds_withdrawn':
        return donation_process_dispute(event)

    print("WEBHOOK ignored: donation_process_stripe_webhook_event: " + event['type'])
    logger.error("DONATION WEBHOOK ignored: donation_process_stripe_webhook_event: " + event['type'])
    return


def write_event_to_local_file(event):
    target = open(event['type'] + "-" + str(datetime.now()) + ".txt", 'w')
    target.write(str(event))
    target.close()
    return


def donation_process_charge(event):           # 'charge.succeeded' webhook
    """
    :param event:
    :return:
    """

    try:
        # print('first line in stripe_donation donation_process_charge')
        # is_one_time_donation = True if 'one_time_donation' in metadata else False
        # print('donation_process_charge # charge.succeeded ... is_one_time_donation:', is_one_time_donation)

        charge = event['data']['object']
        description = charge['description']
        if description == "Subscription creation":
            return donation_update_subscription_with_charge_info(event)

        metadata = charge['metadata']
        source = charge['source']
        outcome = charge['outcome']
        customer = charge['customer']
        data = event['data']
        stripe_object = data['object']

        is_signed_in = False
        voter_we_vote_id = ''
        not_loggedin_voter_we_vote_id = ''
        if 'voter_we_vote_id' in metadata:
            voter_manager = VoterManager()
            results = voter_manager.retrieve_voter_by_we_vote_id(metadata['voter_we_vote_id'])
            if results['voter_found']:
                voter = results['voter']
                is_signed_in = voter.is_signed_in()
            if is_signed_in:
                voter_we_vote_id = metadata['voter_we_vote_id']
            else:
                not_loggedin_voter_we_vote_id = metadata['voter_we_vote_id']

        # if both not_loggedin_voter_we_vote_id and voter_we_vote_id are '', then fraud is likely

        payment = {
            'address_zip': source['address_zip'],
            'amount': charge['amount'],
            'amount_refunded': charge['amount_refunded'],
            'api_version': event['api_version'],
            'brand': source['brand'],
            'campaignx_we_vote_id': metadata['campaignx_we_vote_id'] if 'campaignx_we_vote_id' in metadata else '',
            'country': source['country'],
            'created': datetime.fromtimestamp(event['created'], timezone.utc),
            'currency': charge['currency'],
            'email': metadata['email'] if 'email' in metadata else '',
            'exp_month': source['exp_month'],
            'exp_year': source['exp_year'],
            'failure_code': charge['failure_code'],
            'failure_message': charge['failure_message'],
            'funding': source['funding'],
            'ip_address': '0.0.0.0',                # Need a change on the other side!
            'is_chip_in': metadata['is_chip_in'] if 'is_chip_in' in metadata else '',
            'is_monthly_donation': metadata['is_monthly_donation'] if 'is_monthly_donation' in metadata else '',
            'is_paid': charge['paid'],
            'is_premium_plan': metadata['is_premium_plan'] if 'is_premium_plan' in metadata else '',
            'is_refunded': charge['refunded'],
            'last4': source['last4'],
            'livemode': charge['livemode'],
            'network_status': outcome['network_status'],
            'not_loggedin_voter_we_vote_id': not_loggedin_voter_we_vote_id,
            'paid_at': datetime.fromtimestamp(charge['created'], timezone.utc),
            'reason': outcome['reason'],
            'seller_message': outcome['seller_message'],
            'source_obj': source['object'],
            'status': stripe_object['calculated_statement_descriptor'],
            'stripe_card_id': charge['payment_method'],
            'stripe_charge_id': charge['id'],
            'stripe_customer_id': metadata['stripe_customer_id'] if 'stripe_customer_id' in metadata else '',
            'stripe_request_id': event['request']['id'],
            'stripe_status': charge['status'],
            'stripe_type': stripe_object['object'],
            'voter_we_vote_id': voter_we_vote_id,
            'billing_reason': event['type'],     # for one time payments or chipins
            # 'one_time_donation': metadata['one_time_donation'] if 'one_time_donation' in metadata else '',
            # 'linked_organization_we_vote_id': metadata['linked_organization_we_vote_id'] if 'linked_organization_we_vote_id' in metadata else '',
            # 'premium_plan_type_enum': metadata['premium_plan_type_enum'] if 'premium_plan_type_enum' in metadata else '',
            # 'coupon_code': metadata['coupon_code'] if 'coupon_code' in metadata else '',
        }

        if description is not None:
            is_new, donation_plan_query = StripeManager.stripe_subscription_create_or_update(payment)
        else:
            StripeManager.stripe_payment_create_or_update(payment)

        # StripeManager.create_payment_entry(payment)
        logger.error("DONATION Stripe subscription payment PROCESSED from webhook: " + str(charge['customer']) + ", amount: " +
                     str(charge['amount']) + ", last4:" + str(source['last4']))

    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        logger.error("DONATION donation_process_charge, Stripe: " + error_from_json)

    except Exception as err:
        logger.error("DONATION donation_process_charge, general: " + str(err))

    return


def donation_update_subscription_with_charge_info(event):
    """
     :param event:
     :return:
     """

    try:
        # print('first line in stripe_donation donation_update_subscription_with_charge_info')
        charge = event['data']['object']
        billing_details = charge['billing_details']
        address = billing_details['address']
        outcome = charge['outcome']
        data = event['data']
        stripe_object = data['object']
        payment_method_details = charge['payment_method_details']
        card = payment_method_details['card']
        charge_data = {
            'address_zip': address['postal_code'],
            'amount': charge['amount'],
            'amount_refunded': charge['amount_refunded'],
            'brand': card['brand'],
            'country': card['country'],
            'created': datetime.fromtimestamp(charge['created'], timezone.utc),
            'exp_month': card['exp_month'],
            'exp_year': card['exp_year'],
            'failure_code': charge['failure_code'],
            'failure_message': charge['failure_message'],
            'funding': card['funding'],
            'is_paid': charge['paid'],
            'is_refunded': charge['refunded'],
            'last4': card['last4'],
            'livemode': charge['livemode'],
            'network_status': outcome['network_status'],
            'reason': outcome['reason'],
            'seller_message': outcome['seller_message'],
            'status': stripe_object['calculated_statement_descriptor'],
            'stripe_card_id': charge['payment_method'],
            'stripe_charge_id': charge['id'],
            'stripe_status': charge['status'],
            'billing_reason': event['type'],
        }

        StripeManager.update_subscription_and_payment_on_charge_success(charge_data)

    except Exception as err:
        logger.error("DONATION donation_update_subscription_with_charge_info, error: " + str(err))

    return


def donation_process_subscription_deleted(event):
    """

    :param event:
    :return:
    """
    donation_manager = StripeManager()
    data = event['data']
    subscription = data['object']
    subscription_ended_at = subscription['ended_at']
    subscription_canceled_at = subscription['canceled_at']
    customer_id = subscription['customer']
    stripe_subscription_id = subscription['id']

    # At this time we are only supporting the UI for canceling subscriptions
    if subscription_canceled_at is not None or subscription_ended_at is not None:
        donation_manager.mark_donation_journal_canceled_or_ended(
            stripe_subscription_id, customer_id, subscription_ended_at, subscription_canceled_at)
    return None


# Handle this event (in the same way for now) if it comes in from Stripe
def donation_process_subscription_updated(event):
    """

    :param event:
    :return:
    """
    return donation_process_subscription_deleted(event)


def move_donation_info_to_another_organization(from_organization_we_vote_id, to_organization_we_vote_id):
    status = "MOVE_DONATION_INFO_TO_ANOTHER_ORGANIZATION "
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

    # All we really need to do is find the donation payments that are associated with the "from" organization, and
    # change their organization_we_vote_id to the "to" organization.
    results = StripeManager.move_stripe_donation_payments_from_organization_to_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += results['status']

    results = StripeManager.move_subscription_entries_from_organization_to_organization(
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
    voter_we_vote_id.  Subsequently, when they login, their proper voter_we_vote_id will come into effect.
    If we did not
    call this method before the end of the session, those "un-logged-in" donations would not be associated with the
    voter.
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
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    if from_voter.we_vote_id == to_voter.we_vote_id:
        status += "MOVE_DONATION_INFO-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "
        success = False
        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    # All we really need to do is find the donations that are associated with the "from" voter, and change their
    # voter_we_vote_id to the "to" voter.
    results = StripeManager.move_donation_payment_entries_from_voter_to_voter(from_voter, to_voter)
    status += results['status']
    if not results['success']:
        success = False

    donate_link_results = StripeManager.move_donate_link_to_voter_from_voter_to_voter(from_voter, to_voter)
    status += donate_link_results['status']
    if not donate_link_results['success']:
        success = False

    donation_plan_results = \
        StripeManager.move_stripe_subscription_entries_from_voter_to_voter(from_voter, to_voter)
    status += donation_plan_results['status']
    if not donation_plan_results['success']:
        success = False

    results = {
        'status':       status,
        'success':      success,
        'from_voter':   from_voter,
        'to_voter':     to_voter,
    }
    return results


# see https://stripe.com/docs/subscriptions/lifecycle
def donation_process_subscription_payment(event):    # invoice.payment_succeeded
    try:
        dataobject = event['data']['object']
        if 'pending_webhooks' in dataobject:
            pending_webhooks = dataobject['pending_webhooks']
            if pending_webhooks > 0:
                logger.info(
                    'donation_process_subscription_payment received an invoice object with pending_webhooks of ' +
                    str(pending_webhooks))
        amount = str(dataobject['amount_due'])
        currency = dataobject['currency']
        livemode = dataobject['livemode']
        customer_id = dataobject['customer']
        plan = dataobject['lines']['data'][0]['plan']
        we_plan_id = plan['nickname']   # example ... wv02voter279518-monthly-511
        api_version = event['api_version']
        stripe_plan_id = plan['id']
        request = event['request']
        stripe_request_id = request['id']
        status_transitions = dataobject['status_transitions']
        created = datetime.fromtimestamp(dataobject['created'], timezone.utc)
        paid_at = datetime.fromtimestamp(dataobject['status_transitions']['paid_at'], timezone.utc)
        billing_reason = dataobject['billing_reason']
        last_charged = paid_at
        # paid_at = last_charged
        stripe_charge_id = dataobject['charge']
        customer = stripe.Customer.retrieve(customer_id)
        not_loggedin_voter_we_vote_id = ''
        if billing_reason == 'subscription_create':
            result_request = StripeManager.retrieve_voter_we_vote_id_via_amount_and_customer_id(amount, customer_id)
            voter_we_vote_id = result_request['voter_we_vote_id']
            not_loggedin_voter_we_vote_id = result_request['not_loggedin_voter_we_vote_id']
        else:
            result_link = StripeManager.retrieve_voter_we_vote_id_from_donate_link_to_voter(customer_id)
            voter_we_vote_id = result_link['voter_we_vote_id']

        email = customer['email']
        # source_obj = dataobject['source']['object']
        stripe_customer_id = customer['id']
        stripe_card_id = customer['default_source']
        stripe_subscription_id = dataobject['subscription']
        subscription_created_at = datetime.fromtimestamp(event['created'], timezone.utc)
        # failure_code = str(dataobject['failure_code'])
        is_paid = str(dataobject['paid'])
        # is_refunded = str(dataobject['refunded'])
        # failure_message = str(dataobject['failure_message'])
        # network_status = dataobject['outcome']['network_status']
        stripe_status = dataobject['status']
        # reason = str(dataobject['outcome']['reason'])
        # seller_message = dataobject['outcome']['seller_message']
        stripe_type = dataobject['lines']['data'][0]['type']
        is_premium_plan = 'False'

        StripeManager.update_subscription_on_charge_success(we_plan_id, stripe_request_id,
                                                            stripe_subscription_id, stripe_charge_id,
                                                            subscription_created_at, last_charged,
                                                            amount, billing_reason,  api_version)

        # Now that we have saved the subscription, save what we know about the payment (more will arrive in the webhook)

        stripe_payment = {
            'amount': amount,
            'api_version': api_version,
            'billing_reason': billing_reason,
            'created': created,
            'currency': currency,
            'email': email,
            'is_paid': is_paid,
            'is_premium_plan': is_premium_plan,
            'livemode': livemode,
            'not_loggedin_voter_we_vote_id': not_loggedin_voter_we_vote_id,
            'paid_at': paid_at,
            'stripe_card_id': stripe_card_id,
            'stripe_charge_id': stripe_charge_id,
            'stripe_customer_id': stripe_customer_id,
            'stripe_request_id': stripe_request_id,
            'stripe_status': stripe_status,
            'stripe_subscription_id': stripe_subscription_id,
            'stripe_type': stripe_type,
            'voter_we_vote_id': voter_we_vote_id,
            'we_plan_id': we_plan_id,
        }
        print('Adding or updating StripePayment record on_charge_success stripe_charge_id: ', stripe_charge_id)
        print('Adding or updating StripePayment record on_charge_success: ', stripe_payment)
        StripeManager.stripe_payment_create_or_update(stripe_payment)
    except Exception as err:
        logger.error("DONATION donation_process_subscription_payment: " + str(err))

    return None


def donation_process_refund_payment(event):
    # The Stripe webhook has sent a refund event "charge.refunded"
    success = False
    logger.debug("donation_process_refund_payment: " + json.dumps(event))
    dataobject = event['data']['object']
    charge = dataobject['id']
    paid = dataobject['paid']  # boolean
    if paid:
        success = StripeManager.update_journal_entry_for_refund_completed(charge)

    return success


def donation_refund_for_api(request, charge, voter_we_vote_id):
    # The WebApp has requested a refund

    try:
        refund = stripe.Refund.create(
            charge=charge
        )
    except stripe.error.InvalidRequestError as err:
        body = err.json_body
        error_string = body['error']['message']
        logger.error("DONATION donation_refund_for_api: " + error_string)
        success = StripeManager.update_journal_entry_for_already_refunded(charge, voter_we_vote_id)
        return success

    except StripeManager.DoesNotExist as err:
        logger.error("DONATION donation_refund_for_api returned DoesNotExist for : " + charge)
        return False

    except Exception as err:
        logger.error("donation_refund_for_api: " + str(err))
        return False

    success = StripeManager.update_journal_entry_for_refund(charge, voter_we_vote_id, refund)

    return success


def donation_subscription_cancellation_for_api(voter_we_vote_id, premium_plan_type_enum='', stripe_subscription_id=''):
    """
    We expect either premium_plan_type_enum or stripe_subscription_id. If premium_plan_type_enum is passed in, then
    stripe_subscription_id might be replaced with another value
    :param voter_we_vote_id:
    :param premium_plan_type_enum:
    :param stripe_subscription_id:
    :return:
    """
    status = ''
    success = True
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
            # 'stripe_subs_id': stripe_subs_id,
            'customer_id': '',
            'canceled_at': '',
            'ended_at': '',
            'email': '',
            'voter_we_vote_id': voter_we_vote_id,
            'subscription_list': [],
            'livemode': '',
            'donation_list': [],
            'success': False,
        }
        return json_returned

    voter = voter_results['voter']
    # linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    donation_manager = StripeManager()
    # if positive_value_exists(premium_plan_type_enum):
    #     results = donation_manager.retrieve_donation_plan_definition(
    #         linked_organization_we_vote_id=linked_organization_we_vote_id, is_premium_plan=True,
    #         premium_plan_type_enum=premium_plan_type_enum, donation_plan_is_active=True)
    #     if results['donation_plan_definition_found']:
    #         donation_plan_definition = results['donation_plan_definition']
    #         donation_plan_definition_id = donation_plan_definition.id
    #         if positive_value_exists(donation_plan_definition.stripe_subscription_id):
    #             stripe_subscription_id = donation_plan_definition.stripe_subscription_id
    #         elif not donation_plan_definition.paid_without_stripe:
    #             # Reach out to Stripe to match existing subscription
    #             subscription_list_results = stripe.Subscription.list(limit=10)
    #             if 'data' in subscription_list_results and len(subscription_list_results['data']):
    #                 for one_subscription in subscription_list_results['data']:
    #                     if 'plan' in one_subscription and 'id' in one_subscription['plan']:
    #                         if one_subscription['plan']['id'] == donation_plan_definition.we_plan_id:
    #                             stripe_subscription_id = one_subscription['id']
    #                             donation_plan_definition.stripe_subscription_id = one_subscription['id']
    #                             donation_plan_definition.save()
    #                             break

    if positive_value_exists(stripe_subscription_id):
        # Make sure this voter has the right to cancel this stripe_subscription_id
        try:
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            stripe_customer_id = subscription['customer']
            canceled_at = subscription['canceled_at']
            ended_at = subscription['ended_at']
            # if 'email' in subscription['metadata']:
            #     email_raw = subscription['metadata']['email']
            #     if type(email_raw) == str:
            #         email = email_raw
            #     elif type(email_raw) == tuple:
            #         email = email_raw[0],
            # if 'voter_we_vote_id' in subscription['metadata']:
            #     voter_we_vote_id_raw = subscription['metadata']['voter_we_vote_id']
            #     if type(voter_we_vote_id_raw) == str:
            #         voter_we_vote_id_from_subscription = voter_we_vote_id_raw
            #     elif type(voter_we_vote_id_raw) == tuple:
            #         voter_we_vote_id_from_subscription = voter_we_vote_id_raw[0],
            livemode = subscription['livemode']

            if not positive_value_exists(canceled_at):
                # subscription.delete() is a Stripe API Call to mark subscription deleted on their end, and stop the
                # payment stream, will cause a customer.subscription.deleted to be fired
                results = subscription.delete()
                status += "STRIPE_SUBSCRIPTION_DELETED "
                status += results['status']
                canceled_at = results['canceled_at']
                ended_at = results['ended_at']
            else:
                status += "STRIPE_SUBSCRIPTION_PREVIOUSLY_DELETED "
        except Exception as e:
            logger.error("DONATION donation_subscription_cancellation_for_api err " + str(e))
            status += "DONATION_SUBSCRIPTION_CANCELLATION err:" + str(e) + " "
            success = False

        try:
            # This is also called in the webhook response... either should be sufficient, doing it twice causes no harm
            results = donation_manager.mark_donation_journal_canceled_or_ended(
                stripe_subscription_id, stripe_customer_id, ended_at, canceled_at)
            status += results['status']

            results = donation_manager.mark_subscription_as_canceled(
                donation_plan_definition_id=donation_plan_definition_id, stripe_subscription_id=stripe_subscription_id)
            status += results['status']
        except Exception as e:
            logger.error("DONATION MARK_JOURNAL_OR_DONATION_PLAN_DEFINITION err " + str(e))
            status += "DONATION_SUBSCRIPTION_CANCELLATION err:" + str(e) + " "
            success = False

    # active_results = donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id)
    # active_paid_plan = active_results['active_paid_plan']
    # subscription_list_json = active_results['subscription_list_json']
    #
    # # Switch the organization to this plan. This might be adjusted by the Stripe call backs
    # organization_manager = OrganizationManager()
    # organization_results = organization_manager.retrieve_organization_from_we_vote_id(linked_organization_we_vote_id)
    # if organization_results['organization_found']:
    #     organization = organization_results['organization']
    #     chosen_feature_package = "FREE"
    #     try:
    #         master_feature_package_query = MasterFeaturePackage.objects.all()
    #         master_feature_package_list = list(master_feature_package_query)
    #         for feature_package in master_feature_package_list:
    #             if feature_package.master_feature_package == chosen_feature_package:
    #                 organization.features_provided_bitmap = feature_package.features_provided_bitmap
    #     except Exception as e:
    #         status += "UNABLE_TO_UPDATE_FEATURES_PROVIDED_BITMAP: " + str(e) + " "
    #     try:
    #         organization.chosen_feature_package = chosen_feature_package
    #         organization.save()
    #         organization_saved = True
    #         status += "ORGANIZATION_FEATURE_PACKAGE_SAVED "
    #     except Exception as e:
    #         organization_saved = False
    #         status += "ORGANIZATION_FEATURE_PACKAGE_NOT_SAVED: " + str(e) + " "

    donation_subscription_list, donation_payments_list = donation_lists_for_a_voter(voter_we_vote_id)
    json_returned = {
        'status':           status,
        'success':          success,
        'stripe_subscription_id':  stripe_subscription_id,
        # 'active_paid_plan': active_paid_plan,
        'customer_id':      stripe_customer_id,
        'canceled_at':      canceled_at,
        'ended_at':         ended_at,
        'email':            email,
        'voter_we_vote_id': voter_we_vote_id_from_subscription
        if positive_value_exists(voter_we_vote_id_from_subscription)
        else voter_we_vote_id,
        'livemode':         livemode,
        'organization_saved': organization_saved,
        'donation_list':   ['deprecated'],
        'donation_subscription_list':   donation_subscription_list,
        'donation_payments_list': donation_payments_list
    }
    return json_returned


def local_datetime_string_from_utc_timestamp(utc_timestamp):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    utc_datetime = datetime.utcfromtimestamp(utc_timestamp)
    naive_local_datetime = utc_datetime + offset
    time_zone = pytz.timezone("America/Los_Angeles")
    local_datetime = time_zone.localize(naive_local_datetime)
    dt_string = local_datetime.strftime('%Y-%m-%d %H:%M:%S%z')
    return dt_string


def donation_process_dispute(event):           # 'charge.dispute.created' and 'charge.dispute.funds_withdrawn' webhooks
    try:
        dispute = {}
        dispute['created'] = local_datetime_string_from_utc_timestamp(event['created'])

        dispute['etype'] = event['type']
        is_create = event['type'] == "charge.dispute.created"
        dispute['livemode'] = event['livemode']

        data_object = event['data']['object']
        dispute['balance_transaction_id'] = data_object['balance_transaction']
        dispute['charge_id'] = data_object['charge']
        dispute['reason'] = data_object['reason']
        dispute['transaction_state'] = data_object['status']


        balance_transaction = data_object['balance_transactions'][0]
        dispute['transaction_status'] = balance_transaction['status']
        dispute['amount'] = str(balance_transaction['amount'])
        dispute['description'] = balance_transaction['description']
        dispute['total_cost'] = str(balance_transaction['net'])
        dispute['fee'] = str(balance_transaction['fee'])
        dispute['dispute_source_id'] = balance_transaction['source']

        fee_details = balance_transaction['fee_details'][0]
        dispute['fee_description'] = fee_details['description'] + ": " + fee_details['type']

        evidence = data_object['evidence']
        dispute['billing_address'] = evidence['billing_address']
        dispute['customer_email_address'] = evidence['customer_email_address']
        dispute['customer_name'] = evidence['customer_name']
        dispute['customer_purchase_ip'] = evidence['customer_purchase_ip']

        evidence_details = data_object['evidence_details']
        dispute['evidence_due_by'] = local_datetime_string_from_utc_timestamp(evidence_details['due_by'])
        dispute['evidence_has_evidence'] = evidence_details['has_evidence']
        dispute['evidence_past_due'] = evidence_details['past_due']
        dispute['evidence_submission_count'] = evidence_details['submission_count']

        StripeDispute.save_dispute_transaction(dispute)

    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        logger.error("DONATION donation_process_dispute, Stripe: " + error_from_json)

    except Exception as err:
        logger.error("DONATION donation_process_dispute, general: " + str(err))

    return
