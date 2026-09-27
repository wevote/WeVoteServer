# apis_v1/views/views_extension.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import datetime
import json
import os
from urllib.parse import quote

import boto3
import cloudscraper
import requests
from django.http import HttpResponse

import wevote_functions.admin
from config.environment_variable_functions import get_environment_variable, get_environment_variable_default
from exception.models import handle_exception
from wevote_functions.functions import positive_value_exists

AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
AWS_STORAGE_BUCKET_NAME = "wevote-temporary"
TIKA_SERVER_ENDPOINT = get_environment_variable("TIKA_SERVER_ENDPOINT")

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def pdf_to_html_retrieve_view(request):  # pdfToHtmlRetrieve
    """
    return a URL to a s3 file that contains the html rough equivalent of the PDF
    :param request:
    :return:
    """
    # voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    pdf_url = request.GET.get('pdf_url', '')
    return_version = request.GET.get('version', False)
    json_data = {}

    if not positive_value_exists(pdf_url) and not return_version:
        status = 'PDF_URL_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            's3_url_for_html':          '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    try:
        json_data = process_pdf_to_html(pdf_url, return_version)
    except Exception as e:
        logger.error('call to process_pdf_to_html from pdf_to_html_retrieve_view (Outermost Exception): ' + str(e))

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def build_absolute_path_for_tempfile(tempfile):
    temp_path = get_environment_variable_default("PATH_FOR_TEMP_FILES", "/tmp")
    # logger.error('build_absolute_path_for_tempfile temp_path 1:' + temp_path)

    # March 2023: the value of PATH_FOR_TEMP_FILES on the production servers is '/tmp'-
    if temp_path[-1] != '/':
        temp_path += '/'
    # logger.error('build_absolute_path_for_tempfile temp_path 2:' + temp_path)
    absolute = temp_path + tempfile
    # logger.error('build_absolute_path_for_tempfile absolute: ' + absolute)
    return absolute


# PDF to HTML conversion is done by an Apache Tika server, reached at TIKA_SERVER_ENDPOINT.
# https://cwiki.apache.org/confluence/display/TIKA/TikaServer
# Test cases:
# https://cadem.org/wp-content/uploads/2022/09/2022-CADEM-General-Endorsements.pdf
# https://www.iuoe399.org/media/filer_public/45/77/457700c9-dd70-4cfc-be49-a81cb3fba0a6/2020_lu399_primary_endorsement.pdf
# http://www.local150.org/wp-content/uploads/2018/02/Cook-18-Primary-Web.pdf
# http://www.sddemocrats.org/sites/sdcdp/files/pdf/Endorsements_Flyer_P2020b.pdf
# https://crpa.org/wp-content/uploads/2020-CA-Primary-Candidate-Final.pdf
# https://webcache.googleusercontent.com/search?q=cache:https://cadem.org/wp-content/uploads/2022/09/2022-CADEM-General-Endorsements.pdf

def process_pdf_to_html(pdf_url, return_version):
    output_from_subprocess = 'exception occurred before output was captured'
    status = ''
    success = False
    logger.error('entry to process_pdf_to_html:' + pdf_url + '   ' + str(return_version))

    # Version report, only used to debug connectivity to the Tika server
    if return_version:
        try:
            version_url = TIKA_SERVER_ENDPOINT.rsplit('/tika', 1)[0] + '/version'
            response = requests.get(version_url, timeout=10)
            output_from_subprocess = response.text
            success = response.status_code == 200

        except Exception as e:
            logger.error('Tika version exception: ' + str(e))

        json_data = {
            'status': 'TIKA_SERVER_VERSION',
            'success': success,
            'output_from_subprocess': output_from_subprocess,
            's3_url_for_html': '',
        }
        return json_data

    logger.error('immediately after return_version: ' + str(return_version))
    pdf_file_name = os.path.basename(pdf_url)
    absolute_html_file = build_absolute_path_for_tempfile(pdf_file_name).replace('.pdf', '.html')
    try:
        os.remove(absolute_html_file)    # remove the exact same html file if it already exists on disk
    except Exception:
        pass

    # logger.error('after removing temp files: ' + str(pdf_file_name))

    # use cloudscraper to get past challenges presented by pages hosted at Cloudflare
    scraper = cloudscraper.create_scraper()  # returns a CloudScraper instance
    s3_url_for_html = False
    is_pdf = True
    pdf_text_text = ''
    try:
        raw = scraper.get(pdf_url)
        pdf_text_text = raw.content  # in bytes, not using str(raw.content)
        logger.error('cloudscraper attempt with base PDF url : ' + pdf_url +
                     ' returned bytes: ' + str(len(pdf_text_text)))
        success = True

    # Probably got a http 403 forbidden, due to cloudscraper unsuccessfully handling a Cloudflare challenge
    # Now try to use Google's (hopefully) cached version of the page
    except Exception as scraper_or_tempfile_error:
        status = "First pass with base url failed with a " + str(scraper_or_tempfile_error)
        logger.error('cloudscraper with base PDF url or tempfile write exception: ' +
                      str(scraper_or_tempfile_error))

    if not success:
        logger.error('first pass === not success')
        is_pdf = False
        try:
            logger.error('first pass === not success, pdf_url:  ' + pdf_url)
            encoded = quote(pdf_url, safe='')
            logger.error('encoded success: ' + encoded)
            google_cached_pdf_url = 'https://webcache.googleusercontent.com/search?q=cache:' + encoded
            logger.error('cloudscraper attempt with google cached PDF url: ' + google_cached_pdf_url)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/36.0.1941.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                'Accept-Encoding': 'none',
                'Accept-Language': 'en-US,en;q=0.8',
                'Connection': 'keep-alive'}
            r = requests.get(google_cached_pdf_url, headers)
            logger.error('after requests.get: ' + google_cached_pdf_url)
            # skip saving the pdf file (since we don't have one), and write the final html file to the temp dir
            html_text_text = r.text
            out_file = open(absolute_html_file, 'w')
            out_file.write(html_text_text)

            logger.error('requests was successful with google cached PDF url : ' + google_cached_pdf_url +
                         ' returned bytes: ' + str(len(pdf_text_text)))
            success = True
        except Exception as scraper_or_tempfile_error2:      # Out of luck
            status += ", Second pass with google cached PDF url failed with a: " + str(scraper_or_tempfile_error2)
            logger.error('FATAL requests with google cached PDF url or tempfile write exception: ' +
                         str(scraper_or_tempfile_error2))

    if pdf_text_text and len(pdf_text_text) > 10 and is_pdf:
        try:
            # Send the PDF bytes to the Tika server and ask it to return HTML
            tika_response = requests.put(
                TIKA_SERVER_ENDPOINT,
                data=pdf_text_text,
                headers={'Accept': 'text/html', 'Content-Type': 'application/pdf'},
                timeout=60,
            )
            output_from_subprocess = 'Tika status: ' + str(tika_response.status_code)
            with open(absolute_html_file, 'w') as out_file:
                out_file.write(tika_response.text)
            logger.error('Tika PUT output: ' + output_from_subprocess)
        except Exception as tika_error:
            status += ', ' + str(tika_error)
            logger.error('Tika PUT request exception: ' + str(tika_error))

        try:
            insert_pdf_filename_in_tmp_file(absolute_html_file, pdf_url)
        except Exception as insert_pdf_error:
            status += ', ' + str(insert_pdf_error)
            logger.error('insert_pdf_filename_in_tmp_file exception: ' + str(insert_pdf_error))

    # create temporary file in s3, so it can be served to the We Vote Chrome Extension
    s3_url_for_html = store_temporary_html_file_to_aws(absolute_html_file) or 'NO_TEMPFILE_STORED_IN_S3'
    if not s3_url_for_html.startswith("http"):
        status += ', ' + s3_url_for_html
    # logger.error("stored temp html file: " + absolute_html_file + ', ' + s3_url_for_html)

    if positive_value_exists(s3_url_for_html):
        status = 'PDF_URL_RETURNED successfully with s3_url_for_html, other status = ' + status
    else:
        status = 'PDF_URL_RETURNED un-successfully without a returned S3 URL, other status = ' + status
    json_data = {
        'status': status,
        'success': success,
        'output_from_subprocess': output_from_subprocess,
        's3_url_for_html': s3_url_for_html,
    }
    return json_data


def store_temporary_html_file_to_aws(temp_file_name):
    """
    Upload temporary_html_file directly to AWS
    :param temp_file_name:
    :return:
    """
    s3_html_url = ""
    try:
        head, tail = os.path.split(temp_file_name)
        date_in_a_year = datetime.datetime.now() + + datetime.timedelta(days=365)
        session = boto3.session.Session(region_name=AWS_REGION_NAME)
        s3 = session.resource("s3")
        logger.info('store_temporary_html_file_to_aws upload temp_file: ' + temp_file_name)
        s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_file(
            temp_file_name, tail, ExtraArgs={'Expires': date_in_a_year, 'ContentType': 'text/html'})
        s3_html_url = "https://{bucket_name}.s3.amazonaws.com/{file_location}" \
                      "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                file_location=tail)
    except Exception as e:
        print(e)
        logger.error('store_temporary_html_file_to_aws exception: ' + str(e))

        exception_message = "store_temp_html_file_to_aws failed"
        handle_exception(e, logger=logger, exception_message=exception_message)

    return s3_html_url


def insert_pdf_filename_in_tmp_file(temp_file, pdf_url):
    with open(temp_file, "r") as f:
        contents = f.read()

    value = "<input type=\"hidden\" name=\"pdfFileName\" value=\"{pdf_url}\" />".format(pdf_url=pdf_url)

    # insert the hidden input immediately after the opening <body> tag -- containing the original URL for the PDF
    body_open_index = contents.index("<body")
    insertion_point = contents.index(">", body_open_index) + 1
    contents = contents[:insertion_point] + value + contents[insertion_point:]

    with open(temp_file, "w") as f:
        f.write(contents)
