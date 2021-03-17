# apis_v1/views/views_donation.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
# from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from stripe_donations.controllers import donation_lists_for_a_voter
# donation_active_paid_plan_retrieve, donation_with_stripe_for_api, \
#     donation_process_stripe_webhook_event, \
#     donation_refund_for_api, donation_subscription_cancellation_for_api, donation_journal_history_for_a_voter
from stripe_donations.controllers import donation_active_paid_plan_retrieve, donation_with_stripe_for_api, \
    donation_process_stripe_webhook_event, \
    donation_refund_for_api, donation_subscription_cancellation_for_api, donation_journal_history_for_a_voter
# from donate.models import DonationManager, OrganizationSubscriptionPlans
from stripe_donations.models import StripeManager
import json
from voter.models import fetch_voter_we_vote_id_from_voter_device_link, VoterManager
import wevote_functions.admin
from wevote_functions.functions import get_voter_device_id, positive_value_exists
import stripe

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def donation_with_stripe_view(request):  # donationWithStripe
    """
    Make a charge with a stripe token. This could either be:
    A) one-time or monthly donation
    B) payment for a subscription plan
    :type request: object
    :param request:
    :return:
    """

    token = request.GET.get('token', '')
    client_ip = request.GET.get('client_ip', '')
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
        logger.error('%s', 'donation_with_stripe_view voter_we_vote_id is missing')

    voter_manager = VoterManager()
    linked_organization_we_vote_id = \
        voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(voter_we_vote_id)

    if positive_value_exists(token):
        results = donation_with_stripe_for_api(request, token, client_ip, email, donation_amount, monthly_donation,
                                               voter_we_vote_id, is_organization_plan, coupon_code, plan_type_enum,
                                               linked_organization_we_vote_id)

        org_subs_already_exists = results['org_subs_already_exists'] if \
            'org_subs_already_exists' in results else False

        active_results = donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id)
        active_paid_plan = active_results['active_paid_plan']
        # donation_plan_definition_list_json = active_results['donation_plan_definition_list_json']
        donation_subscription_list, donation_payments_list = donation_lists_for_a_voter(voter_we_vote_id)
        error_message_for_voter = ''
        if 'error_message_for_voter' in results:
            error_message_for_voter = results['error_message_for_voter']
        json_data = {
            'status': results['status'],
            'success': results['success'],
            'active_paid_plan': active_paid_plan,
            'amount_paid': results['amount_paid'],
            'charge_id': results['charge_id'],
            'customer_id': results['customer_id'],
            # 'donation_list': donation_journal_history_for_a_voter(voter_we_vote_id),
            # 'donation_plan_definition_list':    donation_plan_definition_list_json,
            'donation_subscription_list': donation_subscription_list,
            'donation_payments_list': donation_payments_list,
            'error_message_for_voter': error_message_for_voter,
            'monthly_donation': monthly_donation,
            'organization_saved': results['organization_saved'],
            'org_subs_already_exists': org_subs_already_exists,
            'plan_type_enum': results['plan_type_enum'],
            'saved_donation_in_log': results['donation_entry_saved'],
            'saved_stripe_donation': results['saved_stripe_donation'],
            'subscription': results['subscription'],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    else:
        json_data = {
            'status': "TOKEN_IS_MISSING ",
            'success': False,
            'amount_paid': 0,
            'error_message_for_voter': 'Cannot connect to payment processor.',
            'organization_saved': False,
            'plan_type_enum': '',
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
                'donation_list': donation_journal_history_for_a_voter(voter_we_vote_id),
                'voter_we_vote_id': voter_we_vote_id,
            }
        else:
            logger.error('%s', 'donation_refund_view voter_we_vote_id is missing')
            json_data = {
                'status': "VOTER_WE_VOTE_ID_IS_MISSING",
                'success': False,
            }
    else:
        logger.error('%s', 'donation_refund_view stripe_charge_id is missing')
        json_data = {
            'status': "STRIPE_CHARGE_ID_IS_MISSING",
            'success': False,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def donation_cancel_subscription_view(request):  # donationCancelSubscription
    """
    Cancel a stripe subscription or subscription plan
    :type request: object
    :param request:
    :return:
    """

    plan_type_enum = request.GET.get('plan_type_enum', '')
    stripe_subscription_id = request.GET.get('stripe_subscription_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
        if len(voter_we_vote_id) > 0:
            json_data = donation_subscription_cancellation_for_api(
                voter_we_vote_id, plan_type_enum=plan_type_enum, stripe_subscription_id=stripe_subscription_id)
        else:
            logger.error('%s', 'donation_cancel_subscription_view voter_we_vote_id is missing')
            json_data = {
                'status': "VOTER_WE_VOTE_ID_IS_MISSING ",
                'success': False,
            }
    else:
        logger.error('%s', 'donation_cancel_subscription_view stripe_subscription_id is missing')
        json_data = {
            'status': "STRIPE_SUBSCRIPTION_ID_IS_MISSING ",
            'success': False,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


# Using ngrok to test Stripe Webhook
# https://a9a761d9.ngrok.io/apis/v1/donationStripeWebhook/
# http://a9a761d9.ngrok.io -> localhost:8000
# Important!!!!!!!   django urls without a trailing slash do not redirect   !!!!!!
# The webhook in the stripe console HAS TO END WITH A '/' or you are doomed to waste a bunch of time!
@csrf_exempt
def donation_stripe_webhook_view(request):
    # print('first line in donation_stripe_webhook')
    payload = request.body.decode('utf-8')

    try:
        stripe.api_key = get_environment_variable("STRIPE_SECRET_KEY")
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

    except ValueError as e:
        logger.error("donation_stripe_webhook_view, Stripe returned ValueError: " + str(e))
        return HttpResponse(status=400)

    except stripe.error.SignatureVerificationError as err:
        logger.error("donation_stripe_webhook_view, Stripe returned SignatureVerificationError: " + str(err))
        return HttpResponse(status=400)

    except Exception as err:
        logger.error("donation_stripe_webhook_view: " + str(err))
        return HttpResponse(status=400)

    donation_process_stripe_webhook_event(event)

    return HttpResponse(status=200)


def donation_history_list_view(request):   # donationHistory
    """
    Get the donor history list for a voter
    :type request: object
    :param request:
    :return:
    """

    stripe_subscription_id = request.GET.get('stripe_subscription_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    status = ""
    active_paid_plan = {
        'last_amount_paid':         0,
        'plan_type_enum':           '',
        'subscription_active':      False,
        'subscription_canceled_at': '',
        'subscription_ended_at':    '',
        'stripe_subscription_id':          stripe_subscription_id,
    }
    # donation_list = []
    # donation_plan_definition_list_json = []
    donation_subscription_list = []
    donation_payments_list = []

    if positive_value_exists(voter_device_id):
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if not results['voter_found']:
            logger.error("donation_history_list received invalid voter_device_id: " + voter_device_id)
            status += "DONATION_HISTORY_LIST-INVALID_VOTER_DEVICE_ID_PASSED "
            success = False
        else:
            success = True
            voter = results['voter']
            voter_we_vote_id = voter.we_vote_id
            linked_organization_we_vote_id = voter.linked_organization_we_vote_id

            donation_subscription_list, donation_payments_list = donation_lists_for_a_voter(voter_we_vote_id)
            # donation_list = donation_journal_history_for_a_voter(voter_we_vote_id)

            active_results = donation_active_paid_plan_retrieve(linked_organization_we_vote_id, voter_we_vote_id)
            active_paid_plan = active_results['active_paid_plan']
            # donation_plan_definition_list_json = active_results['donation_plan_definition_list_json']

        json_data = {
            'active_paid_plan':                 active_paid_plan,
            'donation_subscription_list':       donation_subscription_list,
            'donation_payments_list':           donation_payments_list,
            # 'donation_list':                    donation_list,
            # 'donation_plan_definition_list':    donation_plan_definition_list_json,
            'status':                           status,
            'success':                          success,
        }
    else:
        logger.error('%s', 'donation_history_list stripe_subscription_id is missing')
        json_data = {
            'active_paid_plan': active_paid_plan,
            'donation_list': [],
            'donation_plan_definition_list': [],
            'status': "DONATION_HISTORY_LIST-STRIPE_SUBSCRIPTION_ID_IS_MISSING",
            'success': False,
        }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


# def coupon_summary_retrieve_for_api_view(request):  # couponSummaryRetrieve
#     coupon_code = request.GET.get('coupon_code', '')
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#
#     if positive_value_exists(voter_device_id):
#         voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
#         json_data = DonationManager.retrieve_coupon_summary(coupon_code)
#     else:
#         json_data = {
#             'success': False,
#             'status': "coupon_summary_retrieve_for_api_view received bad voter_device_id",
#         }
#
#     return HttpResponse(json.dumps(json_data), content_type='application/json')
#
#
# def default_pricing_for_api_view(request):  # defaultPricing
#     json_data = DonationManager.retrieve_default_pricing()
#
#     return HttpResponse(json.dumps(json_data), content_type='application/json')
#
#
# def validate_coupon_for_api_view(request):  # validateCoupon
#     plan_type_enum = request.GET.get('plan_type_enum', '')
#     coupon_code = request.GET.get('coupon_code', '')
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#     print("validate_coupon_for_api_view, plan_type_enum: " + plan_type_enum + ", coupon_code: " + coupon_code)
#
#     if positive_value_exists(voter_device_id):
#         voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
#         json_data = DonationManager.validate_coupon(plan_type_enum, coupon_code)
#     else:
#         json_data = {
#             'success': False,
#             'status': "validate_coupon_for_api_view received bad voter_device_id",
#         }
#
#     return HttpResponse(json.dumps(json_data), content_type='application/json')
#
#
# def create_new_plan_for_api_view(request):
#     authority_required = {'admin'}
#     if not voter_has_authority(request, authority_required):
#         return redirect_to_sign_in_page(request, authority_required)
#
#     coupon_code = request.GET.get('couponCode')
#     plan_type_enum = request.GET.get('planTypeEnum')
#     hidden_plan_comment = request.GET.get('hiddenPlanComment')
#     coupon_applied_message = request.GET.get('couponAppliedMessage')
#     monthly_price_stripe = request.GET.get('monthlyPriceStripe')
#     monthly_price_stripe = monthly_price_stripe if monthly_price_stripe != '' else 0
#     annual_price_stripe = request.GET.get('annualPriceStripe')
#     annual_price_stripe = annual_price_stripe if annual_price_stripe != '' else 0
#     master_feature_package = request.GET.get('masterFeatureType')
#     features_provided_bitmap = request.GET.get('featuresProvidedBitmap')
#     coupon_expires_date = request.GET.get('couponExpiresDate', None)
#     if len(coupon_expires_date) == 0:
#         coupon_expires_date = None
#     print("create_new_plan_for_api_view, plan_type_enum: " + plan_type_enum + ", coupon_code: " + coupon_code)
#     plan_on_stage = 0
#
#     voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
#     if positive_value_exists(voter_device_id):
#         voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
#         plan_on_stage = OrganizationSubscriptionPlans.objects.create(
#             coupon_code=coupon_code,
#             plan_type_enum=plan_type_enum,
#             hidden_plan_comment=hidden_plan_comment,
#             coupon_applied_message=coupon_applied_message,
#             monthly_price_stripe=monthly_price_stripe,
#             annual_price_stripe=annual_price_stripe,
#             master_feature_package=master_feature_package,
#             features_provided_bitmap=features_provided_bitmap,
#             coupon_expires_date=coupon_expires_date)
#         status = "create_new_plan_for_api_view succeeded"
#     else:
#         status = "create_new_plan_for_api_view received bad voter_device_id",
#
#     json_data = {
#         'success': positive_value_exists(plan_on_stage.id),
#         'status': status,
#         'id': plan_on_stage.id if positive_value_exists(plan_on_stage.id) else 0.
#         }
#
#     return HttpResponse(json.dumps(json_data), content_type='application/json')
#

# def delete_plan_for_api_view(request):
#     authority_required = {'admin'}
#     if not voter_has_authority(request, authority_required):
#         return redirect_to_sign_in_page(request, authority_required)
#
#     id = request.GET.get('id')
#     print("delete_coupon_for_api_view, sql id: " + id)
#
#     try:
#         if positive_value_exists(id):
#             OrganizationSubscriptionPlans.objects.filter(id=id).delete()
#             status = "DELETE_PLAN_SUCCESSFUL"
#             success = True
#         else:
#             status = "DELETE_PLAN-MISSING_ID"
#             success = False
#     except Exception as e:
#         status = "DELETE_PLAN-DATABASE_DELETE_EXCEPTION"
#         success = False
#
#     json_data = {
#         'success': success,
#         'status': status,
#         'id': id,
#         }
#
#     return HttpResponse(json.dumps(json_data), content_type='application/json')


def does_paid_subscription_exist_for_api(request):  # doesOrgHavePaidPlan
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_we_vote_id = ''

    if positive_value_exists(voter_device_id):
        voter_we_vote_id = fetch_voter_we_vote_id_from_voter_device_link(voter_device_id)
    else:
        logger.error('%s', 'donation_with_stripe_view voter_we_vote_id is missing')
    voter_manager = VoterManager()
    organization_we_vote_id = voter_manager.fetch_linked_organization_we_vote_id_by_voter_we_vote_id(voter_we_vote_id)
    found_live_paid_subscription_for_the_org = StripeManager.does_paid_subscription_exist(organization_we_vote_id)

    json_data = {
        'org_has_active_paid_plan': found_live_paid_subscription_for_the_org,
        'success': True,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
