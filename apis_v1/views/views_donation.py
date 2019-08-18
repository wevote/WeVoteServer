# apis_v1/views/views_donaton.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from config.base import get_environment_variable
from django.http import HttpResponse
from donate.controllers import donation_with_stripe_for_api, donation_process_stripe_webhook_event, \
    donation_refund_for_api, donation_subscription_cancellation_for_api, donation_history_for_a_voter
from voter.models import VoterManager
from donate.models import DonationManager
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
    is_organization_plan = positive_value_exists(request.GET.get('is_organization_plan', False))
    coupon_code = request.GET.get('coupon_code', '')
    plan_type_enum = request.GET.get('plan_type_enum', '')

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_we_vote_id = ''

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    else:
        logger.error('donation_with_stripe_view voter_we_vote_id is missing')

    linked_organization_we_vote_id = VoterManager().retrieve_linked_organization_by_voter_we_vote_id(voter_we_vote_id)

    if positive_value_exists(token):
        results = donation_with_stripe_for_api(request, token, email, donation_amount, monthly_donation,
                                               voter_we_vote_id, is_organization_plan, coupon_code, plan_type_enum,
                                               linked_organization_we_vote_id)

        org_subs_already_exists = results['org_subs_already_exists'] if \
            'org_subs_already_exists' in results else False
        json_data = {
            'status': results['status'],
            'success': results['success'],
            'charge_id': results['charge_id'],
            'customer_id': results['customer_id'],
            'saved_donation_in_log': results['donation_entry_saved'],
            'saved_stripe_donation': results['saved_stripe_donation'],
            'monthly_donation': monthly_donation,
            'subscription': results['subscription'],
            'donation_list': donation_history_for_a_voter(voter_we_vote_id),
            'error_message_for_voter': results['error_message_for_voter'],
            'org_subs_already_exists': org_subs_already_exists
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    else:
        json_data = {
            'status': "TOKEN_IS_MISSING",
            'success': False,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def donation_refund_view(request):  # donationRefund
    """
    Refund a stripe charge
    :type request: object
    :param request:
    :return:
    """

    charge_id = request.GET.get('charge', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
        if len(charge_id) > 1:
            results = donation_refund_for_api(request, charge_id, voter_we_vote_id)
            json_data = {
                'success': str(results),
                'charge_id': charge_id,
                'donation_list': donation_history_for_a_voter(voter_we_vote_id),
                'voter_we_vote_id': voter_we_vote_id,
            }
        else:
            logger.error('donation_refund_view voter_we_vote_id is missing')
            json_data = {
                'status': "VOTER_WE_VOTE_ID_IS_MISSING",
                'success': False,
            }
    else:
        logger.error('donation_refund_view stripe_charge_id is missing')
        json_data = {
            'status': "STRIPE_CHARGE_ID_IS_MISSING",
            'success': False,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def donation_cancel_subscription_view(request):  # donationCancelSubscription
    """
    Cancel a stripe subscription
    :type request: object
    :param request:
    :return:
    """

    subscription_id = request.GET.get('subscription_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
        if len(subscription_id) > 0:
            json_data = donation_subscription_cancellation_for_api(request, subscription_id, voter_we_vote_id)
        else:
            logger.error('donation_cancel_subscription_view voter_we_vote_id is missing')
            json_data = {
                'status': "VOTER_WE_VOTE_ID_IS_MISSING",
                'success': False,
            }
    else:
        logger.error('donation_cancel_subscription_view stripe_subscription_id is missing')
        json_data = {
            'status': "STRIPE_SUBSCRIPTION_ID_IS_MISSING",
            'success': False,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


# Using ngrok to test Stripe Webhook
# https://a9a761d9.ngrok.io/apis/v1/donationStripeWebhook/
# http://a9a761d9.ngrok.io -> localhost:8000
@csrf_exempt
def donation_stripe_webhook_view(request):
    payload = request.body.decode('utf-8')
    if 'HTTP_STRIPE_SIGNATURE' in request.META:
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    else:
        sig_header = ""
    endpoint_secret = get_environment_variable("STRIPE_SIGNING_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

    except ValueError as e:
        logger.error("donation_stripe_webhook_view, Stripe returned 'Invalid payload'")
        return HttpResponse(status=400)

    except stripe.error.SignatureVerificationError as err:
        logger.error("donation_stripe_webhook_view, Stripe returned SignatureVerificationError: " + str(err))
        return HttpResponse(status=400)

    except Exception as err:
        logger.error("donation_stripe_webhook_view: " + str(err))
        return HttpResponse(status=400)

    donation_process_stripe_webhook_event(event)

    return HttpResponse(status=200)


def donation_history_list_view(request):
    """
    Get the donor history list for a voter
    :type request: object
    :param request:
    :return:
    """

    subscription_id = request.GET.get('subscription_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
        if not positive_value_exists(voter_we_vote_id):
            logger.error("donation_history_list received invalid voter_device_id: " + voter_device_id)
            status = "DONATION_HISTORY_LIST INVALID VOTER_DEVICE_ID PASSED"
            success = False
        else:
            status = "SUCCESSFULY RETRIEVED DONATION HISTORY"
            success = True

        donation_list = donation_history_for_a_voter(voter_we_vote_id)

        json_data = {
            'donation_list': donation_list,
            'status': status,
            'success': success,
        }
    else:
        logger.error('donation_history_list stripe_subscription_id is missing')
        json_data = {
            'donation_list': [],
            'status': "DONATION_HISTORY_LIST STRIPE_SUBSCRIPTION_ID_IS_MISSING",
            'success': False,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')

def validate_coupon_for_api_view(request):
    plan_type_enum = request.GET.get('plan_type_enum', '')
    coupon_code = request.GET.get('coupon_code', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    print("validate_coupon_for_api_view, plan_type_enum: " + plan_type_enum + ", coupon_code: " + coupon_code)

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
        json_data = DonationManager.validate_coupon(plan_type_enum, coupon_code)
    else:
        json_data = {
            'success': False,
            'status': "validate_coupon_for_api_view received bad voter_device_id",
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
