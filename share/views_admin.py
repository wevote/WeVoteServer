# share/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.shortcuts import render
from django.utils.timezone import now

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from datetime import timedelta
from email_outbound.models import EmailAddress, EmailManager
from sms.models import SMSPhoneNumber
from voter.models import voter_has_authority, VoterManager
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, \
    positive_value_exists
from wevote_settings.constants import ELECTION_YEARS_AVAILABLE
from .controllers import update_shared_item_shared_by_info_from_shared_item, \
    update_shared_item_statistics_from_shared_link_clicked, update_shared_link_clicked_year_as_integer, \
    update_who_shares_from_shared_item, update_who_shares_from_shared_link_clicked

from .models import SharedItem, VoterWhoSharesSummaryAllTime, VoterWhoSharesSummaryOneYear

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def shared_item_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}  # We may want to add a "voter_admin"
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    exclude_remind_contact = positive_value_exists(request.GET.get('exclude_remind_contact', False))
    limit_to_last_90_days = positive_value_exists(request.GET.get('limit_to_last_90_days', False))
    number_to_update = convert_to_int(request.GET.get('number_to_update', 10000))
    show_shares_with_zero_clicks = positive_value_exists(request.GET.get('show_shares_with_zero_clicks', False))
    shared_item_search = request.GET.get('shared_item_search', '')
    show_more = positive_value_exists(request.GET.get('show_more', False))
    show_this_year = request.GET.get('show_this_year', False)

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id)
    voter_id = 0
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
        voter_id = convert_to_int(voter_id)

    fix_year_as_integer = True
    if fix_year_as_integer:
        year_results = update_shared_link_clicked_year_as_integer(number_to_update=number_to_update)
        if not year_results['success']:
            message_to_print = "FAILED update_shared_item_statistics_from_shared_link_clicked: {status}".format(
                status=year_results['status']
            )
            messages.add_message(request, messages.ERROR, message_to_print)
        elif positive_value_exists(year_results['shared_link_clicked_updates_remaining']) or \
                positive_value_exists(year_results['shared_link_clicked_changed']) or \
                positive_value_exists(year_results['shared_link_clicked_not_changed']):
            message_to_print = \
                "UPDATE_SHARED_ITEM_YEAR_AS_INTEGER: \n" \
                "shared_link_clicked_changed: {shared_link_clicked_changed:,}, " \
                "shared_link_clicked_not_changed: {shared_link_clicked_not_changed:,}, "\
                "shared_link_clicked_updates_remaining: {shared_link_clicked_updates_remaining:,}\n" \
                "status: {status}\n" \
                "".format(
                    shared_link_clicked_updates_remaining=year_results['shared_link_clicked_updates_remaining'],
                    shared_link_clicked_changed=year_results['shared_link_clicked_changed'],
                    shared_link_clicked_not_changed=year_results['shared_link_clicked_not_changed'],
                    status=year_results['status'],
                )
            messages.add_message(request, messages.INFO, message_to_print)

    update_statistics = True
    if update_statistics:
        statistics_results = update_shared_item_statistics_from_shared_link_clicked(number_to_update=number_to_update)
        if not statistics_results['success']:
            message_to_print = "FAILED update_shared_item_statistics_from_shared_link_clicked: {status}".format(
                status=statistics_results['status']
            )
            messages.add_message(request, messages.ERROR, message_to_print)
        elif positive_value_exists(statistics_results['count_updates_remaining']) or \
                positive_value_exists(statistics_results['shared_items_changed']) or \
                positive_value_exists(statistics_results['shared_items_not_changed']):
            message_to_print = \
                "UPDATE_SHARED_ITEM_STATISTICS_FROM_SHARED_LINK_CLICKED: \n" \
                "shared_items_changed: {shared_items_changed:,}, " \
                "shared_items_not_changed: {shared_items_not_changed:,}, "\
                "count_updates_remaining: {count_updates_remaining:,}" \
                "".format(
                    count_updates_remaining=statistics_results['count_updates_remaining'],
                    shared_items_changed=statistics_results['shared_items_changed'],
                    shared_items_not_changed=statistics_results['shared_items_not_changed'],
                )
            messages.add_message(request, messages.INFO, message_to_print)

        shared_by_results = update_shared_item_shared_by_info_from_shared_item(number_to_update=number_to_update)
        if not shared_by_results['success']:
            message_to_print = "FAILED update_shared_item_shared_by_info_from_shared_item: {status}".format(
                status=shared_by_results['status']
            )
            messages.add_message(request, messages.ERROR, message_to_print)
        elif positive_value_exists(shared_by_results['shared_by_updates_remaining']) or \
                positive_value_exists(shared_by_results['shared_items_changed']) or \
                positive_value_exists(shared_by_results['shared_items_not_changed']):
            message_to_print = \
                "UPDATE_SHARED_ITEM_SHARED_BY_INFO_FROM_SHARED_ITEM: \n" \
                "shared_items_changed: {shared_items_changed:,}, " \
                "shared_items_not_changed: {shared_items_not_changed:,}, "\
                "shared_by_updates_remaining: {shared_by_updates_remaining:,}" \
                "".format(
                    shared_by_updates_remaining=shared_by_results['shared_by_updates_remaining'],
                    shared_items_changed=shared_by_results['shared_items_changed'],
                    shared_items_not_changed=shared_by_results['shared_items_not_changed'],
                )
            messages.add_message(request, messages.INFO, message_to_print)

    if positive_value_exists(shared_item_search):
        # Search for an email address - do not require to be verified
        voter_we_vote_ids_with_email_query = EmailAddress.objects.filter(
            normalized_email_address__icontains=shared_item_search,
        ).values_list('voter_we_vote_id', flat=True)
        voter_we_vote_ids_with_email = list(voter_we_vote_ids_with_email_query)

        # Search for a phone number
        voter_we_vote_ids_with_sms_phone_number_query = SMSPhoneNumber.objects.filter(
            normalized_sms_phone_number__icontains=shared_item_search,
        ).values_list('voter_we_vote_id', flat=True)
        voter_we_vote_ids_with_sms_phone_number = list(voter_we_vote_ids_with_sms_phone_number_query)

        # Now search SharedItem object
        shared_item_query = SharedItem.objects.all()
        search_words = shared_item_search.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            new_filter = Q(campaignx_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(candidate_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(destination_full_url__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(measure_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(other_voter_display_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(other_voter_first_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(other_voter_last_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(other_voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            if len(voter_we_vote_ids_with_email) > 0:
                new_filter = Q(other_voter_we_vote_id__in=voter_we_vote_ids_with_email)
                filters.append(new_filter)

                new_filter = Q(shared_by_voter_we_vote_id__in=voter_we_vote_ids_with_email)
                filters.append(new_filter)

            if len(voter_we_vote_ids_with_sms_phone_number) > 0:
                new_filter = Q(other_voter_we_vote_id__in=voter_we_vote_ids_with_sms_phone_number)
                filters.append(new_filter)

                new_filter = Q(shared_by_voter_we_vote_id__in=voter_we_vote_ids_with_sms_phone_number)
                filters.append(new_filter)

            new_filter = Q(other_voter_email_address_text__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(office_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(shared_by_display_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(shared_by_first_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(shared_by_last_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(shared_by_voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            new_filter = Q(shared_message__icontains=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                shared_item_query = shared_item_query.filter(final_filters)
        shared_item_query = shared_item_query\
            .order_by('-shared_link_clicked_unique_viewer_count', '-shared_link_clicked_count')
    else:
        shared_item_query = SharedItem.objects\
            .order_by('-shared_link_clicked_unique_viewer_count', '-shared_link_clicked_count')

    if positive_value_exists(exclude_remind_contact):
        shared_item_query = shared_item_query.exclude(is_remind_contact_share=True)
    if positive_value_exists(limit_to_last_90_days):
        when_process_must_stop = now() - timedelta(days=90)
        shared_item_query = shared_item_query.filter(date_first_shared__gt=when_process_must_stop)
        show_this_year = 0
    elif positive_value_exists(show_this_year):
        shared_item_query = shared_item_query.filter(date_first_shared__year=show_this_year)
    if not positive_value_exists(show_shares_with_zero_clicks):
        shared_item_query = shared_item_query.filter(shared_link_clicked_count__gt=0)

    shared_item_list_found_count = shared_item_query.count()

    if positive_value_exists(show_more):
        shared_item_list = shared_item_query[:1000]
    else:
        shared_item_list = shared_item_query[:200]

    message_to_print = "{count:,} shared items found.".format(count=shared_item_list_found_count)
    messages.add_message(request, messages.INFO, message_to_print)
    messages_on_stage = get_messages(request)

    template_values = {
        'election_years_available':     ELECTION_YEARS_AVAILABLE,
        'exclude_remind_contact':       exclude_remind_contact,
        'limit_to_last_90_days':        limit_to_last_90_days,
        'messages_on_stage':            messages_on_stage,
        'show_shares_with_zero_clicks': show_shares_with_zero_clicks,
        'shared_item_list':             shared_item_list,
        'shared_item_list_found_count': shared_item_list_found_count,
        'shared_item_search':           shared_item_search,
        'show_more':                    show_more,
        'show_this_year':               show_this_year,
        'voter_id_signed_in': voter_id,
    }
    return render(request, 'share/shared_item_list.html', template_values)

@login_required
def voter_who_shares_summary_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}  # We may want to add a "voter_admin"
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    exclude_remind_contact = positive_value_exists(request.GET.get('exclude_remind_contact', False))
    limit_to_last_90_days = positive_value_exists(request.GET.get('limit_to_last_90_days', False))
    number_to_update = convert_to_int(request.GET.get('number_to_update', False))
    show_shares_with_zero_clicks = positive_value_exists(request.GET.get('show_shares_with_zero_clicks', False))
    voter_summary_search = request.GET.get('voter_summary_search', '')
    show_more = positive_value_exists(request.GET.get('show_more', False))
    show_this_year = convert_to_int(request.GET.get('show_this_year', 0))

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id)
    voter_id = 0
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
        voter_id = convert_to_int(voter_id)

    update_statistics = True
    if update_statistics:
        # Update VoterWhoSharesSummaryAllTime based on SharedItem activity
        shared_by_results = update_who_shares_from_shared_item(
            number_to_update=number_to_update,
            table_name='VoterWhoSharesSummaryAllTime',
        )
        if not shared_by_results['success']:
            message_to_print = "FAILED update_who_shares_all_time_from_shared_item: {status}".format(
                status=shared_by_results['status']
            )
            messages.add_message(request, messages.ERROR, message_to_print)
        elif positive_value_exists(shared_by_results['sharing_summary_items_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_items_not_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_updates_remaining']):
            message_to_print = \
                "WHO_SHARES_ALL_TIME_FROM_SHARED_ITEM: \n" \
                "sharing_summary_items_changed: {sharing_summary_items_changed:,}, " \
                "sharing_summary_items_not_changed: {sharing_summary_items_not_changed:,}, " \
                "sharing_summary_updates_remaining: {sharing_summary_updates_remaining:,} \n" \
                "shared_by_results['status']: {status}" \
                "".format(
                    status=shared_by_results['status'],
                    sharing_summary_items_changed=shared_by_results['sharing_summary_items_changed'],
                    sharing_summary_items_not_changed=shared_by_results['sharing_summary_items_not_changed'],
                    sharing_summary_updates_remaining=shared_by_results['sharing_summary_updates_remaining'],
                )
            messages.add_message(request, messages.INFO, message_to_print)

        # Update 'VoterWhoSharesSummaryAllTime' based on ShareLinkClicked activity
        shared_by_results = update_who_shares_from_shared_link_clicked(
            number_to_update=number_to_update,
            table_name='VoterWhoSharesSummaryAllTime',
        )
        if not shared_by_results['success']:
            message_to_print = "FAILED update_who_shares_all_time_from_shared_link_clicked: {status}".format(
                status=shared_by_results['status']
            )
            messages.add_message(request, messages.ERROR, message_to_print)
        elif positive_value_exists(shared_by_results['sharing_summary_items_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_items_not_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_updates_remaining']):
            message_to_print = \
                "WHO_SHARES_ALL_TIME_FROM_SHARED_LINK_CLICKED: \n" \
                "sharing_summary_items_changed: {sharing_summary_items_changed:,}, " \
                "sharing_summary_items_not_changed: {sharing_summary_items_not_changed:,}, " \
                "sharing_summary_updates_remaining: {sharing_summary_updates_remaining:,} \n" \
                "shared_by_results['status']: {status}" \
                "".format(
                    status=shared_by_results['status'],
                    sharing_summary_items_changed=shared_by_results['sharing_summary_items_changed'],
                    sharing_summary_items_not_changed=shared_by_results['sharing_summary_items_not_changed'],
                    sharing_summary_updates_remaining=shared_by_results['sharing_summary_updates_remaining'],
                )
            messages.add_message(request, messages.INFO, message_to_print)

        # Update VoterWhoSharesSummaryOneYear based on SharedItem activity
        shared_by_results = update_who_shares_from_shared_item(
            number_to_update=number_to_update,
            table_name='VoterWhoSharesSummaryOneYear',
        )
        if not shared_by_results['success']:
            message_to_print = "FAILED update_who_shares_by_year_from_shared_item: {status}".format(
                status=shared_by_results['status']
            )
            messages.add_message(request, messages.ERROR, message_to_print)
        elif positive_value_exists(shared_by_results['sharing_summary_items_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_items_not_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_updates_remaining']):
            message_to_print = \
                "WHO_SHARES_BY_YEAR_FROM_SHARED_ITEM: \n" \
                "sharing_summary_items_changed: {sharing_summary_items_changed:,}, " \
                "sharing_summary_items_not_changed: {sharing_summary_items_not_changed:,}, " \
                "sharing_summary_updates_remaining: {sharing_summary_updates_remaining:,} \n" \
                "shared_by_results['status']: {status}" \
                "".format(
                    status=shared_by_results['status'],
                    sharing_summary_items_changed=shared_by_results['sharing_summary_items_changed'],
                    sharing_summary_items_not_changed=shared_by_results['sharing_summary_items_not_changed'],
                    sharing_summary_updates_remaining=shared_by_results['sharing_summary_updates_remaining'],
                )
            messages.add_message(request, messages.INFO, message_to_print)

        # Update 'VoterWhoSharesSummaryOneYear' based on ShareLinkClicked activity
        shared_by_results = update_who_shares_from_shared_link_clicked(
            number_to_update=number_to_update,
            table_name='VoterWhoSharesSummaryOneYear')
        if not shared_by_results['success']:
            message_to_print = "FAILED update_who_shares_by_year_from_shared_link_clicked: {status}".format(
                status=shared_by_results['status']
            )
            messages.add_message(request, messages.ERROR, message_to_print)
        elif positive_value_exists(shared_by_results['sharing_summary_items_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_items_not_changed']) or \
                positive_value_exists(shared_by_results['sharing_summary_updates_remaining']):
            message_to_print = \
                "WHO_SHARES_BY_YEAR_FROM_SHARED_LINK_CLICKED: \n" \
                "sharing_summary_items_changed: {sharing_summary_items_changed:,}, " \
                "sharing_summary_items_not_changed: {sharing_summary_items_not_changed:,}, " \
                "sharing_summary_updates_remaining: {sharing_summary_updates_remaining:,} \n" \
                "shared_by_results['status']: {status}" \
                "".format(
                    status=shared_by_results['status'],
                    sharing_summary_items_changed=shared_by_results['sharing_summary_items_changed'],
                    sharing_summary_items_not_changed=shared_by_results['sharing_summary_items_not_changed'],
                    sharing_summary_updates_remaining=shared_by_results['sharing_summary_updates_remaining'],
                )
            messages.add_message(request, messages.INFO, message_to_print)

    if positive_value_exists(show_this_year):
        # If filtering by year, use VoterWhoSharesSummaryOneYear object
        voter_who_shares_query = VoterWhoSharesSummaryOneYear.objects.using('readonly').all()
        voter_who_shares_query = voter_who_shares_query.filter(year_as_integer=show_this_year)
    else:
        # Otherwise, use VoterWhoSharesSummaryAllTime object
        voter_who_shares_query = VoterWhoSharesSummaryAllTime.objects.using('readonly').all()

    if positive_value_exists(voter_summary_search):
        # Search for an email address - do not require to be verified
        voter_we_vote_ids_with_email_query = EmailAddress.objects.filter(
            normalized_email_address__icontains=voter_summary_search,
        ).values_list('voter_we_vote_id', flat=True)
        voter_we_vote_ids_with_email = list(voter_we_vote_ids_with_email_query)

        # Search for a phone number
        voter_we_vote_ids_with_sms_phone_number_query = SMSPhoneNumber.objects.filter(
            normalized_sms_phone_number__icontains=voter_summary_search,
        ).values_list('voter_we_vote_id', flat=True)
        voter_we_vote_ids_with_sms_phone_number = list(voter_we_vote_ids_with_sms_phone_number_query)

        search_words = voter_summary_search.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            if len(voter_we_vote_ids_with_email) > 0:
                new_filter = Q(voter_we_vote_id__in=voter_we_vote_ids_with_email)
                filters.append(new_filter)

            if len(voter_we_vote_ids_with_sms_phone_number) > 0:
                new_filter = Q(voter_we_vote_id__in=voter_we_vote_ids_with_sms_phone_number)
                filters.append(new_filter)

            new_filter = Q(shared_by_display_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(voter_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                voter_who_shares_query = voter_who_shares_query.filter(final_filters)
    else:
        # If not searching, don't return entries with only one shared_item and 0 clicks.
        #  This is because some shared item entries are created automatically and don't mean the person intended
        #  to share.
        voter_who_shares_query = voter_who_shares_query.exclude(
            shared_item_count__lte=1,
            shared_link_clicked_count=0,
        )

    if positive_value_exists(limit_to_last_90_days):
        when_process_must_stop = now() - timedelta(days=90)
        voter_who_shares_query = voter_who_shares_query.filter(shared_link_clicked_count_last_updated__gt=when_process_must_stop)
        show_this_year = 0
    if not positive_value_exists(show_shares_with_zero_clicks):
        voter_who_shares_query = voter_who_shares_query.filter(shared_link_clicked_count__gt=0)
    voter_who_shares_query = \
        voter_who_shares_query.order_by(
            '-shared_link_clicked_unique_viewer_count', '-shared_item_count', '-shared_link_clicked_count')

    voter_who_shares_summary_list_found_count = voter_who_shares_query.count()

    if positive_value_exists(show_more):
        voter_who_shares_summary_list = voter_who_shares_query[:1000]
    else:
        voter_who_shares_summary_list = voter_who_shares_query[:200]

    voter_who_shares_summary_list_modified = []
    for voter_who_shares_summary in voter_who_shares_summary_list:
        # Now retrieve all shared items to show under this voter summary
        shared_item_query = SharedItem.objects.using('readonly').all()
        shared_item_query = \
            shared_item_query.filter(shared_by_voter_we_vote_id=voter_who_shares_summary.voter_we_vote_id)
        shared_item_query = shared_item_query.order_by('-date_first_shared')

        # ######################
        # To support searching for a specific URL, we would need a SharedItem-specific search box
        # search_words = voter_summary_search.split()
        # for one_word in search_words:
        #     filters = []  # Reset for each search word
        #
        #     new_filter = Q(destination_full_url__icontains=one_word)
        #     filters.append(new_filter)
        #
        #     # Add the first query
        #     if len(filters):
        #         final_filters = filters.pop()
        #
        #         # ...and "OR" the remaining items in the list
        #         for item in filters:
        #             final_filters |= item
        #
        #         shared_item_query = shared_item_query.filter(final_filters)

        if positive_value_exists(exclude_remind_contact):
            shared_item_query = shared_item_query.exclude(is_remind_contact_share=True)
        if not positive_value_exists(show_shares_with_zero_clicks):
            shared_item_query = shared_item_query.filter(shared_link_clicked_count__gt=0)
        if positive_value_exists(limit_to_last_90_days):
            when_process_must_stop = now() - timedelta(days=90)
            shared_item_query = shared_item_query.filter(date_first_shared__gt=when_process_must_stop)
        if positive_value_exists(show_this_year):
            shared_item_query = shared_item_query.filter(date_first_shared__year=show_this_year)

        voter_who_shares_summary.shared_item_list_count = shared_item_query.count()

        shared_item_list = shared_item_query[:25]
        voter_who_shares_summary.shared_item_list = shared_item_list
        voter_who_shares_summary_list_modified.append(voter_who_shares_summary)

    message_to_print = "{count:,} voters found who shared.".format(count=voter_who_shares_summary_list_found_count)
    messages.add_message(request, messages.INFO, message_to_print)
    messages_on_stage = get_messages(request)

    template_values = {
        'election_years_available':     ELECTION_YEARS_AVAILABLE,
        'exclude_remind_contact':       exclude_remind_contact,
        'limit_to_last_90_days':        limit_to_last_90_days,
        'messages_on_stage':            messages_on_stage,
        'show_shares_with_zero_clicks': show_shares_with_zero_clicks,
        'voter_who_shares_summary_list':             voter_who_shares_summary_list_modified,
        'voter_who_shares_summary_list_found_count': voter_who_shares_summary_list_found_count,
        'voter_summary_search':         voter_summary_search,
        'show_more':                    show_more,
        'show_this_year':               show_this_year,
        'voter_id_signed_in':           voter_id,
    }
    return render(request, 'share/voter_who_shares_summary_list.html', template_values)
