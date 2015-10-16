# organization/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_exception, handle_record_not_found_exception, \
    handle_record_found_more_than_one_exception, handle_record_not_saved_exception
import wevote_functions.admin
from wevote_functions.models import value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_org_integer, fetch_site_unique_id_prefix


logger = wevote_functions.admin.get_logger(__name__)


class OrganizationManager(models.Manager):
    """
    A class for working with the Organization model
    """
    def create_organization(self, organization_name, organization_website, organization_twitter):
        organization = self.create(organization_name=organization_name, organization_website=organization_website,
                                   twitter_handle=organization_twitter)
        return organization

    def retrieve_organization(self, organization_id, we_vote_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage = Organization()
        organization_on_stage_id = 0
        try:
            if organization_id > 0:
                organization_on_stage = Organization.objects.get(id=organization_id)
                organization_on_stage_id = organization_on_stage.id
            elif len(we_vote_id) > 0:
                organization_on_stage = Organization.objects.get(we_vote_id=we_vote_id)
                organization_on_stage_id = organization_on_stage.id
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            logger.warn("Organization.MultipleObjectsReturned")
        except Organization.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            logger.warn("Organization.DoesNotExist")

        organization_on_stage_found = True if organization_on_stage_id > 0 else False
        results = {
            'success':                      True if organization_on_stage_found else False,
            'organization_found':           organization_on_stage_found,
            'organization_id':              organization_on_stage_id,
            'organization':                 organization_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def fetch_organization_id(self, we_vote_id):
        organization_id = 0
        organization_manager = OrganizationManager()
        if len(we_vote_id) > 0:
            results = organization_manager.retrieve_organization(organization_id, we_vote_id)  # TODO DALE
            if results['success']:
                return results['organization_id']
        return 0

    # We can use any of these four unique identifiers:
    #   organization.id, we_vote_id, organization_website, twitter_handle
    # Pass in the value if we want it saved. Pass in "False" if we want to leave it the same.
    def update_or_create_organization(self, organization_id, we_vote_id,
                                      organization_website_search, organization_twitter_search,
                                      organization_name=False, organization_website=False,
                                      organization_twitter=False):
        """
        Either update or create an organization entry.
        """
        exception_multiple_object_returned = False
        organization_on_stage_found = False
        new_organization_created = False

        organization_id = organization_id.clean()
        we_vote_id = we_vote_id.clean()
        organization_website_search = organization_website_search.clean()  # TODO Do further cleanup
        organization_twitter_search = organization_twitter_search.clean()  # TODO Do further cleanup

        # In order of authority
        # 1) organization_id exists? Find it with organization_id or fail
        # 2) we_vote_id exists? Find it with we_vote_id or fail
        # 3) organization_website_search exists? Try to find it. If not, go to step 4
        # 4) organization_twitter_search exists? Try to find it. If not, exit

        success = False
        if value_exists(organization_id) or value_exists(we_vote_id):
            # If here, we know we are updating
            status = "ATTEMPTING UPDATE WITH ORG_ID or WE_VOTE_ID"
            # 1) organization_id exists? Find it with organization_id or fail
            # 2) we_vote_id exists? Find it with we_vote_id or fail
            organization_results = self.retrieve_organization(organization_id, we_vote_id)
            if organization_results['success']:
                organization_on_stage = organization_results['organization']
                if organization_name:
                    organization_on_stage.organization_name = organization_name
                if organization_website:
                    organization_on_stage.organization_website = organization_website
                if organization_twitter:
                    organization_on_stage.twitter_handle = organization_twitter

                if organization_name or organization_website or organization_twitter:
                    organization_on_stage.save()
                    success = True
                    status = "SAVED WITH ORG_ID or WE_VOTE_ID"
                else:
                    success = True
                    status = "NO CHANGES SAVED WITH ORG_ID or WE_VOTE_ID"
        else:
            try:
                # 3) organization_website_search exists? Try to find it. If not, go to step 4
                if value_exists(organization_website_search):
                    try:
                        organization_on_stage = Organization.objects.get(
                            organization_website=organization_website_search)
                        organization_on_stage_found = True
                    except Organization.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        logger.warn("Organization.MultipleObjectsReturned")
                    except Organization.DoesNotExist as e:
                        handle_record_not_found_exception(e, logger)
                        exception_does_not_exist = True
                        logger.warn("Organization.DoesNotExist")

                # 4) organization_twitter_search exists? Try to find it. If not, exit
                if not organization_on_stage_found:
                    if value_exists(organization_twitter_search):
                        try:
                            organization_on_stage = Organization.objects.get(
                                twitter_handle=organization_twitter_search)
                            organization_on_stage_found = True
                        except Organization.MultipleObjectsReturned as e:
                            handle_record_found_more_than_one_exception(e, logger)
                            exception_multiple_object_returned = True
                            logger.warn("Organization.MultipleObjectsReturned")
                        except Organization.DoesNotExist as e:
                            handle_record_not_found_exception(e, logger)
                            exception_does_not_exist = True
                            logger.warn("Organization.DoesNotExist")

                # 3 & 4) Save values entered in steps 3 & 4
                if organization_on_stage_found:
                    if organization_name or organization_website or organization_twitter:
                        if organization_name:
                            organization_on_stage.organization_name = organization_name
                        if organization_website:
                            organization_on_stage.organization_website = organization_website
                        if organization_twitter:
                            organization_on_stage.twitter_handle = organization_twitter
                        organization_on_stage.save()
                        success = True
                        status = "SAVED WITH ORG_ID or WE_VOTE_ID"
                    else:
                        success = True
                        status = "NO CHANGES SAVED WITH ORG_ID or WE_VOTE_ID"
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)

        if not organization_on_stage_found:
            try:
                # If here, create new organization
                organization_on_stage = self.create_organization(organization_name, organization_website,
                                                                 organization_twitter)
                new_organization_created = True
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)

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
        organization_id = int(organization_id)
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
    twitter_handle = models.CharField(max_length=15, null=True, unique=True, verbose_name='twitter handle')

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

    # Link to a logo for this organization
    # logo

    def __unicode__(self):
        return self.organization_name

    class Meta:
        ordering = ('organization_name',)

    objects = OrganizationManager()

    @classmethod
    def create(cls, organization_name, organization_website, organization_twitter):
        organization = cls(organization_name=organization_name, organization_website=organization_website,
                           twitter_handle=organization_twitter)
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
