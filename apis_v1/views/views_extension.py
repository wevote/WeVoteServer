# apis_v1/views/views_extension.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import boto3
import datetime
import json
import os
import urllib.request
from django.http import HttpResponse
import wevote_functions.admin
from config.base import get_environment_variable
from wevote_functions.functions import positive_value_exists, get_voter_device_id
from exception.models import handle_exception
from pdfminer_six import pdf2txt

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
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    pdf_url = request.GET.get('pdf_url', '')

    if not positive_value_exists(pdf_url):
        status = 'PDF_URL_MISSING'
        json_data = {
            'status': status,
            'success': False,
            's3_url_for_html': '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    file_name, headers = urllib.request.urlretrieve(pdf_url)
    temp_file_name = file_name + '.html'

    pdf2txt.main(['-o', temp_file_name, file_name])

    insert_pdf_filename_in_tmp_file(temp_file_name, pdf_url)

    s3_url_for_html = store_temporary_html_file_to_aws(temp_file_name)
    print("views_extension stored temp html file: ", temp_file_name, s3_url_for_html)

    status = 'PDF_URL_RETURNED'
    json_data = {
        'status': status,
        'success': True,
        # 'output_from_subprocess': output,
        's3_url_for_html': s3_url_for_html,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def store_temporary_html_file_to_aws(temp_file_name):
    """
    Upload temporary_html_file directly to AWS
    :param temp_file_name:
    :return:
    """
    s3_html_url = ""
    try:
        head, tail = os.path.split(temp_file_name)
        date_in_a_week = datetime.datetime.now() + + datetime.timedelta(days=7)
        session = boto3.session.Session(region_name=AWS_REGION_NAME,
                                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        s3 = session.resource(AWS_STORAGE_SERVICE)
        s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_file(
            temp_file_name, tail, ExtraArgs={'Expires': date_in_a_week, 'ContentType': 'text/html'})
        s3_html_url = "https://{bucket_name}.s3.amazonaws.com/{file_location}" \
                      "".format(bucket_name=AWS_STORAGE_BUCKET_NAME,
                                file_location=tail)
    except Exception as e:
        print(e)
        exception_message = "store_temp_html_file_to_aws failed"
        handle_exception(e, logger=logger, exception_message=exception_message)

    return s3_html_url


def insert_pdf_filename_in_tmp_file(temp_file, pdf_url):
    f = open(temp_file, "r")
    contents = f.readlines()
    f.close()

    value = "<input type=\"hidden\" name=\"pdfFileName\" value=\"{pdf_url}\" />\n".format(pdf_url=pdf_url)

    # insert the hidden input as the first line of the body -- containgingthe original URL for the PDF
    offset = contents.index("</head><body>\n") + 1
    contents.insert(offset, value)

    f = open(temp_file, "w")
    contents = "".join(contents)
    f.write(contents)
    f.close()
