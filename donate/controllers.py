# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime
import json
import requests
import stripe
from voter.models import fetch_voter_id_from_voter_device_link, VoterAddressManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

stripe.api_key = get_environment_variable("STRIPE_SECRET_KEY")
# STRIPE_URL = get_environment_variable("STRIPE_URL")


def donation_with_stripe_for_api(token):
    try:
        new_customer = stripe.Customer.create(
            source=token,
            description="test customer"
        )

        charge = stripe.Charge.create(
            amount=2000,
            currency="usd",
            description="Monday test charge #2",
            customer=new_customer.id
        )
        # new_customer = StripeCustomerID(customer_id = customer.id)
        # new_customer.save()
        # Tie this to wevote ID

    except stripe.error.CardError:
        # The card has been declined
        pass

    results = {
        'status': "STRIPE_CHARGE_SUCCESSFUL",
        'success': True ,
        'charge_id': charge.id,
        'customer_id': new_customer.id
    }

    return results
