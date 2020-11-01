# search/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import BallotReturnedManager
from config.base import get_environment_variable
from candidate.models import CandidateCampaign
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from elasticsearch import Elasticsearch
from election.models import Election
from measure.models import ContestMeasure
from office.models import ContestOffice
from organization.models import Organization
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)
STATE_CODE_MAP = {
    'AK': 'Alaska',
    'AL': 'Alabama',
    'AR': 'Arkansas',
    'AS': 'American Samoa',
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DC': 'District of Columbia',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'GU': 'Guam',
    'HI': 'Hawaii',
    'IA': 'Iowa',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'MA': 'Massachusetts',
    'MD': 'Maryland',
    'ME': 'Maine',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MO': 'Missouri',
    'MP': 'Northern Mariana Islands',
    'MS': 'Mississippi',
    'MT': 'Montana',
    'NA': 'National',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'NE': 'Nebraska',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NV': 'Nevada',
    'NY': 'New York',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'PR': 'Puerto Rico',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VA': 'Virginia',
    'VI': 'Virgin Islands',
    'VT': 'Vermont',
    'WA': 'Washington',
    'WI': 'Wisconsin',
    'WV': 'West Virginia',
    'WY': 'Wyoming',
}

ELASTIC_SEARCH_TURNED_ON = False


def convert_state_code_to_state_text(incoming_state_code):
    for state_code, state_name in STATE_CODE_MAP.items():
        if incoming_state_code.lower() == state_code.lower():
            return state_name
    else:
        return ""

ELASTIC_SEARCH_CONNECTION_STRING = get_environment_variable("ELASTIC_SEARCH_CONNECTION_STRING")
if positive_value_exists(ELASTIC_SEARCH_CONNECTION_STRING):
    elastic_search_object = Elasticsearch(
        [ELASTIC_SEARCH_CONNECTION_STRING],
        timeout=2, max_retries=2, retry_on_timeout=True,
        maxsize=100
    )


# CandidateCampaign
@receiver(post_save, sender=CandidateCampaign)
def save_candidate_campaign_signal(sender, instance, **kwargs):
    # logger.debug("search.save_candidate_campaign_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        doc = {
            "candidate_name": instance.candidate_name,
            "candidate_twitter_handle": instance.candidate_twitter_handle,
            "twitter_name": instance.twitter_name,
            "party": instance.party,
            "google_civic_election_id": instance.google_civic_election_id,
            "state_code": instance.state_code,
            "we_vote_id": instance.we_vote_id
        }
        try:
            res = elastic_search_object.index(index="candidates", doc_type='candidate', id=instance.id, body=doc)
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to index CandidateCampaign " + str(instance.we_vote_id))
        except Exception as err:
            status = "SAVE_CANDIDATE_CAMPAIGN_SIGNAL, err: " + str(err)
            logger.error(status)


@receiver(post_delete, sender=CandidateCampaign)
def delete_candidate_campaign_signal(sender, instance, **kwargs):
    # logger.debug("search.delete_CandidateCampaign_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="candidates", doc_type='candidate', id=instance.id)
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to delete CandidateCampaign " + str(instance.we_vote_id))
        except Exception as err:
            status = "DELETE_CANDIDATE_CAMPAIGN_SIGNAL, err: " + str(err)
            logger.error(status)


# ContestMeasure
@receiver(post_save, sender=ContestMeasure)
def save_contest_measure_signal(sender, instance, **kwargs):
    # logger.debug("search.save_ContestMeasure_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
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
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to index ContestMeasure " + str(instance.we_vote_id))
        except Exception as err:
            status = "SAVE_CONTEST_MEASURE_SIGNAL, err: " + str(err)
            logger.error(status)


@receiver(post_delete, sender=ContestMeasure)
def delete_contest_measure_signal(sender, instance, **kwargs):
    # logger.debug("search.delete_ContestMeasure_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="measures", doc_type='measure', id=instance.id)
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to delete ContestMeasure " + str(instance.we_vote_id))
        except Exception as err:
            status = "DELETE_CONTEST_MEASURE_SIGNAL, err: " + str(err)
            logger.error(status)


# ContestOffice
@receiver(post_save, sender=ContestOffice)
def save_contest_office_signal(sender, instance, **kwargs):
    # logger.debug("search.save_ContestOffice_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        doc = {
            "we_vote_id": instance.we_vote_id,
            "office_name": instance.office_name,
            "google_civic_election_id": instance.google_civic_election_id,
            "state_code": instance.state_code
        }
        try:
            res = elastic_search_object.index(index="offices", doc_type='office', id=instance.id, body=doc)
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to index ContestOffice " + str(instance.we_vote_id))
        except Exception as err:
            status = "SAVE_CONTEST_OFFICE_SIGNAL, err: " + str(err)
            logger.error(status)


@receiver(post_delete, sender=ContestOffice)
def delete_contest_office_signal(sender, instance, **kwargs):
    # logger.debug("search.delete_ContestOffice_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="offices", doc_type='office', id=instance.id)
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to delete ContestOffice " + str(instance.we_vote_id))
        except Exception as err:
            status = "DELETE_CONTEST_OFFICE_SIGNAL, err: " + str(err)
            logger.error(status)


# Election
@receiver(post_save, sender=Election)
def save_election_signal(sender, instance, **kwargs):
    # logger.debug("search.save_Election_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        ballot_returned_manager = BallotReturnedManager()
        if ballot_returned_manager.should_election_search_data_be_saved(instance.google_civic_election_id):
            doc = {
                "election_name": instance.election_name,
                "election_day_text": instance.election_day_text,
                "google_civic_election_id": instance.google_civic_election_id,
                "state_code": instance.state_code,
                "state_name": convert_state_code_to_state_text(instance.state_code)
            }
            try:
                res = elastic_search_object.index(index="elections", doc_type='election', id=instance.id, body=doc)
                if res["_shards"]["successful"] <= 1:
                    logger.error("failed to index Election " + str(instance.election_name))
            except Exception as err:
                status = "SAVE_ELECTION_SIGNAL, err: " + str(err)
                logger.error(status)
        else:
            try:
                res = elastic_search_object.delete(index="elections", doc_type='election', id=instance.id)
                if res["_shards"]["successful"] <= 1:
                    logger.error("failed to delete1 Election " + str(instance.election_name))
            except Exception as err:
                status = "DELETE_ELECTION_SIGNAL1, err: " + str(err)
                logger.error(status)


@receiver(post_delete, sender=Election)
def delete_election_signal(sender, instance, **kwargs):
    # logger.debug("search.delete_Election_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="elections", doc_type='election', id=instance.id)
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to delete2 Election " + str(instance.election_name))
        except Exception as err:
            status = "DELETE_ELECTION_SIGNAL2, err: " + str(err)
            logger.error(status)


# Organization
@receiver(post_save, sender=Organization)
def save_organization_signal(sender, instance, **kwargs):
    # logger.debug("search.save_Organization_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
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
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to index Organization " + str(instance.we_vote_id))
        except Exception as err:
            status = "SAVE_ORGANIZATION_SIGNAL, err: " + str(err)
            logger.error(status)


@receiver(post_delete, sender=Organization)
def delete_organization_signal(sender, instance, **kwargs):
    # logger.debug("search.delete_Organization_signal")
    if ELASTIC_SEARCH_TURNED_ON and 'elastic_search_object' in globals():
        try:
            res = elastic_search_object.delete(index="organizations", doc_type='organization', id=instance.id)
            if res["_shards"]["successful"] <= 1:
                logger.error("failed to delete Organization " + str(instance.we_vote_id))
        except Exception as err:
            status = "DELETE_ORGANIZATION_SIGNAL, err: " + str(err)
            logger.error(status)


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
