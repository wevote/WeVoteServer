# donate/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import datetime, timezone
from donate.models import DonationManager
from wevote_functions.functions import get_ip_from_headers, positive_value_exists
from wevote_functions.admin import get_logger
from wevote_functions.functions import get_voter_device_id
from voter.models import VoterManager
import json
import stripe
import textwrap


logger = get_logger(__name__)
stripe.api_key = get_environment_variable("STRIPE_SECRET_KEY")


def donation_with_stripe_for_api(request, token, email, donation_amount, monthly_donation, voter_we_vote_id):
    """

    :param request:
    :param token:
    :param email:
    :param donation_amount:
    :param monthly_donation:
    :param voter_we_vote_id:
    :return:
    """
    donation_manager = DonationManager()
    success = False
    saved_stripe_donation = False
    donation_entry_saved = False
    donation_date_time = datetime.today()
    donation_status = 'STRIPE_DONATION_NOT_COMPLETED'
    action_taken = 'VOTER_SUBMITTED_DONATION'
    charge_id = ''
    amount = 0
    currency = ''
    stripe_customer_id = ''
    subscription_saved = 'NOT_APPLICABLE'
    status = ''
    error_message = ''
    funding = ''
    livemode = False
    created = None
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
    exp_month = 0
    exp_year = 0
    last4 = 0
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
    charge = None
    not_loggedin_voter_we_vote_id = None

    ip_address = get_ip_from_headers(request)

    if not positive_value_exists(ip_address):
        ip_address = ''

    if not positive_value_exists(voter_we_vote_id):
        status += "DONATION_WITH_STRIPE_VOTER_WE_VOTE_ID_MISSING "
        error_results = {
            'status':                   status,
            'success':                  success,
            'charge_id':                charge_id,   # Always 0 here
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
            'charge_id':                charge_id,    # Always 0 here
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
                                                                                donation_amount, donation_date_time,
                                                                                email)
                subscription_saved = recurring_donation['voter_subscription_saved']
                status = textwrap.shorten(recurring_donation['status'] + " " + status, width=255, placeholder="...")
                success = recurring_donation['success']
                create_subscription_entry = True
                subscription_id = recurring_donation['subscription_id']
                subscription_plan_id = recurring_donation['subscription_plan_id']
                subscription_created_at = None
                if type(recurring_donation['subscription_created_at']) is int:
                    subscription_created_at = datetime.fromtimestamp(recurring_donation['subscription_created_at'],
                                                                     timezone.utc)
                created = subscription_created_at
                subscription_canceled_at = None
                subscription_ended_at = None
                create_subscription_entry = True
            else:  # One time charge
                charge = stripe.Charge.create(
                    amount=donation_amount,
                    currency="usd",
                    source=token,
                    metadata={'voter_we_vote_id': voter_we_vote_id}
                )
                status = textwrap.shorten("STRIPE_CHARGE_SUCCESSFUL " + status, width=255, placeholder="...")
                create_donation_entry = True
                charge_id = charge.id
                success = positive_value_exists(charge_id)

        if positive_value_exists(charge_id):
            saved_stripe_donation = True
            donation_status = ' DONATION_PROCESSED_SUCCESSFULLY '
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
            logger.debug("Stripe charge successful: " + charge_id + ", amount: " + str(amount) + ", voter_we_vote_id:" +
                         voter_we_vote_id)

    except stripe.error.CardError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status = " STRIPE_STATUS_IS: {http_status} STRIPE_CARD_ERROR_IS: {error_type} " \
                          "STRIPE_MESSAGE_IS: {error_message} " \
                          "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                    error_message=error_from_json['message'])
        status = textwrap.shorten(donation_status + " " + status, width=255, placeholder="...")
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("donation_with_stripe_for_api, CardError: " + error_message)
        # error_text_description = donation_status
    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        donation_status = " STRIPE_STATUS_IS: {http_status} STRIPE_ERROR_IS: {error_type} " \
                          "STRIPE_MESSAGE_IS: {error_message} " \
                          "".format(http_status=e.http_status, error_type=error_from_json['type'],
                                    error_message=error_from_json['message'])
        status = textwrap.shorten(donation_status + " " + status, width=255, placeholder="...")
        error_message = translate_stripe_error_to_voter_explanation_text(e.http_status, error_from_json['type'])
        logger.error("donation_with_stripe_for_api, StripeError : " + donation_status)
    except Exception as err:
        # Something else happened, completely unrelated to Stripe
        donation_status = "A_NON_STRIPE_ERROR_OCCURRED "
        logger.error("donation_with_stripe_for_api threw " + str(err))
        status = textwrap.shorten(donation_status + " " + status, width=255, placeholder="...")
        error_message = 'Your payment was unsuccessful. Please try again later.'
    if "already has the maximum 25 current subscriptions" in status:
        error_message = \
            "No more than 25 active subscriptions are allowed, please delete a subscription before adding another."
        logger.debug("donation_with_stripe_for_api: " + error_message)

    # action_result should be CANCEL_REQUEST_FAILED, CANCEL_REQUEST_SUCCEEDED or DONATION_PROCESSED_SUCCESSFULLY
    action_result = donation_status

    logged_in = is_voter_logged_in(request)
    # print("is_voter_logged_in() = " + str(logged_in))
    if not logged_in:
        not_loggedin_voter_we_vote_id = voter_we_vote_id

    if create_donation_entry:
        # Create the Journal entry for a payment initiated by the UI.  (Automatic payments from the subscription will be
        donation_journal_entry = \
            donation_manager.create_donation_journal_entry("PAYMENT_FROM_UI", ip_address, stripe_customer_id,
                                                           voter_we_vote_id, charge_id, amount, currency, funding,
                                                           livemode, action_taken, action_result, created, failure_code,
                                                           failure_message, network_status, reason, seller_message,
                                                           stripe_type, paid, amount_refunded, refund_count, email,
                                                           address_zip, brand, country, exp_month, exp_year, last4,
                                                           id_card, stripe_object, stripe_status, status, None, None,
                                                           None, None, None, not_loggedin_voter_we_vote_id)
        status = textwrap.shorten(donation_journal_entry['status'] + " " + status, width=255, placeholder="...")

    if create_subscription_entry:
        # Create the Journal entry for a new subscription, with some fields from the intial payment on that subscription
        donation_journal_entry = \
            donation_manager.create_donation_journal_entry("SUBSCRIPTION_SETUP_AND_INITIAL", ip_address,
                                                           stripe_customer_id, voter_we_vote_id, charge_id, amount,
                                                           currency, funding, livemode, action_taken, action_result,
                                                           created, failure_code, failure_message, network_status,
                                                           reason, seller_message,
                                                           stripe_type, paid, amount_refunded, refund_count, email,
                                                           address_zip, brand, country, exp_month, exp_year, last4,
                                                           id_card, stripe_object, stripe_status, status,
                                                           subscription_id, subscription_plan_id,
                                                           subscription_created_at, subscription_canceled_at,
                                                           subscription_ended_at, not_loggedin_voter_we_vote_id)
        donation_entry_saved = donation_journal_entry['success']
        status = textwrap.shorten(donation_journal_entry['status'] + " " + status, width=255, placeholder="...")
        logger.debug("Stripe subscription created successfully: " + subscription_id + ", amount: " + str(amount) +
                     ", voter_we_vote_id:" + voter_we_vote_id)

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


def is_voter_logged_in(request):
    """

    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
    voter_id = voter_results['voter_id']
    if not positive_value_exists(voter_id):
        logger.error("invalid voter_device_id passed to is_voter_logged_in" + voter_device_id)
        return False
    voter = voter_results['voter']
    return voter.is_signed_in()


def translate_stripe_error_to_voter_explanation_text(donation_http_status, error_type):
    """

    :param donation_http_status:
    :param error_type:
    :return:
    """
    donation_manager = DonationManager()
    generic_voter_error_message = 'Your payment was unsuccessful. Please try again later.'

    if donation_http_status == 402:
        error_message_for_voter = donation_manager.retrieve_stripe_card_error_message(error_type)
    else:
        error_message_for_voter = generic_voter_error_message

    return error_message_for_voter


# Get a list of all prior donations by the voter that is associated with this voter_we_vote_id
# If they donated without logging in and then ended the session, then are out of luck for tracking past donations
def donation_history_for_a_voter(voter_we_vote_id):
    """

    :param voter_we_vote_id:
    :return:
    """
    donation_manager = DonationManager()
    donation_list = donation_manager.retrieve_donation_journal_list(voter_we_vote_id)
    refund_days = get_environment_variable("STRIPE_REFUND_DAYS")  # Should be 30, the num of days we will allow refunds

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
                'subscription_canceled_at': str(donation_row.subscription_canceled_at),
                'subscription_ended_at': str(donation_row.subscription_ended_at),
                'refund_days_limit': refund_days,
                'last_charged': str(donation_row.last_charged),
            }
            simple_donation_list.append(json_data)

    return simple_donation_list


def donation_process_stripe_webhook_event(event):
    """
    NOTE: These are the only six events that we handle from the webhook
    :param event:
    :return:
    """
    logger.info("WEBHOOK received: donation_process_stripe_webhook_event: " + event.type)
    # write_event_to_local_file(event);

    if event['type'] == 'charge.succeeded':
        return donation_process_charge(event)
    elif event['type'] == 'customer.subscription.deleted':
        return donation_process_subscription_deleted(event)
    elif event['type'] == 'customer.subscription.updated':
        return donation_process_subscription_updated(event)
    elif event['type'] == 'invoice.payment_succeeded':
        return donation_process_subscription_payment(event)
    elif event['type'] == 'charge.refunded':
        return donation_process_refund_payment(event)
    elif event['type'] == 'invoice.created':
        return donation_process_invoice_created(event)

    logger.info("WEBHOOK ignored: donation_process_stripe_webhook_event: " + event.type)
    return


def write_event_to_local_file(event):
    target = open(event['type'] + "-" + str(datetime.now()) + ".txt", 'w')
    target.write(str(event))
    target.close()
    return


def donation_process_charge(event):           # 'charge.succeeded'
    """

    :param event:
    :return:
    """
    try:
        charge = event['data']['object']
        source = charge['source']
        outcome = charge['outcome']
        customer = charge['customer']
        results = DonationManager.does_donation_journal_charge_exist(charge['id'])

        # Handle stripe test urls with no customer
        if outcome == None:
            outcome = []

        if 'network_status' in outcome:
            network_status = outcome['network_status']
        else:
            network_status = ""
        if customer is None:
            customer = "none"
        else:
            customer = str(charge['customer'])
        if 'reason' in outcome:
            reason = str('reason')
        else:
            reason = 'none'
        if 'seller_message' in outcome:
            seller_message = outcome['seller_message']
        else:
            seller_message = 'none'

            # Charges from subscription payments, won't have our metadata
        try:
            voter_we_vote_id = charge['metadata']['voter_we_vote_id']
            if voter_we_vote_id:
                # Has our metadata?  Then we have already made a journal entry at the time of the donation
                logger.info("Stripe 'charge.succeeded' received for a PAYMENT_FROM_UI -- ignored, charge = " + charge)
                return None
        except Exception:
            voter_we_vote_id = DonationManager.find_we_vote_voter_id_for_stripe_customer(customer)

        if results['success'] and not results['exists']:
            # Create the Journal entry for a payment initiated by an automatic subscription payment.
            DonationManager.create_donation_journal_entry("PAYMENT_AUTO_SUBSCRIPTION", "0.0.0.0",
                                                          customer,
                                                          voter_we_vote_id, charge['id'],
                                                          charge['amount'], charge['currency'], source['funding'],
                                                          charge['livemode'], "",  "",
                                                          datetime.fromtimestamp(charge['created'], timezone.utc),
                                                          str(charge['failure_code']), str(charge['failure_message']),
                                                          network_status, reason, seller_message, event['type'], charge['paid'],
                                                          0, charge['refunds']['total_count'], source['name'],
                                                          source['address_zip'], source['brand'], source['country'],
                                                          source['exp_month'], source['exp_year'],
                                                          int(source['last4']), charge['source']['id'], event['id'],
                                                          charge['status'], "", 'no', None, None, None, None, None)
            logger.debug("Stripe subscription payment from webhook: " + str(charge['customer']) + ", amount: " +
                         str(charge['amount']) + ", last4:" + str(source['last4']))
            DonationManager.update_subscription_with_latest_charge_date(charge['invoice'], charge['created'])

    except stripe.error.StripeError as e:
        body = e.json_body
        error_from_json = body['error']
        logger.error("donation_process_charge, Stripe: " + error_from_json)

    except Exception as err:
        logger.error("donation_process_charge, general: " + str(err))

    return None


def donation_process_subscription_deleted(event):
    """

    :param event:
    :return:
    """
    donation_manager = DonationManager()
    data = event['data']
    subscription = data['object']
    subscription_ended_at = subscription['ended_at']
    subscription_canceled_at = subscription['canceled_at']
    customer_id = subscription['customer']
    subscription_id = subscription['id']

    # At this time we are only supporting the UI for canceling subscriptions
    if subscription_canceled_at is not None or subscription_ended_at is not None:
        donation_manager.mark_subscription_canceled_or_ended(subscription_id, customer_id, subscription_ended_at,
                                                             subscription_canceled_at)
    return None


# Handle this event (in the same way for now) if it comes in from Stripe
def donation_process_subscription_updated(event):
    """

    :param event:
    :return:
    """
    return donation_process_subscription_deleted(event)


def move_donation_info_to_another_voter(from_voter, to_voter):
    """
    Within a session, if the voter donates before logging in, the donations will be created under a new unique
    voter_we_vote_id.  Subsequently when they login, their proper voter_we_vote_id will come into effect.  If we did not
    call this method before the end of the session, those "un-logged-in" donations would not be associated with the voter.
    Unfortunately at this time "un-logged-in" donations created in a session that was ended before logging in will not
    be associated with the correct voter -- we could do this in the future by doing something with email addresses.
    :param from_voter:
    :param to_voter:
    :return:
    """
    status = "MOVE_DONATION_INFO "
    success = False

    if not hasattr(from_voter, "we_vote_id") or not positive_value_exists(from_voter.we_vote_id) \
            or not hasattr(to_voter, "we_vote_id") or not positive_value_exists(to_voter.we_vote_id):
        status = textwrap.shorten("MOVE_DONATION_INFO_MISSING_FROM_OR_TO_VOTER_ID " + status, width=255,
                                  placeholder="...")

        results = {
            'status': status,
            'success': success,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    if from_voter.we_vote_id == to_voter.we_vote_id:
        status += "MOVE_DONATION_INFO-FROM_AND_TO_VOTER_WE_VOTE_IDS_IDENTICAL "

    # All we really need to do is find the donations that are associated with the "from" voter, and change their
    # voter_we_vote_id to the "to" voter.
    results = DonationManager.move_donations_between_donors(from_voter, to_voter)

    return results


# see https://stripe.com/docs/subscriptions/lifecycle
def donation_process_subscription_payment(event):
    dataobject = event['data']['object']
    amount = dataobject['amount_due']
    currency = dataobject['currency']
    customer_id = dataobject['customer']
    plan = dataobject['lines']['data'][0]['plan']
    plan_id = plan['id']

    row_id = DonationManager.check_for_subscription_in_db_without_card_info(customer_id, plan_id)
    if row_id == -1:
        print("Subscription card info is already in db for latest " + plan_id)
        return None

    try:
        customer = stripe.Customer.retrieve(customer_id)
        source = customer['sources']['data'][0]
        id_card = source['id']
        address_zip = source['address_zip']
        brand = source['brand']
        country = source['country']
        exp_month = source['exp_month']
        exp_year = source['exp_year']
        funding = source['funding']
        last4 = source['last4']

        DonationManager.update_subscription_in_db(row_id, amount, currency, id_card, address_zip, brand, country,
                                                  exp_month, exp_year, last4, funding)
    except Exception as err:
        logger.error("donation_process_subscription_payment: " + str(err))

    return None


def donation_process_refund_payment(event):
    # The Stripe webhook has sent a refund event "charge.refunded"
    success = False
    logger.debug("donation_process_refund_payment: " + json.dumps(event))
    dataobject = event['data']['object']
    charge = dataobject['id']
    paid = dataobject['paid']  # boolean
    if paid:
        success = DonationManager.update_journal_entry_for_refund_completed(charge)

    return success


def donation_process_invoice_created(event):
    """
    The only way to associate an incoming automatic payment for a subscription payment
    'invoice.payment_succeeded' is to cache the invoice id number and subscription id when the
    invoice created event arrives.  Then when the 'invoice.payment_succeeded' arrives a few seconds
    later, we can update the subscription 'last_charged' field since we will have cached the
    subscription id
    :param event: The Stripe event
    :return:
    """

    try:
        dataobject = event['data']['object']
        customer_id = dataobject['customer']
        plan = dataobject['lines']['data'][0]['plan']
        donation_plan_id = plan['id']
        subscription_id = dataobject['subscription']
        invoice_id = dataobject['id']
        invoice_date = datetime.fromtimestamp(dataobject['date'], timezone.utc)
        return DonationManager.update_donation_invoice(subscription_id, donation_plan_id, invoice_id,
                                                       invoice_date, customer_id)
    except Exception as e:
        logger.error("donation_process_invoice_created threw " + str(e))

    return

def donation_refund_for_api(request, charge, voter_we_vote_id):
    # The WebApp has requested a refund

    try:
        refund = stripe.Refund.create(
            charge=charge
        )
    except stripe.error.InvalidRequestError as err:
        body = err.json_body
        error_string = body['error']['message']
        logger.error("donation_refund_for_api: " + error_string)
        success = DonationManager.update_journal_entry_for_already_refunded(charge, voter_we_vote_id)
        return success

    except DonationManager.DoesNotExist as err:
        logger.error("donation_refund_for_api returned DoesNotExist for : " + charge)
        return False

    except Exception as err:
        logger.error("donation_refund_for_api: " + str(err))
        return False

    success = DonationManager.update_journal_entry_for_refund(charge, voter_we_vote_id, refund)

    return success


def donation_subscription_cancellation_for_api(request, subscription_id, voter_we_vote_id):
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        results = subscription.delete()
        DonationManager().mark_subscription_canceled_or_ended(subscription['id'], subscription['customer'],
                                                              subscription['ended_at'], subscription['canceled_at'])
        json_returned = {
            'status': results['status'],
            'subscription_id': results['id'],
            'customer_id': results['customer'],
            'canceled_at': results['canceled_at'],
            'ended_at': results['ended_at'],
            'email': results['metadata']['email'],
            'voter_we_vote_id': results['metadata']['voter_we_vote_id'],
            'livemode': results['livemode'],
            'success': True,
        }
    except stripe.error.InvalidRequestError as err:
        # 5/29/17, Does it throw this every time you cancel a valid subscription?
        if "No such subscription:" in str(err):
            logger.info("Marking subscription as canceled due to: " + str(err))

        DonationManager().mark_subscription_canceled_or_ended(subscription['id'], subscription['customer'],
                                                              subscription['ended_at'], subscription['canceled_at'])
        json_returned = {
            'status': "Marking subscription as canceled due to: " + str(err),
            'subscription_id': subscription['id'],
            'customer_id': subscription['customer'],
            'canceled_at': subscription['canceled_at'],
            'ended_at': subscription['ended_at'],
            'email': subscription['metadata']['email'],
            'voter_we_vote_id': subscription['metadata']['voter_we_vote_id'],
            'livemode': subscription['livemode'],
            'success': True,
        }
    except Exception as err:
        logger.error("donation_subscription_cancellation_for_api err " + str(err))
        json_returned = {
            'status': "Error: " + str(err),
            'subscription_id': subscription_id,
            'voter_we_vote_id': voter_we_vote_id,
            'success': False,
        }

    return json_returned
