# donate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
import stripe

logger = wevote_functions.admin.get_logger(__name__)

SAME_DAY_MONTHLY = 'SAME_DAY_MONTHLY'
SAME_DAY_ANNUALLY = 'SAME_DAY_ANNUALLY'
BILLING_FREQUENCY_CHOICES = ((SAME_DAY_MONTHLY, 'SAME_DAY_MONTHLY'),
                             (SAME_DAY_ANNUALLY, 'SAME_DAY_ANNUALLY'))
CURRENCY_USD = 'usd'
CURRENCY_CAD = 'cad'
CURRENCY_CHOICES = ((CURRENCY_USD, 'usd'),
                    (CURRENCY_CAD, 'cad'))

# Stripes currency support https://support.stripe.com/questions/which-currencies-does-stripe-support


class DonateLinkToVoter(models.Model):
    """
    This is a generated table with customer ID's created when a stripe donation is made for the first time
    """
    # The unique customer id from a stripe donation
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255,
                                          unique=True, null=False, blank=False)
    # There are scenarios where a voter_we_vote_id might have multiple customer_id's
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=False, null=False,
                                        blank=False)


class DonationPlanDefinition(models.Model):
    """
    This is a generated table with admin created donation plans that users can subscribe to (recurring donations)
    """
    donation_plan_id = models.CharField(verbose_name="unique recurring donation plan id", default="", max_length=255,
                                        null=False, blank=False)
    plan_name = models.CharField(verbose_name="donation plan name", max_length=255, null=False, blank=False)
    # Don't think this is necessary, based on how recurring donation options are setup in webapp
    # plan_name_visible_to_voter = models.CharField(verbose_name="plan name visible to user", max_length=255,
    #                                               null=False, blank=False)
    # Stripe uses integer pennies for amount (ex: 2000 = $20.00)
    base_cost = models.PositiveIntegerField(verbose_name="recurring donation amount", default=0, null=False)
    billing_interval = models.CharField(verbose_name="recurring donation frequency", max_length=255,
                                        choices=BILLING_FREQUENCY_CHOICES,
                                        null=True, blank=True)
    currency = models.CharField(verbose_name="currency", max_length=255, choices=CURRENCY_CHOICES, default=CURRENCY_USD,
                                null=False, blank=False)
    donation_plan_is_active = models.BooleanField(verbose_name="status of recurring donation plan", default=True,
                                                  null=False, blank=False)


class DonationSubscription(models.Model):
    """
    This is a generated table with all users who are making recurring donations
    """
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255,
                                          unique=False, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", unique=False, null=False,
                                        max_length=255, blank=False)
    donation_plan_id = models.CharField(verbose_name="unique recurring donation plan id", default="",
                                        max_length=255, null=False, blank=False)
    start_date_time = models.DateField(verbose_name="subscription start date", auto_now=False,
                                       auto_now_add=True)
    subscription_id = models.CharField(verbose_name="stripe unique subscription id", max_length=32,
                                       default="", null=False, blank=False)
    subscription_ended_at = models.DateField(verbose_name="subscription ended date", null=True)
    subscription_canceled_at = models.DateField(verbose_name="subscription canceled date", null=True)
    subscription_livemode = models.BooleanField(verbose_name="subscription was made in live mode", default=False,
                                                null=False, blank=False)
    subscription_update = models.PositiveIntegerField(verbose_name="number of updates to this subscription",
                                                       default=0, null=False)  # for when we get webhook updates

class DonationVoterCreditCard(models.Model):
    """
    This is a generated table with donor credit card details
    """
    stripe_card_id = models.CharField(verbose_name="stripe unique credit card id", max_length=255, unique=True,
                                      null=False, blank=False)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255, unique=False,
                                          null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=False, null=False)
    expiration_date_time = models.DateField(verbose_name="credit card expiration date", auto_now=False,
                                            auto_now_add=False)
    last_four_digits = models.PositiveIntegerField(verbose_name="recurring donation amount", default=0, null=False)
    voter_name_on_credit_card = models.CharField(verbose_name="users name on credit card", max_length=255, default="",
                                                 null=False, blank=False)


class DonationFromVoter(models.Model):
    """
    This is a generated table with all donation details
    """
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255,
                                          unique=False, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=False, null=False,
                                        blank=False)
    normalized_email_address = models.EmailField(verbose_name='email address', max_length=254, null=True, blank=True,
                                                 unique=False)
    donation_amount = models.PositiveIntegerField(verbose_name="donation amount", default=0, null=False)
    donation_date_time = models.DateTimeField(verbose_name="donation timestamp", auto_now=False, auto_now_add=True)
    stripe_card_id = models.CharField(verbose_name="stripe unique credit card id", max_length=255, unique=False,
                                      null=False, blank=False)
    charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=255, default="",
                                 null=True, blank=True)
    charge_to_be_processed = models.BooleanField(verbose_name="charge needs to be processed", default=False,
                                                 blank=False)
    charge_processed_successfully = models.BooleanField(verbose_name="donation completed successfully", default=False,
                                                        blank=False)
    charge_cancel_request = models.BooleanField(verbose_name="user wants to cancel donation", default=False,
                                                blank=False)
    charge_failed_requires_voter_action = models.BooleanField(verbose_name="donation failed, requires user action",
                                                              default=False, blank=False)
    charge_refunded = models.BooleanField(verbose_name="A refund was processed successfully", default=False,
                                          blank=False)


class DonationLog(models.Model):
    """
    This is a generated table that will log various donation activity
    """
    ip_address = models.GenericIPAddressField(verbose_name="user ip address", protocol='both', unpack_ipv4=False,
                                              max_length=255, null=True, blank=True, unique=False)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255,
                                          unique=False, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=False, null=False,
                                        blank=False)
    charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=255, default="",
                                 null=True, blank=True)
    action_taken = models.CharField(verbose_name="action taken", max_length=255, default="", null=True, blank=True)
    action_result = models.CharField(verbose_name="action result", max_length=255, default="", null=True, blank=True)
    action_taken_date_time = models.DateTimeField(verbose_name="action taken timestamp", auto_now=False,
                                                  auto_now_add=True)
    action_result_date_time = models.DateTimeField(verbose_name="action result timestamp", auto_now=False,
                                                   auto_now_add=True)
    error_text_description = models.TextField(verbose_name="internal message describing error in detail", null=True,
                                              blank=True)
    error_message_for_voter = models.TextField(verbose_name="detailed card error message shown to voter", null=True,
                                               blank=True)


class DonationHistory(models.Model):
    """
     This is a generated table that will tracks donation and refund activity
     """
    ip_address = models.GenericIPAddressField(verbose_name="user ip address", protocol='both', unpack_ipv4=False,
                                              null=True, blank=True, unique=False)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=32,
                                          unique=False, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, unique=False, null=False,
                                        blank=False)
    charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=32, default="",
                                 null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name="donation amount", default=0, null=False)
    currency = models.CharField(verbose_name="donation currency country code", max_length=8, default="", null=True,
                                blank=True)
    one_time_donation = models.BooleanField(
        verbose_name="True: one time donation, False: a payment for a recurring donation", default=False, blank=False)
    subscription_id = models.CharField(verbose_name="stripe unique subscription id", max_length=32, default="",
                                       unique=False, null=True, blank=True)
    funding = models.CharField(verbose_name="stripe returns 'credit' also might be debit, etc", max_length=32,
                               default="", null=True, blank=True)
    livemode = models.BooleanField(verbose_name="True: Live transaction, False: Test transaction", default=False,
                                   blank=False)
    action_taken = models.CharField(verbose_name="action taken", max_length=64, default="", null=True, blank=True)
    action_result = models.CharField(verbose_name="action result", max_length=64, default="", null=True, blank=True)
    created = models.DateTimeField(verbose_name="stripe record creation timestamp", auto_now=False,
                                   auto_now_add=False)
    failure_code = models.CharField(verbose_name="failure code reported by stripe", max_length=32, default="",
                                    null=True, blank=True)
    failure_message = models.CharField(verbose_name="failure message reported by stripe", max_length=255, default="",
                                       null=True, blank=True)
    network_status = models.CharField(verbose_name="network status reported by stripe", max_length=64, default="",
                                      null=True, blank=True)
    reason = models.CharField(verbose_name="reason for failure reported by stripe", max_length=255, default="",
                              null=True, blank=True)
    seller_message = models.CharField(verbose_name="plain text message to us from stripe", max_length=255, default="",
                                      null=True, blank=True)
    stripe_type = models.CharField(verbose_name="authorization outcome message to us from stripe", max_length=64,
                                   default="", null=True, blank=True)
    paid = models.CharField(verbose_name="payment outcome message to us from stripe", max_length=64, default="",
                            null=True, blank=True)
    amount_refunded = models.PositiveIntegerField(verbose_name="refund amount", default=0, null=False)
    refund_count = models.PositiveIntegerField(
        verbose_name="Number of refunds, in the case of partials (currently not supported)", default=0, null=False)
    name = models.CharField(verbose_name="stripe returns the donor's email address as a name", max_length=255,
                            default="", null=True, blank=True)
    address_zip = models.CharField(verbose_name="stripe returns the donor's zip code", max_length=32, default="",
                                   null=True, blank=True)
    brand = models.CharField(verbose_name="the brand of the credit card, eg. Visa, Amex", max_length=32, default="",
                             null=True, blank=True)
    country = models.CharField(verbose_name="the country code of the bank that issued the credit card", max_length=8,
                               default="", null=True, blank=True)
    exp_month = models.PositiveIntegerField(verbose_name="the expiration month of the credit card", default=0,
                                            null=False)
    exp_year = models.PositiveIntegerField(verbose_name="the expiration year of the credit card", default=0, null=False)
    last4 = models.PositiveIntegerField(verbose_name="the last 4 digits of the credit card", default=0, null=False)
    id_card = models.CharField(verbose_name="stripe's internal id code for the credit card", max_length=32, default="",
                               null=True, blank=True)
    stripe_object = models.CharField(verbose_name="stripe returns 'card' for card, maybe different for bitcoin, etc.",
                                     max_length=32, default="", null=True, blank=True)
    stripe_status = models.CharField(verbose_name="status string reported by stripe", max_length=64, default="",
                                     null=True, blank=True)
    status = models.CharField(verbose_name="our generated status message", max_length=255, default="", null=True,
                             blank=True)


class DonationManager(models.Model):

    def create_donate_link_to_voter(self, stripe_customer_id, voter_we_vote_id):

        new_customer_id_created = False

        if not voter_we_vote_id:
            success = False
            status = 'MISSING_VOTER_WE_VOTE_ID'
        else:
            try:
                new_customer_id_created = DonateLinkToVoter.objects.create(
                    stripe_customer_id=stripe_customer_id, voter_we_vote_id=voter_we_vote_id)
                success = True
                status = 'STRIPE_CUSTOMER_ID_SAVED '
            except:
                success = False
                status = 'STRIPE_CUSTOMER_ID_NOT_SAVED '

        saved_results = {
            'success': success,
            'status': status,
            'new_stripe_customer_id': new_customer_id_created
        }
        return saved_results

    def create_donation_from_voter(self, stripe_customer_id, voter_we_vote_id, donation_amount, email,
                                   donation_date_time, charge_id, charge_processed_successfully):

        new_donation_from_voter_created = False
        stripe_card_id = 'tbd'
        charge_to_be_processed = False
        charge_cancel_request = False
        charge_failed_requires_voter_action = False
        charge_refunded = False

        try:
            new_donation_from_voter_created = DonationFromVoter.objects.create(
                stripe_customer_id=stripe_customer_id,
                voter_we_vote_id=voter_we_vote_id,
                normalized_email_address=email,
                donation_amount=donation_amount,
                donation_date_time=donation_date_time,
                stripe_card_id=stripe_card_id,
                charge_id=charge_id,
                charge_to_be_processed=charge_to_be_processed,
                charge_processed_successfully=charge_processed_successfully,
                charge_cancel_request=charge_cancel_request,
                charge_failed_requires_voter_action=charge_failed_requires_voter_action,
                charge_refunded=charge_refunded)

            success = True
            status = 'STRIPE_DONATION_FROM_VOTER_SAVED'
        except:
            success = False
            status = 'STRIPE_DONATION_FROM_VOTER_NOT_SAVED'

        saved_donation = {
            'success': success,
            'status': status,
            'new_stripe_donation': new_donation_from_voter_created
        }
        return saved_donation

    def retrieve_stripe_customer_id(self, voter_we_vote_id):

        stripe_customer_id = ''
        status = ''
        success = bool
        if positive_value_exists(voter_we_vote_id):
            try:
                stripe_customer_id_queryset = DonateLinkToVoter.objects.filter(
                    voter_we_vote_id=voter_we_vote_id).values()
                stripe_customer_id = stripe_customer_id_queryset[0]['stripe_customer_id']
                # print("model stripe_customer_id_query " + stripe_customer_id)
                if positive_value_exists(stripe_customer_id):
                    success = True
                    status = "STRIPE_CUSTOMER_ID_RETRIEVED"
                else:
                    success = False
                    status = "EXISTING_STRIPE_CUSTOMER_ID_NOT_FOUND"
            except Exception as e:
                success = False
                status = "STRIPE_CUSTOMER_ID_RETRIEVAL_ATTEMPT_FAILED"

        results = {
            'success': success,
            'status': status,
            'stripe_customer_id': stripe_customer_id,
        }
        return results

    def create_donation_log_entry(self, ip_address, stripe_customer_id, voter_we_vote_id, charge_id, action_taken,
                                  action_taken_date_time, action_result, action_result_date_time,
                                  error_text_description, error_message_for_voter):

        new_donation_entry_created = False
        # action_taken should be VOTER_SUBMITTED_DONATION, VOTER_CANCELED_DONATION or CANCEL_REQUEST_SUBMITTED
        # action_result should be CANCEL_REQUEST_FAILED, CANCEL_REQUEST_SUCCEEDED or DONATION_PROCESSED_SUCCESSFULLY
        action_taken = action_taken[:75]
        action_result = action_result[:75]

        try:
            new_donation_entry_created = DonationLog.objects.create(
                ip_address=ip_address, stripe_customer_id=stripe_customer_id, voter_we_vote_id=voter_we_vote_id,
                charge_id=charge_id, action_taken=action_taken, action_taken_date_time=action_taken_date_time,
                action_result=action_result, action_result_date_time=action_result_date_time,
                error_text_description=error_text_description, error_message_for_voter=error_message_for_voter)
            success = True
            status = 'DONATION_LOG_ENTRY_SAVED'
        except Exception as e:
            success = False
            status = 'DONATION_LOG_ENTRY_NOT_SAVED'

        saved_results = {
            'success': success,
            'status': status,
            'donation_entry_saved': new_donation_entry_created
        }
        return saved_results

    def retrieve_or_create_recurring_donation_plan(self, donation_amount):

        recurring_donation_plan_id = "monthly-" + str(donation_amount)
        # plan_name = donation_plan_id + " Plan"
        billing_interval = "monthly"
        currency = "usd"
        donation_plan_is_active = True
        exception_multiple_object_returned = False
        status = ''
        stripe_plan_id = ''
        try:
            # the donation plan needs to exist in two places: our stripe account and our database
            # plans can be created here or in our stripe account dashboard
            donation_plan_query, is_new = DonationPlanDefinition.objects.get_or_create(
                donation_plan_id=recurring_donation_plan_id,
                plan_name=recurring_donation_plan_id,
                base_cost=donation_amount,
                billing_interval=billing_interval,
                currency=currency,
                donation_plan_is_active=donation_plan_is_active)
            if is_new:
                # if a donation plan is not found, we've added it to our database
                success = True
                status += 'SUBSCRIPTION_PLAN_CREATED_IN_DATABASE '
            else:
                # if it is found, do nothing - no need to update
                success = True
                status += 'DONATION_PLAN_ALREADY_EXISTS_IN_DATABASE '

            plan_id_query = stripe.Plan.retrieve(recurring_donation_plan_id)
            if positive_value_exists(plan_id_query.id):
                stripe_plan_id = plan_id_query.id
                print("plan_id_query.id " + plan_id_query.id)
        except DonationManager.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            success = False
            status += 'MULTIPLE_MATCHING_SUBSCRIPTION_PLANS_FOUND'
            exception_multiple_object_returned = True

        except stripe.error.StripeError:
            pass
            # TODO specific error handling

        if not positive_value_exists(stripe_plan_id):
            # if plan doesn't exist in stripe, we need to create it (note it's already been created in database)
            plan = stripe.Plan.create(
                amount=donation_amount,
                interval="month",
                currency="usd",
                name=recurring_donation_plan_id,
                id=recurring_donation_plan_id,
            )
            if plan.id:
                success = True
                status += 'SUBSCRIPTION_PLAN_CREATED_IN_STRIPE'
            else:
                success = False
                status += 'SUBSCRIPTION_PLAN_NOT_CREATED_IN_STRIPE'
        results = {
            'success': success,
            'status': status,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'recurring_donation_plan_id': recurring_donation_plan_id,
        }
        return results

    def create_donation_history_entry(
            self, ip_address, stripe_customer_id, voter_we_vote_id, charge_id, amount, currency, one_time_donation,
            subscription_id, funding, livemode, action_taken, action_result, created, failure_code, failure_message,
            network_status, reason, seller_message, stripe_type, paid, amount_refunded, refund_count, name, address_zip,
            brand, country, exp_month, exp_year, last4, id_card, stripe_object, stripe_status, status):

        new_history_entry = 0
        success = False
        try:
            new_history_entry = DonationHistory.objects.create(
                ip_address=ip_address, stripe_customer_id=stripe_customer_id, voter_we_vote_id=voter_we_vote_id,
                charge_id=charge_id, amount=amount, currency=currency, one_time_donation=one_time_donation,
                subscription_id=subscription_id, funding=funding, livemode=livemode, action_taken=action_taken,
                action_result=action_result, created=created, failure_code=failure_code,
                failure_message=failure_message, network_status=network_status, reason=reason,
                seller_message=seller_message, stripe_type=stripe_type, paid=paid, amount_refunded=amount_refunded,
                refund_count=refund_count, name=name, address_zip=address_zip, brand=brand, country=country,
                exp_month=exp_month, exp_year=exp_year, last4=last4, id_card=id_card, stripe_object=stripe_object,
                stripe_status=stripe_status, status=status)

            success = True
            status = 'NEW_HISTORY_ENTRY_SAVED'
        except Exception:
            success = False
            status = 'NEW_HISTORY_ENTRY_NOT_SAVED'

        saved_results = {
            'success': success,
            'status': status,
            'history_entry_saved': new_history_entry
        }
        return saved_results


    def create_subscription_entry(self, stripe_customer_id, voter_we_vote_id, donation_plan_id, start_date_time,
                                  donation_amount, subscription_id, ended_at, canceled_at, livemode):

        new_donation_subscription_entry = False
        try:
            new_donation_subscription_entry = DonationSubscription.objects.create(stripe_customer_id=stripe_customer_id,
                                                                                  voter_we_vote_id=voter_we_vote_id,
                                                                                  donation_plan_id=donation_plan_id,
                                                                                  start_date_time=start_date_time,
                                                                                  donation_amount=donation_amount,
                                                                                  subscription_id=subscription_id,
                                                                                  ended_at=ended_at,
                                                                                  canceled_at=canceled_at,
                                                                                  livemode=livemode)
            success = True
            status = 'NEW_SUBSCRIPTION_ENTRY_SAVED'
        # except Exception as e:
        #     handle_exception(e, logger=logger)
        #     status = 'FAILED_NEW_SUBSCRIPTION_ENTRY_SAVE' \
        #              '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e)
        except:
            success = False
            status = 'NEW_SUBSCRIPTION_ENTRY_NOT_SAVED'
            subscription_id = ""

        saved_results = {
            'success': success,
            'status': status,
            'subscription_id' : subscription_id,
            'donation_entry_saved': new_donation_subscription_entry
        }
        return saved_results

    def create_recurring_donation(self, stripe_customer_id, voter_we_vote_id, donation_amount, start_date_time):

        subscription_entry = object
        success = False
        donation_plan_id = "monthly-" + str(donation_amount)

        donation_plan_id_query = self.retrieve_or_create_recurring_donation_plan(donation_amount)
        if donation_plan_id_query['success']:
            status = donation_plan_id_query['status']

            try:
                subscription = stripe.Subscription.create(
                    customer=stripe_customer_id,
                    plan=donation_plan_id
                )
                success = True
                canceled_at = subscription['canceled_at']
                ended_at = subscription['ended_at']
                subscription_id = subscription['id']
                livemode = subscription['livemode']
                status += "USER_SUCCESSFULLY_SUBSCRIBED_TO_PLAN"
                subscription_entry = self.create_subscription_entry(stripe_customer_id, voter_we_vote_id,
                                                                    donation_plan_id, start_date_time, donation_amount,
                                                                    subscription_id, ended_at, canceled_at, livemode )



            except stripe.error.StripeError as e:
                body = e.json_body
                err = body['error']
                status = "STATUS_IS_{}_AND_ERROR_IS_{}".format(e.http_status, err['type'])
                print("Type is: {}".format(err['type']))

        else:
            status = donation_plan_id_query['status']

        results = {
            'success': success,
            'status': status,
            'recurring_donation_plan_id': donation_plan_id,
            'voter_subscription_saved': subscription_entry['status']
        }
        return results

    def retrieve_stripe_card_error_message(self, error_type):
        voter_card_error_message = 'Your card has been declined for an unknown reason. Contact your bank for more' \
                                               ' information.'

        card_error_message = {
            'approve_with_id': 'The transaction cannot be authorized. Please try again or contact your bank.',
            'card_not_supported': 'Your card does not support this type of purchase. Contact your bank for more '
                                  'information.',
            'card_velocity_exceeded': 'You have exceeded the balance or credit limit available on your card.',
            'currency_not_supported': 'Your card does not support the specified currency.',
            'duplicate_transaction': 'This transaction has been declined because a transaction with identical amount '
                                     'and credit card information was submitted very recently.',
            'fraudulent': 'This transaction has been flagged as potentially fraudulent. Contact your bank for more '
                          'information.',
            'incorrect_number':	'Your card number is incorrect. Please enter the correct number and try again.',
            'incorrect_pin': 'Your pin is incorrect. Please enter the correct number and try again.',
            'incorrect_zip': 'Your ZIP/postal code is incorrect. Please enter the correct number and try again.',
            'insufficient_funds': 'Your card has insufficient funds to complete this transaction.',
            'invalid_account': 'Your card, or account the card is connected to, is invalid. Contact your bank for more'
                               ' information.',
            'invalid_amount': 'The payment amount exceeds the amount that is allowed. Contact your bank for more '
                              'information.',
            'invalid_cvc': 'Your CVC number is incorrect. Please enter the correct number and try again.',
            'invalid_expiry_year': 'The expiration year is invalid. Please enter the correct number and try again.',
            'invalid_number': 'Your card number is incorrect. Please enter the correct number and try again.',
            'invalid_pin': 'Your pin is incorrect. Please enter the correct number and try again.',
            'issuer_not_available': 'The payment cannot be authorized. Please try again or contact your bank.',
            'new_account_information_available': 'Your card, or account the card is connected to, is invalid. Contact '
                                                 'your bank for more information.',
            'withdrawal_count_limit_exceeded': 'You have exceeded the balance or credit limit on your card. Please try '
                                               'another payment method.',
            'pin_try_exceeded':	'The allowable number of PIN tries has been exceeded. Please try again later or use '
                                   'another payment method.',
            'processing_error':	'An error occurred while processing the card. Please try again.'
        }

        for error in card_error_message:
            if error == error_type:
                voter_card_error_message = card_error_message[error]
                break
                # Any other error types that are not in this dict will use the generic voter_card_error_message

        return voter_card_error_message

    def retrieve_donation_history_list(self, we_vote_id):
        voters_donation_list = []
        status = ''

        try:
            donation_queryset = DonationHistory.objects.values_list('created', 'amount', 'currency',
                                                                    'one_time_donation', 'brand', 'exp_month',
                                                                    'exp_year', 'last4', 'stripe_status', 'charge_id')
            donation_queryset = donation_queryset.filter(voter_we_vote_id=we_vote_id)
            voters_donation_list = donation_queryset

            if len(donation_queryset):
                success = True
                status += ' CACHED_WE_VOTE_HISTORY_LIST_RETRIEVED '
            else:
                voters_donation_list = []
                success = True
                status += ' NO_HISTORY_EXISTS_FOR_THIS_VOTER '

        except DonationHistory.DoesNotExist as e:
            status += " WE_VOTE_HISTORY_DOES_NOT_EXIST "
            success = True

        except Exception as e:
            status += " FAILED_TO RETRIEVE_CACHED_WE_VOTE_HISTORY_LIST "
            success = False
            # handle_exception(e, logger=logger, exception_message=status)

        results = {
            'success': success,
            'status': status,
            'voters_donation_list': voters_donation_list
        }

        return results
