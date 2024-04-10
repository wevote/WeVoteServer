# image/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from exception.models import handle_exception
from io import BytesIO
from PIL import Image, ImageOps
from urllib.request import Request, urlopen
import urllib
import requests
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def analyze_remote_url(image_url_https):
    """
    Validate url and get image properties
    :param image_url_https:
    :return:
    """
    image_format = None
    image_height = None
    image_width = None
    image_url_valid = False
    try:
        if image_url_https is not None:
            # urlopen(Request(image_url_https))
            remote_url_req = urllib.request.Request(
                image_url_https,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/36.0.1941.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                    'Accept-Encoding': 'none',
                    'Accept-Language': 'en-US,en;q=0.8',
                    'Connection': 'keep-alive'})
            remote_url = urlopen(remote_url_req)
            image_url_valid = True
    except Exception as e:
        image_url_valid = False
        exception_message = "analyze_remote_url: image url {image_url_https} is not valid."\
            .format(image_url_https=image_url_https)
        handle_exception(e, logger=logger, exception_message=exception_message)

    if image_url_valid:
        try:
            response = requests.get(image_url_https)
            original_image = Image.open(BytesIO(response.content))
            image_format = original_image.format
            image = ImageOps.exif_transpose(original_image)
            image_width, image_height = image.size
        except Exception as e:
            image_url_valid = False

    results = {
        'image_url_valid':              image_url_valid,
        'image_width':                  image_width,
        'image_height':                 image_height,
        'image_format':                 image_format.lower() if image_format is not None else image_format
    }
    return results


def analyze_image_file(image_file):
    """
    Analyse inMemoryUploadedFile object to get image properties
    :param image_file:
    :return:
    """
    image_format = None
    image_height = None
    image_width = None
    image_url_valid = False
    if image_file is not None:
        image_url_valid = True
        original_image = Image.open(image_file.file)
        image_format = original_image.format
        image = ImageOps.exif_transpose(original_image)
        # When PIL opens image file, pointer will go to end of file so seeking it to 0 to access again
        image_file.seek(0)
        image_width, image_height = image.size

    results = {
        'image_url_valid':              image_url_valid,
        'image_width':                  image_width,
        'image_height':                 image_height,
        'image_format':                 image_format.lower() if image_format is not None else image_format
    }
    return results


def analyze_image_in_memory(image_in_memory):
    """
    Analyse inMemoryUploadedFile object to get image properties
    :param image_in_memory:
    :return:
    """
    image_format = None
    image_height = None
    image_width = None
    image_url_valid = False
    if image_in_memory is not None:
        image_url_valid = True
        image_width, image_height = image_in_memory.size
        image_format = image_in_memory.format

    results = {
        'image_url_valid':              image_url_valid,
        'image_width':                  image_width,
        'image_height':                 image_height,
        'image_format':                 image_format.lower() if image_format is not None else image_format
    }
    return results


def change_default_profile_image_if_needed(
        object_with_photo_fields=None,
        new_profile_image_key=''):
    at_least_one_change = False
    new_profile_image_key_large = ''
    new_profile_image_key_medium = ''
    new_profile_image_key_tiny = ''
    save_changes = False
    status = ''
    success = True

    if not hasattr(object_with_photo_fields, 'we_vote_hosted_profile_image_url_large'):
        status += "NOT_VALID_OBJECT_WITH_PHOTO_FIELDS "
        success = False
    try:
        new_profile_image_key_large = new_profile_image_key + "_large"
        if not hasattr(object_with_photo_fields, new_profile_image_key_large):
            status += "MISSING_NEW_PROFILE_IMAGE_URL_LARGE_ATTRIBUTE "
            success = False
        new_profile_image_key_medium = new_profile_image_key + "_medium"
        new_profile_image_key_tiny = new_profile_image_key + "_tiny"
    except Exception as e:
        status += "NEW_PROFILE_IMAGE_KEY_PROBLEM: " + str(e) + " "
        success = False
    if success:
        new_profile_image_value_large = getattr(object_with_photo_fields, new_profile_image_key_large)
        if new_profile_image_value_large != object_with_photo_fields.we_vote_hosted_profile_image_url_large:
            object_with_photo_fields.we_vote_hosted_profile_image_url_large = new_profile_image_value_large
            at_least_one_change = True
        new_profile_image_value_medium = getattr(object_with_photo_fields, new_profile_image_key_medium)
        if new_profile_image_value_medium != object_with_photo_fields.we_vote_hosted_profile_image_url_medium:
            object_with_photo_fields.we_vote_hosted_profile_image_url_medium = new_profile_image_value_medium
            at_least_one_change = True
        new_profile_image_value_tiny = getattr(object_with_photo_fields, new_profile_image_key_tiny)
        if new_profile_image_value_tiny != object_with_photo_fields.we_vote_hosted_profile_image_url_tiny:
            object_with_photo_fields.we_vote_hosted_profile_image_url_tiny = new_profile_image_value_tiny
            at_least_one_change = True
        if at_least_one_change:
            save_changes = True

    results = {
        'object_with_photo_fields': object_with_photo_fields,
        'save_changes':             save_changes,
        'status':                   status,
        'success':                  success,
    }
    return results
