# stripe_ip_history/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta

import pytz
from django.db import models

import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


class StripeIpHistory(models.Model):
    """
    This table tracks pre-donation attempts, and is called when reCaptcha on the /more/donate page is validated.
    It blocks one attack vector for card "testing" -- testing the validity of stolen cards
    """
    objects = None
    date = models.DateTimeField(verbose_name="Date of the captcha test", null=True, auto_now=True)
    ip_address = models.GenericIPAddressField(
        verbose_name="user ip address", protocol='both', unpack_ipv4=False, null=True, blank=True, unique=False)
    country_code = models.CharField(
        verbose_name="ISO Country code from GEOIP", max_length=2, null=True, blank=True, unique=False)
    voter_we_vote_id = models.CharField(
        verbose_name="Captcha session we vote user id", max_length=255, unique=False, null=False, blank=False)
    email = models.EmailField(
        verbose_name='voters email address, this is checked before they enter it on the donation form, so only what is '
                     'in the voter record', max_length=255, unique=False, null=True, blank=True)
    captcha_score = models.FloatField(null=True, verbose_name='reCaptcha score returned from Google')
    captcha_success = models.BooleanField(verbose_name="reCaptcha success returned from Google", default=True,)
    blocked_by_captcha = models.BooleanField(
        verbose_name="Did Google reCaptcha cause a block", default=True,)
    blocked_by_country = models.BooleanField(
        verbose_name="Did our country check cause a block", default=True,)
    blocked_by_frequency_hours = models.BooleanField(
        verbose_name="Did users frequency of donating cause a block (initially five in an hour) ", default=True,)
    blocked_by_frequency_days = models.BooleanField(
        verbose_name="Did users frequency of donating cause a block (initially twenty in a week", default=True,)


class StripeIpHistoryManager:
    @staticmethod
    def create_ip_history_record(ip_address, country_code, voter_we_vote_id, email, captcha_score, captcha_success,
                                 blocked_by_captcha, blocked_by_country, blocked_by_frequency_hours,
                                 blocked_by_frequency_days):
        """

        """
        try:
            StripeIpHistory.objects.create(
                ip_address=ip_address,
                country_code=country_code,
                voter_we_vote_id=voter_we_vote_id,
                email=email,
                captcha_score=captcha_score,
                captcha_success=captcha_success,
                blocked_by_captcha=blocked_by_captcha,
                blocked_by_country=blocked_by_country,
                blocked_by_frequency_hours=blocked_by_frequency_hours,
                blocked_by_frequency_days=blocked_by_frequency_days,
            )
            success = True
            status = 'STRIPE_IP_HISTORY_RECORD_SAVED '
        except Exception as e:
            success = False
            status = 'STRIPE_IP_HISTORY_RECORD_WAS_NOT_SAVED '
            logger.error('Stripe Ip History save failed with exception: ', e)

        saved_results = {
            'success': success,
            'status': status,
        }
        return saved_results

    @staticmethod
    def count_stripe_ip_records_for_ip(ip_address, number_of_minutes, number_of_days):
        success = False
        minutes_match_count = -1
        days_match_count = -1
        try:
            sf_timezone = pytz.timezone("US/Pacific")
            now = sf_timezone.localize(datetime.now())
            start_days = now - timedelta(days=number_of_days)
            stripe_ip_history_queryset = StripeIpHistory.objects.filter(
                date__range=[start_days, now],
                ip_address=ip_address,
            )
            days_match_count = stripe_ip_history_queryset.count()

            start_minutes = now - timedelta(minutes=number_of_minutes)
            stripe_ip_history_queryset = StripeIpHistory.objects.filter(
                date__range=[start_minutes, now],
                ip_address=ip_address,
            )
            minutes_match_count = stripe_ip_history_queryset.count()
            success = True
            status = "STRIPE_IP_HISTORY_RECORDS_COUNTED "
        except Exception as e:
            status = "STRIPE_IP_HISTORY_RECORDS_COUNT_FAILED "
            logger.error('count_stripe_ip_records_for_ip failed for ip {%s} with error {%s)' % (ip_address, str(e)))

        results = {
            'success': success,
            'status': status,
            'minutes_match_count': minutes_match_count,
            'days_match_count': days_match_count,
        }
        return results

    @staticmethod
    def clear_ip_history_records_for_one_ip(ip_address):
        stripe_ip_history_queryset = StripeIpHistory.objects.filter(ip_address=ip_address)
        records_count = stripe_ip_history_queryset.count()
        stripe_ip_history_queryset.delete()

        results = {
           'status': 'DELETED_' + str(records_count) + '_RECORDS',
           'success': True,
           'records_cleared': records_count,
        }

        return results
