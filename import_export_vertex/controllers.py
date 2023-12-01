# import_export_vertex/controllers.py
# Brought to you by We Vote. Be good.
import urllib.request
from socket import timeout
from time import time

import vertexai
from google.oauth2 import service_account
from vertexai.language_models import TextGenerationModel

from config.base import get_environment_variable
from wevote_functions.functions import positive_value_exists

# logger = wevote_functions.admin.get_logger(__name__)

GOOGLE_PROJECT_ID = 'we-vote-ballot'
VERTEX_SERVICE_ENDPOINT = 'us-west1'


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

    t0 = time()
    print('Entry: find_names_of_people_on_one_web_page -- ', site_url)
    try:
        credentials = service_account.Credentials.from_service_account_file(
                get_environment_variable("GOOGLE_APPLICATION_CREDENTIALS_VERTEX"))
        # os.environ["SERVICE_ACCOUNT_ID"] = 'vertexai-name-of-people@we-vote-ballot.iam.gserviceaccount.com'
        vertexai.init(
            credentials=credentials,
            project=GOOGLE_PROJECT_ID,
            location=VERTEX_SERVICE_ENDPOINT)
        t1 = time()
        temperature = 0.2
        parameters = {
            "temperature": temperature,  # Temperature controls the degree of randomness in token selection.
            "max_output_tokens": 5,  # Token limit determines the maximum amount of text output.
            "top_p": 0,  # Tokens are selected from most probable to least
            # until the sum of their probabilities equals the top_p value.
            "top_k": 1,  # A top_k of 1 means the selected token is the most probable among all tokens.
        }
        model = TextGenerationModel.from_pretrained("text-bison")
        t2 = time()

        print('---- 1 ----')  # This works 11/30/23
        response = model.predict("What is life?")
        print(f"Response #1 from Model: {response.text}")
        t3 = time()

        print('---- 2 ----')  # This works 11/30/23
        response = model.predict("Who is Lashrecse Aird?")
        print(f"Response #2 from Model: {response.text}")
        t4 = time()

        print('---- 3 ----')  # This kind of works 11/30/23, it returns a list of names
        response = model.predict("What are the names on " + site_url)
        print(f"Response #3 from Model: {response.text}")
        t5 = time()

        print('---- 4 ----')  # Does not work
        response = model.predict(
            "Return a python list of names from 'One name is George Washington and another name is Thomas Jefferson.'",
            **parameters,
        )
        print(f"Response #4 from Model: {response.text}")
        t6 = time()

        print('---- 5 ----')  # Does not work
        response = model.predict("""Background text: 
            One name is George Washington and another name is Thomas Jefferson.
            Q: Return a python list of names?""",
            **parameters)
        print(f'Response #5 from Vertex Model: {response.text}')
        t7 = time()

        #  Feel free to remove logging and print lines in this file
        print(
            '(Ok) find_names_of_people_on_one_web_page init took {:.6f} seconds, '.format(t1-t0) +
            'load model (text-bison) took {:.6f} seconds, '.format(t2-t1) +
            'predict 1 took {:.6f} seconds, '.format(t3-t2) +
            'predict 2 took {:.6f} seconds, '.format(t4-t3) +
            'predict 3 took {:.6f} seconds, '.format(t5-t4) +
            'predict 4 took {:.6f} seconds, '.format(t6-t5) +
            'predict 5 took {:.6f} seconds, '.format(t7-t6) +
            'total took {:.6f} seconds'.format(t7-t0))

    except Exception as error_message:
        print(f"Error response from Vertex Model: {error_message}")
        status += "VERTEX_ERROR: {error_message}".format(error_message=error_message)

    names_list_found = positive_value_exists(len(names_list))
    results = {
        'status':           status,
        'success':          success,
        'names_list':       names_list,
        'names_list_found': names_list_found,
    }
    return results


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'

def older_find_names_of_people_on_one_web_page(site_url):
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
                credential_path= get_environment_variable('GOOGLE_APPLICATION_CREDENTIALS_VERTEX'),
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
