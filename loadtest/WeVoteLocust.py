from locust import HttpLocust, TaskSet, task

class WeVoteTasks(TaskSet):

    @task(1)
    def organizationCount(self):
        response = self.client.get("/apis/v1/organizationCount/")
        #print "organizationCount:", response.status_code, response.content
        pass

    @task(1)
    def voterCount(self):
        response = self.client.get("/apis/v1/voterCount/")
        #print "voterCount:", response.status_code, response.content
        pass


class WeVoteLocust(HttpLocust):
    task_set = WeVoteTasks
    min_wait = 500 #0.5s
    max_wait = 1500
