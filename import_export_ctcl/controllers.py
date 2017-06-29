# import_export_ctcl/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import wevote_functions.admin
from electoral_district.controllers import electoral_district_import_from_xml_data
import xml.etree.ElementTree as ElementTree
from party.controllers import party_import_from_xml_data
from .models import CandidateSelection
from exception.models import handle_exception

logger = wevote_functions.admin.get_logger(__name__)

CTCL_SAMPLE_XML_FILE = "import_export_ctcl/import_data/GoogleCivic.Sample.xml"

# Deprecated function, currently not used
def import_ctcl_from_xml(request):
    load_from_url = False
    results = ''
    success = False
    status = ''
    if load_from_url:
        # Request xml file from CTCL servers
        logger.debug("TO BE IMPLEMENTED: Load CTCL XML from url")
    else:
        # Load saved xml from local file
        xml_tree = ElementTree.parse(CTCL_SAMPLE_XML_FILE)
        xml_root = xml_tree.getroot()
        logger.debug("Loading CTCL sample XML from local file")

        if xml_root:
            # Look for ElectoralDistrict and create the Master table first. ElectoralDistrict is the direct child node
            # of VipObject
            electoral_district_item_list = ''

            electoral_district_item_list = xml_root.findall('ElectoralDistrict')
            if electoral_district_item_list:
                electoral_district_results = electoral_district_import_from_xml_data(electoral_district_item_list)

                if not electoral_district_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'ELECTORAL_DISTRICT_IMPORT_FAILED'
                    }
                    return results
                    # to_continue_parsing = False

            # Look for Party data and create Master table. Party is the direct child node of VipObject
            party_item_list = xml_root.findall('Party')

            party_results = party_import_from_xml_data(party_item_list)
            if not party_results['success']:
                results = {
                    'success': False,
                    'import_complete': 'PARTY_IMPORT_FAILED'
                }
                return results

            # Create a batch manager and invoke its class functions
            # TODO fix below import, temporary fix to avoid circular dependency
            from import_export_batches.models import BatchManager
            try:
                batch_manager = BatchManager()
                # Ballot Measure import, look for BallotMeasureContest
                ballot_measure_results = ''
                ballot_measure_results = batch_manager.store_measure_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not ballot_measure_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'BALLOT_MEASURE_IMPORT_FAILED'
                    }
                    return results

                # Office import, look for Office
                office_results = ''
                office_results = batch_manager.store_elected_office_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not office_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'ELECTED_OFFICE_IMPORT_FAILED'
                    }
                    return results

                politician_results = ''
                politician_results = batch_manager.store_politician_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not politician_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'POLITICIAN_IMPORT_FAILED'
                    }
                    return results

                candidate_results = ''
                candidate_results = batch_manager.store_candidate_xml(CTCL_SAMPLE_XML_FILE, 0, '', xml_root)
                if not candidate_results['success']:
                    results = {
                        'success': False,
                        'import_complete': 'CANDIDATE_IMPORT_FAILED'
                    }
                    return results

            except BatchManager.DoesNotExist:
                status = 'IMPORT_FAILED'
                success = False

                # success = 'True'
                # status = 'CTCL_SAMPLE_DATA_IMPORT_COMPLETE'

    results = {
        'success': True,
        'import_complete': 'CTCL_SAMPLE_DATA_IMPORT_COMPLETE'
    }

    return results


def create_candidate_selection_rows(xml_root, batch_set_id=0):
    """
    Create candidate selection entries in the CandidateSelection table based on CTCL XML CandidateSelection node values
    :param xml_root: 
    :param batch_set_id: 
    :return: 
    """
    success = False
    status = ''
    candidate_selection_created = False

    # Look for CandidateSelection and create the batch_header first. CandidateSelection is the direct child node
    # of VipObject
    candidate_selection_xml_node = xml_root.findall('CandidateSelection')
    candidate_selection = ''

    for one_candidate_selection in candidate_selection_xml_node:
        # look for relevant information under CandidateSelection: id, CandidateIds
        candidate_selection_id = one_candidate_selection.attrib['id']

        contest_office_id_node = one_candidate_selection.find("./CandidateIds")
        if contest_office_id_node is None:
            candidate_selection = CandidateSelection()
            results = {
                'success':                      False,
                'status':                       'CREATE_CANDIDATE_SELECTION_ROWS-CONTEST_OFFICE_ID_NOT_FOUND',
                'candidate_selection_created':  False,
                'candidate_selection':          candidate_selection,
            }
            return results

        contest_office_id = contest_office_id_node.text

        try:
            candidate_selection = CandidateSelection.objects.create( batch_set_id=batch_set_id,
                                                                     candidate_selection_id=candidate_selection_id,
                                                                     contest_office_id=contest_office_id,
                )
            if candidate_selection:
                candidate_selection_created = True
                success = True
                status = "CANDIDATE_SELECTION_CREATED"
        except Exception as e:
            candidate_selection_created = False
            candidate_selection = CandidateSelection()
            success = False
            status = "CANDIDATE_SELECTION_NOT_CREATED"
            handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                      success,
        'status':                       status,
        'candidate_selection_created':  candidate_selection_created,
        'candidate_selection':          candidate_selection
    }
    return results
