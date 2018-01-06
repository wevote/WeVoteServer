#!/usr/bin/env python
# Test this by entering the search string "election" on a command line like this:
# /home/wevote/WeVoteServer/search/query_test_script.py election

from elasticsearch import Elasticsearch
import sys

es = Elasticsearch(["172.31.24.246:9200"], timeout = 120, max_retries = 5, retry_on_timeout = True)

if len(sys.argv) < 2:
        print "Usage: %s <search term>" % (sys.argv[0])
        sys.exit(-1)

search_term = sys.argv[1]
#query = { "query": {"match": { "candidate_name": "Joe"}}}
#query = { "query": {"match": { "candidate_name": "Joe"}}}
#query = { "query": { "multi_match": { "type": "phrase_prefix", "query": search_term, "fields": [ "candidate_name", "candidate_twitter_handle", "twitter_name", "measure_subtitle", "measure_text", "measure_title", "office_name", "first_name", "middle_name", "last_name", "party", "organization_name", "organization_twitter_handle", "twitter_description" ] } }}
query = { "query": { "multi_match": { "type": "phrase_prefix", "query": search_term, "fields": [ "google_civic_election_id", "candidate_name", "candidate_twitter_handle", "election_name", "twitter_name", "measure_subtitle", "measure_text", "measure_title", "office_name", "party", "organization_name", "organization_twitter_handle", "twitter_description" ] } }}
query_with_missing_last_election_date = { "query": { "multi_match": { "type": "phrase_prefix",
                                                    "query": search_term,
                                                    "fields": [ "election_name^3", "google_civic_election_id",
                                                                "candidate_name",
                                                                "candidate_twitter_handle", "election_name",
                                                                "twitter_name", "measure_subtitle", "measure_text",
                                                                "measure_title", "office_name", "party",
                                                                "organization_name", "organization_twitter_handle",
                                                                "twitter_description", "state_name"],
                                                    "slop": 5}},
                                          "sort": [{"election_day_text": {"missing": "1111-11-11"}},
                                                   {"_score": {"order": "desc"}}]}

query_with_missing_election_date_without_order = { "query": { "multi_match": { "type": "phrase_prefix",
                                                                               "query": search_term,
                                                                               "fields": [ "election_name^3", "google_civic_election_id",
                                                                                        "candidate_name",
                                                                                        "candidate_twitter_handle", "election_name",
                                                                                        "twitter_name", "measure_subtitle", "measure_text",
                                                                                        "measure_title", "office_name", "party",
                                                                                        "organization_name", "organization_twitter_handle",
                                                                                        "twitter_description", "state_name"],
                                                                               "slop": 5}},
                                                   "sort": [{"election_day_text": {"missing": "1111-11-11"}},
                                                            {"_score": {"order": "desc"}}]}
query_with_election_missing_date_value = { "query": { "multi_match": { "type": "phrase_prefix",
                                                                       "query": search_term,
                                                                       "fields": [ "election_name^3", "google_civic_election_id",
                                                                                "candidate_name",
                                                                                "candidate_twitter_handle", "election_name",
                                                                                "twitter_name", "measure_subtitle", "measure_text",
                                                                                "measure_title", "office_name", "party",
                                                                                "organization_name", "organization_twitter_handle",
                                                                                "twitter_description", "state_name"],
                                                                       "slop": 5}},
                                           "sort": [{"election_day_text": {"missing": "1111-11-11", "order": "desc"}},
                                                    {"_score": {"order": "desc"}}]}

# Example of querying ALL indexes
res = es.search(body=query)
res_with_missing_last_election_date = es.search(body=query_with_missing_last_election_date)
# res_with_missing_election_date_without_order = es.search(body=query_with_missing_election_date_without_order)
# res_with_election_missing_date_value = es.search(body=query_with_election_missing_date_value)

print "Got %d hits from all index search: " % res['hits']['total']
print "Got %d hits from all index search: " % res_with_missing_last_election_date['hits']['total']
# print "Got %d hits from all index search: " % res_with_missing_election_date_without_order['hits']['total']
# print "Got %d hits from all index search: " % res_with_election_missing_date_value['hits']['total']
for hit in res['hits']['hits']:
        print "------------- RESULT --------------"
        for field in hit:
                print "%s: %s" % (field, hit[field])
print "============================================"
print "============================================"
for hit in res_with_missing_last_election_date['hits']['hits']:
        print "------------- RESULT --------------"
        for field in hit:
                print "%s: %s" % (field, hit[field])
print "============================================"
# print "============================================"
# for hit in res_with_missing_election_date_without_order['hits']['hits']:
#         print "------------- RESULT --------------"
#         for field in hit:
#                 print "%s: %s" % (field, hit[field])
# print "============================================"
# print "============================================"
# for hit in res_with_election_missing_date_value['hits']['hits']:
#         print "------------- RESULT --------------"
#         for field in hit:
#                 print "%s: %s" % (field, hit[field])


# example of querying single index
if (True):
        res = es.search(index="elections", body={ "query": {"match": { "google_civic_election_id": "5000"}}})
        print "Got %d hits from single index search: " % res['hits']['total']

        for hit in res['hits']['hits']:
                for field in hit:
                        print "%s: %s" % (field, hit[field])

