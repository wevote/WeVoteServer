# apis_v1/views/views_donaton.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
from donate.controllers import donation_with_stripe_for_api, donation_process_stripe_webhook_event
import json
from voter.models import fetch_voter_we_vote_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id, positive_value_exists
import stripe
from django.views.decorators.csrf import csrf_exempt

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def donation_with_stripe_view(request):  # donationWithStripe
    """
    Make a charge with a stripe token
    :type request: object
    :param request:
    :return:
    """

    token = request.GET.get('token', '')
    email = request.GET.get('email', '')
    donation_amount = request.GET.get('donation_amount', 0)
    monthly_donation = positive_value_exists(request.GET.get('monthly_donation', False))

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_we_vote_id = ''

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    else:
        print('view voter_we_vote_id is missing')

    if positive_value_exists(token):
        results = donation_with_stripe_for_api(request, token, email, donation_amount, monthly_donation,
                                               voter_we_vote_id)

        json_data = {
            'status': results['status'],
            'success': results['success'],
            'charge_id': results['charge_id'],
            'customer_id': results['customer_id'],
            'saved_donation_in_log': results['donation_entry_saved'],
            'saved_stripe_donation': results['saved_stripe_donation'],
            'monthly_donation': monthly_donation,
            'subscription': results['subscription'],
            'error_message_for_voter': results['error_message_for_voter']

        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    else:
        json_data = {
            'status': "TOKEN_IS_MISSING",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

# TODO: Move the endpoint secret to the environment variables
# Set your secret key: remember to change this to your live secret key in production
# See your keys here: https://dashboard.stripe.com/account/apikeys
# You can find your endpoint's secret in your webhook settings
endpoint_secret = "sk_test_mgeds61AuQ7vGBfwVxFdQqTh"


@csrf_exempt
def donation_stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret)

    except ValueError as e:
        logger.error("apis_v1/views/views_donation.py, Stripe returned \"Invalid payload\": "
                     # TODO: Debug e, and see if there is something worth adding to the log
                     )
        return HttpResponse(status=400)

    except stripe.error.SignatureVerificationError as e:
        logger.error("apis_v1/views/views_donation.py, Stripe returned \"Invalid signature\": "
                     # TODO: Debug e, and see if there is something worth adding to the log
                     )
        return HttpResponse(status=400)

    except:
        logger.error("apis_v1/views/views_donation.py, Stripe returned \"Unknown\": ")
        return HttpResponse(status=400)
    donation_process_stripe_webhook_event(event)

    return HttpResponse(status=200)
