# import_export_maplight/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import MapLightContestOfficeManager, MapLightCandidateManager, MapLightContestOffice, \
    MapLightCandidate, validate_maplight_date
from exception.models import handle_record_not_saved_exception
import json
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)

MAPLIGHT_SAMPLE_BALLOT_JSON_FILE = "import_export_maplight/import_data/maplight_sf_ballot_sample.json"
MAPLIGHT_SAMPLE_CONTEST_JSON_FILE = "import_export_maplight/import_data/contest_{contest_id}.json"


def import_maplight_from_json(request):
    load_from_url = False
    ballot_for_one_voter_array = []
    if load_from_url:
        # Request json file from Maplight servers
        logger.debug("TO BE IMPLEMENTED: Load Maplight JSON from url")
        # request = requests. get(VOTER_INFO_URL, params={
        #     "key": GOOGLE_CIVIC_API_KEY,  # This comes from an environment variable
        #     "address": "254 Hartford Street San Francisco CA",
        #     "electionId": "2000",
        # })
        # structured_json = json.loads(request.text)
    else:
        # Load saved json from local file
        logger.debug("Loading Maplight sample JSON from local file")

        with open(MAPLIGHT_SAMPLE_BALLOT_JSON_FILE) as ballot_for_one_voter_json:
            ballot_for_one_voter_array = json.load(ballot_for_one_voter_json)

    # A MapLight ballot query is essentially an array of contests with the key as the contest_id
    if ballot_for_one_voter_array and len(ballot_for_one_voter_array):
        # Parse the JSON here. This JSON is a list of contests on the ballot for one voter.
        for contest_id in ballot_for_one_voter_array:
            # Get a description of the contest. Office? Measure?
            contest_overview_array = ballot_for_one_voter_array[contest_id]

            if contest_overview_array['type'] == "office":
                # Get a description of the office the candidates are competing for
                # contest_office_description_json = contest_overview_array['office']

                # With the contest_id, we can look up who is running
                politicians_running_for_one_contest_array = []
                if load_from_url:
                    logger.debug("TO BE IMPLEMENTED: Load MapLight JSON for a contest from URL")
                else:
                    json_file_with_the_data_from_this_contest = MAPLIGHT_SAMPLE_CONTEST_JSON_FILE.format(
                        contest_id=contest_id)
                    try:
                        with open(json_file_with_the_data_from_this_contest) as json_data:
                            politicians_running_for_one_contest_array = json.load(json_data)
                    except Exception as e:
                        logger.error("File {file_path} not found.".format(
                            file_path=json_file_with_the_data_from_this_contest))
                        # Don't try to process the file if it doesn't exist, but go to the next entry
                        continue

                import_maplight_contest_office_candidates_from_array(politicians_running_for_one_contest_array)

            # Also add measure
    return


def import_maplight_contest_office_candidates_from_array(politicians_running_for_one_contest_array):
    maplight_contest_office_saved = False  # Has the contest these politicians are running for been saved?
    maplight_contest_office_manager = MapLightContestOfficeManager()
    maplight_candidate_manager = MapLightCandidateManager()

    loop_count = 0
    loop_count_limit = 1

    for politician_id in politicians_running_for_one_contest_array:
        one_politician_array = politicians_running_for_one_contest_array[politician_id]

        # Save the office_contest so we can link the politicians to it first

        if not maplight_contest_office_saved:
            maplight_contest_office = MapLightContestOffice()
            if 'contest' in one_politician_array:
                maplight_contest_array = one_politician_array['contest']
                if 'office' in maplight_contest_array:
                    maplight_contest_office_array = maplight_contest_array['office']
                if 'id' in maplight_contest_array:
                    maplight_contest_id = maplight_contest_array['id']
                    maplight_contest_office = \
                        maplight_contest_office_manager.fetch_maplight_contest_office_from_id_maplight(
                            maplight_contest_id)

            # If an internal identifier is found, then we know we have an object
            if maplight_contest_office.id:
                maplight_contest_office_saved = True
                # try:
                #     maplight_contest_office.contest_id = maplight_contest_array['id']
                #     maplight_contest_office.election_date = maplight_contest_array['election_date']
                #     maplight_contest_office.title = maplight_contest_array['title']
                #     maplight_contest_office.type = maplight_contest_array['type']
                #     maplight_contest_office.url = maplight_contest_array['url']
                #     # Save into this db the 'office'?
                #     # Save into this db the 'jurisdiction'?
                #     maplight_contest_office.save()
                #     maplight_contest_office_saved = True
                #
                # except Exception as e:
                #     handle_record_not_saved_exception(e)
            else:
                try:
                    maplight_contest_office = MapLightContestOffice(
                        contest_id=maplight_contest_array['id'],
                        election_date=maplight_contest_array['election_date'],
                        title=maplight_contest_array['title'],
                        type=maplight_contest_array['type'],
                        url=maplight_contest_array['url'],
                    )
                    # Save into this db the 'office'?
                    # Save into this db the 'jurisdiction'?
                    maplight_contest_office.save()
                    maplight_contest_office_saved = True

                except Exception as e:
                    handle_record_not_saved_exception(e, logger=logger)

        maplight_candidate = maplight_candidate_manager.fetch_maplight_candidate_from_candidate_id_maplight(
            one_politician_array['candidate_id'])

        if maplight_candidate.id:
            logger.warning(u"Candidate {display_name} previously saved".format(
                display_name=maplight_candidate.display_name
            ))
        else:
            # Not found in the MapLightCandidate database, so we need to save
            try:
                maplight_candidate = MapLightCandidate()
                maplight_candidate.politician_id = one_politician_array['politician_id']
                maplight_candidate.candidate_id = one_politician_array['candidate_id']
                maplight_candidate.display_name = one_politician_array['display_name']
                maplight_candidate.original_name = one_politician_array['original_name']
                maplight_candidate.gender = one_politician_array['gender']
                maplight_candidate.first_name = one_politician_array['first_name']
                maplight_candidate.middle_name = one_politician_array['middle_name']
                maplight_candidate.last_name = one_politician_array['last_name']
                maplight_candidate.name_prefix = one_politician_array['name_prefix']
                maplight_candidate.name_suffix = one_politician_array['name_suffix']
                maplight_candidate.bio = one_politician_array['bio']
                maplight_candidate.party = one_politician_array['party']
                maplight_candidate.candidate_flags = one_politician_array['candidate_flags']
                if validate_maplight_date(one_politician_array['last_funding_update']):
                    maplight_candidate.last_funding_update = one_politician_array['last_funding_update']
                maplight_candidate.roster_name = one_politician_array['roster_name']
                maplight_candidate.photo = one_politician_array['photo']
                maplight_candidate.url = one_politician_array['url']

                maplight_candidate.save()
                logger.info(u"Candidate {display_name} added".format(
                    display_name=maplight_candidate.display_name
                ))

            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)

        # TODO: Now link the candidate to the contest
