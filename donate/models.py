# donate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models

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
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=True, null=False,
                                        blank=False)


class DonationPlanDefinition(models.Model):
    """
    This is a generated table with admin created donation plans that users can subscribe to (recurring donations)
    """
    plan_identifier = models.CharField(verbose_name="unique plan name", max_length=255, unique=True, null=False,
                                       blank=False)
    plan_name = models.CharField(verbose_name="donation plan name", max_length=255, null=False, blank=False)
    plan_name_visible_to_voter = models.CharField(verbose_name="plan name visible to user", max_length=255,
                                                  null=False, blank=False)
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
                                          unique=True, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", unique=True, null=False, max_length=255,
                                        blank=False)
    donation_plan_name = models.CharField(verbose_name="recurring donation plan name", default="", max_length=255,
                                          null=False,
                                          blank=False)
    start_date_time = models.DateField(verbose_name="subscription start date", auto_now=False, auto_now_add=True)


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
    donation_amount = models.PositiveIntegerField(verbose_name="donation amount", default=0, null=False)
    donation_date_time = models.DateTimeField(verbose_name="donation timestamp", auto_now=False, auto_now_add=True)
    stripe_card_id = models.CharField(verbose_name="stripe unique credit card id", max_length=255, unique=False,
                                      null=False, blank=False)
    charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=255, default="",
                                 null=False, blank=False)
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
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", max_length=255,
                                          unique=False, null=False, blank=False)
    voter_we_vote_id = models.CharField(verbose_name="unique we vote user id", max_length=255, unique=False, null=False,
                                        blank=False)
    charge_id = models.CharField(verbose_name="unique charge id per specific donation", max_length=255, default="",
                                 null=False, blank=False)
    action_taken = models.CharField(verbose_name="action taken", max_length=255, default="", null=True, blank=True)
    action_result = models.CharField(verbose_name="action result", max_length=255, default="", null=True, blank=True)
    action_taken_date_time = models.DateTimeField(verbose_name="action taken timestamp", auto_now=False,
                                                  auto_now_add=True)
    action_result_date_time = models.DateTimeField(verbose_name="action result timestamp", auto_now=False,
                                                   auto_now_add=True)