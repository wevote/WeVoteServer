# apis_v1/views/views_extension.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import datetime
import json
import os
import re
from urllib.parse import quote

import boto3
import cloudscraper
import requests
from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable, get_environment_variable_default
from exception.models import handle_exception
from wevote_functions.functions import positive_value_exists

AWS_ACCESS_KEY_ID = get_environment_variable("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = get_environment_variable("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
AWS_STORAGE_BUCKET_NAME = "wevote-temporary"
AWS_STORAGE_SERVICE = "s3"

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
        logger.error('pdf2htmlEX call to process_pdf_to_html from pdf_to_html_retrieve_view (Outermost Exception): ' +
                     str(e))

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def build_output_string(process):
    std_output_raw = process.stdout
    std_output = '\'' + std_output_raw.decode("utf-8") + '\'' if std_output_raw else '\'\''
    err_output_raw = process.stderr
    err_output = '\'' + err_output_raw.decode("utf-8") + '\'' if err_output_raw else '\'\''
    output_from_subprocess = \
        ('stdout: ' + std_output + ', stderr: ' + err_output).replace('\n', '')
    return output_from_subprocess


def build_absolute_path_for_tempfile(tempfile):
    temp_path = get_environment_variable_default("PATH_FOR_TEMP_FILES", "/tmp")
    # logger.error('pdf2htmlEX build_absolute_path_for_tempfile temp_path 1:' + temp_path)

    # March 2023: the value of PATH_FOR_TEMP_FILES on the production servers is '/tmp'-
    if temp_path[-1] != '/':
        temp_path += '/'
    # logger.error('pdf2htmlEX build_absolute_path_for_tempfile temp_path 2:' + temp_path)
    absolute = temp_path + tempfile
    # logger.error('pdf2htmlEX build_absolute_path_for_tempfile absolute: ' + absolute)
    return absolute


# https://github.com/pdf2htmlEX/pdf2htmlEX  !We use a fork of the abandoned coolwanglu original repo.
# https://github.com/pdf2htmlEX/pdf2htmlEX/wiki/Command-Line-Options
# In December 2020, we installed a docker image in AWS/EC2: https://hub.docker.com/r/cardboardci/pdf2htmlex
# pdf2htmlEX -zoom 1.3 Cook-18-Primary-Web.pdf
# March 2023:
# docker run -ti --rm --mount src="$(pwd)",target=/pdf,type=bind pdf2htmlex/pdf2htmlex:0.18.8.rc2-master-20200820-
# ubuntu-20.04-x86_64 --zoom 1.3 .//2022-CADEM-General-Endorsements.pdf
# Test cases:
# https://cadem.org/wp-content/uploads/2022/09/2022-CADEM-General-Endorsements.pdf
# https://www.iuoe399.org/media/filer_public/45/77/457700c9-dd70-4cfc-be49-a81cb3fba0a6/2020_lu399_primary_endorsement.pdf
# http://www.local150.org/wp-content/uploads/2018/02/Cook-18-Primary-Web.pdf
# http://www.sddemocrats.org/sites/sdcdp/files/pdf/Endorsements_Flyer_P2020b.pdf
# https://crpa.org/wp-content/uploads/2020-CA-Primary-Candidate-Final.pdf
# https://webcache.googleusercontent.com/search?q=cache:https://cadem.org/wp-content/uploads/2022/09/2022-CADEM-General-Endorsements.pdf

# You can test Apache Tika on your Mac by downloading the latest version of
#      https://www.apache.org/dyn/closer.lua/tika/2.9.2/tika-server-standard-2.9.2.jar
# Then running
#          java -jar tika-server-standard-2.9.2.jar
# Which starts a Tika server on http://localhost:9998/

def process_pdf_to_html(pdf_url, return_version=False):
    output_from_subprocess = 'exception occurred before output was captured'
    status = ''
    success = False
    # logger.error('process_pdf_to_html entry to process_pdf_to_html:' + pdf_url + '   ' + str(return_version))
    # Version report, only used to debug the pdf2htmlEX installation in our AWS/EC2 instances
    # if return_version:
    #     try:
    #         command = 'pdf2htmlEX -v'
    #         # logger.error('pdf2htmlEX command: ' + command)
    #
    #         process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    #         output_from_subprocess = build_output_string(process)
    #
    #         # logger.error('pdf2htmlEX version ' + output_from_subprocess)
    #         success = True
    #
    #     except Exception as e:
    #         logger.error('pdf2htmlEX version exception: ' + str(e))
    #
    #     json_data = {
    #         'status': 'PDF2HTMLEX_VERSION',
    #         'success': success,
    #         'output_from_subprocess': output_from_subprocess,
    #         's3_url_for_html': '',
    #     }
    #     return json_data

    # logger.error('process_pdf_to_html immediately after return_version: ' + str(return_version))
    html_file_name = os.path.basename(pdf_url).replace('.pdf', '.html')
    absolute_html_file = build_absolute_path_for_tempfile(html_file_name)
    try:
        os.remove(absolute_html_file)    # remove the exact same html file if it already exists on disk
    except Exception:
        pass

    # logger.error('process_pdf_to_html after removing temp files: ' + str(pdf_file_name))

    # use cloudscraper to get past challenges presented by pages hosted at Cloudflare
    scraper = cloudscraper.create_scraper()  # returns a CloudScraper instance
    is_pdf = True
    pdf_text_text = ''
    try:
        raw = scraper.get(pdf_url)
        pdf_text_text = raw.content  # in bytes, not using str(raw.content)
        # logger.error('process_pdf_to_html cloudscraper attempt with base PDF url : ' + pdf_url +
        #              ' returned bytes: ' + str(len(pdf_text_text)))
        success = True

    # Probably got a http 403 forbidden, due to cloudscraper unsuccessfully handling a Cloudflare challenge
    # Now try to use Google's (hopefully) cached version of the page
    except Exception as scraper_or_tempfile_error:
        status = "First pass with base url failed with a " + str(scraper_or_tempfile_error)
        # logger.error('process_pdf_to_html cloudscraper with base PDF url or tempfile write exception: ' +
        #              str(scraper_or_tempfile_error))

    if not success:
        logger.error('process_pdf_to_html first pass === not success')
        is_pdf = False
        try:
            # logger.error('process_pdf_to_html first pass === not success, pdf_url:  ' + pdf_url)
            encoded = quote(pdf_url, safe='')
            # logger.error('process_pdf_to_html encoded success: ' + encoded)
            google_cached_pdf_url = 'https://webcache.googleusercontent.com/search?q=cache:' + encoded
            # logger.error('process_pdf_to_html cloudscraper attempt with google cached PDF url: ' + google_cached_pdf_url)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/36.0.1941.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                'Accept-Encoding': 'none',
                'Accept-Language': 'en-US,en;q=0.8',
                'Connection': 'keep-alive'}
            r = requests.get(google_cached_pdf_url, headers)
            # logger.error('process_pdf_to_html after requests.get: ' + google_cached_pdf_url)
            # skip saving the pdf file (since we don't have one), and write the final html file to the temp dir
            html_text_text = r.text
            out_file = open(absolute_html_file, 'w')
            out_file.write(html_text_text)

            # logger.error('process_pdf_to_html requests was successful with google cached PDF url : ' +
            #      google_cached_pdf_url + ' returned bytes: ' + str(len(pdf_text_text)))
            success = True
        except Exception as scraper_or_tempfile_error2:      # Out of luck
            status += ", Second pass with google cached PDF url failed with a: " + str(scraper_or_tempfile_error2)
            logger.error('process_pdf_to_html FATAL requests with google cached PDF url or tempfile write exception: ' +
                         str(scraper_or_tempfile_error2))

    if pdf_text_text and len(pdf_text_text) > 10 and is_pdf:
        try:
            # Run Tika from docker image to convert pdf to html
            import tika
            tika.initVM()
            from tika import parser
            server_endpoint = get_environment_variable_default("TIKA_SERVER_ENDPOINT", 'http://tika:9998/tika')
            if len(server_endpoint) == 0:
                server_endpoint = 'http://tika:9998/tika'
            parsed_result = parser.from_buffer(pdf_text_text, server_endpoint, xmlContent=True)
            output_html = parsed_content_to_full_html(parsed_result['content'], pdf_url)
            out_file = open(absolute_html_file, 'w')
            out_file.write(output_html)
            out_file.close()
        except Exception as tika_error:
            status += ', ' + str(tika_error)
            logger.error('process_pdf_to_html subprocess.run exception: ' + str(tika_error))

    # create temporary file in s3, so it can be served to the We Vote Chrome Extension
    s3_url_for_html = store_temporary_html_file_to_aws(absolute_html_file) or 'NO_TEMPFILE_STORED_IN_S3'
    if not s3_url_for_html.startswith("http"):
        status += ', ' + s3_url_for_html
    # logger.error("process_pdf_to_html stored temp html file: " + absolute_html_file + ', ' + s3_url_for_html)

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
        session = boto3.session.Session(region_name=AWS_REGION_NAME,
                                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        s3 = session.resource(AWS_STORAGE_SERVICE)
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


def parsed_content_to_full_html(content, pdf_url):
    content = content.replace('<title></title>', '<title>' + pdf_url + '</title>')
    inp = "<input type=\"hidden\" name=\"pdfFileName\" value=\"{pdf_url}\" />\n".format(pdf_url=pdf_url)
    content = content.replace('<body>', '<body>\n' + inp)
    content = re.sub(r'(?<!>)\n', '<br>\n', content)
    return content
