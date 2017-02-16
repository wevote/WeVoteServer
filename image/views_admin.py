# image/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from admin_tools.views import redirect_to_sign_in_page
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.shortcuts import render
from image.controllers import migrate_remote_voter_image_urls_to_local_cache
from voter.models import fetch_voter_id_from_voter_device_link, voter_has_authority
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_api_device_id

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def cache_images_locally_for_all_voters_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    voter_id = convert_to_int(voter_id)

    messages_on_stage = get_messages(request)
    '''
    voter_list = Voter.objects.order_by('-is_admin', '-is_verified_volunteer', 'facebook_email', 'twitter_screen_name',
                                        'last_name', 'first_name')
    voter_list = voter_list[:200]

    for voter in voter_list:
        results = cache_images_locally_for_voter_api(voter.id)
    '''
    cache_all_kind_of_images_results = migrate_remote_voter_image_urls_to_local_cache(voter_id)
    template_values = {
        'messages_on_stage':                messages_on_stage,
        'voter_id':                         voter_id,
        'voter_we_vote_id':                 cache_all_kind_of_images_results['voter_we_vote_id'],
        'cached_twitter_profile_image':      cache_all_kind_of_images_results['cached_twitter_profile_image'],
        'cached_twitter_background_image':  cache_all_kind_of_images_results['cached_twitter_background_image'],
        'cached_twitter_banner_image':      cache_all_kind_of_images_results['cached_twitter_banner_image'],
    }
    return render(request, 'image/cache_images_locally_for_all_voters.html', template_values)
