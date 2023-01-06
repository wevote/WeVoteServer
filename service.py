#!/usr/bin/env python

import os
import boto3
import json
from config.base import get_environment_variable


# max time (in sec) that a job may take to complete
#  this prevents a different worker from picking up a job that
#  is currently being handled by another worker
MAX_JOB_PROCESSING_TIME = 60


def process_request(function, body, message):
    if function == 'ProfileImageFetchResize':
        # TODO add code to do work here
        return True

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
                    next

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




    
