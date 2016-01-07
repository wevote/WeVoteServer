# import_export_vote_smart/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from organization.models import OrganizationManager, Organization
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


class VoteSmartCandidateManager(models.Model):

    def __unicode__(self):
        return "VoteSmartCandidateManager"

    def retrieve_candidate_from_vote_smart_id(self, vote_smart_candidate_id):
        return self.retrieve_vote_smart_candidate(vote_smart_candidate_id)

    def retrieve_vote_smart_candidate_from_we_vote_id(self, we_vote_id):
        vote_smart_candidate_id = 0
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        return vote_smart_candidate_manager.retrieve_vote_smart_candidate(vote_smart_candidate_id, we_vote_id)

    def fetch_vote_smart_candidate_id_from_we_vote_id(self, we_vote_id):
        vote_smart_candidate_id = 0
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate(vote_smart_candidate_id, we_vote_id)
        if results['success']:
            return results['vote_smart_candidate_id']
        return 0

    def retrieve_vote_smart_candidate_from_we_vote_local_id(self, local_candidate_id):
        vote_smart_candidate_id = 0
        we_vote_id = ''
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        return vote_smart_candidate_manager.retrieve_vote_smart_candidate(
            vote_smart_candidate_id, we_vote_id, candidate_maplight_id)

    def retrieve_vote_smart_candidate_from_full_name(self, candidate_name, state_code=None):
        vote_smart_candidate_id = 0
        we_vote_id = ''
        candidate_maplight_id = ''
        vote_smart_candidate_manager = VoteSmartCandidateManager()

        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate(
            vote_smart_candidate_id, first_name, last_name, state_code)
        return results

    def retrieve_vote_smart_candidate_from_name_components(self, first_name=None, last_name=None, state_code=None):
        vote_smart_candidate_id = 0
        vote_smart_candidate_manager = VoteSmartCandidateManager()

        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate(
            vote_smart_candidate_id, first_name, last_name, state_code)
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_vote_smart_candidate(
            self, vote_smart_candidate_id=None, first_name=None, last_name=None, state_code=None):
        """
        We want to return one and only one candidate
        :param vote_smart_candidate_id:
        :param first_name:
        :param last_name:
        :param state_code:
        :return:
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        vote_smart_candidate = VoteSmartCandidate()

        try:
            if positive_value_exists(vote_smart_candidate_id):
                vote_smart_candidate = VoteSmartCandidate.objects.get(candidateId=vote_smart_candidate_id)
                vote_smart_candidate_id = convert_to_int(vote_smart_candidate.candidateId)
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_FOUND_BY_ID"
            elif positive_value_exists(first_name) or positive_value_exists(last_name):
                candidate_queryset = VoteSmartCandidate.objects.all()
                if positive_value_exists(first_name):
                    first_name = first_name.replace("`", "'")  # Vote Smart doesn't like this kind of apostrophe: `
                    candidate_queryset = candidate_queryset.filter(Q(firstName__istartswith=first_name) |
                                                                   Q(nickName__istartswith=first_name) |
                                                                   Q(preferredName__istartswith=first_name))
                if positive_value_exists(last_name):
                    last_name = last_name.replace("`", "'")  # Vote Smart doesn't like this kind of apostrophe: `
                    candidate_queryset = candidate_queryset.filter(lastName__iexact=last_name)
                if positive_value_exists(state_code):
                    candidate_queryset = candidate_queryset.filter(Q(electionStateId__iexact=state_code) |
                                                                   Q(electionStateId__iexact="NA"))
                vote_smart_candidate_list = list(candidate_queryset[:1])
                if vote_smart_candidate_list:
                    vote_smart_candidate = vote_smart_candidate_list[0]
                else:
                    vote_smart_candidate = VoteSmartCandidate()
                vote_smart_candidate_id = convert_to_int(vote_smart_candidate.candidateId)
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_FOUND_BY_NAME"
            else:
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_SEARCH_INDEX_MISSING"
        except VoteSmartCandidate.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            status = "RETRIEVE_VOTE_SMART_CANDIDATE_MULTIPLE_OBJECTS_RETURNED"
        except VoteSmartCandidate.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_VOTE_SMART_CANDIDATE_NOT_FOUND"

        results = {
            'success':                      True if positive_value_exists(vote_smart_candidate_id) else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'vote_smart_candidate_found':   True if positive_value_exists(vote_smart_candidate_id) else False,
            'vote_smart_candidate_id':      vote_smart_candidate_id,
            'vote_smart_candidate':         vote_smart_candidate,
        }
        return results

    def retrieve_vote_smart_candidate_bio(self, vote_smart_candidate_id):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        vote_smart_candidate_bio = VoteSmartCandidateBio()
        vote_smart_candidate_bio_found = False

        try:
            if positive_value_exists(vote_smart_candidate_id):
                vote_smart_candidate_bio = VoteSmartCandidateBio.objects.get(candidateId=vote_smart_candidate_id)
                vote_smart_candidate_id = convert_to_int(vote_smart_candidate_bio.candidateId)
                vote_smart_candidate_bio_found = True
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_BIO_FOUND_BY_ID"
                success = True
            else:
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_BIO_ID_MISSING"
                success = False
        except VoteSmartCandidateBio.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            status = "RETRIEVE_VOTE_SMART_CANDIDATE_BIO_MULTIPLE_OBJECTS_RETURNED"
            success = False
        except VoteSmartCandidateBio.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_VOTE_SMART_CANDIDATE_BIO_NOT_FOUND"
            success = False

        results = {
            'success':                          success,
            'status':                           status,
            'error_result':                     error_result,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
            'vote_smart_candidate_bio_found':   vote_smart_candidate_bio_found,
            'vote_smart_candidate_id':          vote_smart_candidate_id,
            'vote_smart_candidate_bio':         vote_smart_candidate_bio,
        }
        return results


class VoteSmartCandidate(models.Model):
    """http://api.votesmart.org/docs/Candidates.html
    """
    candidateId = models.CharField(max_length=15, primary_key=True)
    firstName = models.CharField(max_length=255)
    nickName = models.CharField(max_length=255)
    middleName = models.CharField(max_length=255)
    preferredName = models.CharField(max_length=255)
    lastName = models.CharField(max_length=255)
    suffix = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    ballotName = models.CharField(max_length=255)
    electionParties = models.CharField(max_length=255)
    electionStatus = models.CharField(max_length=255)
    electionStage = models.CharField(max_length=255)
    electionDistrictId = models.CharField(max_length=255)
    electionDistrictName = models.CharField(max_length=255)
    electionOffice = models.CharField(max_length=255)
    electionOfficeId = models.CharField(max_length=255)
    electionStateId = models.CharField(max_length=255)
    electionOfficeTypeId = models.CharField(max_length=255)
    electionYear = models.CharField(max_length=255)
    electionSpecial = models.CharField(max_length=255)
    electionDate = models.CharField(max_length=255)
    officeParties = models.CharField(max_length=255)
    officeStatus = models.CharField(max_length=255)
    officeDistrictId = models.CharField(max_length=255)
    officeDistrictName = models.CharField(max_length=255)
    officeStateId = models.CharField(max_length=255)
    officeId = models.CharField(max_length=255)
    officeName = models.CharField(max_length=255)
    officeTypeId = models.CharField(max_length=255)
    runningMateId = models.CharField(max_length=255)
    runningMateName = models.CharField(max_length=255)


def vote_smart_candidate_object_filter(one_candidate):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param one_candidate:
    :return:
    """
    one_candidate_filtered = {
        'candidateId': one_candidate.candidateId,
        'firstName': one_candidate.firstName,
        'nickName': one_candidate.nickName,
        'middleName': one_candidate.middleName,
        'preferredName': one_candidate.preferredName,
        'lastName': one_candidate.lastName,
        'suffix': one_candidate.suffix,
        'title': one_candidate.title,
        'ballotName': one_candidate.ballotName,
        'electionParties': one_candidate.electionParties,
        'electionStatus': one_candidate.electionStatus,
        'electionStage': one_candidate.electionStage,
        'electionDistrictId': one_candidate.electionDistrictId,
        'electionDistrictName': one_candidate.electionDistrictName,
        'electionOffice': one_candidate.electionOffice,
        'electionOfficeId': one_candidate.electionOfficeId,
        'electionStateId': one_candidate.electionStateId,
        'electionOfficeTypeId': one_candidate.electionOfficeTypeId,
        'electionYear': one_candidate.electionYear,
        'electionSpecial': one_candidate.electionSpecial,
        'electionDate': one_candidate.electionDate,
        'officeParties': one_candidate.officeParties,
        'officeStatus': one_candidate.officeStatus,
        'officeDistrictId': one_candidate.officeDistrictId,
        'officeDistrictName': one_candidate.officeDistrictName,
        'officeStateId': one_candidate.officeStateId,
        'officeId': one_candidate.officeId,
        'officeName': one_candidate.officeName,
        'officeTypeId': one_candidate.officeTypeId,
        'runningMateId': one_candidate.runningMateId,
        'runningMateName': one_candidate.runningMateName,
    }
    return one_candidate_filtered


class VoteSmartCandidateBio(models.Model):
    """
    http://api.votesmart.org/docs/CandidateBio.html
    """
    candidateId = models.CharField(max_length=15, primary_key=True)
    crpId = models.CharField(max_length=15)  # OpenSecrets ID
    firstName = models.CharField(max_length=255)
    nickName = models.CharField(max_length=255)
    middleName = models.CharField(max_length=255)
    lastName = models.CharField(max_length=255)
    preferredName = models.CharField(max_length=255)
    suffix = models.CharField(max_length=255)
    birthDate = models.CharField(max_length=255)
    birthPlace = models.CharField(max_length=255)
    pronunciation = models.CharField(max_length=255)
    gender = models.CharField(max_length=255)
    family = models.CharField(max_length=255)
    photo = models.CharField(max_length=255)
    homeCity = models.CharField(max_length=255)
    homeState = models.CharField(max_length=255)
    religion = models.CharField(max_length=255)
    # specialMsg = models.CharField(max_length=255)
    # parties = models.CharField(max_length=255)
    # title = models.CharField(max_length=255)
    # shortTitle = models.CharField(max_length=255)
    # name = models.CharField(max_length=255)
    # type = models.CharField(max_length=255)
    # status = models.CharField(max_length=255)
    # firstElect = models.CharField(max_length=255)
    # lastElect = models.CharField(max_length=255)
    # nextElect = models.CharField(max_length=255)
    # termStart = models.CharField(max_length=255)
    # termEnd = models.CharField(max_length=255)
    # district = models.CharField(max_length=255)
    # districtId = models.CharField(max_length=255)
    # stateId = models.CharField(max_length=255)
    education = models.CharField(max_length=255)
    # profession


def vote_smart_candidate_bio_object_filter(one_candidate_bio):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param one_candidate_bio:
    :return:
    """
    one_candidate_bio_filtered = {
        'candidateId': one_candidate_bio.candidateId,
        'crpId': one_candidate_bio.crpId,  # Open Secrets ID
        'firstName': one_candidate_bio.firstName,
        'nickName': one_candidate_bio.nickName,
        'middleName': one_candidate_bio.middleName,
        'lastName': one_candidate_bio.lastName,
        'suffix': one_candidate_bio.suffix,
        'birthDate': one_candidate_bio.birthDate,
        'birthPlace': one_candidate_bio.birthPlace,
        'pronunciation': one_candidate_bio.pronunciation,
        'gender': one_candidate_bio.gender,
        'family': one_candidate_bio.family,
        'photo': one_candidate_bio.photo,
        'homeCity': one_candidate_bio.homeCity,
        'homeState': one_candidate_bio.homeState,
        'religion': one_candidate_bio.religion,
        # 'specialMsg': one_candidate_bio.specialMsg,
        # 'parties': one_candidate_bio.parties,
        # 'title': one_candidate_bio.title,
        # 'shortTitle': one_candidate_bio.shortTitle,
        # 'name': one_candidate_bio.name,
        # 'type': one_candidate_bio.type,
        # 'status': one_candidate_bio.status,
        # 'firstElect': one_candidate_bio.firstElect,
        # 'lastElect': one_candidate_bio.lastElect,
        # 'nextElect': one_candidate_bio.nextElect,
        # 'termStart': one_candidate_bio.termStart,
        # 'termEnd': one_candidate_bio.termEnd,
        # 'district': one_candidate_bio.district,
        # 'districtId': one_candidate_bio.districtId,
        # 'stateId': one_candidate_bio.stateId,
    }
    return one_candidate_bio_filtered


class VoteSmartOfficialManager(models.Model):

    def __unicode__(self):
        return "VoteSmartOfficialManager"

    def retrieve_official_from_vote_smart_id(self, vote_smart_candidate_id):
        return self.retrieve_vote_smart_official(vote_smart_candidate_id)

    def retrieve_vote_smart_official_from_we_vote_id(self, we_vote_id):
        vote_smart_candidate_id = 0
        vote_smart_official_manager = VoteSmartOfficialManager()
        return vote_smart_official_manager.retrieve_vote_smart_official(vote_smart_candidate_id, we_vote_id)

    def fetch_vote_smart_candidate_id_from_we_vote_id(self, we_vote_id):
        vote_smart_candidate_id = 0
        vote_smart_official_manager = VoteSmartOfficialManager()
        results = vote_smart_official_manager.retrieve_vote_smart_official(vote_smart_candidate_id, we_vote_id)
        if results['success']:
            return results['vote_smart_candidate_id']
        return 0

    def retrieve_vote_smart_official_from_we_vote_local_id(self, local_official_id):
        vote_smart_candidate_id = 0
        we_vote_id = ''
        vote_smart_official_manager = VoteSmartOfficialManager()
        return vote_smart_official_manager.retrieve_vote_smart_official(
            vote_smart_candidate_id, we_vote_id, official_maplight_id)

    def retrieve_vote_smart_official_from_full_name(self, official_name, state_code=None):
        vote_smart_candidate_id = 0
        we_vote_id = ''
        official_maplight_id = ''
        vote_smart_official_manager = VoteSmartOfficialManager()

        results = vote_smart_official_manager.retrieve_vote_smart_official(
            vote_smart_candidate_id, first_name, last_name, state_code)
        return results

    def retrieve_vote_smart_official_from_name_components(self, first_name=None, last_name=None, state_code=None):
        vote_smart_candidate_id = 0
        vote_smart_official_manager = VoteSmartOfficialManager()

        results = vote_smart_official_manager.retrieve_vote_smart_official(
            vote_smart_candidate_id, first_name, last_name, state_code)
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_vote_smart_official(
            self, vote_smart_candidate_id=None, first_name=None, last_name=None, state_code=None):
        """
        We want to return one and only one official
        :param vote_smart_candidate_id:
        :param first_name:
        :param last_name:
        :param state_code:
        :return:
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        vote_smart_official = VoteSmartOfficial()

        try:
            if positive_value_exists(vote_smart_candidate_id):
                vote_smart_official = VoteSmartOfficial.objects.get(candidateId=vote_smart_candidate_id)
                vote_smart_candidate_id = convert_to_int(vote_smart_official.candidateId)
                status = "RETRIEVE_VOTE_SMART_OFFICIAL_FOUND_BY_ID"
            elif positive_value_exists(first_name) or positive_value_exists(last_name):
                official_queryset = VoteSmartOfficial.objects.all()
                if positive_value_exists(first_name):
                    official_queryset = official_queryset.filter(firstName__istartswith=first_name)
                if positive_value_exists(last_name):
                    official_queryset = official_queryset.filter(lastName__iexact=last_name)
                if positive_value_exists(state_code):
                    official_queryset = official_queryset.filter(officeStateId__iexact=state_code)
                vote_smart_official_list = list(official_queryset[:1])
                if vote_smart_official_list:
                    vote_smart_official = vote_smart_official_list[0]
                else:
                    vote_smart_official = VoteSmartOfficial()
                vote_smart_candidate_id = convert_to_int(vote_smart_official.candidateId)
                status = "RETRIEVE_VOTE_SMART_OFFICIAL_FOUND_BY_NAME"
            else:
                status = "RETRIEVE_VOTE_SMART_OFFICIAL_SEARCH_INDEX_MISSING"
        except VoteSmartOfficial.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            status = "RETRIEVE_VOTE_SMART_OFFICIAL_MULTIPLE_OBJECTS_RETURNED"
        except VoteSmartOfficial.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_VOTE_SMART_OFFICIAL_NOT_FOUND"

        results = {
            'success':                      True if positive_value_exists(vote_smart_candidate_id) else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'vote_smart_official_found':   True if positive_value_exists(vote_smart_candidate_id) else False,
            'vote_smart_candidate_id':      vote_smart_candidate_id,
            'vote_smart_official':         vote_smart_official,
        }
        return results


class VoteSmartOfficial(models.Model):
    """
    http://api.votesmart.org/docs/Officials.html
    """
    candidateId = models.CharField(max_length=15, primary_key=True)
    firstName = models.CharField(max_length=255)
    nickName = models.CharField(max_length=255)
    middleName = models.CharField(max_length=255)
    lastName = models.CharField(max_length=255)
    suffix = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    electionParties = models.CharField(max_length=255)
    officeParties = models.CharField(max_length=255)
    officeStatus = models.CharField(max_length=255)
    officeDistrictId = models.CharField(max_length=255)
    officeDistrictName = models.CharField(max_length=255)
    officeTypeId = models.CharField(max_length=255)
    officeId = models.CharField(max_length=255)
    officeName = models.CharField(max_length=255)
    officeStateId = models.CharField(max_length=255)


def vote_smart_official_object_filter(one_official):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param one_official:
    :return:
    """
    one_official_filtered = {
        'candidateId': one_official.candidateId,
        'firstName': one_official.firstName,
        'nickName': one_official.nickName,
        'middleName': one_official.middleName,
        'lastName': one_official.lastName,
        'suffix': one_official.suffix,
        'title': one_official.title,
        'electionParties': one_official.electionParties,
        'officeParties': one_official.officeParties,
        'officeStatus': one_official.officeStatus,
        'officeDistrictId': one_official.officeDistrictId,
        'officeDistrictName': one_official.officeDistrictName,
        'officeTypeId': one_official.officeTypeId,
        'officeId': one_official.officeId,
        'officeName': one_official.officeName,
        'officeStateId': one_official.officeStateId,
    }
    return one_official_filtered


class VoteSmartRatingManager(models.Model):

    def __unicode__(self):
        return "VoteSmartRatingManager"

    def retrieve_candidate_from_vote_smart_id(self, vote_smart_candidate_id):
        return self.retrieve_vote_smart_candidate(vote_smart_candidate_id)

    def retrieve_vote_smart_candidate_from_we_vote_id(self, we_vote_id):
        vote_smart_candidate_id = 0
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        return vote_smart_candidate_manager.retrieve_vote_smart_candidate(vote_smart_candidate_id, we_vote_id)

    def fetch_vote_smart_candidate_id_from_we_vote_id(self, we_vote_id):
        vote_smart_candidate_id = 0
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate(vote_smart_candidate_id, we_vote_id)
        if results['success']:
            return results['vote_smart_candidate_id']
        return 0

    def retrieve_vote_smart_candidate_from_we_vote_local_id(self, local_candidate_id):
        vote_smart_candidate_id = 0
        we_vote_id = ''
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        return vote_smart_candidate_manager.retrieve_vote_smart_candidate(
            vote_smart_candidate_id, we_vote_id, candidate_maplight_id)

    def retrieve_vote_smart_candidate_from_full_name(self, candidate_name, state_code=None):
        vote_smart_candidate_id = 0
        we_vote_id = ''
        candidate_maplight_id = ''
        vote_smart_candidate_manager = VoteSmartCandidateManager()

        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate(
            vote_smart_candidate_id, first_name, last_name, state_code)
        return results

    def retrieve_vote_smart_candidate_from_name_components(self, first_name=None, last_name=None, state_code=None):
        vote_smart_candidate_id = 0
        vote_smart_candidate_manager = VoteSmartCandidateManager()

        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate(
            vote_smart_candidate_id, first_name, last_name, state_code)
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_vote_smart_candidate(
            self, vote_smart_candidate_id=None, first_name=None, last_name=None, state_code=None):
        """
        We want to return one and only one candidate
        :param vote_smart_candidate_id:
        :param first_name:
        :param last_name:
        :param state_code:
        :return:
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        vote_smart_candidate = VoteSmartCandidate()

        try:
            if positive_value_exists(vote_smart_candidate_id):
                vote_smart_candidate = VoteSmartCandidate.objects.get(candidateId=vote_smart_candidate_id)
                vote_smart_candidate_id = convert_to_int(vote_smart_candidate.candidateId)
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_FOUND_BY_ID"
            elif positive_value_exists(first_name) or positive_value_exists(last_name):
                candidate_queryset = VoteSmartCandidate.objects.all()
                if positive_value_exists(first_name):
                    first_name = first_name.replace("`", "'")  # Vote Smart doesn't like this kind of apostrophe: `
                    candidate_queryset = candidate_queryset.filter(Q(firstName__istartswith=first_name) |
                                                                   Q(nickName__istartswith=first_name) |
                                                                   Q(preferredName__istartswith=first_name))
                if positive_value_exists(last_name):
                    last_name = last_name.replace("`", "'")  # Vote Smart doesn't like this kind of apostrophe: `
                    candidate_queryset = candidate_queryset.filter(lastName__iexact=last_name)
                if positive_value_exists(state_code):
                    candidate_queryset = candidate_queryset.filter(Q(electionStateId__iexact=state_code) |
                                                                   Q(electionStateId__iexact="NA"))
                vote_smart_candidate_list = list(candidate_queryset[:1])
                if vote_smart_candidate_list:
                    vote_smart_candidate = vote_smart_candidate_list[0]
                else:
                    vote_smart_candidate = VoteSmartCandidate()
                vote_smart_candidate_id = convert_to_int(vote_smart_candidate.candidateId)
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_FOUND_BY_NAME"
            else:
                status = "RETRIEVE_VOTE_SMART_CANDIDATE_SEARCH_INDEX_MISSING"
        except VoteSmartCandidate.MultipleObjectsReturned as e:
            exception_multiple_object_returned = True
            status = "RETRIEVE_VOTE_SMART_CANDIDATE_MULTIPLE_OBJECTS_RETURNED"
        except VoteSmartCandidate.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_VOTE_SMART_CANDIDATE_NOT_FOUND"

        results = {
            'success':                      True if positive_value_exists(vote_smart_candidate_id) else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'vote_smart_candidate_found':   True if positive_value_exists(vote_smart_candidate_id) else False,
            'vote_smart_candidate_id':      vote_smart_candidate_id,
            'vote_smart_candidate':         vote_smart_candidate,
        }
        return results


class VoteSmartCategory(models.Model):
    """http://api.votesmart.org/docs/Rating.html
    """
    categoryId = models.CharField(max_length=15, primary_key=True)
    name = models.CharField(max_length=255)


def vote_smart_category_filter(category):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param category:
    :return:
    """
    category_filtered = {
        'categoryId': category.categoryId,
        'name': category.name,
    }
    return category_filtered


class VoteSmartRating(models.Model):
    """
    http://api.votesmart.org/docs/Rating.html
    A Vote Smart rating is like a voter guide, because it contains a package of candidateId/rating pairs like this:
    {'candidateRating': [{'candidateId': '53279', 'rating': '40'},
                         {'candidateId': '53266', 'rating': '90'},
    """
    ratingId = models.CharField(max_length=15, primary_key=True)
    sigId = models.CharField(verbose_name="special interest group id", max_length=15)
    timeSpan = models.CharField(max_length=255)
    ratingName = models.CharField(max_length=255)
    ratingText = models.TextField()


# This is the filter used for the Vote Smart call: Rating.getCandidateRating
# http://api.votesmart.org/docs/Rating.html
def vote_smart_candidate_rating_filter(rating):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param rating:
    :return:
    """
    rating_filtered = {
        'ratingId':     rating.ratingId,
        'rating':       rating.rating,
        'timeSpan':     rating.timespan,  # Seems to be typo with lower case "s"
        'ratingName':   rating.ratingName,
        'ratingText':   rating.ratingText,
        'sigId':        rating.sigId,
    }
    return rating_filtered


# This is the filter used for the Vote Smart call: Rating.getSigRatings
# http://api.votesmart.org/docs/Rating.html
def vote_smart_rating_list_filter(rating):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param rating:
    :return:
    """
    rating_filtered = {
        'ratingId': rating.ratingId,
        'timeSpan': rating.timespan,  # Seems to be typo with lower case "s"
        'ratingName': rating.ratingName,
        'ratingText': rating.ratingText,
    }
    return rating_filtered


class VoteSmartRatingOneCandidate(models.Model):
    """
    http://api.votesmart.org/docs/Rating.html
    A Vote Smart rating is like a voter guide, because it contains a package of candidateId/rating pairs like this:
    {'candidateRating': [{'candidateId': '53279', 'rating': '40'},
                         {'candidateId': '53266', 'rating': '90'},
    """
    ratingId = models.CharField(max_length=15)
    sigId = models.CharField(verbose_name="special interest group id", max_length=15)
    candidateId = models.CharField(max_length=15)
    timeSpan = models.CharField(max_length=255)
    rating = models.CharField(max_length=255)
    ratingName = models.CharField(max_length=255)
    ratingText = models.TextField()


def vote_smart_rating_one_candidate_filter(rating_one_candidate):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param rating:
    :return:
    """
    rating_one_candidate_filtered = {
        'candidateId': rating_one_candidate.candidateId,
        'rating': rating_one_candidate.rating,
    }
    return rating_one_candidate_filtered


class VoteSmartRatingCategoryLink(models.Model):
    """http://api.votesmart.org/docs/Rating.html
    """
    ratingId = models.CharField(max_length=15)
    sigId = models.CharField(verbose_name="group id for this rating", max_length=15)
    candidateId = models.CharField(verbose_name="vote smart candidate id for this rating", max_length=15)
    timeSpan = models.CharField(max_length=255)
    categoryId = models.CharField(verbose_name="category id for this rating", max_length=15)
    categoryName = models.CharField(verbose_name="category name", max_length=255)


class VoteSmartSpecialInterestGroup(models.Model):
    """http://api.votesmart.org/docs/Rating.html
    """
    sigId = models.CharField(verbose_name="special interest group id", max_length=15, primary_key=True)
    parentId = models.CharField(max_length=15)
    stateId = models.CharField(max_length=2)
    name = models.CharField(verbose_name="name of special interest group", max_length=255)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    zip = models.CharField(max_length=255)
    phone1 = models.CharField(max_length=255)
    phone2 = models.CharField(max_length=255)
    fax = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    contactName = models.CharField(max_length=255)


def vote_smart_special_interest_group_list_filter(special_interest_group_from_list):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param special_interest_group:
    :return:
    """
    special_interest_group_list_filtered = {
        'sigId': special_interest_group_from_list.sigId,
        'parentId': special_interest_group_from_list.parentId,
        'name': special_interest_group_from_list.name,
    }
    return special_interest_group_list_filtered


def vote_smart_special_interest_group_filter(special_interest_group):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param special_interest_group:
    :return:
    """
    special_interest_group_filtered = {
        'sigId': special_interest_group.sigId,
        'parentId': special_interest_group.parentId,
        'stateId': special_interest_group.stateId,
        'name': special_interest_group.name,
        'description': special_interest_group.description,
        'address': special_interest_group.address,
        'city': special_interest_group.city,
        'state': special_interest_group.state,
        'zip': special_interest_group.zip,
        'phone1': special_interest_group.phone1,
        'phone2': special_interest_group.phone2,
        'fax': special_interest_group.fax,
        'email': special_interest_group.email,
        'url': special_interest_group.url,
        'contactName': special_interest_group.contactName,
    }
    return special_interest_group_filtered


class VoteSmartSpecialInterestGroupManager(models.Model):

    def __unicode__(self):
        return "VoteSmartSpecialInterestGroupManager"

    def update_or_create_we_vote_organization(self, vote_smart_special_interest_group_id):
        # See if we can find an existing We Vote organization with vote_smart_special_interest_group_id
        if not positive_value_exists(vote_smart_special_interest_group_id):
            results = {
                'success':              False,
                'status':               "SPECIAL_INTEREST_GROUP_ID_MISSING",
                'organization_found':   False,
                'organization':         Organization(),
            }
            return results

        # Retrieve Special Interest Group
        try:
            vote_smart_organization = VoteSmartSpecialInterestGroup.objects.get(
                sigId=vote_smart_special_interest_group_id)
            vote_smart_organization_found = True
        except VoteSmartSpecialInterestGroup.MultipleObjectsReturned as e:
            vote_smart_organization_found = False
        except VoteSmartSpecialInterestGroup.DoesNotExist as e:
            # An organization matching this Vote Smart ID wasn't found
            vote_smart_organization_found = False

        if not vote_smart_organization_found:
            results = {
                'success':              False,
                'status':               "SPECIAL_INTEREST_GROUP_MISSING",
                'organization_found':   False,
                'organization':         Organization(),
            }
            return results

        we_vote_organization_manager = OrganizationManager()
        organization_id = 0
        organization_we_vote_id = None
        we_vote_organization_found = False
        results = we_vote_organization_manager.retrieve_organization(organization_id, organization_we_vote_id,
                                                                     vote_smart_special_interest_group_id)

        if results['organization_found']:
            success = True
            status = "NOT UPDATING RIGHT NOW"
            we_vote_organization_found = True
            we_vote_organization = results['organization']
            # Update existing organization entry
        else:
            # Create new organization, or find existing org via other fields
            try:
                defaults_from_vote_smart = {
                    'organization_name': vote_smart_organization.name,
                    'organization_address': vote_smart_organization.address,
                    'organization_city': vote_smart_organization.city,
                    'organization_state': vote_smart_organization.state,
                    'organization_zip': vote_smart_organization.zip,
                    'organization_phone1': vote_smart_organization.phone1,
                    'organization_phone2': vote_smart_organization.phone2,
                    'organization_fax': vote_smart_organization.fax,
                    'organization_email': vote_smart_organization.email,
                    'organization_website': vote_smart_organization.url,
                    'organization_contact_name': vote_smart_organization.contactName,
                    'organization_description': vote_smart_organization.description,
                    'state_served_code': vote_smart_organization.stateId,
                    'vote_smart_id': vote_smart_organization.sigId,
                }
                we_vote_organization, created = Organization.objects.update_or_create(
                    organization_name=vote_smart_organization.name,
                    # organization_website=vote_smart_organization.url,
                    # organization_email=vote_smart_organization.email,
                    defaults=defaults_from_vote_smart,
                )
                success = True
                status = "UPDATE_OR_CREATE_ORGANIZATION_FROM_VOTE_SMART"
                we_vote_organization_found = True
            except Organization.MultipleObjectsReturned as e:
                success = False
                status = "UPDATE_OR_CREATE_ORGANIZATION_FROM_VOTE_SMART_MULTIPLE_FOUND"
                we_vote_organization = Organization()
            except Exception as error_instance:
                error_message = error_instance.args
                status = "UPDATE_OR_CREATE_ORGANIZATION_FROM_VOTE_SMART_FAILED: " \
                         "{error_message}".format(error_message=error_message)
                success = False
                we_vote_organization = Organization()

        results = {
            'success':              success,
            'status':               status,
            'organization_found':   we_vote_organization_found,
            'organization':         we_vote_organization,
        }
        return results


class VoteSmartState(models.Model):
    """http://api.votesmart.org/docs/State.html
    """
    stateId = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=50)
    senators = models.CharField(max_length=255)  # example:  0
    billUrl = models.CharField(max_length=255)  # example:
    usCircuit = models.CharField(max_length=255)  # example:  Ninth
    ltGov = models.CharField(max_length=255)  # example:  t
    rollLower = models.CharField(max_length=255)  # example:  Roll no.
    lowerLegis = models.CharField(max_length=255)  # example:  Assembly
    voterReg = models.CharField(max_length=255)  # example:  <p style="orphans: 1;"><strong><span sty
    flower = models.CharField(max_length=255)  # example:  Golden Poppy
    area = models.CharField(max_length=255)  # example:  158,693 sq mi
    upperLegis = models.CharField(max_length=255)  # example:  Legislature
    termLength = models.CharField(max_length=255)  # example:  0
    bicameral = models.CharField(max_length=255)  # example:  t
    capital = models.CharField(max_length=255)  # example:  Sacramento
    voteUrl = models.CharField(max_length=255)  # example:
    nickName = models.CharField(max_length=255)  # example:  The Golden State
    bird = models.CharField(max_length=255)  # example:  California Valley Quail
    highPoint = models.CharField(max_length=255)  # example:  Mt. Whitney, 14,491 ft
    termLimit = models.CharField(max_length=255)  # example:  0
    lowPoint = models.CharField(max_length=255)  # example:  Death Valley, 282 ft below sea level.
    primaryDate = models.CharField(max_length=255)  # example:
    stateType = models.CharField(max_length=255)  # example:  State
    statehood = models.CharField(max_length=255)  # example:  Sept. 9, 1850 (31st state)
    reps = models.CharField(max_length=255)  # example:  0
    motto = models.CharField(max_length=255)  # example:  Eureka [I Have Found It]
    population = models.CharField(max_length=255)  # example:  36,961,664 (2009 est.)
    tree = models.CharField(max_length=255)  # example:
    generalDate = models.CharField(max_length=255)  # example:
    rollUpper = models.CharField(max_length=255)  # example:  Roll no.
    largestCity = models.CharField(max_length=255)  # example:


def vote_smart_state_filter(one_state):
    """
    Filter down the complete dict from Vote Smart to just the fields we use locally
    :param one_state:
    :return:
    """
    one_state_filtered = {
        'stateId': one_state['stateId'],
        'name': one_state['name'],
    }
    return one_state_filtered


# Methods.
def get_state(state_id):
    """Retrieve State from database."""
    return VoteSmartState.objects.filter(stateId=state_id)


def get_states():
    """"Retrieve all State objects from database."""
    return VoteSmartState.objects.all()
