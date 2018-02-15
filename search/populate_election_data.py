#!/usr/bin/env python

import sys
import psycopg2
from elasticsearch import Elasticsearch
import json
import logging

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


def convert_state_code_to_state_text(incoming_state_code):
    for state_code, state_name in STATE_CODE_MAP.items():
        if incoming_state_code.lower() == state_code.lower():
            return state_name
    else:
        return ""


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
indexes = ['election']


# create indexes
index_settings = { 'settings': { 'number_of_shards': 3, 'number_of_replicas': 0 } }
for index in indexes:
	logging.info("Dropping index %s", index)
	es.indices.delete(index = index, ignore = [400, 404])
	logging.info("Creating index %s", index)
	es.indices.create(index = index, body = index_settings)

# index election_election table
logging.info("Indexing election data")
cur = conn.cursor()
# cur.execute("SELECT election_name, election_day_text, election_election.google_civic_election_id, state_code, id FROM election_election INNER JOIN ﻿ballot_ballotreturned ON election_election.google_civic_election_id =﻿ballot_ballotreturned.google_civic_election_id WHERE ballot_ballotreturned.ballot_location_display_option_on = true")
cur.execute("SELECT election_name, election_day_text, google_civic_election_id, state_code, id FROM election_election")
rows = cur.fetchall()

bulk_data = []
for row in rows:
	bulk_data.append({
		'index' : { "_index" : "elections", "_type" : "election", "_id" : row[4] }
	})
	bulk_data.append({ 
		"election_name": row[0],
		"election_day_text": row[1],
		"google_civic_election_id": row[2],
		"state_code": row[3],
		"state_name": convert_state_code_to_state_text(row[3])
	})

logging.info("Bulk indexing election data")
bulk_data_json = "\n".join(map(json.dumps,bulk_data))
if bulk_data_json: es.bulk(body = bulk_data_json)
bulk_data = []
