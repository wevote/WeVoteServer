from datetime import time
from logging import error
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone

from measure.models import ContestMeasure
from position.models import PositionEntered

import json

class WeVoteAPIsV1TestsPositionListForBallotItem(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.position_list_for_ballot_item_url = reverse("apis_v1:positionListForBallotItemView")

    def test_retrieve_with_missing_ballot_item_id(self):
        """
        Test response when request has no ballot_item_id
        """
        response = self.client.get(self.position_list_for_ballot_item_url)
        json_data = json.loads(response.content.decode())

        # note: this status has no trailing whitespace, but others do
        expected = {
            "status": "POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID",
            "success": False,
            "count": 0,
            "kind_of_ballot_item": "UNKNOWN",
            "ballot_item_id": 0,
            "ballot_item_we_vote_id": "",
            "position_list": []
        }

        # status key should be in response
        self.assertEqual('status' in json_data, True,
                        "no 'status' returned in json response")

        # "status": "POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID",
        self.assertEqual(json_data['status'], expected['status'],
                        f"Expected: {expected['status']}\n \
                        Received: {json_data['status']} ")

        # "success": False,
        self.assertEqual(json_data['success'], expected['success'],
                        f"Expected: {expected['success']}\n \
                        Received: {json_data['success']} ")

        # "count": 0,
        self.assertEqual(json_data["count"], expected['count'],
                        f"Expected: {expected['count']}\n \
                        Received: {json_data['count']} ")

        # "kind_of_ballot_item": "UNKNOWN",
        self.assertEqual(json_data["kind_of_ballot_item"],
                        expected['kind_of_ballot_item'],
                        f"Expected: {expected['kind_of_ballot_item']}\nReceived: {json_data['kind_of_ballot_item']} ")

        # "ballot_item_id": 0,
        self.assertEqual(json_data["ballot_item_id"],
                        expected['ballot_item_id'],
                        f"Expected: {expected['ballot_item_id']}\nReceived: {json_data['ballot_item_id']} ")

        # "ballot_item_we_vote_id": "",
        self.assertEqual(json_data["ballot_item_we_vote_id"],
                        expected['ballot_item_we_vote_id'],
                        f"Expected: {expected['ballot_item_we_vote_id']}\nReceived: {json_data['ballot_item_we_vote_id']} ")

        # "position_list": []
        self.assertEqual(len(json_data["position_list"]), len(expected["position_list"]),
                         f"Expected failed response to return empty position_list")

    def test_retrieve_with_invalid_kind_of_ballot_item(self):
        """
        Test response when request has invalid kind_of_ballot_item
        valid options: "OFFICE", "CANDIDATE", "POLITICIAN" or "MEASURE"
        """
        # Stub Measure
        measure = ContestMeasure(
            measure_title="Mock Measure",
            district_id=123,
            district_name='LandTown',
            state_code='CA')
        measure.save()

        # check correct param will return success to establish a baseline
        response_valid = self.client.get(self.position_list_for_ballot_item_url, {
            "kind_of_ballot_item": "MEASURE",
            "ballot_item_id": measure.id,
            "ballot_item_we_vote_id": measure.we_vote_id
        })
        json_data_valid = json.loads(response_valid.content.decode())

        # Note: this status has a trailing whitespace
        # status: "POSITION_LIST_FOR_BALLOT_ITEM KIND_OF_BALLOT_ITEM_MEASURE "
        self.assertEqual(json_data_valid['status'],
            "POSITION_LIST_FOR_BALLOT_ITEM KIND_OF_BALLOT_ITEM_MEASURE ",
            f"Expected: POSITION_LIST_FOR_BALLOT_ITEM KIND_OF_BALLOT_ITEM_MEASURE  \n \
            Received: {json_data_valid['status']} ")

        # this will fail because "measure" is not uppercase
        invalid_parameter = {
            "kind_of_ballot_item": "measure",
            "ballot_item_id": measure.id,
            "ballot_item_we_vote_id": measure.we_vote_id
        }

        response_invalid = self.client.get(self.position_list_for_ballot_item_url, invalid_parameter)
        json_data = json.loads(response_invalid.content.decode())

        # note: this status has no trailing whitespace, but others may
        expected = {
            "status": "POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID",
            "success": False,
            "count": 0,
            "kind_of_ballot_item": "UNKNOWN",
            "ballot_item_id": 0,
            "ballot_item_we_vote_id": "",
            "position_list": []
        }

        # status key should be in response
        self.assertEqual('status' in json_data, True,
                        "no 'status' returned in json response")

        # "status": "POSITION_LIST_RETRIEVE_MISSING_BALLOT_ITEM_ID",
        self.assertEqual(json_data['status'], expected['status'],
                         f"Expected: {expected['status']}\n \
                         Received: {json_data['status']} ")

        # "success": False,
        self.assertEqual(json_data['success'], expected['success'],
                        f"Expected: {expected['success']}\n \
                        Received: {json_data['success']} ")

        # "count": 0,
        self.assertEqual(json_data["count"], expected['count'],
                         f"Expected: {expected['count']}\n \
                         Received: {json_data['count']} ")

        # "kind_of_ballot_item": "UNKNOWN",
        self.assertEqual(json_data["kind_of_ballot_item"],
                         expected['kind_of_ballot_item'],
                         f"Expected: {expected['kind_of_ballot_item']}\n \
                        Received: {json_data['kind_of_ballot_item']} ")

        # "ballot_item_id": 0,
        self.assertEqual(json_data["ballot_item_id"],
                         expected['ballot_item_id'],
                         f"Expected: {expected['ballot_item_id']}\n \
                        Received: {json_data['ballot_item_id']} ")

        # "ballot_item_we_vote_id": "",
        self.assertEqual(json_data["ballot_item_we_vote_id"],
                         expected['ballot_item_we_vote_id'],
                         f"Expected: {expected['ballot_item_we_vote_id']} \n \ Received: {json_data['ballot_item_we_vote_id']} ")

        # "position_list": []
        self.assertEqual(len(json_data["position_list"]),
                         len(expected["position_list"]),
                         f"Expected failed response to return empty position_list")
