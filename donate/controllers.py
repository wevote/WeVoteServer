# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime
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
    one_time_donation = True
    subscription_id = ''
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
    name = ''
    address_zip = ''
    brand = ''
    country = ''
    exp_month = ''
    exp_year = ''
    last4 = ''
    id_card = ''
    stripe_object = ''
    stripe_status = ''

    ip_address = get_ip_from_headers(request)

    if not positive_value_exists(ip_address):
        ip_address = ''

    if not positive_value_exists(voter_we_vote_id):
        status += "DONATION_WITH_STRIPE_VOTER_WE_VOTE_ID_MISSING "
        error_results = {
            'status':                   status,
            'success':                  success,
            'charge_id':                charge_id,
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
            'charge_id':                charge_id,
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
                # recurring_donation_saved = recurring_donation['recurring_donation_plan_id']
                # recurring_donation_saved = recurring_donation['status']
                subscription_saved = recurring_donation['voter_subscription_saved']
                status += recurring_donation['status']
                success = recurring_donation['success']
                one_time_donation = False
                subscription_id = recurring_donation['subscription_id']
                charge_processed_successfully = recurring_donation['success']
                # TODO April 2017: Following lines were not being executed if recurring, but what we want to do is make
                # record, and make a charge record for the first payment.
                # Previous 3 code lines will do nothing, need to rethink

            charge = stripe.Charge.create(
                amount=donation_amount,
                currency="usd",
                customer=stripe_customer_id
            )
            status = 'STRIPE_CHARGE_SUCCESSFUL'
            charge_id = charge.id
            success = positive_value_exists(charge_id)

        if positive_value_exists(charge_id):
            saved_donation = donation_manager.create_donation_from_voter(stripe_customer_id, voter_we_vote_id,
                                                                         donation_amount, email,
                                                                         donation_date_time, charge_id,
                                                                         charge_processed_successfully)
            saved_stripe_donation = saved_donation['success']
            donation_status = saved_donation['status'] + ' DONATION_PROCESSED_SUCCESSFULLY '
            stripe_detail = stripe.Charge.retrieve(charge_id)
            amount = stripe_detail['amount']
            currency = stripe_detail['currency']
            amount_refunded = stripe_detail['amount_refunded']
            funding = stripe_detail['source']['funding']
            livemode = stripe_detail['livemode']
            utc_dt = datetime.utcfromtimestamp(stripe_detail['created'])
            created = utc_dt.isoformat()
            failure_code = str(stripe_detail['failure_code'])
            failure_message = str(stripe_detail['failure_message'])
            network_status = stripe_detail['outcome']['network_status']
            reason = str(stripe_detail['outcome']['reason'])
            seller_message = stripe_detail['outcome']['seller_message']
            stripe_type = stripe_detail['outcome']['type']
            paid = str(stripe_detail['paid'])
            amount_refunded = stripe_detail['amount_refunded']
            refund_count = stripe_detail['refunds']['total_count']
            name = stripe_detail['source']['name']
            address_zip = stripe_detail['source']['address_zip']
            brand = stripe_detail['source']['brand']
            country = stripe_detail['source']['country']
            exp_month = stripe_detail['source']['exp_month']
            exp_year = stripe_detail['source']['exp_year']
            last4 = int(stripe_detail['source']['last4'])
            id_card = stripe_detail['source']['id']
            stripe_object = stripe_detail['source']['object']
            stripe_status = stripe_detail['status']

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

    donation_history_results = donation_manager.create_donation_history_entry(
        ip_address, stripe_customer_id, voter_we_vote_id, charge_id, amount, currency, one_time_donation,
        subscription_id, funding, livemode, action_taken, action_result, created, failure_code, failure_message,
        network_status, reason, seller_message, stripe_type, paid, amount_refunded, refund_count, name, address_zip,
        brand, country, exp_month, exp_year, last4, id_card, stripe_object, stripe_status, status)

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
    donation_list = donation_manager.retrieve_donation_history_list(voter_we_vote_id)

    simple_donation_list = []
    for donation_row in donation_list['voters_donation_list']:
        json_data = {
            'created': str(donation_row.created),
            'amount': donation_row.amount,
            'currency': donation_row.currency,
            'one_time_donation': donation_row.one_time_donation,
            'brand': donation_row.brand,
            'exp_month': donation_row.exp_month,
            'exp_year': donation_row.exp_year,
            'last4': donation_row.last4,
            'stripe_status': donation_row.stripe_status,
            'charge_id': donation_row.charge_id
        }
        simple_donation_list.append(json_data)

    return simple_donation_list
