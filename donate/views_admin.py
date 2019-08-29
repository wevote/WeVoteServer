# donate/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import pytz

from admin_tools.views import redirect_to_sign_in_page
from donate.models import DonationManager
from voter.models import voter_has_authority
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


@login_required
def organization_subscription_list_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    plans_list = DonationManager.retrieve_subscription_plan_list()
    plans = []

    for plan in plans_list['subscription_plan_list']:
        try:
            created_at_dt = plan.plan_created_at.astimezone(pytz.timezone("US/Pacific"))  # Display PST/PDST
            nice_created_at = created_at_dt.strftime("%m/%d/%Y %H:%M")
            if plan.coupon_expires_date == None or plan.coupon_expires_date == '':
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
            'coupon_expires_date': nice_expires_dt
        }
        plans.append(plan_dict)

    template_values = {
        'plans': plans,
    }

    return render(request, 'organization_plans/plan_list.html', template_values)

