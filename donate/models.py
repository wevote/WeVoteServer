# donate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
import datetime  # Note this is importing the module. "from datetime import datetime" imports the class
from django.db import models
from django.db.models import F, Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from geopy.geocoders import get_geocoder_for_service
from geopy.exc import GeocoderQuotaExceeded
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

class DonateLinkToVoter(models.Model):
    """
    This is a generated table with customer ID's created when a stripe donation is made for the first time
    """
    # The unique customer id from a stripe donation
    customer_id = models.CharField(verbose_name="stripe unique customer id", default=0, null=False, blank=False)
    voter_id = models.CharField(verbose_name="unique we vote user id", default=0, null=False, blank=False)


class DonationPlanDefinition(models.Model):

    plan_identifier = models.CharField(verbose_name="stripe unique customer id", default=0, null=False, blank=False)
    plan_name = models.CharField(verbose_name="stripe unique customer id", default=0, null=False, blank=False)
    plan_name_visible_to_voter = models.CharField(verbose_name="plan name visible to user", default=0, null=False, blank=False)
    base_cost = models.PositiveIntegerField(verbose_name="recurring donation amount", default=0, null=False)
    billing_frequency_choices = ('SAME_DAY_MONTHLY', 'SAME_DAY_ANNUALLY')
    billing_interval = models.CharField(verbose_name="recurring donation frequency", choices=billing_frequency_choices, default='SAME_DAY_MONTHLY', null=False, blank=False)
    currency = models.CharField(verbose_name="currency", default='USD', null=False, blank=False)
    donation_plan_is_active = models.BooleanField(verbose_name="status of recurring donation plan", default=False, blank=False)


class DonationSubscription(models.Model):

    voter_id = models.CharField(verbose_name="unique we vote user id", default=0, null=False, blank=False)
    stripe_customer_id = models.CharField(verbose_name="stripe unique customer id", default=0, null=False, blank=False)
    donation_plan_name = models.CharField(verbose_name="recurring donation plan name", default=0, null=False, blank=False)
    start_date_time = models.DateField(verbose_name="subscription start date", auto_now=False, auto_now_add=True)


class DonationVoterCreditCard(models.Model):
    voter_id = models.CharField(verbose_name="unique we vote user id", default=0, null=False, blank=False)
    expiration_date_time = models.DateField(verbose_name="credit card expiration date", auto_now=False, auto_now_add=True)
    last_four_digits = models.PositiveIntegerField(verbose_name="recurring donation amount", default=0, null=False)
    name_on_credit_card = models.CharField(verbose_name="credit card name", default=0, null=False, blank=False)