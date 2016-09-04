import os
import json
from locust import HttpLocust, TaskSet, task

class WeVoteTasks(TaskSet):

    def on_start(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), "test_variables.json")) as f:
                self.voter_device_id = json.loads(f.read())["voter_device_id"]
        except Exception as e:
            print("Cant find test_variables.json, generating new voter_device_id")
            response = self.client.get("/apis/v1/deviceIdGenerate/")
            self.voter_device_id = response.json()["voter_device_id"]
        print("voter_device_id = %s" % self.voter_device_id)

    @task(1)
    def homepage(self):
        voter_device_id = self.voter_device_id
        response = self.client.get("/apis/v1/voterAllStarsStatusRetrieve/?voter_device_id=%s" %
                                   voter_device_id, name="voterAllStarsStatusRetrieve")
        response = self.client.get("/apis/v1/voterRetrieve/?voter_device_id=%s" %
                                   voter_device_id, name="voterRetrieve")
        response = self.client.get("/apis/v1/voterAddressRetrieve/?voter_device_id=%s" %
                                   voter_device_id, name="voterAddressRetrieve")
        response = self.client.get("/apis/v1/searchAll/?voter_device_id=%s" %
                                   voter_device_id, name="searchAll")
        response = self.client.get("/apis/v1/voterAllPositionsRetrieve/?voter_device_id=%s" %
                                   voter_device_id, name="voterAllPositionsRetrieve")
        response = self.client.get("/apis/v1/positionsCountForAllBallotItems/?voter_device_id=%s" %
                                   voter_device_id, name="positionsCountForAllBallotItems")
        response = self.client.get("/apis/v1/voterAllPositionsRetrieve/?voter_device_id=%s" %
                                   voter_device_id, name="voterAllPositionsRetrieve")
        response = self.client.get("/apis/v1/voterGuidesToFollowRetrieve/?voter_device_id=%s&google_civic_election_id=5000&maximum_number_to_retrieve=15&search_string=" %
                                   voter_device_id, name="voterGuidesToFollowRetrieve")
        response = self.client.get("/apis/v1/voterGuidesFollowedRetrieve/?voter_device_id=%s" %
                                   voter_device_id, name="voterGuidesFollowedRetrieve")
        response = self.client.get("/apis/v1/voterBallotItemsRetrieve/?voter_device_id=%s&use_test_election=false" %
                                   voter_device_id, name="voterBallotItemsRetrieve")
        response = self.client.get("/apis/v1/positionsCountForAllBallotItems/?voter_device_id=%s" %
                                   voter_device_id, name="positionsCountForAllBallotItems")
        response = self.client.get("/apis/v1/voterGuidesToFollowRetrieve/?voter_device_id=%s&google_civic_election_id=0&maximum_number_to_retrieve=15&search_string=" %
                                   voter_device_id, name="voterGuidesToFollowRetrieve")

    # @task(1)
    # def organizationCount(self):
    #     response = self.client.get("/apis/v1/organizationCount/")
    #     #print "organizationCount:", response.status_code, response.content
    #     pass
    #
    # @task(1)
    # def voterCount(self):
    #     response = self.client.get("/apis/v1/voterCount/")
    #     #print "voterCount:", response.status_code, response.content
    #     pass


class WeVoteLocust(HttpLocust):
    task_set = WeVoteTasks
    min_wait = 500 #0.5s
    max_wait = 1500
