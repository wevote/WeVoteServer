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

# Example of querying ALL indexes
res = es.search(body=query)

print "Got %d hits from all index search: " % res['hits']['total']

for hit in res['hits']['hits']:
        print "------------- RESULT --------------"
        for field in hit:
                print "%s: %s" % (field, hit[field])


# example of querying single index
if (True):
        res = es.search(index="elections", body={ "query": {"match": { "google_civic_election_id": "5000"}}})
        print "Got %d hits from single index search: " % res['hits']['total']

        for hit in res['hits']['hits']:
                for field in hit:
                        print "%s: %s" % (field, hit[field])

