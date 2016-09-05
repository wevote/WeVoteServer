# signals/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# Register signal savd and delete receiver for  CandidateCampaign, ContestMeasure, ContestOffice and Organization objects.
# Updates ElasticSearch index with any change to the object.
# Exceptions are cought and logged, so the transaction goes through even if indexing fails.
# In case of indexing errors, a full reindexing should be performed to bring the indexes up to speed
# TODO: move to seach module

import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from config.base import get_environment_variable

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from elasticsearch import Elasticsearch

from candidate.models import CandidateCampaign
from measure.models import ContestMeasure
from office.models import ContestOffice
from organization.models import Organization

logger = wevote_functions.admin.get_logger(__name__)

ELASTIC_SEARCH_CONNECTION_STRING = get_environment_variable("ELASTIC_SEARCH_CONNECTION_STRING")
if positive_value_exists(ELASTIC_SEARCH_CONNECTION_STRING):
    elastic_search_object = Elasticsearch(
        [ELASTIC_SEARCH_CONNECTION_STRING],
        timeout=2, max_retries=2, retry_on_timeout=True,
        maxsize=100
    )

# CandidateCampaign
@receiver(post_save, sender=CandidateCampaign)
def save_CandidateCampaign_signal(sender, instance, **kwargs):
    logger.debug("signals.save_CandidateCampaign_signal")
    if 'elastic_search_object' in globals():
        doc = {
            "candidate_name": instance.candidate_name,
            "candidate_twitter_handle": instance.candidate_twitter_handle,
            "twitter_name": instance.twitter_name,
            "party": instance.party,
            "google_civic_election_id": instance.google_civic_election_id,
            "state_code": instance.state_code,
            "we_vote_id" : instance.we_vote_id
        }
        try:
            res = elastic_search_object.index(index="candidates", doc_type='candidate', id=instance.id, body=doc)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to index CandidateCampaign " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)

@receiver(post_delete, sender=CandidateCampaign)
def delete_CandidateCampaign_signal(sender, instance, **kwargs):
    logger.debug("signals.delete_CandidateCampaign_signal")
    if 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="candidates", doc_type='candidate', id=instance.id)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to delete CandidateCampaign " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)

# ContestMeasure
@receiver(post_save, sender=ContestMeasure)
def save_ContestMeasure_signal(sender, instance, **kwargs):
    logger.debug("signals.save_ContestMeasure_signal")
    if 'elastic_search_object' in globals():
        doc = {
            "we_vote_id": instance.we_vote_id,
            "measure_subtitle": instance.measure_subtitle,
            "measure_text": instance.measure_text,
            "measure_title": instance.measure_title,
            "google_civic_election_id": instance.google_civic_election_id,
            "state_code": instance.state_code
        }
        try:
            res = elastic_search_object.index(index="measures", doc_type='measure', id=instance.id, body=doc)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to index ContestMeasure " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)

@receiver(post_delete, sender=ContestMeasure)
def delete_ContestMeasure_signal(sender, instance, **kwargs):
    logger.debug("signals.delete_ContestMeasure_signal")
    if 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="measures", doc_type='measure', id=instance.id)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to delete ContestMeasure " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)

# ContestOffice
@receiver(post_save, sender=ContestOffice)
def save_ContestOffice_signal(sender, instance, **kwargs):
    logger.debug("signals.save_ContestOffice_signal")
    if 'elastic_search_object' in globals():
        doc = {
            "we_vote_id": instance.we_vote_id,
            "office_name": instance.office_name,
            "google_civic_election_id": instance.google_civic_election_id,
            "state_code": instance.state_code
        }
        try:
            res = elastic_search_object.index(index="offices", doc_type='office', id=instance.id, body=doc)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to index ContestMeasure " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)

@receiver(post_delete, sender=ContestOffice)
def delete_ContestOffice_signal(sender, instance, **kwargs):
    logger.debug("signals.delete_ContestOffice_signal")
    if 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="offices", doc_type='office', id=instance.id)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to delete ContestMeasure " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)

# Organization
@receiver(post_save, sender=Organization)
def save_Organization_signal(sender, instance, **kwargs):
    logger.debug("signals.save_Organization_signal")
    if 'elastic_search_object' in globals():
        doc = {
            "we_vote_id": instance.we_vote_id,
            "organization_name": instance.organization_name,
            "organization_twitter_handle": instance.organization_twitter_handle,
            "organization_website": instance.organization_website,
            "twitter_description": instance.twitter_description,
            "state_served_code": instance.state_served_code,
        }
        try:
            res = elastic_search_object.index(index="organizations", doc_type='organization', id=instance.id, body=doc)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to index Organization " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)

@receiver(post_delete, sender=Organization)
def delete_Organization_signal(sender, instance, **kwargs):
    logger.debug("signals.delete_Organization_signal")
    if 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="organizations", doc_type='organization', id=instance.id)
            if (res["_shards"]["successful"]<=1):
                logger.error("failed to delete Organization " + instance.we_vote_id)
        except Exception as err:
            logger.error(err)


# @receiver(post_save)
# def save_signal(sender, **kwargs):
#     print("### save")
#
# @receiver(post_delete)
# def delete_signal(sender, **kwargs):
#     print("### delete")
#
# from django.core.signals import request_finished
# @receiver(request_finished)
# def request_signal(sender, **kwargs):
#     print("> request!")
#
# print("Signals Up")
