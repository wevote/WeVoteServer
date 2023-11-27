# import_export_vertex/controllers.py
# Brought to you by We Vote. Be good.

from config.base import get_environment_variable
from django.utils.timezone import localtime, now
from geopy.geocoders import get_geocoder_for_service
import json
import os
import requests
from socket import timeout
import urllib.request
import vertexai
from vertexai.language_models import TextGenerationModel
from wevote_functions.functions import convert_district_scope_to_ballotpedia_race_office_level, \
    convert_level_to_race_office_level, convert_state_text_to_state_code, convert_to_int, \
    extract_district_id_label_when_district_id_exists_from_ocd_id, extract_district_id_from_ocd_division_id, \
    extract_facebook_username_from_text_string, extract_instagram_handle_from_text_string, \
    extract_state_code_from_address_string, extract_state_from_ocd_division_id, \
    extract_twitter_handle_from_text_string, extract_vote_usa_measure_id, extract_vote_usa_office_id, \
    is_voter_device_id_valid, logger, positive_value_exists, STATE_CODE_MAP

GEOCODE_TIMEOUT = 10
GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
GOOGLE_APPLICATION_CREDENTIALS_VERTEX = get_environment_variable("GOOGLE_APPLICATION_CREDENTIALS_VERTEX")
GOOGLE_PROJECT_ID = 'we-vote-ballot'
VERTEX_SERVICE_ENDPOINT = 'us-west1'


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


def find_names_of_people_on_one_web_page(site_url):
    names_list = []
    names_list_found = False
    status = ""
    success = False
    if len(site_url) < 10:
        status += 'FIND_NAMES_ON_ONE_PAGE-PROPER_URL_NOT_PROVIDED: ' + site_url
        results = {
            'status':           status,
            'success':          success,
            'names_list':       names_list,
            'names_list_found': names_list_found,
        }
        return results

    urllib._urlopener = FakeFirefoxURLopener()
    headers = {
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           }
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Encoding': 'none',
    # 'Accept-Language': 'en-US,en;q=0.8',
    # 'Connection': 'keep-alive'
    # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        all_html_raw = page.read()
        all_html = all_html_raw.decode("utf8")
        page.close()
        try:
            # all_html_lower_case = all_html.lower()

            # This is expecting a file instead of an API key
            # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS_VERTEX
            # os.environ["SERVICE_ACCOUNT_ID"] = 'vertexai-name-of-people@we-vote-ballot.iam.gserviceaccount.com'
            vertexai.init(
                credential_path=GOOGLE_APPLICATION_CREDENTIALS_VERTEX,
                project=GOOGLE_PROJECT_ID,
                location=VERTEX_SERVICE_ENDPOINT)
            temperature = 0.2
            parameters = {
                "temperature": temperature,  # Temperature controls the degree of randomness in token selection.
                "max_output_tokens": 5,  # Token limit determines the maximum amount of text output.
                "top_p": 0,  # Tokens are selected from most probable to least
                             # until the sum of their probabilities equals the top_p value.
                "top_k": 1,  # A top_k of 1 means the selected token is the most probable among all tokens.
            }
            model = TextGenerationModel.from_pretrained("text-bison@001")
            response = model.predict("""Background text: 
One name is George Washington and another name is Thomas Jefferson.
Q: Return a python list of names?""",
                **parameters,
            )
            print(f"Response from Vertex Model: {response.text}")
        except Exception as error_message:
            status += "VERTEX_ERROR: {error_message}".format(error_message=error_message)

        success = True
        status += "FINISHED_SCRAPING_PAGE "
    except timeout:
        status += "FIND_NAMES_ON_PAGE-WEB_PAGE_SCRAPE_TIMEOUT_ERROR "
        success = False
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status += "FIND_NAMES_ON_PAGE_SOCIAL_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status += "FIND_NAMES_ON_PAGE_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False

    names_list_found = positive_value_exists(len(names_list))
    results = {
        'status':           status,
        'success':          success,
        'names_list':       names_list,
        'names_list_found': names_list_found,
    }
    return results
