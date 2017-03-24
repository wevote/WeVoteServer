# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime
from donate.models import DonationManager
import stripe
from wevote_functions.functions import positive_value_exists

stripe.api_key = get_environment_variable("STRIPE_SECRET_KEY")


def donation_with_stripe_for_api(token, email, donation_amount, monthly_donation, voter_we_vote_id):

    donation_manager = DonationManager()
    success = False
    saved_stripe_customer_id = False
    saved_stripe_donation = False
    charge_id = ''
    stripe_customer_id = ''
    # voter_we_vote_id needs to unique and can't be blank in datatable
    voter_we_vote_id = 'test2'
    try:
        customer = stripe.Customer.create(
            source=token,
            email=email
        )

        # put plan query or creation in a manager
        # if monthly_donation:
        #     plan = stripe.Plan.create(
        #         name="Basic Plan",
        #         id="monthly-amount",
        #         interval="month",
        #         currency="usd",
        #         amount=0,
        #     )
        #     # maybe need a dict here to determine what plan to subscribe based on donation_amount
        #     stripe.Subscription.create(
        #         customer=customer.id,
        #         # plan unique ID
        #         plan="basic-monthly"
        #     )
        #
        # else:
        charge = stripe.Charge.create(
            amount=donation_amount,
            currency="usd",
            customer=customer.id
        )
        status = 'STRIPE_CHARGE_SUCCESSFUL'
        success = True
        stripe_customer_id = customer.id
        charge_id = charge.id

    except stripe.error.CardError as e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err = body['error']
        status = "STATUS_IS_%s_AND_ERROR_IS_%s" % e.http_status, err['type']
        pass
    except Exception:
        # Something else happened, completely unrelated to Stripe
        status = "A_NON_STRIPE_ERROR_OCCURRED"
        pass

    if positive_value_exists(stripe_customer_id and charge_id):
        saved_results = donation_manager.create_donate_link_to_voter(stripe_customer_id, voter_we_vote_id)
        saved_stripe_customer_id = saved_results['success']
        charge_processed_successfully = True
        donation_date_time = datetime.today()
        saved_donation = donation_manager.create_donation_from_voter(stripe_customer_id, voter_we_vote_id,
                                                                     donation_amount, email,
                                                                     donation_date_time, charge_id,
                                                                     charge_processed_successfully)
        saved_stripe_donation = saved_donation['success']

    results = {
        'status': status,
        'success': success,
        'charge_id': charge_id,
        'customer_id': stripe_customer_id,
        'saved_stripe_customer_id': saved_stripe_customer_id,
        'saved_stripe_donation': saved_stripe_donation
    }

    return results
