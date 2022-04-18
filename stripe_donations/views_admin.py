# donate/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import pytz
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from config.base import get_environment_variable
from donate.models import DonationManager
from stripe_donations.models import StripeDispute
from voter.models import voter_has_authority
from wevote_functions.functions import convert_to_int

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
def dispute_list_view(request):
    authority_required = {'partner_organization', 'political_data_viewer', 'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    number_of_disputes = StripeDispute.objects.filter(Q(etype="charge.dispute.funds_withdrawn")).count()
    page_offset = convert_to_int(request.GET.get('page_offset', '0'))
    page_limit = 10

    WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
    prev_page_url = None if page_offset == 0 else \
        WE_VOTE_SERVER_ROOT_URL + '/stripe_donations/dispute_list?page_offset=' + str(page_offset - page_limit)

    next_page_url = None if number_of_disputes < page_limit or page_offset + page_limit >= number_of_disputes else \
        WE_VOTE_SERVER_ROOT_URL + '/stripe_donations/dispute_list?page_offset=' + str(page_offset + page_limit)

    disputes = StripeDispute.objects.all().order_by('-created')
    disputes_funds_withdrawn = disputes.filter(Q(etype="charge.dispute.funds_withdrawn"))[page_offset:page_offset+page_limit]
    disputes_list = list(disputes_funds_withdrawn)

    template_values = {
         'disputes_list': disputes_list,
         'number_of_disputes': number_of_disputes,
         'page_offset': page_offset,
         'next_page_url': next_page_url,
         'prev_page_url': prev_page_url,
    }
    return render(request, 'stripe_donations/disputes_list.html', template_values)
