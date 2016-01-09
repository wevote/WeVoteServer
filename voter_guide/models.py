# voter_guide/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_exception, handle_record_not_found_exception, \
    handle_record_found_more_than_one_exception
from organization.models import Organization
import wevote_functions.admin
from wevote_functions.models import convert_to_int, convert_to_str, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


class VoterGuideManager(models.Manager):
    """
    A class for working with the VoterGuide model
    """
    def update_or_create_organization_voter_guide_by_election_id(self, organization_we_vote_id,
                                                                 google_civic_election_id):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.ORGANIZATION
        exception_multiple_object_returned = False
        if not google_civic_election_id or not organization_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_ORGANIZATION_VOTER_GUIDE'
            success = False
            new_voter_guide_created = False
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'organization_we_vote_id': organization_we_vote_id,
                    # The rest of the values
                }
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    organization_we_vote_id__exact=organization_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_ORGANIZATION'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_ORGANIZATION'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_ORGANIZATION'
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_organization_voter_guide_by_time_span(self, organization_we_vote_id, vote_smart_time_span):
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.ORGANIZATION
        exception_multiple_object_returned = False
        if not vote_smart_time_span or not organization_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_ORGANIZATION_VOTER_GUIDE_BY_TIME_SPAN'
            success = False
            new_voter_guide_created = False
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'vote_smart_time_span': vote_smart_time_span,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'organization_we_vote_id': organization_we_vote_id,
                    # The rest of the values
                }
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    vote_smart_time_span__exact=vote_smart_time_span,
                    organization_we_vote_id__exact=organization_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_ORGANIZATION_BY_TIME_SPAN'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_ORGANIZATION_BY_TIME_SPAN'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_ORGANIZATION_BY_TIME_SPAN'
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_public_figure_voter_guide(self, google_civic_election_id, public_figure_we_vote_id):
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.PUBLIC_FIGURE
        exception_multiple_object_returned = False
        if not google_civic_election_id or not public_figure_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_PUBLIC_FIGURE_VOTER_GUIDE'
            new_voter_guide_created = False
            success = False
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'public_figure_we_vote_id': public_figure_we_vote_id,
                    # The rest of the values
                }
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_guide_owner_type__exact=voter_guide_owner_type,
                    public_figure_we_vote_id__exact=public_figure_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_PUBLIC_FIGURE'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_PUBLIC_FIGURE'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_PUBLIC_FIGURE'
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_voter_voter_guide(self, google_civic_election_id, owner_voter_id):
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.VOTER
        owner_voter_id = convert_to_int(owner_voter_id)
        exception_multiple_object_returned = False
        if not google_civic_election_id or not owner_voter_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_VOTER_VOTER_GUIDE'
            new_voter_guide_created = False
            success = False
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'owner_voter_id': owner_voter_id,
                    # The rest of the values
                }
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_guide_owner_type__exact=voter_guide_owner_type,
                    owner_voter_id__exact=owner_voter_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_VOTER'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_VOTER'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_VOTER'
                exception_multiple_object_returned = True
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def retrieve_voter_guide(self, voter_guide_id=0, google_civic_election_id=0,
                             organization_we_vote_id=None, public_figure_we_vote_id=None, owner_we_vote_id=None):
        voter_guide_id = convert_to_int(voter_guide_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        organization_we_vote_id = convert_to_str(organization_we_vote_id)
        public_figure_we_vote_id = convert_to_str(public_figure_we_vote_id)
        owner_we_vote_id = convert_to_str(owner_we_vote_id)

        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_guide_on_stage = VoterGuide()
        voter_guide_on_stage_id = 0
        status = "ERROR_ENTERING_RETRIEVE_VOTER_GUIDE"
        try:
            if positive_value_exists(voter_guide_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ID"  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(id=voter_guide_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_ID"
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ORGANIZATION_WE_VOTE_ID"  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              organization_we_vote_id=organization_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_ORGANIZATION_WE_VOTE_ID"
            elif positive_value_exists(public_figure_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_PUBLIC_FIGURE_WE_VOTE_ID"  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              public_figure_we_vote_id=public_figure_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_PUBLIC_FIGURE_WE_VOTE_ID"
            elif positive_value_exists(owner_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_VOTER_WE_VOTE_ID"  # Set this in case the get fails
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              owner_we_vote_id=owner_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_VOTER_WE_VOTE_ID"
            else:
                status = "Insufficient variables included to retrieve one voter guide."
        except VoterGuide.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status += ", ERROR_MORE_THAN_ONE_VOTER_GUIDE_FOUND"
        except VoterGuide.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status += ", VOTER_GUIDE_NOT_FOUND"

        voter_guide_on_stage_found = True if voter_guide_on_stage_id > 0 else False
        results = {
            'success':                      True if voter_guide_on_stage_found else False,
            'status':                       status,
            'voter_guide_found':            voter_guide_on_stage_found,
            'voter_guide_id':               voter_guide_on_stage_id,
            'organization_we_vote_id':      voter_guide_on_stage.organization_we_vote_id,
            'public_figure_we_vote_id':     voter_guide_on_stage.public_figure_we_vote_id,
            'owner_we_vote_id':             voter_guide_on_stage.owner_we_vote_id,
            'voter_guide':                  voter_guide_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def delete_voter_guide(self, voter_guide_id):
        voter_guide_id = convert_to_int(voter_guide_id)
        voter_guide_deleted = False

        try:
            if voter_guide_id:
                results = self.retrieve_voter_guide(voter_guide_id)
                if results['voter_guide_found']:
                    voter_guide = results['voter_guide']
                    voter_guide_id = voter_guide.id
                    voter_guide.delete()
                    voter_guide_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':              voter_guide_deleted,
            'voter_guide_deleted': voter_guide_deleted,
            'voter_guide_id':      voter_guide_id,
        }
        return results


class VoterGuide(models.Model):
    # We are relying on built-in Python id field

    # NOTE: We are using we_vote_id's instead of internal ids
    # The unique id of the organization. May be null if voter_guide owned by a public figure or voter instead of org.
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure. May be null if voter_guide owned by org or voter instead of public figure.
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure. May be null if voter_guide owned by org or public figure instead of voter.
    owner_we_vote_id = models.CharField(
        verbose_name="individual voter's we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the voter that owns this guide. May be null if voter_guide owned by an org
    # or public figure instead of by a voter.
    # DEPRECATE THIS - 2015-11-11 We should use
    owner_voter_id = models.PositiveIntegerField(
        verbose_name="the unique voter id of the voter who this guide is about", default=0, null=True, blank=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True)

    # Usually in one of these two formats 2015, 2014-2015
    vote_smart_time_span = models.CharField(
        verbose_name="the period in which the organization stated this position", max_length=255, null=True,
        blank=True, unique=False)

    ORGANIZATION = 'O'
    PUBLIC_FIGURE = 'P'
    VOTER = 'V'
    VOTER_GUIDE_TYPE_CHOICES = (
        (ORGANIZATION, 'Organization'),
        (PUBLIC_FIGURE, 'Public Figure or Politician'),
        (VOTER, 'Voter'),
    )

    voter_guide_owner_type = models.CharField(
        verbose_name="is owner org, public figure, or voter?", max_length=1, choices=VOTER_GUIDE_TYPE_CHOICES,
        default=ORGANIZATION)

    # The date of the last change to this voter_guide
    last_updated = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def __unicode__(self):
        return self.last_updated

    class Meta:
        ordering = ('last_updated',)

    objects = VoterGuideManager()

    def organization(self):
        try:
            organization = Organization.objects.get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("voter_guide.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("voter_guide.organization did not find")
            return
        return organization


# This is the class that we use to rapidly show lists of voter guides, regardless of whether they are from an
# organization, public figure, or voter
class VoterGuideList(models.Model):
    """
    A set of methods to retrieve a list of voter_guides
    """

    def retrieve_voter_guides_to_follow_by_ballot_item(self, ballot_item_we_vote_id):
        success = False
        status = "TO_BE_DETERMINED"
        voter_guide_list = []
        voter_guide_list_found = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_voter_guides_to_follow_by_election(self, google_civic_election_id):
        success = False
        status = "TO_BE_DETERMINED"
        voter_guide_list = []
        voter_guide_list_found = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    # NOTE: This is extremely simple way to retrieve voter guides. Being replaced by:
    #  retrieve_voter_guides_by_ballot_item(ballot_item_we_vote_id) AND
    #  retrieve_voter_guides_by_election(google_civic_election_id)
    def retrieve_voter_guides_for_election(self, google_civic_election_id):
        voter_guide_list = []
        voter_guide_list_found = False

        try:
            voter_guide_queryset = VoterGuide.objects.order_by('last_updated')
            voter_guide_list = voter_guide_queryset.filter(
                google_civic_election_id=google_civic_election_id)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_all_voter_guides(self):
        voter_guide_list = []
        voter_guide_list_found = False
        try:
            voter_guide_queryset = VoterGuide.objects.order_by('last_updated')
            voter_guide_list = voter_guide_queryset

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results


class VoterGuidePossibilityManager(models.Manager):
    """
    A class for working with the VoterGuidePossibility model
    """
    def update_or_create_voter_guide_possibility(self, voter_guide_possibility_url, google_civic_election_id=0):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        # TODO Implement the following to have a chance of normalizing URL's pasted in by volunteers
        #   http://nullege.com/codes/search/scrapy.utils.url.canonicalize_url
        # voter_guide_possibility_url =
        exception_multiple_object_returned = False
        if voter_guide_possibility_url and google_civic_election_id:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_possibility_url': voter_guide_possibility_url,
                    # The rest of the values
                }
                voter_guide_possibility_on_stage, new_voter_guide_possibility_created = \
                    VoterGuidePossibility.objects.update_or_create(
                        google_civic_election_id__exact=google_civic_election_id,
                        voter_guide_possibility_url__exact=voter_guide_possibility_url,
                        defaults=updated_values)
                success = True
                if new_voter_guide_possibility_created:
                    status = 'VOTER_GUIDE_POSSIBILITY_CREATED_WITH_ELECTION'
                else:
                    status = 'VOTER_GUIDE_POSSIBILITY_UPDATED_WITH_ELECTION'
            except VoterGuidePossibility.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDE_POSSIBILITIES_FOUND_BY_URL_AND_ELECTION'
                exception_multiple_object_returned = True
                new_voter_guide_possibility_created = False
        elif voter_guide_possibility_url:  # No google_civic_election_id provided
            try:
                updated_values = {
                    # Values we search against below
                    'voter_guide_possibility_url': voter_guide_possibility_url,
                    # The rest of the values
                }
                voter_guide_possibility_on_stage, new_voter_guide_possibility_created = \
                    VoterGuidePossibility.objects.update_or_create(
                        voter_guide_possibility_url__exact=voter_guide_possibility_url,
                        defaults=updated_values)
                success = True
                if new_voter_guide_possibility_created:
                    status = 'VOTER_GUIDE_POSSIBILITY_CREATED_WITHOUT_ELECTION'
                else:
                    status = 'VOTER_GUIDE_POSSIBILITY_UPDATED_WITHOUT_ELECTION'
            except VoterGuidePossibility.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDE_POSSIBILITIES_FOUND_BY_URL'
                exception_multiple_object_returned = True
                new_voter_guide_possibility_created = False
        else:
            status = 'ERROR_VARIABLES_MISSING_FOR_VOTER_GUIDE_POSSIBILITY'
            success = False
            new_voter_guide_possibility_created = False

        results = {
            'success':                              success,
            'status':                               status,
            'MultipleObjectsReturned':              exception_multiple_object_returned,
            'voter_guide_possibility_saved':        success,
            'new_voter_guide_possibility_created':  new_voter_guide_possibility_created,
        }
        return results

    def retrieve_voter_guide_possibility_from_url(self, voter_guide_possibility_url):
        voter_guide_possibility_id = 0
        google_civic_election_id = 0
        return self.retrieve_voter_guide_possibility(voter_guide_possibility_id, google_civic_election_id,
                                                     voter_guide_possibility_url)

    def retrieve_voter_guide_possibility(self, voter_guide_possibility_id=0, google_civic_election_id=0,
                                         voter_guide_possibility_url='',
                                         organization_we_vote_id=None,
                                         public_figure_we_vote_id=None,
                                         owner_we_vote_id=None):
        voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        organization_we_vote_id = convert_to_str(organization_we_vote_id)
        public_figure_we_vote_id = convert_to_str(public_figure_we_vote_id)
        owner_we_vote_id = convert_to_str(owner_we_vote_id)

        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_guide_possibility_on_stage = VoterGuidePossibility()
        voter_guide_possibility_on_stage_id = 0
        try:
            if positive_value_exists(voter_guide_possibility_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_ID"  # Set this in case the get fails
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(id=voter_guide_possibility_id)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_ID"
                success = True
            elif positive_value_exists(voter_guide_possibility_url):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_URL"  # Set this in case the get fails
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    voter_guide_possibility_url=voter_guide_possibility_url)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_URL"
                success = True
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                # Set this status in case the 'get' fails
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_ORGANIZATION_WE_VOTE_ID"
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    google_civic_election_id=google_civic_election_id,
                    organization_we_vote_id=organization_we_vote_id)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_ORGANIZATION_WE_VOTE_ID"
                success = True
            elif positive_value_exists(public_figure_we_vote_id) and positive_value_exists(google_civic_election_id):
                # Set this status in case the 'get' fails
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_PUBLIC_FIGURE_WE_VOTE_ID"
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    google_civic_election_id=google_civic_election_id,
                    public_figure_we_vote_id=public_figure_we_vote_id)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_PUBLIC_FIGURE_WE_VOTE_ID"
                success = True
            elif positive_value_exists(owner_we_vote_id) and positive_value_exists(google_civic_election_id):
                # Set this status in case the 'get' fails
                status = "ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_VOTER_WE_VOTE_ID"
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    google_civic_election_id=google_civic_election_id,
                    owner_we_vote_id=owner_we_vote_id)
                voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                status = "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_VOTER_WE_VOTE_ID"
                success = True
            else:
                status = "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_INSUFFICIENT_VARIABLES"
                success = False
        except VoterGuidePossibility.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status += ", ERROR_MORE_THAN_ONE_VOTER_GUIDE_POSSIBILITY_FOUND"
            success = False
        except VoterGuidePossibility.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status = "VOTER_GUIDE_POSSIBILITY_NOT_FOUND"
            success = True

        voter_guide_possibility_on_stage_found = True if voter_guide_possibility_on_stage_id > 0 else False
        results = {
            'success':                          success,
            'status':                           status,
            'voter_guide_possibility_found':    voter_guide_possibility_on_stage_found,
            'voter_guide_possibility_id':       voter_guide_possibility_on_stage_id,
            'voter_guide_possibility_url':      voter_guide_possibility_on_stage.voter_guide_possibility_url,
            'organization_we_vote_id':          voter_guide_possibility_on_stage.organization_we_vote_id,
            'public_figure_we_vote_id':         voter_guide_possibility_on_stage.public_figure_we_vote_id,
            'owner_we_vote_id':                 voter_guide_possibility_on_stage.owner_we_vote_id,
            'voter_guide':                      voter_guide_possibility_on_stage,
            'error_result':                     error_result,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
        }
        return results

    def delete_voter_guide_possibility(self, voter_guide_possibility_id):
        voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
        voter_guide_deleted = False

        try:
            if voter_guide_possibility_id:
                results = self.retrieve_voter_guide_possibility(voter_guide_possibility_id)
                if results['voter_guide_found']:
                    voter_guide = results['voter_guide']
                    voter_guide_possibility_id = voter_guide.id
                    voter_guide.delete()
                    voter_guide_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':              voter_guide_deleted,
            'voter_guide_deleted': voter_guide_deleted,
            'voter_guide_possibility_id':      voter_guide_possibility_id,
        }
        return results


class VoterGuidePossibility(models.Model):
    """
    We ask volunteers to enter a list of urls that might have voter guides. This table stores the URLs and partial
    information, prior to a full-fledged voter guide being saved in the VoterGuide table.
    """
    # We are relying on built-in Python id field

    # Where a volunteer thinks there is a voter guide
    voter_guide_possibility_url = models.URLField(verbose_name='url of possible voter guide', blank=True, null=True)

    # The unique id of the organization, if/when we know it
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure, if/when we know it
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure, if/when we know it
    owner_we_vote_id = models.CharField(
        verbose_name="individual voter's we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(verbose_name="google civic election id", null=True)

    # TODO Convert these to refer to the values set in VoterGuide so we don't duplicate them here
    ORGANIZATION = 'O'
    PUBLIC_FIGURE = 'P'
    VOTER = 'V'
    VOTER_GUIDE_TYPE_CHOICES = (
        (ORGANIZATION, 'Organization'),
        (PUBLIC_FIGURE, 'Public Figure or Politician'),
        (VOTER, 'Voter'),
    )

    voter_guide_owner_type = models.CharField(
        verbose_name="is owner org, public figure, or voter?", max_length=1, choices=VOTER_GUIDE_TYPE_CHOICES,
        default=ORGANIZATION)

    # The date of the last change to this voter_guide_possibility
    last_updated = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def __unicode__(self):
        return self.last_updated

    class Meta:
        ordering = ('last_updated',)

    objects = VoterGuideManager()

    def organization(self):
        try:
            organization = Organization.objects.get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("voter_guide.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("voter_guide.organization did not find")
            return
        return organization
