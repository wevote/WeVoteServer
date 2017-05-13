# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime, timezone
from donate.models import DonationManager
import stripe
from wevote_functions.functions import get_ip_from_headers, positive_value_exists

stripe.api_key = get_environment_variable("STRIPE_SECRET_KEY")


# TODO set up currency option in webapp
def donation_with_stripe_for_api(request, token, email, donation_amount, monthly_donation, voter_we_vote_id):

    donation_manager = DonationManager()
    success = False
    saved_stripe_donation = False
    donation_entry_saved = False
    donation_date_time = datetime.today()
    donation_status = 'STRIPE_DONATION_NOT_COMPLETED'
    action_taken = 'VOTER_SUBMITTED_DONATION'
    action_taken_date_time = donation_date_time
    charge_id = ''
    amount = 0
    currency = ''
    stripe_customer_id = ''
    subscription_saved = 'NOT_APPLICABLE'
    status = ''
    charge_processed_successfully = bool
    error_text_description = ''
    error_message = ''
    funding = ''
    livemode = False
    created = 0
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
    exp_month = ''
    exp_year = ''
    last4 = ''
    id_card = ''
    stripe_object = ''
    stripe_status = ''
    subscription_id = None
    subscription_plan_id = None
    subscription_created_at = None
    subscription_canceled_at = None
    subscription_ended_at = None
    create_donation_entry = False
    create_subscription_entry = False

    ip_address = get_ip_from_headers(request)

    if not positive_value_exists(ip_address):
        ip_address = ''

    if not positive_value_exists(voter_we_vote_id):
        status += "DONATION_WITH_STRIPE_VOTER_WE_VOTE_ID_MISSING "
        error_results = {
            'status':                   status,
            'success':                  success,
            'charge_id':                charge_id,   # TODO: always 0 here, could use the token like "tok_1AHa3PD153UBwRssV96hVKHq"
            'customer_id':              stripe_customer_id,
            'donation_entry_saved':     donation_entry_saved,
            'saved_stripe_donation':    saved_stripe_donation,
            'monthly_donation':         monthly_donation,
            'subscription':             subscription_saved

        }

        return error_results

    if not positive_value_exists(email):
        status += "DONATION_WITH_STRIPE_EMAIL_MISSING "
        error_results = {
            'status':                   status,
            'success':                  success,
            'charge_id':                charge_id,    # TODO: always 0 here, could use the token like "tok_1AHa3PD153UBwRssV96hVKHq"
            'customer_id':              stripe_customer_id,
            'donation_entry_saved':     donation_entry_saved,
            'saved_stripe_donation':    saved_stripe_donation,
            'monthly_donation':         monthly_donation,
            'subscription':             subscription_saved

        }

        return error_results

    try:
        results = donation_manager.retrieve_stripe_customer_id(voter_we_vote_id)
        if results['success']:
            stripe_customer_id = results['stripe_customer_id']
            status += "STRIPE_CUSTOMER_ID_ALREADY_EXISTS "
        else:
            customer = stripe.Customer.create(
                source=token,
                email=email
            )
            stripe_customer_id = customer.id
            saved_results = donation_manager.create_donate_link_to_voter(stripe_customer_id, voter_we_vote_id)
            status += saved_results['status']

        if positive_value_exists(stripe_customer_id):
            if positive_value_exists(monthly_donation):
                recurring_donation = donation_manager.create_recurring_donation(stripe_customer_id, voter_we_vote_id,
                                                                                donation_amount, donation_date_time)
                subscription_saved = recurring_donation['voter_subscription_saved']
                status += recurring_donation['status']
                success = recurring_donation['success']
                create_subscription_entry = True
                subscription_id = recurring_donation['subscription_id']
                charge_processed_successfully = recurring_donation['success']
                subscription_plan_id = recurring_donation['subscription_plan_id']
                subscription_created_at = datetime.fromtimestamp(recurring_donation['subscription_created_at'],
                                                                 timezone.utc)
                subscription_canceled_at = None
                subscription_ended_at = None

            charge = stripe.Charge.create(
                amount=donation_amount,
                currency="usd",
                source=token
            )
            status += 'STRIPE_CHARGE_SUCCESSFUL '
            create_donation_entry = True
            charge_id = charge.id
            success = positive_value_exists(charge_id)

        if positive_value_exists(charge_id):
            saved_donation = donation_manager.create_donation_from_voter(stripe_customer_id, voter_we_vote_id,
                                                                         donation_amount, email,
                                                                         donation_date_time, charge_id,
                                                                         charge_processed_successfully)
            saved_stripe_donation = saved_donation['success']
            donation_status = saved_donation['status'] + ' DONATION_PROCESSED_SUCCESSFULLY '
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

    except stripe.error.CardError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status = " STRIPE_STATUS_IS: {http_status} STRIPE_CARD_ERROR_IS: {error_type} " \
                          "STRIPE_MESSAGE_IS: {error_message} " \
                          "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                    error_message=error_from_json['message'])
        status += donation_status
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        error_text_description = donation_status
    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status = " STRIPE_STATUS_IS: {http_status} STRIPE_ERROR_IS: {error_type} " \
                          "STRIPE_MESSAGE_IS: {error_message} " \
                          "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                    error_message=error_from_json['message'])
        status += donation_status
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        error_text_description = donation_status
        print(donation_status)
    except Exception:
        # Something else happened, completely unrelated to Stripe
        donation_status = "A_NON_STRIPE_ERROR_OCCURRED "
        status += donation_status
        error_message = 'Your payment was unsuccessful. Please try again later.'

    result_taken = donation_status  # TODO: Update this to match "action_result" below
    action_result = donation_status  # TODO: Update this to match "action_result" below
    result_taken_date_time = donation_date_time

    # steve:  These are good, will need to be expanded when webhooks are setup, to indicate recurring payments etc
    # action_taken should be VOTER_SUBMITTED_DONATION, VOTER_CANCELED_DONATION or CANCEL_REQUEST_SUBMITTED
    # action_result should be CANCEL_REQUEST_FAILED, CANCEL_REQUEST_SUCCEEDED or DONATION_PROCESSED_SUCCESSFULLY
    donation_log_results = donation_manager.create_donation_log_entry(
        ip_address, stripe_customer_id, voter_we_vote_id, charge_id, action_taken, action_taken_date_time,
        result_taken, result_taken_date_time, error_text_description, error_message)

    if create_donation_entry:
        # Create the Journal entry for a payment initiated by the UI.  (Automatic payments from the subscription will be
        donation_journal_results = donation_manager.create_donation_journal_entry("PAYMENT_FROM_UI",
            ip_address, stripe_customer_id, voter_we_vote_id, charge_id, amount, currency, funding, livemode,
            action_taken, action_result, created, failure_code, failure_message, network_status, reason, seller_message,
            stripe_type, paid, amount_refunded, refund_count, email, address_zip,
            brand, country, exp_month, exp_year, last4, id_card, stripe_object, stripe_status, status,
            None, None, None, None, None)
    if create_subscription_entry:
        # Create the Journal entry for a new subscription, with some fields from the intial payment on that subscription
        donation_history_results = donation_manager.create_donation_journal_entry("SUBS_SETUP_AND_INITIAL",
            ip_address, stripe_customer_id, voter_we_vote_id, charge_id, amount, currency, funding, livemode,
            action_taken, action_result, created, failure_code, failure_message, network_status, reason, seller_message,
            stripe_type, paid, amount_refunded, refund_count, email, address_zip,
            brand, country, exp_month, exp_year, last4, id_card, stripe_object, stripe_status, status,
            subscription_id, subscription_plan_id, subscription_created_at, subscription_canceled_at,
            subscription_ended_at)

        donation_entry_saved = donation_log_results['success']

    results = {
        'status': status,
        'success': success,
        'charge_id': charge_id,
        'customer_id': stripe_customer_id,
        'donation_entry_saved': donation_entry_saved,
        'saved_stripe_donation': saved_stripe_donation,
        'monthly_donation': monthly_donation,
        'subscription': subscription_saved,
        'error_message_for_voter': error_message
    }

    return results


def translate_stripe_error_to_voter_explanation_text(donation_http_status, error_type):
    donation_manager = DonationManager()
    generic_voter_error_message = 'Your payment was unsuccessful. Please try again later.'

    if donation_http_status == 402:
        error_message_for_voter = donation_manager.retrieve_stripe_card_error_message(error_type)
    else:
        error_message_for_voter = generic_voter_error_message

    return error_message_for_voter


# Get a list of all prior donations by the voter that is associated with this voter_we_vote_id
# If they donated without logging in they are out of luck for tracking past donations
def donation_history_for_a_voter(voter_we_vote_id):
    donation_manager = DonationManager()
    donation_list = donation_manager.retrieve_donation_journal_list(voter_we_vote_id)

    simple_donation_list = []
    if donation_list['success']:
        for donation_row in donation_list['voters_donation_list']:
            json_data = {
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
                'subscription_id': donation_row.subscription_id,
                'subscription_canceled_at': donation_row.subscription_canceled_at,
                'subscription_ended_at': donation_row.subscription_ended_at
            }
            simple_donation_list.append(json_data)

    return simple_donation_list
