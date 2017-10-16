# party/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Party, PartyManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, LANGUAGE_CODE_ENGLISH
import xml.etree.ElementTree as ElementTree
from exception.models import handle_exception

logger = wevote_functions.admin.get_logger(__name__)


def party_import_from_sample_file(filename):
    """
    Get the XML data, and either create new entries or update existing
    :return:
    """
    # Load saved xml from local file
    logger.info("Loading parties from local XML file")

    xml_tree = ElementTree.parse(filename)
    # xml_tree = ElementTree.parse("/home/neelam/WeVote/vip_data_from_ctcl-Nov28_2016.xml")
    xml_root = xml_tree.getroot()

    party_item_list = ''

    if xml_root:
        # Look for Party and create the Master table first. Party is the direct child node
        # of VipObject
        party_item_list = xml_root.findall('Party')
        # number_of_parties = len(party_item_list)

    return party_import_from_xml_data(party_item_list)


def party_import_from_xml_data(party_xml_data):
    """
    Get the xml data, and either create new entries or update existing entries for party
    :return:
    """

    party_not_processed = 0
    party_saved = 0
    party_updated = 0
    success = False
    status = ''

    party_manager = PartyManager()
    for one_party in party_xml_data:
        # party_id_temp = ''
        party_name_english = None
        party_abbreviation = ''
        ctcl_uuid = ''
        duplicate_entry = 0

        party_id_temp = one_party.attrib['id']
        party_name_node_english = one_party.find("./Name/Text/[@language='" + LANGUAGE_CODE_ENGLISH + "']")
        if party_name_node_english is not None:
            party_name_english = party_name_node_english.text

        party_abbreviation_node = one_party.find('Abbreviation')
        if party_abbreviation_node is not None:
            party_abbreviation = party_abbreviation_node.text

        external_identifiers_list = one_party.findall(
            "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']/Value")
        if external_identifiers_list is not None:
            # look for value of 'ctcl-uuid' type value under ExternalIdentifier
            ctcl_uuid = one_party.find("./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']/Value").text

            # defaults = {
            #     'party_abbreviation': party_abbreviation,
            #     'ctcl_uuid': ctcl_uuid,
            # }
        # Make sure we have the minimum required variables
        if not positive_value_exists(party_id_temp) or not positive_value_exists(party_name_english):
            party_not_processed += 1
            continue

        # check if this is a duplicate entry
        try:
            party_query = Party.objects.order_by('id')
            if party_query:
                party_query = party_query.filter(party_id_temp=party_id_temp)
                # TODO currently update is not handled.Based on what constitues a unique row, update needs to be handled
                if party_query.count() > 0:
                    party_not_processed += 1
                    duplicate_entry = 1
            if duplicate_entry > 0:
                # This entry already exists, do not call update_or_create. Set success to True
                success = True
                status = "PARTY_ENTRY_EXISTS"
            else:
                try:
                    updated_values = {
                        'party_abbreviation': party_abbreviation,
                        'ctcl_uuid': ctcl_uuid,
                        'party_id_temp': party_id_temp,
                        'party_name': party_name_english
                    }

                    results = party_manager.update_or_create_party(
                        party_id_temp, ctcl_uuid, party_name_english, updated_values)
                    if not results:
                        party_not_processed += 1
                        success = False
                    elif results['new_party_created']:
                        party_saved += 1
                        success = True
                        status = "PARTY_IMPORT_PROCESS_CREATED"
                    else:
                        party_updated += 1
                        success = True
                        status = "PARTY_IMPORT_PROCESS_UPDATED"
                except Exception as e:
                    status = 'FAILED update_or_create_party. ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    handle_exception(e, logger=logger, exception_message=status)
                    success = False
                    pass

        except Party.DoesNotExist:
            pass

    party_results = {
        'success':          success,
        'status':           status,
        'saved':            party_saved,
        'updated':          party_updated,
        'not_processed':    party_not_processed,
    }

    return party_results


def retrieve_all_party_names_and_ids_api():
    results = ''
    try:
        party_manager = PartyManager()
        results = party_manager.retrieve_all_party_names_and_ids()
        if not results:
            # party_not_processed += 1
            success = False
            status = "PARTY_RETRIEVE_FAILED"
            results = {
                'success': success,
                'status': status,
            }

    except Exception as e:
        status = 'FAILED retrieve_all_party_names_and_ids. ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)

    return results
