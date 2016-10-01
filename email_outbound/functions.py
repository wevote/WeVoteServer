# email_outbound/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import FRIEND_INVITATION_TEMPLATE, VERIFY_EMAIL_ADDRESS_TEMPLATE
from django.template.loader import get_template
from django.template import Context
import json


def get_template_filename(kind_of_email_template, text_or_html):
    if kind_of_email_template == VERIFY_EMAIL_ADDRESS_TEMPLATE:
        if text_or_html == "HTML":
            return "verify_email_address.html"
        else:
            return "verify_email_address.txt"
    elif kind_of_email_template == FRIEND_INVITATION_TEMPLATE:
        if text_or_html == "HTML":
            return "friend_invitation.html"
        else:
            return "friend_invitation.txt"

    # If the template wasn't recognized, return GENERIC_EMAIL_TEMPLATE
    if text_or_html == "HTML":
        return "generic_email.html"
    else:
        return "generic_email.txt"


def merge_message_content_with_template(kind_of_email_template, template_variables_in_json):
    success = True
    status = ""

    # Transfer JSON template variables back into a dict
    template_variables_dict = json.loads(template_variables_in_json)
    template_variables_object = Context(template_variables_dict)

    # Set up the templates
    text_template_path = "email_outbound/email_templates/" + get_template_filename(kind_of_email_template, "TEXT")
    html_template_path = "email_outbound/email_templates/" + get_template_filename(kind_of_email_template, "HTML")

    # We need to combine the template_variables_in_json with the kind_of_email_template
    text_template = get_template(text_template_path)
    html_template = get_template(html_template_path)

    if "subject" in template_variables_dict:
        subject = template_variables_dict['subject']
    else:
        subject = "From We Vote"

    message_text = text_template.render(template_variables_object)
    message_html = html_template.render(template_variables_object)

    results = {
        'success':      success,
        'status':       status,
        'subject':      subject,
        'message_text': message_text,
        'message_html': message_html,
    }
    return results
