# electoral_district/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ElectoralDistrict, ElectoralDistrictManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, convert_to_int, extract_state_from_ocd_division_id, \
    extract_district_from_ocd_division_id
import xml.etree.ElementTree as ElementTree
from exception.models import handle_exception
from exception.models import handle_record_found_more_than_one_exception

logger = wevote_functions.admin.get_logger(__name__)


def electoral_districts_import_from_sample_file(filename):
    """
    Get the XML data, and either create new entries or update existing
    :return:
    """
    # Load saved xml from local file
    logger.info("Loading electoral_districts from local XML file")

    xml_tree = ElementTree.parse(filename)
    xml_root = xml_tree.getroot()

    electoral_district_item_list = ''

    if xml_root:
        # Look for ElectoralDistrict and create the Master table first. ElectoralDistrict is the direct child node
        # of vipObject
        electoral_district_item_list = xml_root.findall('ElectoralDistrict')
        # number_of_electoral_districts = len(electoral_district_item_list)

    return electoral_district_import_from_xml_data(electoral_district_item_list)


def electoral_district_import_from_xml_data(electoral_district_xml_data):
    """
    Get the xml data, and either create new entries or update existing entries for electoral district
    :return:
    """

    electoral_district_not_processed = 0
    electoral_district_saved = 0
    electoral_district_updated = 0
    success = False
    status = ''

    electoral_district_manager = ElectoralDistrictManager()

    limit_for_testing = 0

    for one_electoral_district in electoral_district_xml_data:
        total_count = electoral_district_saved + electoral_district_not_processed + electoral_district_updated
        if positive_value_exists(limit_for_testing) and total_count >= limit_for_testing:
            # This limitation is used when we are doing development and testing
            break

        electoral_district_number = None
        electoral_district_other_type = ''
        ocd_id_external_id = ''
        electoral_district_type = ''

        duplicate_entry = 0

        ctcl_id_temp = one_electoral_district.attrib['id']
        electoral_district_name = one_electoral_district.find('Name').text

        electoral_district_type_found = one_electoral_district.find('Type')
        if electoral_district_type_found is not None:
            electoral_district_type = electoral_district_type_found.text

        # TODO validate electoral_district_type from electoralDistrictType enum

        electoral_district_number_found = one_electoral_district.find('Number')
        if electoral_district_number_found is not None:
            electoral_district_number = convert_to_int(electoral_district_number_found.text)

        electoral_district_other_type_found = one_electoral_district.find('OtherType')

        if electoral_district_other_type_found is not None:
            electoral_district_other_type = electoral_district_other_type_found.text

        external_identifiers_list = one_electoral_district.findall(
            "./ExternalIdentifiers/ExternalIdentifier/[Type='ocd-id']/Value")
        if external_identifiers_list is not None:
            # look for value of 'ocd-id type value under ExternalIdentifier
            ocd_id_external_id = one_electoral_district.find(
                "./ExternalIdentifiers/ExternalIdentifier/[Type='ocd-id']/Value").text

        # Pull state_code from ocdDivisionId
        if positive_value_exists(ocd_id_external_id):
            # ocd_division_id = ocd_id_external_id
            state_code = extract_state_from_ocd_division_id(ocd_id_external_id)
            if not positive_value_exists(state_code):
                district_code = extract_district_from_ocd_division_id(ocd_id_external_id)
                district_code.lower()
                # check if it is District of Columbia (DC). DC doesn't have state substring in ocd_id
                if district_code == 'dc':
                    state_code = 'dc'
        else:
            state_code = ''

        # Always store state_code in lower case
        if state_code:
            state_code = state_code.lower()

        # Make sure we have the minimum required variables
        if not positive_value_exists(ctcl_id_temp) or not positive_value_exists(electoral_district_name):
            electoral_district_not_processed += 1
            continue

        # check if this is a duplicate entry
        try:
            # TODO check what constitutes a UNIQUE record in the table
            electoral_district_query = ElectoralDistrict.objects.order_by('id')
            if electoral_district_query:
                electoral_district_query = electoral_district_query.filter(
                    ctcl_id_temp=ctcl_id_temp, electoral_district_name=electoral_district_name)
                # electoral_district_query = electoral_district_query.filter(
                #     electoral_district_name=electoral_district_name)
                # TODO currently update is not handled. Based on what constitutes a unique row, handle update
                if electoral_district_query.count() > 0:
                    duplicate_entry = 1
                    electoral_district_not_processed += 1

            if duplicate_entry > 0:
                # This entry already exists, skip update_or_create. set success to True
                success = True
                status += "ELECTORAL_DISTRICT_ENTRY_EXISTS "
            else:
                try:
                    updated_values = {
                        'electoral_district_type':          electoral_district_type,
                        'electoral_district_number':        electoral_district_number,
                        'electoral_district_other_type':    electoral_district_other_type,
                        'ocd_id_external_id':               ocd_id_external_id,
                        'state_code':                       state_code
                    }
                    results = electoral_district_manager.update_or_create_electoral_district(
                        ctcl_id_temp,
                        electoral_district_name,
                        updated_values)
                    if not results:
                        electoral_district_not_processed += 1
                        success = False
                    elif results['new_electoral_district_created']:
                        electoral_district_saved += 1
                        success = True
                        status += "ELECTORAL_DISTRICT_IMPORT_PROCESS_CREATED "
                    else:
                        electoral_district_updated += 1
                        success = True
                        status += "ELECTORAL_DISTRICT_IMPORT_PROCESS_UPDATED "
                except Exception as e:
                    status += 'FAILED update_or_create_electoral_district. ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    handle_exception(e, logger=logger, exception_message=status)
                    success = False
                    pass

        except ElectoralDistrict.DoesNotExist:
            pass

    electoral_district_results = {
        'success':          success,
        'status':           status,
        'saved':            electoral_district_saved,
        'updated':          electoral_district_updated,
        'not_processed':    electoral_district_not_processed,
    }

    return electoral_district_results


def retrieve_electoral_district(ctcl_id_temp):
    results = ''
    state_code = ''
    state_code_found = False
    electoral_district_found = False

    try:
        electoral_district_query = ElectoralDistrict.objects.all()
        electoral_district_item = electoral_district_query.get(ctcl_id_temp=ctcl_id_temp)
        electoral_district_found = True
        state_code = electoral_district_item.state_code
        if positive_value_exists(state_code):
            state_code_found = True

    except ElectoralDistrict.MultipleObjectsReturned as e:
        electoral_district_item = ElectoralDistrict()
        handle_record_found_more_than_one_exception(e, logger)

        status = "ERROR_MORE_THAN_ONE_ELECTORAL_DISTRICT_FOUND"

    except ElectoralDistrict.DoesNotExist:
        electoral_district_item = ElectoralDistrict()
        pass

    # return electoral_district_item
    results = {
        'electoral_district_found': electoral_district_found,
        'state_code_found':         state_code_found,
        'electoral_district':       electoral_district_item,
        'state_code':               state_code
    }

    return results


def get_electoral_district_number(self):
    return self.electoral_district_number


def get_electoral_district_name(self):
    return self.electoral_district_name


def get_electoral_district_other_type(self):
    return self.electoral_district_other_type


def get_electoral_district_type(self):
    return self.electoral_district_type
