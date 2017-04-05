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
    saved_stripe_customer_id = False
    saved_stripe_donation = False
    donation_entry_saved = False
    donation_date_time = datetime.today()
    donation_status = 'STRIPE_DONATION_NOT_COMPLETED'
    action_taken = 'VOTER_SUBMITTED_DONATION'
    action_taken_date_time = donation_date_time
    charge_id = ''
    stripe_customer_id = ''
    subscription_saved = 'NOT_APPLICABLE'
    status = ''
    charge_processed_successfully = bool
    error_text_description = ''

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
                charge_processed_successfully = recurring_donation['success']
            else:
                charge = stripe.Charge.create(
                    amount=donation_amount,
                    currency="usd",
                    customer=stripe_customer_id
                )
                status = 'STRIPE_CHARGE_SUCCESSFUL'
                charge_id = charge.id
                success = positive_value_exists(charge_id)
                charge_processed_successfully = positive_value_exists(charge_id)

        if charge_processed_successfully:
            saved_donation = donation_manager.create_donation_from_voter(stripe_customer_id, voter_we_vote_id,
                                                                         donation_amount, email,
                                                                         donation_date_time, charge_id,
                                                                         charge_processed_successfully)
            saved_stripe_donation = saved_donation['success']
            donation_status = saved_donation['status'] + ' DONATION_PROCESSED_SUCCESSFULLY '

    except stripe.error.CardError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status = " STRIPE_STATUS_IS: {http_status} STRIPE_ERROR_IS: {error_type} " \
                          "STRIPE_MESSAGE_IS: {error_message} " \
                          "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                    error_message=error_from_json['message'])
        status += donation_status
        error_text_description = donation_status
    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status = " STRIPE_STATUS_IS: {http_status} STRIPE_ERROR_IS: {error_type} " \
                          "STRIPE_MESSAGE_IS: {error_message} " \
                          "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                    error_message=error_from_json['message'])
        status += donation_status
        error_text_description = donation_status
        print(donation_status)
    except Exception:
        # Something else happened, completely unrelated to Stripe
        donation_status = "A_NON_STRIPE_ERROR_OCCURRED "
        status += donation_status

    result_taken = donation_status  # TODO: Update this to match "action_result" below
    result_taken_date_time = donation_date_time

    # action_taken should be VOTER_SUBMITTED_DONATION, VOTER_CANCELED_DONATION or CANCEL_REQUEST_SUBMITTED
    # action_result should be CANCEL_REQUEST_FAILED, CANCEL_REQUEST_SUCCEEDED or DONATION_PROCESSED_SUCCESSFULLY
    donation_log_results = donation_manager.create_donation_log_entry(
        ip_address, stripe_customer_id, voter_we_vote_id, charge_id, action_taken, action_taken_date_time,
        result_taken, result_taken_date_time, error_text_description)
    donation_entry_saved = donation_log_results['success']

    results = {
        'status': status,
        'success': success,
        'charge_id': charge_id,
        'customer_id': stripe_customer_id,
        'donation_entry_saved': donation_entry_saved,
        'saved_stripe_donation': saved_stripe_donation,
        'monthly_donation': monthly_donation,
        'subscription': subscription_saved

    }

    return results
