# apis_v1/documentation_source/pdf_to_html_doc.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def pdf_to_html_retrieve_view(url_root):
    """
    Show documentation about pdfToHtmlRetrieve
    """
    required_query_parameter_list = [
        {
            'name':         'voter_device_id',
            'value':        'string',  # boolean, integer, long, string
            'description':  'An 88 character unique identifier linked to a voter record on the server',
        },
        {
            'name': 'pdf_url',
            'value': 'string',  # boolean, integer, long, string
            'description': 'The valid URL, from which to load the PDF to be converted',
        },
    ]
    optional_query_parameter_list = [
    ]

    potential_status_codes_list = [
        {
            'code':         'PDF_URL_MISSING',
            'description':  'The URL to the PDF is either missing or invalid.',
        },
        {
            'code':         'PDF_URL_RETURNED',
            'description':  'The API call has returned a URL to a new HTML page in S3',
        },
    ]

    try_now_link_variables_dict = {
    }

    api_response = '{\n' \
                   '  "status": string,\n' \
                   '  "success": boolean,\n' \
                   '  "output_from_subprocess": string,\n' \
                   '  "s3_url_for_html": string (a public url to a new or reused HTML page in S3),\n' \
                   '}'

    template_values = {
        'api_name': 'pdfToHtmlRetrieve',
        'api_slug': 'pdfToHtmlRetrieve',
        'api_introduction':
            "Convert a PDF to an HTML file in S3, and return the URL",
        'try_now_link': 'apis_v1:pdfToHtmlRetrieve',
        'try_now_link_variables_dict': try_now_link_variables_dict,
        'url_root': url_root,
        'get_or_post': 'GET',
        'required_query_parameter_list': required_query_parameter_list,
        'optional_query_parameter_list': optional_query_parameter_list,
        'api_response': api_response,
        'api_response_notes':
            "",
        'potential_status_codes_list': potential_status_codes_list,
    }
    return template_values
