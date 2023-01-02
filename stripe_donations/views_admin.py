# donate/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import timedelta

import pytz
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils.timezone import now

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from donate.models import DonationManager
from stripe_donations.models import StripeDispute, StripePayments
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int
from wevote_settings.models import fetch_stripe_processing_enabled_state, set_stripe_processing_enabled_state

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def organization_subscription_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    plans_list = DonationManager.retrieve_subscription_plan_list()
    plans = []
    monthly_price_stripe = ''
    annual_price_stripe = ''

    for plan in plans_list['subscription_plan_list']:
        try:
            created_at_dt = plan.plan_created_at.astimezone(pytz.timezone("US/Pacific"))  # Display PST/PDST
            nice_created_at = created_at_dt.strftime("%m/%d/%Y %H:%M")
            if plan.coupon_expires_date is None or plan.coupon_expires_date == '':
                nice_expires_dt = 'None'
            else:
                expires_dt = plan.coupon_expires_date.astimezone(pytz.timezone("US/Pacific"))  # Display PST/PDST
                nice_expires_dt = expires_dt.strftime("%m/%d/%Y %H:%M")
            monthly_price_stripe = "{:0.2f}".format(plan.monthly_price_stripe / 100.0)
            annual_price_stripe = "{:0.2f}".format(plan.annual_price_stripe / 100.0)
        except Exception as e:
            print(e)
            nice_created_at = "format error"
            nice_expires_dt = "format error"

        plan_dict = {
            'id': plan.id,
            'coupon_code': plan.coupon_code,
            'plan_type_enum': plan.plan_type_enum,
            'coupon_applied_message': plan.coupon_applied_message,
            'hidden_plan_comment': plan.hidden_plan_comment,
            'monthly_price_stripe': monthly_price_stripe,
            'annual_price_stripe': annual_price_stripe,
            'redemptions': plan.redemptions,
            'master_feature_package': plan.master_feature_package,
            'features_provided_bitmap': plan.features_provided_bitmap,
            'plan_created_at': nice_created_at,
            'coupon_expires_date': nice_expires_dt,
            'is_archived': plan.is_archived,
        }
        plans.append(plan_dict)

    template_values = {
        'plans': plans,
    }

    return render(request, 'organization_plans/plan_list.html', template_values)


@login_required
def suspect_charges_list_view(request):
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)
    template_values = {}
    page_limit = 10
    server_root = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
    template_values['dispute'] = request.GET.get('dispute', True)
    new_stripe_enabled_value = request.GET.get('set_stripe_enabled')
    month_ago = now() - timedelta(days=30)

    # Disputes ########################
    number_of_disputes = StripeDispute.objects.filter(Q(etype="charge.dispute.funds_withdrawn")).count()
    template_values['number_of_disputes_month'] = StripeDispute.objects.filter(Q(created__gt=month_ago) & Q(etype="charge.dispute.funds_withdrawn")).count()
    template_values['number_of_disputes'] = StripeDispute.objects.filter(Q(etype="charge.dispute.funds_withdrawn")).count()
    page_offset_disputes = convert_to_int(request.GET.get('page_offset_disputes', '0'))
    template_values['page_offset_disputes'] = page_offset_disputes
    template_values['prev_page_url_disputes'] = None if page_offset_disputes == 0 else \
        server_root + '/stripe_donations/suspects_list?dispute=true&page_offset_disputes=' + str(page_offset_disputes - page_limit)
    template_values['next_page_url_disputes'] = None if number_of_disputes < page_limit or page_offset_disputes + page_limit >= number_of_disputes else \
        server_root + '/stripe_donations/suspects_list?dispute=true&page_offset_disputes=' + str(page_offset_disputes + page_limit)
    disputes = StripeDispute.objects.all().order_by('-created')
    disputes_funds_withdrawn = disputes.filter(Q(etype="charge.dispute.funds_withdrawn"))[page_offset_disputes:page_offset_disputes+page_limit]
    template_values['disputes_list'] = list(disputes_funds_withdrawn)

    # Suspect Charges  #############
    page_offset_suspects = convert_to_int(request.GET.get('page_offset_suspects', '0'))
    number_of_suspects = StripePayments.objects.all().count()
    template_values['number_of_suspects_month'] = StripePayments.objects.all().filter(Q(created__gt=month_ago)).count()
    template_values['page_offset_suspects'] = page_offset_suspects
    template_values['number_of_suspects'] = number_of_suspects
    suspects_query = StripePayments.objects.all().order_by('-created')
    suspects_query = suspects_query.exclude((Q(voter_we_vote_id__isnull=True) | Q(voter_we_vote_id__iexact="")) &
        (Q(not_loggedin_voter_we_vote_id__isnull=True) | Q(not_loggedin_voter_we_vote_id__iexact="")))[page_offset_suspects:page_offset_suspects+page_limit]
    template_values['suspects_list'] = list(suspects_query)
    template_values['prev_page_url_suspects'] = None if page_offset_suspects == 0 else \
        server_root + '/stripe_donations/suspects_list?dispute=false&page_offset_suspects=' + str(page_offset_suspects - page_limit)
    template_values['next_page_url_suspects'] = None if number_of_suspects < page_limit or page_offset_suspects + page_limit >= number_of_suspects else \
        server_root + '/stripe_donations/suspects_list?dispute=false&page_offset_suspects=' + str(page_offset_suspects + page_limit)

    if new_stripe_enabled_value is not None:
        set_stripe_processing_enabled_state(new_stripe_enabled_value == 'true')

    template_values['stripe_processing_enabled'] = fetch_stripe_processing_enabled_state()

    return render(request, 'stripe_donations/suspects_list.html', template_values)
