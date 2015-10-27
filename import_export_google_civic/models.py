# import_export_google_civic/models.py
# Brought to you by We Vote. Be good.
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_functions.models import positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


class GoogleCivicContestReferendum(models.Model):
    # The title of the referendum (e.g. 'Proposition 42'). This field is only populated for contests
    # of type 'Referendum'.
    referendum_title = models.CharField(
        verbose_name="google civic referendum title", max_length=255, null=False, blank=False)
    # A brief description of the referendum. This field is only populated for contests of type 'Referendum'.
    referendum_subtitle = models.CharField(
        verbose_name="google civic referendum subtitle", max_length=255, null=False, blank=False)
    # A link to the referendum. This field is only populated for contests of type 'Referendum'.
    referendum_url = models.CharField(
        verbose_name="google civic referendum details url", max_length=255, null=True, blank=False)
    # The unique ID of the election containing this referendum. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=255, null=False, blank=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    # The internal We Vote unique ID of the election containing this referendum, so we can check integrity of imports.
    we_vote_election_id = models.CharField(
        verbose_name="we vote election id", max_length=255, null=True, blank=True)
    # A number specifying the position of this contest on the voter's ballot.
    ballot_placement = models.CharField(
        verbose_name="google civic ballot placement", max_length=255, null=True, blank=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="google civic district name", max_length=255, null=False, blank=False)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=255, null=False, blank=False)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_ocd_id = models.CharField(verbose_name="google civic district ocd id",
                                       max_length=255, null=False, blank=False)
    # A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = models.CharField(verbose_name="google civic primary party",
                                                 max_length=255, null=True, blank=True)
    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    # Has this entry been processed and transferred to the live We Vote tables?
    was_processed = models.BooleanField(verbose_name="is primary election", default=False, null=False, blank=False)

