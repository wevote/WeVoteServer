# import_export_open_people/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import date, timedelta
from django.db import models
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


class OpenPeopleApiCounter(models.Model):
    datetime_of_action = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)
    kind_of_action = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    number_of_items_sent_in_query = models.PositiveIntegerField(null=True, db_index=True)


class OpenPeopleApiCounterDailySummary(models.Model):
    date_of_action = models.DateField(verbose_name='date of action', null=False, auto_now=False)
    kind_of_action = models.CharField(verbose_name="kind of call", max_length=50, null=True, blank=True)


class OpenPeopleApiCounterWeeklySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    week_of_action = models.SmallIntegerField(verbose_name='number of the week', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call", max_length=50, null=True, blank=True)


class OpenPeopleApiCounterMonthlySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    month_of_action = models.SmallIntegerField(verbose_name='number of the month', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call", max_length=50, null=True, blank=True)


# noinspection PyBroadException
class OpenPeopleApiCounterManager(models.Manager):

    def create_counter_entry(self, kind_of_action, number_of_items_sent_in_query=0):
        """
        Create an entry that records that a call to the OpenPeople Api was made.
        """
        try:
            number_of_items_sent_in_query = convert_to_int(number_of_items_sent_in_query)

            # TODO: We need to work out the timezone questions
            OpenPeopleApiCounter.objects.create(
                kind_of_action=kind_of_action,
                number_of_items_sent_in_query=number_of_items_sent_in_query,
            )
            success = True
            status = 'ENTRY_SAVED'
        except Exception:
            success = False
            status = 'SOME_ERROR'

        results = {
            'success':                  success,
            'status':                   status,
        }
        return results

    def retrieve_daily_summaries(self, kind_of_action='', days_to_display=30):
        # Start with today and cycle backwards in time
        daily_summaries = []
        day_on_stage = date.today()  # TODO: We need to work out the timezone questions
        number_found = 0
        maximum_attempts = 365
        attempt_count = 0

        try:
            while number_found <= days_to_display and attempt_count <= maximum_attempts:
                attempt_count += 1
                counter_queryset = OpenPeopleApiCounter.objects.all()
                if positive_value_exists(kind_of_action):
                    counter_queryset = counter_queryset.filter(kind_of_action=kind_of_action)

                # Find the number of these entries on that particular day
                counter_queryset = counter_queryset.filter(
                    datetime_of_action__year=day_on_stage.year,
                    datetime_of_action__month=day_on_stage.month,
                    datetime_of_action__day=day_on_stage.day)
                api_call_count = counter_queryset.count()

                # If any api calls were found on that date, pass it out for display
                if positive_value_exists(api_call_count):
                    daily_summary = {
                        'date_string': day_on_stage,
                        'count': api_call_count,
                    }
                    daily_summaries.append(daily_summary)
                    number_found += 1

                day_on_stage -= timedelta(days=1)
        except Exception:
            pass

        return daily_summaries
