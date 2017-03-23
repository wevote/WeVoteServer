# import_export_ctcl/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import wevote_functions.admin
import xml.etree.ElementTree as ET
from django.contrib import messages


logger = wevote_functions.admin.get_logger(__name__)

CTCL_SAMPLE_XML_FILE = "import_export_ctcl/import_data/GoogleCivic.Sample.xml"

def import_ctcl_from_xml(request):
    load_from_url = False
    if load_from_url:
        # Request xml file from CTCL servers
        logger.debug("TO BE IMPLEMENTED: Load CTCL XML from url")
    else:
        # Load saved xml from local file
        logger.debug("Loading CTCL sample XML from local file")

        # ballot_measure_xml_element = request.get(CTCL_SAMPLE_XML_FILE, )
        xml_tree = ET.parse(CTCL_SAMPLE_XML_FILE)
        xml_root = xml_tree.getroot()

        if xml_root:
            for child in xml_root:
                messages.add_message(request, messages.INFO, child.tag, child.attrib)

            # Look for BallotMeasureSelection and create the Master table first
            for ballotMeasureSelectionItem in xml_root.findall('BallotMeasureSelection'):
                ballotMeasureSelectionItemId = ballotMeasureSelectionItem.get('id')
                # insert this row in ballotMeasureSelection table

            # Look for BallotMeasureContest node in the XML. BallotMeasureContest is the direct child node of vipObject
            vipChildren = xml_root.getchildren()
            if vipChildren and len(vipChildren):
                for vipChildElement in vipChildren:
                    messages.add_message(request, messages.INFO, vipChildElement.tag, vipChildElement.attrib)
                    # BallotSelectionIds is a separate table with BallotMeasureSelection
                    # TBD Add each BallotSelectionIds element to BallotMeasureSelection table?
                    # import BallotMeasureContest data from the file
                    # for ballotMeasureContestElement in xml_root.iter('BallotMeasureContest'):
                    #     messages.add_message(ballotMeasureContestElement.attrib)
    return