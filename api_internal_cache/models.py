# api_internal_cache/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.utils.timezone import now
from django.db.models import Q
from datetime import timedelta
import json
from wevote_functions.functions import positive_value_exists


class ApiInternalCacheManager(models.Manager):
    def __unicode__(self):
        return "ApiInternalCacheManager"

    def create_api_internal_cache(
            self,
            api_name='',
            cached_api_response_serialized='',
            election_id_list_serialized='',
            date_cached=None):
        status = ''
        api_internal_cache = None
        api_internal_cache_id = 0
        api_internal_cache_saved = False

        if not positive_value_exists(api_name):
            status += "API_INTERNAL_CACHE_MISSING_API_NAME "
            results = {
                'success':                  False,
                'status':                   status,
                'api_internal_cache_saved': api_internal_cache_saved,
                'api_internal_cache':       api_internal_cache,
                'api_internal_cache_id':    0,
            }
            return results

        if date_cached is None:
            date_cached = now()

        try:
            api_internal_cache = ApiInternalCache.objects.create(
                api_name=api_name,
                cached_api_response_serialized=cached_api_response_serialized,
                date_cached=date_cached,
                election_id_list_serialized=election_id_list_serialized,
            )
            api_internal_cache_saved = True
            api_internal_cache_id = api_internal_cache.id
            success = True
            status += "API_INTERNAL_CACHE_CREATED "
        except Exception as e:
            api_internal_cache_saved = False
            success = False
            status += "API_INTERNAL_CACHE_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'api_internal_cache_saved':     api_internal_cache_saved,
            'api_internal_cache':           api_internal_cache,
            'api_internal_cache_id':        api_internal_cache_id,
        }
        return results

    def create_api_refresh_request(
            self,
            api_name='',
            election_id_list_serialized='',
            date_refresh_is_needed=None):
        status = ''
        api_refresh_request = None
        api_refresh_request_saved = False

        if not positive_value_exists(api_name):
            status += "API_REFRESH_REQUEST_MISSING_API_NAME "
            results = {
                'success':                      False,
                'status':                       status,
                'api_refresh_request_saved':    api_refresh_request_saved,
                'api_refresh_request':          api_refresh_request,
            }
            return results

        if date_refresh_is_needed is None:
            date_refresh_is_needed = now()

        try:
            api_refresh_request = ApiRefreshRequest.objects.create(
                api_name=api_name,
                election_id_list_serialized=election_id_list_serialized,
                date_refresh_is_needed=date_refresh_is_needed,
                date_scheduled=now(),
            )
            api_refresh_request_saved = True
            success = True
            status += "API_REFRESH_REQUEST_CREATED "
        except Exception as e:
            api_refresh_request_saved = False
            success = False
            status += "API_REFRESH_REQUEST_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'api_refresh_request_saved':    api_refresh_request_saved,
            'api_refresh_request':          api_refresh_request,
        }
        return results

    def does_api_refresh_request_exist_in_future(
            self,
            api_name='',
            election_id_list_serialized=''):
        api_refresh_request_found = False
        status = ''
        success = True

        try:
            query = ApiRefreshRequest.objects.filter(
                api_name__iexact=api_name,
                date_refresh_is_needed__gt=now(),
                election_id_list_serialized__iexact=election_id_list_serialized,
                refresh_completed=False)
            number_found = query.count()
            if positive_value_exists(number_found):
                api_refresh_request_found = True
        except ApiRefreshRequest.DoesNotExist:
            status += "API_REFRESH_REQUEST_IN_FUTURE_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'API_REFRESH_REQUEST_IN_FUTURE_ERROR ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'api_refresh_request_found':        api_refresh_request_found,
        }
        return results

    def mark_prior_api_internal_cache_entries_as_replaced(
            self,
            api_name="",
            election_id_list_serialized="",
            excluded_api_internal_cache_id=0):
        status = ''
        success = True
        if positive_value_exists(excluded_api_internal_cache_id):
            try:
                query = ApiInternalCache.objects.filter(
                    api_name__iexact=api_name,
                    election_id_list_serialized__iexact=election_id_list_serialized,
                    replaced=False)
                query = query.exclude(id=excluded_api_internal_cache_id)
                number_updated = query.update(
                    replaced=True,
                    date_replaced=now(),
                )
                status += "API_INTERNAL_CACHE_MARK_REPLACED_COUNT: " + str(number_updated) + " "
            except Exception as e:
                success = False
                status += 'API_INTERNAL_CACHE_MARK_REPLACED_ERROR ' + str(e) + ' '
        else:
            status += 'MUST_SPECIFY_REPLACEMENT_CACHE '
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

    def mark_refresh_completed_for_prior_api_refresh_requested(
            self,
            api_name='',
            election_id_list_serialized=''):
        status = ''
        try:
            number_updated = ApiRefreshRequest.objects.filter(
                api_name__iexact=api_name,
                election_id_list_serialized__iexact=election_id_list_serialized,
                date_refresh_is_needed__lte=now(),
                refresh_completed=False)\
                .update(
                date_refresh_completed=now(),
                refresh_completed=True)
            success = True
            status += "API_REFRESH_REQUESTED_MARK_REFRESH_COUNT: " + str(number_updated) + " "
        except Exception as e:
            success = False
            status += 'MARK_REFRESH_COMPLETED_ERROR ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
        }
        return results

    def retrieve_next_api_refresh_request(self):
        api_refresh_request = None
        api_refresh_request_found = False
        api_refresh_request_list = []
        status = ''

        try:
            # Pick up Refresh requests that were started over 15 minutes ago, and not marked as refresh_completed since
            fifteen_minutes_ago = now() - timedelta(minutes=15)
            query = ApiRefreshRequest.objects.filter(
                date_refresh_is_needed__lte=now(),
                refresh_completed=False)
            query = query.filter(Q(date_checked_out__isnull=True) | Q(date_checked_out__lte=fifteen_minutes_ago))
            query = query.order_by('-date_refresh_is_needed')
            api_refresh_request_list = list(query)
            if len(api_refresh_request_list):
                api_refresh_request = api_refresh_request_list[0]
                api_refresh_request_found = True
            success = True
        except ApiRefreshRequest.DoesNotExist:
            success = True
            status += "RETRIEVE_NEXT_REFRESH_REQUEST_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'RETRIEVE_NEXT_REFRESH_REQUEST_ERROR ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'api_refresh_request':              api_refresh_request,
            'api_refresh_request_found':        api_refresh_request_found,
            'api_refresh_request_list':         api_refresh_request_list,
        }
        return results

    def retrieve_latest_api_internal_cache(
            self,
            api_name='',
            election_id_list_serialized=''):
        api_internal_cache = None
        api_internal_cache_found = False
        api_internal_cache_list = []
        cached_api_response_json_data = {}
        status = ''

        if not positive_value_exists(api_name):
            status += "RETRIEVE_LATEST_CACHE-MISSING_API_NAME "
            results = {
                'success':                          False,
                'status':                           status,
                'api_internal_cache':               None,
                'api_internal_cache_found':         False,
                'api_internal_cache_list':          [],
                'cached_api_response_json_data':    {},
            }
            return results

        try:
            query = ApiInternalCache.objects.filter(
                api_name__iexact=api_name,
                election_id_list_serialized__iexact=election_id_list_serialized,
                replaced=False)
            query = query.exclude(cached_api_response_serialized='')
            query = query.order_by('-date_cached')
            api_internal_cache_list = list(query)
            if len(api_internal_cache_list):
                api_internal_cache = api_internal_cache_list[0]
                api_internal_cache_found = True
                if positive_value_exists(api_internal_cache.cached_api_response_serialized):
                    cached_api_response_json_data = api_internal_cache.cached_api_response_json_data()
            success = True
        except ApiInternalCache.DoesNotExist:
            success = True
            status += "RETRIEVE_LATEST_CACHE_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'RETRIEVE_LATEST_CACHE_ERROR ' + str(e) + ' '

        results = {
            'success':                          success,
            'status':                           status,
            'api_internal_cache':               api_internal_cache,
            'api_internal_cache_found':         api_internal_cache_found,
            'api_internal_cache_list':          api_internal_cache_list,
            'cached_api_response_json_data':    cached_api_response_json_data,
        }
        return results

    def schedule_refresh_of_api_internal_cache(
            self,
            api_name='',
            election_id_list_serialized='',
            api_internal_cache=None):
        api_internal_cache_found = False
        status = ''
        success = True

        if api_internal_cache and hasattr(api_internal_cache, 'api_name'):
            # Work with this existing object
            api_internal_cache_found = True
            status += "API_INTERNAL_CACHE_PASSED_IN "
        else:
            status += "API_INTERNAL_CACHE_NOT_PASSED_IN "
            results = self.retrieve_latest_api_internal_cache(
                api_name=api_name,
                election_id_list_serialized=election_id_list_serialized)
            if results['api_internal_cache_found']:
                api_internal_cache_found = True
                api_internal_cache = results['api_internal_cache']
                status += "API_INTERNAL_CACHE_RETRIEVED "

        # Was there an existing api_internal_cache retrieved in the last 60 minutes?
        # If not, schedule refresh immediately.
        create_entry_immediately = False
        if not api_internal_cache_found:
            create_entry_immediately = True
        elif api_internal_cache and hasattr(api_internal_cache, 'date_cached'):
            sixty_minutes_ago = now() - timedelta(hours=1)
            if api_internal_cache.date_cached < sixty_minutes_ago:
                create_entry_immediately = True
        if create_entry_immediately:
            # We don't pass in date_refresh_is_needed, so it assumes value is "immediately"
            results = self.create_api_refresh_request(
                api_name=api_name,
                election_id_list_serialized=election_id_list_serialized)
            status += results['status']

        # Do we have an ApiRefreshRequest entry scheduled in the future? If not, schedule one 55 minutes from now.
        results = self.does_api_refresh_request_exist_in_future(
            api_name=api_name,
            election_id_list_serialized=election_id_list_serialized)
        if not results['success']:
            status += "NOT_ABLE_TO_SEE-(does_api_refresh_request_exist_in_future): " + str(results['status']) + " "
        elif results['api_refresh_request_found']:
            status += "API_REFRESH_REQUEST_FOUND "
        else:
            date_refresh_is_needed = now() + timedelta(minutes=55)  # Schedule 55 minutes from now
            results = self.create_api_refresh_request(
                api_name=api_name,
                election_id_list_serialized=election_id_list_serialized,
                date_refresh_is_needed=date_refresh_is_needed)
            status += results['status']

        results = {
            'success':                          success,
            'status':                           status,
        }
        return results


class ApiInternalCache(models.Model):
    """
    We pre-generate responses for API calls that take too long for a voter to wait.
    """
    api_name = models.CharField(max_length=255, null=False, blank=True, default='')
    election_id_list_serialized = models.TextField(null=False, default='')
    # The full json response, serialized
    cached_api_response_serialized = models.TextField(null=False, default='')
    date_cached = models.DateTimeField(null=True, auto_now_add=True)
    # If there is a newer version of this data, set "replaced" to True
    replaced = models.BooleanField(default=False)
    date_replaced = models.DateTimeField(null=True)

    def cached_api_response_json_data(self):
        if positive_value_exists(self.cached_api_response_serialized):
            return json.loads(self.cached_api_response_serialized)
        else:
            return {}


class ApiRefreshRequest(models.Model):
    """
    Our internal caching logic has determined that the import_batch_system should kick off a refresh of this data
    """
    api_name = models.CharField(max_length=255, null=True, blank=True, unique=False)
    election_id_list_serialized = models.TextField(null=True, blank=True)
    # When was this scheduled for processing?
    date_scheduled = models.DateTimeField(null=True, auto_now_add=True)
    # When should the refresh take place? (i.e., any time after this date)
    date_refresh_is_needed = models.DateTimeField(null=True)
    # When did the scheduled process start?
    date_checked_out = models.DateTimeField(null=True)
    # When did the refresh finish?
    date_refresh_completed = models.DateTimeField(null=True)
    # A boolean to make it easy to figure out which refreshes have finished, and which one's haven't
    refresh_completed = models.BooleanField(default=False)
