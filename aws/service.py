#!/usr/bin/env python3

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import boto3
import json
from config.base import get_environment_variable

from functions.voter_profile import voter_profiler_job_example

# max time (in sec) that a job may take to complete
#  this prevents a different worker from picking up a job that
#  is currently being handled by another worker
MAX_JOB_PROCESSING_TIME = 60

MAX_JOB_RETRY_ATTEMPTS = 5

def process_request(function, body, message):

    if function == 'ProfileImageFetchResize':
        return voter_profiler_job_example(body)
    # TODO add other async jobs here

    # default: no function found
    return False




def worker_run(queue_url):
    AWS_REGION_NAME = get_environment_variable("AWS_REGION_NAME")
    sqs = boto3.client('sqs', region_name=AWS_REGION_NAME)

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
                    job_retry_count = int(message['Attributes']['ApproximateReceiveCount'])
                    if job_retry_count > MAX_JOB_RETRY_ATTEMPTS:
                        print("Message crossed max retry attempts, deleting.")
                        processed = True

            else:
                print("No function provided in SQS message, deleting invalid request.")
                processed = True

            # Delete processed message from queue
            if processed:
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )
                print('Deleted message: %s' % message)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sqs_url = os.environ.get("WEVOTE_SQS_WEB_FUNCTIONS_QUEUE_URL")
    worker_run(sqs_url)




    
