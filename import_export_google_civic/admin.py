# import_export_google_civic/admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import admin

from import_export_google_civic.models import GoogleCivicElection
from import_export_google_civic.models import GoogleCivicCandidateCampaign
from import_export_google_civic.models import GoogleCivicContestOffice
from import_export_google_civic.models import GoogleCivicContestReferendum


# class GoogleCivicElectionAdmin(admin.ModelAdmin):
#     fieldsets = [
#         (None, {'fields': ['google_civic_election_id', 'name', 'election_day']}),
#     ]
#     list_display = ('id', 'google_civic_election_id', 'name', 'election_day')
#     list_filter = ['name']
#     search_fields = ['id', 'google_civic_election_id', 'name']
#
# admin.site.register(GoogleCivicElection, GoogleCivicElectionAdmin)
#
# class GoogleCivicContestOfficeAdmin(admin.ModelAdmin):
#     fieldsets = [
#         (None, {'fields': ['office', 'district_name', 'district_scope', 'district_ocd_id', 'google_civic_election_id']}),
#     ]
#     list_display = ('id', 'office', 'district_name', 'district_scope', 'district_ocd_id', 'google_civic_election_id')
#     list_filter = ['office']
#     search_fields = ['id', 'office', 'district_ocd_id', 'google_civic_election_id']
#
# admin.site.register(GoogleCivicContestOffice, GoogleCivicContestOfficeAdmin)

# class GoogleCivicCandidateAdmin(admin.ModelAdmin):
#     fieldsets = [
#         (None, {'fields': ['name', 'party', 'google_civic_election_id', 'google_civic_contest_office_id']}),
#     ]
#     list_display = ('name', 'party', 'google_civic_election_id', 'google_civic_contest_office_id')
#     list_filter = ['name']
#     search_fields = ['id', 'google_civic_election_id', 'name']
#
# admin.site.register(GoogleCivicCandidateCampaign, GoogleCivicCandidateAdmin)


class GoogleCivicContestReferendumAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['referendum_title', 'referendum_subtitle', 'district_scope', 'district_ocd_id', 'google_civic_election_id']}),
    ]
    list_display = ('id', 'referendum_title', 'referendum_subtitle', 'district_scope', 'district_ocd_id', 'google_civic_election_id')
    list_filter = ['referendum_title']
    search_fields = ['id', 'referendum_title', 'district_ocd_id', 'google_civic_election_id']

admin.site.register(GoogleCivicContestReferendum, GoogleCivicContestReferendumAdmin)
