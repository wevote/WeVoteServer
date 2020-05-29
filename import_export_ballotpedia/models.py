# import_export_ballotpedia/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


from datetime import date, timedelta
from django.db import models
from wevote_functions.functions import convert_to_int, positive_value_exists


class BallotpediaApiCounter(models.Model):
    datetime_of_action = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now=True)
    kind_of_action = models.CharField(verbose_name="kind of call to ballotpedia", max_length=50, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)
    ballotpedia_election_id = models.PositiveIntegerField(verbose_name="ballotpedia election id", null=True)


class BallotpediaApiCounterDailySummary(models.Model):
    date_of_action = models.DateField(verbose_name='date of action', null=False, auto_now=False)
    kind_of_action = models.CharField(verbose_name="kind of call to ballotpedia", max_length=50, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)
    ballotpedia_election_id = models.PositiveIntegerField(verbose_name="ballotpedia election id", null=True)


class BallotpediaApiCounterWeeklySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    week_of_action = models.SmallIntegerField(verbose_name='number of the week', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call to ballotpedia", max_length=50, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)
    ballotpedia_election_id = models.PositiveIntegerField(verbose_name="ballotpedia election id", null=True)


class BallotpediaApiCounterMonthlySummary(models.Model):
    year_of_action = models.SmallIntegerField(verbose_name='year of action', null=False)
    month_of_action = models.SmallIntegerField(verbose_name='number of the month', null=False)
    kind_of_action = models.CharField(verbose_name="kind of call to ballotpedia", max_length=50, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)
    ballotpedia_election_id = models.PositiveIntegerField(verbose_name="ballotpedia election id", null=True)


# noinspection PyBroadException
class BallotpediaApiCounterManager(models.Model):
    # Extending models.Models creates a useless empty table, we probably want to extend models.Manager here
    def create_counter_entry(self, kind_of_action, google_civic_election_id=0, ballotpedia_election_id=0):
        """
        Create an entry that records that a call to the Ballotpedia Api was made.
        """
        try:
            google_civic_election_id = convert_to_int(google_civic_election_id)

            # TODO: We need to work out the timezone questions
            BallotpediaApiCounter.objects.create(
                kind_of_action=kind_of_action,
                google_civic_election_id=google_civic_election_id,
                ballotpedia_election_id=ballotpedia_election_id,
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

    def retrieve_daily_summaries(self, kind_of_action='', google_civic_election_id=0, ballotpedia_election_id=0):
        # Start with today and cycle backwards in time
        daily_summaries = []
        day_on_stage = date.today()  # TODO: We need to work out the timezone questions
        number_found = 0
        days_to_display = 30
        maximum_attempts = 45
        attempt_count = 0

        try:
            # Limit the number of times this runs to EITHER 1) 5 positive numbers
            #  OR 2) 30 days in the past, whichever comes first
            while number_found <= days_to_display and attempt_count <= maximum_attempts:
                attempt_count += 1
                counter_queryset = BallotpediaApiCounter.objects.all()
                if positive_value_exists(kind_of_action):
                    counter_queryset = counter_queryset.filter(kind_of_action=kind_of_action)
                if positive_value_exists(google_civic_election_id):
                    counter_queryset = counter_queryset.filter(google_civic_election_id=google_civic_election_id)
                if positive_value_exists(ballotpedia_election_id):
                    counter_queryset = counter_queryset.filter(ballotpedia_election_id=ballotpedia_election_id)

                # Find the number of these entries on that particular day
                counter_queryset = counter_queryset.filter(datetime_of_action__contains=day_on_stage)
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
