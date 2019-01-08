# donate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from datetime import datetime, timezone, timedelta
from exception.models import handle_exception, handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
import stripe
import textwrap
import time


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


class DonationJournal(models.Model):
    """
     This is a generated table that will tracks donation and refund activity
     """
    record_enum = models.CharField(
        verbose_name="enum of record type {PAYMENT_FROM_UI, PAYMENT_AUTO_SUBSCRIPTION, SUBSCRIPTION_SETUP_AND_INITIAL}",
        max_length=32, unique=False, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, unique=False, null=False,
                                        blank=False)
    not_loggedin_voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=32, unique=False,
                                                     null=True, blank=True)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=32,
                                          unique=False, null=False, blank=False)
    charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=32, default="",
                                 null=True, blank=True)
    subscription_id = models.CharField(verbose_name="unique subscription id for one voter, amount, and creation time",
                                       max_length=32, default="", null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name="donation amount", default=0, null=False)
    currency = models.CharField(verbose_name="donation currency country code", max_length=8, default="", null=True,
                                blank=True)
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
    email = models.CharField(verbose_name="stripe returns the donor's email address as a name", max_length=255,
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
    subscription_plan_id = models.CharField(verbose_name="stripe subscription plan id", max_length=64, default="",
                                            unique=False, null=True, blank=True)
    subscription_created_at = models.DateTimeField(verbose_name="stripe subscription creation timestamp",
                                                   auto_now=False, auto_now_add=False, null=True)
    subscription_canceled_at = models.DateTimeField(verbose_name="stripe subscription canceled timestamp",
                                                    auto_now=False, auto_now_add=False, null=True)
    subscription_ended_at = models.DateTimeField(verbose_name="stripe subscription ended timestamp", auto_now=False,
                                                 auto_now_add=False, null=True)
    ip_address = models.GenericIPAddressField(verbose_name="user ip address", protocol='both', unpack_ipv4=False,
                                              null=True, blank=True, unique=False)
    last_charged = models.DateTimeField(verbose_name="stripe subscription most recent charge timestamp", auto_now=False,
                                        auto_now_add=False, null=True)


class DonationInvoice(models.Model):
    """
    This is a generated table that caches donation invoices, since they contain both the invoice id and subscription id
    that is necessary to associate the charge succeeded stripe event with a subscription
    """
    subscription_id = models.CharField(verbose_name="unique stripe subscription id",
                                       max_length=64, default="", null=True, blank=True)
    donation_plan_id = models.CharField(
        verbose_name="plan id for one voter and an amount, can have duplicates "
        "if voter has multiple subscriptions for the same amount", default="", max_length=255, null=False, blank=False)
    invoice_id = models.CharField(verbose_name="unique stripe invoice id for one payment",
                                  max_length=64, default="", null=True, blank=True)
    invoice_date = models.DateTimeField(verbose_name="creation date for this stripe invoice", auto_now=False,
                                        auto_now_add=False, null=True)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=32,
                                          unique=False, null=False, blank=False)


class DonationManager(models.Model):
    @staticmethod
    def create_donate_link_to_voter(stripe_customer_id, voter_we_vote_id):
        """"

        :param stripe_customer_id:
        :param voter_we_vote_id:
        :return:
        """
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

    @staticmethod
    def retrieve_stripe_customer_id(voter_we_vote_id):
        """

        :param voter_we_vote_id:
        :return:
        """
        stripe_customer_id = ''
        status = ''
        success = bool
        if positive_value_exists(voter_we_vote_id):
            try:
                stripe_customer_id_queryset = DonateLinkToVoter.objects.filter(
                    voter_we_vote_id__iexact=voter_we_vote_id).values()
                stripe_customer_id = stripe_customer_id_queryset[0]['stripe_customer_id']
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

    @staticmethod
    def retrieve_or_create_recurring_donation_plan(voter_we_vote_id, donation_amount):
        """
        June 2017, we create these records, but never read them
        :param donation_amount:
        :return:
        """
        recurring_donation_plan_id = voter_we_vote_id + "-monthly-" + str(donation_amount)
        # plan_name = donation_plan_id + " Plan"
        billing_interval = "monthly"
        currency = "usd"
        donation_plan_is_active = True
        exception_multiple_object_returned = False
        status = ''
        stripe_plan_id = ''
        success = False

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
                logger.debug("Stripe, plan_id_query.id " + plan_id_query.id)
        except DonationManager.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            success = False
            status += 'MULTIPLE_MATCHING_SUBSCRIPTION_PLANS_FOUND '
            exception_multiple_object_returned = True

        except stripe.error.StripeError:
            pass

        if not positive_value_exists(stripe_plan_id):
            # if plan doesn't exist in stripe, we need to create it (note it's already been created in database)
            plan = stripe.Plan.create(
                amount=donation_amount,
                interval="month",
                currency="usd",
                nickname=recurring_donation_plan_id,
                id=recurring_donation_plan_id,
            )
            if plan.id:
                success = True
                status += 'SUBSCRIPTION_PLAN_CREATED_IN_STRIPE '
            else:
                success = False
                status += 'SUBSCRIPTION_PLAN_NOT_CREATED_IN_STRIPE '
        results = {
            'success': success,
            'status': status,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'recurring_donation_plan_id': recurring_donation_plan_id,
        }
        return results

    @staticmethod
    def create_donation_journal_entry(
            record_enum, ip_address, stripe_customer_id, voter_we_vote_id, charge_id, amount, currency,
            funding, livemode, action_taken, action_result, created, failure_code, failure_message, network_status,
            reason, seller_message, stripe_type, paid, amount_refunded, refund_count, email, address_zip, brand,
            country, exp_month, exp_year, last4, id_card, stripe_object, stripe_status, status, subscription_id,
            subscription_plan_id, subscription_created_at, subscription_canceled_at, subscription_ended_at,
            not_loggedin_voter_we_vote_id):
        """

        :param record_enum:
        :param ip_address:
        :param stripe_customer_id:
        :param voter_we_vote_id:
        :param charge_id:
        :param amount:
        :param currency:
        :param funding:
        :param livemode:
        :param action_taken:
        :param action_result:
        :param created:
        :param failure_code:
        :param failure_message:
        :param network_status:
        :param reason:
        :param seller_message:
        :param stripe_type:
        :param paid:
        :param amount_refunded:
        :param refund_count:
        :param email:
        :param address_zip:
        :param brand:
        :param country:
        :param exp_month:
        :param exp_year:
        :param last4:
        :param id_card:
        :param stripe_object:
        :param stripe_status:
        :param status:
        :param subscription_id:
        :param subscription_plan_id:
        :param subscription_created_at:
        :param subscription_canceled_at:
        :param subscription_ended_at:
        :param not_loggedin_voter_we_vote_id:
        :return:
        """
        new_history_entry = 0

        try:
            new_history_entry = DonationJournal.objects.create(
                record_enum=record_enum, ip_address=ip_address, stripe_customer_id=stripe_customer_id,
                voter_we_vote_id=voter_we_vote_id, charge_id=charge_id, amount=amount, currency=currency,
                funding=funding, livemode=livemode, action_taken=action_taken,
                action_result=action_result, created=created, failure_code=failure_code,
                failure_message=failure_message, network_status=network_status, reason=reason,
                seller_message=seller_message, stripe_type=stripe_type, paid=paid, amount_refunded=amount_refunded,
                refund_count=refund_count, email=email, address_zip=address_zip, brand=brand, country=country,
                exp_month=exp_month, exp_year=exp_year, last4=last4, id_card=id_card, stripe_object=stripe_object,
                stripe_status=stripe_status, status=status, subscription_id=subscription_id,
                subscription_plan_id=subscription_plan_id, subscription_created_at=subscription_created_at,
                subscription_canceled_at=subscription_canceled_at, subscription_ended_at=subscription_ended_at,
                not_loggedin_voter_we_vote_id=not_loggedin_voter_we_vote_id)

            success = True
            status = 'NEW_HISTORY_ENTRY_SAVED'
        except Exception as e:
            success = False

        saved_results = {
            'success': success,
            'status': status,
            'history_entry_saved': new_history_entry
        }
        return saved_results

    def create_recurring_donation(self, stripe_customer_id, voter_we_vote_id, donation_amount, start_date_time, email):
        """

        # subscription_entry = object
        :param stripe_customer_id:
        :param voter_we_vote_id:
        :param donation_amount:
        :param start_date_time:
        :param email:
        :return:
        """

        donation_plan_id = voter_we_vote_id + "-monthly-" + str(donation_amount)

        donation_plan_id_query = self.retrieve_or_create_recurring_donation_plan(voter_we_vote_id, donation_amount)
        if donation_plan_id_query['success']:
            status = donation_plan_id_query['status']

            try:
                # If not logged in, this voter_we_vote_id will not be the same as the logged in id.
                # Passing the voter_we_vote_id to the subscription gives us a chance to associate logged in with not
                # logged in subscriptions in the future
                subscription = stripe.Subscription.create(
                    customer=stripe_customer_id,
                    plan=donation_plan_id,
                    metadata={'voter_we_vote_id': voter_we_vote_id, 'email': email}
                )
                success = True
                subscription_id = subscription['id']
                status += "USER_SUCCESSFULLY_SUBSCRIBED_TO_PLAN "

                results = {
                    'success': success,
                    'status': status,
                    'voter_subscription_saved': status,
                    'subscription_plan_id': donation_plan_id,
                    'subscription_created_at': subscription['created'],
                    'subscription_id': subscription_id
                }

            except stripe.error.StripeError as e:
                success = False
                body = e.json_body
                err = body['error']
                status = "STRIPE_ERROR_IS_" + err['message'] + "_END"
                logger.error("create_recurring_donation StripeError: " + status)

                results = {
                    'success': False,
                    'status': status,
                    'voter_subscription_saved': False,
                    'subscription_plan_id': "",
                    'subscription_created_at': "",
                    'subscription_id': ""
                }
        else:
            results = donation_plan_id_query

        return results

    @staticmethod
    def retrieve_stripe_card_error_message(error_type):
        """

        :param error_type:
        :return:
        """
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

    @staticmethod
    def retrieve_donation_journal_list(we_vote_id):
        """

        :param we_vote_id:
        :return:
        """
        voters_donation_list = []
        status = ''

        try:
            donation_queryset = DonationJournal.objects.all().order_by('-created')
            donation_queryset = donation_queryset.filter(voter_we_vote_id__iexact=we_vote_id)
            voters_donation_list = donation_queryset

            if len(donation_queryset):
                success = True
                status += ' CACHED_WE_VOTE_HISTORY_LIST_RETRIEVED '
            else:
                voters_donation_list = []
                success = True
                status += ' NO_HISTORY_EXISTS_FOR_THIS_VOTER '

        except DonationJournal.DoesNotExist:
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

    @staticmethod
    def does_donation_journal_charge_exist(charge_id):
        """

        :param charge_id:
        :return:
        """
        try:
            donation_queryset = DonationJournal.objects.all()
            donation_queryset = donation_queryset.filter(charge_id=charge_id)

            if len(donation_queryset):
                exists = True
                success = True
            else:
                exists = False
                success = True

        except Exception as e:
            exists = False
            success = True
            handle_exception(e, logger=logger, exception_message="Exception in does_donation_journal_charge_exist")

        results = {
            'exists': exists,
            'success': success,
        }

        return results

    @staticmethod
    def mark_subscription_canceled_or_ended(subscription_id, customer_id, subscription_ended_at,
                                            subscription_canceled_at):
        """

        :param subscription_id:
        :param customer_id:
        :param subscription_ended_at:
        :param subscription_canceled_at:
        :return:
        """
        try:
            subscription_row = DonationJournal.objects.get(subscription_id=subscription_id,
                                                           stripe_customer_id=customer_id)
            subscription_row.subscription_ended_at = datetime.fromtimestamp(subscription_ended_at, timezone.utc)
            subscription_row.subscription_canceled_at = datetime.fromtimestamp(subscription_canceled_at, timezone.utc)
            subscription_row.save()

        except DonationJournal.DoesNotExist:
            logger.error("mark_subscription_canceled_or_ended: Subscription " + subscription_id + " with customer_id " +
                         customer_id + " does not exist")
            return False

        except Exception as e:
            handle_exception(e, logger=logger, exception_message="Exception in mark_subscription_canceled_or_ended")
            return False

        return True

    @staticmethod
    def move_donations_between_donors(from_voter, to_voter):
        """

        :param from_voter:
        :param to_voter:
        :return:
        """
        status = ''
        voter_we_vote_id = from_voter.we_vote_id
        to_voter_we_vote_id = to_voter.we_vote_id

        try:
            rows = DonationJournal.objects.get(voter_we_vote_id__iexact=voter_we_vote_id)
            rows.voter_we_vote_id = to_voter_we_vote_id
            rows.save()
            status = "move_donations_between_donors MOVED-DONATIONS-FROM-" + \
                     voter_we_vote_id + "-TO-" + to_voter_we_vote_id + " "
            logger.debug(status)

        except DonationJournal.DoesNotExist:
            # The not-loggedin-voter rarely has made a donation, so this is not a problem
            status += " NO-DONATIONS-TO-MOVE-FROM-" + \
                      voter_we_vote_id + "-TO-" + to_voter_we_vote_id + " "
            logger.debug("move_donations_between_donors 1:" + status)
            results = {
                'status': status,
                'success': False,
                'from_voter': from_voter,
                'to_voter': to_voter,
            }
            return results

        except Exception as e:
            status += " EXCEPTION-IN-move_donations_between_donors "
            logger.error("move_donations_between_donors 2:" + status)
            results = {
                'status': status,
                'success': False,
                'from_voter': from_voter,
                'to_voter': to_voter,
            }
            return results

        results = {
            'status': status,
            'success': True,
            'from_voter': from_voter,
            'to_voter': to_voter,
        }
        return results

    @staticmethod
    def check_for_subscription_in_db_without_card_info(customer, plan_id):
        # get the rows with the correct subscription_plan_id, most recently created first (created a few seconds ago)
        # since subscription_plan_id has the we_voter_voter_id, it is very specific
        row_id = -1
        try:
            queryset = DonationJournal.objects.all().order_by('-id')
            rows = queryset.filter(subscription_plan_id=plan_id)
            if len(rows):
                row = rows[0]
                if row.last4 == 0:
                    row_id = row.id
        except DonationJournal.DoesNotExist:
            logger.error("check_for_subscription_in_db_without_card_info row does not exist for stripe customer" +
                         customer)
        except Exception as e:
            logger.error("check_for_subscription_in_db_without_card_info Exception " + str(e))

        return row_id

    @staticmethod
    def update_subscription_in_db(row_id, amount, currency, id_card, address_zip, brand, country, exp_month, exp_year,
                                  last4, funding):
        try:
            row = DonationJournal.objects.get(id=row_id)
            row.amount = amount
            row.currency = currency
            row.id_card = id_card
            row.address_zip = address_zip
            row.brand = brand
            row.country = country
            row.exp_month = exp_month
            row.exp_year = exp_year
            row.last4 = last4
            row.funding = funding
            row.save()
            logger.debug("update_subscription_in_db row=" + str(row_id) + ", plan_id=" + str(row.subscription_plan_id) +
                         ", amount=" + str(amount))
        except Exception as err:
            logger.error("update_subscription_in_db: " + str(err))

        return

    @staticmethod
    def find_we_vote_voter_id_for_stripe_customer(stripe_customer_id):

        try:
            queryset = DonationJournal.objects.all().order_by('-id')
            rows = queryset.filter(stripe_customer_id=stripe_customer_id)
            for row in rows:
                if row.not_loggedin_voter_we_vote_id == None and \
                   row.record_enum == "SUBSCRIPTION_SETUP_AND_INITIAL" and \
                   row.voter_we_vote_id != "":
                    return row.voter_we_vote_id
            for row in rows:
                if row.not_loggedin_voter_we_vote_id != None:
                    return row.not_loggedin_voter_we_vote_id

            return ""

        except DonationJournal.DoesNotExist:
            logger.error("find_we_vote_voter_id_for_stripe_customer row does not exist")
        except Exception as e:
            logger.error("find_we_vote_voter_id_for_stripe_customer: " + str(e))

        return ""

    @staticmethod
    def update_journal_entry_for_refund(charge, voter_we_vote_id, refund):
        if refund and refund['amount'] > 0 and refund['status'] == "succeeded":
            row = DonationJournal.objects.get(charge_id__iexact=charge, voter_we_vote_id__iexact=voter_we_vote_id)
            row.status = textwrap.shorten(row.status + " CHARGE_REFUND_REQUESTED" + "_" + str(refund['created']) +
                                          "_" + refund['currency'] + "_" + str(refund['amount']) + "_REFUND_ID" +
                                          refund['id'] + " ", width=255, placeholder="...")
            row.amount_refunded = refund['amount']
            row.stripe_status = "refund pending"
            row.save()
            logger.debug("update_journal_entry_for_refund for charge " + charge + ", with status: " + row.status)

            return "True"

        logger.error("update_journal_entry_for_refund bad charge or refund for charge_id " + charge +
                     " and voter_we_vote_id " + voter_we_vote_id)
        return "False"

    @staticmethod
    def update_journal_entry_for_already_refunded(charge, voter_we_vote_id):
        row = DonationJournal.objects.get(charge_id__iexact=charge, voter_we_vote_id__iexact=voter_we_vote_id)
        row.status = textwrap.shorten(row.status + "CHARGE_WAS_ALREADY_REFUNDED_" + str(datetime.utcnow()) + " ",
                                      width=255, placeholder="...")
        row.amount_refunded = row.amount
        row.stripe_status = "refunded"
        row.save()
        logger.debug("update_journal_entry_for_refund_completed for charge " + charge + ", with status: " + row.status)

        return "True"

    @staticmethod
    def update_journal_entry_for_refund_completed(charge):
        logger.debug("update_journal_entry_for_refund_completed: " + charge)
        try:
            row = DonationJournal.objects.get(charge_id=charge)
            row.status = textwrap.shorten(row.status + "CHARGE_REFUNDED_" + str(datetime.utcnow()) + " ", width=255,
                                          placeholder="...")
            row.stripe_status = "refunded"
            row.save()
            logger.debug("update_journal_entry_for_refund_completed for charge " + charge + ", with status: " +
                         row.status)
            return "True"

        except DonationJournal.DoesNotExist:
            logger.error("update_journal_entry_for_refund_completed row does not exist for charge " + charge)
        return "False"

    @staticmethod
    def update_donation_invoice(subscription_id, donation_plan_id, invoice_id, invoice_date, customer_id):
        """
        Store the invoice for later use, when the charge.succeeded comes through
        :param subscription_id:
        :param donation_plan_id:
        :param invoice_id:
        :param invoice_date:
        :param customer_id:
        :return:
        """
        debug = logger.debug("update_donation_invoice: " + donation_plan_id + " " + subscription_id + " " + invoice_id)

        try:
            new_invoice_entry = DonationInvoice.objects.create(
                subscription_id=subscription_id, donation_plan_id=donation_plan_id, invoice_id=invoice_id,
                invoice_date=invoice_date, stripe_customer_id=customer_id)

            success = True
            status = 'NEW_INVOICE_ENTRY_SAVED'

        except Exception as e:
            success = False

        saved_results = {
            'success': success,
            'status': status,
            'history_entry_saved': new_invoice_entry
        }
        return saved_results

    @staticmethod
    def update_subscription_with_latest_charge_date(invoice_id, invoice_date):
        """
        Get the last_charged into the subscription row in the DonationJournal
        :param: invoice_id:
        :param invoice_date:
        :return:
        """

        # First find the subscription_id from the cached invoices
        row_invoice = DonationInvoice.objects.get(invoice_id=invoice_id)
        try:
            subscription_id = row_invoice.subscription_id
        except Exception as e:
            # Sometimes the payment, comes a second before the invoice (yuck), so try one more time in 10 seconds
            logger.debug("update_subscription_with_latest_charge_date: trying again after 10 sec for " + invoice_id)
            time.sleep(10)
            row_invoice = DonationInvoice.objects.get(invoice_id=invoice_id)
            subscription_id = row_invoice.subscription_id

        try:
            # Then find the subscription in the DonationJournal row that matches the subscription_id
            row_subscription = DonationJournal.objects.get(subscription_id=subscription_id,
                                                           record_enum="SUBSCRIPTION_SETUP_AND_INITIAL")
            row_subscription.last_charged = datetime.fromtimestamp(invoice_date, timezone.utc)
            row_subscription.save()
            logger.debug("update_subscription_with_latest_charge_date: " + invoice_id + " " +
                        subscription_id + "  journal row: " + str(row_subscription.id))

            # Finally, remove older invoice records ... the invoice records are only needed for a minute or two.
            # Save 10 days worth of invoice, in case we need to diagnose a problem.
            how_many_days= 10
            queryset = DonationInvoice.objects.filter(invoice_date__lte=datetime.fromtimestamp(
                int(time.time()), timezone.utc) - timedelta(days=how_many_days))
            logger.info("update_subscription_with_latest_charge_date: DELETED " + str(queryset.count()) +
                        " invoice rows that were older than " + str(how_many_days) + " days old.")
            queryset.delete()

        except Exception as e:
            handle_exception(e, logger=logger,
                             exception_message="update_subscription_with_latest_charge_date: " + str(e))
        return
