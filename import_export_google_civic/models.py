# import_export_google_civic/models.py
# Brought to you by We Vote. Be good.
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html
# -*- coding: UTF-8 -*-

from ballot.models import BallotItem
from datetime import date, timedelta
from django.db import models
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


def retrieve_google_civic_election_id_for_voter(voter_id):
    """
    Grab the first ballot_item we can find for this voter and return the google_civic_election_id
    """
    google_civic_election_id = 0
    success = False

    if positive_value_exists(voter_id):
        try:
            ballot_item_query = BallotItem.objects.filter(
                voter_id__exact=voter_id,
            )
            ballot_item_list = list(ballot_item_query[:1])
            if ballot_item_list:
                one_ballot_item = ballot_item_list[0]
                google_civic_election_id = one_ballot_item.google_civic_election_id
                success = True
        except BallotItem.DoesNotExist:
            pass

    results = {
        'success': success,
        'google_civic_election_id': google_civic_election_id,
    }
    return results


def fetch_google_civic_election_id_for_voter_id(voter_id):
    # Look to see if we have ballot_items stored for this voter and pull google_civic_election_id from that
    results = retrieve_google_civic_election_id_for_voter(voter_id)
    if results['success']:
        google_civic_election_id = results['google_civic_election_id']
    else:
        google_civic_election_id = 0

    return google_civic_election_id


class GoogleCivicApiCounter(models.Model):
    # The data and time we reached out to the Google Civic API
    datetime_of_action = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)
    kind_of_action = models.CharField(verbose_name="kind of call to google", max_length=50, null=True, blank=True)
    # If a 'ballot' entry, store the election this is for
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)


# This table contains summary entries generated from individual entries stored in the GoogleCivicApiCounter table
class GoogleCivicApiCounterDailySummary(models.Model):
    # The date (without time) we are summarizing
    date_of_action = models.DateField(verbose_name='date of action', null=False, auto_now=False)
    # For each day we will have an "all" entry, as well as one entry with the total number (per day)
    #  of each kind of call to Google
    kind_of_action = models.CharField(verbose_name="kind of call to google", max_length=50, null=True, blank=True)
    # If a 'ballot' entry, store the election this is for
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)


# This table contains summary entries generated from individual entries stored in the GoogleCivicApiCounter table
class GoogleCivicApiCounterWeeklySummary(models.Model):
    # The year as a 4 digit integer
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    # The week in this year as a number between 1-52
    # For each week we will have an "all" entry, as well as one entry with the total number (per day)
    #  of each kind of call to Google
    week_of_action = models.SmallIntegerField(verbose_name='number of the week', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call to google", max_length=50, null=True, blank=True)
    # If a 'ballot' entry, store the election this is for
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)


# This table contains summary entries generated from individual entries stored in the GoogleCivicApiCounter table
class GoogleCivicApiCounterMonthlySummary(models.Model):
    # The year as a 4 digit integer
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    # The week in this year as a number between 1-52
    # For each month we will have an "all" entry, as well as one entry with the total number (per day)
    #  of each kind of call to Google
    month_of_action = models.SmallIntegerField(verbose_name='number of the month', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call to google", max_length=50, null=True, blank=True)
    # If a 'ballot' entry, store the election this is for
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)


# noinspection PyBroadException
class GoogleCivicApiCounterManager(models.Model):
    def create_counter_entry(self, kind_of_action, google_civic_election_id=0):
        """
        Create an entry that records that a call to the Google Civic Api was made.
        """
        try:
            google_civic_election_id = convert_to_int(google_civic_election_id)

            # TODO: We need to work out the timezone questions
            GoogleCivicApiCounter.objects.create(
                kind_of_action=kind_of_action,
                google_civic_election_id=google_civic_election_id,
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

    def retrieve_daily_summaries(self, kind_of_action='', google_civic_election_id=0):
        # Start with today and cycle backwards in time
        daily_summaries = []
        day_on_stage = date.today()  # TODO: We need to work out the timezone questions
        number_found = 0
        maximum_attempts = 30
        attempt_count = 0

        try:
            # Limit the number of times this runs to EITHER 1) 5 positive numbers
            #  OR 2) 30 days in the past, whichever comes first
            while number_found <= 5 and attempt_count <= maximum_attempts:
                attempt_count += 1
                counter_queryset = GoogleCivicApiCounter.objects.all()
                if positive_value_exists(kind_of_action):
                    counter_queryset = counter_queryset.filter(kind_of_action=kind_of_action)
                if positive_value_exists(google_civic_election_id):
                    counter_queryset = counter_queryset.filter(google_civic_election_id=google_civic_election_id)

                # Find the number of these entries on that particular day
                counter_queryset = counter_queryset.filter(datetime_of_action__contains=day_on_stage)
                api_call_count = len(counter_queryset)

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
