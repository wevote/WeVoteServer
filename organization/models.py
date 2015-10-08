# organization/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
import wevote_functions.admin
from wevote_settings.models import fetch_next_id_we_vote_last_org_integer, fetch_site_unique_id_prefix


logger = wevote_functions.admin.get_logger(__name__)


class Organization(models.Model):
    # We are relying on built-in Python id field

    # The id_we_vote identifier is unique across all We Vote sites, and allows us to share our org info with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "org", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.id_we_vote_last_org_integer
    id_we_vote = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)
    name = models.CharField(
        verbose_name="organization name", max_length=255, default=None, null=True, blank=True)
    url = models.URLField(verbose_name='url of the endorsing organization', blank=True, null=True)
    twitter_handle = models.CharField(max_length=15, null=True, unique=False, verbose_name='twitter handle')

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
        return self.name

    class Meta:
        ordering = ('name',)

    # We override the save function so we can auto-generate id_we_vote
    def save(self, *args, **kwargs):
        # Even if this organization came from another source we still need a unique id_we_vote
        if self.id_we_vote:
            self.id_we_vote = self.id_we_vote.strip()
        if self.id_we_vote == "" or self.id_we_vote is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_id_we_vote_last_org_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "org" = tells us this is a unique id for an org
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.id_we_vote = "wv{site_unique_id_prefix}org{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
            # TODO we need to deal with the situation where id_we_vote is NOT unique on save
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


class OrganizationManager(models.Model):
    """
    A class for working with the Organization model
    """
    def retrieve_organization(self, organization_id, id_we_vote=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage = Organization()
        organization_on_stage_id = 0
        try:
            if organization_id > 0:
                organization_on_stage = Organization.objects.get(id=organization_id)
                organization_on_stage_id = organization_on_stage.id
            elif len(id_we_vote) > 0:
                organization_on_stage = Organization.objects.get(id_we_vote=id_we_vote)
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

    def fetch_organization_id(self, id_we_vote):
        organization_id = 0
        organization_manager = OrganizationManager()
        if len(id_we_vote) > 0:
            results = organization_manager.retrieve_organization(organization_id, id_we_vote)  # TODO DALE
            if results['success']:
                return results['organization_id']
        return 0
