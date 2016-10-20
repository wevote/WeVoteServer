#!/usr/bin/env python

import sys
import psycopg2
from elasticsearch import Elasticsearch
import json
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s: %(message)s')

if len(sys.argv) != 6:
	print("Usage: %s <pgsql-host> <pgsql-username> <pgsql-password> <pgsql-db> <elasticsearch-host>" % sys.argv[0])
	sys.exit(-1)

pgsql_host = sys.argv[1]
pgsql_user = sys.argv[2]
pgsql_pass = sys.argv[3]
pgsql_db = sys.argv[4]
es_host = sys.argv[5]

conn = psycopg2.connect(
	database = pgsql_db,
	user = pgsql_user,
	password = pgsql_pass,
	host = pgsql_host,
	port = "5432"
)

print("Connected to DB")


es = Elasticsearch([es_host + ":9200"], timeout = 20, max_retries = 5, retry_on_timeout = True)

print("Connected to ES")

# 2016-08-27 We no longer index politician data
indexes = ['candidates','offices','organizations']


# create indexes
index_settings = { 'settings': { 'number_of_shards': 3, 'number_of_replicas': 0 } }
for index in indexes:
	logging.info("Dropping index %s", index)
	es.indices.delete(index = index, ignore = [400, 404])
	logging.info("Creating index %s", index)
	es.indices.create(index = index, body = index_settings)

logging.info("Dropping index %s", "measures")
es.indices.delete(index = "measures", ignore = [400, 404])
logging.info("Creating index %s", "measures")
es.indices.create(index = "measures", body = { "aliases": {}, "mappings": { "measure": { "properties": { "google_civic_election_id": { "type": "string" }, "measure_subtitle": { "type": "string", "analyzer": "measure_synonyms" }, "measure_text": { "type": "string", "analyzer": "measure_synonyms" }, "measure_title": { "type": "string", "analyzer": "measure_synonyms" }, "state_code": { "type": "string" }, "we_vote_id": { "type": "string" } } } }, "settings": { "index": { "number_of_shards": "3", "number_of_replicas": "0"}, "analysis": { "filter": { "measure_synonym_filter": { "type": "synonym", "synonyms": [ "proposition,prop" ] } }, "analyzer": { "measure_synonyms": { "tokenizer": "standard", "filter": [ "lowercase", "measure_synonym_filter" ] } } } }, "warmers": {} } )

# index candidate_candidatecampaign table
logging.info("Indexing candidate data")
cur = conn.cursor()
cur.execute("SELECT candidate_name, candidate_twitter_handle, twitter_name, party, google_civic_election_id, state_code, we_vote_id, id  FROM candidate_candidatecampaign")
rows = cur.fetchall()

bulk_data = []
for row in rows:
	bulk_data.append({
		'index' : { "_index" : "candidates", "_type" : "candidate", "_id" : row[7] }
	})
	bulk_data.append({ 
		"candidate_name": row[0],
		"candidate_twitter_handle": row[1],
		"twitter_name": row[2],
		"party": row[3],
		"google_civic_election_id": row[4],
		"state_code": row[5],
		"we_vote_id" : row[6]
	})

logging.info("Bulk indexing candidate data")
bulk_data_json = "\n".join(map(json.dumps,bulk_data))
if bulk_data_json: es.bulk(body = bulk_data_json)
bulk_data = []

# index measure_contestmeasure table
logging.info("Indexing measure data")
cur.execute("SELECT id, we_vote_id, measure_subtitle, measure_text, measure_title, google_civic_election_id, state_code FROM measure_contestmeasure")
rows = cur.fetchall()
for row in rows:
	bulk_data.append({
		'index' : { "_index" : "measures", "_type" : "measure", "_id" : row[0] }
	})
	bulk_data.append({ 
		"we_vote_id": row[1],
		"measure_subtitle": row[2],
		"measure_text": row[3],
		"measure_title": row[4],
		"google_civic_election_id": row[5],
		"state_code": row[6]
	})

logging.info("Bulk indexing measure data")
bulk_data_json = "\n".join(map(json.dumps,bulk_data))
if bulk_data_json: es.bulk(body = bulk_data_json)
bulk_data = []

# index office_contestoffice table
logging.info("Indexing office data")
cur.execute("SELECT id, we_vote_id, office_name, google_civic_election_id, state_code FROM office_contestoffice")
rows = cur.fetchall()
for row in rows:
	bulk_data.append({
		'index' : { "_index" : "offices", "_type" : "office", "_id" : row[0] }
	})
	bulk_data.append({ 
		"we_vote_id": row[1],
		"office_name": row[2],
		"google_civic_election_id": row[3],
		"state_code": row[4]
	})

logging.info("Bulk indexing office data")
bulk_data_json = "\n".join(map(json.dumps,bulk_data))
if bulk_data_json: es.bulk(body = bulk_data_json)
bulk_data = []

# index politician_politician table
#logging.info("Indexing politician data")
#cur.execute("SELECT id, first_name, middle_name, last_name, state_code FROM politician_politician")
#rows = cur.fetchall()
#for row in rows:
#	bulk_data.append({
#		'index' : { "_index" : "politicians", "_type" : "politician", "_id" : row[0] }
#	})
#	bulk_data.append({ 
#		"first_name": row[1],
#		"middle_name": row[2],
#		"last_name": row[3],
#		"state_code": row[4]
#	})
#
#logging.info("Bulk indexing politician data")
#bulk_data_json = "\n".join(map(json.dumps,bulk_data))
#if bulk_data_json: es.bulk(body = bulk_data_json)
#bulk_data = []


# index organization_organization table
logging.info("Indexing organization data")
cur.execute("SELECT id, we_vote_id, organization_name, organization_twitter_handle, organization_website, twitter_description, state_served_code FROM organization_organization")
rows = cur.fetchall()
for row in rows:
	bulk_data.append({
		'index' : { "_index" : "organizations", "_type" : "organization", "_id" : row[0] }
	})
	bulk_data.append({ 
		"we_vote_id": row[1],
		"organization_name": row[2],
		"organization_twitter_handle": row[3],
		"organization_website": row[4],
		"twitter_description": row[5],
		"state_served_code": row[6]
	})

logging.info("Bulk indexing organization data")
bulk_data_json = "\n".join(map(json.dumps,bulk_data))
if bulk_data_json: es.bulk(body = bulk_data_json)
bulk_data = []
