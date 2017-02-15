# image/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from io import BytesIO
from PIL import Image
from urllib.request import Request, urlopen
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
            urlopen(Request(image_url_https))
            image_url_valid = True
    except Exception as e:
        image_url_valid = False

    if image_url_valid:
        response = requests.get(image_url_https)
        image = Image.open(BytesIO(response.content))
        image_width, image_height = image.size
        image_format = image.format

    results = {
        'image_url_valid':              image_url_valid,
        'image_width':                  image_width,
        'image_height':                 image_height,
        'image_format':                 image_format.lower() if image_format is not None else image_format
    }
    return results
