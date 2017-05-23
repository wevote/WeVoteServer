# bookmark/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BookmarkItem
# from star.models import StarItem, StarItemList, StarItemManager
import wevote_functions.admin
from voter.models import voter_has_authority
from admin_tools.views import redirect_to_sign_in_page
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.contrib.messages import get_messages
from bookmark.models import ITEM_BOOKMARKED, ITEM_NOT_BOOKMARKED
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


# This page does not need to be protected.
# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
# class ExportBookmarkItemDataView(APIView):
#     def get(self, request, format=None):
#         bookmark_list = BookmarkItem.objects.all()
#         serializer = BookmarkItemSerializer(bookmark_list, many=True)
#         return Response(serializer.data)

# @login_required
# def find_and_update_bookmarks_view(request):
#     authority_required = {'admin'}  # admin, verified_volunteer
#     if not voter_has_authority(request, authority_required):
#         return redirect_to_sign_in_page(request, authority_required)
#
#     number_of_duplicates = 0
#     try:
#         # get the bookmark data from star table - star_item
#         star_item_list = StarItem.objects.order_by('id')
#     except StarItem.DoesNotExist:
#         pass
#
#     # Loop through all of the bookmarks in this list
#     for star_item in star_item_list:
#         if star_item.star_status == 'STARRED':
#             bookmark_status = ITEM_BOOKMARKED
#         else:
#             bookmark_status = ITEM_NOT_BOOKMARKED
#         bookmark_duplicates_query = BookmarkItem.objects.order_by('id')
#
#         # filter by voter_id and candidate_campaign_id and candidate_campaign_we_vote_id to find duplicate rows
#         # filter duplicate queries based on candidate_campaign_id and candidate_campaign_we_vote_id
#         if positive_value_exists(star_item.candidate_campaign_id) or \
#                 positive_value_exists(star_item.candidate_campaign_we_vote_id):
#             bookmark_candidate_campaign_duplicates_query = bookmark_duplicates_query.filter(
#                 voter_id=star_item.voter_id,
#                 candidate_campaign_id=star_item.candidate_campaign_id,
#                 candidate_campaign_we_vote_id=star_item.candidate_campaign_we_vote_id)
#             if bookmark_candidate_campaign_duplicates_query.count() > 0:
#                 number_of_duplicates = 0
#             else:
#                 defaults={
#                     'bookmark_status': bookmark_status,
#                     'date_last_changed': star_item.date_last_changed
#                 }
#
#         # filter duplicate queries based on contest_office_id and contest_office_we_vote_id
#         if positive_value_exists(star_item.contest_office_id) or \
#                 positive_value_exists(star_item.contest_office_we_vote_id):
#             bookmark_contest_office_duplicates_query = bookmark_duplicates_query.filter(
#                 voter_id=star_item.voter_id,
#                 contest_office_id=star_item.contest_office_id,
#                 contest_office_we_vote_id=star_item.contest_office_we_vote_id)
#
#             if bookmark_contest_office_duplicates_query.count() > 0:
#                 number_of_duplicates += 1
#
#             else:
#                 defaults={
#                     'bookmark_status': bookmark_status,
#                     'date_last_changed': star_item.date_last_changed
#                 }
#
#         if positive_value_exists(star_item.contest_measure_id) or \
#                 positive_value_exists(star_item.contest_measure_we_vote_id):
#             bookmark_contest_measure_duplicates_query = bookmark_duplicates_query.filter(
#                 voter_id=star_item.voter_id,
#                 contest_measure_id=star_item.contest_measure_id,
#                 contest_measure_we_vote_id=star_item.contest_measure_we_vote_id)
#
#             if bookmark_contest_measure_duplicates_query.count() > 0:
#                 number_of_duplicates += 1
#             else:
#                 defaults={
#                     'bookmark_status': bookmark_status,
#                     'date_last_changed': star_item.date_last_changed
#                 }
#
#         if number_of_duplicates >= 1:
#             messages.add_message(request, messages.ERROR, 'Duplicate Bookmark found')
#         else:
#             try:
#                 results = BookmarkItem.objects.update_or_create(
#                     voter_id=star_item.voter_id,
#                     contest_measure_id= star_item.contest_measure_id,
#                     contest_measure_we_vote_id= star_item.contest_measure_we_vote_id,
#                     contest_office_id= star_item.contest_office_id,
#                     contest_office_we_vote_id= star_item.contest_office_we_vote_id,
#                     candidate_campaign_id= star_item.candidate_campaign_id,
#                     candidate_campaign_we_vote_id= star_item.candidate_campaign_we_vote_id,
#                     defaults= defaults
#                 )
#
#                 if not results:
#                     messages.add_message(request, messages.ERROR, results)
#             except Exception as e:
#                 messages.add_message(request, messages.ERROR, 'Could not copy bookmark.')
#
#     return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))