import json
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from config.base import get_environment_variable

# For testing the job queue system locally, you can run an SQS 
# server locally using localstack within docker.
# Use the following commands to install:
#
#   pip install localstack localstack-client awscli-local
#
#   localstack start -d     (wait for sqs service to launch)
#
#   awslocal sqs create-queue --queue-name job-queue.fifo \
#     --attributes FifoQueue=true,ContentBasedDeduplication=true
#
# Make sure the QueueUrl displayed matches AWS_SQS_WEB_QUEUE_URL in
#  config file environment-variables.json

# max time (in sec) that a job may take to complete
#  this prevents a different worker from picking up a job that
#  is currently being handled by another worker
MAX_JOB_PROCESSING_TIME = 60
MAX_JOB_RETRY_ATTEMPTS = 5

def process_request(function, body, message):

    if function == 'ProfileImageFetchResize':
        from aws.functions.voter_profile import voter_profiler_job_example
        return voter_profiler_job_example(body)
    # TODO add other async jobs here

    # default: no function found, act as
    #  processed so it gets deleted
    print(f"Job references unknown function [{function}], deleting.")
    return True


def worker_run(queue_url):
    if queue_url.startswith('http://localhost'):
        try:
            import localstack_client.session as boto3
        except:
            import boto3
    else:
        import boto3

    sqs = boto3.client('sqs')

    while True:
        # Receive message from SQS queue
        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=['All'],
            MaxNumberOfMessages=1,
            MessageAttributeNames=['All'],
            VisibilityTimeout=MAX_JOB_PROCESSING_TIME,
            WaitTimeSeconds=20
        )

        if 'Messages' in response.keys() and len(response['Messages']) > 0:
            message = response['Messages'][0]
            print("Got message:", message)
            receipt_handle = message['ReceiptHandle']
            processed = False


            if 'Function' in message['MessageAttributes'].keys():
                function = message['MessageAttributes']['Function']['StringValue']
                print(f"Calling function [{function}]")
                body = json.loads(message['Body'])
                try:
                    processed = process_request(function, body, message)
                except Exception as e:
                    print("Failed to call function {function}:", e)

            else:
                print("No function provided in SQS message, deleting invalid request.")
                processed = True

            # expire messages after max number of retries
            if not processed:
                job_retry_count = int(message['Attributes']['ApproximateReceiveCount'])
                if job_retry_count > MAX_JOB_RETRY_ATTEMPTS:
                    print("Message crossed max retry attempts, deleting.")
                    processed = True

            # Delete processed message from queue
            if processed:
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                print('Deleted message: %s' % message)



class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        print("Starting job worker, waiting for jobs from SQS..")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        sqs_url = get_environment_variable("AWS_SQS_WEB_QUEUE_URL")
        worker_run(sqs_url)




    
