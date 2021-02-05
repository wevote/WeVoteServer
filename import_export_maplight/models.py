# import_export_maplight/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateCampaign, ContestOffice
from datetime import datetime
from django.db import models
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_saved_exception
import json
from office.models import ContestOfficeManager
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


def validate_maplight_date(d):
    try:
        datetime.strptime(d, '%Y-%m-%d')
        return True
    except ValueError:
        return False


# TODO Also create MapLightContestMeasure
class MapLightContestOffice(models.Model):
    election_date = models.DateField('election date', default=None, null=True, blank=True)  # "2014-09-03"
    contest_id = models.CharField(
        verbose_name='contest id', max_length=255, null=False, blank=False, unique=True)  # "O1524"
    title = models.CharField(
        verbose_name='title', max_length=255, null=False, blank=False, unique=False)  # "Governor - California"
    type = models.CharField(
        verbose_name='type', max_length=255, null=False, blank=False, unique=False)  # "office"

    # "http://votersedge.org/california/2014/november/state/candidates/governor"
    url = models.CharField(verbose_name='url', max_length=255, null=False, blank=False, unique=False)


class MapLightContestOfficeManager(models.Manager):

    def __unicode__(self):
        return "MapLightContestOfficeManager"

    def retrieve_maplight_contest_office_from_id(self, contest_office_id):
        maplight_contest_office_manager = MapLightContestOfficeManager()
        return maplight_contest_office_manager.retrieve_maplight_contest_office(contest_office_id)

    def fetch_maplight_contest_office_from_id_maplight(self, id_maplight):
        maplight_contest_office_manager = MapLightContestOfficeManager()
        results = maplight_contest_office_manager.retrieve_maplight_contest_office_from_id_maplight(id_maplight)
        if results['success']:
            return results['maplight_contest_office']
        return MapLightContestOffice()

    def retrieve_maplight_contest_office_from_id_maplight(self, id_maplight):
        contest_office_id = 0
        maplight_contest_office_manager = MapLightContestOfficeManager()
        return maplight_contest_office_manager.retrieve_maplight_contest_office(contest_office_id, id_maplight)

    def fetch_maplight_contest_office_id_from_id_maplight(self, id_maplight):
        contest_office_id = 0
        maplight_contest_office_manager = MapLightContestOfficeManager()
        results = maplight_contest_office_manager.retrieve_maplight_contest_office(contest_office_id, id_maplight)
        if results['success']:
            return results['maplight_contest_office_id']
        return 0

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_maplight_contest_office(self, contest_office_id, id_maplight=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        maplight_contest_office_on_stage = MapLightContestOffice()

        try:
            if contest_office_id > 0:
                maplight_contest_office_on_stage = MapLightContestOffice.objects.get(id=contest_office_id)
                contest_office_id = maplight_contest_office_on_stage.id
            elif len(id_maplight) > 0:
                maplight_contest_office_on_stage = MapLightContestOffice.objects.get(contest_id=id_maplight)
                contest_office_id = maplight_contest_office_on_stage.id
        except MapLightContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
        except MapLightContestOffice.DoesNotExist as e:
            exception_does_not_exist = True

        results = {
            'success':                          True if contest_office_id > 0 else False,
            'error_result':                     error_result,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'maplight_contest_office_found':    True if contest_office_id > 0 else False,
            'contest_office_id':                contest_office_id,
            'maplight_contest_office':          maplight_contest_office_on_stage,
        }
        return results


class MapLightCandidate(models.Model):
    candidate_id = models.IntegerField(verbose_name='candidate id', null=False, blank=False, unique=True)  # "5746"
    display_name = models.CharField(
        verbose_name='display name', max_length=255, null=False, blank=False, unique=False)  # "Jerry Brown"
    first_name = models.CharField(
        verbose_name='first name', max_length=255, null=False, blank=True, unique=False)
    models.CharField(
        verbose_name='display name', max_length=255, null=False, blank=False, unique=False)
    gender = models.CharField(
        verbose_name='gender', max_length=1, null=False, blank=False, default='U', unique=False)  # "M"
    last_funding_update = models.DateField(
        verbose_name='last funding update date', default=None, null=True, blank=True)  # "2014-09-03"
    last_name = models.CharField(
        verbose_name='last name', max_length=255, null=False, blank=True, unique=False)  # "Brown"
    middle_name = models.CharField(verbose_name='middle name', max_length=255, null=False, blank=False, unique=False)
    name_prefix = models.CharField(verbose_name='name prefix', max_length=255, null=False, blank=True, unique=False)
    name_suffix = models.CharField(verbose_name='name suffix', max_length=255, null=False, blank=True, unique=False)
    original_name = models.CharField(
        verbose_name='original name', max_length=255, null=False, blank=True, unique=False)  # "Edmund G Brown"
    party = models.CharField(
        verbose_name='political party', max_length=255, null=False, blank=True, unique=False)  # "Democratic"

    # "http://votersedge.org/sites/all/modules/map/modules/map_proposition/images/politicians/2633.jpg?v"
    photo = models.CharField(
        verbose_name='photo url', max_length=255, null=False, blank=True, unique=False)
    politician_id = models.IntegerField(verbose_name='politician id', null=False, blank=False, unique=True)  # "2633"
    roster_name = models.CharField(
        verbose_name='roster name', max_length=255, null=False, blank=True, unique=False)  # "Jerry Brown"
    type = models.CharField(verbose_name='type', max_length=255, null=False, blank=True, unique=False)

    # "http://votersedge.org/california/2014/november/state/candidates/governor/2633-jerry-brown"
    url = models.CharField(verbose_name='url', max_length=255, null=False, blank=True, unique=False)


class MapLightCandidateManager(models.Manager):

    def __unicode__(self):
        return "MapLightCandidateManager"

    def retrieve_maplight_candidate_from_id(self, candidate_id):
        maplight_candidate_manager = MapLightCandidateManager()
        return maplight_candidate_manager.retrieve_maplight_candidate(candidate_id)

    def retrieve_maplight_candidate_from_candidate_id_maplight(self, candidate_id_maplight):
        candidate_id = 0
        politician_id_maplight = 0
        maplight_candidate_manager = MapLightCandidateManager()
        return maplight_candidate_manager.retrieve_maplight_candidate(
            candidate_id, candidate_id_maplight, politician_id_maplight)

    def fetch_maplight_candidate_from_candidate_id_maplight(self, candidate_id_maplight):
        maplight_candidate_manager = MapLightCandidateManager()
        results = maplight_candidate_manager.retrieve_maplight_candidate_from_candidate_id_maplight(
            candidate_id_maplight)
        if results['success']:
            return results['maplight_candidate']
        else:
            return MapLightCandidate()

    def retrieve_maplight_candidate_from_politician_id_maplight(self, politician_id_maplight):
        candidate_id = 0
        candidate_id_maplight = 0
        maplight_candidate_manager = MapLightCandidateManager()
        return maplight_candidate_manager.retrieve_maplight_candidate(
            candidate_id, candidate_id_maplight, politician_id_maplight)

    def fetch_maplight_candidate_from_politician_id_maplight(self, politician_id_maplight):
        maplight_candidate_manager = MapLightCandidateManager()
        results = maplight_candidate_manager.retrieve_maplight_candidate_from_politician_id_maplight(
            politician_id_maplight)
        if results['success']:
            return results['maplight_candidate']
        else:
            return MapLightCandidate()

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_maplight_candidate(self, candidate_id, candidate_id_maplight=None, politician_id_maplight=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        maplight_candidate_on_stage = MapLightCandidate()

        try:
            if candidate_id > 0:
                maplight_candidate_on_stage = MapLightCandidate.objects.get(id=candidate_id)
                candidate_id = maplight_candidate_on_stage.id
            elif len(candidate_id_maplight) > 0:
                maplight_candidate_on_stage = MapLightCandidate.objects.get(candidate_id=candidate_id_maplight)
                candidate_id = maplight_candidate_on_stage.id
            elif len(politician_id_maplight) > 0:
                maplight_candidate_on_stage = MapLightCandidate.objects.get(politician_id=politician_id_maplight)
                candidate_id = maplight_candidate_on_stage.id
        except MapLightCandidate.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
        except MapLightCandidate.DoesNotExist as e:
            exception_does_not_exist = True

        results = {
            'success':                          True if candidate_id > 0 else False,
            'error_result':                     error_result,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'maplight_candidate_found':         True if candidate_id > 0 else False,
            'candidate_id':                     candidate_id,
            'maplight_candidate':               maplight_candidate_on_stage,
        }
        return results
