# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime
from donate.models import DonationManager
import json
import stripe
from wevote_functions.functions import positive_value_exists
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
    charge_id = ''
    stripe_customer_id = ''
    recurring_donation_saved = ''
    status = ''
    # for testing purposes, voter_we_vote_id can't be an empty string (due to model properties)
    voter_we_vote_id = 'test5'

    ip_address = get_ip_from_headers(request)

    if not positive_value_exists(ip_address):
        ip_address = ''

    try:
        results = donation_manager.retrieve_stripe_customer_id(voter_we_vote_id)
        if results['success']:
            stripe_customer_id = results['stripe_customer_id']
        else:
            customer = stripe.Customer.create(
                source=token,
                email=email
            )
            stripe_customer_id = customer.id
            saved_results = donation_manager.create_donate_link_to_voter(stripe_customer_id, voter_we_vote_id)
            saved_stripe_customer_id = saved_results['success']
            charge_processed_successfully = True

        if positive_value_exists(monthly_donation):
            donation_plan_id_query = donation_manager.retrieve_or_create_recurring_donation_plan(donation_amount)
            if donation_plan_id_query['success']:
                status = donation_plan_id_query['status']
            else:
                status = donation_plan_id_query['status']

            #     recurring_donation = donation_manager.create_recurring_donation(stripe_customer_id, voter_we_vote_id,
            #                                                                 donation_amount, donation_date_time)
            # # recurring_donation_saved = recurring_donation['recurring_donation_plan_id']
            # recurring_donation_saved = recurring_donation['status']
            # print("recurring_donation_saved in controller " + recurring_donation_saved)
            # status = recurring_donation['status']
            # success = recurring_donation['success']
        else:
            charge = stripe.Charge.create(
                amount=donation_amount,
                currency="usd",
                customer=stripe_customer_id
            )
            status = 'STRIPE_CHARGE_SUCCESSFUL'
            success = True
            charge_id = charge.id

    except stripe.error.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err = body['error']
        status = "STATUS_IS_%s_AND_ERROR_IS_%s" % e.http_status, err['type']
    except stripe.error.StripeError as e:
        body = e.json_body
        err = body['error']
        status = "STATUS_IS_{}_AND_ERROR_IS_{}".format(e.http_status, err['type'])
        print("Type is: {}".format(err['type']))
    except Exception:
        # Something else happened, completely unrelated to Stripe
        status += "A_NON_STRIPE_ERROR_OCCURRED"

    if positive_value_exists(charge_id):
        saved_donation = donation_manager.create_donation_from_voter(stripe_customer_id, voter_we_vote_id,
                                                                     donation_amount, email,
                                                                     donation_date_time, charge_id,
                                                                     charge_processed_successfully)
        saved_stripe_donation = saved_donation['success']
        action_taken = 'VOTER_SUBMITTED_DONATION'
        action_taken_date_time = donation_date_time
        result_taken = 'DONATION_PROCESSED_SUCCESSFULLY'
        result_taken_date_time = donation_date_time

        saved_entry = donation_manager.create_donation_log_entry(ip_address, stripe_customer_id, voter_we_vote_id,
                                                                 charge_id, action_taken, action_taken_date_time,
                                                                 result_taken, result_taken_date_time)
        donation_entry_saved = saved_entry['success']
    results = {
        'status': status,
        'success': success,
        'charge_id': charge_id,
        'customer_id': stripe_customer_id,
        'saved_stripe_customer_id': saved_stripe_customer_id,
        'saved_stripe_donation': saved_stripe_donation,
        'donation_entry_saved': donation_entry_saved,
        'monthly_donation': monthly_donation,
        'monthly_donation_plan_id': recurring_donation_saved

    }

    return results
