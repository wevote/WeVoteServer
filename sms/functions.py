# sms/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import SIGN_IN_CODE_SMS_TEMPLATE
from django.template.loader import get_template
from django.template import Context
import json


def get_sms_template_filename(kind_of_sms_template):
    if kind_of_sms_template == SIGN_IN_CODE_SMS_TEMPLATE:
        return "sign_in_code_sms.txt"
    # If the template wasn't recognized, return GENERIC_SMS_TEMPLATE
    return "sign_in_code_sms.txt"


def merge_message_content_with_template(kind_of_sms_template, template_variables_in_json):
    success = True
    status = "KIND_OF_SMS_TEMPLATE: " + str(kind_of_sms_template) + " "
    message_text = ""

    # Transfer JSON template variables back into a dict
    template_variables_dict = json.loads(template_variables_in_json)
    # template_variables_object = Context(template_variables_dict)  # Used previously with Django 1.8

    # Set up the templates
    text_template_path = "sms/sms_templates/" + get_sms_template_filename(kind_of_sms_template)

    # We need to combine the template_variables_in_json with the kind_of_sms_template
    text_template = get_template(text_template_path)

    try:
        message_text = text_template.render(template_variables_dict)
        status += "RENDERED_TEXT_TEMPLATE "
    except Exception as e:
        status += "FAILED_RENDERING_TEMPLATE, error: " + str(e) + " "
        success = False

    results = {
        'success':      success,
        'status':       status,
        'message_text': message_text,
    }
    return results
