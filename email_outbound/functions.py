# email_outbound/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import base64
import uuid
from bs4 import BeautifulSoup
from config.base import get_environment_variable
from .models import CAMPAIGNX_FRIEND_HAS_SUPPORTED_TEMPLATE, CAMPAIGNX_NEWS_ITEM_TEMPLATE, \
    CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE, CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_TEMPLATE, \
    FRIEND_ACCEPTED_INVITATION_TEMPLATE, FRIEND_INVITATION_TEMPLATE, LINK_TO_SIGN_IN_TEMPLATE, \
    MESSAGE_TO_FRIEND_TEMPLATE, NOTICE_FRIEND_ENDORSEMENTS_TEMPLATE, NOTICE_VOTER_DAILY_SUMMARY_TEMPLATE, \
    REMIND_CONTACT, SEND_BALLOT_TO_SELF, SEND_BALLOT_TO_FRIENDS, SIGN_IN_CODE_EMAIL_TEMPLATE, \
    VERIFY_EMAIL_ADDRESS_TEMPLATE, EmailAttachments
from django.template.loader import get_template
from html.parser import HTMLParser
import re
import json

import boto3

def get_template_filename(kind_of_email_template, text_or_html):
    if kind_of_email_template == VERIFY_EMAIL_ADDRESS_TEMPLATE:
        if text_or_html == "HTML":
            return "verify_email_address.html"
        else:
            return "verify_email_address.txt"
    elif kind_of_email_template == CAMPAIGNX_FRIEND_HAS_SUPPORTED_TEMPLATE:
        if text_or_html == "HTML":
            return "campaignx_friend_has_supported.html"
        else:
            return "campaignx_friend_has_supported.txt"
    elif kind_of_email_template == CAMPAIGNX_NEWS_ITEM_TEMPLATE:
        if text_or_html == "HTML":
            return "campaignx_news_item.html"
        else:
            return "campaignx_news_item.txt"
    elif kind_of_email_template == CAMPAIGNX_SUPER_SHARE_ITEM_TEMPLATE:
        if text_or_html == "HTML":
            return "campaignx_super_share_item.html"
        else:
            return "campaignx_super_share_item.txt"
    elif kind_of_email_template == CAMPAIGNX_SUPPORTER_INITIAL_RESPONSE_TEMPLATE:
        if text_or_html == "HTML":
            return "campaignx_supporter_initial_response.html"
        else:
            return "campaignx_supporter_initial_response.txt"
    elif kind_of_email_template == FRIEND_INVITATION_TEMPLATE:
        if text_or_html == "HTML":
            return "friend_invitation.html"
        else:
            return "friend_invitation.txt"
    elif kind_of_email_template == FRIEND_ACCEPTED_INVITATION_TEMPLATE:
        if text_or_html == "HTML":
            return "friend_accepted_invitation.html"
        else:
            return "friend_accepted_invitation.txt"
    elif kind_of_email_template == LINK_TO_SIGN_IN_TEMPLATE:
        if text_or_html == "HTML":
            return "link_to_sign_in.html"
        else:
            return "link_to_sign_in.txt"
    elif kind_of_email_template == MESSAGE_TO_FRIEND_TEMPLATE:
        if text_or_html == "HTML":
            return "message_to_friend.html"
        else:
            return "message_to_friend.txt"
    elif kind_of_email_template == NOTICE_FRIEND_ENDORSEMENTS_TEMPLATE:
        if text_or_html == "HTML":
            return "notice_friend_endorsements.html"
        else:
            return "notice_friend_endorsements.txt"
    elif kind_of_email_template == NOTICE_VOTER_DAILY_SUMMARY_TEMPLATE:
        if text_or_html == "HTML":
            return "notice_voter_daily_summary.html"
        else:
            return "notice_voter_daily_summary.txt"
    elif kind_of_email_template == REMIND_CONTACT:
        if text_or_html == "HTML":
            return "remind_contact.html"
        else:
            return "remind_contact.txt"
    elif kind_of_email_template == SEND_BALLOT_TO_SELF:
        if text_or_html == "HTML":
            return "send_ballot_to_self.html"
        else:
            return "send_ballot_to_self.txt"
    elif kind_of_email_template == SEND_BALLOT_TO_FRIENDS:
        if text_or_html == "HTML":
            return "send_ballot_to_friends.html"
        else:
            return "send_ballot_to_friends.txt"
    elif kind_of_email_template == SIGN_IN_CODE_EMAIL_TEMPLATE:
        if text_or_html == "HTML":
            return "sign_in_code_email.html"
        else:
            return "sign_in_code_email.txt"
    # If the template wasn't recognized, return GENERIC_EMAIL_TEMPLATE
    if text_or_html == "HTML":
        return "generic_email.html"
    else:
        return "generic_email.txt"


def merge_message_content_with_template(kind_of_email_template, template_variables_in_json):
    success = True
    status = "KIND_OF_EMAIL_TEMPLATE: " + str(kind_of_email_template) + " "
    message_text = ""
    message_html = ""

    # Transfer JSON template variables back into a dict
    template_variables_dict = json.loads(template_variables_in_json)
    # template_variables_object = Context(template_variables_dict)  # Used previously with Django 1.8

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

    try:
        message_text = text_template.render(template_variables_dict)
        status += "RENDERED_TEXT_TEMPLATE "
        message_html = html_template.render(template_variables_dict)
        status += "RENDERED_HTML_TEMPLATE "
    except Exception as e:
        status += "FAILED_RENDERING_TEMPLATE, error: " + str(e) + " "
        success = False

    results = {
        'success':      success,
        'status':       status,
        'subject':      subject,
        'message_text': message_text,
        'message_html': message_html,
    }
    return results


class HTMLToPlainText(HTMLParser):
    """Convert HTML to plain text, preserving structure and readability."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_line = []
        self.in_script = False
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        # Add line breaks for block elements
        if tag in ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr']:
            if self.current_line:
                self.text_parts.append(''.join(self.current_line).strip())
                self.current_line = []

        # Add extra line break for headers
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.text_parts.append('')

        # Track script and style tags to ignore their content
        if tag == 'script':
            self.in_script = True
        elif tag == 'style':
            self.in_style = True

    def handle_endtag(self, tag):
        if tag in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table']:
            if self.current_line:
                self.text_parts.append(''.join(self.current_line).strip())
                self.current_line = []
            self.text_parts.append('')  # Add blank line after these elements

        if tag == 'script':
            self.in_script = False
        elif tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        # Ignore content in script and style tags
        if self.in_script or self.in_style:
            return

        # Clean up whitespace but preserve single spaces
        cleaned_data = ' '.join(data.split())
        if cleaned_data:
            self.current_line.append(cleaned_data)

    def get_text(self):
        # Add any remaining text
        if self.current_line:
            self.text_parts.append(''.join(self.current_line).strip())

        # Join all parts and clean up excessive blank lines
        text = '\n'.join(self.text_parts)
        # Replace 3+ newlines with just 2 newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def convert_html_to_plain_text(html_content):
    """
    Convert HTML email content to plain text.

    Args:
        html_content: String containing HTML

    Returns:
        Plain text version of the HTML content
    """
    if not html_content:
        return ''

    try:
        parser = HTMLToPlainText()
        parser.feed(html_content)
        plain_text = parser.get_text()
        return plain_text
    except Exception as e:
        # Fallback: strip all HTML tags if parser fails
        plain_text = re.sub(r'<[^>]+>', '', html_content)
        # Clean up whitespace
        plain_text = re.sub(r'\s+', ' ', plain_text)
        return plain_text.strip()


# S3 functions
# create s3 bucket
def _s3_client_bucket():
    # Works with env keys or IAM role
    AWS_ACCESS_KEY_ID = get_environment_variable("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = get_environment_variable("AWS_SECRET_ACCESS_KEY")
    AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
    AWS_STORAGE_BUCKET_NAME = get_environment_variable("AWS_STORAGE_BUCKET_NAME")
    AWS_STORAGE_SERVICE = "s3"

    session = boto3.session.Session(region_name=AWS_REGION_NAME,
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    s3 = session.resource(AWS_STORAGE_SERVICE)
    return s3.Bucket(AWS_STORAGE_BUCKET_NAME)


# make filename safe
def _safe_filename(name: str) -> str:
  # basic sanitize; you can harden this if needed
  name = (name or "file").replace("\\", "/").split("/")[-1]
  return "".join(ch for ch in name if ch.isalnum() or ch in (" ", ".", "_", "-", "(", ")", "[", "]")).strip() or "file"


# build s3 key
def build_s3_key(*, campaign_id: int | None, template_id: int | None, draft_uuid: None, original_filename: str) -> str:
  owner = "unknown"
  if campaign_id:
    owner = f"campaigns/{campaign_id}"
  elif template_id:
    owner = f"templates/{template_id}"
  else:
    owner = f"drafts/{draft_uuid}"

  clean = _safe_filename(original_filename)
  u = uuid.uuid4().hex
  return f"email/{owner}/attachments/{u}-{clean}"


# Uploads a Django InMemoryUploadedFile / TemporaryUploadedFile to S3.
#   Returns size in bytes.
def upload_fileobj_to_s3(*, fileobj, key: str, content_type: str = "") -> int:
  bucket = _s3_client_bucket()

  # Ensure we can compute size without reading into memory
  size = getattr(fileobj, "size", None)
  kwargs = dict(Fileobj=fileobj, Key=key)
  if content_type:
      kwargs["ExtraArgs"] = {"ContentType": content_type}
  bucket.upload_fileobj(**kwargs)

  return int(size or 0)


# stream and prepare file from s3 for download
def download_bytes_from_s3(*, key: str) -> bytes:
  bucket = _s3_client_bucket()
  obj = bucket.Object(key).get()
  return obj["Body"]


# delete file from s3
def delete_from_s3(*, key: str) -> None:
  bucket = _s3_client_bucket()
  bucket.Object(key).delete()


# move file location from old key to new key in s3
def move_s3_object(*, old_key: str, new_key: str) -> None:
    bucket = _s3_client_bucket()

    copy_source = {"Bucket": bucket.name, "Key": old_key}

    # Copy to new key
    bucket.Object(new_key).copy(copy_source)

    # Delete old key
    bucket.Object(old_key).delete()


# prepare attachments to send via sendgrid
# expects: email_body (html str), email campaign object
# need b64 encoding to send attachments via sendgrid
# email body in html needs inline tags to be modified before send
def build_prepared_campaign_attachments(body: str, email_campaign):
    prepared_attachments = []
    bucket = _s3_client_bucket()

    # get non-inline attachments
    attachments = EmailAttachments.objects.filter(email_campaign=email_campaign, is_inline=False)
    for att in attachments:
        obj = bucket.Object(att.s3_key).get()
        raw_bytes = obj["Body"].read()
        b64encoding = base64.b64encode(raw_bytes).decode("utf-8")

        prepared_attachments.append({
            "id": att.id,
            "original_name": att.original_name,
            "content_type": att.content_type or "application/octet-stream",
            "b64encoding": b64encoding,
            "inline": False
        })

    # parse body for inline img tags
    soup = BeautifulSoup(body, 'html.parser')
    for img in soup.find_all('img'):
        original_src = img.get('src')

        # get attachment ids
        try:
            parts = original_src.split('/')
            attachment_id = next(p for p in parts if p.isdigit())
        except StopIteration:
            continue

        try:
            att_obj = EmailAttachments.objects.get(id=attachment_id)
            obj = bucket.Object(att_obj.s3_key).get()
            raw_bytes = obj["Body"].read()
            b64encoding = base64.b64encode(raw_bytes).decode("utf-8")
        except EmailAttachments.DoesNotExist:
            continue

        # create and covert the img tag to a cid tag
        cid = f"img_{attachment_id}"
        img['src'] = f"cid:{cid}"

        # prepare attachments
        prepared_attachments.append({
            "id": att_obj.id,
            "original_name": att_obj.original_name,
            "content_type": att_obj.content_type or "application/octet-stream",
            "b64encoding": b64encoding,
            "inline": True
        })

    # return final body and prepared attachments
    final_body = str(soup)
    return final_body, prepared_attachments


# get inline attachment ids for cleanup
def get_inline_attachment_ids_from_html(html: str) -> set[int]:
    if not html:
        return set()

    matches = re.findall(r'attachments/render/(\d+)/', html)
    return {int(x) for x in matches}


# cleanup attachments that are not part of inline body anymore
# expects html body and email campaign object or email template object related to body
def cleanup_unused_inline_attachments(html: str, email_campaign=None, email_template=None):
    referenced_ids = get_inline_attachment_ids_from_html(html)
    s3_keys = list(
        EmailAttachments.objects.filter(id__in=referenced_ids)
        .values_list('s3_key', flat=True)
    )

    try:
        inline_attachments = None
        if email_campaign:
            inline_attachments = EmailAttachments.objects.filter(
                email_campaign=email_campaign,
                is_inline=True,
            )
        elif email_template:
            inline_attachments = EmailAttachments.objects.filter(
                email_template=email_template,
                is_inline=True,
            )
        else:
            raise ValueError("Either campaign or template must be provided")

        for att in inline_attachments:
            if att.s3_key not in s3_keys:
                att_s3_key = att.s3_key
                att_count = EmailAttachments.objects.filter(s3_key=att_s3_key).count()
                if att_count > 1:
                    att.delete()
                elif att_count == 1:
                    att.delete()
                    delete_from_s3(key=att.s3_key)

    except ValueError as e:
        print(f"Caught an error: {e}")
