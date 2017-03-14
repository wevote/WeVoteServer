# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime
from donate.models import DonateLinkToVoter, DonationFromVoter, DonationLog, DonationPlanDefinition, DonationSubscription,\
DonationVoterCreditCard
import json
import requests
import stripe
from voter.models import VoterDeviceLinkManager, fetch_voter_we_vote_id_from_voter_id
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

stripe.api_key = get_environment_variable("STRIPE_SECRET_KEY")

def donation_with_stripe_for_api(token, voter_we_vote_id):

    try:
        customer = stripe.Customer.create(
            source=token,
            description="test customer"
        )

        charge = stripe.Charge.create(
            amount=2000,
            currency="usd",
            description="Monday test charge #2",
            customer=customer.id
        )

    except stripe.error.CardError:
        # The card has been declined
        pass

    results = {
        'status': "STRIPE_CHARGE_SUCCESSFUL",
        'success': True ,
        'charge_id': charge.id,
        'customer_id': customer.id
    }

    return results
