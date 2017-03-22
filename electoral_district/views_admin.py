# electoral/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ElectoralDistrict, ElectoralDistrictManager
from .controllers import electoral_districts_import_from_sample_file
from admin_tools.views import redirect_to_sign_in_page
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from exception.models import handle_record_not_found_exception
from voter.models import voter_has_authority
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

#
# @login_required()
# def electoral_district_list_view(request):
#     authority_required = {'verified_volunteer'}  # admin, verified_volunteer
#     if not voter_has_authority(request, authority_required):
#         return redirect_to_sign_in_page(request, authority_required)
#
#     messages_on_stage = get_messages(request)
#     try:
#         electoral_district_list_query = ElectoralDistrict.objects.all()
#         electoral_district_list_query = electoral_district_list_query.order_by('ctcl_id_temp').reverse()
#         electoral_district_list = electoral_district_list_query
#     except Exception as e:
#         handle_record_not_found_exception(e,logger=logger)
#         # pass
#
#     template_values = {
#         'messages_on_stage': messages_on_stage,
#         'electoral_district_list': electoral_district_list,
#     }
#     return render(request, 'electoral_district/electoral_district_list.html', template_values)

@login_required
def electoral_district_import_from_xml_view(request):

    results = electoral_districts_import_from_sample_file()

    if not results['success']:
        messages.add_message(request, messages.ERROR, results['status'])
    else:
        messages.add_message(request, messages.INFO, 'Electoral Districts import completed. '
                                                     'Saved: {saved}, Updated: {updated}, '
                                                     'Not processed: {not_processed}'
                                                     ''.format(saved=results['saved'],
                                                               updated=results['updated'],
                                                               not_processed=results['not_processed']))
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))