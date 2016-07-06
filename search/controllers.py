# search/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from elasticsearch import Elasticsearch
from voter.models import fetch_voter_id_from_voter_device_link
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)
ELASTIC_SEARCH_CONNECTION_STRING = get_environment_variable("ELASTIC_SEARCH_CONNECTION_STRING")


def search_all_for_api(text_from_search_field, voter_device_id):
    """

    :param text_from_search_field:
    :param voter_device_id:
    :return:
    """
    if not positive_value_exists(text_from_search_field):
        results = {
            'status':                   'TEXT_FROM_SEARCH_FIELD_MISSING',
            'success':                  True,
            'text_from_search_field':   text_from_search_field,
            'voter_device_id':          voter_device_id,
            'search_results_found':     False,
            'search_results':           [],
        }
        return results

    if not positive_value_exists(ELASTIC_SEARCH_CONNECTION_STRING):
        results = {
            'status':                   'MISSING_ELASTIC_SEARCH_CONNECTION_STRING',
            'success':                  False,
            'text_from_search_field':   text_from_search_field,
            'voter_device_id':          voter_device_id,
            'search_results_found':     False,
            'search_results':           [],
        }
        return results

    # Get voter_id from the voter_device_id so we can know who is doing the starring
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results = {
            'status':                   'VALID_VOTER_DEVICE_ID_MISSING',
            'success':                  False,
            'text_from_search_field':   text_from_search_field,
            'voter_device_id':          voter_device_id,
            'search_results_found':     False,
            'search_results':           [],
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        results = {
            'status':                   "VALID_VOTER_ID_MISSING",
            'success':                  False,
            'text_from_search_field':   text_from_search_field,
            'voter_device_id':          voter_device_id,
            'search_results_found':     False,
            'search_results':           [],
        }
        return results

    elastic_search_object = Elasticsearch([ELASTIC_SEARCH_CONNECTION_STRING],
                                          timeout=2, max_retries=1, retry_on_timeout=True)

    # query = {"query": {"match": {"candidate_name": text_from_search_field}}}
    query = {"query": {"multi_match": {"type": "phrase_prefix",
                                       "query": text_from_search_field,
                                       "fields": ["candidate_name",
                                                  "candidate_twitter_handle", "twitter_name",
                                                  "measure_subtitle", "measure_text", "measure_title",
                                                  "office_name", "first_name", "middle_name", "last_name",
                                                  "party", "organization_name", "organization_twitter_handle",
                                                  "twitter_description"]}}}

    # Example of querying ALL indexes
    search_results = []
    search_count = 0
    try:
        res = elastic_search_object.search(body=query)
        # See bottom of this file for example results from Elastic Search

        for hit in res['hits']['hits']:
            one_search_result_type = hit['_type']
            one_search_result_id = hit['_id']
            one_search_result_dict = hit['_source']
            one_search_result_score = hit['_score']
            if one_search_result_type == "office":
                link_internal = "/office/" + one_search_result_dict['we_vote_id']

                one_search_result = {
                    'result_title':             one_search_result_dict['office_name'],
                    'result_image':             "",
                    'result_subtitle':          "",
                    'result_summary':           "",
                    'result_score':             one_search_result_score,
                    'link_internal':            link_internal,
                    'kind_of_owner':            "OFFICE",
                    'google_civic_election_id': one_search_result_dict['google_civic_election_id'],
                    'state_code':               one_search_result_dict['state_code'],
                    'twitter_handle':           "",
                    'we_vote_id':               one_search_result_dict['we_vote_id'],
                    'local_id':                 one_search_result_id,
                }
                search_results.append(one_search_result)
                search_count += 1
            elif one_search_result_type == "candidate":
                if positive_value_exists(one_search_result_dict['candidate_twitter_handle']):
                    link_internal = "/" + one_search_result_dict['candidate_twitter_handle']
                else:
                    link_internal = "/candidate/" + one_search_result_dict['we_vote_id']

                one_search_result = {
                    'result_title':             one_search_result_dict['candidate_name'],
                    'result_image':             "",
                    'result_subtitle':          "",
                    'result_summary':           "",
                    'result_score':             one_search_result_score,
                    'link_internal':            link_internal,
                    'kind_of_owner':            "CANDIDATE",
                    'google_civic_election_id': one_search_result_dict['google_civic_election_id'],
                    'state_code':               one_search_result_dict['state_code'],
                    'twitter_handle':           one_search_result_dict['candidate_twitter_handle'],
                    'we_vote_id':               one_search_result_dict['we_vote_id'],
                    'local_id':                 one_search_result_id,
                }
                search_results.append(one_search_result)
                search_count += 1
            elif one_search_result_type == "measure":
                if positive_value_exists(one_search_result_dict['measure_twitter_handle']):
                    link_internal = "/" + one_search_result_dict['measure_twitter_handle']
                else:
                    link_internal = "/measure/" + one_search_result_dict['we_vote_id']

                one_search_result = {
                    'result_title':             one_search_result_dict['measure_title'],
                    'result_image':             "",
                    'result_subtitle':          one_search_result_dict['measure_subtitle'],
                    'result_summary':           one_search_result_dict['measure_text'],
                    'result_score':             one_search_result_score,
                    'link_internal':            link_internal,
                    'kind_of_owner':            "MEASURE",
                    'google_civic_election_id': one_search_result_dict['google_civic_election_id'],
                    'state_code':               one_search_result_dict['state_code'],
                    'twitter_handle':           one_search_result_dict['measure_twitter_handle'],
                    'we_vote_id':               one_search_result_dict['we_vote_id'],
                    'local_id':                 one_search_result_id,
                }
                search_results.append(one_search_result)
                search_count += 1
            elif one_search_result_type == "organization":
                if 'organization_twitter_handle' in one_search_result_dict and \
                        positive_value_exists(one_search_result_dict['organization_twitter_handle']):
                    link_internal = "/" + one_search_result_dict['organization_twitter_handle']
                else:
                    link_internal = "/voterguide/" + one_search_result_dict['we_vote_id']

                one_search_result = {
                    'result_title':             one_search_result_dict['organization_name'],
                    'result_image':             "",
                    'result_subtitle':          "",
                    'result_summary':           one_search_result_dict['twitter_description'],
                    'result_score':             one_search_result_score,
                    'link_internal':            link_internal,
                    'kind_of_owner':            "ORGANIZATION",
                    'google_civic_election_id': 0,
                    'state_code':               one_search_result_dict['state_served_code'],
                    'twitter_handle':           one_search_result_dict['organization_twitter_handle'],
                    'we_vote_id':               one_search_result_dict['we_vote_id'],
                    'local_id':                 one_search_result_id,
                }
                search_results.append(one_search_result)
                search_count += 1
            elif one_search_result_type == "politician":
                # If we are here, then we should skip out. We can't display politicians w/o twitter_handle yet
                break
                # if positive_value_exists(one_search_result_dict['politician_twitter_handle']):
                #     link_internal = "/" + one_search_result_dict['politician_twitter_handle']
                # else:
                #     link_internal = "/candidate/" + one_search_result_dict['we_vote_id']
                #
                # one_search_result = {
                #     'result_title': one_search_result_dict['name'],
                #     'result_image':             "",
                #     'result_subtitle':          "",
                #     'result_summary':           "",
                #     'result_score':             one_search_result_score,
                #     'link_internal':            link_internal,
                #     'kind_of_owner':            "POLITICIAN",
                #     'google_civic_election_id': 0,
                #     'state_code':               one_search_result_dict['state_served_code'],
                #     'twitter_handle':           one_search_result_dict['politician_twitter_handle,'],
                #     'we_vote_id':               one_search_result_dict['we_vote_id'],
                #     'local_id':                 one_search_result_id,
                # }
                # search_results.append(one_search_result)
                # search_count += 1
        status = "SEARCH_ALL_COMPLETE"
        success = True

    except Exception as e:
        status = 'ELASTIC_SEARCH_EXCEPTION'
        success = False

    results = {
        'status':                   status,
        'success':                  success,
        'text_from_search_field':   text_from_search_field,
        'voter_device_id':          voter_device_id,
        'search_results_found':     True if search_count > 0 else False,
        'search_results':           search_results,
    }
    return results

# ------------- RESULT --------------
# _score: 1.3017262
# _type: candidate
# _id: 692
# _source: {u'we_vote_id': u'wv01cand2446', u'candidate_name': u'Richard A. Gwaltney',
#           u'google_civic_election_id': u'4162', u'twitter_name': None, u'party': u'Independent',
#           u'state_code': u'va', u'candidate_twitter_handle': None}
# _index: candidates
# ------------- RESULT --------------
# _score: 1.3648399
# _type: measure
# _id: 95
# _source: {u'we_vote_id': u'wv02meas95', u'measure_title': u'Proposed Constitutional Amendment A',
#           u'google_civic_election_id': u'2000', u'measure_subtitle': u'To prohibit an increase in the state '
#                                                                      u'income tax rate in effect January 1, 2015 '
#                                                                      u'(Senate Resolution 415).',
#           u'measure_text': u'', u'state_code': u'ga'}
# _index: measures
# ------------- RESULT --------------
# _score: 2.0133548
# _type: office
# _id: 765
# _source: {u'office_name': u'SCHOOL BOARD - CONSOLIDATED DISTRICT A', u'we_vote_id': u'wv02off322',
#           u'google_civic_election_id': u'4188', u'state_code': u'nc'}
# _index: offices
# ------------- RESULT --------------
# _score: 1.7513412
# _type: organization
# _id: 1298
# _source: {u'we_vote_id': u'wv02org1282', u'state_served_code': u'NA',
#           u'organization_website,': u'http://www.networklobby.org',
#           u'organization_twitter_handle,': u'NETWORKLobby',
#           u'organization_name': u'NETWORK, A National Catholic Social Justice Lobby',
#           u'twitter_description,': u'A #Catholic leader in the global movement for justice & peace. '
#                                    u'Organizers of #nunsonthebus. RTs not endorsements.'}
# _index: organizations
