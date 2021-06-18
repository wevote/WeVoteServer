# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable, get_environment_variable_default
from datetime import datetime, timezone
from stripe_donations.models import StripeManager
# from organization.models import OrganizationManager
from wevote_functions.functions import positive_value_exists
from wevote_functions.admin import get_logger
from wevote_functions.functions import convert_pennies_integer_to_dollars_string, get_voter_device_id
from voter.models import VoterManager
import json
import stripe
import textwrap


logger = get_logger(__name__)
stripe.api_key = get_environment_variable_default("STRIPE_SECRET_KEY", "")
if len(stripe.api_key) and not stripe.api_key.startswith("sk_"):
    logger.error("Configuration error, the stripe secret key, must begin with 'sk_' -- don't use the publishable key "
                 "on the server!")


def donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id):
    status = ''
    active_paid_plan_found = False
    donation_plan_definition_list = []
    donation_plan_definition_list_json = []
    coupon_code = ''
    we_plan_id = ''
    plan_type_enum = ''
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
        # if positive_value_exists(donation_plan_definition.is_organization_plan):
        if positive_value_exists(donation_plan_definition.donation_plan_is_active):
            active_paid_plan_found = True
            donation_plan_definition_id = donation_plan_definition.id
            # plan_type_enum = donation_plan_definition.plan_type_enum
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
        'we_plan_id':         we_plan_id,
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


def donation_with_stripe_for_api(request, token, payment_method_id, client_ip, email, donation_amount, monthly_donation,
                                 voter_we_vote_id, is_organization_plan, coupon_code, plan_type_enum,
                                 organization_we_vote_id):
    """
    Initiate a donation or organization subscription plan using the Stripe Payment API, and record details in our DB
    :param request:
    :param token: The Stripe token.id for the card and transaction
    :param payment_method_id: payment method selected/created on the client CheckoutForm.jsx
    :param client_ip:
    :param email:
    :param donation_amount:  the amount of the donation, but not used for organization subscriptions
    :param monthly_donation: (boolean) is this a monthly donation subscription
    :param voter_we_vote_id:
    :param is_organization_plan:  True for a organization plan, False for a donation (one time or donation subscription)
    :param coupon_code: Our coupon codes for pricing and features that are looked up
           in the OrganizationSubscriptionPlans
    :param plan_type_enum: Type of organization plan, or undefined for donations
    :param organization_we_vote_id: The organization that benefits from this paid plan (subscription)
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
        'monthly_donation': monthly_donation,
        'subscription_already_exists': False,
        'org_subs_already_exists': False,
        'organization_saved': False,
        'plan_type_enum': plan_type_enum,
        'saved_stripe_donation': '',
        'stripe_subscription_created': False,
        'subscription_saved': 'NOT_APPLICABLE',
    }

    charge, not_loggedin_voter_we_vote_id = None, None
    donation_date_time = datetime.today()
    raw_donation_status = ''
    is_signed_in = is_voter_logged_in(request)

    if is_organization_plan:
        results['amount_paid'] = 0

    if not positive_value_exists(voter_we_vote_id):
        results['status'] += "DONATION_WITH_STRIPE_VOTER_WE_VOTE_ID_MISSING "
        return results

    if not positive_value_exists(email) and not is_organization_plan:
        results['status'] += "DONATION_WITH_STRIPE_EMAIL_MISSING "
        results['error_message_for_voter'] = 'An email address is required by our payment processor.'
        return results

    # Use a default coupon_code if none is specified
    if is_organization_plan:
        if len(coupon_code) < 2:
            coupon_code = 'DEFAULT-' + results['plan_type_enum']
    else:
        coupon_code = ''

    # If is_organization_plan, set the price from the coupon, not whatever was passed in.
    if is_organization_plan:
        increment_redemption_cnt = False
        coupon_price, org_subs_id = StripeManager.get_coupon_price(results['plan_type_enum'], coupon_code,
                                                                   increment_redemption_cnt)
        if int(donation_amount) > 0:
            print("Warning for developers, the donation_amount that is passed in for organization plans is ignored,"
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
            # if positive_value_exists(is_organization_plan):
            #     # If here, we are processing organization subscription
            #     results['status'] += 'DONATION_SUBSCRIPTION_SETUP '
            #     if "MONTHLY" in results['plan_type_enum']:
            #         recurring_interval = 'month'
            #     elif "YEARLY" in results['plan_type_enum']:
            #         recurring_interval = 'year'
            #     else:
            #         recurring_interval = 'year'
            #     subscription_results = donation_manager.create_organization_subscription(
            #         results['stripe_customer_id'], voter_we_vote_id, donation_amount, donation_date_time,
            #         email, coupon_code, results['plan_type_enum'], organization_we_vote_id,
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
            # If here, we are processing a donation subscription or Membership
            if positive_value_exists(monthly_donation):
                results['status'] += 'DONATION_SUBSCRIPTION_SETUP '
                # The Stripe API calls are made within the following function call
                recurring_donation_results = donation_manager.create_recurring_donation(
                    results['stripe_customer_id'], voter_we_vote_id,
                    donation_amount, donation_date_time,
                    email, is_organization_plan,
                    coupon_code, results['plan_type_enum'],
                    organization_we_vote_id, client_ip, payment_method_id, is_signed_in)

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
                        'one_time_donation': True,
                        'organization_we_vote_id': organization_we_vote_id,
                        'plan_type_enum': results['plan_type_enum'],
                        'voter_we_vote_id': voter_we_vote_id,
                        'coupon_code': coupon_code,
                        'stripe_customer_id': dm_results['stripe_customer_id']
                    }
                )
                results['status'] += textwrap.shorten("STRIPE_CHARGE_SUCCESSFUL " + results['status'], width=255,
                                                      placeholder="...")
                results['charge_id'] = charge.id
                results['success'] = positive_value_exists(charge.id)

        if positive_value_exists(charge) and positive_value_exists(charge.id):
            results['saved_stripe_donation'] = True
            results['status'] += ' DONATION_PROCESSED_SUCCESSFULLY '
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
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("donation_with_stripe_for_api, CardError: " + error_message)
    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        raw_donation_status += " STRIPE_STATUS_IS: {http_status} STRIPE_ERROR_IS: {error_type} " \
                               "STRIPE_MESSAGE_IS: {error_message} " \
                               "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                         error_message=error_from_json['message'])
        results['status'] += textwrap.shorten(raw_donation_status + " " + results['status'], width=255,
                                              placeholder="...")
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("donation_with_stripe_for_api, StripeError : " + raw_donation_status)
    except Exception as err:
        # Something else happened, completely unrelated to Stripe
        logger.error("donation_with_stripe_for_api caught: ", err)
        raw_donation_status += "A_NON_STRIPE_ERROR_OCCURRED "
        logger.error("donation_with_stripe_for_api threw " + str(err))
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
                'plan_type_enum': donation_row.plan_type_enum,
                'stripe_subscription_id': donation_row.stripe_subscription_id,
                'subscription_canceled_at': str(donation_row.subscription_canceled_at),
                'subscription_ended_at': str(donation_row.subscription_ended_at),
                'refund_days_limit': refund_days,
                'last_charged': str(donation_row.last_charged),
                'is_organization_plan': positive_value_exists(donation_row.is_organization_plan),
                'organization_we_vote_id': str(donation_row.organization_we_vote_id),
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
                # 'plan_type_enum': payment_row.plan_type_enum,
                'stripe_subscription_id': payment_row.stripe_subscription_id,
                'refund_days_limit': refund_days,
                'last_charged': str(payment_row.paid_at),
                # 'is_organization_plan': positive_value_exists(payment_row.is_organization_plan),
                # 'organization_we_vote_id': str(payment_row.organization_we_vote_id),
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
                # 'plan_type_enum': subscription_row.plan_type_enum,
                'stripe_subscription_id': subscription_row.stripe_subscription_id,
                'subscription_canceled_at': str(subscription_row.subscription_canceled_at),
                'subscription_ended_at': str(subscription_row.subscription_ended_at),
                'refund_days_limit': refund_days,
                'last_charged': str(payment.paid_at) if payment else '',
                # 'is_organization_plan': positive_value_exists(subscription_row.is_organization_plan),
                # 'organization_we_vote_id': str(subscription_row.organization_we_vote_id),
            }
            donation_subscription_list.append(json_data)

    return donation_subscription_list, donation_payments_list


def donation_process_stripe_webhook_event(event):
    """
    NOTE: These are the only six events that we handle from the webhook
    :param event:
    :return:
    """
    etype = event.type
    api_version = event.api_version
    logger.info("WEBHOOK received: donation_process_stripe_webhook_event: " + etype)
    print("WEBHOOK received: donation_process_stripe_webhook_event: " + etype)
    # write_event_to_local_file(event);

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
    # elif etype == 'invoice.created':  Abandoned March 2021, not needed with new api
    #     return donation_process_invoice_created(event)

    print("WEBHOOK ignored: donation_process_stripe_webhook_event: " + event.type)
    logger.info("WEBHOOK ignored: donation_process_stripe_webhook_event: " + event.type)
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
        charge = event['data']['object']
        description = charge['description']
        metadata = charge['metadata']
        is_one_time_donation = True if 'one_time_donation' in metadata else False
        print('donation_process_charge # charge.succeeded ... is_one_time_donation:', is_one_time_donation)

        if description == "Subscription creation":
            print('charge.succeeded webhook is NOT Needed for subscriptions as of 3/16/21: ' + description)
            return
        elif not is_one_time_donation:
            print('charge.succeeded webhook received -- not for a subs AND without one_time_donation in metadata')
            return

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

        payment = {
            # record_enum
            'voter_we_vote_id': voter_we_vote_id,
            'not_loggedin_voter_we_vote_id': not_loggedin_voter_we_vote_id,
            'stripe_customer_id': metadata['stripe_customer_id'],
            'stripe_charge_id': charge['id'],
            'stripe_card_id': charge['payment_method'],
            'stripe_request_id': event['request']['id'],
            # stripe_subscription_id
            'currency': charge['currency'],
            'livemode': charge['livemode'],
            # action_taken
            # action_result
            'amount': charge['amount'],
            'created': datetime.fromtimestamp(event['created'], timezone.utc),
            'failure_code': charge['failure_code'],
            'failure_message': charge['failure_message'],
            'network_status': outcome['network_status'],
            # billing_reason
            'reason': outcome['reason'],
            'seller_message': outcome['seller_message'],
            'stripe_type': stripe_object['object'],
            # payment_msg
            'is_paid': charge['paid'],
            'is_refunded': charge['refunded'],
            'source_obj': source['object'],
            'funding': source['funding'],
            'amount_refunded': charge['amount_refunded'],
            'email': metadata['email'] if 'email' in metadata else '',    # Need a change on the other side!
            'address_zip': source['address_zip'],
            'brand': source['brand'],
            'country': source['country'],
            'exp_month': source['exp_month'],
            'exp_year': source['exp_year'],
            'last4': source['last4'],
            'stripe_status': charge['status'],
            'status': stripe_object['calculated_statement_descriptor'],
            # we_plan_id
            'paid_at': datetime.fromtimestamp(charge['created'], timezone.utc),
            'ip_address': '0.0.0.0',                # Need a change on the other side!
            'is_organization_plan': False,
            'api_version': event['api_version'],
        }

        StripeManager.create_payment_entry(payment)
        logger.debug("Stripe subscription payment from webhook: " + str(charge['customer']) + ", amount: " +
                     str(charge['amount']) + ", last4:" + str(source['last4']))

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

    # All we really need to do is find the donations that are associated with the "from" organization, and change their
    # organization_we_vote_id to the "to" organization.
    results = StripeManager.move_donation_journal_entries_from_organization_to_organization(
        from_organization_we_vote_id, to_organization_we_vote_id)
    status += results['status']

    results = StripeManager.move_donation_plan_definition_entries_from_organization_to_organization(
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
    results = StripeManager.move_donation_payment_entries_from_voter_to_voter(from_voter, to_voter)
    status += results['status']

    donate_link_results = StripeManager.move_donate_link_to_voter_from_voter_to_voter(from_voter, to_voter)
    status += donate_link_results['status']

    donation_plan_results = \
        StripeManager.move_stripe_subscription_entries_from_voter_to_voter(from_voter, to_voter)
    status += donation_plan_results['status']

    results = {
        'status': status,
        'success': success,
        'from_voter': from_voter,
        'to_voter': to_voter,
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
        card_source = stripe.Customer.retrieve_source(stripe_customer_id, stripe_card_id)
        address_zip = card_source['address_zip']
        brand = card_source['brand']
        country = card_source['country']
        exp_month = card_source['exp_month']
        exp_year = card_source['exp_year']
        funding = card_source['funding']
        last4 = card_source['last4']
        # email = dataobject['billing_details']['email']
        stripe_subscription_id = dataobject['subscription']
        # This is very close to the subscription_created_at time, but doesn't come from the exact correct object
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
        is_organization_plan = 'False'

        StripeManager.update_subscription_on_charge_success(we_plan_id, stripe_request_id,
                                                            stripe_subscription_id, stripe_charge_id,
                                                            subscription_created_at, last_charged,
                                                            brand, exp_month, exp_year, last4, api_version)

        # Not that we have saved the subscription, save what we know about the payment (more will arrive in the webhook)

        stripe_payment = {
            # 'we_plan_id': we_plan_id,
            'voter_we_vote_id': voter_we_vote_id,
            'not_loggedin_voter_we_vote_id': not_loggedin_voter_we_vote_id,
            'stripe_customer_id': stripe_customer_id,
            'stripe_request_id': stripe_request_id,
            'stripe_subscription_id': stripe_subscription_id,
            'stripe_charge_id': stripe_charge_id,
            'billing_reason': billing_reason,
            'amount': amount,
            'currency': currency,
            'funding': funding,
            'address_zip': address_zip,
            'email': email,
            'country': country,
            'paid_at': paid_at,
            'livemode': livemode,
            'stripe_card_id': stripe_card_id,
            'brand': brand,
            'exp_month': exp_month,
            'exp_year': exp_year,
            'last4': last4,
            # Not in invoice success: failure_code, failure_message, network_status, reason, seller_message, is_refunded
            'stripe_type': stripe_type,
            'is_paid': is_paid,
            'stripe_status': stripe_status,
            'we_plan_id': we_plan_id,
            'api_version': api_version,
            'is_organization_plan': is_organization_plan,
            'created': created,
        }
        print('Adding new StripePayment record on_charge_success: ', stripe_payment)
        StripeManager.add_payment_on_charge_success(stripe_payment)
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
        logger.error("donation_refund_for_api: " + error_string)
        success = StripeManager.update_journal_entry_for_already_refunded(charge, voter_we_vote_id)
        return success

    except StripeManager.DoesNotExist as err:
        logger.error("donation_refund_for_api returned DoesNotExist for : " + charge)
        return False

    except Exception as err:
        logger.error("donation_refund_for_api: " + str(err))
        return False

    success = StripeManager.update_journal_entry_for_refund(charge, voter_we_vote_id, refund)

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
            # 'stripe_subs_id': stripe_subs_id,
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
    # linked_organization_we_vote_id = voter.linked_organization_we_vote_id

    donation_manager = StripeManager()
    # if positive_value_exists(plan_type_enum):
    #     results = donation_manager.retrieve_donation_plan_definition(
    #         organization_we_vote_id=linked_organization_we_vote_id, is_organization_plan=True,
    #         plan_type_enum=plan_type_enum, donation_plan_is_active=True)
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
            logger.error("donation_subscription_cancellation_for_api err " + str(e))
            status += "DONATION_SUBSCRIPTION_CANCELLATION err:" + str(e) + " "
            success = False

        try:
            # This is also called in the webhook response... either should be sufficient, doing it twice causes no harm
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

    # active_results = donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id)
    # active_paid_plan = active_results['active_paid_plan']
    # donation_plan_definition_list_json = active_results['donation_plan_definition_list_json']
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
