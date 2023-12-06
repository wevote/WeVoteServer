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


class FakeFirefoxURLopener(urllib.request.FancyURLopener):
    version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0)' \
            + ' Gecko/20100101 Firefox/25.0'


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
        print('---- vertexai.init took {:.6f} seconds'.format(t1-t0))

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
        print('---- TextGenerationModel took {:.6f} seconds'.format(t2-t1))

        print(f'---- Question ==> \'{question}\' <==')
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
        print('---- model.predict took {:.6f} seconds'.format(t3-t2))
        print('---- total took {:.6f} seconds'.format(t3-t0))
        print(f'---- Question query from Vertex Model: {response_text}')

        #  Feel free to remove logging and print lines in this file
        performance = "(Ok) ask_google_vertex_a_question Vertex init took {:.6f} seconds, ".format(t1-t0)
        performance += "load model (text-bison) took {:.6f} seconds, ".format(t2-t1)
        performance += "Question query took {:.6f} seconds, ".format(t3-t2)
        performance += "total took {:.6f} seconds ".format(t3-t0)
        print(performance)
        status += performance
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
                names_list = list(re.split('; |, |\*|\r\n|\r|\n', response_text))
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
    success = False
    print('---- find_names_of_people_on_one_web_page for ', site_url)
    t0 = time()
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
    all_text_without_html = ""
    all_html_found = False
    names_list = []
    names_list_found = False
    t0 = time()
    all_text_without_head = None
    try:
        request = urllib.request.Request(site_url, None, headers)
        page = urllib.request.urlopen(request, timeout=5)
        all_html_raw = page.read()
        all_html = all_html_raw.decode("utf8")
        all_html_found = True
        page.close()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(all_html, "html.parser")
        soup.find('head').decompose()  # find head tag and decompose/destroy it from the html
        all_text_without_head = soup.get_text()

        # import re
        # clean = re.compile('<.*?>')
        # all_text_without_html = re.sub(clean, '', all_html)

        success = True
        status += "FINISHED_SCRAPING_PAGE "

        print('---- find_names_of_people_on_one_web_page scrape took {:.6f} seconds'.format(time()-t0))
        sub_results = find_names_of_people_from_incoming_text(all_text_without_head)
        status += sub_results['status']
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


# def find_names_steve1(site_url):
#     names_list = []
#     names_list_found = False
#     status = ""
#     success = False
#     if len(site_url) < 10:
#         status += 'FIND_NAMES_ON_ONE_PAGE-PROPER_URL_NOT_PROVIDED: ' + site_url
#         results = {
#             'status':           status,
#             'success':          success,
#             'names_list':       names_list,
#             'names_list_found': names_list_found,
#         }
#         return results
#
#     t0 = time()
#     print('Entry: find_names_of_people_on_one_web_page -- ', site_url)
#     try:
#         credentials = service_account.Credentials.from_service_account_file(
#                 get_environment_variable("GOOGLE_APPLICATION_CREDENTIALS_VERTEX"))
#         # os.environ["SERVICE_ACCOUNT_ID"] = 'vertexai-name-of-people@we-vote-ballot.iam.gserviceaccount.com'
#         vertexai.init(
#             credentials=credentials,
#             project=GOOGLE_PROJECT_ID,
#             location=VERTEX_SERVICE_ENDPOINT)
#         t1 = time()
#         temperature = 0.2
#         parameters = {
#             "temperature": temperature,  # Temperature controls the degree of randomness in token selection.
#             "max_output_tokens": 5,  # Token limit determines the maximum amount of text output.
#             "top_p": 0,  # Tokens are selected from most probable to least
#             # until the sum of their probabilities equals the top_p value.
#             "top_k": 1,  # A top_k of 1 means the selected token is the most probable among all tokens.
#         }
#         model = TextGenerationModel.from_pretrained("text-bison")
#         t2 = time()
#
#         print('---- 1 ----')  # This works 11/30/23
#         response = model.predict("What is life?")
#         print(f"Response #1 from Model: {response.text}")
#         t3 = time()
#
#         print('---- 2 ----')  # This works 11/30/23
#         response = model.predict("Who is Lashrecse Aird?")
#         print(f"Response #2 from Model: {response.text}")
#         t4 = time()
#
#         print('---- 3 ----')  # This kind of works 11/30/23, it returns a list of names
#         response = model.predict("Return all names of people shown on this website: " + site_url)
#         print(f"Response #3 from Model: {response.text}")
#         t5 = time()
#
#         print('---- 4 ----')  # Does work
#         response = model.predict(
#             "Return all names of people in this following text: "
#             "One name is George Washington and another name is Thomas Jefferson.",
#             **parameters,
#         )
#         print(f"Response #4 from Model: {response.text}")
#         t6 = time()
#
#         print('---- 5 ----')  # Does not work
#         response = model.predict("""Background text:
#             One name is George Washington and another name is Thomas Jefferson.
#             Q: Return a python list of names?""",
#             **parameters)
#         print(f'Response #5 from Vertex Model: {response.text}')
#         t7 = time()
#
#         #  Feel free to remove logging and print lines in this file
#         print(
#             '(Ok) find_names_of_people_on_one_web_page init took {:.6f} seconds, '.format(t1-t0) +
#             'load model (text-bison) took {:.6f} seconds, '.format(t2-t1) +
#             'predict 1 took {:.6f} seconds, '.format(t3-t2) +
#             'predict 2 took {:.6f} seconds, '.format(t4-t3) +
#             'predict 3 took {:.6f} seconds, '.format(t5-t4) +
#             'predict 4 took {:.6f} seconds, '.format(t6-t5) +
#             'predict 5 took {:.6f} seconds, '.format(t7-t6) +
#             'total took {:.6f} seconds'.format(t7-t0))
#
#     except Exception as error_message:
#         print(f"Error response from Vertex Model: {error_message}")
#         status += "VERTEX_ERROR: {error_message}".format(error_message=error_message)
#
#     names_list_found = positive_value_exists(len(names_list))
#     results = {
#         'status':           status,
#         'success':          success,
#         'names_list':       names_list,
#         'names_list_found': names_list_found,
#     }
#     return results


# def find_names_dale1(site_url):
#     names_list = []
#     names_list_found = False
#     status = ""
#     success = False
#     if len(site_url) < 10:
#         status += 'FIND_NAMES_ON_ONE_PAGE-PROPER_URL_NOT_PROVIDED: ' + site_url
#         results = {
#             'status':           status,
#             'success':          success,
#             'names_list':       names_list,
#             'names_list_found': names_list_found,
#         }
#         return results
#
#     t0 = time()
#     print('Entry: find_names_of_people_on_one_web_page -- ', site_url)
#     try:
#         credentials = service_account.Credentials.from_service_account_file(
#                 get_environment_variable("GOOGLE_APPLICATION_CREDENTIALS_VERTEX"))
#         # os.environ["SERVICE_ACCOUNT_ID"] = 'vertexai-name-of-people@we-vote-ballot.iam.gserviceaccount.com'
#         vertexai.init(
#             credentials=credentials,
#             project=GOOGLE_PROJECT_ID,
#             location=VERTEX_SERVICE_ENDPOINT)
#         t1 = time()
#         temperature = 0.2
#         parameters = {
#             "temperature": temperature,  # Temperature controls the degree of randomness in token selection.
#             "max_output_tokens": 5,  # Token limit determines the maximum amount of text output.
#             "top_p": 0,  # Tokens are selected from most probable to least
#             # until the sum of their probabilities equals the top_p value.
#             "top_k": 1,  # A top_k of 1 means the selected token is the most probable among all tokens.
#         }
#         model = TextGenerationModel.from_pretrained("text-bison")
#         t2 = time()
#
#         # print('---- 1 ----')  # This works 11/30/23
#         # response = model.predict("What is life?")
#         # print(f"Response #1 from Model: {response.text}")
#         # t3 = time()
#         #
#         # print('---- 2 ----')  # This works 11/30/23
#         # response = model.predict("Who is Lashrecse Aird?")
#         # print(f"Response #2 from Model: {response.text}")
#         # t4 = time()
#
#         # print('---- 3 ----')  # This kind of works 11/30/23, it returns a list of names
#         # response = model.predict("What are the names on " + site_url)
#         # print(f"Response #3 from Model: {response.text}")
#         # t5 = time()
#
#         # print('---- 4 ----')  # Does not work
#         # response = model.predict(
#         #     "Return a python list of names from 'One name is George Washington and another name is Thomas Jefferson.'",
#         #     **parameters,
#         # )
#         # print(f"Response #4 from Model: {response.text}")
#         # t6 = time()
#         #
#         print('---- 5 ----')  # Works with or without parameters, with the following question
#         question = "Return all names of people in this following text:"
#         text_to_search = "One name is George Washington and another name is Thomas Jefferson."
#         response = model.predict(
#             "{question} {text_to_search}"
#             "".format(
#                 question=question,
#                 text_to_search=text_to_search),
#             **parameters)
#         # response = model.predict(
#         #     "Return all names of people in this following text: {text_to_search}"
#         #     "".format(text_to_search=text_to_search))
#         print(f'Response #5 from Vertex Model to \'{question}\': {response.text}')
#         t7 = time()
#
#         #  Feel free to remove logging and print lines in this file
#         print(
#             '(Ok) find_names_of_people_on_one_web_page_dale1 init took {:.6f} seconds, '.format(t1-t0) +
#             'load model (text-bison) took {:.6f} seconds, '.format(t2-t1) +
#             'predict 5 took {:.6f} seconds, '.format(t7-t2) +
#             'total took {:.6f} seconds'.format(t7 - t0))
#         # 'predict 1 took {:.6f} seconds, '.format(t3-t2) +
#         # 'predict 2 took {:.6f} seconds, '.format(t4-t3) +
#         # 'predict 3 took {:.6f} seconds, '.format(t5-t4) +
#         # 'predict 4 took {:.6f} seconds, '.format(t6-t5) +
#         # 'predict 5 took {:.6f} seconds, '.format(t7-t6) +
#         # 'total took {:.6f} seconds'.format(t7-t0))
#
#     except Exception as error_message:
#         print(f"Error response from Vertex Model: {error_message}")
#         status += "VERTEX_ERROR: {error_message}".format(error_message=error_message)
#
#     names_list_found = positive_value_exists(len(names_list))
#     results = {
#         'status':           status,
#         'success':          success,
#         'names_list':       names_list,
#         'names_list_found': names_list_found,
#     }
#     return results
