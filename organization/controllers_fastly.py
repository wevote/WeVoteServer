# organization/controllers_fastly.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import boto3
from config.base import get_environment_variable
import logging
import requests
from wevote_functions.functions import positive_value_exists

AWS_ACCESS_KEY_ID = get_environment_variable("AWS_ACCESS_KEY_ID")
AWS_HOSTED_ZONE_ID = get_environment_variable("AWS_HOSTED_ZONE_ID")
AWS_SECRET_ACCESS_KEY = get_environment_variable("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
FASTLY_API_HOSTNAME = get_environment_variable("FASTLY_API_HOSTNAME")
FASTLY_API_SERVICE_ID = get_environment_variable("FASTLY_API_SERVICE_ID")
FASTLY_API_TOKEN = get_environment_variable("FASTLY_API_TOKEN")
FASTLY_WILDCARD_CNAME = get_environment_variable("FASTLY_WILDCARD_CNAME")

HEADERS = {
    'Fastly-Key': FASTLY_API_TOKEN,
    'Accept': 'application/json',
}


def get_current_fastly_config_version():
    url = "%s/service/%s/version" % (FASTLY_API_HOSTNAME, FASTLY_API_SERVICE_ID)
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        logging.warning("Unable to get list of versions: %s", response.content)
        return None
    versions = response.json()
    for v in versions:
        if v['active'] == True:
            return v['number']
    return None


def get_wevote_subdomain_status(chosen_subdomain_string):
    status = ''
    subdomain_exists = False
    success = False

    current_fastly_version_number = get_current_fastly_config_version()
    status += "GET_WE_VOTE_SUBDOMAIN_STATUS " + str(chosen_subdomain_string) + " " + \
              str(current_fastly_version_number) + " "
    if positive_value_exists(current_fastly_version_number):
        url = "{fastly_api_hostname}/service/{fastly_api_service_id}/version/{current_fastly_version_number}/domain" \
              "/{chosen_subdomain_string}.wevote.us/check" \
              "".format(fastly_api_hostname=FASTLY_API_HOSTNAME,
                        fastly_api_service_id=FASTLY_API_SERVICE_ID,
                        current_fastly_version_number=current_fastly_version_number,
                        chosen_subdomain_string=chosen_subdomain_string)
        try:
            response = requests.get(url, headers=HEADERS)
            status += "FASTLY_STATUS_CODE: " + str(response.status_code) + " "
            if response.status_code == 200:
                json_response_as_list = response.json()
                details = json_response_as_list[0]
                subdomain_exists = json_response_as_list[2]
                status += "SUBDOMAIN_ALREADY_EXISTS "
                success = True
            elif response.status_code == 404:
                json_response = response.json()
                status += json_response['msg'] + " " + json_response['detail'] + " "
                success = True
            else:
                status += "RESPONSE_STATUS_NOT_RECOGNIZED "
                success = False
        except Exception as e:
            status += "EXCEPTION_FROM_FASTLY " + str(e) + " "
            success = False

    json_results = {
        'status':                           status,
        'success':                          success,
        'current_fastly_version_number':    current_fastly_version_number,
        'subdomain_exists':                 subdomain_exists,
    }
    return json_results


def clone_current_fastly_config_version(current_fastly_version_number):
    new_fastly_version_number = None
    status = ''
    clone_successful = False
    success = False

    if positive_value_exists(current_fastly_version_number):
        url = "{fastly_api_hostname}/service/{fastly_api_service_id}/version/{current_fastly_version_number}/clone" \
              "".format(fastly_api_hostname=FASTLY_API_HOSTNAME,
                        fastly_api_service_id=FASTLY_API_SERVICE_ID,
                        current_fastly_version_number=current_fastly_version_number)

        try:
            response = requests.put(url, headers=HEADERS)
            status += "FASTLY_STATUS_CODE: " + str(response.status_code) + " "
            if response.status_code == 200:
                version = response.json()
                new_fastly_version_number = version['number']
                clone_successful = True
                status += "FASTLY_CONFIG_CLONED "
                success = True
            elif response.status_code == 404:
                json_response = response.json()
                status += json_response['msg'] + " " + json_response['detail'] + " "
                success = False
            else:
                status += "RESPONSE_STATUS_NOT_RECOGNIZED "
                success = False
        except Exception as e:
            status += "EXCEPTION_FROM_FASTLY " + str(e) + " "
            success = False
    else:
        status += "MISSING_VERSION_NUMBER "

    json_results = {
        'status':                           status,
        'success':                          success,
        'current_fastly_version_number':    current_fastly_version_number,
        'new_fastly_version_number':        new_fastly_version_number,
        'clone_successful':                 clone_successful,
    }
    return json_results


def add_fastly_domain(new_fastly_version_number, new_subdomain):
    status = ''
    subdomain_exists = False
    new_full_domain = "{new_subdomain}.wevote.us".format(new_subdomain=new_subdomain)

    status += "ADDING_FASTLY_DOMAIN: " + str(new_full_domain) + " "
    url = "{fastly_api_hostname}/service/{fastly_api_service_id}/version/{new_fastly_version_number}/domain" \
          "".format(fastly_api_hostname=FASTLY_API_HOSTNAME,
                    fastly_api_service_id=FASTLY_API_SERVICE_ID,
                    new_fastly_version_number=new_fastly_version_number)
    data = {
        'name': new_full_domain,
    }
    try:
        response = requests.post(url, headers=HEADERS, data=data)
        status += "FASTLY_STATUS_CODE: " + str(response.status_code) + " "
        if response.status_code == 200:
            json_response = response.json()
            subdomain_exists = True
            status += "DOMAIN_EXISTS "
            success = True
        elif response.status_code == 404:
            json_response = response.json()
            status += json_response['msg'] + " " + json_response['detail'] + " "
            success = True
        else:
            status += "RESPONSE_STATUS_NOT_RECOGNIZED "
            success = False
    except Exception as e:
        status += "EXCEPTION_FROM_FASTLY " + str(e) + " "
        success = False

    json_results = {
        'status':                       status,
        'success':                      success,
        'new_fastly_version_number':    new_fastly_version_number,
        'subdomain_exists':             subdomain_exists,
    }
    return json_results


def del_fastly_domain(new_version, domain_to_remove):
    url = "%s/service/%s/version/%s/domain/%s" % (FASTLY_API_HOSTNAME, FASTLY_API_SERVICE_ID,
                                                  new_version, domain_to_remove)
    response = requests.delete(url, headers=HEADERS)
    if response.status_code != 200:
        logging.warning("Unable to remove domain (%s) to new version (%d) of service", domain_to_remove, new_version)
        return False
    return True


def activate_new_fastly_config_version(new_fastly_version_number):
    clone_activated = False
    status = ""
    success = True
    status += "ACTIVATING_NEW_FASTLY_CONFIG: " + str(new_fastly_version_number) + " "
    if positive_value_exists(new_fastly_version_number):
        url = "{fastly_api_hostname}/service/{fastly_api_service_id}/version/{new_fastly_version_number}/activate" \
              "".format(fastly_api_hostname=FASTLY_API_HOSTNAME,
                        fastly_api_service_id=FASTLY_API_SERVICE_ID,
                        new_fastly_version_number=new_fastly_version_number)
        try:
            response = requests.put(url, headers=HEADERS)
            status += "FASTLY_STATUS_CODE: " + str(response.status_code) + " "
            if response.status_code == 200:
                json_response = response.json()
                clone_activated = True
                status += "FASTLY_CONFIG_ACTIVATED "
                success = True
            elif response.status_code == 404:
                json_response = response.json()
                status += json_response['msg'] + " " + json_response['detail'] + " "
                success = False
            else:
                status += "RESPONSE_STATUS_NOT_RECOGNIZED "
                success = False
        except Exception as e:
            status += "EXCEPTION_FROM_FASTLY " + str(e) + " "
            success = False
    else:
        status += "MISSING_VERSION_NUMBER "

    json_results = {
        'status':                       status,
        'success':                      success,
        'new_fastly_version_number':    new_fastly_version_number,
        'clone_activated':              clone_activated,
    }
    return json_results


def route53_request(new_domain, action):
    status = ""
    success = True
    status += "ADDING_ROUTE53_FOR_DOMAIN: " + str(new_domain) + " " + str(action) + " "
    try:
        client = boto3.client('route53',
                              aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        response = client.change_resource_record_sets(
            HostedZoneId=AWS_HOSTED_ZONE_ID,
            ChangeBatch={
                'Changes': [
                    {
                        'Action': action,
                        'ResourceRecordSet': {
                            'Name': new_domain,
                            'Type': 'CNAME',
                            'TTL': 300,
                            'ResourceRecords': [
                                {
                                    'Value': FASTLY_WILDCARD_CNAME
                                }
                            ]
                        }
                    }
                ]
            }
        )
        status += "NEW_ROUTE53_ACTION_FOR_DOMAIN: " + str(new_domain) + " " + str(action) + " "
    except Exception as e:
        logging.exception("Unable to add route53 for wevote.us new_domain" + str(e))
        status += "ROUTE53_EXCEPTION: " + str(e) + " "
        success = False
    json_status = {
        'status': status,
        'success': success,
    }
    return json_status


def add_subdomain_route53_record(new_subdomain):
    new_full_domain = "{new_subdomain}.wevote.us".format(new_subdomain=new_subdomain)
    logging.info("Adding DNS record for domain [%s]", new_full_domain)
    results = route53_request(new_full_domain, 'CREATE')
    logging.info(results['status'])
    json_status = {
        'status': results['status'],
        'success': results['success'],
    }
    return json_status


def delete_subdomain_route53_record(new_subdomain):
    new_full_domain = "{new_subdomain}.wevote.us".format(new_subdomain=new_subdomain)
    logging.info("Removing DNS record for domain [%s]", new_full_domain)
    results = route53_request(new_full_domain, 'DELETE')
    logging.info(results['status'])
    json_status = {
        'status': results['status'],
        'success': results['success'],
    }
    return json_status


def add_wevote_subdomain_to_fastly(new_subdomain):
    status = ""
    success = True
    logging.info("Adding new subdomain [%s]", new_subdomain)
    status += "ADDING_NEW_SUBDOMAIN: " + str(new_subdomain) + " "

    # add domain to fastly config
    current_version = get_current_fastly_config_version()
    if current_version is None:
        logging.error("Unable to get current version")
        status += "UNABLE_TO_GET_CURRENT_FASTLY_VERSION "
        json_status = {
            'status':   status,
            'success':  False,
        }
        return json_status

    clone_results = clone_current_fastly_config_version(current_version)
    clone_successful = clone_results['clone_successful']
    if positive_value_exists(clone_successful):
        new_fastly_version_number = clone_results['new_fastly_version_number']
        status += "FASTLY_CONFIG_CLONED "
    else:
        status += clone_results['status']
        status += "UNABLE_TO_CLONE_NEW_FASTLY_CONFIG "
        json_status = {
            'status': status,
            'success': False,
        }
        return json_status

    add_results = add_fastly_domain(new_fastly_version_number, new_subdomain)
    if not add_results['subdomain_exists']:
        logging.error("Unable to add new subdomain to service")
        status += add_results['status']
        status += "UNABLE_TO_ADD_NEW_FASTLY_SUBDOMAIN "
        json_status = {
            'status': status,
            'success': False,
        }
        return json_status

    activate_results = activate_new_fastly_config_version(new_fastly_version_number)
    if not activate_results['clone_activated']:
        logging.error("Unable to activate new version of service")
        status += activate_results['status']
        status += "UNABLE_TO_ACTIVATE_NEW_FASTLY_CONFIG_VERSION "
        json_status = {
            'status': status,
            'success': False,
        }
        return json_status

    logging.info("New domain %s added to service", new_subdomain)
    status += "NEW_SUBDOMAIN_ADDED: " + str(new_subdomain) + " "
    json_status = {
        'status': status,
        'success': success,
    }
    return json_status


def delete_wevote_subdomain_from_fastly(subdomain):
    logging.info("Removing subdomain [%s]", subdomain)

    # remove domain from fastly config
    current_version = get_current_fastly_config_version()
    if current_version == None:
        logging.error("Unable to get current version")
        return
    new_version = clone_current_fastly_config_version(current_version)
    if del_fastly_domain(new_version, subdomain) != True:
        logging.error("Unable to remove domain from service")
        return
    if activate_new_fastly_config_version(new_version) != True:
        logging.error("Unable to activate new version of service")
        return
    logging.info("Domain %s removed from Fastly service", subdomain)
