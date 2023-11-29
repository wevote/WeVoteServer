# import_export_vertex/controllers.py
# Brought to you by We Vote. Be good.

import urllib.request
from socket import timeout

import vertexai
from google.oauth2 import service_account
from vertexai.language_models import TextGenerationModel

from config.base import get_environment_variable
from wevote_functions.functions import positive_value_exists

GEOCODE_TIMEOUT = 10
GOOGLE_CIVIC_API_KEY = get_environment_variable("GOOGLE_CIVIC_API_KEY")
GOOGLE_MAPS_API_KEY = get_environment_variable("GOOGLE_MAPS_API_KEY")
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
            credentials = service_account.Credentials.from_service_account_file(
                get_environment_variable("GOOGLE_APPLICATION_CREDENTIALS_VERTEX"))
            # all_html_lower_case = all_html.lower()

            # os.environ["SERVICE_ACCOUNT_ID"] = 'vertexai-name-of-people@we-vote-ballot.iam.gserviceaccount.com'
            vertexai.init(
                credentials=credentials,
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
            print('Before TextGenerationModel.from_pretrained (times out in 120 secs if unsuccessful)')
            model = TextGenerationModel.from_pretrained("text-bison")
            print('TextGenerationModel.from_pretrained returned a model')
            response = model.predict("""Background text: 
One name is George Washington and another name is Thomas Jefferson.
Q: Return a python list of names?""",
                **parameters,
            )
            print(f"Response from Vertex Model: {response.text}")
        except Exception as error_message:
            print(f"Error response from Vertex Model: {error_message}")
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
