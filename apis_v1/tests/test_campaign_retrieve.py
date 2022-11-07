# apis_v1/test_campaign_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TransactionTestCase
from django.test import Client
from voter.models import VoterDeviceLink
 
import json

# Tests both campaignRetrieveView and campaignRetrieveAsOwnerView

# Inheriting from TransactionTestCase enables test mirror 
# to redirect queries from 'readonly' database to 'default'. 

class WeVoteAPIsV1TestsCampaignRetrieve(TransactionTestCase):
    databases = ["default", "readonly"]



    def setUp(self):
 
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_address_save_url = reverse("apis_v1:voterAddressSaveView")
        self.voter_retrieve_url = reverse("apis_v1:voterRetrieveView")
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.campaign_save_url = reverse("apis_v1:campaignSaveView")
        self.campaign_retrieve_url = reverse("apis_v1:campaignRetrieveView")
        self.campaign_retrieve_as_owner_url = reverse("apis_v1:campaignRetrieveAsOwnerView")
        # Creating Client object allows passing in META data to the
        # request object.
        self.client2 = Client(HTTP_USER_AGENT='Mozilla/5.0')
        
 

    def test_campaign_retrieve_with_no_voter_device_id(self):
        
        
        response1 = self.client2.get(self.campaign_retrieve_url)
        json_data1 = json.loads(response1.content.decode())
        
        # print("\ncampaign_retrieve_url:" + "\n")
        # print(response1.content)

        self.assertEqual('status' in json_data1,
                         True,
                         "status expected in the json response, and not found")

        self.assertEqual(json_data1['status'],
                         "CAMPAIGNX_NOT_FOUND-MISSING_VARIABLES CAMPAIGNX_RETRIEVE_ERROR ",
                         "status = {status} Expected status CAMPAIGNX_NOT_FOUND-MISSING_VARIABLES CAMPAIGNX_RETRIEVE_ERROR ".format(status=json_data1['status']))

        self.assertEqual(json_data1['success'],
                         False,
                         "success = {success} Expected fail".format(success=json_data1['success']))
                         
                         
                         
        
        response2 = self.client2.get(self.campaign_retrieve_as_owner_url)
        json_data2 = json.loads(response2.content.decode())
        
        # print("\ncampaign_retrieve_as_owner:" + "\n")
        # print(response2.content)

        self.assertEqual('status' in json_data2,
                         True,
                         "status expected in the json response, and not found")

        self.assertEqual(json_data2['status'],
                         "VALID_VOTER_ID_MISSING ",
                         "status = {status} Expected status VALID_VOTER_ID_MISSING ".format(status=json_data2['status']))

        self.assertEqual(json_data2['success'],
                         False,
                         "success = {success} Expected fail".format(success=json_data2['success']))




    def test_campaign_retrieve_with_voter_device_id(self):


        #### Generate a voter device id ####
        response1 = self.client2.get(self.generate_voter_device_id_url)
        json_data1 = json.loads(response1.content.decode())

        # print("\ngenerate_voter_device_id_url:" + "\n")
        # print(response1.content)

        self.assertEqual('voter_device_id' in json_data1,
                         True,
                         "voter_device_id expected in the json response, and not found")

        self.assertEqual(json_data1['status'],
                         "DEVICE_ID_GENERATE_VALUE_DOES_NOT_EXIST",
                         "status = {status} Expected status DEVICE_ID_GENERATE_VALUE_DOES_NOT_EXIST".format(status=json_data1['status']))

        self.assertEqual(json_data1['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data1['success']))                         

        voter_device_id = json_data1['voter_device_id'] if 'voter_device_id' in json_data1 else ''
        


        #### Generate a voter we vote id ####
            # Requires a voter device id #
        response2 = self.client2.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())
        
        # print("\nvoter_create_url:" + "\n")
        # print(response2.content)

        self.assertEqual('voter_we_vote_id' in json_data2,
                         True,
                         "voter_we_vote_id expected in the json response, and not found")

        self.assertEqual(json_data2['status'],
                         "VOTER_CREATED",
                         "status = {status} Expected status VOTER_CREATED".format(status=json_data2['status']))

        self.assertEqual(json_data2['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data2['success']))

        voter_we_vote_id = json_data2['voter_we_vote_id'] if 'voter_we_vote_id' in json_data2 else ''

        
        
        #### Generate voter address ####
            # Using voter device id #
        voter_address = "2 Lincoln Memorial Cir NW, Washington, DC 20002"
        response11 = self.client2.get(self.voter_address_save_url, {'voter_device_id': voter_device_id, 'voter_we_vote_id': voter_we_vote_id, 'text_for_map_search': voter_address, 'simple_save': True})
        json_data11 = json.loads(response11.content.decode())
        
        # print("\nvoter_address_save_url:" + "\n")
        # print(response11.content)
        


        #### Generate an organization we vote id ####
            # Requires a voter device id & voter we vote id #
        response3 = self.client2.get(self.voter_retrieve_url,{'voter_device_id': voter_device_id})
        json_data3 = json.loads(response3.content.decode())
        
        # print("\nvoter_retrieve_url:" + "\n")
        # print(response3.content) 

        self.assertEqual('linked_organization_we_vote_id' in json_data3,
                         True,
                         "linked_organization_we_vote_id expected in the json response, and not found")

        self.assertEqual(json_data3['status'],
                         "VOTER_RETRIEVE_START VOTER_DEVICE_ID_RECEIVED VOTER_FOUND VOTER.LINKED_ORGANIZATION_WE_VOTE_ID-MISSING EXISTING_ORGANIZATION_NOT_FOUND ORGANIZATION_CREATED FACEBOOK_LINK_TO_VOTER_NOT_FOUND ",
                         "status = {status} Expected status VOTER_RETRIEVE_START VOTER_DEVICE_ID_RECEIVED VOTER_FOUND VOTER.LINKED_ORGANIZATION_WE_VOTE_ID-MISSING EXISTING_ORGANIZATION_NOT_FOUND ORGANIZATION_CREATED FACEBOOK_LINK_TO_VOTER_NOT_FOUND ".format(status=json_data3['status']))

        self.assertEqual(json_data3['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data3['success']))

        organization_we_vote_id = json_data3["linked_organization_we_vote_id"] if "linked_organization_we_vote_id" in json_data3 else ''




        #### Generate a campaignx we vote id ####
            # Requires a voter device id, voter we vote id & organization we vote id #
        response4 = self.client2.get(self.campaign_save_url, {'voter_device_id': voter_device_id, 'voter_we_vote_id': voter_we_vote_id, 'organization_we_vote_id': organization_we_vote_id, 'in_draft_mode': False, 'in_draft_mode_changed': True})
        json_data4 = json.loads(response4.content.decode())
        
        # print("\ncampaign_save_url:" + "\n")
        # print(response4.content)

        self.assertEqual('campaignx_we_vote_id' in json_data4,
                         True,
                         "campaignx_we_vote_id expected in the json response, and not found")

        self.assertEqual(json_data4['status'],
                         "CAMPAIGNX_OWNER_CREATED RETRIEVE_CAMPAIGNX_AS_OWNER-VOTER_WE_VOTE_ID-NOT_FOUND CAMPAIGNX_CREATED ",
                         "status = {status} Expected status CAMPAIGNX_OWNER_CREATED RETRIEVE_CAMPAIGNX_AS_OWNER-VOTER_WE_VOTE_ID-NOT_FOUND CAMPAIGNX_CREATED ".format(status=json_data4['status']))

        self.assertEqual(json_data4['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data4['success']))

        campaignx_we_vote_id = json_data4["campaignx_we_vote_id"] if "campaignx_we_vote_id" in json_data4 else ''




        #### Retrieve campaign ####
        response5 = self.client2.get(self.campaign_retrieve_url, {'voter_device_id': voter_device_id, 'campaignx_we_vote_id': campaignx_we_vote_id})
        json_data5 = json.loads(response5.content.decode())
        
        # print("\ncampaign_retrieve_url:" + "\n")
        # print(response5.content)

        self.assertEqual(json_data5['status'],
                         "CAMPAIGNX_FOUND_WITH_WE_VOTE_ID ",
                         "status = {status} Expected status CAMPAIGNX_FOUND_WITH_WE_VOTE_ID ".format(status=json_data5['status']))

        self.assertEqual(json_data5['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data5['success']))

        self.assertEqual(len(json_data5["campaignx_owner_list"]), 
                         1,
                         "Expected position_list to have length 1, "
                         "actual length = {length}".format(length=len(json_data5["campaignx_owner_list"])))




        #### Retrieve campaign with voter-we-vote-id as an owner ####
        response6 = self.client2.get(self.campaign_retrieve_as_owner_url, {'voter_device_id': voter_device_id, 'campaignx_we_vote_id': campaignx_we_vote_id})
        json_data6 = json.loads(response6.content.decode())
        
        # print("\ncampaign_retrieve_as_owner:" + "\n")
        # print(response6.content)

        self.assertEqual(json_data6['status'],
                         "RETRIEVE_CAMPAIGNX_AS_OWNER_FOUND_WITH_WE_VOTE_ID ",
                         "status = {status} Expected status RETRIEVE_CAMPAIGNX_AS_OWNER_FOUND_WITH_WE_VOTE_ID ".format(status=json_data6['status']))

        self.assertEqual(json_data6['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data6['success']))                         

        self.assertEqual(json_data6['voter_can_send_updates_to_campaignx'],
                         True,
                         "voter_can_send_updates_to_campaignx = {voter_can_send_updates_to_campaignx} Expected true".format(voter_can_send_updates_to_campaignx=json_data6['voter_can_send_updates_to_campaignx']))
       



        #### Generate another set of voter entry variables: ####
        ## voter device id ####
        response7 = self.client2.get(self.generate_voter_device_id_url)
        json_data7 = json.loads(response7.content.decode())

        voter_device_id_2 = json_data7['voter_device_id'] if 'voter_device_id' in json_data7 else ''

        ## voter we vote id ##
        response8 = self.client2.get(self.voter_create_url, {'voter_device_id': voter_device_id_2})
        json_data8 = json.loads(response8.content.decode())

        voter_we_vote_id_2 = json_data8['voter_we_vote_id'] if 'voter_we_vote_id' in json_data8 else ''
        
        voter_address_2 = "300 E St SW, Washington, DC 20546"
        response12 = self.client2.get(self.voter_address_save_url, {'voter_device_id': voter_device_id_2, 'voter_we_vote_id': voter_we_vote_id_2, 'text_for_map_search': voter_address_2, 'simple_save': True})
        json_data12 = json.loads(response12.content.decode())
        
        # print("\nvoter_address_save_url:" + "\n")
        # print(response12.content)



        #### Retrieve campaign with non-owner voter id ####
        response9 = self.client2.get(self.campaign_retrieve_as_owner_url, {'voter_device_id': voter_device_id_2, 'campaignx_we_vote_id': campaignx_we_vote_id})
        json_data9 = json.loads(response9.content.decode())

        # print("\ncampaign_retrieve_as_owner:" + "\n")
        # print(response9.content)
        
        self.assertEqual(json_data9['status'],
                         "RETRIEVE_CAMPAIGNX_AS_OWNER_FOUND_WITH_WE_VOTE_ID ",
                         "status = {status} Expected status RETRIEVE_CAMPAIGNX_AS_OWNER_FOUND_WITH_WE_VOTE_ID ".format(status=json_data9['status']))

        self.assertEqual(json_data9['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data9['success']))                         

        self.assertEqual(json_data9['voter_can_send_updates_to_campaignx'],
                         False,
                         "voter_can_send_updates_to_campaignx = {voter_can_send_updates_to_campaignx} Expected false".format(voter_can_send_updates_to_campaignx=json_data9['voter_can_send_updates_to_campaignx']))        



        #### Retrieve campaign with invalid campaign id ####
        campaignx_we_vote_id_2 = "invalidID"

        response10 = self.client2.get(self.campaign_retrieve_url, {'voter_device_id': voter_device_id, 'campaignx_we_vote_id': campaignx_we_vote_id_2})
        json_data10 = json.loads(response10.content.decode())

        # print("\ncampaign_retrieve with invalid id:" + "\n")
        # print(response10.content)        

        self.assertEqual(json_data10['status'],
                         "CAMPAIGNX_NOT_FOUND_DoesNotExist CAMPAIGNX_NOT_FOUND: CAMPAIGNX_NOT_FOUND_DoesNotExist  ",
                         "status = {status} Expected status CAMPAIGNX_NOT_FOUND_DoesNotExist CAMPAIGNX_NOT_FOUND: CAMPAIGNX_NOT_FOUND_DoesNotExist  ".format(status=json_data10['status']))

        self.assertEqual(json_data10['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data10['success']))

        self.assertEqual(len(json_data10["campaignx_owner_list"]), 
                         0,
                         "Expected position_list to have length 0, "
                         "actual length = {length}".format(length=len(json_data10["campaignx_owner_list"])))
                         
                        
                        
        #### Direct database access ####
        # Allows views of the 'readonly' database to compare against
        # the 'default' database views used in the rest of the code:
        
        # The explanation for .using() is here: 
        # https://docs.djangoproject.com/en/dev/topics/db/multi-db/#manually-selecting-a-database

        # device_entry = VoterDeviceLink.objects.using('readonly').all().values()
        # print("Readonly voter device ID: ")
        # print(device_entry)

        # device_entry_2 = VoterDeviceLink.objects.using('default').all().values()
        # print("Default voter device ID: ")
        # print(device_entry_2)
