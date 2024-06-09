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
from wevote_functions.utils import scrape_url

# logger = wevote_functions.admin.get_logger(__name__)

GOOGLE_PROJECT_ID = 'we-vote-ballot'
VERTEX_SERVICE_ENDPOINT = 'us-west1'


def ask_google_vertex_a_question(question, text_to_search):
    response_text = None
    response_text_found = False
    status = ''
    success = True
    t0 = time()
    try:
        credentials = service_account.Credentials.from_service_account_file(
                get_environment_variable("GOOGLE_APPLICATION_CREDENTIALS_VERTEX"))
        # os.environ["SERVICE_ACCOUNT_ID"] = 'vertexai-name-of-people@we-vote-ballot.iam.gserviceaccount.com'
        vertexai.init(
            credentials=credentials,
            project=GOOGLE_PROJECT_ID,
            location=VERTEX_SERVICE_ENDPOINT)
        t1 = time()
        # print('---- vertexai.init took {:.6f} seconds'.format(t1-t0))

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
        # print('---- TextGenerationModel took {:.6f} seconds'.format(t2-t1))
        #
        # print(f'---- Question ==> \'{question}\' <==')
        # text_to_search = "One name is George Washington and another name is Thomas Jefferson."
        # WITH PARAMETERS
        # response = model.predict(
        #     "{question} {text_to_search}"
        #     "".format(
        #         question=question,
        #         text_to_search=text_to_search),
        #     **parameters)
        # WITHOUT PARAMETERS
        response = model.predict(
            "{question} {text_to_search}"
            "".format(
                question=question,
                text_to_search=text_to_search))
        response_text = response.text
        if positive_value_exists(response_text):
            response_text_found = True
        t3 = time()
        # print('---- model.predict took {:.6f} seconds'.format(t3-t2))
        # print('---- total took {:.6f} seconds'.format(t3-t0))
        # print(f'---- Question query from Vertex Model: {response_text}')
        #
        # #  Feel free to remove logging and print lines in this file
        # performance = "(Ok) ask_google_vertex_a_question Vertex init took {:.6f} seconds, ".format(t1-t0)
        # performance += "load model (text-bison) took {:.6f} seconds, ".format(t2-t1)
        # performance += "Question query took {:.6f} seconds, ".format(t3-t2)
        # performance += "total took {:.6f} seconds ".format(t3-t0)
        # print(performance)
        # status += performance
    except Exception as error_message:
        print(f"Error response from Vertex Model: {error_message}")
        status += "VERTEX_ERROR: {error_message} ".format(error_message=error_message)

    results = {
        'status':               status,
        'success':              success,
        'response_text':        response_text,
        'response_text_found':  response_text_found,
    }
    return results


def find_names_of_people_from_incoming_text(text_to_scan=''):
    names_list = []
    names_list_found = False
    success = True
    status = ""
    if len(text_to_scan) < 3:
        status += 'FIND_NAMES_ON_ONE_PAGE-PROPER_TEXT_NOT_PROVIDED '
        success = False
        results = {
            'status':           status,
            'success':          success,
            'names_list':       names_list,
            'names_list_found': names_list_found,
        }
        return results

    text_to_scan_cleaned = ""
    text_to_scan_found = False
    t0 = time()
    try:
        text_to_scan_cleaned = text_to_scan
        if len(text_to_scan_cleaned) > 0:
            text_to_scan_found = True

        status += "FINISHED_CLEANING_INCOMING_TEXT "
    except timeout:
        status += "FIND_NAMES_IN_TEXT_CLEANING_TIMEOUT_ERROR "
        success = False
    except IOError as error_instance:
        # Catch the error message coming back from urllib.request.urlopen and pass it in the status
        error_message = error_instance
        status += "FIND_NAMES_IN_TEXT_IO_ERROR: {error_message}".format(error_message=error_message)
        success = False
    except Exception as error_instance:
        error_message = error_instance
        status += "FIND_NAMES_IN_TEXT_GENERAL_EXCEPTION_ERROR: {error_message}".format(error_message=error_message)
        success = False
    t1 = time()

    if text_to_scan_found:
        question = "Return all names of people in this following text: "
        results = ask_google_vertex_a_question(question, text_to_search=text_to_scan_cleaned)
        if results['response_text_found']:
            response_text = results['response_text']
            if positive_value_exists(response_text):
                import re
                cleaned = response_text.replace('\n- ', '\n')
                names_list = list(re.split('; |, |\*|\r\n|\r|\n', cleaned))
                names_list.pop(0)     # remove 'The following names are mentioned in the text:'
        status += results['status']

    names_list_found = positive_value_exists(len(names_list))
    results = {
        'status':           status,
        'success':          success,
        'names_list':       names_list,
        'names_list_found': names_list_found,
    }
    return results


def find_names_of_people_on_one_web_page(site_url=''):
    names_list = []
    names_list_found = False
    status = ""
    success = True
    print('---- find_names_of_people_on_one_web_page for ', site_url)
    t0 = time()
    if len(site_url) < 10:
        status += 'FIND_NAMES_ON_ONE_PAGE-PROPER_URL_NOT_PROVIDED: ' + site_url
        success = False
        results = {
            'status':           status,
            'success':          success,
            'names_list':       names_list,
            'names_list_found': names_list_found,
        }
        return results

    try:
        scrape_res = scrape_url(site_url)
        try:
            status += scrape_res.status
        except Exception as e:
            status += "ERROR: scrape_res doesn't have status attribute: " + str(e) + " "
            success = False
        try:
            all_text_without_head = scrape_res.all_html
        except Exception as e:
            all_text_without_head = ""
            status += "ERROR: scrape_res doesn't have all_html attribute: " + str(e) + " "
            success = False

        if success:
            status += "FINISHED_SCRAPING_PAGE "

            print('---- find_names_of_people_on_one_web_page scrape took {:.6f} seconds'.format(time()-t0))
            sub_results = find_names_of_people_from_incoming_text(all_text_without_head)
            if 'status' in sub_results:
                status += sub_results['status']
            if 'success' in sub_results:
                success &= sub_results['success']
            names_list = sub_results['names_list']
            names_list_found = sub_results['names_list_found']

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
    t1 = time()

    results = {
        'status':           status,
        'success':          success,
        'names_list':       names_list,
        'names_list_found': names_list_found,
    }
    return results

