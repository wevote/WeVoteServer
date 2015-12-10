# organization/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, \
    handle_record_found_more_than_one_exception, handle_record_not_saved_exception
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_org_integer, fetch_site_unique_id_prefix


logger = wevote_functions.admin.get_logger(__name__)


class OrganizationManager(models.Manager):
    """
    A class for working with the Organization model
    """
    def create_organization_simple(self, organization_name, organization_website, organization_twitter_handle,
                                   organization_email='', organization_facebook='', organization_image=''):
        try:
            organization = self.create(organization_name=organization_name,
                                       organization_website=organization_website,
                                       organization_twitter_handle=organization_twitter_handle,
                                       organization_email=organization_email,
                                       organization_facebook=organization_facebook,
                                       organization_image=organization_image)
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            organization = Organization
        return organization

    def create_organization(self, organization_name, organization_website, organization_twitter_handle,
                            organization_email='', organization_facebook='', organization_image=''):
        try:
            organization = self.create(organization_name=organization_name,
                                       organization_website=organization_website,
                                       organization_twitter_handle=organization_twitter_handle,
                                       organization_email=organization_email,
                                       organization_facebook=organization_facebook,
                                       organization_image=organization_image)
            status = "CREATE_ORGANIZATION_SUCCESSFUL"
            success = True
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            organization = Organization
            status = "CREATE_ORGANIZATION_FAILED"
            success = False
        results = {
            'success':      success,
            'status':       status,
            'organization': organization,
        }
        return results

    def retrieve_organization(self, organization_id, we_vote_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage = Organization()
        organization_on_stage_id = 0
        status = "ERROR_ENTERING_RETRIEVE_ORGANIZATION"
        try:
            if positive_value_exists(organization_id):
                status = "ERROR_RETRIEVING_ORGANIZATION_WITH_ID"
                organization_on_stage = Organization.objects.get(id=organization_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_ID"
            elif positive_value_exists(we_vote_id):
                status = "ERROR_RETRIEVING_ORGANIZATION_WITH_WE_VOTE_ID"
                organization_on_stage = Organization.objects.get(we_vote_id=we_vote_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_WE_VOTE_ID"
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status = "ERROR_MORE_THAN_ONE_ORGANIZATION_FOUND"
            # logger.warn("Organization.MultipleObjectsReturned")
        except Organization.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status += ", ORGANIZATION_NOT_FOUND"
            # logger.warn("Organization.DoesNotExist")

        organization_on_stage_found = True if organization_on_stage_id > 0 else False
        results = {
            'success':                      True if organization_on_stage_found else False,
            'status':                       status,
            'organization_found':           organization_on_stage_found,
            'organization_id':
                organization_on_stage.id if organization_on_stage.id else organization_on_stage_id,
            'we_vote_id':
                organization_on_stage.we_vote_id if organization_on_stage.we_vote_id else we_vote_id,
            'organization':                 organization_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def fetch_organization_id(self, we_vote_id):
        organization_id = 0
        if positive_value_exists(we_vote_id):
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization(organization_id, we_vote_id)
            if results['success']:
                return results['organization_id']
        return 0

    def fetch_we_vote_id_from_local_id(self, organization_id):
        if positive_value_exists(organization_id):
            results = self.retrieve_organization(organization_id)
            if results['organization_found']:
                organization = results['organization']
                return organization.we_vote_id
            else:
                return ''
        else:
            return ''

    # We can use any of these four unique identifiers:
    #   organization.id, we_vote_id, organization_website, organization_twitter_handle
    # Pass in the value if we want it saved. Pass in "False" if we want to leave it the same.
    def update_or_create_organization(self, organization_id, we_vote_id,
                                      organization_website_search, organization_twitter_search,
                                      organization_name=False, organization_website=False,
                                      organization_twitter_handle=False, organization_email=False,
                                      organization_facebook=False, organization_image=False):
        """
        Either update or create an organization entry.
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage_found = False
        new_organization_created = False
        organization_on_stage = Organization()
        status = "ENTERING_UPDATE_OR_CREATE_ORGANIZATION"

        organization_id = convert_to_int(organization_id)
        we_vote_id = we_vote_id.strip()
        organization_website_search = organization_website_search.strip()
        organization_twitter_search = organization_twitter_search.strip()
        organization_name = organization_name.strip() if organization_name else False
        organization_website = organization_website.strip() if organization_website else False
        organization_twitter_handle = organization_twitter_handle.strip() if organization_twitter_handle else False
        organization_email = organization_email.strip() if organization_email else False
        organization_facebook = organization_facebook.strip() if organization_facebook else False
        organization_image = organization_image.strip() if organization_image else False

        # In order of authority
        # 1) organization_id exists? Find it with organization_id or fail
        # 2) we_vote_id exists? Find it with we_vote_id or fail
        # 3) organization_website_search exists? Try to find it. If not, go to step 4
        # 4) organization_twitter_search exists? Try to find it. If not, exit

        success = False
        if positive_value_exists(organization_id) or positive_value_exists(we_vote_id):
            # If here, we know we are updating
            # 1) organization_id exists? Find it with organization_id or fail
            # 2) we_vote_id exists? Find it with we_vote_id or fail
            organization_results = self.retrieve_organization(organization_id, we_vote_id)
            if organization_results['success']:
                organization_on_stage = organization_results['organization']
                if organization_name:
                    organization_on_stage.organization_name = organization_name
                if organization_website:
                    organization_on_stage.organization_website = organization_website
                if organization_twitter_handle:
                    organization_on_stage.organization_twitter_handle = organization_twitter_handle
                if organization_email:
                    organization_on_stage.organization_email = organization_email
                if organization_facebook:
                    organization_on_stage.organization_facebook = organization_facebook
                if organization_image:
                    organization_on_stage.organization_image = organization_image

                if organization_name or organization_website or organization_twitter_handle \
                        or organization_email or organization_facebook or organization_image:
                    organization_on_stage.save()
                    success = True
                    status = "SAVED_WITH_ORG_ID_OR_WE_VOTE_ID"
                else:
                    success = True
                    status = "NO_CHANGES_SAVED_WITH_ORG_ID_OR_WE_VOTE_ID"
            else:
                status = "ORGANIZATION_COULD_NOT_BE_FOUND_WITH_ORG_ID_OR_WE_VOTE_ID"
        else:
            try:
                found_with_status = ''

                # 3) organization_website_search exists? Try to find it. If not, go to step 4
                if positive_value_exists(organization_website_search):
                    try:
                        organization_on_stage = Organization.objects.get(
                            organization_website=organization_website_search)
                        organization_on_stage_found = True
                        found_with_status = "FOUND_WITH_WEBSITE"
                    except Organization.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        logger.warn("Organization.MultipleObjectsReturned")
                    except Organization.DoesNotExist as e:
                        # Not a problem -- an organization matching this twitter handle wasn't found
                        exception_does_not_exist = True

                # 4) organization_twitter_search exists? Try to find it. If not, exit
                if not organization_on_stage_found:
                    if positive_value_exists(organization_twitter_search):
                        try:
                            organization_on_stage = Organization.objects.get(
                                organization_twitter_handle=organization_twitter_search)
                            organization_on_stage_found = True
                            found_with_status = "FOUND_WITH_TWITTER"
                        except Organization.MultipleObjectsReturned as e:
                            handle_record_found_more_than_one_exception(e, logger)
                            exception_multiple_object_returned = True
                            logger.warn("Organization.MultipleObjectsReturned")
                        except Organization.DoesNotExist as e:
                            # Not a problem -- an organization matching this twitter handle wasn't found
                            exception_does_not_exist = True

                # 3 & 4) Save values entered in steps 3 & 4
                if organization_on_stage_found:
                    if organization_name or organization_website or organization_twitter_handle \
                            or organization_email or organization_facebook or organization_image:
                        if organization_name:
                            organization_on_stage.organization_name = organization_name
                        if organization_website:
                            organization_on_stage.organization_website = organization_website
                        if organization_twitter_handle:
                            organization_on_stage.organization_twitter_handle = organization_twitter_handle
                        if organization_email:
                            organization_on_stage.organization_email = organization_email
                        if organization_facebook:
                            organization_on_stage.organization_facebook = organization_facebook
                        if organization_image:
                            organization_on_stage.organization_image = organization_image
                        organization_on_stage.save()
                        success = True
                        status = found_with_status + " SAVED"
                    else:
                        success = True
                        status = found_with_status + " NO_CHANGES_SAVED"
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)

        if not organization_on_stage_found:
            try:
                # If here, create new organization
                results = Organization.objects.create_organization(organization_name, organization_website,
                                                                   organization_twitter_handle, organization_email,
                                                                   organization_facebook, organization_image)
                if results['success']:
                    new_organization_created = True
                    success = True
                    status = "NEW_ORGANIZATION_CREATED_IN_UPDATE_OR_CREATE"
                    organization_on_stage = results['organization']
                else:
                    success = False
                    status = results['status']
                    organization_on_stage = Organization

            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                success = False
                status = "NEW_ORGANIZATION_COULD_NOT_BE_CREATED"
                organization_on_stage = Organization

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'organization':             organization_on_stage,
            'new_organization_created': new_organization_created,
        }
        return results

    def delete_organization(self, organization_id):
        organization_id = convert_to_int(organization_id)
        organization_deleted = False

        try:
            if organization_id:
                results = self.retrieve_organization(organization_id)
                if results['organization_found']:
                    organization = results['organization']
                    organization_id = organization.id
                    organization.delete()
                    organization_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':              organization_deleted,
            'organization_deleted': organization_deleted,
            'organization_id':      organization_id,
        }
        return results


class OrganizationListManager(models.Manager):
    """
    A class for working with lists of Organizations
    """

    def organization_search_find_any_possibilities(self, organization_name, organization_twitter_handle,
                                                   organization_website, organization_email):
        """
        We want to find *any* possible organization that includes any of the search terms
        :param organization_name:
        :param organization_twitter_handle:
        :param organization_website:
        :param organization_email:
        :return:
        """
        organization_list_for_json = {}
        try:
            filters = []
            organization_list_for_json = []
            organization_objects_list = []
            if positive_value_exists(organization_name):
                new_filter = Q(organization_name__icontains=organization_name)
                filters.append(new_filter)

            if positive_value_exists(organization_twitter_handle):
                new_filter = Q(organization_twitter_handle__icontains=organization_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(organization_website):
                new_filter = Q(organization_website__icontains=organization_website)
                filters.append(new_filter)

            if positive_value_exists(organization_email):
                new_filter = Q(organization_email__icontains=organization_email)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                organization_objects_list = Organization.objects.filter(final_filters)

            if len(organization_objects_list):
                organizations_found = True
                status = 'ORGANIZATIONS_RETRIEVED'
                for organization in organization_objects_list:
                    one_organization_json = {
                        'organization_id': organization.id,
                        'organization_we_vote_id': organization.we_vote_id,
                        'organization_name':
                            organization.organization_name if positive_value_exists(
                                organization.organization_name) else '',
                        'organization_website': organization.organization_website if positive_value_exists(
                            organization.organization_website) else '',
                        'organization_twitter_handle':
                            organization.organization_twitter_handle if positive_value_exists(
                                organization.organization_twitter_handle) else '',
                        'organization_email':
                            organization.organization_email if positive_value_exists(
                                organization.organization_email) else '',
                        'organization_facebook':
                            organization.organization_facebook if positive_value_exists(
                                organization.organization_facebook) else '',
                    }
                    organization_list_for_json.append(one_organization_json)
            else:
                organizations_found = False
                status = 'NO_ORGANIZATIONS_RETRIEVED'
            success = True
        except Organization.DoesNotExist:
            # No organizations found. Not a problem.
            organizations_found = False
            status = 'NO_ORGANIZATIONS_FOUND_DoesNotExist'
            success = True  # We are still successful if no organizations are found
        except Exception as e:
            organizations_found = False
            handle_exception(e, logger=logger)
            status = 'FAILED organization_search_find_any_possibilities ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        results = {
            'status':               status,
            'success':              success,
            'organizations_found':  organizations_found,
            'organizations_list':   organization_list_for_json,
        }
        return results


class Organization(models.Model):
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our org info with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "org", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_org_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=True)
    organization_name = models.CharField(
        verbose_name="organization name", max_length=255, null=False, blank=False)
    organization_website = models.URLField(verbose_name='url of the endorsing organization', blank=True, null=True)
    organization_twitter_handle = models.CharField(
        verbose_name='organization twitter handle', max_length=255, null=True, unique=False)
    organization_email = models.EmailField(
        verbose_name='organization contact email address', max_length=255, unique=False, null=True, blank=True)
    organization_facebook = models.URLField(verbose_name='url of facebook page', blank=True, null=True)
    organization_image = models.CharField(verbose_name='organization image', max_length=255, null=True, unique=False)

    NONPROFIT_501C3 = '3'
    NONPROFIT_501C4 = '4'
    POLITICAL_ACTION_COMMITTEE = 'P'
    CORPORATION = 'C'
    NEWS_CORPORATION = 'N'
    UNKNOWN = 'U'
    ORGANIZATION_TYPE_CHOICES = (
        (NONPROFIT_501C3, 'Nonprofit 501c3'),
        (NONPROFIT_501C4, 'Nonprofit 501c4'),
        (POLITICAL_ACTION_COMMITTEE, 'Political Action Committee'),
        (CORPORATION, 'Corporation'),
        (NEWS_CORPORATION, 'News Corporation'),
        (UNKNOWN, 'Unknown'),
    )

    organization_type = models.CharField(
        verbose_name="type of org", max_length=1, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)

    def __unicode__(self):
        return self.organization_name

    class Meta:
        ordering = ('organization_name',)

    objects = OrganizationManager()

    @classmethod
    def create(cls, organization_name, organization_website, organization_twitter_handle, organization_email,
               organization_facebook, organization_image):
        organization = cls(organization_name=organization_name,
                           organization_website=organization_website,
                           organization_twitter_handle=organization_twitter_handle,
                           organization_email=organization_email,
                           organization_facebook=organization_facebook,
                           organization_image=organization_image)
        return organization

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this organization came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_org_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "org" = tells us this is a unique id for an org
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}org{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
            # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        super(Organization, self).save(*args, **kwargs)

    def is_nonprofit_501c3(self):
        return self.organization_type in self.NONPROFIT_501C3

    def is_nonprofit_501c4(self):
        return self.organization_type in self.NONPROFIT_501C4

    def is_political_action_committee(self):
        return self.organization_type in self.POLITICAL_ACTION_COMMITTEE

    def is_corporation(self):
        return self.organization_type in self.CORPORATION

    def is_news_corporation(self):
        return self.organization_type in self.NEWS_CORPORATION

    def is_organization_type_specified(self):
        return self.organization_type in (
            self.NONPROFIT_501C3, self.NONPROFIT_501C4, self.POLITICAL_ACTION_COMMITTEE,
            self.CORPORATION, self.NEWS_CORPORATION)
