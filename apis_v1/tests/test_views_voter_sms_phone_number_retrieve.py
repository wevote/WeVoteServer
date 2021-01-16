# apis_v1/tests/test_views_voter_sms_phone_number_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
from email_outbound.models import EmailAddress, EmailManager
import json

class WeVoteAPIsV1TestsVoterSMSPhoneNumberRetrieve(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_sms_phone_number_save_url = reverse("apis_v1:voterSMSPhoneNumberSaveView")
        self.voter_sms_phone_number_retrieve_url = reverse("apis_v1:voterSMSPhoneNumberRetrieveView")

    def test_retrieve_with_no_voter_device_id(self):
        response = self.client.get(self.voter_sms_phone_number_retrieve_url)
        json_data = json.loads(response.content.decode())

        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual(json_data['status'],
                         "VALID_VOTER_DEVICE_ID_MISSING",
                         "status = {status} Expected status VALID_VOTER_DEVICE_ID_MISSING"
                         "voter_device_id: {voter_device_id}".format(status=json_data['status'],
                                                                     voter_device_id=json_data['voter_device_id']))

        self.assertEqual(len(json_data['sms_phone_number_list']),
                         0,
                         "Expected sms_phone_number_list to have length 0, "
                         "actual_length = {length}".format(length=len(json_data["sms_phone_number_list"])))

    def test_retrieve_with_voter_device_id(self):
        response = self.client.get(self.generate_voter_device_id_url)
        json_data = json.loads(response.content.decode())
        voter_device_id = json_data['voter_device_id'] if 'voter_device_id' in json_data else ''

        # Create a voter so we can test retrieve
        response2 = self.client.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())

        self.assertEqual('status' in json_data2, True,
                         "status expected in the voterSMSPhoneNumberRetrieve json response but not found")

        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterSMSPhoneNumberRetrieve json response but not found")

        # Retrieve voter's phone number list (verify that voter does not have an phone number list)
        response3 = self.client.get(self.voter_sms_phone_number_retrieve_url, {'voter_device_id':voter_device_id})
        json_data3 = json.loads(response3.content.decode())

        self.assertEqual('status' in json_data3, True,
                         "status expected in the json response, and not found")
        self.assertEqual(json_data3['status'],
                         "NO_SMS_PHONE_NUMBER_LIST_RETRIEVED ",
                         "status = {status} Expected status NO_SMS_PHONE_NUMBER_LIST_RETRIEVED"
                         "voter_device_id: {voter_device_id}".format(status=json_data3['status'],
                                                                      voter_device_id=json_data3['voter_device_id']))

        self.assertEqual(len(json_data3['sms_phone_number_list']), 0,
                         "Expected sms_phone_number_list to have length 0, "
                         "actual length = {length}".format(length=len(json_data3['sms_phone_number_list'])))


        # Valid Voter Device ID with a Phone Number
        # Save a phone number for the voter
        # Note: When saving a phone number, system checks to see if the area code is valid
        self.client.get(self.voter_sms_phone_number_save_url, {'sms_phone_number':
                                                                            '888-888-8888',
                                                                    'voter_device_id': voter_device_id})

        # Retrieve the voter's sms phone number
        response5 = self.client.get(self.voter_sms_phone_number_retrieve_url, {'voter_device_id': voter_device_id})
        json_data5 = json.loads(response5.content.decode())

        # Verify that the response contains one sms phone number
        self.assertEqual(len(json_data5['sms_phone_number_list']), 1,
                         'Expected sms_phone_number_list to have length 1, '
                         'actual length = {length}'.format(length=len(json_data5['sms_phone_number_list'])))

        # Verify that the response's sms phone number is correct (matches the one we created)
        response_number = json_data5["sms_phone_number_list"][0]["normalized_sms_phone_number"]
        self.assertEqual(response_number, '+1 888-888-8888',
                         'Expected sms phone number to be 888-888-8888, '
                         'actual sms phone number = {sms_phone_number}'.format(sms_phone_number=response_number))
