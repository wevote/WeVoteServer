# electoral_district/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import ElectoralDistrict, ElectoralDistrictManager, ELECTORAL_DISTRICT_TYPE_CHOICES
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, convert_to_int
import xml.etree.ElementTree as ET
from import_export_ctcl.controllers import CTCL_SAMPLE_XML_FILE
from exception.models import handle_exception

logger = wevote_functions.admin.get_logger(__name__)

def electoral_districts_import_from_sample_file():
    """
    Get the XML data, and either create new entries or update existing
    :return:
    """
    # Load saved xml from local file
    logger.info("Loading electoral_districts from local XML file")

    xml_tree = ET.parse(CTCL_SAMPLE_XML_FILE)
    xml_root = xml_tree.getroot()

    if xml_root:
        # Look for ElectoralDistrict and create the Master table first. ElectoralDistrict is the direct child node
        # of vipObject
        electoralDistrictItemList = xml_root.findall('ElectoralDistrict')
        number_of_electoral_districts = len(electoralDistrictItemList)

    return electoral_district_import_from_xml_data(electoralDistrictItemList)


def electoral_district_import_from_xml_data(electoral_district_xml_data):
    """
    Get the xml data, and either create new entries or update existing entries for electoral district
    :return:
    """

    electoral_district_not_processed = 0
    electoral_district_saved = 0
    electoral_district_updated = 0
    success = False

    electoral_district_manager = ElectoralDistrictManager()
    for one_electoral_district in electoral_district_xml_data:
        electoral_district_number = None
        electoral_district_other_type = ''
        ocd_id_external_id = ''

        ctcl_id_temp = one_electoral_district.attrib['id']
        electoral_district_name = one_electoral_district.find('Name').text

        electoral_district_type_found = one_electoral_district.find('Type')
        if electoral_district_type_found is not None:
            electoral_district_type = electoral_district_type_found.text

        #TODO validate electoral_district_type from electoralDistrictType enum

        electoral_district_number_found = one_electoral_district.find('Number')
        if electoral_district_number_found is not None:
            electoral_district_number = convert_to_int(electoral_district_number_found.text)
            defaults = {
                'electoral_district_number' : electoral_district_number,
                'electoral_district_other_type' : electoral_district_other_type,
                'ocd_id_external_id': ocd_id_external_id
            }

        electoral_district_other_type_found = one_electoral_district.find('OtherType')

        if electoral_district_other_type_found is not None:
            electoral_district_other_type = electoral_district_other_type_found.text
            defaults = {
                'electoral_district_number' : electoral_district_number,
                'electoral_district_other_type' : electoral_district_other_type,
                'ocd_id_external_id': ocd_id_external_id
            }

        external_identifiers_list = one_electoral_district.findall(
            "./ExternalIdentifiers/ExternalIdentifier/[Type='ocd-id']/Value")
        if external_identifiers_list is not None:
            # look for value of 'ocd-id type value under ExternalIdentifier
            ocd_id_external_id = one_electoral_district.find(
                "./ExternalIdentifiers/ExternalIdentifier/[Type='ocd-id']/Value").text
            defaults = {
                'electoral_district_number' : electoral_district_number,
                'electoral_district_other_type' : electoral_district_other_type,
                'ocd_id_external_id' : ocd_id_external_id
            }
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
                # TODO currently update is not handled. Based on what constitues a unique row, update needs to be handled
                if electoral_district_query.count() > 0:
                    electoral_district_not_processed += 1
                else:
                    try:
                        results = electoral_district_manager.update_or_create_electoral_district(
                            ctcl_id_temp,
                            electoral_district_name,
                            electoral_district_type,
                            electoral_district_number,
                            electoral_district_other_type, ocd_id_external_id)
                        if not results:
                            electoral_district_not_processed += 1
                            success = False
                        elif results['new_electoral_district_created']:
                            electoral_district_saved += 1
                            success = True
                            status = "ELECTORAL_DISTRICT_IMPORT_PROCESS_CREATED"
                        else:
                            electoral_district_updated += 1
                            success = True
                            status = "ELECTORAL_DISTRICT_IMPORT_PROCESS_UPDATED"
                    except Exception as e:
                        status = 'FAILED update_or_create_electoral_district. ' \
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

def get_electoral_district_number(self):
    return self.electoral_district_number

def get_electoral_district_name(self):
    return self.electoral_district_name

def get_electoral_district_other_type(self):
    return self.electoral_district_other_type

def get_electoral_district_type(self):
    return self.electoral_district_type